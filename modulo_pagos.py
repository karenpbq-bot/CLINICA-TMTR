"""
Módulo de Pagos: control de abonos y saldos pendientes.
"""

import flet as ft
from database import (
    listar_pagos,
    registrar_pago,
    saldo_pendiente,
    listar_pacientes,
    listar_tratamientos,
)

METODOS_PAGO = [
    "Efectivo",
    "Tarjeta de Débito",
    "Tarjeta de Crédito",
    "Transferencia Bancaria",
    "Obra Social",
    "Cheque",
    "Otro",
]


class ResumenFinanciero(ft.UserControl):
    """Tarjetas de resumen: total presupuestado, pagado y saldo."""

    def __init__(self, paciente_id: str):
        super().__init__()
        self.paciente_id = paciente_id

    def build(self):
        tratamientos = listar_tratamientos(self.paciente_id)
        pagos = listar_pagos(self.paciente_id)

        total = sum(float(t.get("costo", 0)) for t in tratamientos)
        pagado = sum(float(p.get("monto", 0)) for p in pagos)
        saldo = total - pagado

        def tarjeta(titulo, monto, color):
            return ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(titulo, size=12, color=ft.colors.WHITE70),
                        ft.Text(f"$ {monto:.2f}", size=20,
                                weight=ft.FontWeight.BOLD, color=ft.colors.WHITE),
                    ],
                    spacing=4,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=color,
                border_radius=10,
                padding=16,
                expand=True,
            )

        return ft.Row(
            controls=[
                tarjeta("Total Presupuestado", total, ft.colors.BLUE_700),
                tarjeta("Total Pagado", pagado, ft.colors.GREEN_700),
                tarjeta("Saldo Pendiente", saldo,
                        ft.colors.RED_700 if saldo > 0 else ft.colors.GREY_600),
            ],
            spacing=12,
        )


class FormularioPago(ft.UserControl):
    """Formulario para registrar un nuevo abono."""

    def __init__(self, paciente_id: str, on_guardar=None):
        super().__init__()
        self.paciente_id = paciente_id
        self.on_guardar = on_guardar

    def build(self):
        tratamientos = listar_tratamientos(self.paciente_id)

        self.dd_tratamiento = ft.Dropdown(
            label="Imputar a tratamiento (opcional)",
            options=[
                ft.dropdown.Option(
                    t["id"],
                    f"Diente {t.get('diente', '–')} · {t.get('descripcion', '')} · $ {float(t.get('costo', 0)):.2f}",
                )
                for t in tratamientos
            ],
        )

        self.tf_monto = ft.TextField(
            label="Monto ($)",
            keyboard_type=ft.KeyboardType.NUMBER,
            autofocus=True,
        )

        self.dd_metodo = ft.Dropdown(
            label="Método de pago",
            value="Efectivo",
            options=[ft.dropdown.Option(m) for m in METODOS_PAGO],
        )

        self.tf_comprobante = ft.TextField(label="Nº Comprobante / Recibo")

        self.tf_notas = ft.TextField(
            label="Notas",
            multiline=True,
            min_lines=2,
        )

        return ft.Column(
            controls=[
                ft.Text("Registrar Pago", size=14, weight=ft.FontWeight.BOLD),
                self.dd_tratamiento,
                ft.Row(controls=[self.tf_monto, self.dd_metodo], spacing=8),
                self.tf_comprobante,
                self.tf_notas,
                ft.ElevatedButton("Confirmar Pago", icon=ft.icons.PAYMENT, on_click=self.guardar),
            ],
            spacing=10,
        )

    def guardar(self, e):
        monto_str = self.tf_monto.value.strip().replace(",", ".")
        if not monto_str:
            return

        datos = {
            "paciente_id": self.paciente_id,
            "tratamiento_id": self.dd_tratamiento.value,
            "monto": float(monto_str),
            "metodo": self.dd_metodo.value,
            "comprobante": self.tf_comprobante.value,
            "notas": self.tf_notas.value,
        }
        registrar_pago(datos)
        if self.on_guardar:
            self.on_guardar()


class HistorialPagos(ft.UserControl):
    """Tabla de pagos realizados por el paciente."""

    def __init__(self, paciente_id: str):
        super().__init__()
        self.paciente_id = paciente_id

    def build(self):
        pagos = listar_pagos(self.paciente_id)

        if not pagos:
            return ft.Text("Sin pagos registrados.", color=ft.colors.GREY_500)

        filas = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(str(p.get("fecha", ""))[:10])),
                ft.DataCell(ft.Text(p.get("metodo", ""))),
                ft.DataCell(ft.Text(f"$ {float(p.get('monto', 0)):.2f}",
                                    weight=ft.FontWeight.W_600)),
                ft.DataCell(ft.Text(p.get("comprobante", ""))),
                ft.DataCell(ft.Text(p.get("notas", ""), size=11)),
            ])
            for p in pagos
        ]

        return ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Fecha")),
                ft.DataColumn(ft.Text("Método")),
                ft.DataColumn(ft.Text("Monto"), numeric=True),
                ft.DataColumn(ft.Text("Comprobante")),
                ft.DataColumn(ft.Text("Notas")),
            ],
            rows=filas,
        )


class PagosView(ft.UserControl):
    """Vista principal del módulo de pagos."""

    def __init__(self, paciente_id: str = None):
        super().__init__()
        self.paciente_id = paciente_id
        self.mostrar_formulario = False

    def build(self):
        return ft.Column(
            controls=[
                ft.Text("Control de Pagos", size=18, weight=ft.FontWeight.BOLD),
                self._selector_paciente(),
            ],
            spacing=16,
            padding=8,
            expand=True,
        )

    def _selector_paciente(self):
        pacientes = listar_pacientes()
        return ft.Column(
            controls=[
                ft.Dropdown(
                    label="Seleccionar paciente",
                    options=[
                        ft.dropdown.Option(p["id"], f"{p['apellido']}, {p['nombre']}")
                        for p in pacientes
                    ],
                    on_change=lambda e: self._cargar_paciente(e.control.value),
                    width=360,
                ),
                ft.Container(key="contenido_pagos"),
            ],
            spacing=12,
        )

    def _cargar_paciente(self, paciente_id: str):
        self.paciente_id = paciente_id
        self.mostrar_formulario = False

        contenido = ft.Column(
            controls=[
                ResumenFinanciero(paciente_id),
                ft.Divider(),
                ft.ElevatedButton(
                    "+ Registrar Pago",
                    icon=ft.icons.ADD,
                    on_click=lambda e: self._toggle_formulario(paciente_id),
                ),
                FormularioPago(paciente_id, on_guardar=lambda: self._cargar_paciente(paciente_id))
                if self.mostrar_formulario else ft.Container(),
                ft.Divider(),
                ft.Text("Historial de Pagos", size=14, weight=ft.FontWeight.BOLD),
                HistorialPagos(paciente_id),
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        # Reemplazar el contenedor de contenido
        col = self.controls[0] if self.controls else None
        if col and isinstance(col, ft.Column):
            # Encontrar el container de contenido y actualizarlo
            for ctrl in col.controls:
                if isinstance(ctrl, ft.Column):
                    if len(ctrl.controls) > 1:
                        ctrl.controls[1] = contenido
                        break
        self.update()

    def _toggle_formulario(self, paciente_id: str):
        self.mostrar_formulario = not self.mostrar_formulario
        self._cargar_paciente(paciente_id)
