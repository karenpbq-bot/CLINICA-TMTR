"""
Módulo de Agenda: citas cruzando disponibilidad confirmada de especialistas.
Flet 0.84: Dropdown.on_select en lugar de on_change, show_dialog/pop_dialog.
"""

import flet as ft
from database import (
    listar_citas, crear_cita, actualizar_cita, cancelar_cita, eliminar_cita,
    listar_pacientes, listar_especialistas, listar_disponibilidad,
)

ESTADOS_CITA = ["pendiente", "confirmada", "realizada", "cancelada"]
ESTADO_COLOR = {
    "pendiente":  "#FFE0B2",
    "confirmada": "#BBDEFB",
    "realizada":  "#C8E6C9",
    "cancelada":  "#FFCDD2",
}
ESTADO_ICON = {
    "pendiente":  ft.Icons.HOURGLASS_EMPTY,
    "confirmada": ft.Icons.CHECK_CIRCLE_OUTLINE,
    "realizada":  ft.Icons.CHECK_CIRCLE,
    "cancelada":  ft.Icons.CANCEL,
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
        try:
            pacientes    = listar_pacientes()
            especialistas = listar_especialistas()
        except Exception:
            pacientes, especialistas = [], []

        self.dd_paciente = ft.Dropdown(
            label="Paciente *",
            value=self.cita.get("paciente_id"),
            options=[
                ft.dropdown.Option(p["id"], f"{p.get('apellido','')}, {p.get('nombre','')}")
                for p in pacientes
            ],
            expand=True,
        )
        self.info_disp = ft.Text(
            "Seleccioná un especialista para ver su disponibilidad confirmada.",
            color="#757575", size=12,
        )
        self.dd_especialista = ft.Dropdown(
            label="Especialista",
            value=self.cita.get("especialista_id"),
            options=[
                ft.dropdown.Option(
                    e["id"],
                    f"Dr/a. {e.get('apellido','')}, {e.get('nombre','')}",
                )
                for e in especialistas
            ],
            expand=True,
            on_select=self._on_especialista,
        )
        # Descomponer fecha_hora existente (formato ISO: YYYY-MM-DD HH:MM)
        _fh = str(self.cita.get("fecha_hora", ""))
        _fecha_iso  = _fh[:10]   # YYYY-MM-DD
        _hora_val   = _fh[11:16] if len(_fh) >= 16 else ""

        # Convertir fecha ISO a DD/MM/YYYY para mostrar al usuario
        _fecha_display = ""
        if len(_fecha_iso) == 10:
            try:
                a, m, d = _fecha_iso.split("-")
                _fecha_display = f"{d}/{m}/{a}"
            except Exception:
                pass

        self.tf_fecha = ft.TextField(
            label="Fecha  (DD/MM/YYYY) *",
            value=_fecha_display,
            hint_text="ej. 25/07/2025",
            expand=True,
            keyboard_type=ft.KeyboardType.DATETIME,
        )
        self.tf_hora = ft.TextField(
            label="Hora  (HH:MM) *",
            value=_hora_val,
            hint_text="ej. 09:30",
            width=130,
            keyboard_type=ft.KeyboardType.DATETIME,
        )
        self.dd_duracion = ft.Dropdown(
            label="Duración",
            value=str(self.cita.get("duracion_min", 30)),
            options=[ft.dropdown.Option(str(m), f"{m} min") for m in [15, 30, 45, 60, 90]],
            width=150,
        )
        self.dd_estado = ft.Dropdown(
            label="Estado",
            value=self.cita.get("estado", "pendiente"),
            options=[ft.dropdown.Option(s, s.capitalize()) for s in ESTADOS_CITA],
            width=180,
        )
        self.tf_motivo = ft.TextField(
            label="Motivo de la consulta",
            value=self.cita.get("motivo", ""),
            multiline=True, min_lines=2,
        )
        self.tf_notas = ft.TextField(
            label="Notas adicionales",
            value=self.cita.get("notas", ""),
            multiline=True, min_lines=2,
        )

        if self.cita.get("especialista_id"):
            self._cargar_disponibilidad(self.cita["especialista_id"])

        self.controls = [
            ft.Text(
                "Nueva Cita" if not self.cita.get("id") else "Editar Cita",
                size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900,
            ),
            ft.Row(controls=[self.dd_paciente, self.dd_especialista], spacing=8),
            self.info_disp,
            ft.Row(controls=[self.tf_fecha, self.tf_hora, self.dd_duracion], spacing=8),
            ft.Row(controls=[self.dd_estado], spacing=8),
            self.tf_motivo,
            self.tf_notas,
            ft.Row(controls=[
                ft.FilledButton("Guardar cita", icon=ft.Icons.SAVE, on_click=self._guardar),
                ft.OutlinedButton(
                    "Cancelar cita", icon=ft.Icons.CANCEL,
                    on_click=self._cancelar,
                    visible=bool(self.cita.get("id") and self.cita.get("estado") != "cancelada"),
                ),
            ], spacing=8),
        ]

    def _cargar_disponibilidad(self, eid: str):
        try:
            bloques = [b for b in listar_disponibilidad(eid) if b.get("certeza") == "confirmado"]
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
        except Exception:
            pass

    def _on_especialista(self, e):
        eid = self.dd_especialista.value
        if not eid:
            return
        self._cargar_disponibilidad(eid)
        self.info_disp.update()

    @staticmethod
    def _parsear_fecha_hora(fecha_str: str, hora_str: str) -> str:
        """
        Convierte DD/MM/YYYY + HH:MM  →  YYYY-MM-DD HH:MM
        Lanza ValueError si el formato no es válido.
        """
        fecha_str = fecha_str.strip()
        hora_str  = hora_str.strip()
        if not fecha_str:
            raise ValueError("Ingresá la fecha.")
        if not hora_str:
            raise ValueError("Ingresá la hora.")
        partes = fecha_str.replace("-", "/").split("/")
        if len(partes) != 3:
            raise ValueError("Fecha inválida. Usá el formato DD/MM/YYYY.")
        d, m, a = partes
        if len(a) != 4 or not (a.isdigit() and m.isdigit() and d.isdigit()):
            raise ValueError("Fecha inválida. Usá el formato DD/MM/YYYY.")
        if ":" not in hora_str or len(hora_str) < 4:
            raise ValueError("Hora inválida. Usá el formato HH:MM.")
        return f"{a}-{m.zfill(2)}-{d.zfill(2)} {hora_str}"

    def _guardar(self, e):
        if not self.dd_paciente.value:
            if self.snack_fn:
                self.snack_fn("Seleccioná un paciente.", error=True)
            return
        try:
            fecha_hora_iso = self._parsear_fecha_hora(
                self.tf_fecha.value or "", self.tf_hora.value or ""
            )
        except ValueError as err:
            if self.snack_fn:
                self.snack_fn(str(err), error=True)
            return
        datos = {
            "paciente_id":     self.dd_paciente.value,
            "especialista_id": self.dd_especialista.value,
            "fecha_hora":      fecha_hora_iso,
            "duracion_min":    int(self.dd_duracion.value or 30),
            "estado":          self.dd_estado.value or "pendiente",
            "motivo":          self.tf_motivo.value.strip(),
            "notas":           self.tf_notas.value.strip(),
        }
        try:
            if self.cita.get("id"):
                actualizar_cita(self.cita["id"], datos)
                if self.snack_fn:
                    self.snack_fn("Cita actualizada correctamente.")
            else:
                crear_cita(datos)
                if self.snack_fn:
                    self.snack_fn("Cita creada correctamente.")
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
        self._todas_citas: list[dict] = []
        self._filtro_estado = "todas"

        self._lista_col   = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, expand=True)
        self._detalle_col = ft.Column(expand=True, visible=False, spacing=8)

        self._dd_filtro = ft.Dropdown(
            label="Filtrar por estado",
            value="todas",
            options=[
                ft.dropdown.Option("todas", "Todas"),
                *[ft.dropdown.Option(s, s.capitalize()) for s in ESTADOS_CITA],
            ],
            width=200,
            on_select=self._aplicar_filtro,
        )

        panel_izq = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Agenda de Citas", size=16, weight=ft.FontWeight.BOLD),
                    ft.FilledButton("+ Nueva Cita", icon=ft.Icons.ADD,
                                   on_click=lambda e: self._seleccionar({})),
                    self._dd_filtro,
                    ft.Divider(height=4),
                    self._lista_col,
                ],
                spacing=8, expand=True,
            ),
            width=340, padding=12,
            border=ft.border.only(right=ft.BorderSide(1, "#E0E0E0")),
        )
        panel_der = ft.Container(
            content=self._detalle_col, expand=True, padding=16,
        )
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
            self._todas_citas = listar_citas()
        except Exception as ex:
            self._snack(f"Error cargando citas: {ex}", error=True)
            self._todas_citas = []
        self._renderizar_lista()

    def _aplicar_filtro(self, e):
        self._filtro_estado = self._dd_filtro.value or "todas"
        self._renderizar_lista()

    def _renderizar_lista(self):
        filtradas = (
            self._todas_citas if self._filtro_estado == "todas"
            else [c for c in self._todas_citas if c.get("estado") == self._filtro_estado]
        )
        self._lista_col.controls.clear()
        if not filtradas:
            self._lista_col.controls.append(
                ft.Text("Sin citas para el filtro seleccionado.", color="#9E9E9E", size=12)
            )
        for c in filtradas:
            pac   = c.get("pacientes") or {}
            esp   = c.get("especialistas") or {}
            estado = c.get("estado", "pendiente")
            self._lista_col.controls.append(
                ft.Container(
                    content=ft.ListTile(
                        leading=ft.Icon(
                            ESTADO_ICON.get(estado, ft.Icons.EVENT),
                            color="#424242", size=20,
                        ),
                        title=ft.Text(
                            f"{pac.get('apellido','?')}, {pac.get('nombre','?')}",
                            size=13,
                        ),
                        subtitle=ft.Text(
                            f"{str(c.get('fecha_hora',''))[:16]}  ·  "
                            f"Dr/a. {esp.get('apellido','–')}",
                            size=11,
                        ),
                        trailing=ft.Text(estado.capitalize(), size=11,
                                         weight=ft.FontWeight.W_500),
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
            FormularioCita(
                cita,
                on_guardar=self._refrescar,
                snack_fn=self._snack,
            )
        ]
        if self._detalle_col.page:
            self._detalle_col.update()

    def _refrescar(self):
        self._cargar()
        self._detalle_col.visible = False
        if self._detalle_col.page:
            self._detalle_col.update()
