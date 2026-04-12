"""
Módulo de Tratamientos: presupuestos detallados por diente y cara tratada.
"""

import flet as ft
from database import (
    listar_tratamientos,
    crear_tratamiento,
    actualizar_tratamiento,
    listar_pacientes,
    listar_especialistas,
)

CARAS_DIENTE = ["Oclusal", "Vestibular", "Lingual/Palatino", "Mesial", "Distal"]

ESTADOS_TRATAMIENTO = {
    "presupuestado": "Presupuestado",
    "aprobado":      "Aprobado",
    "realizado":     "Realizado",
}

TIPOS_TRATAMIENTO = [
    "Consulta / Revisión",
    "Limpieza / Profilaxis",
    "Obturación (Resina)",
    "Obturación (Amalgama)",
    "Endodoncia",
    "Extracción Simple",
    "Extracción Quirúrgica",
    "Corona Porcelana",
    "Corona Metal-Porcelana",
    "Implante Dental",
    "Carilla Porcelana",
    "Ortodoncia – Cuota mensual",
    "Blanqueamiento",
    "Placa Miorelajante",
    "Radiografía Periapical",
    "Radiografía Panorámica",
    "Otro",
]


class ItemTratamiento(ft.UserControl):
    """Fila de un ítem de presupuesto."""

    def __init__(self, tratamiento: dict, on_actualizar=None):
        super().__init__()
        self.tratamiento = tratamiento
        self.on_actualizar = on_actualizar

    def build(self):
        t = self.tratamiento
        estado = t.get("estado", "presupuestado")
        colores_estado = {
            "presupuestado": ft.colors.ORANGE_100,
            "aprobado":      ft.colors.BLUE_100,
            "realizado":     ft.colors.GREEN_100,
        }

        return ft.Container(
            content=ft.ResponsiveRow(
                controls=[
                    ft.Text(
                        f"Diente {t.get('diente', '–')} · {t.get('cara', '–')}",
                        col={"sm": 3},
                        size=12,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Text(t.get("descripcion", ""), col={"sm": 5}, size=12),
                    ft.Text(f"$ {float(t.get('costo', 0)):.2f}", col={"sm": 2}, size=12),
                    ft.Text(
                        ESTADOS_TRATAMIENTO.get(estado, estado),
                        col={"sm": 2},
                        size=11,
                        color=ft.colors.BLACK87,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=ft.padding.symmetric(vertical=6, horizontal=10),
            bgcolor=colores_estado.get(estado, ft.colors.GREY_100),
            border_radius=6,
            on_click=lambda e: self.on_actualizar(self.tratamiento) if self.on_actualizar else None,
        )


class FormularioTratamiento(ft.UserControl):
    """Formulario para agregar/editar un ítem de presupuesto."""

    def __init__(self, paciente_id: str, tratamiento: dict = None, on_guardar=None):
        super().__init__()
        self.paciente_id = paciente_id
        self.tratamiento = tratamiento or {}
        self.on_guardar = on_guardar

    def build(self):
        t = self.tratamiento
        especialistas = listar_especialistas()

        # Opciones de dientes FDI
        dientes_opciones = [
            ft.dropdown.Option(str(d), str(d))
            for d in (
                list(range(11, 19)) + list(range(21, 29)) +
                list(range(31, 39)) + list(range(41, 49))
            )
        ]

        return ft.Column(
            controls=[
                ft.Text(
                    "Agregar Ítem" if not t.get("id") else "Editar Ítem",
                    size=14, weight=ft.FontWeight.BOLD,
                ),
                ft.ResponsiveRow(controls=[
                    ft.Dropdown(
                        label="Diente (FDI)",
                        value=str(t.get("diente", "")) if t.get("diente") else None,
                        options=dientes_opciones,
                        col={"sm": 4},
                    ),
                    ft.Dropdown(
                        label="Cara",
                        value=t.get("cara"),
                        options=[ft.dropdown.Option(c) for c in CARAS_DIENTE],
                        col={"sm": 4},
                    ),
                    ft.Dropdown(
                        label="Especialista",
                        value=t.get("especialista_id"),
                        options=[
                            ft.dropdown.Option(e["id"], f"Dr/a. {e['apellido']}")
                            for e in especialistas
                        ],
                        col={"sm": 4},
                    ),
                    ft.Dropdown(
                        label="Tratamiento",
                        value=t.get("descripcion"),
                        options=[ft.dropdown.Option(tp) for tp in TIPOS_TRATAMIENTO],
                        col={"sm": 8},
                    ),
                    ft.TextField(
                        label="Costo ($)",
                        value=str(t.get("costo", "0")),
                        keyboard_type=ft.KeyboardType.NUMBER,
                        col={"sm": 4},
                    ),
                    ft.Dropdown(
                        label="Estado",
                        value=t.get("estado", "presupuestado"),
                        options=[
                            ft.dropdown.Option(k, v) for k, v in ESTADOS_TRATAMIENTO.items()
                        ],
                        col={"sm": 6},
                    ),
                ]),
                ft.ElevatedButton("Guardar Ítem", icon=ft.icons.SAVE, on_click=self.guardar),
            ],
            spacing=10,
        )

    def guardar(self, e):
        # TODO: recolectar valores de los campos y llamar crear_tratamiento / actualizar_tratamiento
        if self.on_guardar:
            self.on_guardar()


class TratamientosView(ft.UserControl):
    """Vista principal del módulo de tratamientos / presupuestos."""

    def __init__(self, paciente_id: str = None):
        super().__init__()
        self.paciente_id = paciente_id
        self.mostrar_formulario = False

    def build(self):
        if not self.paciente_id:
            return ft.Column(
                controls=[
                    ft.Text("Módulo de Tratamientos", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        "Selecciona un paciente desde el módulo de Pacientes para ver y gestionar "
                        "su presupuesto de tratamientos.",
                        color=ft.colors.GREY_600,
                    ),
                    self._selector_paciente(),
                ],
                spacing=16,
                padding=16,
            )

        return self._vista_paciente()

    def _selector_paciente(self):
        pacientes = listar_pacientes()
        return ft.Dropdown(
            label="Seleccionar paciente",
            options=[
                ft.dropdown.Option(p["id"], f"{p['apellido']}, {p['nombre']}")
                for p in pacientes
            ],
            on_change=lambda e: self._cambiar_paciente(e.control.value),
            width=320,
        )

    def _cambiar_paciente(self, paciente_id: str):
        self.paciente_id = paciente_id
        self.update()

    def _vista_paciente(self):
        tratamientos = listar_tratamientos(self.paciente_id)
        total = sum(float(t.get("costo", 0)) for t in tratamientos)

        items = [ItemTratamiento(t) for t in tratamientos]

        return ft.Column(
            controls=[
                ft.Text("Presupuesto de Tratamientos", size=18, weight=ft.FontWeight.BOLD),
                ft.Row(
                    controls=[
                        ft.Text(f"Total: $ {total:.2f}", size=14, weight=ft.FontWeight.W_600),
                        ft.ElevatedButton(
                            "+ Agregar ítem",
                            icon=ft.icons.ADD,
                            on_click=lambda e: self.toggle_formulario(),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                FormularioTratamiento(self.paciente_id, on_guardar=self.refrescar)
                if self.mostrar_formulario else ft.Container(),
                ft.Divider(),
                ft.Column(controls=items if items else [
                    ft.Text("Sin tratamientos registrados.", color=ft.colors.GREY_500)
                ], spacing=6),
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def toggle_formulario(self):
        self.mostrar_formulario = not self.mostrar_formulario
        self.update()

    def refrescar(self):
        self.mostrar_formulario = False
        self.update()
