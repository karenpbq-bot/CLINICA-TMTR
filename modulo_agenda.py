"""
Módulo de Agenda: sistema de citas cruzando disponibilidad confirmada
de especialistas con pacientes.
"""

import flet as ft
from database import (
    listar_citas,
    crear_cita,
    actualizar_cita,
    cancelar_cita,
    listar_pacientes,
    listar_especialistas,
    listar_disponibilidad,
)

ESTADOS_CITA = ["pendiente", "confirmada", "realizada", "cancelada"]

ESTADO_COLOR = {
    "pendiente":   ft.colors.ORANGE_200,
    "confirmada":  ft.colors.BLUE_200,
    "realizada":   ft.colors.GREEN_200,
    "cancelada":   ft.colors.RED_200,
}


class FormularioCita(ft.UserControl):
    """Formulario para crear o editar una cita."""

    def __init__(self, cita: dict, on_guardar=None):
        super().__init__()
        self.cita = cita
        self.on_guardar = on_guardar
        self.especialista_seleccionado = None

    def build(self):
        pacientes = listar_pacientes()
        especialistas = listar_especialistas()

        self.dd_paciente = ft.Dropdown(
            label="Paciente",
            value=self.cita.get("paciente_id"),
            options=[
                ft.dropdown.Option(p["id"], f"{p['apellido']}, {p['nombre']}")
                for p in pacientes
            ],
        )

        self.dd_especialista = ft.Dropdown(
            label="Especialista",
            value=self.cita.get("especialista_id"),
            options=[
                ft.dropdown.Option(e["id"], f"Dr/a. {e['apellido']}, {e['nombre']}")
                for e in especialistas
            ],
            on_change=self.on_especialista_cambio,
        )

        self.disponibilidad_info = ft.Text(
            "Selecciona un especialista para ver su disponibilidad confirmada.",
            color=ft.colors.GREY_600,
            size=12,
        )

        self.tf_fecha = ft.TextField(
            label="Fecha y Hora (YYYY-MM-DD HH:MM)",
            value=self.cita.get("fecha_hora", ""),
        )

        self.dd_duracion = ft.Dropdown(
            label="Duración",
            value=str(self.cita.get("duracion_min", 30)),
            options=[
                ft.dropdown.Option("15", "15 min"),
                ft.dropdown.Option("30", "30 min"),
                ft.dropdown.Option("45", "45 min"),
                ft.dropdown.Option("60", "60 min"),
                ft.dropdown.Option("90", "90 min"),
            ],
        )

        self.dd_estado = ft.Dropdown(
            label="Estado",
            value=self.cita.get("estado", "pendiente"),
            options=[ft.dropdown.Option(s, s.capitalize()) for s in ESTADOS_CITA],
        )

        self.tf_motivo = ft.TextField(
            label="Motivo de la consulta",
            value=self.cita.get("motivo", ""),
            multiline=True,
            min_lines=2,
        )

        self.tf_notas = ft.TextField(
            label="Notas adicionales",
            value=self.cita.get("notas", ""),
            multiline=True,
            min_lines=2,
        )

        return ft.Column(
            controls=[
                ft.Text("Nueva Cita" if not self.cita.get("id") else "Editar Cita",
                        size=16, weight=ft.FontWeight.BOLD),
                self.dd_paciente,
                self.dd_especialista,
                self.disponibilidad_info,
                ft.Row(controls=[self.tf_fecha, self.dd_duracion], spacing=8),
                self.dd_estado,
                self.tf_motivo,
                self.tf_notas,
                ft.Row(
                    controls=[
                        ft.ElevatedButton("Guardar", icon=ft.icons.SAVE, on_click=self.guardar),
                        ft.OutlinedButton("Cancelar cita",
                                         icon=ft.icons.CANCEL,
                                         on_click=self.cancelar_cita,
                                         visible=bool(self.cita.get("id"))),
                    ],
                    spacing=8,
                ),
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
        )

    def on_especialista_cambio(self, e):
        esp_id = self.dd_especialista.value
        if not esp_id:
            return
        bloques_confirmados = [
            b for b in listar_disponibilidad(esp_id) if b.get("certeza") == "confirmado"
        ]
        if bloques_confirmados:
            dias_str = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
            resumen = "  |  ".join(
                f"{dias_str[b['dia_semana']]} {b['hora_inicio']}–{b['hora_fin']}"
                for b in bloques_confirmados
            )
            self.disponibilidad_info.value = f"🟢 Disponibilidad confirmada: {resumen}"
            self.disponibilidad_info.color = ft.colors.GREEN_700
        else:
            self.disponibilidad_info.value = "⚠️ Este especialista no tiene bloques confirmados."
            self.disponibilidad_info.color = ft.colors.ORANGE_700
        self.update()

    def guardar(self, e):
        datos = {
            "paciente_id": self.dd_paciente.value,
            "especialista_id": self.dd_especialista.value,
            "fecha_hora": self.tf_fecha.value,
            "duracion_min": int(self.dd_duracion.value),
            "estado": self.dd_estado.value,
            "motivo": self.tf_motivo.value,
            "notas": self.tf_notas.value,
        }
        if self.cita.get("id"):
            actualizar_cita(self.cita["id"], datos)
        else:
            crear_cita(datos)
        if self.on_guardar:
            self.on_guardar()

    def cancelar_cita(self, e):
        if self.cita.get("id"):
            cancelar_cita(self.cita["id"])
            if self.on_guardar:
                self.on_guardar()


class AgendaView(ft.UserControl):
    """Vista principal de la agenda de citas."""

    def build(self):
        self.lista_column = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, expand=True)
        self.detalle = ft.Column(expand=True, visible=False)
        self.cargar_lista()

        return ft.Row(
            controls=[
                ft.Container(
                    content=ft.Column(controls=[
                        ft.Text("Agenda", size=18, weight=ft.FontWeight.BOLD),
                        ft.ElevatedButton("+ Nueva Cita", on_click=self.nueva_cita),
                        self.lista_column,
                    ], spacing=8, expand=True),
                    width=320,
                    padding=8,
                ),
                ft.VerticalDivider(width=1),
                ft.Container(content=self.detalle, expand=True, padding=8),
            ],
            expand=True,
        )

    def cargar_lista(self):
        self.lista_column.controls.clear()
        citas = listar_citas()
        for c in citas:
            paciente = c.get("pacientes") or {}
            especialista = c.get("especialistas") or {}
            estado = c.get("estado", "pendiente")
            self.lista_column.controls.append(
                ft.Container(
                    content=ft.ListTile(
                        title=ft.Text(
                            f"{paciente.get('apellido', '')}, {paciente.get('nombre', '')}"
                        ),
                        subtitle=ft.Text(
                            f"{c.get('fecha_hora', '')} · Dr/a. {especialista.get('apellido', '')}"
                        ),
                        trailing=ft.Text(estado.capitalize(),
                                         color=ft.colors.BLACK87, size=11),
                        on_click=lambda e, cita=c: self.seleccionar_cita(cita),
                    ),
                    bgcolor=ESTADO_COLOR.get(estado, ft.colors.GREY_100),
                    border_radius=6,
                )
            )

    def seleccionar_cita(self, cita: dict):
        self.detalle.visible = True
        self.detalle.controls = [
            FormularioCita(cita, on_guardar=self.refrescar)
        ]
        self.update()

    def nueva_cita(self, e):
        self.seleccionar_cita({})

    def refrescar(self):
        self.cargar_lista()
        self.detalle.visible = False
        self.update()
