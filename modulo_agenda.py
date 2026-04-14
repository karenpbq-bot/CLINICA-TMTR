"""
Módulo de Agenda: citas cruzando disponibilidad confirmada de especialistas.
Flet 0.84: Dropdown.on_select, show_dialog/pop_dialog.
FormularioCita incluye calendario interactivo del especialista seleccionado.
"""

import calendar as _cal_mod
from datetime import date, timedelta, datetime

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
MESES_ES    = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]

H_INI_CAL  = 7
H_FIN_CAL  = 20
ALTO_CELDA = 18
ANCHO_HORA = 42

COLOR_DISP   = "#FFF9C4"   # amarillo claro – disponibilidad
COLOR_CITA   = "#FFB74D"   # naranja – cita ya programada
COLOR_SEL    = "#90CAF9"   # azul claro – celda seleccionada
COLOR_HOY    = "#E3F2FD"   # azul muy suave – día actual
COLOR_BORDER = "#E0E0E0"


# ── Calendario Interactivo ──────────────────────────────────────────────────

class CalendarioPicker(ft.Column):
    """
    Calendario semanal o de 2 semanas interactivo:
    - Amarillo  = bloque de disponibilidad configurado
    - Naranja   = cita ya agendada
    - Azul      = celda seleccionada por el usuario
    Al hacer clic sobre una celda se invoca on_pick(fecha: date, hora: int).
    """

    def __init__(self, on_pick=None):
        super().__init__(expand=True, spacing=4)
        self.on_pick        = on_pick
        self._especialista_id: str | None = None
        self._disp:  list[dict] = []
        self._citas: list[dict] = []
        self._vista  = "semana"          # "semana" | "2semanas"
        self._inicio = self._lunes_hoy()
        self._sel: tuple[date, int] | None = None  # (fecha, hora) seleccionados

        # ── controles de navegación ──────────────────────────────────────
        self._lbl_periodo = ft.Text("", size=12, weight=ft.FontWeight.W_600,
                                    color="#1565C0")
        btn_prev = ft.IconButton(ft.Icons.CHEVRON_LEFT,  icon_size=18,
                                 on_click=lambda e: self._navegar(-1),
                                 style=ft.ButtonStyle(padding=4))
        btn_next = ft.IconButton(ft.Icons.CHEVRON_RIGHT, icon_size=18,
                                 on_click=lambda e: self._navegar(1),
                                 style=ft.ButtonStyle(padding=4))
        self._btn_semana   = ft.TextButton("1 sem",  on_click=lambda e: self._cambiar_vista("semana"))
        self._btn_2semanas = ft.TextButton("2 sem",  on_click=lambda e: self._cambiar_vista("2semanas"))
        self._actualizar_btns_vista()

        nav_row = ft.Row(
            controls=[
                btn_prev, self._lbl_periodo, btn_next,
                ft.Container(expand=True),
                self._btn_semana, self._btn_2semanas,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=2,
        )

        # ── leyenda ──────────────────────────────────────────────────────
        def chip(label, color):
            return ft.Row([
                ft.Container(width=10, height=10, bgcolor=color,
                             border_radius=2),
                ft.Text(label, size=10, color="#616161"),
            ], spacing=4, tight=True)

        leyenda = ft.Row([
            chip("Disponible", COLOR_DISP),
            chip("Ocupado",    COLOR_CITA),
            chip("Seleccionado", COLOR_SEL),
        ], spacing=12)

        self._grid_wrap = ft.Container(expand=True)
        self.controls   = [nav_row, leyenda, ft.Divider(height=4), self._grid_wrap]

    # ── helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _lunes_hoy() -> date:
        hoy = date.today()
        return hoy - timedelta(days=hoy.weekday())

    @staticmethod
    def _parsear_fh(fh) -> datetime | None:
        s = str(fh)[:16].replace("T", " ")
        try:
            return datetime.strptime(s, "%Y-%m-%d %H:%M")
        except Exception:
            return None

    def _actualizar_btns_vista(self):
        bold  = ft.FontWeight.BOLD
        norm  = ft.FontWeight.NORMAL
        azul  = ft.Colors.BLUE_900
        gris  = ft.Colors.BLACK54
        self._btn_semana.style   = ft.ButtonStyle(color=azul if self._vista == "semana"   else gris)
        self._btn_2semanas.style = ft.ButtonStyle(color=azul if self._vista == "2semanas" else gris)

    def _cambiar_vista(self, v: str):
        self._vista  = v
        self._inicio = self._lunes_hoy()
        self._actualizar_btns_vista()
        self._renderizar()
        if self.page:
            self.update()

    def _navegar(self, d: int):
        semanas = 1 if self._vista == "semana" else 2
        self._inicio += timedelta(weeks=semanas * d)
        self._renderizar()
        if self.page:
            self.update()

    def _rango_fechas(self) -> tuple[date, date]:
        semanas = 1 if self._vista == "semana" else 2
        return self._inicio, self._inicio + timedelta(weeks=semanas)

    # ── datos ────────────────────────────────────────────────────────────

    def cargar_especialista(self, especialista_id: str | None):
        self._especialista_id = especialista_id
        self._sel = None
        if especialista_id:
            try:
                self._disp = listar_disponibilidad(especialista_id)
            except Exception:
                self._disp = []
            try:
                todas = listar_citas({"especialista_id": especialista_id})
                self._citas = [c for c in todas if c.get("estado") != "cancelada"]
            except Exception:
                self._citas = []
        else:
            self._disp  = []
            self._citas = []
        self._renderizar()
        if self.page:
            self.update()

    # ── color de celda ───────────────────────────────────────────────────

    def _color_celda(self, dia: date, hora: int) -> str:
        if self._sel and self._sel == (dia, hora):
            return COLOR_SEL
        # cita ya agendada (naranja)
        for c in self._citas:
            cdt = self._parsear_fh(c.get("fecha_hora", ""))
            if cdt is None:
                continue
            try:
                dur    = int(c.get("duracion_min", 30))
                h_fin  = cdt.hour + (cdt.minute + dur + 59) // 60
                if cdt.date() == dia and cdt.hour <= hora < max(cdt.hour + 1, h_fin):
                    return COLOR_CITA
            except Exception:
                pass
        # disponibilidad (amarillo)
        dia_sem = dia.weekday()
        for b in self._disp:
            if b.get("dia_semana") == dia_sem:
                try:
                    h_ini_b = int(str(b.get("hora_inicio", "00:00"))[:2])
                    h_fin_b = int(str(b.get("hora_fin",   "00:00"))[:2])
                    if h_ini_b <= hora < h_fin_b:
                        return COLOR_DISP
                except Exception:
                    pass
        return "#FFFFFF"

    # ── renderizado ──────────────────────────────────────────────────────

    def _renderizar(self):
        desde, hasta = self._rango_fechas()
        hasta_inc = hasta - timedelta(days=1)
        self._lbl_periodo.value = (
            f"{desde.day} {MESES_ES[desde.month-1]} – "
            f"{hasta_inc.day} {MESES_ES[hasta_inc.month-1]} {hasta_inc.year}"
        )
        dias = [(desde + timedelta(days=i)) for i in range((hasta - desde).days)]
        self._grid_wrap.content = self._grilla(dias)

    def _grilla(self, dias: list[date]) -> ft.Control:
        hoy = date.today()

        # ── cabecera ──────────────────────────────────────────────────
        cab_hora = ft.Container(width=ANCHO_HORA, height=28)
        celdas_cab = [
            ft.Container(
                content=ft.Column([
                    ft.Text(DIAS_CORTOS[d.weekday()], size=8, color="#757575"),
                    ft.Text(str(d.day), size=12, weight=ft.FontWeight.W_600,
                            color="#1565C0" if d == hoy else "#212121"),
                ], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                expand=True, height=28,
                bgcolor=COLOR_HOY if d == hoy else "#FAFAFA",
                alignment=ft.Alignment(0, 0),
                border=ft.border.only(
                    left=ft.BorderSide(1, COLOR_BORDER),
                    bottom=ft.BorderSide(2, "#BDBDBD"),
                ),
            )
            for d in dias
        ]
        header = ft.Row(controls=[cab_hora] + celdas_cab, spacing=0)

        # ── filas horarias ─────────────────────────────────────────────
        filas = []
        for hora in range(H_INI_CAL, H_FIN_CAL):
            etiq = ft.Container(
                content=ft.Text(f"{hora:02d}:00", size=9, color="#9E9E9E"),
                width=ANCHO_HORA, height=ALTO_CELDA,
                alignment=ft.Alignment(1, -1),
                padding=ft.padding.only(right=4, top=2),
            )
            celdas = []
            for d in dias:
                color = self._color_celda(d, hora)
                celda = ft.Container(
                    expand=True, height=ALTO_CELDA,
                    bgcolor=color,
                    border=ft.border.all(0.5, COLOR_BORDER),
                    tooltip=f"{DIAS_CORTOS[d.weekday()]} {d.day}/{d.month}  {hora:02d}:00",
                    on_click=self._make_click(d, hora),
                )
                celdas.append(celda)
            filas.append(ft.Row(controls=[etiq] + celdas, spacing=0))

        return ft.Column(
            controls=[
                header,
                ft.Column(controls=filas, spacing=0),
            ],
            spacing=0,
        )

    def _make_click(self, dia: date, hora: int):
        def handler(e):
            self._sel = (dia, hora)
            self._renderizar()
            if self.page:
                self.update()
            if self.on_pick:
                self.on_pick(dia, hora)
        return handler


# ── Formulario de Cita ──────────────────────────────────────────────────────

class FormularioCita(ft.Row):
    """
    Layout de dos columnas:
    - Izquierda: formulario compacto
    - Derecha:   calendario interactivo del especialista (clic → llena fecha/hora)
    """

    def __init__(self, cita: dict, on_guardar=None, snack_fn=None):
        super().__init__(
            expand=True, spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )
        self.cita       = cita
        self.on_guardar = on_guardar
        self.snack_fn   = snack_fn
        self._construir()

    def _construir(self):
        try:
            pacientes     = listar_pacientes()
            especialistas = listar_especialistas()
        except Exception:
            pacientes, especialistas = [], []

        # ── Descomponer fecha_hora existente ─────────────────────────────
        _fh = str(self.cita.get("fecha_hora", ""))
        _fecha_iso = _fh[:10]
        _hora_val  = _fh[11:16] if len(_fh) >= 16 else ""
        # También manejar formato con T (Supabase ISO)
        if len(_fh) >= 16 and "T" in _fh:
            _hora_val = _fh[11:16]

        _fecha_display = ""
        if len(_fecha_iso) == 10:
            try:
                a, m, d = _fecha_iso.split("-")
                _fecha_display = f"{d}/{m}/{a}"
            except Exception:
                pass

        # ── Campos del formulario ─────────────────────────────────────────
        _DD_W = 234   # ancho uniforme para los dos dropdowns principales
        self.dd_paciente = ft.Dropdown(
            label="Paciente *",
            value=self.cita.get("paciente_id"),
            width=_DD_W,
            options=[
                ft.dropdown.Option(p["id"], f"{p.get('apellido','')}, {p.get('nombre','')}")
                for p in pacientes
            ],
        )
        self.dd_especialista = ft.Dropdown(
            label="Especialista",
            value=self.cita.get("especialista_id"),
            width=_DD_W,
            options=[
                ft.dropdown.Option(
                    e["id"],
                    f"Dr/a. {e.get('apellido','')}, {e.get('nombre','')}",
                )
                for e in especialistas
            ],
            on_select=self._on_especialista,
        )
        self.tf_fecha = ft.TextField(
            label="Fecha (DD/MM/YYYY) *",
            value=_fecha_display,
            hint_text="ej. 22/04/2026",
            keyboard_type=ft.KeyboardType.DATETIME,
            width=220,
            text_size=12,
            dense=True,
        )
        self.tf_hora = ft.TextField(
            label="Hora (HH:MM) *",
            value=_hora_val,
            hint_text="15:30",
            keyboard_type=ft.KeyboardType.DATETIME,
            width=220,
            text_size=12,
            dense=True,
        )
        self.dd_duracion = ft.Dropdown(
            label="Duración",
            value=str(self.cita.get("duracion_min", 30)),
            options=[ft.dropdown.Option(str(m), f"{m} min") for m in [15, 30, 45, 60, 90]],
            width=112,
            text_size=12,
            dense=True,
        )
        self.dd_estado = ft.Dropdown(
            label="Estado",
            value=self.cita.get("estado", "pendiente"),
            options=[ft.dropdown.Option(s, s.capitalize()) for s in ESTADOS_CITA],
            width=128,
            text_size=12,
            dense=True,
        )
        self.tf_motivo = ft.TextField(
            label="Motivo",
            value=self.cita.get("motivo", ""),
            multiline=True, min_lines=2,
        )
        self.tf_notas = ft.TextField(
            label="Notas",
            value=self.cita.get("notas", ""),
            multiline=True, min_lines=2,
        )

        # ── Calendario picker ─────────────────────────────────────────────
        self._calendario = CalendarioPicker(on_pick=self._on_slot_seleccionado)

        # ── Panel izquierdo (formulario) ──────────────────────────────────
        titulo = ft.Text(
            "Nueva Cita" if not self.cita.get("id") else "Editar Cita",
            size=15, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900,
        )
        self._btn_cancelar = ft.OutlinedButton(
            "Cancelar cita", icon=ft.Icons.CANCEL,
            on_click=self._cancelar, width=220,
            visible=bool(self.cita.get("id") and self.cita.get("estado") != "cancelada"),
        )
        btns = ft.Column([
            ft.FilledButton("Guardar", icon=ft.Icons.SAVE,
                            on_click=self._guardar, width=220),
            self._btn_cancelar,
        ], spacing=6)

        panel_izq = ft.Container(
            content=ft.Column(
                controls=[
                    titulo,
                    ft.Divider(height=4),
                    self.dd_paciente,
                    self.dd_especialista,
                    # Margen superior para que la etiqueta flotante no tape el dropdown
                    ft.Container(
                        content=ft.Column([self.tf_fecha, self.tf_hora], spacing=8),
                        margin=ft.margin.only(top=10),
                    ),
                    ft.Row([self.dd_duracion, self.dd_estado], spacing=8),
                    self.tf_motivo,
                    self.tf_notas,
                    btns,
                ],
                spacing=8,
                scroll=ft.ScrollMode.AUTO,
            ),
            width=258,
            padding=ft.padding.only(right=10),
            border=ft.border.only(right=ft.BorderSide(1, "#E0E0E0")),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )

        # ── Panel derecho (calendario) ────────────────────────────────────
        self._lbl_cal = ft.Text(
            "Seleccioná un especialista para ver su disponibilidad.",
            size=12, color="#9E9E9E",
            italic=True,
        )
        panel_der = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Disponibilidad del especialista",
                            size=13, weight=ft.FontWeight.W_500, color="#424242"),
                    self._lbl_cal,
                    self._calendario,
                ],
                spacing=6, expand=True,
            ),
            expand=True,
            padding=ft.padding.only(left=12, right=14),
        )

        self.controls = [panel_izq, panel_der]

    # La carga de datos se hace en did_mount (regla Flet 0.84):
    # el control debe estar en la página antes de llamar a update().
    def did_mount(self):
        if self.cita.get("especialista_id"):
            self._cargar_calendario(self.cita["especialista_id"])

    # ── callbacks ────────────────────────────────────────────────────────

    def _on_especialista(self, e):
        eid = self.dd_especialista.value
        self._cargar_calendario(eid)

    def _cargar_calendario(self, especialista_id: str | None):
        if especialista_id:
            self._lbl_cal.value = "Hacé clic en una celda para seleccionar fecha y hora."
            self._lbl_cal.color = "#1565C0"
        else:
            self._lbl_cal.value = "Seleccioná un especialista para ver su disponibilidad."
            self._lbl_cal.color = "#9E9E9E"
        self._calendario.cargar_especialista(especialista_id)
        if self._lbl_cal.page:
            self._lbl_cal.update()

    def _on_slot_seleccionado(self, dia: date, hora: int):
        """El usuario hizo clic en una celda del calendario."""
        self.tf_fecha.value = f"{dia.day:02d}/{dia.month:02d}/{dia.year}"
        self.tf_hora.value  = f"{hora:02d}:00"
        if self.tf_fecha.page:
            self.tf_fecha.update()
            self.tf_hora.update()

    # ── validar / guardar ────────────────────────────────────────────────

    @staticmethod
    def _parsear_fecha_hora(fecha_str: str, hora_str: str) -> str:
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
            "motivo":          (self.tf_motivo.value or "").strip(),
            "notas":           (self.tf_notas.value  or "").strip(),
        }
        try:
            if self.cita.get("id"):
                actualizar_cita(self.cita["id"], datos)
                if self.snack_fn:
                    self.snack_fn("Cita actualizada correctamente.")
            else:
                resultado = crear_cita(datos)
                # Guardar el id retornado para que próximos guardados sean UPDATE
                if resultado and isinstance(resultado, list) and resultado[0].get("id"):
                    self.cita["id"] = resultado[0]["id"]
                    self.cita["estado"] = datos.get("estado", "pendiente")
                    # Mostrar botón Cancelar ahora que la cita existe
                    self._btn_cancelar.visible = True
                    if self._btn_cancelar.page:
                        self._btn_cancelar.update()
                if self.snack_fn:
                    self.snack_fn("Cita creada. Podés modificarla o agregar otra desde '+ Nueva Cita'.")
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


# ── Vista de Agenda ─────────────────────────────────────────────────────────

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
            width=196,
            on_select=self._aplicar_filtro,
        )

        _BARRA = 220   # ancho de la barra lateral

        panel_izq = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Agenda de Citas", size=16, weight=ft.FontWeight.BOLD),
                    ft.FilledButton("+ Nueva Cita", icon=ft.Icons.ADD,
                                   on_click=lambda e: self._seleccionar({}),
                                   width=_BARRA - 24),
                    self._dd_filtro,
                    ft.Divider(height=4),
                    self._lista_col,
                ],
                spacing=8, expand=True,
            ),
            width=_BARRA, padding=ft.padding.all(12),
            border=ft.border.only(right=ft.BorderSide(1, "#E0E0E0")),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
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
            pac    = c.get("pacientes") or {}
            esp    = c.get("especialistas") or {}
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
                            f"{str(c.get('fecha_hora',''))[:16].replace('T',' ')}  ·  "
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
