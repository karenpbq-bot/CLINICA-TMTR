"""
Módulo de Historia Clínica Odontológica.
Basado en ficha clínica estándar: información general, anamnesis,
signos vitales, antecedentes médicos y observaciones.
"""

import datetime
import flet as ft
from database import obtener_historia_clinica, guardar_historia_clinica

ANTECEDENTES = [
    ("tratamiento_medico",      "1. Tratamiento médico actual"),
    ("medicamentos",            "2. Toma de medicamentos"),
    ("alergias",                "3. Alergias"),
    ("cardiopatias",            "4. Cardiopatías"),
    ("presion_arterial",        "5. Alteración presión arterial"),
    ("embarazo",                "6. Embarazo"),
    ("diabetes",                "7. Diabetes"),
    ("hepatitis",               "8. Hepatitis"),
    ("irradiaciones",           "9. Irradiaciones"),
    ("discrasias",              "10. Discrasias sanguíneas"),
    ("fiebre_reumatica",        "11. Fiebre reumática"),
    ("enf_renales",             "12. Enfermedades renales"),
    ("inmunosupresion",         "13. Inmunosupresión"),
    ("trastornos_emocionales",  "14. Trastornos emocionales"),
    ("trastornos_respiratorios","15. Trastornos respiratorios"),
    ("trastornos_gastricos",    "16. Trastornos gástricos"),
    ("epilepsia",               "17. Epilepsia"),
    ("cirugias",                "18. Cirugías (incluye orales)"),
    ("enf_orales",              "19. Enfermedades orales"),
    ("otras_alteraciones",      "20. Otras alteraciones"),
    ("fuma_licor",              "21. Fuma o consume licor"),
]

VIH_OPTIONS = ["Negativo", "Positivo", "No informado"]


def _seccion(titulo: str, icono: str) -> ft.Container:
    """Encabezado visual de sección."""
    return ft.Container(
        content=ft.Row(controls=[
            ft.Icon(icono, size=18, color="#FFFFFF"),
            ft.Text(titulo, size=13, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
        ], spacing=8),
        bgcolor="#1565C0", border_radius=6,
        padding=ft.padding.symmetric(horizontal=14, vertical=8),
        margin=ft.margin.only(top=10, bottom=4),
    )


class HistoriaClinicaView(ft.Column):
    """
    Formulario de Historia Clínica Odontológica.
    Carga datos existentes de Supabase al inicializarse.
    """

    def __init__(self, paciente_id: str, snack_fn=None):
        super().__init__(
            spacing=6,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
        self.paciente_id = paciente_id
        self.snack_fn    = snack_fn
        self._historia   = {}
        self._cb_map: dict[str, ft.Checkbox] = {}
        self._construir()

    # ── Helpers ──────────────────────────────────────────────────────────

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
            label=label,
            value=value or "",
            multiline=multiline,
            min_lines=min_lines,
            width=width,
            expand=expand,
            dense=True,
        )

    # ── Construcción del formulario ───────────────────────────────────────

    def _construir(self):
        try:
            self._historia = obtener_historia_clinica(self.paciente_id) or {}
        except Exception:
            self._historia = {}

        h  = self._historia
        sv = h.get("signos_vitales") or {}
        ant = h.get("antecedentes") or {}

        fecha_hoy = str(h.get("fecha_elaboracion") or datetime.date.today())[:10]

        # ── 1. Información General ────────────────────────────────────────
        self.tf_historia_no  = self._tf("N° Historia", h.get("historia_no",""), width=160)
        self.tf_odontologo   = self._tf("Odontólogo responsable", h.get("odontologo",""), expand=True)
        self.tf_fecha        = self._tf("Fecha", fecha_hoy, width=140)

        # ── 2. Anamnesis ──────────────────────────────────────────────────
        self.tf_motivo       = self._tf(
            "Motivo de consulta",
            h.get("motivo_consulta",""),
            multiline=True, min_lines=2, expand=True,
        )
        self.tf_enfermedad   = self._tf(
            "Enfermedad actual",
            h.get("enfermedad_actual",""),
            multiline=True, min_lines=2, expand=True,
        )

        # ── 3. Signos Vitales ─────────────────────────────────────────────
        self.tf_estatura     = self._tf("Estatura (cm)", sv.get("estatura",""), width=120)
        self.tf_peso         = self._tf("Peso (kg)",    sv.get("peso",""),    width=110)
        self.tf_temperatura  = self._tf("Temp. (°C)",   sv.get("temperatura",""), width=110)
        self.tf_pulso        = self._tf("Pulso (bpm)",  sv.get("pulso",""),   width=110)
        self.tf_tension      = self._tf("T.A. (mmHg)",  sv.get("tension_arterial",""), width=120)
        self.tf_fr           = self._tf("F.R. (rpm)",   sv.get("frecuencia_resp",""),  width=110)
        self.dd_vih          = ft.Dropdown(
            label="VIH",
            value=sv.get("vih", "Negativo"),
            options=[ft.dropdown.Option(o) for o in VIH_OPTIONS],
            width=150, dense=True,
        )

        # ── 4. Antecedentes Médicos (checkboxes) ─────────────────────────
        self._cb_map = {}
        for key, _ in ANTECEDENTES:
            cb = ft.Checkbox(value=bool(ant.get(key, False)), label="")
            self._cb_map[key] = cb

        # ── 5. Observaciones ──────────────────────────────────────────────
        self.tf_observaciones = self._tf(
            "Observaciones y notas adicionales",
            h.get("observaciones",""),
            multiline=True, min_lines=3, expand=True,
        )

        # ── Armar filas de antecedentes (2 columnas) ─────────────────────
        mitad = (len(ANTECEDENTES) + 1) // 2
        col_izq = ft.Column(spacing=2)
        col_der = ft.Column(spacing=2)
        for i, (key, label) in enumerate(ANTECEDENTES):
            fila = ft.Row(controls=[
                self._cb_map[key],
                ft.Text(label, size=12, expand=True),
            ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            if i < mitad:
                col_izq.controls.append(fila)
            else:
                col_der.controls.append(fila)

        existe = bool(h.get("id"))
        lbl_btn = "Actualizar Historia Clínica" if existe else "Guardar Historia Clínica"

        self.controls = [
            # Título
            ft.Container(
                content=ft.Row(controls=[
                    ft.Icon(ft.Icons.MEDICAL_INFORMATION, size=22, color="#1565C0"),
                    ft.Text("Historia Clínica Odontológica",
                            size=17, weight=ft.FontWeight.BOLD, color="#1565C0"),
                ], spacing=10),
                padding=ft.padding.only(bottom=4),
            ),

            # 1. Información General
            _seccion("1. INFORMACIÓN GENERAL", ft.Icons.INFO_OUTLINE),
            ft.Row(controls=[
                self.tf_historia_no, self.tf_odontologo, self.tf_fecha,
            ], spacing=10, wrap=True),

            # 2. Anamnesis
            _seccion("2. ANAMNESIS", ft.Icons.NOTES),
            self.tf_motivo,
            self.tf_enfermedad,

            # 3. Signos Vitales
            _seccion("3. SIGNOS VITALES", ft.Icons.MONITOR_HEART),
            ft.Row(controls=[
                self.tf_estatura, self.tf_peso, self.tf_temperatura,
                self.tf_pulso,    self.tf_tension, self.tf_fr, self.dd_vih,
            ], spacing=8, wrap=True),

            # 4. Antecedentes
            _seccion("4. ANTECEDENTES MÉDICOS Y ODONTOLÓGICOS", ft.Icons.HEALTH_AND_SAFETY),
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Container(content=col_izq, expand=True),
                        ft.VerticalDivider(width=1, color="#E0E0E0"),
                        ft.Container(content=col_der, expand=True),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                border=ft.border.all(1, "#E0E0E0"),
                border_radius=6, padding=10,
            ),

            # 5. Observaciones
            _seccion("5. OBSERVACIONES", ft.Icons.EDIT_NOTE),
            self.tf_observaciones,

            # Botón guardar
            ft.Container(
                content=ft.FilledButton(
                    lbl_btn,
                    icon=ft.Icons.SAVE,
                    on_click=self._guardar,
                ),
                padding=ft.padding.symmetric(vertical=10),
            ),
        ]

    # ── Guardar ──────────────────────────────────────────────────────────

    def _guardar(self, e):
        antecedentes = {key: self._cb_map[key].value for key, _ in ANTECEDENTES}
        signos_vitales = {
            "estatura":         self.tf_estatura.value.strip(),
            "peso":             self.tf_peso.value.strip(),
            "temperatura":      self.tf_temperatura.value.strip(),
            "pulso":            self.tf_pulso.value.strip(),
            "tension_arterial": self.tf_tension.value.strip(),
            "frecuencia_resp":  self.tf_fr.value.strip(),
            "vih":              self.dd_vih.value or "Negativo",
        }
        datos = {
            "historia_no":       self.tf_historia_no.value.strip(),
            "odontologo":        self.tf_odontologo.value.strip(),
            "fecha_elaboracion": self.tf_fecha.value.strip() or str(datetime.date.today()),
            "motivo_consulta":   self.tf_motivo.value.strip(),
            "enfermedad_actual": self.tf_enfermedad.value.strip(),
            "signos_vitales":    signos_vitales,
            "antecedentes":      antecedentes,
            "observaciones":     self.tf_observaciones.value.strip(),
        }
        try:
            guardar_historia_clinica(self.paciente_id, datos)
            self._snack("Historia Clínica guardada correctamente.")
        except Exception as ex:
            self._snack(f"Error al guardar: {ex}", error=True)
