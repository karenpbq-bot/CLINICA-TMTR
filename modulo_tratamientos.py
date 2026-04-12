"""
Módulo de Tratamientos: presupuestos detallados por diente y cara tratada.
"""

import flet as ft
from database import (
    listar_tratamientos, crear_tratamiento, actualizar_tratamiento,
    listar_pacientes, listar_especialistas,
)

CARAS_DIENTE = ["Oclusal", "Vestibular", "Lingual/Palatino", "Mesial", "Distal"]
ESTADOS_TRATAMIENTO = {
    "presupuestado": "Presupuestado",
    "aprobado":      "Aprobado",
    "realizado":     "Realizado",
}
ESTADO_COLOR = {
    "presupuestado": "#FFE0B2",
    "aprobado":      "#BBDEFB",
    "realizado":     "#C8E6C9",
}
TIPOS_TRATAMIENTO = [
    "Consulta / Revisión", "Limpieza / Profilaxis",
    "Obturación (Resina)", "Obturación (Amalgama)",
    "Endodoncia", "Extracción Simple", "Extracción Quirúrgica",
    "Corona Porcelana", "Corona Metal-Porcelana", "Implante Dental",
    "Carilla Porcelana", "Ortodoncia – Cuota mensual",
    "Blanqueamiento", "Placa Miorelajante",
    "Radiografía Periapical", "Radiografía Panorámica", "Otro",
]
DIENTES_FDI = (
    list(range(11, 19)) + list(range(21, 29)) +
    list(range(31, 39)) + list(range(41, 49))
)


class FormularioTratamiento(ft.Column):
    def __init__(self, paciente_id: str, tratamiento: dict = None,
                 on_guardar=None, snack_fn=None):
        super().__init__(spacing=10)
        self.paciente_id = paciente_id
        self.tratamiento = tratamiento or {}
        self.on_guardar = on_guardar
        self.snack_fn = snack_fn
        self._construir()

    def _construir(self):
        t = self.tratamiento
        especialistas = listar_especialistas()

        self.dd_diente = ft.Dropdown(
            label="Diente (FDI)",
            value=str(t["diente"]) if t.get("diente") else None,
            options=[ft.dropdown.Option(str(d), str(d)) for d in DIENTES_FDI],
            width=130,
        )
        self.dd_cara = ft.Dropdown(
            label="Cara",
            value=t.get("cara"),
            options=[ft.dropdown.Option(c) for c in CARAS_DIENTE],
            width=180,
        )
        self.dd_especialista = ft.Dropdown(
            label="Especialista",
            value=t.get("especialista_id"),
            options=[ft.dropdown.Option(e["id"],
                     f"Dr/a. {e.get('apellido','')}") for e in especialistas],
            expand=True,
        )
        self.dd_tipo = ft.Dropdown(
            label="Tratamiento",
            value=t.get("descripcion"),
            options=[ft.dropdown.Option(tp) for tp in TIPOS_TRATAMIENTO],
            expand=True,
        )
        self.tf_costo = ft.TextField(
            label="Costo ($)", value=str(t.get("costo", "0")),
            keyboard_type=ft.KeyboardType.NUMBER, width=130,
        )
        self.dd_estado = ft.Dropdown(
            label="Estado", value=t.get("estado", "presupuestado"),
            options=[ft.dropdown.Option(k, v) for k, v in ESTADOS_TRATAMIENTO.items()],
            width=180,
        )

        self.controls = [
            ft.Text("Agregar Ítem" if not t.get("id") else "Editar Ítem",
                    size=14, weight=ft.FontWeight.BOLD),
            ft.Row(controls=[self.dd_diente, self.dd_cara, self.tf_costo], spacing=8),
            ft.Row(controls=[self.dd_tipo, self.dd_especialista], spacing=8),
            ft.Row(controls=[self.dd_estado], spacing=8),
            ft.ElevatedButton("Guardar Ítem", icon=ft.Icons.SAVE, on_click=self._guardar),
        ]

    def _guardar(self, e):
        descripcion = self.dd_tipo.value
        if not descripcion:
            if self.snack_fn:
                self.snack_fn("Seleccioná un tipo de tratamiento.", error=True)
            return
        datos = {
            "paciente_id":     self.paciente_id,
            "especialista_id": self.dd_especialista.value,
            "diente":          int(self.dd_diente.value) if self.dd_diente.value else None,
            "cara":            self.dd_cara.value,
            "descripcion":     descripcion,
            "costo":           float(self.tf_costo.value.replace(",", ".") or 0),
            "estado":          self.dd_estado.value or "presupuestado",
        }
        try:
            if self.tratamiento.get("id"):
                actualizar_tratamiento(self.tratamiento["id"], datos)
            else:
                crear_tratamiento(datos)
            if self.snack_fn:
                self.snack_fn("Tratamiento guardado.")
            if self.on_guardar:
                self.on_guardar()
        except Exception as ex:
            if self.snack_fn:
                self.snack_fn(f"Error: {ex}", error=True)


class TratamientosView(ft.Column):
    def __init__(self):
        super().__init__(spacing=16, expand=True, scroll=ft.ScrollMode.AUTO)
        self.paciente_id: str | None = None
        self._mostrar_form = False
        self._contenido = ft.Column(spacing=12, expand=True)
        self._construir_selector()

    def _snack(self, msg, error=False):
        if self.page:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(msg),
                bgcolor=ft.Colors.RED_700 if error else ft.Colors.GREEN_700,
                open=True,
            )
            self.page.update()

    def _construir_selector(self):
        pacientes = listar_pacientes()
        self.dd_selector = ft.Dropdown(
            label="Seleccionar paciente",
            options=[ft.dropdown.Option(p["id"],
                     f"{p.get('apellido','')}, {p.get('nombre','')}") for p in pacientes],
            on_change=lambda e: self._cargar_paciente(e.control.value),
            width=360,
        )
        self.controls = [
            ft.Text("Módulo de Tratamientos", size=18, weight=ft.FontWeight.BOLD),
            self.dd_selector,
            self._contenido,
        ]

    def _cargar_paciente(self, pid: str):
        self.paciente_id = pid
        self._mostrar_form = False
        self._actualizar_contenido()

    def _actualizar_contenido(self):
        if not self.paciente_id:
            self._contenido.controls = []
            if self._contenido.page:
                self._contenido.update()
            return

        tratamientos = listar_tratamientos(self.paciente_id)
        total = sum(float(t.get("costo", 0)) for t in tratamientos)

        items = []
        for t in tratamientos:
            estado = t.get("estado", "presupuestado")
            esp = t.get("especialistas") or {}
            items.append(
                ft.Container(
                    content=ft.Row(controls=[
                        ft.Column(controls=[
                            ft.Text(
                                f"Diente {t.get('diente','–')} · {t.get('cara','–')}",
                                size=12, weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(t.get("descripcion", ""), size=12),
                            ft.Text(f"Dr/a. {esp.get('apellido','–')}", size=11,
                                    color="#757575"),
                        ], spacing=2, expand=True),
                        ft.Column(controls=[
                            ft.Text(f"$ {float(t.get('costo',0)):.2f}",
                                    size=13, weight=ft.FontWeight.W_600),
                            ft.Text(ESTADOS_TRATAMIENTO.get(estado, estado),
                                    size=11, color="#424242"),
                        ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.END),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=10, border_radius=6,
                    bgcolor=ESTADO_COLOR.get(estado, "#F5F5F5"),
                )
            )

        form = (FormularioTratamiento(self.paciente_id,
                                       on_guardar=self._refrescar,
                                       snack_fn=self._snack)
                if self._mostrar_form else ft.Container())

        self._contenido.controls = [
            ft.Row(controls=[
                ft.Text(f"Total presupuestado: $ {total:.2f}",
                        size=14, weight=ft.FontWeight.W_600),
                ft.ElevatedButton(
                    "- Cerrar" if self._mostrar_form else "+ Agregar ítem",
                    icon=ft.Icons.REMOVE if self._mostrar_form else ft.Icons.ADD,
                    on_click=lambda e: self._toggle_form(),
                ),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            form,
            ft.Divider(),
            ft.Column(controls=items if items else [
                ft.Text("Sin tratamientos registrados.", color="#9E9E9E")
            ], spacing=6),
        ]
        if self._contenido.page:
            self._contenido.update()

    def _toggle_form(self):
        self._mostrar_form = not self._mostrar_form
        self._actualizar_contenido()

    def _refrescar(self):
        self._mostrar_form = False
        self._actualizar_contenido()
