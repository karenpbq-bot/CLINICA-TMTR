"""
Módulo de Pacientes — Historia Clínica Odontológica completa.
Incluye: selector de paciente, información general, anamnesis,
signos vitales, antecedentes, odontograma diagnóstico y observaciones.
"""

import datetime
import flet as ft
from database import (
    listar_pacientes,
    obtener_historia_clinica,
    guardar_historia_clinica,
    obtener_odontograma,
    guardar_diente,
    actualizar_diagnostico_dental,
)

# ── Constantes del odontograma ─────────────────────────────────────────────

ESTADOS_DIENTE = {
    "sano":       {"color": "#FFFFFF", "borde": "#BDBDBD", "label": "Sano"},
    "caries":     {"color": "#EF9A9A", "borde": "#C62828", "label": "Caries"},
    "obturado":   {"color": "#90CAF9", "borde": "#1565C0", "label": "Obturado"},
    "fractura":   {"color": "#FFCC80", "borde": "#E65100", "label": "Fractura"},
    "extraccion": {"color": "#CE93D8", "borde": "#6A1B9A", "label": "Extracción"},
    "corona":     {"color": "#FFF176", "borde": "#F9A825", "label": "Corona"},
    "implante":   {"color": "#A5D6A7", "borde": "#2E7D32", "label": "Implante"},
    "ausente":    {"color": "#EEEEEE", "borde": "#757575", "label": "Ausente"},
}
CARAS = ["oclusal", "vestibular", "lingual", "mesial", "distal"]
DIENTES_ADULTO = [
    [18, 17, 16, 15, 14, 13, 12, 11, 21, 22, 23, 24, 25, 26, 27, 28],
    [48, 47, 46, 45, 44, 43, 42, 41, 31, 32, 33, 34, 35, 36, 37, 38],
]

# ── Constantes del formulario ──────────────────────────────────────────────

ANTECEDENTES = [
    ("tratamiento_medico",       "1. Tratamiento médico actual"),
    ("medicamentos",             "2. Toma de medicamentos"),
    ("alergias",                 "3. Alergias"),
    ("cardiopatias",             "4. Cardiopatías"),
    ("presion_arterial",         "5. Alteración presión arterial"),
    ("embarazo",                 "6. Embarazo"),
    ("diabetes",                 "7. Diabetes"),
    ("hepatitis",                "8. Hepatitis"),
    ("irradiaciones",            "9. Irradiaciones"),
    ("discrasias",               "10. Discrasias sanguíneas"),
    ("fiebre_reumatica",         "11. Fiebre reumática"),
    ("enf_renales",              "12. Enfermedades renales"),
    ("inmunosupresion",          "13. Inmunosupresión"),
    ("trastornos_emocionales",   "14. Trastornos emocionales"),
    ("trastornos_respiratorios", "15. Trastornos respiratorios"),
    ("trastornos_gastricos",     "16. Trastornos gástricos"),
    ("epilepsia",                "17. Epilepsia"),
    ("cirugias",                 "18. Cirugías (incluye orales)"),
    ("enf_orales",               "19. Enfermedades orales"),
    ("otras_alteraciones",       "20. Otras alteraciones"),
    ("fuma_licor",               "21. Fuma o consume licor"),
]

VIH_OPTIONS = ["Negativo", "Positivo", "No informado"]


def _posicion_diente(numero: int) -> str:
    if 11 <= numero <= 18:
        return "Superior Derecho"
    if 21 <= numero <= 28:
        return "Superior Izquierdo"
    if 31 <= numero <= 38:
        return "Inferior Izquierdo"
    if 41 <= numero <= 48:
        return "Inferior Derecho"
    return ""


def _seccion(titulo: str, icono: str) -> ft.Container:
    return ft.Container(
        content=ft.Row(controls=[
            ft.Icon(icono, size=18, color="#FFFFFF"),
            ft.Text(titulo, size=13, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
        ], spacing=8),
        bgcolor="#1565C0", border_radius=6,
        padding=ft.padding.symmetric(horizontal=14, vertical=8),
        margin=ft.margin.only(top=10, bottom=4),
    )


# ── Widget de diente para la cuadrícula ───────────────────────────────────

class _DienteDiag(ft.Column):
    def __init__(self, numero: int, caras_estado: dict,
                 tiene_diagnostico: bool, on_select):
        super().__init__(
            spacing=1,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.numero            = numero
        self.caras_estado      = {c: caras_estado.get(c, "sano") for c in CARAS}
        self.tiene_diagnostico = tiene_diagnostico
        self.on_select         = on_select
        self._contenedores: dict[str, ft.Container] = {}
        self._lbl = ft.Text(str(numero), size=7,
                            text_align=ft.TextAlign.CENTER, color="#616161")
        self._ind = ft.Container(
            width=10, height=3, border_radius=1,
            bgcolor="#1565C0" if tiene_diagnostico else "transparent",
        )
        self._construir()

    def _celda(self, cara: str) -> ft.Container:
        estado = self.caras_estado[cara]
        cfg    = ESTADOS_DIENTE[estado]
        c = ft.Container(
            width=11, height=11,
            bgcolor=cfg["color"],
            border=ft.border.all(1, cfg["borde"]),
            border_radius=1,
            tooltip=f"{cara.capitalize()}: {cfg['label']}",
            on_click=lambda e: self.on_select(self.numero),
        )
        self._contenedores[cara] = c
        return c

    def actualizar(self, caras_estado: dict, tiene_diagnostico: bool):
        self.caras_estado      = {c: caras_estado.get(c, "sano") for c in CARAS}
        self.tiene_diagnostico = tiene_diagnostico
        for cara, cont in self._contenedores.items():
            cfg = ESTADOS_DIENTE[self.caras_estado[cara]]
            cont.bgcolor = cfg["color"]
            cont.border  = ft.border.all(1, cfg["borde"])
            cont.tooltip = f"{cara.capitalize()}: {cfg['label']}"
            if cont.page:
                cont.update()
        self._ind.bgcolor = "#1565C0" if tiene_diagnostico else "transparent"
        if self._ind.page:
            self._ind.update()

    def _construir(self):
        self.controls = [
            self._celda("vestibular"),
            ft.Row(controls=[
                self._celda("mesial"),
                self._celda("oclusal"),
                self._celda("distal"),
            ], spacing=1),
            self._celda("lingual"),
            self._lbl,
            self._ind,
        ]


# ── Panel de detalle para una pieza ──────────────────────────────────────

class _DetalleDiente(ft.Column):
    def __init__(self, numero: int, caras_estado: dict,
                 diagnostico: str, on_guardar):
        super().__init__(spacing=10, expand=True, scroll=ft.ScrollMode.AUTO)
        self.numero       = numero
        self.caras_estado = {c: caras_estado.get(c, "sano") for c in CARAS}
        self.on_guardar   = on_guardar
        self._contenedores: dict[str, ft.Container] = {}

        self.tf_diagnostico = ft.TextField(
            label="Diagnóstico / Zona a intervenir",
            value=diagnostico,
            multiline=True,
            min_lines=3,
            expand=True,
        )
        self._estado_resumen = ft.Column(spacing=4)
        self._construir()

    def _celda_grande(self, cara: str) -> ft.Container:
        estado = self.caras_estado[cara]
        cfg    = ESTADOS_DIENTE[estado]
        c = ft.Container(
            width=38, height=38,
            bgcolor=cfg["color"],
            border=ft.border.all(2, cfg["borde"]),
            border_radius=5,
            tooltip=f"Clic para cambiar — {cara.capitalize()}: {cfg['label']}",
            on_click=lambda e, ca=cara: self._ciclar(ca),
            content=ft.Text(
                cara[:3].upper(), size=7.5,
                text_align=ft.TextAlign.CENTER,
                weight=ft.FontWeight.W_600,
                color="#1A1A1A",
            ),
            alignment=ft.Alignment(0, 0),
        )
        self._contenedores[cara] = c
        return c

    def _ciclar(self, cara: str):
        estados = list(ESTADOS_DIENTE.keys())
        sig = estados[(estados.index(self.caras_estado[cara]) + 1) % len(estados)]
        self.caras_estado[cara] = sig
        cfg = ESTADOS_DIENTE[sig]
        c   = self._contenedores[cara]
        c.bgcolor = cfg["color"]
        c.border  = ft.border.all(2, cfg["borde"])
        c.tooltip = f"Clic para cambiar — {cara.capitalize()}: {cfg['label']}"
        if c.page:
            c.update()
        self._refrescar_resumen()

    def _refrescar_resumen(self):
        self._estado_resumen.controls = [
            ft.Container(
                content=ft.Row(controls=[
                    ft.Container(
                        width=10, height=10,
                        bgcolor=ESTADOS_DIENTE[st]["color"],
                        border=ft.border.all(1, ESTADOS_DIENTE[st]["borde"]),
                        border_radius=2,
                    ),
                    ft.Text(f"{cara.capitalize()}: {ESTADOS_DIENTE[st]['label']}", size=11),
                ], spacing=5),
                padding=ft.padding.symmetric(horizontal=6, vertical=2),
                border=ft.border.all(1, "#E0E0E0"),
                border_radius=4,
            )
            for cara, st in self.caras_estado.items()
        ]
        if self._estado_resumen.page:
            self._estado_resumen.update()

    def _guardar(self, e):
        self.on_guardar(
            self.numero,
            dict(self.caras_estado),
            self.tf_diagnostico.value.strip(),
        )

    def _construir(self):
        self._refrescar_resumen()
        superficie = ft.Column(controls=[
            ft.Row(controls=[self._celda_grande("vestibular")],
                   alignment=ft.MainAxisAlignment.CENTER),
            ft.Row(controls=[
                self._celda_grande("mesial"),
                self._celda_grande("oclusal"),
                self._celda_grande("distal"),
            ], spacing=6, alignment=ft.MainAxisAlignment.CENTER),
            ft.Row(controls=[self._celda_grande("lingual")],
                   alignment=ft.MainAxisAlignment.CENTER),
        ], spacing=6, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

        self.controls = [
            ft.Container(
                content=ft.Row(controls=[
                    ft.Icon(ft.Icons.MEDICAL_SERVICES, color="#1565C0", size=22),
                    ft.Column(controls=[
                        ft.Text(f"Pieza {self.numero}",
                                size=16, weight=ft.FontWeight.BOLD),
                        ft.Text(_posicion_diente(self.numero),
                                size=11, color="#757575"),
                    ], spacing=2),
                ], spacing=10),
                bgcolor="#E3F2FD", border_radius=6,
                padding=ft.padding.symmetric(horizontal=12, vertical=8),
            ),
            ft.Divider(height=4),
            ft.Text("Superficies — clic para cambiar estado:",
                    size=12, weight=ft.FontWeight.W_500),
            ft.Container(
                content=superficie,
                border=ft.border.all(1, "#BBDEFB"),
                border_radius=6, padding=12, bgcolor="#FAFAFA",
            ),
            ft.Text("Estado por superficie:", size=11, color="#616161"),
            self._estado_resumen,
            ft.Divider(height=4),
            self.tf_diagnostico,
            ft.FilledButton("Guardar pieza", icon=ft.Icons.SAVE,
                            on_click=self._guardar),
        ]


# ── Odontograma con diagnóstico ───────────────────────────────────────────

class OdontogramaDiagnosticoView(ft.Column):
    def __init__(self, paciente_id: str,
                 diagnostico_dental: dict | None = None,
                 snack_fn=None):
        super().__init__(spacing=6, expand=True)
        self.paciente_id  = paciente_id
        self.diagnosticos = dict(diagnostico_dental or {})
        self.snack_fn     = snack_fn

        self._datos_odonto: dict[int, dict]    = {}
        self._diente_sel: int | None           = None
        self._widgets: dict[int, _DienteDiag] = {}

        self._fila_sup = ft.Row(spacing=3, wrap=False)
        self._fila_inf = ft.Row(spacing=3, wrap=False)
        self._panel    = ft.Container(
            expand=True,
            border=ft.border.all(1, "#E0E0E0"),
            border_radius=6, padding=12,
            content=ft.Column(controls=[
                ft.Icon(ft.Icons.TOUCH_APP, size=32, color="#BDBDBD"),
                ft.Text("Seleccioná una pieza dental",
                        color="#9E9E9E", italic=True, size=13),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
               alignment=ft.MainAxisAlignment.CENTER,
               expand=True),
        )
        self._construir_layout()

    def did_mount(self):
        try:
            filas = obtener_odontograma(self.paciente_id)
            self._datos_odonto = {r["diente"]: r.get("caras", {}) for r in filas}
        except Exception:
            self._datos_odonto = {}
        self._poblar_filas()
        self.update()

    def _poblar_filas(self):
        def build(nums):
            widgets = []
            for n in nums:
                caras = self._datos_odonto.get(n, {c: "sano" for c in CARAS})
                tiene = bool(self.diagnosticos.get(str(n), "").strip())
                w = _DienteDiag(n, caras, tiene, self._on_seleccionar)
                self._widgets[n] = w
                widgets.append(w)
            return widgets
        self._fila_sup.controls = build(DIENTES_ADULTO[0])
        self._fila_inf.controls = build(DIENTES_ADULTO[1])

    def _on_seleccionar(self, numero: int):
        self._diente_sel = numero
        self._actualizar_panel()

    def _actualizar_panel(self):
        n = self._diente_sel
        if n is None:
            return
        caras = self._datos_odonto.get(n, {c: "sano" for c in CARAS})
        diag  = self.diagnosticos.get(str(n), "")
        self._panel.content = _DetalleDiente(
            numero=n, caras_estado=caras,
            diagnostico=diag, on_guardar=self._guardar_pieza,
        )
        if self._panel.page:
            self._panel.update()

    def _guardar_pieza(self, numero: int, caras: dict, diagnostico: str):
        try:
            guardar_diente(self.paciente_id, numero, caras)
            self._datos_odonto[numero] = caras
        except Exception as ex:
            if self.snack_fn:
                self.snack_fn(f"Error guardando superficies: {ex}", error=True)
            return
        self.diagnosticos[str(numero)] = diagnostico
        try:
            actualizar_diagnostico_dental(self.paciente_id, self.diagnosticos)
        except Exception as ex:
            if self.snack_fn:
                self.snack_fn(f"Error guardando diagnóstico: {ex}", error=True)
            return
        if numero in self._widgets:
            self._widgets[numero].actualizar(caras, bool(diagnostico.strip()))
        if self.snack_fn:
            self.snack_fn(f"Pieza {numero} guardada correctamente.")

    def _leyenda(self) -> ft.Row:
        return ft.Row(controls=[
            ft.Row(controls=[
                ft.Container(width=11, height=11, bgcolor=v["color"],
                             border=ft.border.all(1, v["borde"]),
                             border_radius=2),
                ft.Text(v["label"], size=10),
            ], spacing=3)
            for v in ESTADOS_DIENTE.values()
        ], wrap=True, spacing=10)

    def _construir_layout(self):
        cuadricula = ft.Container(
            content=ft.Column(controls=[
                ft.Row(controls=[
                    ft.Icon(ft.Icons.ARROW_UPWARD, size=12, color="#757575"),
                    ft.Text("SUPERIOR  (18 → 11 | 21 → 28)",
                            size=10, color="#616161"),
                ], spacing=4),
                ft.Container(
                    content=self._fila_sup,
                    bgcolor="#F5F9FF",
                    border=ft.border.all(1, "#BBDEFB"),
                    border_radius=4, padding=6,
                ),
                ft.Divider(height=4),
                ft.Row(controls=[
                    ft.Icon(ft.Icons.ARROW_DOWNWARD, size=12, color="#757575"),
                    ft.Text("INFERIOR  (48 → 41 | 31 → 38)",
                            size=10, color="#616161"),
                ], spacing=4),
                ft.Container(
                    content=self._fila_inf,
                    bgcolor="#F5FFF5",
                    border=ft.border.all(1, "#C8E6C9"),
                    border_radius=4, padding=6,
                ),
                ft.Divider(height=6),
                ft.Text("Leyenda (clic en superficie del panel derecho):",
                        size=10, color="#757575"),
                self._leyenda(),
                ft.Container(height=4),
                ft.Row(controls=[
                    ft.Container(width=10, height=10,
                                 bgcolor="#1565C0", border_radius=2),
                    ft.Text("= tiene diagnóstico registrado",
                            size=10, color="#424242"),
                ], spacing=5),
            ], spacing=6),
            border=ft.border.all(1, "#E0E0E0"),
            border_radius=6, padding=10,
        )
        self.controls = [
            ft.Row(controls=[cuadricula, self._panel], spacing=12,
                   expand=True,
                   vertical_alignment=ft.CrossAxisAlignment.START),
        ]


# ── Historia Clínica completa para un paciente ─────────────────────────────

class HistoriaClinicaView(ft.Column):
    """
    Formulario completo de Historia Clínica Odontológica.
    Se instancia con un paciente_id específico.
    """

    def __init__(self, paciente_id: str, snack_fn=None):
        super().__init__(spacing=6, expand=True, scroll=ft.ScrollMode.AUTO)
        self.paciente_id = paciente_id
        self.snack_fn    = snack_fn
        self._historia   = {}
        self._cb_map: dict[str, ft.Checkbox] = {}
        self._odontograma_view: OdontogramaDiagnosticoView | None = None
        self._construir()

    def _snack(self, msg: str, error: bool = False):
        if self.snack_fn:
            self.snack_fn(msg, error)
        elif self.page:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(msg),
                bgcolor=ft.Colors.RED_700 if error else ft.Colors.GREEN_700,
                open=True,
            )
            self.page.update()

    def _tf(self, label: str, value: str = "", width=None,
            multiline=False, min_lines=1, expand=False) -> ft.TextField:
        return ft.TextField(
            label=label, value=value or "",
            multiline=multiline, min_lines=min_lines,
            width=width, expand=expand, dense=True,
        )

    def _construir(self):
        try:
            self._historia = obtener_historia_clinica(self.paciente_id) or {}
        except Exception:
            self._historia = {}

        h   = self._historia
        sv  = h.get("signos_vitales") or {}
        ant = h.get("antecedentes") or {}
        dd  = h.get("diagnostico_dental") or {}

        fecha_hoy = str(h.get("fecha_elaboracion") or datetime.date.today())[:10]

        self.tf_historia_no = self._tf("N° Historia", h.get("historia_no",""), width=160)
        self.tf_odontologo  = self._tf("Odontólogo responsable", h.get("odontologo",""), expand=True)
        self.tf_fecha       = self._tf("Fecha", fecha_hoy, width=140)
        self.tf_motivo      = self._tf("Motivo de consulta",
                                       h.get("motivo_consulta",""),
                                       multiline=True, min_lines=2, expand=True)
        self.tf_enfermedad  = self._tf("Enfermedad actual",
                                       h.get("enfermedad_actual",""),
                                       multiline=True, min_lines=2, expand=True)
        self.tf_estatura    = self._tf("Estatura (cm)", sv.get("estatura",""), width=120)
        self.tf_peso        = self._tf("Peso (kg)",     sv.get("peso",""),     width=110)
        self.tf_temp        = self._tf("Temp. (°C)",    sv.get("temperatura",""), width=110)
        self.tf_pulso       = self._tf("Pulso (bpm)",   sv.get("pulso",""),    width=110)
        self.tf_tension     = self._tf("T.A. (mmHg)",   sv.get("tension_arterial",""), width=120)
        self.tf_fr          = self._tf("F.R. (rpm)",    sv.get("frecuencia_resp",""),  width=110)
        self.dd_vih         = ft.Dropdown(
            label="VIH",
            value=sv.get("vih", "Negativo"),
            options=[ft.dropdown.Option(o) for o in VIH_OPTIONS],
            width=150, dense=True,
        )

        self._cb_map = {}
        for key, _ in ANTECEDENTES:
            self._cb_map[key] = ft.Checkbox(value=bool(ant.get(key, False)), label="")

        mitad   = (len(ANTECEDENTES) + 1) // 2
        col_izq = ft.Column(spacing=2)
        col_der = ft.Column(spacing=2)
        for i, (key, label) in enumerate(ANTECEDENTES):
            fila = ft.Row(controls=[
                self._cb_map[key],
                ft.Text(label, size=12, expand=True),
            ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            (col_izq if i < mitad else col_der).controls.append(fila)

        self._odontograma_view = OdontogramaDiagnosticoView(
            paciente_id=self.paciente_id,
            diagnostico_dental=dd,
            snack_fn=self._snack,
        )

        self.tf_observaciones = self._tf(
            "Observaciones y notas adicionales",
            h.get("observaciones",""),
            multiline=True, min_lines=3, expand=True,
        )

        existe  = bool(h.get("id"))
        lbl_btn = "Actualizar Historia Clínica" if existe else "Guardar Historia Clínica"

        self.controls = [
            ft.Container(
                content=ft.Row(controls=[
                    ft.Icon(ft.Icons.MEDICAL_INFORMATION, size=22, color="#1565C0"),
                    ft.Text("Historia Clínica Odontológica",
                            size=17, weight=ft.FontWeight.BOLD, color="#1565C0"),
                ], spacing=10),
                padding=ft.padding.only(bottom=4),
            ),
            _seccion("1. INFORMACIÓN GENERAL", ft.Icons.INFO_OUTLINE),
            ft.Row(controls=[
                self.tf_historia_no, self.tf_odontologo, self.tf_fecha,
            ], spacing=10, wrap=True),
            _seccion("2. ANAMNESIS", ft.Icons.NOTES),
            self.tf_motivo,
            self.tf_enfermedad,
            _seccion("3. SIGNOS VITALES", ft.Icons.MONITOR_HEART),
            ft.Row(controls=[
                self.tf_estatura, self.tf_peso, self.tf_temp,
                self.tf_pulso, self.tf_tension, self.tf_fr, self.dd_vih,
            ], spacing=8, wrap=True),
            _seccion("4. ANTECEDENTES MÉDICOS Y ODONTOLÓGICOS",
                     ft.Icons.HEALTH_AND_SAFETY),
            ft.Container(
                content=ft.Row(controls=[
                    ft.Container(content=col_izq, expand=True),
                    ft.VerticalDivider(width=1, color="#E0E0E0"),
                    ft.Container(content=col_der, expand=True),
                ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.START),
                border=ft.border.all(1, "#E0E0E0"),
                border_radius=6, padding=10,
            ),
            _seccion("5. ODONTOGRAMA Y DIAGNÓSTICO POR PIEZA",
                     ft.Icons.MEDICAL_SERVICES),
            ft.Text(
                "Clic en un diente → marcá las superficies y escribí el diagnóstico → "
                "«Guardar pieza». Indicador azul = pieza con diagnóstico.",
                size=11, color="#616161", italic=True,
            ),
            ft.Container(
                content=self._odontograma_view,
                border=ft.border.all(1, "#E0E0E0"),
                border_radius=6, padding=8,
                height=420,
            ),
            _seccion("6. OBSERVACIONES", ft.Icons.EDIT_NOTE),
            self.tf_observaciones,
            ft.Container(
                content=ft.FilledButton(lbl_btn, icon=ft.Icons.SAVE,
                                        on_click=self._guardar),
                padding=ft.padding.symmetric(vertical=10),
            ),
        ]

    def _guardar(self, e):
        signos_vitales = {
            "estatura":         self.tf_estatura.value.strip(),
            "peso":             self.tf_peso.value.strip(),
            "temperatura":      self.tf_temp.value.strip(),
            "pulso":            self.tf_pulso.value.strip(),
            "tension_arterial": self.tf_tension.value.strip(),
            "frecuencia_resp":  self.tf_fr.value.strip(),
            "vih":              self.dd_vih.value or "Negativo",
        }
        antecedentes = {key: self._cb_map[key].value for key, _ in ANTECEDENTES}
        diagnostico_dental = (
            self._odontograma_view.diagnosticos if self._odontograma_view else {}
        )
        datos = {
            "historia_no":        self.tf_historia_no.value.strip(),
            "odontologo":         self.tf_odontologo.value.strip(),
            "fecha_elaboracion":  self.tf_fecha.value.strip() or str(datetime.date.today()),
            "motivo_consulta":    self.tf_motivo.value.strip(),
            "enfermedad_actual":  self.tf_enfermedad.value.strip(),
            "signos_vitales":     signos_vitales,
            "antecedentes":       antecedentes,
            "diagnostico_dental": diagnostico_dental,
            "observaciones":      self.tf_observaciones.value.strip(),
        }
        try:
            guardar_historia_clinica(self.paciente_id, datos)
            self._snack("Historia Clínica guardada correctamente.")
        except Exception as ex:
            self._snack(f"Error al guardar: {ex}", error=True)


# ── Vista principal del módulo Pacientes ──────────────────────────────────

class PacientesView(ft.Column):
    """
    Módulo principal de Pacientes.
    Muestra un selector de paciente y carga su Historia Clínica completa.
    """

    def __init__(self):
        super().__init__(spacing=0, expand=True)
        self.paciente_id: str | None = None
        self._area = ft.Container(
            expand=True,
            padding=ft.padding.all(16),
            content=ft.Column(controls=[
                ft.Icon(ft.Icons.PERSON_SEARCH, size=48, color="#BDBDBD"),
                ft.Text("Seleccioná un paciente para ver su Historia Clínica",
                        color="#9E9E9E", size=14, italic=True),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
               alignment=ft.MainAxisAlignment.CENTER,
               expand=True),
        )
        self._construir()

    def _construir(self):
        try:
            pacientes = listar_pacientes()
        except Exception:
            pacientes = []

        self.dd_selector = ft.Dropdown(
            label="Seleccionar paciente",
            hint_text="Elegí un paciente de la lista...",
            options=[
                ft.dropdown.Option(
                    p["id"],
                    f"{p.get('apellido','–')}, {p.get('nombre','')}",
                )
                for p in sorted(pacientes,
                                 key=lambda x: x.get("apellido",""))
            ],
            on_select=self._on_selector,
            width=420,
        )

        self.controls = [
            ft.Container(
                content=ft.Column(controls=[
                    ft.Text("Historia Clínica de Pacientes",
                            size=18, weight=ft.FontWeight.BOLD),
                    self.dd_selector,
                ], spacing=10),
                padding=ft.padding.symmetric(horizontal=16, vertical=12),
            ),
            ft.Divider(height=1, color="#E0E0E0"),
            self._area,
        ]

    def _on_selector(self, e):
        pid = self.dd_selector.value
        if not pid:
            return
        self.paciente_id = pid
        self._area.content = HistoriaClinicaView(
            paciente_id=pid,
            snack_fn=self._snack,
        )
        if self._area.page:
            self._area.update()

    def _snack(self, msg: str, error: bool = False):
        if self.page:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(msg),
                bgcolor=ft.Colors.RED_700 if error else ft.Colors.GREEN_700,
                open=True,
            )
            self.page.update()
