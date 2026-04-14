"""
Módulo de Especialistas: gestión de profesionales y su disponibilidad.
Panel de detalle con 2 pestañas:
  0 – Datos del Especialista
  1 – Disponibilidad Semanal (calendario + editor de bloques)
"""

import flet as ft
from datetime import date, datetime, timedelta
import calendar as _cal_mod

from database import (
    listar_especialistas, crear_especialista, actualizar_especialista,
    listar_disponibilidad, guardar_disponibilidad, eliminar_disponibilidad,
    listar_citas,
)

ESPECIALIDADES_DISPONIBLES = [
    "Odontología General", "Ortodoncia", "Odontopediatría", "Periodoncia",
    "Endodoncia", "Implantología", "Cirugía Maxilofacial",
    "Estética Dental", "Rehabilitación Oral", "Radiología Dental",
]
DIAS_SEMANA  = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
DIAS_CORTOS  = ["Lun",   "Mar",    "Mié",       "Jue",    "Vie",     "Sáb",    "Dom"]
CERTEZA_OPCIONES = [
    ("confirmado",    "🟢 Confirmado"),
    ("probable",      "🟡 Probable"),
    ("por_confirmar", "⚪ Por confirmar"),
]
MESES_ES = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]

# Colores disponibilidad (amarillo) y citas (naranja)
CERT_COLOR = {
    "confirmado":    "#FFE500",
    "probable":      "#FFF176",
    "por_confirmar": "#FFF9C4",
}
COLOR_CITA   = "#FFB74D"   # naranja
COLOR_LIBRE  = "#FFFFFF"
COLOR_AFUERA = "#F5F5F5"

# Dimensiones del grid horario
H_INI_CAL   = 7
H_FIN_CAL   = 20
ALTO_CELDA  = 30   # px por hora
ANCHO_HORA  = 54   # columna de hora
ANCHO_DIA   = 88   # columna por día


# ═══════════════════════════════════════════════════════════════════════════
#  EDITOR DE BLOQUES DE DISPONIBILIDAD  (panel desplegable)
# ═══════════════════════════════════════════════════════════════════════════

_CERT_BADGE_COLOR = {
    "confirmado":    ("#FFE500", "#5D4037"),
    "probable":      ("#FFF176", "#5D4037"),
    "por_confirmar": ("#EEEEEE", "#616161"),
}
_CERT_LABEL = {
    "confirmado": "Confirmado", "probable": "Probable",
    "por_confirmar": "Por confirmar",
}


class DisponibilidadEditor(ft.Column):
    """
    Panel desplegable para configurar los bloques horarios del especialista.
    Permite seleccionar varios días a la vez y guarda un bloque por cada día
    seleccionado. Al guardar se refresca el calendario automáticamente.
    """

    def __init__(self, especialista_id: str, on_cambio=None, snack_fn=None):
        super().__init__(spacing=0)
        self.especialista_id = especialista_id
        self.on_cambio       = on_cambio
        self.snack_fn        = snack_fn
        self.bloques: list[dict] = []
        self._expandido = False

        # ── Formulario de nuevo bloque ─────────────────────────────────────
        self._dias_cbs = [
            ft.Checkbox(label=d, value=False)
            for d in ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        ]
        self.tf_ini  = ft.TextField(label="Desde", value="08:00",
                                    hint_text="HH:MM", width=110)
        self.tf_fin  = ft.TextField(label="Hasta",  value="12:00",
                                    hint_text="HH:MM", width=110)
        self.dd_cert = ft.Dropdown(
            label="Certeza", value="confirmado",
            options=[ft.dropdown.Option(v, l) for v, l in CERTEZA_OPCIONES],
            width=190,
        )

        # ── Lista de bloques existentes ────────────────────────────────────
        self._lista_col = ft.Column(spacing=4)

        # ── Panel interior (invisible hasta abrir) ─────────────────────────
        self._panel = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Días:", size=12, weight=ft.FontWeight.W_500),
                    ft.Row(controls=self._dias_cbs, spacing=4),
                    ft.Row(controls=[
                        self.tf_ini, self.tf_fin, self.dd_cert,
                        ft.FilledButton(
                            "Guardar bloques", icon=ft.Icons.SAVE,
                            on_click=self._guardar_nuevos,
                        ),
                    ], spacing=8),
                    ft.Divider(height=8, color="#E0E0E0"),
                    ft.Text("Bloques configurados:", size=12,
                            weight=ft.FontWeight.W_500, color="#616161"),
                    self._lista_col,
                ],
                spacing=8,
            ),
            visible=False,
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            bgcolor="#FAFAFA",
            border=ft.border.only(
                left=ft.BorderSide(1, "#E0E0E0"),
                right=ft.BorderSide(1, "#E0E0E0"),
                bottom=ft.BorderSide(1, "#E0E0E0"),
            ),
            border_radius=ft.border_radius.only(bottom_left=8, bottom_right=8),
        )

        self._btn_toggle = ft.Container(
            content=ft.Row(controls=[
                ft.Icon(ft.Icons.KEYBOARD_ARROW_RIGHT, size=18, color="#1565C0"),
                ft.Text("Configurar bloques horarios", size=13,
                        weight=ft.FontWeight.W_500, color="#1565C0"),
                ft.Container(expand=True),
                ft.Text("(clic para desplegar)", size=11, color="#9E9E9E"),
            ], spacing=6),
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            bgcolor="#E3F2FD",
            border=ft.border.all(1, "#BBDEFB"),
            border_radius=8,
            on_click=self._toggle,
            ink=True,
        )

        self.controls = [self._btn_toggle, self._panel]

    def did_mount(self):
        self._recargar()

    def _recargar(self):
        try:
            self.bloques = listar_disponibilidad(self.especialista_id)
        except Exception as ex:
            if self.snack_fn:
                self.snack_fn(f"Error: {ex}", error=True)
        self._reconstruir_lista()
        if self.page:
            self.update()

    def _toggle(self, e):
        self._expandido = not self._expandido
        self._panel.visible = self._expandido
        # Rotar ícono
        icono = self._btn_toggle.content.controls[0]
        icono.name = (ft.Icons.KEYBOARD_ARROW_DOWN if self._expandido
                      else ft.Icons.KEYBOARD_ARROW_RIGHT)
        if self.page:
            self.update()

    # ── Guardar nuevos bloques (uno por cada día seleccionado) ─────────────

    def _guardar_nuevos(self, e):
        dias_sel = [i for i, cb in enumerate(self._dias_cbs) if cb.value]
        if not dias_sel:
            if self.snack_fn:
                self.snack_fn("Seleccioná al menos un día.", error=True)
            return
        h_ini = (self.tf_ini.value or "").strip()
        h_fin = (self.tf_fin.value or "").strip()
        if not h_ini or not h_fin:
            if self.snack_fn:
                self.snack_fn("Ingresá los horarios Desde y Hasta.", error=True)
            return
        cert = self.dd_cert.value or "confirmado"
        guardados = 0
        try:
            for dia in dias_sel:
                payload = {
                    "especialista_id": self.especialista_id,
                    "dia_semana":  dia,
                    "hora_inicio": h_ini,
                    "hora_fin":    h_fin,
                    "certeza":     cert,
                }
                res = guardar_disponibilidad(payload)
                bloque = res[0] if isinstance(res, list) else res
                self.bloques.append(bloque)
                guardados += 1
            # Limpiar selección de días
            for cb in self._dias_cbs:
                cb.value = False
            self._reconstruir_lista()
            if self.snack_fn:
                self.snack_fn(f"{guardados} bloque(s) guardado(s) correctamente.")
            if self.on_cambio:
                self.on_cambio()
        except Exception as ex:
            if self.snack_fn:
                self.snack_fn(f"Error: {ex}", error=True)

    # ── Lista compacta de bloques existentes ───────────────────────────────

    def _reconstruir_lista(self):
        self._lista_col.controls.clear()
        if not self.bloques:
            self._lista_col.controls.append(
                ft.Text("Sin bloques configurados.", size=11, color="#9E9E9E",
                        italic=True)
            )
        for b in self.bloques:
            cert  = b.get("certeza", "por_confirmar")
            bg_c, fg_c = _CERT_BADGE_COLOR.get(cert, ("#EEEEEE", "#616161"))
            dia_nombre = DIAS_SEMANA[int(b.get("dia_semana", 0))]
            self._lista_col.controls.append(
                ft.Container(
                    content=ft.Row(controls=[
                        ft.Container(
                            content=ft.Text(dia_nombre, size=11,
                                            weight=ft.FontWeight.W_600),
                            bgcolor="#FFFFFF",
                            border=ft.border.all(1, "#BDBDBD"),
                            border_radius=4,
                            padding=ft.padding.symmetric(horizontal=8, vertical=3),
                        ),
                        ft.Text(
                            f"{b.get('hora_inicio','?')} – {b.get('hora_fin','?')}",
                            size=12,
                        ),
                        ft.Container(
                            content=ft.Text(_CERT_LABEL.get(cert, cert),
                                            size=10, color=fg_c),
                            bgcolor=bg_c,
                            border_radius=10,
                            padding=ft.padding.symmetric(horizontal=8, vertical=2),
                        ),
                        ft.Container(expand=True),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            icon_color=ft.Colors.RED_400,
                            icon_size=18,
                            tooltip="Eliminar bloque",
                            on_click=lambda e, bid=b.get("id"): self._eliminar(bid),
                        ),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.padding.symmetric(horizontal=6, vertical=4),
                    border_radius=6,
                    bgcolor="#FFFFFF",
                    border=ft.border.all(1, "#E0E0E0"),
                )
            )
        if self._lista_col.page:
            self._lista_col.update()

    def _eliminar(self, bid: str):
        if not bid:
            return
        try:
            eliminar_disponibilidad(bid)
            self.bloques = [b for b in self.bloques if b.get("id") != bid]
            self._reconstruir_lista()
            if self.on_cambio:
                self.on_cambio()
        except Exception as ex:
            if self.snack_fn:
                self.snack_fn(f"Error: {ex}", error=True)


# ═══════════════════════════════════════════════════════════════════════════
#  CALENDARIO DE DISPONIBILIDAD
# ═══════════════════════════════════════════════════════════════════════════

class CalendarioDisponibilidad(ft.Column):
    """
    Calendario tipo Google Calendar.
    Amarillo = disponibilidad configurada
    Naranja   = citas ya programadas (no canceladas)
    """

    def __init__(self, especialista_id: str, snack_fn=None):
        super().__init__(spacing=0)
        self.especialista_id = especialista_id
        self.snack_fn = snack_fn
        self._vista   = "semana"
        self._inicio  = self._lunes_hoy()
        self._disp: list[dict] = []
        self._citas: list[dict] = []

        self._lbl_periodo = ft.Text("", size=13, weight=ft.FontWeight.W_500, expand=True)
        self._grid_wrap   = ft.Container()

        self._btn_sem  = self._mk_btn_vista("1 Semana",  "semana")
        self._btn_2sem = self._mk_btn_vista("2 Semanas", "2semanas")
        self._btn_mes  = self._mk_btn_vista("Mes",       "mes")

        barra_nav = ft.Row(controls=[
            ft.IconButton(ft.Icons.CHEVRON_LEFT,  on_click=lambda e: self._navegar(-1),
                          tooltip="Período anterior"),
            self._lbl_periodo,
            ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=lambda e: self._navegar(1),
                          tooltip="Período siguiente"),
            ft.Container(expand=True),
            self._btn_sem, self._btn_2sem, self._btn_mes,
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=4)

        leyenda = ft.Row(controls=[
            self._chip_leyenda("Disponible (confirmado)", "#FFE500"),
            self._chip_leyenda("Disponible (probable)",   "#FFF176"),
            self._chip_leyenda("Disponible (por confirmar)", "#FFF9C4"),
            self._chip_leyenda("Cita programada",         "#FFB74D"),
        ], spacing=8, wrap=False)

        self.controls = [
            barra_nav,
            leyenda,
            ft.Divider(height=4, color="#E0E0E0"),
            self._grid_wrap,
        ]

    @staticmethod
    def _chip_leyenda(label: str, color: str) -> ft.Container:
        return ft.Container(
            content=ft.Row(controls=[
                ft.Container(width=14, height=14, bgcolor=color,
                             border=ft.border.all(1, "#BDBDBD"), border_radius=3),
                ft.Text(label, size=10, color="#616161"),
            ], spacing=4),
        )

    def _mk_btn_vista(self, label: str, vista: str) -> ft.ElevatedButton:
        activa = self._vista == vista
        return ft.ElevatedButton(
            label, height=30,
            on_click=lambda e, v=vista: self._cambiar_vista(v),
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.BLUE_700 if activa else ft.Colors.GREY_200,
                color=ft.Colors.WHITE if activa else ft.Colors.GREY_800,
                padding=ft.padding.symmetric(horizontal=10, vertical=0),
            ),
        )

    def _actualizar_btns_vista(self):
        for btn, v in [(self._btn_sem, "semana"), (self._btn_2sem, "2semanas"), (self._btn_mes, "mes")]:
            activa = self._vista == v
            btn.style = ft.ButtonStyle(
                bgcolor=ft.Colors.BLUE_700 if activa else ft.Colors.GREY_200,
                color=ft.Colors.WHITE if activa else ft.Colors.GREY_800,
                padding=ft.padding.symmetric(horizontal=10, vertical=0),
            )
            if btn.page:
                btn.update()

    @staticmethod
    def _lunes_hoy() -> date:
        hoy = date.today()
        return hoy - timedelta(days=hoy.weekday())

    def did_mount(self):
        self.refresh()

    def refresh(self):
        try:
            self._disp = listar_disponibilidad(self.especialista_id)
        except Exception:
            self._disp = []
        try:
            todas = listar_citas({"especialista_id": self.especialista_id})
            self._citas = [c for c in todas if c.get("estado") != "cancelada"]
        except Exception:
            self._citas = []
        self._renderizar()

    # ── navegación ─────────────────────────────────────────────────────────

    def _cambiar_vista(self, v: str):
        self._vista = v
        self._inicio = self._lunes_hoy()
        self._actualizar_btns_vista()
        self.refresh()

    def _navegar(self, d: int):
        if self._vista == "semana":
            self._inicio += timedelta(weeks=d)
        elif self._vista == "2semanas":
            self._inicio += timedelta(weeks=2 * d)
        else:
            y, m = self._inicio.year, self._inicio.month
            m += d
            if m > 12: m, y = 1, y + 1
            elif m < 1: m, y = 12, y - 1
            self._inicio = date(y, m, 1)
        self.refresh()

    def _rango_fechas(self) -> tuple[date, date]:
        if self._vista == "semana":
            return self._inicio, self._inicio + timedelta(weeks=1)
        elif self._vista == "2semanas":
            return self._inicio, self._inicio + timedelta(weeks=2)
        else:
            y, m = self._inicio.year, self._inicio.month
            _, nd = _cal_mod.monthrange(y, m)
            return date(y, m, 1), date(y, m, nd) + timedelta(days=1)

    # ── colores ────────────────────────────────────────────────────────────

    @staticmethod
    def _parsear_fh(fh: str) -> datetime | None:
        """Parsea fecha_hora en cualquier formato ISO devuelto por Supabase.
        Soporta '2026-04-22 15:30', '2026-04-22T15:30', '2026-04-22T15:30:00+00:00'.
        """
        s = str(fh)[:16].replace("T", " ")
        try:
            return datetime.strptime(s, "%Y-%m-%d %H:%M")
        except Exception:
            return None

    def _color_celda(self, dia: date, hora: int) -> str:
        dia_sem = dia.weekday()
        # 1. Cita programada (naranja, prioridad alta)
        for c in self._citas:
            cdt = self._parsear_fh(c.get("fecha_hora", ""))
            if cdt is None:
                continue
            try:
                dur = int(c.get("duracion_min", 30))
                c_h_fin = cdt.hour + (cdt.minute + dur + 59) // 60
                if cdt.date() == dia and cdt.hour <= hora < max(cdt.hour + 1, c_h_fin):
                    return COLOR_CITA
            except Exception:
                pass
        # 2. Disponibilidad configurada (amarillo)
        for b in self._disp:
            if b.get("dia_semana") == dia_sem:
                try:
                    h_i = int(str(b.get("hora_inicio", "00:00"))[:2])
                    h_f = int(str(b.get("hora_fin",   "00:00"))[:2])
                    if h_i <= hora < h_f:
                        return CERT_COLOR.get(b.get("certeza", ""), "#FFF9C4")
                except Exception:
                    pass
        return COLOR_LIBRE

    # ── renderizado ────────────────────────────────────────────────────────

    def _renderizar(self):
        desde, hasta = self._rango_fechas()
        # Actualizar label período
        hasta_inc = hasta - timedelta(days=1)
        if self._vista == "mes":
            self._lbl_periodo.value = f"{MESES_ES[desde.month-1]} {desde.year}"
        else:
            self._lbl_periodo.value = (
                f"{desde.day} {MESES_ES[desde.month-1]} – "
                f"{hasta_inc.day} {MESES_ES[hasta_inc.month-1]} {hasta_inc.year}"
            )
        if self._lbl_periodo.page:
            self._lbl_periodo.update()

        if self._vista == "mes":
            self._grid_wrap.content = self._grilla_mes(desde)
        else:
            dias = [(desde + timedelta(days=i)) for i in range((hasta - desde).days)]
            self._grid_wrap.content = self._grilla_horaria(dias)

        if self._grid_wrap.page:
            self._grid_wrap.update()

    def _grilla_horaria(self, dias: list[date]) -> ft.Control:
        hoy = date.today()

        # ── cabecera de días ──────────────────────────────────────────────
        cab_hora = ft.Container(width=ANCHO_HORA, height=38)
        celdas_cab = [
            ft.Container(
                content=ft.Column(controls=[
                    ft.Text(DIAS_CORTOS[d.weekday()], size=10, color="#757575"),
                    ft.Text(str(d.day), size=14, weight=ft.FontWeight.W_600,
                            color="#1565C0" if d == hoy else "#212121"),
                ], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                expand=True,
                height=38,
                bgcolor="#E3F2FD" if d == hoy else "#FAFAFA",
                alignment=ft.Alignment(0, 0),
                border=ft.border.only(
                    left=ft.BorderSide(1, "#E0E0E0"),
                    bottom=ft.BorderSide(2, "#BDBDBD"),
                ),
            )
            for d in dias
        ]
        header = ft.Row(controls=[cab_hora] + celdas_cab, spacing=0)

        # ── filas horarias ────────────────────────────────────────────────
        filas = []
        for hora in range(H_INI_CAL, H_FIN_CAL):
            etiq = ft.Container(
                content=ft.Text(f"{hora:02d}:00", size=10, color="#9E9E9E"),
                width=ANCHO_HORA, height=ALTO_CELDA,
                alignment=ft.Alignment(1, -1),
                padding=ft.padding.only(right=6, top=2),
            )
            celdas = [
                ft.Container(
                    expand=True,
                    height=ALTO_CELDA,
                    bgcolor=self._color_celda(d, hora),
                    border=ft.border.all(0.5, "#E0E0E0"),
                    tooltip=f"{DIAS_CORTOS[d.weekday()]} {d.day}/{d.month} {hora:02d}:00",
                )
                for d in dias
            ]
            filas.append(ft.Row(controls=[etiq] + celdas, spacing=0))

        return ft.Column(
            controls=[
                header,
                ft.Column(controls=filas, spacing=0),
            ],
            spacing=0,
        )

    def _grilla_mes(self, desde: date) -> ft.Control:
        y, m  = desde.year, desde.month
        _, nd = _cal_mod.monthrange(y, m)
        hoy   = date.today()

        # Cabecera días de semana
        cab_dias = ft.Row(controls=[
            ft.Container(
                content=ft.Text(d, size=11, color="#757575",
                                weight=ft.FontWeight.W_500),
                expand=True, height=26,
                alignment=ft.Alignment(0, 0),
            )
            for d in DIAS_CORTOS
        ], spacing=0)

        offset   = date(y, m, 1).weekday()
        dias_mes = [None] * offset + [date(y, m, dd) for dd in range(1, nd + 1)]
        while len(dias_mes) % 7:
            dias_mes.append(None)

        semanas = []
        for s in range(len(dias_mes) // 7):
            semana = dias_mes[s * 7: s * 7 + 7]
            celdas = []
            for dia in semana:
                if dia is None:
                    celdas.append(ft.Container(expand=True, height=56,
                                               bgcolor=COLOR_AFUERA,
                                               border=ft.border.all(0.5, "#E0E0E0")))
                    continue
                dia_sem = dia.weekday()
                tiene_cita = any(
                    str(c.get("fecha_hora", ""))[:10] == dia.isoformat()
                    for c in self._citas
                )
                tiene_disp = any(b.get("dia_semana") == dia_sem for b in self._disp)
                if dia == hoy:
                    bg = "#1565C0"
                    fg = "#FFFFFF"
                elif tiene_cita:
                    bg, fg = COLOR_CITA, "#212121"
                elif tiene_disp:
                    bg, fg = "#FFFDE7", "#212121"
                else:
                    bg, fg = COLOR_LIBRE, "#212121"
                celdas.append(ft.Container(
                    content=ft.Text(str(dia.day), size=13, color=fg,
                                    weight=ft.FontWeight.W_600 if dia == hoy
                                    else ft.FontWeight.NORMAL),
                    expand=True, height=56,
                    bgcolor=bg,
                    alignment=ft.Alignment(0, -1),
                    padding=ft.padding.only(top=4),
                    border=ft.border.all(0.5, "#E0E0E0"),
                ))
            semanas.append(ft.Row(controls=celdas, spacing=0))

        return ft.Column(controls=[cab_dias] + semanas, spacing=0)


# ═══════════════════════════════════════════════════════════════════════════
#  FORMULARIO DE DATOS DEL ESPECIALISTA
# ═══════════════════════════════════════════════════════════════════════════

class FormularioEspecialista(ft.Column):
    def __init__(self, especialista: dict, on_guardado=None, snack_fn=None):
        super().__init__(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
        self.especialista = especialista
        self.on_guardado  = on_guardado
        self.snack_fn     = snack_fn
        self._construir()

    def _guardar(self, e):
        if not (self.tf_nombre.value or "").strip() or not (self.tf_apellido.value or "").strip():
            if self.snack_fn:
                self.snack_fn("Nombre y Apellido son obligatorios.", error=True)
            return
        especialidades = [esp for esp, cb in self._esp_checks.items() if cb.value]
        datos = {
            "nombre":         (self.tf_nombre.value    or "").strip(),
            "apellido":       (self.tf_apellido.value  or "").strip(),
            "matricula":      (self.tf_matricula.value or "").strip() or None,
            "telefono":       (self.tf_telefono.value  or "").strip() or None,
            "email":          (self.tf_email.value     or "").strip() or None,
            "especialidades": especialidades,
        }
        try:
            if self.especialista.get("id"):
                actualizar_especialista(self.especialista["id"], datos)
                self.especialista.update(datos)
                if self.snack_fn:
                    self.snack_fn("Especialista actualizado.")
            else:
                res = crear_especialista(datos)
                self.especialista = res[0] if isinstance(res, list) else res
                if self.snack_fn:
                    self.snack_fn("Especialista creado.")
            if self.on_guardado:
                self.on_guardado(self.especialista)
        except Exception as ex:
            if self.snack_fn:
                self.snack_fn(f"Error: {ex}", error=True)

    def _construir(self):
        e  = self.especialista
        sl = e.get("especialidades") or []
        self.tf_nombre    = ft.TextField(label="Nombre *",   value=e.get("nombre",    ""), expand=True)
        self.tf_apellido  = ft.TextField(label="Apellido *",  value=e.get("apellido",  ""), expand=True)
        self.tf_matricula = ft.TextField(label="Matrícula",   value=e.get("matricula", ""), expand=True)
        self.tf_telefono  = ft.TextField(label="Teléfono",    value=e.get("telefono",  ""), expand=True)
        self.tf_email     = ft.TextField(label="Email",       value=e.get("email",     ""), expand=True)
        cbs = [ft.Checkbox(label=esp, value=esp in sl, col={"sm": 6, "md": 4})
               for esp in ESPECIALIDADES_DISPONIBLES]
        self._esp_checks = {ESPECIALIDADES_DISPONIBLES[i]: cb for i, cb in enumerate(cbs)}
        self.controls = [
            ft.Text("Datos del Especialista", size=14,
                    weight=ft.FontWeight.BOLD, color="#1565C0"),
            ft.Row(controls=[self.tf_nombre, self.tf_apellido], spacing=8),
            ft.Row(controls=[self.tf_matricula, self.tf_telefono], spacing=8),
            self.tf_email,
            ft.Divider(),
            ft.Text("Especialidades", size=14, weight=ft.FontWeight.BOLD, color="#1565C0"),
            ft.ResponsiveRow(controls=cbs),
            ft.FilledButton("Guardar", icon=ft.Icons.SAVE, on_click=self._guardar),
        ]


# ═══════════════════════════════════════════════════════════════════════════
#  PANEL DE DETALLE CON 2 PESTAÑAS
# ═══════════════════════════════════════════════════════════════════════════

def _mk_tab_btn(label: str, activa: bool, on_click) -> ft.ElevatedButton:
    return ft.ElevatedButton(
        label, on_click=on_click, height=34,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.BLUE_700 if activa else ft.Colors.GREY_200,
            color=ft.Colors.WHITE if activa else ft.Colors.GREY_800,
        ),
    )


class _PanelEspecialista(ft.Column):
    def __init__(self, esp: dict, on_guardado=None, snack_fn=None):
        super().__init__(spacing=0, expand=True)
        self.esp         = esp
        self.on_guardado = on_guardado
        self.snack_fn    = snack_fn
        self._tab        = 0
        self._cal: CalendarioDisponibilidad | None = None

        # Encabezado dinámico
        self._lbl_titulo = ft.Text(
            self._titulo(),
            size=17, weight=ft.FontWeight.BOLD,
        )

        # Botones de pestañas
        self._btn_datos = _mk_tab_btn("Datos del Especialista", True,
                                      lambda e: self._ir_tab(0))
        self._btn_disp  = _mk_tab_btn("Disponibilidad Semanal", False,
                                      lambda e: self._ir_tab(1))

        self._barra_tabs = ft.Row(controls=[
            self._btn_datos,
            self._btn_disp if esp.get("id") else ft.Container(),
        ], spacing=8)

        self._area = ft.Column(spacing=0, expand=True)

        self.controls = [
            self._lbl_titulo,
            self._barra_tabs,
            ft.Divider(height=6, color="#E0E0E0"),
            self._area,
        ]
        self._cargar_tab(0)

    def _titulo(self) -> str:
        if not self.esp.get("id"):
            return "Nuevo Especialista"
        return f"Dr/a. {self.esp.get('apellido','')}, {self.esp.get('nombre','')}"

    def _ir_tab(self, i: int):
        self._tab = i
        self._btn_datos.style = ft.ButtonStyle(
            bgcolor=ft.Colors.BLUE_700 if i == 0 else ft.Colors.GREY_200,
            color=ft.Colors.WHITE if i == 0 else ft.Colors.GREY_800,
        )
        self._btn_disp.style = ft.ButtonStyle(
            bgcolor=ft.Colors.BLUE_700 if i == 1 else ft.Colors.GREY_200,
            color=ft.Colors.WHITE if i == 1 else ft.Colors.GREY_800,
        )
        if self._btn_datos.page:
            self._btn_datos.update()
        if self._btn_disp.page:
            self._btn_disp.update()
        self._cargar_tab(i)
        if self._area.page:
            self._area.update()

    def _cargar_tab(self, i: int):
        if i == 0:
            self._cal = None
            self._area.controls = [
                FormularioEspecialista(
                    self.esp,
                    on_guardado=self._on_datos_guardados,
                    snack_fn=self.snack_fn,
                )
            ]
        else:
            eid = self.esp.get("id")
            if not eid:
                return
            self._cal = CalendarioDisponibilidad(eid, snack_fn=self.snack_fn)
            self._area.controls = [
                ft.Column(
                    controls=[
                        DisponibilidadEditor(
                            eid,
                            on_cambio=lambda: self._cal.refresh() if self._cal else None,
                            snack_fn=self.snack_fn,
                        ),
                        ft.Divider(height=10, color="#E0E0E0"),
                        self._cal,
                    ],
                    spacing=0,
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                )
            ]

    def _on_datos_guardados(self, esp: dict):
        self.esp = esp
        self._lbl_titulo.value = self._titulo()
        if self._lbl_titulo.page:
            self._lbl_titulo.update()
        # Habilitar pestaña Disponibilidad
        self._barra_tabs.controls[1] = self._btn_disp
        if self._barra_tabs.page:
            self._barra_tabs.update()
        if self.on_guardado:
            self.on_guardado(esp)


# ═══════════════════════════════════════════════════════════════════════════
#  VISTA PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════

class EspecialistasView(ft.Row):
    def __init__(self):
        super().__init__(expand=True, spacing=0)
        self._todos: list[dict] = []
        self._lista_col   = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, expand=True)
        self._detalle_col = ft.Column(expand=True, visible=False, spacing=0)

        panel_izq = ft.Container(
            content=ft.Column(controls=[
                ft.Text("Especialistas", size=16, weight=ft.FontWeight.BOLD),
                ft.FilledButton("+ Nuevo", icon=ft.Icons.PERSON_ADD,
                                on_click=lambda e: self._seleccionar({})),
                ft.Divider(height=4),
                self._lista_col,
            ], spacing=8, expand=True),
            width=200, padding=10,
            border=ft.border.only(right=ft.BorderSide(1, "#E0E0E0")),
        )
        panel_der = ft.Container(
            content=self._detalle_col, expand=True, padding=12,
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
            self._todos = listar_especialistas()
        except Exception as ex:
            self._snack(f"Error: {ex}", error=True)
        self._refrescar_lista()

    def _refrescar_lista(self):
        self._lista_col.controls.clear()
        for esp in self._todos:
            especs = esp.get("especialidades") or []
            self._lista_col.controls.append(
                ft.ListTile(
                    title=ft.Text(
                        f"Dr/a. {esp.get('apellido','')}, {esp.get('nombre','')}", size=13),
                    subtitle=ft.Text(", ".join(especs[:2]) or "Sin especialidad", size=11),
                    on_click=lambda e, s=esp: self._seleccionar(s),
                    content_padding=ft.padding.symmetric(horizontal=8),
                )
            )
        if self._lista_col.page:
            self._lista_col.update()

    def _seleccionar(self, esp: dict):
        self._detalle_col.visible = True
        self._detalle_col.controls = [
            _PanelEspecialista(
                esp,
                on_guardado=self._on_guardado,
                snack_fn=self._snack,
            )
        ]
        if self._detalle_col.page:
            self._detalle_col.update()

    def _on_guardado(self, esp: dict):
        ids = [e["id"] for e in self._todos]
        if esp.get("id") not in ids:
            self._todos.insert(0, esp)
        else:
            self._todos[ids.index(esp["id"])] = esp
        self._refrescar_lista()
        self._seleccionar(esp)
