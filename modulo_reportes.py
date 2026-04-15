"""
Módulo de Reportes Colectivos — ORTHOCLINIC
Pestañas:
  1. Historia Clínica    → exporta .docx  (un paciente)
  2. Reporte Financiero  → multi-especialista / multi-paciente → .xlsx
  3. Reporte de Agenda   → multi-especialista + rango de fechas → .xlsx
"""

import os
import datetime
import flet as ft

from database import (
    listar_pacientes,
    listar_especialistas,
    obtener_paciente,
    obtener_historia_clinica,
    obtener_reporte_financiero_total,
    obtener_agenda_consolidada,
)

# ═══════════════════════════════════════════════════════════════════════════
#  Constantes visuales
# ═══════════════════════════════════════════════════════════════════════════

_AZUL      = "#1565C0"
_AZUL_BG   = "#E3F2FD"
_GRIS_BG   = "#F5F5F5"
_BORDE     = "#E0E0E0"
_OUT_DIR   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reportes")
os.makedirs(_OUT_DIR, exist_ok=True)

_COL_ESTADO_CITA = {
    "pendiente":  ("#FFF8E1", "#E65100"),
    "confirmada": ("#E8F5E9", "#1B5E20"),
    "realizada":  ("#E3F2FD", "#1565C0"),
    "cancelada":  ("#FFEBEE", "#C62828"),
}
_COL_ESTADO_TRAT = {
    "presupuestado": ("#FFF8E1", "#E65100"),
    "aprobado":      ("#E8F5E9", "#1B5E20"),
    "realizado":     ("#E3F2FD", "#1565C0"),
}


# ═══════════════════════════════════════════════════════════════════════════
#  Helpers UI
# ═══════════════════════════════════════════════════════════════════════════

def _snack(page: ft.Page, msg: str, error: bool = False):
    page.snack_bar = ft.SnackBar(
        content=ft.Text(msg),
        bgcolor=ft.Colors.RED_700 if error else ft.Colors.GREEN_700,
        open=True,
    )
    page.update()


def _titulo_mod(texto: str) -> ft.Container:
    return ft.Container(
        content=ft.Row(controls=[
            ft.Icon(ft.Icons.ANALYTICS, color=ft.Colors.WHITE, size=18),
            ft.Text(texto, size=14, weight=ft.FontWeight.BOLD,
                    color=ft.Colors.WHITE),
        ], spacing=10),
        bgcolor=_AZUL,
        padding=ft.padding.symmetric(horizontal=18, vertical=12),
    )


def _titulo_sec(texto: str, icono: str) -> ft.Container:
    return ft.Container(
        content=ft.Row(controls=[
            ft.Icon(icono, size=15, color=ft.Colors.WHITE),
            ft.Text(texto, size=11, weight=ft.FontWeight.BOLD,
                    color=ft.Colors.WHITE),
        ], spacing=8),
        bgcolor=_AZUL, border_radius=5,
        padding=ft.padding.symmetric(horizontal=12, vertical=7),
        margin=ft.margin.only(top=6, bottom=3),
    )


def _card(content) -> ft.Container:
    return ft.Container(
        content=content,
        bgcolor=ft.Colors.WHITE, border_radius=10,
        padding=16,
        border=ft.border.all(1, _BORDE),
        shadow=ft.BoxShadow(blur_radius=4, color="#12121208",
                            offset=ft.Offset(0, 2)),
    )


def _badge(texto: str, bg: str, fg: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(texto.capitalize(), size=10,
                        weight=ft.FontWeight.W_600, color=fg),
        bgcolor=bg, border_radius=20,
        padding=ft.padding.symmetric(horizontal=10, vertical=3),
    )


def _encabezado_tabla(columnas: list[tuple[str, int]]) -> ft.Container:
    return ft.Container(
        content=ft.Row(controls=[
            ft.Text(lbl, size=10, weight=ft.FontWeight.BOLD,
                    color=_AZUL, expand=exp)
            for lbl, exp in columnas
        ], spacing=0),
        bgcolor=_AZUL_BG,
        padding=ft.padding.symmetric(horizontal=12, vertical=7),
        border=ft.border.only(bottom=ft.BorderSide(1.5, "#BBDEFB")),
    )


def _fila_tabla(celdas: list[tuple], alt: bool = False) -> ft.Container:
    controls = []
    for val, exp in celdas:
        if isinstance(val, ft.Control):
            controls.append(ft.Container(content=val, expand=exp))
        else:
            controls.append(
                ft.Text(str(val) if val else "—", size=10, expand=exp,
                        color="#212121"))
    return ft.Container(
        content=ft.Row(controls=controls, spacing=0),
        bgcolor="#FAFAFA" if alt else ft.Colors.WHITE,
        padding=ft.padding.symmetric(horizontal=12, vertical=6),
        border=ft.border.only(bottom=ft.BorderSide(0.4, _BORDE)),
    )


def _sin_datos() -> ft.Container:
    return ft.Container(
        content=ft.Column(controls=[
            ft.Icon(ft.Icons.SEARCH_OFF, size=40, color=ft.Colors.GREY_400),
            ft.Text("Sin datos para la selección.", size=13,
                    color=ft.Colors.GREY_500),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
           alignment=ft.MainAxisAlignment.CENTER),
        expand=True, alignment=ft.Alignment(0, 0),
    )


def _btn_azul(texto: str, icono: str, on_click) -> ft.ElevatedButton:
    return ft.ElevatedButton(
        texto, icon=icono, on_click=on_click,
        style=ft.ButtonStyle(bgcolor=_AZUL, color=ft.Colors.WHITE),
    )


def _fmt_fecha(iso: str) -> str:
    if not iso:
        return "—"
    try:
        return datetime.datetime.fromisoformat(
            iso.replace("Z", "+00:00")).strftime("%d/%m/%Y")
    except Exception:
        return str(iso)[:10]


def _fmt_monto(v) -> str:
    try:
        return f"$ {float(v):,.2f}"
    except Exception:
        return "$ 0,00"


def _dlg_ok(page: ft.Page, titulo: str, cuerpo: str):
    dlg = ft.AlertDialog(
        title=ft.Text(titulo),
        content=ft.Column(controls=[
            ft.Text(cuerpo, selectable=True, size=12),
            ft.Text("Descargable desde la carpeta 'reportes/' del proyecto.",
                    size=11, color="#616161"),
        ], tight=True, spacing=6),
        actions=[ft.TextButton("Cerrar",
                               on_click=lambda _: page.pop_dialog())],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.show_dialog(dlg)


# ═══════════════════════════════════════════════════════════════════════════
#  _MultiSelector — Panel de selección múltiple con checkboxes
# ═══════════════════════════════════════════════════════════════════════════

class _MultiSelector(ft.Column):
    """
    Panel reutilizable de multi-selección mediante checkboxes.
    Muestra 'Todos' / 'Ninguno' y una lista scrollable de ítems.
    """

    def __init__(self, label: str, alto: int = 130):
        super().__init__(spacing=2, expand=True)
        self._label  = label
        self._items: list[tuple[str, str]] = []   # (id, texto)
        self._checks: dict[str, ft.Checkbox] = {}
        self._alto   = alto
        self._lista  = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO)
        self._construir()

    def _construir(self):
        self.controls = [
            ft.Text(self._label.upper(), size=9,
                    weight=ft.FontWeight.BOLD, color="#9E9E9E"),
            ft.Row(controls=[
                ft.TextButton("Todos",   on_click=self._todos),
                ft.TextButton("Ninguno", on_click=self._ninguno),
            ], spacing=0),
            ft.Container(
                content=self._lista,
                border=ft.border.all(1, _BORDE),
                border_radius=6,
                bgcolor=ft.Colors.WHITE,
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                height=self._alto,
            ),
        ]

    def set_items(self, items: list[tuple[str, str]]):
        """items: lista de (id, label). Selecciona todos por defecto."""
        self._items  = items
        self._checks = {}
        controles    = []
        for item_id, item_label in items:
            cb = ft.Checkbox(
                label=item_label,
                value=True,
                label_style=ft.TextStyle(size=11),
            )
            self._checks[item_id] = cb
            controles.append(cb)
        self._lista.controls = controles
        if self._lista.page:
            self._lista.update()

    def get_selected_ids(self) -> list[str] | None:
        """
        None  → todos seleccionados (o no hay ítems) → sin filtro
        []    → ninguno seleccionado
        [ids] → selección parcial
        """
        if not self._items:
            return None
        selected = [iid for iid, cb in self._checks.items() if cb.value]
        if len(selected) == len(self._items):
            return None   # "Todos" = sin filtro
        return selected

    def get_selected_labels(self) -> list[str]:
        """Retorna los labels de los ítems seleccionados."""
        return [
            label
            for (iid, label) in self._items
            if self._checks.get(iid) and self._checks[iid].value
        ]

    def _todos(self, e=None):
        for cb in self._checks.values():
            cb.value = True
        if self.page:
            self.update()

    def _ninguno(self, e=None):
        for cb in self._checks.values():
            cb.value = False
        if self.page:
            self.update()


# ═══════════════════════════════════════════════════════════════════════════
#  TAB 1 — Historia Clínica (.docx)  [un paciente a la vez]
# ═══════════════════════════════════════════════════════════════════════════

class _HistoriaClinicaTab(ft.Column):
    def __init__(self):
        super().__init__(spacing=0, expand=True)
        self._dd_pac = ft.Dropdown(
            label="Seleccionar paciente",
            hint_text="Elegí un paciente…",
            options=[],
            expand=True, dense=True,
            on_select=self._on_pac,
        )
        self._info_area = ft.Container(expand=True)
        self._btn_word  = ft.ElevatedButton(
            "Generar Word (.docx)",
            icon=ft.Icons.ARTICLE,
            on_click=self._exportar,
            visible=False,
            style=ft.ButtonStyle(bgcolor="#283593",
                                  color=ft.Colors.WHITE),
        )
        self._paciente = None
        self._historia = None
        self._construir()

    def _construir(self):
        barra = ft.Container(
            content=ft.Row(controls=[
                ft.Icon(ft.Icons.PERSON_SEARCH, color=_AZUL),
                ft.Row(controls=[self._dd_pac], expand=True),
                self._btn_word,
            ], spacing=12,
               vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            bgcolor=_GRIS_BG,
            border=ft.border.only(bottom=ft.BorderSide(1, _BORDE)),
        )
        self.controls = [barra, self._info_area]

    def did_mount(self):
        try:
            pacs = listar_pacientes()
            self._dd_pac.options = [
                ft.dropdown.Option(
                    p["id"],
                    f"{p.get('apellido','—')}, {p.get('nombre','')}  "
                    f"({'DNI: ' + p['dni'] if p.get('dni') else 'sin DNI'})",
                )
                for p in sorted(pacs, key=lambda x: x.get("apellido", ""))
            ]
            if self._dd_pac.page:
                self._dd_pac.update()
        except Exception as ex:
            print(f"[HC-Tab] error cargando pacientes: {ex}", flush=True)

    def _on_pac(self, e=None):
        pid = self._dd_pac.value
        if not pid:
            return
        self._info_area.content = ft.Container(
            content=ft.ProgressRing(),
            alignment=ft.Alignment(0, 0), expand=True)
        if self._info_area.page:
            self._info_area.update()
        try:
            self._paciente = obtener_paciente(pid) or {}
            self._historia = obtener_historia_clinica(pid) or {}
        except Exception as ex:
            self._info_area.content = ft.Text(f"Error: {ex}",
                                               color=ft.Colors.RED_700)
            if self._info_area.page:
                self._info_area.update()
            return
        self._btn_word.visible = True
        if self._btn_word.page:
            self._btn_word.update()
        self._mostrar_resumen()

    def _mostrar_resumen(self):
        p = self._paciente or {}
        h = self._historia or {}
        sv = h.get("signos_vitales") or {}
        ant_dict = h.get("antecedentes") or {}

        def _campo(lbl, val):
            return ft.Column(controls=[
                ft.Text(lbl.upper(), size=9, weight=ft.FontWeight.BOLD,
                        color="#9E9E9E"),
                ft.Text(str(val) if val else "—", size=11, color="#212121"),
            ], spacing=2, expand=True)

        ficha = _card(ft.Column(controls=[
            _titulo_sec("Ficha del Paciente", ft.Icons.PERSON),
            ft.Row(controls=[
                _campo("Apellido",   p.get("apellido", "")),
                _campo("Nombre",     p.get("nombre", "")),
                _campo("DNI",        p.get("dni", "")),
                _campo("Fec. nac.",  _fmt_fecha(p.get("fecha_nac", ""))),
            ], spacing=16),
            ft.Row(controls=[
                _campo("Grupo sang.", p.get("grupo_sangre", "")),
                _campo("Teléfono",    p.get("telefono", "")),
                _campo("Email",       p.get("email", "")),
                _campo("Obra social", p.get("obra_social", "")),
            ], spacing=16),
            ft.Row(controls=[
                _campo("Dirección",     p.get("direccion", "")),
                _campo("Alergias",      p.get("alergias", "")),
                _campo("Nro. afiliado", p.get("nro_afiliado", "")),
            ], spacing=16),
        ], spacing=10))

        positivos = [lbl for key, lbl in [
            ("tratamiento_medico",       "Trat. médico"),
            ("medicamentos",             "Medicamentos"),
            ("alergias_med",             "Alergias med."),
            ("cardiopatias",             "Cardiopatías"),
            ("presion_arterial_alt",     "Alt. tensión"),
            ("embarazo",                 "Embarazo"),
            ("diabetes",                 "Diabetes"),
            ("hepatitis",                "Hepatitis"),
            ("irradiaciones",            "Irradiaciones"),
            ("discrasias",               "Discrasias"),
            ("fiebre_reumatica",         "Fiebre reumática"),
            ("enf_renales",              "Enf. renales"),
            ("inmunosupresion",          "Inmunosupresión"),
            ("trastornos_emocionales",   "Trast. emocional"),
            ("trastornos_respiratorios", "Trast. respiratorio"),
            ("trastornos_gastricos",     "Trast. gástrico"),
            ("epilepsia",                "Epilepsia"),
            ("cirugias",                 "Cirugías"),
            ("enf_orales",               "Enf. orales"),
            ("otras_alteraciones",       "Otras alt."),
            ("fuma_licor",               "Tabaquismo/Alcohol"),
        ] if ant_dict.get(key)]

        ant_chips = ft.Row(controls=[
            ft.Container(
                content=ft.Text(lbl, size=10, weight=ft.FontWeight.W_600,
                                color="#C62828"),
                bgcolor="#FFEBEE", border_radius=12,
                padding=ft.padding.symmetric(horizontal=10, vertical=3),
            )
            for lbl in positivos
        ] or [ft.Text("Sin antecedentes positivos registrados",
                      size=11, color="#9E9E9E")],
            wrap=True, spacing=6,
        )

        anamnesis = _card(ft.Column(controls=[
            _titulo_sec("Anamnesis — Antecedentes positivos",
                        ft.Icons.WARNING_AMBER),
            ant_chips,
        ], spacing=8))

        sv_cols = [
            ("Presión",  sv.get("tension_arterial", "")),
            ("Pulso",    sv.get("pulso", "")),
            ("Temp.",    sv.get("temperatura", "")),
            ("F. Resp.", sv.get("frecuencia_resp", "")),
            ("Peso",     (sv.get("peso", "") + " kg") if sv.get("peso") else "—"),
            ("Talla",    (sv.get("estatura", "") + " cm") if sv.get("estatura") else "—"),
        ]
        cv = _card(ft.Column(controls=[
            _titulo_sec("Constantes Vitales", ft.Icons.MONITOR_HEART),
            ft.Row(controls=[_campo(l, v) for l, v in sv_cols], spacing=12),
        ], spacing=8))

        consulta = _card(ft.Column(controls=[
            _titulo_sec("Datos de la Consulta", ft.Icons.NOTES),
            ft.Row(controls=[
                _campo("N° Historia", h.get("historia_no", "")),
                _campo("Odontólogo",  h.get("odontologo", "")),
                _campo("Fecha",       _fmt_fecha(h.get("fecha_elaboracion", ""))),
            ], spacing=16),
            _campo("Motivo de consulta", h.get("motivo_consulta", "")),
            _campo("Hallazgos / Enfermedad actual", h.get("enfermedad_actual", "")),
            _campo("Observaciones", h.get("observaciones", "")),
        ], spacing=10))

        nota = ft.Container(
            content=ft.Row(controls=[
                ft.Icon(ft.Icons.INFO_OUTLINE, size=16, color=_AZUL),
                ft.Text(
                    "Hacé clic en 'Generar Word (.docx)' para descargar "
                    "el documento completo con los 21 antecedentes.",
                    size=11, color=_AZUL,
                ),
            ], spacing=8),
            bgcolor=_AZUL_BG, border_radius=8,
            padding=ft.padding.symmetric(horizontal=14, vertical=8),
        )

        self._info_area.content = ft.Container(
            content=ft.Column(
                controls=[ficha, anamnesis, cv, consulta, nota],
                spacing=10, scroll=ft.ScrollMode.AUTO,
            ),
            padding=ft.padding.all(14), expand=True,
        )
        if self._info_area.page:
            self._info_area.update()

    def _exportar(self, e=None):
        if not self._paciente:
            if self.page:
                _snack(self.page, "Seleccioná un paciente primero.", error=True)
            return
        try:
            from generar_archivos import generar_historia_clinica_docx
            ruta   = generar_historia_clinica_docx(
                self._paciente, self._historia or {},
                output_dir=_OUT_DIR,
            )
            nombre = os.path.basename(ruta)
            print(f"[DOCX] {ruta}", flush=True)
            if self.page:
                _dlg_ok(self.page, "Historia Clínica generada",
                        f"Archivo: {nombre}")
        except Exception as ex:
            import traceback; traceback.print_exc()
            if self.page:
                _snack(self.page, f"Error: {ex}", error=True)


# ═══════════════════════════════════════════════════════════════════════════
#  TAB 2 — Reporte Financiero Total (.xlsx)
#  Multi-selección de especialistas + paciente + saldo mínimo
# ═══════════════════════════════════════════════════════════════════════════

class _ReporteFinancieroTab(ft.Column):
    def __init__(self):
        super().__init__(spacing=0, expand=True)

        self._sel_esp = _MultiSelector("Especialistas", alto=140)
        self._dd_pac  = ft.Dropdown(
            label="Paciente",
            hint_text="Todos…",
            options=[ft.dropdown.Option("", "(Todos)")],
            expand=True, dense=True,
        )
        self._tf_saldo = ft.TextField(
            label="Saldo mínimo ($)",
            value="0",
            hint_text="Ej: 500",
            dense=True,
            keyboard_type=ft.KeyboardType.NUMBER,
            width=140,
        )
        self._area  = ft.Container(expand=True)
        self._datos: list[dict] = []
        self._construir_shell()

    def _construir_shell(self):
        filtros = ft.Container(
            content=ft.Column(controls=[
                ft.Row(controls=[
                    ft.Container(content=self._sel_esp, expand=3),
                    ft.Column(controls=[
                        ft.Row(controls=[self._dd_pac], expand=True),
                        ft.Row(controls=[self._tf_saldo]),
                    ], expand=3, spacing=10),
                ], spacing=16, vertical_alignment=ft.CrossAxisAlignment.START),
                ft.Row(controls=[
                    _btn_azul("Aplicar filtros", ft.Icons.FILTER_ALT,
                              lambda _: self._cargar()),
                    ft.ElevatedButton(
                        "Exportar Excel (.xlsx)",
                        icon=ft.Icons.FILE_DOWNLOAD,
                        on_click=self._exportar,
                        style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_800,
                                              color=ft.Colors.WHITE),
                    ),
                ], spacing=10),
            ], spacing=10),
            padding=ft.padding.symmetric(horizontal=14, vertical=12),
            bgcolor=_GRIS_BG,
            border=ft.border.only(bottom=ft.BorderSide(1, _BORDE)),
        )
        self.controls = [filtros, self._area]

    def did_mount(self):
        try:
            esps = listar_especialistas()
            self._sel_esp.set_items([
                (e["id"],
                 f"{e.get('apellido', '')} {e.get('nombre', '')}".strip())
                for e in esps
            ])
            pacs = listar_pacientes()
            self._dd_pac.options = [ft.dropdown.Option("", "(Todos)")] + [
                ft.dropdown.Option(
                    p["id"],
                    f"{p.get('apellido', '')} {p.get('nombre', '')}".strip()
                )
                for p in sorted(pacs, key=lambda x: x.get("apellido", ""))
            ]
            if self.page:
                self._dd_pac.update()
        except Exception as ex:
            print(f"[FinancieroTab] error cargando: {ex}", flush=True)
        self._cargar()

    def _cargar(self):
        self._area.content = ft.Container(
            content=ft.ProgressRing(),
            alignment=ft.Alignment(0, 0), expand=True,
        )
        if self._area.page:
            self._area.update()

        esp_ids = self._sel_esp.get_selected_ids()   # None = todos
        pac_id  = self._dd_pac.value or None
        try:
            saldo_min = float((self._tf_saldo.value or "0").replace(",", "."))
        except Exception:
            saldo_min = 0.0

        # Si ningún especialista seleccionado → mostrar aviso
        if esp_ids is not None and len(esp_ids) == 0:
            self._area.content = ft.Container(
                content=ft.Column(controls=[
                    ft.Icon(ft.Icons.WARNING_AMBER, size=36,
                            color=ft.Colors.ORANGE_700),
                    ft.Text("Seleccioná al menos un especialista.",
                            size=13, color=ft.Colors.ORANGE_700),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   alignment=ft.MainAxisAlignment.CENTER),
                expand=True, alignment=ft.Alignment(0, 0),
            )
            if self._area.page:
                self._area.update()
            return

        pac_ids = [pac_id] if pac_id else None
        try:
            todos = obtener_reporte_financiero_total(
                especialista_ids=esp_ids,
                paciente_ids=pac_ids,
            )
            self._datos = [d for d in todos
                           if float(d.get("saldo", 0)) >= saldo_min]
        except Exception as ex:
            self._area.content = ft.Text(f"Error: {ex}",
                                          color=ft.Colors.RED_700)
            if self._area.page:
                self._area.update()
            return
        self._refrescar_tabla(saldo_min)

    def _refrescar_tabla(self, saldo_min: float = 0.0):
        datos = self._datos
        if not datos:
            self._area.content = _sin_datos()
            if self._area.page:
                self._area.update()
            return

        columnas = [
            ("Paciente", 4), ("DNI", 2), ("Obra Social", 2),
            ("Especialista", 3), ("Tratamientos", 1),
            ("Total Costo", 2), ("Pagado", 2), ("Saldo", 2),
        ]
        filas = [_encabezado_tabla(columnas)]

        gran_c = gran_p = gran_s = 0.0
        for i, d in enumerate(datos):
            pac = d.get("paciente") or {}
            esp = d.get("especialista") or {}
            nom_pac = f"{pac.get('apellido','')} {pac.get('nombre','')}".strip()
            nom_esp = f"{esp.get('apellido','')} {esp.get('nombre','')}".strip()
            costo   = float(d.get("total_costo", 0))
            pagado  = float(d.get("total_pagado", 0))
            saldo   = float(d.get("saldo", 0))
            gran_c += costo; gran_p += pagado; gran_s += saldo

            saldo_ctrl = ft.Text(
                _fmt_monto(saldo), size=10, weight=ft.FontWeight.BOLD,
                color=ft.Colors.RED_700 if saldo > 0 else ft.Colors.GREEN_700,
            )
            filas.append(_fila_tabla([
                (nom_pac or "—",                     4),
                (pac.get("dni") or "—",              2),
                (pac.get("obra_social") or "—",      2),
                (nom_esp or "—",                     3),
                (str(d.get("n_tratamientos", 0)),    1),
                (_fmt_monto(costo),                  2),
                (_fmt_monto(pagado),                 2),
                (saldo_ctrl,                         2),
            ], alt=i % 2 == 1))

        total_bar = ft.Container(
            content=ft.Row(controls=[
                ft.Text(f"{len(datos)} registros",
                        size=11, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                ft.Text("Costo total:", size=11),
                ft.Text(_fmt_monto(gran_c), size=12,
                        weight=ft.FontWeight.BOLD, color=_AZUL),
                ft.Text("  Pagado:", size=11),
                ft.Text(_fmt_monto(gran_p), size=12,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.GREEN_700),
                ft.Text("  Saldo pendiente:", size=11),
                ft.Text(_fmt_monto(gran_s), size=12,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.RED_700 if gran_s > 0
                              else ft.Colors.GREEN_700),
            ], spacing=8, wrap=False),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            bgcolor=_AZUL_BG,
            border=ft.border.only(top=ft.BorderSide(1, "#BBDEFB")),
        )

        self._area.content = ft.Container(
            content=ft.Column(controls=[
                ft.Container(
                    content=ft.Column(controls=filas, spacing=0),
                    expand=True,
                ),
                total_bar,
            ], spacing=0, expand=True, scroll=ft.ScrollMode.AUTO),
            expand=True,
        )
        if self._area.page:
            self._area.update()

    def _exportar(self, e=None):
        if not self._datos:
            if self.page:
                _snack(self.page, "Cargá los datos con 'Aplicar filtros' primero.",
                       error=True)
            return
        try:
            from generar_archivos import generar_excel_financiero_total
            esp_labels = self._sel_esp.get_selected_labels()
            desc = "Especialistas: " + (
                ", ".join(esp_labels) if esp_labels else "Todos"
            )
            pac_val = self._dd_pac.value
            if pac_val:
                for opt in self._dd_pac.options:
                    if opt.key == pac_val:
                        desc += f"  |  Paciente: {opt.text or ''}"
                        break
            try:
                saldo_min = float(
                    (self._tf_saldo.value or "0").replace(",", "."))
            except Exception:
                saldo_min = 0.0

            ruta   = generar_excel_financiero_total(
                self._datos,
                filtros_desc=desc,
                saldo_minimo=saldo_min,
                output_dir=_OUT_DIR,
            )
            nombre = os.path.basename(ruta)
            print(f"[XLSX-Financiero] {ruta}", flush=True)
            if self.page:
                _dlg_ok(self.page, "Reporte Financiero generado",
                        f"Archivo: {nombre}")
        except Exception as ex:
            import traceback; traceback.print_exc()
            if self.page:
                _snack(self.page, f"Error: {ex}", error=True)


# ═══════════════════════════════════════════════════════════════════════════
#  TAB 3 — Reporte de Agenda Consolidada (.xlsx)
#  Multi-selección de especialistas + rango libre de fechas
# ═══════════════════════════════════════════════════════════════════════════

class _ReporteAgendaTab(ft.Column):
    def __init__(self):
        super().__init__(spacing=0, expand=True)

        today     = datetime.date.today()
        semana    = (today + datetime.timedelta(days=7)).isoformat()
        self._sel_esp = _MultiSelector("Especialistas", alto=140)
        self._tf_desde = ft.TextField(
            label="Desde (AAAA-MM-DD)",
            value=today.isoformat(),
            dense=True, width=155,
            hint_text="2025-01-01",
        )
        self._tf_hasta = ft.TextField(
            label="Hasta (AAAA-MM-DD)",
            value=semana,
            dense=True, width=155,
            hint_text="2025-12-31",
        )
        self._dd_estado = ft.Dropdown(
            label="Estado de cita",
            value="",
            options=[
                ft.dropdown.Option("",          "(Todos)"),
                ft.dropdown.Option("pendiente",  "Pendiente"),
                ft.dropdown.Option("confirmada", "Confirmada"),
                ft.dropdown.Option("realizada",  "Realizada"),
                ft.dropdown.Option("cancelada",  "Cancelada"),
            ],
            dense=True, width=160,
        )
        self._area  = ft.Container(expand=True)
        self._datos: list[dict] = []
        self._construir_shell()

    def _construir_shell(self):
        filtros = ft.Container(
            content=ft.Column(controls=[
                ft.Row(controls=[
                    ft.Container(content=self._sel_esp, expand=3),
                    ft.Column(controls=[
                        ft.Row(controls=[
                            self._tf_desde,
                            ft.Text("→", size=14, color=_AZUL),
                            self._tf_hasta,
                        ], spacing=8),
                        ft.Row(controls=[self._dd_estado]),
                    ], expand=3, spacing=10),
                ], spacing=16, vertical_alignment=ft.CrossAxisAlignment.START),
                ft.Row(controls=[
                    _btn_azul("Ver agenda", ft.Icons.CALENDAR_VIEW_MONTH,
                              lambda _: self._cargar()),
                    ft.ElevatedButton(
                        "Exportar Excel (.xlsx)",
                        icon=ft.Icons.FILE_DOWNLOAD,
                        on_click=self._exportar,
                        style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_800,
                                              color=ft.Colors.WHITE),
                    ),
                ], spacing=10),
            ], spacing=10),
            padding=ft.padding.symmetric(horizontal=14, vertical=12),
            bgcolor=_GRIS_BG,
            border=ft.border.only(bottom=ft.BorderSide(1, _BORDE)),
        )
        self.controls = [filtros, self._area]

    def did_mount(self):
        try:
            esps = listar_especialistas()
            self._sel_esp.set_items([
                (e["id"],
                 f"{e.get('apellido', '')} {e.get('nombre', '')}".strip())
                for e in esps
            ])
        except Exception as ex:
            print(f"[AgendaTab] error cargando especialistas: {ex}", flush=True)
        self._cargar()

    def _cargar(self):
        self._area.content = ft.Container(
            content=ft.ProgressRing(),
            alignment=ft.Alignment(0, 0), expand=True,
        )
        if self._area.page:
            self._area.update()

        esp_ids = self._sel_esp.get_selected_ids()

        if esp_ids is not None and len(esp_ids) == 0:
            self._area.content = ft.Container(
                content=ft.Column(controls=[
                    ft.Icon(ft.Icons.WARNING_AMBER, size=36,
                            color=ft.Colors.ORANGE_700),
                    ft.Text("Seleccioná al menos un especialista.",
                            size=13, color=ft.Colors.ORANGE_700),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   alignment=ft.MainAxisAlignment.CENTER),
                expand=True, alignment=ft.Alignment(0, 0),
            )
            if self._area.page:
                self._area.update()
            return

        desde  = (self._tf_desde.value or "").strip()
        hasta  = (self._tf_hasta.value or "").strip()
        estado = self._dd_estado.value or None

        try:
            citas = obtener_agenda_consolidada(
                especialista_ids=esp_ids,
                fecha_inicio=desde or None,
                fecha_fin=hasta or None,
            )
            if estado:
                citas = [c for c in citas if c.get("estado") == estado]
            self._datos = citas
        except Exception as ex:
            self._area.content = ft.Text(f"Error: {ex}",
                                          color=ft.Colors.RED_700)
            if self._area.page:
                self._area.update()
            return
        self._refrescar_tabla(desde, hasta)

    def _refrescar_tabla(self, desde: str, hasta: str):
        datos = self._datos
        DIAS_ES = {0: "Lun", 1: "Mar", 2: "Mié", 3: "Jue",
                   4: "Vie", 5: "Sáb", 6: "Dom"}

        info_bar = ft.Container(
            content=ft.Row(controls=[
                ft.Icon(ft.Icons.INFO_OUTLINE, size=14, color=_AZUL),
                ft.Text(
                    f"{len(datos)} cita(s) — "
                    f"{_fmt_fecha(desde) if desde else '?'} "
                    f"→ {_fmt_fecha(hasta) if hasta else '?'}",
                    size=11, color=_AZUL,
                ),
            ], spacing=8),
            bgcolor=_AZUL_BG, border_radius=6,
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            margin=ft.margin.only(left=14, right=14, top=8, bottom=4),
        )

        if not datos:
            self._area.content = ft.Column(controls=[info_bar, _sin_datos()],
                                            spacing=0, expand=True)
            if self._area.page:
                self._area.update()
            return

        # Contadores por estado
        est_count: dict[str, int] = {}
        for c in datos:
            est = c.get("estado", "")
            est_count[est] = est_count.get(est, 0) + 1

        contador_chips = ft.Row(controls=[
            ft.Container(
                content=ft.Text(
                    f"{est.capitalize()}: {cnt}",
                    size=10, weight=ft.FontWeight.W_600,
                    color=_COL_ESTADO_CITA.get(est, ("#EEE", "#333"))[1],
                ),
                bgcolor=_COL_ESTADO_CITA.get(est, ("#EEE", "#333"))[0],
                border_radius=12,
                padding=ft.padding.symmetric(horizontal=10, vertical=3),
            )
            for est, cnt in sorted(est_count.items())
        ], spacing=6, wrap=True)

        columnas = [
            ("Fecha", 2), ("Día", 1), ("Hora", 1), ("Paciente", 4),
            ("Teléfono", 2), ("Especialista", 3), ("Motivo", 4),
            ("Estado", 2),
        ]
        filas = [_encabezado_tabla(columnas)]

        for i, c in enumerate(datos):
            pac = c.get("pacientes") or {}
            esp = c.get("especialistas") or {}
            nom_pac = f"{pac.get('apellido','')} {pac.get('nombre','')}".strip()
            nom_esp = f"{esp.get('apellido','')} {esp.get('nombre','')}".strip()
            estado  = c.get("estado", "")
            bg, fg  = _COL_ESTADO_CITA.get(estado, ("#EEE", "#333"))
            iso = c.get("fecha_hora", "")
            try:
                dt    = datetime.datetime.fromisoformat(
                    iso.replace("Z", "+00:00"))
                fecha = dt.strftime("%d/%m/%Y")
                dia   = DIAS_ES.get(dt.weekday(), "")
                hora  = dt.strftime("%H:%M")
            except Exception:
                fecha = iso[:10]; dia = ""; hora = ""

            filas.append(_fila_tabla([
                (fecha, 2), (dia, 1), (hora, 1),
                (nom_pac or "—", 4),
                (pac.get("telefono") or "—", 2),
                (nom_esp or "—", 3),
                (c.get("motivo") or "—", 4),
                (_badge(estado, bg, fg), 2),
            ], alt=i % 2 == 1))

        self._area.content = ft.Container(
            content=ft.Column(controls=[
                info_bar,
                ft.Container(
                    content=contador_chips,
                    padding=ft.padding.symmetric(horizontal=14, vertical=4),
                ),
                ft.Container(
                    content=ft.Column(controls=filas, spacing=0),
                    expand=True,
                ),
            ], spacing=0, expand=True, scroll=ft.ScrollMode.AUTO),
            expand=True,
        )
        if self._area.page:
            self._area.update()

    def _exportar(self, e=None):
        if not self._datos:
            if self.page:
                _snack(self.page, "Cargá los datos con 'Ver agenda' primero.",
                       error=True)
            return
        try:
            from generar_archivos import generar_excel_agenda_consolidada
            esp_labels = self._sel_esp.get_selected_labels()
            desde = (self._tf_desde.value or "").strip()
            hasta = (self._tf_hasta.value or "").strip()
            ruta   = generar_excel_agenda_consolidada(
                self._datos,
                especialistas_nombres=esp_labels or None,
                fecha_inicio=desde,
                fecha_fin=hasta,
                output_dir=_OUT_DIR,
            )
            nombre = os.path.basename(ruta)
            print(f"[XLSX-Agenda] {ruta}", flush=True)
            if self.page:
                _dlg_ok(self.page, "Agenda Consolidada generada",
                        f"Archivo: {nombre}")
        except Exception as ex:
            import traceback; traceback.print_exc()
            if self.page:
                _snack(self.page, f"Error: {ex}", error=True)


# ═══════════════════════════════════════════════════════════════════════════
#  ReportesView — vista principal con 3 pestañas
# ═══════════════════════════════════════════════════════════════════════════

class ReportesView(ft.Column):
    def __init__(self):
        super().__init__(spacing=0, expand=True)

        self._tab_hc  = _HistoriaClinicaTab()
        self._tab_fin = _ReporteFinancieroTab()
        self._tab_age = _ReporteAgendaTab()

        _t1 = ft.Tab("Historia Clínica",    ft.Icons.ARTICLE)
        _t2 = ft.Tab("Reporte Financiero",  ft.Icons.ACCOUNT_BALANCE_WALLET)
        _t3 = ft.Tab("Reporte de Agenda",   ft.Icons.CALENDAR_MONTH)
        _t1.content = ft.Container(content=self._tab_hc,  expand=True, padding=0)
        _t2.content = ft.Container(content=self._tab_fin, expand=True, padding=0)
        _t3.content = ft.Container(content=self._tab_age, expand=True, padding=0)
        _tab_items  = [_t1, _t2, _t3]

        tabs = ft.Tabs(
            _tab_items,
            len(_tab_items),
            selected_index=0,
            animation_duration=200,
            expand=True,
        )

        self.controls = [
            _titulo_mod("Reportes Colectivos — ORTHOCLINIC"),
            tabs,
        ]
