"""
Módulo de Agenda: citas cruzando disponibilidad confirmada de especialistas.
"""

import flet as ft
from database import (
    listar_citas, crear_cita, actualizar_cita, cancelar_cita,
    listar_pacientes, listar_especialistas, listar_disponibilidad,
)

ESTADOS_CITA = ["pendiente", "confirmada", "realizada", "cancelada"]
ESTADO_COLOR = {
    "pendiente":  "#FFE0B2",
    "confirmada": "#BBDEFB",
    "realizada":  "#C8E6C9",
    "cancelada":  "#FFCDD2",
}
DIAS_CORTOS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


class FormularioCita(ft.Column):
    def __init__(self, cita: dict, on_guardar=None, snack_fn=None):
        super().__init__(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
        self.cita = cita
        self.on_guardar = on_guardar
        self.snack_fn = snack_fn
        self._construir()

    def _construir(self):
        pacientes = listar_pacientes()
        especialistas = listar_especialistas()

        self.dd_paciente = ft.Dropdown(
            label="Paciente",
            value=self.cita.get("paciente_id"),
            options=[ft.dropdown.Option(p["id"], f"{p.get('apellido','')}, {p.get('nombre','')}")
                     for p in pacientes],
        )
        self.dd_especialista = ft.Dropdown(
            label="Especialista",
            value=self.cita.get("especialista_id"),
            options=[ft.dropdown.Option(e["id"],
                     f"Dr/a. {e.get('apellido','')}, {e.get('nombre','')}")
                     for e in especialistas],
            on_change=self._on_especialista,
        )
        self.info_disp = ft.Text(
            "Seleccioná un especialista para ver su disponibilidad confirmada.",
            color="#757575", size=12,
        )
        self.tf_fecha    = ft.TextField(label="Fecha y Hora (YYYY-MM-DD HH:MM)",
                                        value=self.cita.get("fecha_hora", ""), expand=True)
        self.dd_duracion = ft.Dropdown(
            label="Duración", value=str(self.cita.get("duracion_min", 30)),
            options=[ft.dropdown.Option(str(m), f"{m} min")
                     for m in [15, 30, 45, 60, 90]],
            width=160,
        )
        self.dd_estado = ft.Dropdown(
            label="Estado", value=self.cita.get("estado", "pendiente"),
            options=[ft.dropdown.Option(s, s.capitalize()) for s in ESTADOS_CITA],
        )
        self.tf_motivo = ft.TextField(label="Motivo", value=self.cita.get("motivo", ""),
                                      multiline=True, min_lines=2)
        self.tf_notas  = ft.TextField(label="Notas adicionales",
                                      value=self.cita.get("notas", ""),
                                      multiline=True, min_lines=2)

        self.controls = [
            ft.Text("Nueva Cita" if not self.cita.get("id") else "Editar Cita",
                    size=16, weight=ft.FontWeight.BOLD),
            self.dd_paciente,
            self.dd_especialista,
            self.info_disp,
            ft.Row(controls=[self.tf_fecha, self.dd_duracion], spacing=8),
            self.dd_estado,
            self.tf_motivo,
            self.tf_notas,
            ft.Row(controls=[
                ft.FilledButton("Guardar", icon=ft.Icons.SAVE, on_click=self._guardar),
                ft.OutlinedButton("Cancelar cita", icon=ft.Icons.CANCEL,
                                  on_click=self._cancelar,
                                  visible=bool(self.cita.get("id"))),
            ], spacing=8),
        ]

    def _on_especialista(self, e):
        eid = self.dd_especialista.value
        if not eid:
            return
        try:
            bloques = [b for b in listar_disponibilidad(eid)
                       if b.get("certeza") == "confirmado"]
            if bloques:
                resumen = "  |  ".join(
                    f"{DIAS_CORTOS[b['dia_semana']]} {b['hora_inicio']}–{b['hora_fin']}"
                    for b in bloques
                )
                self.info_disp.value = f"🟢 Disponibilidad confirmada: {resumen}"
                self.info_disp.color = "#2E7D32"
            else:
                self.info_disp.value = "⚠️ Sin bloques confirmados para este especialista."
                self.info_disp.color = "#E65100"
            self.info_disp.update()
        except Exception as ex:
            if self.snack_fn:
                self.snack_fn(f"Error: {ex}", error=True)

    def _guardar(self, e):
        datos = {
            "paciente_id":     self.dd_paciente.value,
            "especialista_id": self.dd_especialista.value,
            "fecha_hora":      self.tf_fecha.value,
            "duracion_min":    int(self.dd_duracion.value or 30),
            "estado":          self.dd_estado.value,
            "motivo":          self.tf_motivo.value,
            "notas":           self.tf_notas.value,
        }
        try:
            if self.cita.get("id"):
                actualizar_cita(self.cita["id"], datos)
            else:
                crear_cita(datos)
            if self.snack_fn:
                self.snack_fn("Cita guardada correctamente.")
            if self.on_guardar:
                self.on_guardar()
        except Exception as ex:
            if self.snack_fn:
                self.snack_fn(f"Error: {ex}", error=True)

    def _cancelar(self, e):
        try:
            cancelar_cita(self.cita["id"])
            if self.snack_fn:
                self.snack_fn("Cita cancelada.")
            if self.on_guardar:
                self.on_guardar()
        except Exception as ex:
            if self.snack_fn:
                self.snack_fn(f"Error: {ex}", error=True)


class AgendaView(ft.Row):
    def __init__(self):
        super().__init__(expand=True, spacing=0)
        self._lista_col   = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, expand=True)
        self._detalle_col = ft.Column(expand=True, visible=False, spacing=8)

        panel_izq = ft.Container(
            content=ft.Column(controls=[
                ft.Text("Agenda de Citas", size=16, weight=ft.FontWeight.BOLD),
                ft.FilledButton("+ Nueva Cita", icon=ft.Icons.ADD,
                                  on_click=lambda e: self._seleccionar({})),
                ft.Divider(height=4),
                self._lista_col,
            ], spacing=8, expand=True),
            width=320, padding=12,
            border=ft.border.only(right=ft.BorderSide(1, "#E0E0E0")),
        )
        panel_der = ft.Container(content=self._detalle_col, expand=True, padding=12)
        self.controls = [panel_izq, panel_der]

    def did_mount(self):
        self._cargar()

    def _snack(self, msg, error=False):
        if self.page:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(msg),
                bgcolor=ft.Colors.RED_700 if error else ft.Colors.GREEN_700,
                open=True,
            )
            self.page.update()

    def _cargar(self):
        try:
            citas = listar_citas()
        except Exception as ex:
            self._snack(f"Error: {ex}", error=True)
            citas = []
        self._lista_col.controls.clear()
        for c in citas:
            pac = c.get("pacientes") or {}
            esp = c.get("especialistas") or {}
            estado = c.get("estado", "pendiente")
            self._lista_col.controls.append(
                ft.Container(
                    content=ft.ListTile(
                        title=ft.Text(
                            f"{pac.get('apellido','')}, {pac.get('nombre','')}",
                            size=13,
                        ),
                        subtitle=ft.Text(
                            f"{str(c.get('fecha_hora',''))[:16]} · Dr/a. {esp.get('apellido','')}",
                            size=11,
                        ),
                        trailing=ft.Text(estado.capitalize(), size=11),
                        on_click=lambda e, cita=c: self._seleccionar(cita),
                        content_padding=ft.padding.symmetric(horizontal=8),
                    ),
                    bgcolor=ESTADO_COLOR.get(estado, "#F5F5F5"),
                    border_radius=6,
                )
            )
        if self._lista_col.page:
            self._lista_col.update()

    def _seleccionar(self, cita: dict):
        self._detalle_col.visible = True
        self._detalle_col.controls = [
            FormularioCita(cita, on_guardar=self._refrescar, snack_fn=self._snack)
        ]
        if self._detalle_col.page:
            self._detalle_col.update()

    def _refrescar(self):
        self._cargar()
        self._detalle_col.visible = False
        if self._detalle_col.page:
            self._detalle_col.update()
