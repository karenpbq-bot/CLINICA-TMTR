"""
Módulo de Especialistas: gestión de profesionales y su disponibilidad.
"""

import flet as ft
from database import (
    listar_especialistas,
    crear_especialista,
    actualizar_especialista,
    listar_disponibilidad,
    guardar_disponibilidad,
    eliminar_disponibilidad,
)

ESPECIALIDADES_DISPONIBLES = [
    "Odontología General",
    "Ortodoncia",
    "Odontopediatría",
    "Periodoncia",
    "Endodoncia",
    "Implantología",
    "Cirugía Maxilofacial",
    "Estética Dental",
    "Rehabilitación Oral",
    "Radiología Dental",
]

DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# Niveles de certeza con íconos de color
CERTEZA_OPCIONES = {
    "confirmado":   {"label": "🟢 Confirmado",     "valor": "confirmado"},
    "probable":     {"label": "🟡 Probable",        "valor": "probable"},
    "por_confirmar":{"label": "⚪ Por confirmar", "valor": "por_confirmar"},
}


class DisponibilidadEditor(ft.UserControl):
    """Editor de bloques de disponibilidad semanal para un especialista."""

    def __init__(self, especialista_id: str):
        super().__init__()
        self.especialista_id = especialista_id
        self.bloques = []

    def did_mount(self):
        self.bloques = listar_disponibilidad(self.especialista_id)
        self.update()

    def agregar_bloque(self, e):
        nuevo = {
            "especialista_id": self.especialista_id,
            "dia_semana": 0,
            "hora_inicio": "08:00",
            "hora_fin": "12:00",
            "certeza": "por_confirmar",
        }
        resultado = guardar_disponibilidad(nuevo)
        if resultado:
            self.bloques.append(resultado[0] if isinstance(resultado, list) else resultado)
        self.update()

    def build(self):
        filas = []
        for bloque in self.bloques:
            certeza_actual = bloque.get("certeza", "por_confirmar")
            certeza_label = CERTEZA_OPCIONES.get(certeza_actual, {}).get("label", certeza_actual)

            fila = ft.Row(
                controls=[
                    ft.Dropdown(
                        label="Día",
                        value=str(bloque.get("dia_semana", 0)),
                        options=[
                            ft.dropdown.Option(str(i), d) for i, d in enumerate(DIAS_SEMANA)
                        ],
                        width=130,
                    ),
                    ft.TextField(label="Desde", value=bloque.get("hora_inicio", "08:00"), width=90),
                    ft.TextField(label="Hasta", value=bloque.get("hora_fin", "12:00"), width=90),
                    ft.Dropdown(
                        label="Certeza",
                        value=certeza_actual,
                        options=[
                            ft.dropdown.Option(v["valor"], v["label"])
                            for v in CERTEZA_OPCIONES.values()
                        ],
                        width=170,
                    ),
                    ft.IconButton(
                        icon=ft.icons.DELETE_OUTLINE,
                        tooltip="Eliminar bloque",
                        icon_color=ft.colors.RED_400,
                        on_click=lambda e, bid=bloque.get("id"): self.eliminar_bloque(bid),
                    ),
                ],
                spacing=8,
                wrap=True,
            )
            filas.append(fila)

        return ft.Column(
            controls=[
                ft.Text("Disponibilidad Semanal", size=14, weight=ft.FontWeight.BOLD),
                *filas,
                ft.TextButton(
                    "+ Agregar bloque horario",
                    icon=ft.icons.ADD,
                    on_click=self.agregar_bloque,
                ),
            ],
            spacing=8,
        )

    def eliminar_bloque(self, bloque_id: str):
        if bloque_id:
            eliminar_disponibilidad(bloque_id)
            self.bloques = [b for b in self.bloques if b.get("id") != bloque_id]
            self.update()


class FormularioEspecialista(ft.UserControl):
    """Formulario para crear/editar un especialista."""

    def __init__(self, especialista: dict):
        super().__init__()
        self.especialista = especialista

    def build(self):
        e = self.especialista
        especialidades_seleccionadas = e.get("especialidades", []) or []

        checkboxes_especialidades = ft.ResponsiveRow(
            controls=[
                ft.Checkbox(
                    label=esp,
                    value=esp in especialidades_seleccionadas,
                    col={"sm": 6, "md": 4},
                )
                for esp in ESPECIALIDADES_DISPONIBLES
            ]
        )

        controles = [
            ft.Text("Datos del Especialista", size=14, weight=ft.FontWeight.BOLD),
            ft.ResponsiveRow(controls=[
                ft.TextField(label="Nombre", value=e.get("nombre", ""), col={"sm": 6}),
                ft.TextField(label="Apellido", value=e.get("apellido", ""), col={"sm": 6}),
                ft.TextField(label="Matrícula", value=e.get("matricula", ""), col={"sm": 6}),
                ft.TextField(label="Teléfono", value=e.get("telefono", ""), col={"sm": 6}),
                ft.TextField(label="Email", value=e.get("email", ""), col={"sm": 12}),
            ]),
            ft.Divider(),
            ft.Text("Especialidades", size=14, weight=ft.FontWeight.BOLD),
            checkboxes_especialidades,
            ft.ElevatedButton("Guardar Especialista", icon=ft.icons.SAVE),
        ]

        if e.get("id"):
            controles += [
                ft.Divider(),
                DisponibilidadEditor(e["id"]),
            ]

        return ft.Column(controls=controles, spacing=12, scroll=ft.ScrollMode.AUTO)


class EspecialistasView(ft.UserControl):
    """Vista principal del módulo de especialistas."""

    def build(self):
        self.lista_column = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO)
        self.detalle = ft.Column(expand=True, visible=False)
        self.cargar_lista()

        return ft.Row(
            controls=[
                ft.Container(
                    content=ft.Column(controls=[
                        ft.Text("Especialistas", size=18, weight=ft.FontWeight.BOLD),
                        ft.ElevatedButton("+ Nuevo", on_click=self.nuevo_especialista),
                        self.lista_column,
                    ], spacing=8),
                    width=260,
                    padding=8,
                ),
                ft.VerticalDivider(width=1),
                ft.Container(content=self.detalle, expand=True, padding=8),
            ],
            expand=True,
        )

    def cargar_lista(self):
        self.lista_column.controls.clear()
        especialistas = listar_especialistas()
        for esp in especialistas:
            especialidades = esp.get("especialidades") or []
            self.lista_column.controls.append(
                ft.ListTile(
                    title=ft.Text(f"Dr/a. {esp['apellido']}, {esp['nombre']}"),
                    subtitle=ft.Text(", ".join(especialidades[:2]) or "Sin especialidad"),
                    on_click=lambda e, s=esp: self.seleccionar(s),
                )
            )

    def seleccionar(self, especialista: dict):
        self.detalle.visible = True
        self.detalle.controls = [FormularioEspecialista(especialista)]
        self.update()

    def nuevo_especialista(self, e):
        self.seleccionar({})
