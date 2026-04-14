"""
Módulo de Reportes — ORTHOCLINIC
Pestañas:
  1. Historia Clínica → exporta .docx
  2. Presupuestos      → filtros + exporta .xlsx
  3. Agenda            → cronograma especialista + exporta .xlsx
"""

import os
import datetime
import flet as ft

from database import (
    listar_pacientes,
    listar_especialistas,
    obtener_paciente,
    obtener_historia_clinica,
    obtener_datos_reporte_presupuestos,
    obtener_datos_citas,
)

# ═══════════════════════════════════════════════════════════════════════════
#  Constantes visuales
# ═══════════════════════════════════════════════════════════════════════════

_AZUL      = "#1565C0"
_AZUL_BG   = "#E3F2FD"
_GRIS_BG   = "#F5F5F5"
_BORDE     = "#E0E0E0"
_OUT_DIR   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reportes")

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
            ft.Icon(ft.Icons.ASSESSMENT, color=ft.Colors.WHITE, size=18),
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
        expand=True, alignment=ft.alignment.center,
    )


def _btn_azul(texto: str, icono: str, on_click) -> ft.ElevatedButton:
    return ft.ElevatedButton(
        texto, icon=icono, on_click=on_click,
        style=ft.ButtonStyle(bgcolor=_AZUL, color=ft.Colors.WHITE),
    )


def _btn_rojo(texto: str, on_click) -> ft.ElevatedButton:
    return ft.ElevatedButton(
        texto, icon=ft.Icons.DESCRIPTION, on_click=on_click,
        style=ft.ButtonStyle(bgcolor=ft.Colors.RED_800,
                              color=ft.Colors.WHITE),
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
#  TAB 1 — Historia Clínica (.docx)
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
            style=ft.ButtonStyle(bgcolor=ft.Colors.INDIGO_700,
                                  color=ft.Colors.WHITE),
        )
        self._paciente  = None
        self._historia  = None
        self._construir()

    def _construir(self):
        barra = ft.Container(
            content=ft.Row(controls=[
                ft.Icon(ft.Icons.PERSON_SEARCH, color=_AZUL),
                ft.Row(controls=[self._dd_pac], expand=True),
                self._btn_word,
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
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
            content=ft.ProgressRing(), alignment=ft.alignment.center, expand=True)
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
                _campo("Apellido",   p.get("apellido","")),
                _campo("Nombre",     p.get("nombre","")),
                _campo("DNI",        p.get("dni","")),
                _campo("Fec. nac.",  _fmt_fecha(p.get("fecha_nac",""))),
            ], spacing=16),
            ft.Row(controls=[
                _campo("Grupo sang.", p.get("grupo_sangre","")),
                _campo("Teléfono",    p.get("telefono","")),
                _campo("Email",       p.get("email","")),
                _campo("Obra social", p.get("obra_social","")),
            ], spacing=16),
            ft.Row(controls=[
                _campo("Dirección",     p.get("direccion","")),
                _campo("Alergias",      p.get("alergias","")),
                _campo("Nro. afiliado", p.get("nro_afiliado","")),
            ], spacing=16),
        ], spacing=10))

        # Antecedentes positivos
        positivos = [lbl for key, lbl in [
            ("tratamiento_medico","Trat. médico"),("medicamentos","Medicamentos"),
            ("alergias_med","Alergias med."),("cardiopatias","Cardiopatías"),
            ("presion_arterial_alt","Alt. tensión"),("embarazo","Embarazo"),
            ("diabetes","Diabetes"),("hepatitis","Hepatitis"),
            ("irradiaciones","Irradiaciones"),("discrasias","Discrasias"),
            ("fiebre_reumatica","Fiebre reumática"),("enf_renales","Enf. renales"),
            ("inmunosupresion","Inmunosupresión"),("trastornos_emocionales","Trast. emocional"),
            ("trastornos_respiratorios","Trast. respiratorio"),
            ("trastornos_gastricos","Trast. gástrico"),
            ("epilepsia","Epilepsia"),("cirugias","Cirugías"),
            ("enf_orales","Enf. orales"),("otras_alteraciones","Otras alt."),
            ("fuma_licor","Tabaquismo/Alcohol"),
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
            _titulo_sec("Anamnesis — Antecedentes positivos", ft.Icons.WARNING_AMBER),
            ant_chips,
        ], spacing=8))

        sv_cols = [
            ("Presión",   sv.get("tension_arterial","")),
            ("Pulso",     sv.get("pulso","")),
            ("Temp.",     sv.get("temperatura","")),
            ("F. Resp.",  sv.get("frecuencia_resp","")),
            ("Peso",      (sv.get("peso","") + " kg") if sv.get("peso") else "—"),
            ("Talla",     (sv.get("estatura","") + " cm") if sv.get("estatura") else "—"),
        ]
        cv = _card(ft.Column(controls=[
            _titulo_sec("Constantes Vitales", ft.Icons.MONITOR_HEART),
            ft.Row(controls=[_campo(l, v) for l, v in sv_cols], spacing=12),
        ], spacing=8))

        consulta = _card(ft.Column(controls=[
            _titulo_sec("Datos de la Consulta", ft.Icons.NOTES),
            ft.Row(controls=[
                _campo("N° Historia",  h.get("historia_no","")),
                _campo("Odontólogo",   h.get("odontologo","")),
                _campo("Fecha",        _fmt_fecha(h.get("fecha_elaboracion",""))),
            ], spacing=16),
            _campo("Motivo de consulta", h.get("motivo_consulta","")),
            _campo("Hallazgos / Enfermedad actual",
                   h.get("enfermedad_actual","")),
            _campo("Observaciones",  h.get("observaciones","")),
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
#  TAB 2 — Presupuestos (.xlsx)
# ═══════════════════════════════════════════════════════════════════════════

class _PresupuestosTab(ft.Column):
    def __init__(self):
        super().__init__(spacing=0, expand=True)
        self._dd_esp = ft.Dropdown(
            label="Especialista", value="",
            options=[ft.dropdown.Option("","(Todos)")],
            expand=True, dense=True,
        )
        self._dd_pac = ft.Dropdown(
            label="Paciente", value="",
            options=[ft.dropdown.Option("","(Todos)")],
            expand=True, dense=True,
        )
        self._tf_saldo = ft.TextField(
            label="Saldo mínimo ($)", value="0",
            hint_text="Ej: 500", dense=True,
            expand=True,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        self._area  = ft.Container(expand=True)
        self._datos: list[dict] = []
        self._construir_shell()

    def _construir_shell(self):
        filtros = ft.Container(
            content=ft.Column(controls=[
                ft.Row(controls=[
                    ft.Row(controls=[self._dd_esp], expand=3),
                    ft.Row(controls=[self._dd_pac], expand=3),
                    ft.Row(controls=[self._tf_saldo], expand=2),
                ], spacing=10),
                ft.Row(controls=[
                    _btn_azul("Aplicar filtros", ft.Icons.FILTER_ALT,
                               lambda _: self._cargar()),
                    ft.ElevatedButton(
                        "Exportar Excel (.xlsx)",
                        icon=ft.Icons.TABLE_CHART,
                        on_click=self._exportar,
                        style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_800,
                                              color=ft.Colors.WHITE),
                    ),
                ], spacing=10),
            ], spacing=8),
            padding=ft.padding.symmetric(horizontal=14, vertical=12),
            bgcolor=_GRIS_BG,
            border=ft.border.only(bottom=ft.BorderSide(1, _BORDE)),
        )
        self.controls = [filtros, self._area]

    def did_mount(self):
        try:
            esps = listar_especialistas()
            self._dd_esp.options = [ft.dropdown.Option("","(Todos)")] + [
                ft.dropdown.Option(e["id"],
                    f"{e.get('apellido','')} {e.get('nombre','')}".strip())
                for e in esps
            ]
            pacs = listar_pacientes()
            self._dd_pac.options = [ft.dropdown.Option("","(Todos)")] + [
                ft.dropdown.Option(p["id"],
                    f"{p.get('apellido','')} {p.get('nombre','')}".strip())
                for p in sorted(pacs, key=lambda x: x.get("apellido",""))
            ]
            if self.page:
                self._dd_esp.update()
                self._dd_pac.update()
        except Exception as ex:
            print(f"[Presupuestos] error cargando opciones: {ex}", flush=True)
        self._cargar()

    def _cargar(self):
        self._area.content = ft.Container(
            content=ft.ProgressRing(),
            alignment=ft.alignment.center, expand=True,
        )
        if self._area.page:
            self._area.update()

        try:
            saldo_min = float((self._tf_saldo.value or "0").replace(",","."))
        except Exception:
            saldo_min = 0.0

        filtros = {
            "especialista_id": self._dd_esp.value or None,
            "paciente_id":     self._dd_pac.value or None,
            "saldo_minimo":    saldo_min,
        }
        try:
            self._datos = obtener_datos_reporte_presupuestos(filtros)
        except Exception as ex:
            self._area.content = ft.Text(f"Error: {ex}",
                                          color=ft.Colors.RED_700)
            if self._area.page:
                self._area.update()
            return
        self._refrescar_tabla()

    def _refrescar_tabla(self):
        datos = self._datos
        if not datos:
            self._area.content = _sin_datos()
            if self._area.page:
                self._area.update()
            return

        columnas = [
            ("Paciente", 4), ("Descripción", 5), ("Diente", 1),
            ("Especialista", 3), ("Estado", 2),
            ("Costo", 2), ("Pagado", 2), ("Saldo", 2),
        ]
        filas = [_encabezado_tabla(columnas)]

        total_c = total_p = total_s = 0.0
        for i, t in enumerate(datos):
            pac = (t.get("pacientes") or {})
            esp = (t.get("especialistas") or {})
            nom_pac = f"{pac.get('apellido','')} {pac.get('nombre','')}".strip()
            nom_esp = f"{esp.get('apellido','')} {esp.get('nombre','')}".strip()
            estado  = t.get("estado","")
            bg, fg  = _COL_ESTADO_TRAT.get(estado, ("#EEE","#333"))
            costo   = float(t.get("costo", 0))
            pagado  = float(t.get("pagado", 0))
            saldo   = float(t.get("saldo", 0))
            total_c += costo; total_p += pagado; total_s += saldo

            saldo_txt = ft.Text(
                _fmt_monto(saldo), size=10,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.RED_700 if saldo > 0 else ft.Colors.GREEN_700,
            )
            filas.append(_fila_tabla([
                (nom_pac or "—", 4),
                (t.get("descripcion","") or "—", 5),
                (str(t.get("diente","")) if t.get("diente") else "—", 1),
                (nom_esp or "—", 3),
                (_badge(estado, bg, fg), 2),
                (_fmt_monto(costo), 2),
                (_fmt_monto(pagado), 2),
                (saldo_txt, 2),
            ], alt=i % 2 == 1))

        total_bar = ft.Container(
            content=ft.Row(controls=[
                ft.Text(f"{len(datos)} tratamientos",
                        size=11, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                ft.Text("Costo:", size=11),
                ft.Text(_fmt_monto(total_c), size=12,
                        weight=ft.FontWeight.BOLD, color=_AZUL),
                ft.Text("  Pagado:", size=11),
                ft.Text(_fmt_monto(total_p), size=12,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.GREEN_700),
                ft.Text("  Saldo:", size=11),
                ft.Text(_fmt_monto(total_s), size=12,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.RED_700 if total_s > 0
                              else ft.Colors.GREEN_700),
            ], spacing=8, wrap=False),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            bgcolor=_AZUL_BG,
            border=ft.border.only(top=ft.BorderSide(1, "#BBDEFB")),
        )

        self._area.content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Column(controls=filas, spacing=0),
                        expand=True,
                    ),
                    total_bar,
                ],
                spacing=0, expand=True, scroll=ft.ScrollMode.AUTO,
            ),
            expand=True,
        )
        if self._area.page:
            self._area.update()

    def _exportar(self, e=None):
        if not self._datos:
            if self.page:
                _snack(self.page, "Aplicá los filtros primero.", error=True)
            return
        try:
            from generar_archivos import generar_excel_presupuestos
            esp_val = self._dd_esp.value
            pac_val = self._dd_pac.value
            desc    = []
            if esp_val:
                desc.append(f"Especialista: {esp_val[:8]}")
            if pac_val:
                desc.append(f"Paciente: {pac_val[:8]}")
            sal = self._tf_saldo.value or "0"
            if sal != "0":
                desc.append(f"Saldo mín: ${sal}")

            ruta   = generar_excel_presupuestos(
                self._datos,
                filtros_desc="  |  ".join(desc),
                output_dir=_OUT_DIR,
            )
            nombre = os.path.basename(ruta)
            print(f"[XLSX-Presup] {ruta}", flush=True)
            if self.page:
                _dlg_ok(self.page, "Excel de Presupuestos generado",
                        f"Archivo: {nombre}")
        except Exception as ex:
            import traceback; traceback.print_exc()
            if self.page:
                _snack(self.page, f"Error: {ex}", error=True)


# ═══════════════════════════════════════════════════════════════════════════
#  TAB 3 — Agenda / Cronograma (.xlsx)
# ═══════════════════════════════════════════════════════════════════════════

class _AgendaTab(ft.Column):
    def __init__(self):
        super().__init__(spacing=0, expand=True)
        self._dd_esp = ft.Dropdown(
            label="Especialista", value="",
            options=[ft.dropdown.Option("","(Todos)")],
            expand=True, dense=True,
        )
        self._dd_per = ft.Dropdown(
            label="Período", value="semana",
            options=[
                ft.dropdown.Option("semana",    "Próxima semana (7 días)"),
                ft.dropdown.Option("quincena",  "Próxima quincena (15 días)"),
                ft.dropdown.Option("mes",       "Próximo mes (30 días)"),
            ],
            expand=True, dense=True,
        )
        self._area  = ft.Container(expand=True)
        self._datos: list[dict] = []
        self._esp_nombre: str   = ""
        self._construir_shell()

    def _construir_shell(self):
        filtros = ft.Container(
            content=ft.Row(controls=[
                ft.Row(controls=[self._dd_esp], expand=4),
                ft.Row(controls=[self._dd_per], expand=3),
                _btn_azul("Ver cronograma", ft.Icons.CALENDAR_VIEW_WEEK,
                           lambda _: self._cargar()),
                ft.ElevatedButton(
                    "Exportar Excel (.xlsx)",
                    icon=ft.Icons.TABLE_CHART,
                    on_click=self._exportar,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_800,
                                          color=ft.Colors.WHITE),
                ),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.END),
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            bgcolor=_GRIS_BG,
            border=ft.border.only(bottom=ft.BorderSide(1, _BORDE)),
        )
        self.controls = [filtros, self._area]

    def did_mount(self):
        try:
            esps = listar_especialistas()
            self._dd_esp.options = [ft.dropdown.Option("","(Todos)")] + [
                ft.dropdown.Option(e["id"],
                    f"{e.get('apellido','')} {e.get('nombre','')}".strip())
                for e in esps
            ]
            if self._dd_esp.page:
                self._dd_esp.update()
        except Exception as ex:
            print(f"[Agenda-Tab] error: {ex}", flush=True)
        self._cargar()

    def _cargar(self):
        self._area.content = ft.Container(
            content=ft.ProgressRing(),
            alignment=ft.alignment.center, expand=True,
        )
        if self._area.page:
            self._area.update()

        esp_id  = self._dd_esp.value or None
        periodo = self._dd_per.value or "semana"

        # Guardar nombre del especialista para el Excel
        if esp_id:
            for opt in self._dd_esp.options:
                if opt.key == esp_id:
                    self._esp_nombre = opt.text or ""
                    break
        else:
            self._esp_nombre = ""

        try:
            self._datos = obtener_datos_citas(
                especialista_id=esp_id,
                periodo=periodo,
            )
        except Exception as ex:
            self._area.content = ft.Text(f"Error: {ex}",
                                          color=ft.Colors.RED_700)
            if self._area.page:
                self._area.update()
            return
        self._refrescar_tabla()

    def _refrescar_tabla(self):
        datos   = self._datos
        periodo = self._dd_per.value or "semana"
        PERIODOS = {"semana":"7 días","quincena":"15 días","mes":"30 días"}
        periodo_txt = PERIODOS.get(periodo, periodo)

        # Barra de info
        info_bar = ft.Container(
            content=ft.Row(controls=[
                ft.Icon(ft.Icons.INFO_OUTLINE, size=14, color=_AZUL),
                ft.Text(
                    f"{len(datos)} cita(s) para los próximos {periodo_txt}"
                    + (f" — {self._esp_nombre}" if self._esp_nombre else ""),
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

        DIAS_ES = {0:"Lun",1:"Mar",2:"Mié",3:"Jue",4:"Vie",5:"Sáb",6:"Dom"}
        columnas = [
            ("Fecha", 2), ("Día", 1), ("Hora", 1), ("Paciente", 4),
            ("Teléfono", 2), ("Especialista", 3), ("Motivo", 4), ("Estado", 2),
        ]
        filas = [_encabezado_tabla(columnas)]

        est_count: dict[str, int] = {}
        for i, c in enumerate(datos):
            pac    = (c.get("pacientes") or {})
            esp    = (c.get("especialistas") or {})
            nom_pac = f"{pac.get('apellido','')} {pac.get('nombre','')}".strip()
            nom_esp = f"{esp.get('apellido','')} {esp.get('nombre','')}".strip()
            estado  = c.get("estado","")
            bg, fg  = _COL_ESTADO_CITA.get(estado, ("#EEE","#333"))
            est_count[estado] = est_count.get(estado, 0) + 1
            iso = c.get("fecha_hora","")
            try:
                dt  = datetime.datetime.fromisoformat(iso.replace("Z","+00:00"))
                fecha = dt.strftime("%d/%m/%Y")
                dia   = DIAS_ES.get(dt.weekday(), "")
                hora  = dt.strftime("%H:%M")
            except Exception:
                fecha = iso[:10]; dia = ""; hora = ""

            filas.append(_fila_tabla([
                (fecha, 2), (dia, 1), (hora, 1),
                (nom_pac or "—", 4),
                (pac.get("telefono","") or "—", 2),
                (nom_esp or "—", 3),
                (c.get("motivo","") or "—", 4),
                (_badge(estado, bg, fg), 2),
            ], alt=i % 2 == 1))

        total_bar = ft.Container(
            content=ft.Row(controls=[
                ft.Text(f"Total: {len(datos)} citas", size=11,
                        weight=ft.FontWeight.BOLD),
                *[_badge(f"{n} {est}",
                         *_COL_ESTADO_CITA.get(est, ("#EEE","#333")))
                  for est, n in sorted(est_count.items())],
            ], spacing=10, wrap=True),
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            bgcolor=_AZUL_BG,
            border=ft.border.only(top=ft.BorderSide(1, "#BBDEFB")),
        )

        self._area.content = ft.Column(
            controls=[
                info_bar,
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Container(
                                content=ft.Column(controls=filas, spacing=0),
                                expand=True,
                            ),
                            total_bar,
                        ],
                        spacing=0, expand=True, scroll=ft.ScrollMode.AUTO,
                    ),
                    expand=True,
                ),
            ],
            spacing=0, expand=True,
        )
        if self._area.page:
            self._area.update()

    def _exportar(self, e=None):
        if not self._datos:
            if self.page:
                _snack(self.page, "Cargá el cronograma primero.", error=True)
            return
        try:
            from generar_archivos import generar_excel_agenda
            ruta   = generar_excel_agenda(
                self._datos,
                especialista_nombre=self._esp_nombre,
                periodo=self._dd_per.value or "semana",
                output_dir=_OUT_DIR,
            )
            nombre = os.path.basename(ruta)
            print(f"[XLSX-Agenda] {ruta}", flush=True)
            if self.page:
                _dlg_ok(self.page, "Excel de Agenda generado",
                        f"Archivo: {nombre}")
        except Exception as ex:
            import traceback; traceback.print_exc()
            if self.page:
                _snack(self.page, f"Error: {ex}", error=True)


# ═══════════════════════════════════════════════════════════════════════════
#  Vista principal: ReportesView
# ═══════════════════════════════════════════════════════════════════════════

_TABS = [
    ("Historia Clínica", ft.Icons.ARTICLE,         _HistoriaClinicaTab),
    ("Presupuestos",     ft.Icons.REQUEST_QUOTE,    _PresupuestosTab),
    ("Agenda",           ft.Icons.CALENDAR_VIEW_WEEK, _AgendaTab),
]


class ReportesView(ft.Column):
    def __init__(self):
        super().__init__(spacing=0, expand=True)
        self._tab      = 0
        self._area     = ft.Container(expand=True)
        self._tab_btns: list[ft.ElevatedButton] = []
        self._construir()

    def _construir(self):
        for i, (lbl, icn, _cls) in enumerate(_TABS):
            idx = i
            btn = ft.ElevatedButton(
                lbl, icon=icn,
                on_click=lambda _, x=idx: self._sel(x),
                style=ft.ButtonStyle(
                    bgcolor=_AZUL if i == 0 else ft.Colors.WHITE,
                    color=ft.Colors.WHITE if i == 0 else "#212121",
                ),
            )
            self._tab_btns.append(btn)

        barra_tabs = ft.Container(
            content=ft.Row(controls=self._tab_btns, spacing=6),
            padding=ft.padding.symmetric(horizontal=14, vertical=8),
            bgcolor="#FAFAFA",
            border=ft.border.only(bottom=ft.BorderSide(1, _BORDE)),
        )

        self.controls = [
            _titulo_mod("Reportes ORTHOCLINIC — Documentos y Exportaciones"),
            barra_tabs,
            self._area,
        ]

    def did_mount(self):
        self._cargar_vista()

    def _sel(self, idx: int):
        self._tab = idx
        for i, btn in enumerate(self._tab_btns):
            btn.style = ft.ButtonStyle(
                bgcolor=_AZUL if i == idx else ft.Colors.WHITE,
                color=ft.Colors.WHITE if i == idx else "#212121",
            )
            if btn.page:
                btn.update()
        self._cargar_vista()

    def _cargar_vista(self):
        _cls  = _TABS[self._tab][2]
        vista = _cls()
        self._area.content = vista
        if self._area.page:
            self._area.update()
