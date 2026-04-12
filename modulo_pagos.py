"""
Módulo de Pagos: control de abonos y saldos pendientes.
"""

import flet as ft
from database import (
    listar_pagos, registrar_pago, listar_pacientes,
    listar_tratamientos,
)

METODOS_PAGO = [
    "Efectivo", "Tarjeta de Débito", "Tarjeta de Crédito",
    "Transferencia Bancaria", "Obra Social", "Cheque", "Otro",
]


def _tarjeta_resumen(titulo: str, monto: float, color: str) -> ft.Container:
    return ft.Container(
        content=ft.Column(controls=[
            ft.Text(titulo, size=12, color="#FAFAFA"),
            ft.Text(f"$ {monto:.2f}", size=20, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
        ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor=color, border_radius=10, padding=16, expand=True,
    )


class FormularioPago(ft.Column):
    def __init__(self, paciente_id: str, on_guardar=None, snack_fn=None):
        super().__init__(spacing=10)
        self.paciente_id = paciente_id
        self.on_guardar = on_guardar
        self.snack_fn = snack_fn
        self._construir()

    def _construir(self):
        tratamientos = listar_tratamientos(self.paciente_id)

        self.dd_tratamiento = ft.Dropdown(
            label="Imputar a tratamiento (opcional)",
            options=[
                ft.dropdown.Option(
                    t["id"],
                    f"D{t.get('diente','–')} {t.get('cara','')} · "
                    f"{t.get('descripcion','')} · $ {float(t.get('costo',0)):.2f}",
                )
                for t in tratamientos
            ],
        )
        self.tf_monto     = ft.TextField(label="Monto ($)", autofocus=True,
                                          keyboard_type=ft.KeyboardType.NUMBER, expand=True)
        self.dd_metodo    = ft.Dropdown(
            label="Método de pago", value="Efectivo",
            options=[ft.dropdown.Option(m) for m in METODOS_PAGO],
            expand=True,
        )
        self.tf_comprob   = ft.TextField(label="Nº Comprobante / Recibo", expand=True)
        self.tf_notas     = ft.TextField(label="Notas", multiline=True, min_lines=2)

        self.controls = [
            ft.Text("Registrar Pago", size=14, weight=ft.FontWeight.BOLD),
            self.dd_tratamiento,
            ft.Row(controls=[self.tf_monto, self.dd_metodo], spacing=8),
            self.tf_comprob,
            self.tf_notas,
            ft.ElevatedButton("Confirmar Pago", icon=ft.Icons.PAYMENT,
                              on_click=self._guardar),
        ]

    def _guardar(self, e):
        monto_str = (self.tf_monto.value or "").strip().replace(",", ".")
        if not monto_str:
            if self.snack_fn:
                self.snack_fn("Ingresá el monto.", error=True)
            return
        try:
            datos = {
                "paciente_id":    self.paciente_id,
                "tratamiento_id": self.dd_tratamiento.value,
                "monto":          float(monto_str),
                "metodo":         self.dd_metodo.value,
                "comprobante":    self.tf_comprob.value,
                "notas":          self.tf_notas.value,
            }
            registrar_pago(datos)
            if self.snack_fn:
                self.snack_fn("Pago registrado correctamente.")
            if self.on_guardar:
                self.on_guardar()
        except Exception as ex:
            if self.snack_fn:
                self.snack_fn(f"Error: {ex}", error=True)


class PagosView(ft.Column):
    def __init__(self):
        super().__init__(spacing=16, expand=True)
        self.paciente_id: str | None = None
        self._mostrar_form = False
        self._resumen_row  = ft.Row(spacing=12)
        self._form_area    = ft.Column(spacing=0)
        self._historial    = ft.Column(spacing=6)
        self._construir_base()

    def _snack(self, msg, error=False):
        if self.page:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(msg),
                bgcolor=ft.Colors.RED_700 if error else ft.Colors.GREEN_700,
                open=True,
            )
            self.page.update()

    def _construir_base(self):
        pacientes = listar_pacientes()
        self.dd_selector = ft.Dropdown(
            label="Seleccionar paciente",
            options=[ft.dropdown.Option(p["id"],
                     f"{p.get('apellido','')}, {p.get('nombre','')}") for p in pacientes],
            on_change=lambda e: self._cargar_paciente(e.control.value),
            width=360,
        )
        self.controls = [
            ft.Text("Control de Pagos", size=18, weight=ft.FontWeight.BOLD),
            self.dd_selector,
            self._resumen_row,
            self._form_area,
            self._historial,
        ]

    def _cargar_paciente(self, pid: str):
        self.paciente_id = pid
        self._mostrar_form = False
        self._actualizar()

    def _actualizar(self):
        if not self.paciente_id:
            return

        tratamientos = listar_tratamientos(self.paciente_id)
        pagos        = listar_pagos(self.paciente_id)
        total    = sum(float(t.get("costo", 0)) for t in tratamientos)
        pagado   = sum(float(p.get("monto", 0)) for p in pagos)
        saldo    = total - pagado

        # Tarjetas de resumen
        self._resumen_row.controls = [
            _tarjeta_resumen("Total Presupuestado", total, "#1565C0"),
            _tarjeta_resumen("Total Pagado", pagado, "#2E7D32"),
            _tarjeta_resumen("Saldo Pendiente", saldo,
                             "#C62828" if saldo > 0 else "#616161"),
        ]

        # Formulario de pago
        self._form_area.controls = [
            ft.Row(controls=[
                ft.ElevatedButton(
                    "- Cerrar" if self._mostrar_form else "+ Registrar Pago",
                    icon=ft.Icons.REMOVE if self._mostrar_form else ft.Icons.ADD,
                    on_click=lambda e: self._toggle_form(),
                ),
            ]),
            FormularioPago(self.paciente_id,
                           on_guardar=self._refrescar,
                           snack_fn=self._snack)
            if self._mostrar_form else ft.Container(),
        ]

        # Historial
        filas = []
        for p in pagos:
            filas.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(str(p.get("fecha",""))[:10], size=11)),
                ft.DataCell(ft.Text(p.get("metodo",""), size=11)),
                ft.DataCell(ft.Text(f"$ {float(p.get('monto',0)):.2f}",
                                    size=11, weight=ft.FontWeight.W_600)),
                ft.DataCell(ft.Text(p.get("comprobante",""), size=11)),
                ft.DataCell(ft.Text(p.get("notas",""), size=11)),
            ]))

        self._historial.controls = [
            ft.Divider(),
            ft.Text("Historial de Pagos", size=14, weight=ft.FontWeight.W_500),
            ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Fecha", size=11)),
                    ft.DataColumn(ft.Text("Método", size=11)),
                    ft.DataColumn(ft.Text("Monto", size=11), numeric=True),
                    ft.DataColumn(ft.Text("Comprobante", size=11)),
                    ft.DataColumn(ft.Text("Notas", size=11)),
                ],
                rows=filas,
                column_spacing=16,
            ) if filas else ft.Text("Sin pagos registrados.", color="#9E9E9E"),
        ]

        for widget in [self._resumen_row, self._form_area, self._historial]:
            if widget.page:
                widget.update()

    def _toggle_form(self):
        self._mostrar_form = not self._mostrar_form
        self._actualizar()

    def _refrescar(self):
        self._mostrar_form = False
        self._actualizar()
