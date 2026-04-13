"""
Módulo de Pacientes — Historia Clínica Odontológica.
Pestañas: Ficha | Anamnesis | Exploración | Odontograma
Odontograma técnico de 5 superficies por pieza (estilo geométrico FDI).
"""

import datetime
import flet as ft
from database import (
    listar_pacientes,
    obtener_paciente,
    crear_paciente,
    actualizar_paciente,
    obtener_historia_clinica,
    guardar_historia_clinica,
    obtener_odontograma,
    guardar_diente,
    actualizar_diagnostico_dental,
    registrar_constante,
)

# ── Constantes exportadas (usadas por otros módulos) ──────────────────────

ESTADOS_DIENTE = {
    "sano":      {"color": "#FFFFFF", "borde": "#BDBDBD", "label": "Sano"},
    "caries":    {"color": "#E53935", "borde": "#B71C1C", "label": "Caries"},
    "obturado":  {"color": "#1E88E5", "borde": "#0D47A1", "label": "Obturado"},
    "ausente":   {"color": "#37474F", "borde": "#000000", "label": "Ausente"},
    "corona":    {"color": "#FDD835", "borde": "#F57F17", "label": "Corona"},
    "fractura":  {"color": "#FF6D00", "borde": "#BF360C", "label": "Fractura"},
    "extraccion":{"color": "#37474F", "borde": "#000000", "label": "Ausente"},
    "implante":  {"color": "#81C784", "borde": "#2E7D32", "label": "Implante"},
}
CARAS         = ["oclusal", "vestibular", "lingual", "mesial", "distal"]
DIENTES_ADULTO = [
    [18, 17, 16, 15, 14, 13, 12, 11, 21, 22, 23, 24, 25, 26, 27, 28],
    [48, 47, 46, 45, 44, 43, 42, 41, 31, 32, 33, 34, 35, 36, 37, 38],
]
DIENTES_DECIDUOS = [
    [55, 54, 53, 52, 51, 61, 62, 63, 64, 65],
    [85, 84, 83, 82, 81, 71, 72, 73, 74, 75],
]

ANTECEDENTES = [
    ("tratamiento_medico",       "01. Tratamiento médico actual"),
    ("medicamentos",             "02. Toma de medicamentos"),
    ("alergias_med",             "03. Alergias a medicamentos"),
    ("cardiopatias",             "04. Cardiopatías"),
    ("presion_arterial_alt",     "05. Alteración presión arterial"),
    ("embarazo",                 "06. Embarazo"),
    ("diabetes",                 "07. Diabetes"),
    ("hepatitis",                "08. Hepatitis"),
    ("irradiaciones",            "09. Irradiaciones previas"),
    ("discrasias",               "10. Discrasias sanguíneas"),
    ("fiebre_reumatica",         "11. Fiebre reumática"),
    ("enf_renales",              "12. Enfermedades renales"),
    ("inmunosupresion",          "13. Inmunosupresión / VIH"),
    ("trastornos_emocionales",   "14. Trastornos emocionales"),
    ("trastornos_respiratorios", "15. Trastornos respiratorios"),
    ("trastornos_gastricos",     "16. Trastornos gástricos"),
    ("epilepsia",                "17. Epilepsia"),
    ("cirugias",                 "18. Cirugías previas"),
    ("enf_orales",               "19. Enfermedades orales previas"),
    ("otras_alteraciones",       "20. Otras alteraciones sistémicas"),
    ("fuma_licor",               "21. Tabaquismo / Consumo de alcohol"),
]

GRUPOS_SANGRE = ["A+", "A−", "B+", "B−", "AB+", "AB−", "O+", "O−", "Desconocido"]


def _snack_page(page: ft.Page, msg: str, error: bool = False):
    page.snack_bar = ft.SnackBar(
        content=ft.Text(msg),
        bgcolor=ft.Colors.RED_700 if error else ft.Colors.GREEN_700,
        open=True,
    )
    page.update()


def _tf(label: str, value: str = "", width=None,
        multiline=False, min_lines=1, expand=False,
        hint: str = "") -> ft.TextField:
    return ft.TextField(
        label=label, value=value or "",
        hint_text=hint,
        multiline=multiline, min_lines=min_lines,
        width=width, expand=expand, dense=True,
    )


def _titulo(texto: str, icono: str) -> ft.Container:
    return ft.Container(
        content=ft.Row(controls=[
            ft.Icon(icono, size=16, color="#FFFFFF"),
            ft.Text(texto, size=12, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
        ], spacing=8),
        bgcolor="#1565C0", border_radius=5,
        padding=ft.padding.symmetric(horizontal=12, vertical=7),
        margin=ft.margin.only(top=8, bottom=4),
    )


# ═══════════════════════════════════════════════════════════════════════════
#  ODONTOGRAMA TÉCNICO GEOMÉTRICO
# ═══════════════════════════════════════════════════════════════════════════

_HERRAMIENTAS = [
    ("sano",     "#FFFFFF", "#BDBDBD", "Sano / Limpiar"),
    ("caries",   "#E53935", "#B71C1C", "Caries"),
    ("obturado", "#1E88E5", "#0D47A1", "Obturado"),
    ("ausente",  "#37474F", "#000000", "Ausente"),
    ("corona",   "#FDD835", "#F57F17", "Corona"),
    ("fractura", "#FF6D00", "#BF360C", "Fractura"),
]


class _DienteTecnico(ft.Column):
    """
    Diagrama geométrico rectangular de 5 superficies (estilo FDI clínico).
    Layout del rectángulo dividido en 5 zonas:
        ┌──────────────────┐
        │   VESTIBULAR     │  ← franja superior completa
        ├────────┬──┬──────┤
        │ MESIAL │OC│DISTAL│  ← fila media con centro Oclusal
        ├────────┴──┴──────┤
        │   LINGUAL/PAL.   │  ← franja inferior completa
        └──────────────────┘
               [  nº  ]
    """
    SZ  = 13   # alto de cada franja (px)
    SW  = 12   # ancho de Mesial/Oclusal/Distal (px cada uno)

    def __init__(self, numero: int, caras: dict, on_clic_cara):
        super().__init__(
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.numero       = numero
        self.caras        = {c: caras.get(c, "sano") for c in CARAS}
        self.on_clic_cara = on_clic_cara
        self._celdas: dict[str, ft.Container] = {}
        self._lbl = ft.Text(
            str(numero), size=8,
            text_align=ft.TextAlign.CENTER,
            color="#37474F", weight=ft.FontWeight.W_600,
        )
        self._construir()

    # ── crea una celda con color según el estado actual ─────────────────
    def _celda(self, cara: str, w: int, h: int) -> ft.Container:
        est = self.caras.get(cara, "sano")
        cfg = ESTADOS_DIENTE[est]
        c = ft.Container(
            width=w, height=h,
            bgcolor=cfg["color"],
            border=ft.border.all(0.6, cfg["borde"]),
            on_click=lambda e, ca=cara: self.on_clic_cara(self.numero, ca),
            tooltip=cara.capitalize(),
            alignment=ft.Alignment(0, 0),
        )
        self._celdas[cara] = c
        return c

    def _construir(self):
        W = self.SW * 3   # ancho total del diente (Mesial+Oclusal+Distal)
        H = self.SZ       # alto de vestibular/lingual
        # El rectángulo completo del diente
        diente_rect = ft.Container(
            content=ft.Column(controls=[
                # Franja superior — Vestibular
                self._celda("vestibular", W, H),
                # Fila media — Mesial | Oclusal | Distal
                ft.Row(controls=[
                    self._celda("mesial",   self.SW, self.SW),
                    self._celda("oclusal",  self.SW, self.SW),
                    self._celda("distal",   self.SW, self.SW),
                ], spacing=0),
                # Franja inferior — Lingual / Palatino
                self._celda("lingual", W, H),
            ], spacing=0),
            border=ft.border.all(1.2, "#78909C"),
            border_radius=2,
        )
        self.controls = [
            diente_rect,
            ft.Container(
                content=self._lbl,
                width=W, alignment=ft.Alignment(0, 0),
                padding=ft.padding.only(top=1),
            ),
        ]

    def actualizar(self, caras: dict):
        self.caras = {c: caras.get(c, "sano") for c in CARAS}
        for cara, c in self._celdas.items():
            cfg = ESTADOS_DIENTE[self.caras[cara]]
            c.bgcolor = cfg["color"]
            c.border  = ft.border.all(0.6, cfg["borde"])
            if c.page:
                c.update()


class OdontogramaView(ft.Column):
    """
    Odontograma técnico completo: permanentes + deciduos.
    Herramienta activa seleccionable; clic en superficie = aplica herramienta.
    """

    def __init__(self, paciente_id: str,
                 diagnostico_dental: dict | None = None,
                 snack_fn=None):
        super().__init__(spacing=8, expand=True, scroll=ft.ScrollMode.AUTO)
        self.paciente_id     = paciente_id
        self.diagnosticos    = dict(diagnostico_dental or {})
        self.snack_fn        = snack_fn
        self.herramienta     = "caries"
        self._datos: dict[int, dict] = {}
        self._widgets: dict[int, _DienteTecnico] = {}
        self._btn_herr: dict[str, ft.ElevatedButton] = {}

        self._fila_adult_sup = ft.Row(spacing=4, wrap=False)
        self._fila_adult_inf = ft.Row(spacing=4, wrap=False)
        self._fila_dec_sup   = ft.Row(spacing=4, wrap=False)
        self._fila_dec_inf   = ft.Row(spacing=4, wrap=False)

        self._panel_diag = ft.Container(
            content=ft.Column(controls=[
                ft.Icon(ft.Icons.TOUCH_APP, size=28, color="#BDBDBD"),
                ft.Text("Seleccioná herramienta y\nhacé clic en una superficie",
                        color="#9E9E9E", italic=True, size=12,
                        text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
               alignment=ft.MainAxisAlignment.CENTER),
            expand=True, border=ft.border.all(1, "#E0E0E0"),
            border_radius=6, padding=12,
        )
        self._construir()

    def did_mount(self):
        try:
            filas = obtener_odontograma(self.paciente_id)
            self._datos = {r["diente"]: r.get("caras", {}) for r in filas}
        except Exception:
            self._datos = {}
        self._poblar_filas()
        self.update()

    # ── Herramientas ──────────────────────────────────────────────────────

    def _btn_herramienta(self, key: str, color: str, borde: str,
                          label: str) -> ft.ElevatedButton:
        activa = key == self.herramienta
        btn = ft.ElevatedButton(
            label, height=30,
            style=ft.ButtonStyle(
                bgcolor=color if activa else "#F5F5F5",
                color="#000000" if color in ("#FFFFFF", "#FDD835") else ("#FFFFFF" if activa else "#424242"),
                side=ft.BorderSide(2, borde if activa else "#BDBDBD"),
            ),
            on_click=lambda e, k=key: self._sel_herramienta(k),
        )
        self._btn_herr[key] = btn
        return btn

    def _sel_herramienta(self, key: str):
        self.herramienta = key
        for k, btn in self._btn_herr.items():
            col, brd, _ = next((c, b, l) for ck, c, b, l in _HERRAMIENTAS if ck == k)
            activa = k == key
            btn.style = ft.ButtonStyle(
                bgcolor=col if activa else "#F5F5F5",
                color="#000000" if col in ("#FFFFFF", "#FDD835") else ("#FFFFFF" if activa else "#424242"),
                side=ft.BorderSide(2, brd if activa else "#BDBDBD"),
            )
            if btn.page:
                btn.update()

    # ── Construcción de filas ──────────────────────────────────────────────

    def _poblar_filas(self):
        def build_fila(numeros):
            ws = []
            for n in numeros:
                caras = self._datos.get(n, {c: "sano" for c in CARAS})
                w = _DienteTecnico(n, caras, self._on_clic)
                self._widgets[n] = w
                ws.append(ft.Container(content=w, padding=ft.padding.symmetric(horizontal=1)))
            return ws

        self._fila_adult_sup.controls = build_fila(DIENTES_ADULTO[0])
        self._fila_adult_inf.controls = build_fila(DIENTES_ADULTO[1])
        self._fila_dec_sup.controls   = build_fila(DIENTES_DECIDUOS[0])
        self._fila_dec_inf.controls   = build_fila(DIENTES_DECIDUOS[1])

    def _on_clic(self, numero: int, cara: str):
        herr = self.herramienta
        if numero not in self._datos:
            self._datos[numero] = {c: "sano" for c in CARAS}
        if herr == "ausente":
            for c in CARAS:
                self._datos[numero][c] = "ausente"
        else:
            actual = self._datos[numero].get(cara, "sano")
            self._datos[numero][cara] = herr if actual != herr else "sano"

        caras_nuevas = dict(self._datos[numero])
        if numero in self._widgets:
            self._widgets[numero].actualizar(caras_nuevas)

        self._actualizar_panel(numero)

        try:
            guardar_diente(self.paciente_id, numero, caras_nuevas)
        except Exception as ex:
            if self.snack_fn:
                self.snack_fn(f"Error al guardar diente {numero}: {ex}", error=True)

    def _actualizar_panel(self, numero: int):
        caras = self._datos.get(numero, {})
        diag  = self.diagnosticos.get(str(numero), "")
        tf_diag = ft.TextField(
            label="Diagnóstico / Tratamiento indicado",
            value=diag, multiline=True, min_lines=2, expand=True,
        )

        def guardar_diag(e):
            self.diagnosticos[str(numero)] = tf_diag.value.strip()
            try:
                actualizar_diagnostico_dental(self.paciente_id, self.diagnosticos)
                if self.snack_fn:
                    self.snack_fn(f"Diagnóstico pieza {numero} guardado.")
            except Exception as ex:
                if self.snack_fn:
                    self.snack_fn(f"Error: {ex}", error=True)

        resumen = ft.Column(spacing=3, controls=[
            ft.Row(controls=[
                ft.Container(
                    width=10, height=10,
                    bgcolor=ESTADOS_DIENTE.get(est, ESTADOS_DIENTE["sano"])["color"],
                    border=ft.border.all(1, ESTADOS_DIENTE.get(est, ESTADOS_DIENTE["sano"])["borde"]),
                    border_radius=2,
                ),
                ft.Text(f"{c.capitalize()}: {ESTADOS_DIENTE.get(est, ESTADOS_DIENTE['sano'])['label']}",
                        size=11),
            ], spacing=5)
            for c, est in caras.items()
        ])

        self._panel_diag.content = ft.Column(controls=[
            ft.Text(f"Pieza {numero}", size=14,
                    weight=ft.FontWeight.BOLD, color="#1565C0"),
            resumen,
            ft.Divider(height=6),
            tf_diag,
            ft.FilledButton("Guardar diagnóstico",
                            icon=ft.Icons.SAVE, on_click=guardar_diag),
        ], spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
        if self._panel_diag.page:
            self._panel_diag.update()

    def _fila_etiqueta(self, texto: str, color: str) -> ft.Container:
        return ft.Container(
            content=ft.Text(texto, size=9, color="#616161",
                            text_align=ft.TextAlign.CENTER),
            bgcolor=color, border_radius=3,
            padding=ft.padding.symmetric(horizontal=6, vertical=2),
            margin=ft.margin.only(bottom=2),
        )

    def _construir(self):
        herr_row = ft.Row(controls=[
            self._btn_herramienta(k, c, b, l)
            for k, c, b, l in _HERRAMIENTAS
        ], spacing=6, wrap=True)

        cuadricula = ft.Container(
            content=ft.Column(controls=[
                ft.Text("PERMANENTES", size=10, color="#757575",
                        weight=ft.FontWeight.W_600),
                self._fila_etiqueta("SUPERIOR  ▸  18 → 11 | 21 → 28", "#E3F2FD"),
                ft.Container(
                    content=self._fila_adult_sup,
                    bgcolor="#F5F9FF",
                    border=ft.border.all(1, "#BBDEFB"),
                    border_radius=4, padding=6,
                ),
                ft.Divider(height=4, color="#E0E0E0"),
                self._fila_etiqueta("INFERIOR  ▸  48 → 41 | 31 → 38", "#E8F5E9"),
                ft.Container(
                    content=self._fila_adult_inf,
                    bgcolor="#F5FFF5",
                    border=ft.border.all(1, "#C8E6C9"),
                    border_radius=4, padding=6,
                ),
                ft.Divider(height=8, color="#E0E0E0"),
                ft.Text("DECIDUOS / TEMPORALES", size=10, color="#757575",
                        weight=ft.FontWeight.W_600),
                self._fila_etiqueta("SUPERIOR  ▸  55 → 51 | 61 → 65", "#FFF3E0"),
                ft.Container(
                    content=self._fila_dec_sup,
                    bgcolor="#FFFDE7",
                    border=ft.border.all(1, "#FFCC80"),
                    border_radius=4, padding=6,
                ),
                self._fila_etiqueta("INFERIOR  ▸  85 → 81 | 71 → 75", "#FCE4EC"),
                ft.Container(
                    content=self._fila_dec_inf,
                    bgcolor="#FFF8F8",
                    border=ft.border.all(1, "#F48FB1"),
                    border_radius=4, padding=6,
                ),
            ], spacing=4),
            border=ft.border.all(1, "#E0E0E0"),
            border_radius=6, padding=10,
        )

        self.controls = [
            ft.Container(
                content=ft.Column(controls=[
                    ft.Text("Herramienta activa:",
                            size=12, weight=ft.FontWeight.W_500),
                    herr_row,
                ], spacing=6),
                bgcolor="#F8F8F8",
                border=ft.border.all(1, "#E0E0E0"),
                border_radius=6, padding=10,
            ),
            ft.Row(controls=[
                ft.Container(content=cuadricula,
                             expand=True, scroll=ft.ScrollMode.HORIZONTAL),
                self._panel_diag,
            ], spacing=10, expand=True,
               vertical_alignment=ft.CrossAxisAlignment.START),
        ]


# ═══════════════════════════════════════════════════════════════════════════
#  PESTAÑA: FICHA DEL PACIENTE
# ═══════════════════════════════════════════════════════════════════════════

class _FichaView(ft.Column):
    def __init__(self, paciente_id: str | None, snack_fn):
        super().__init__(spacing=8, expand=True, scroll=ft.ScrollMode.AUTO)
        self.paciente_id = paciente_id
        self.snack_fn    = snack_fn
        self._datos: dict = {}
        self._construir()

    def _construir(self):
        if self.paciente_id:
            try:
                self._datos = obtener_paciente(self.paciente_id) or {}
            except Exception:
                self._datos = {}

        d = self._datos
        self.tf_nombre    = _tf("Nombre *", d.get("nombre",""), expand=True)
        self.tf_apellido  = _tf("Apellido *", d.get("apellido",""), expand=True)
        self.tf_dni       = _tf("DNI / Cédula", d.get("dni",""), width=180)
        self.tf_fec_nac   = _tf("Fecha nacimiento", d.get("fecha_nac",""),
                                 width=160, hint="AAAA-MM-DD")
        self.tf_telefono  = _tf("Teléfono", d.get("telefono",""), width=200)
        self.tf_email     = _tf("Correo electrónico", d.get("email",""), expand=True)
        self.tf_direccion = _tf("Dirección", d.get("direccion",""), expand=True)
        self.tf_obra      = _tf("Obra social", d.get("obra_social",""), expand=True)
        self.tf_afiliado  = _tf("Nro. afiliado", d.get("nro_afiliado",""), width=180)
        self.dd_sangre    = ft.Dropdown(
            label="Grupo sanguíneo",
            value=d.get("grupo_sangre", "Desconocido"),
            options=[ft.dropdown.Option(g) for g in GRUPOS_SANGRE],
            width=170, dense=True,
        )
        self.tf_alergias  = _tf("Alergias conocidas",
                                 d.get("alergias",""),
                                 multiline=True, min_lines=2, expand=True)

        lbl_btn = "Actualizar ficha" if self.paciente_id else "Crear paciente"

        self.controls = [
            _titulo("DATOS PERSONALES", ft.Icons.PERSON),
            ft.Row(controls=[self.tf_nombre, self.tf_apellido], spacing=10),
            ft.Row(controls=[self.tf_dni, self.tf_fec_nac, self.dd_sangre], spacing=10, wrap=True),
            _titulo("CONTACTO", ft.Icons.CONTACT_PHONE),
            ft.Row(controls=[self.tf_telefono, self.tf_email], spacing=10),
            self.tf_direccion,
            _titulo("COBERTURA MÉDICA", ft.Icons.HEALTH_AND_SAFETY),
            ft.Row(controls=[self.tf_obra, self.tf_afiliado], spacing=10),
            _titulo("ALERGIAS", ft.Icons.WARNING_AMBER),
            self.tf_alergias,
            ft.Container(
                content=ft.FilledButton(lbl_btn, icon=ft.Icons.SAVE,
                                        on_click=self._guardar),
                padding=ft.padding.symmetric(vertical=10),
            ),
        ]

    def _guardar(self, e):
        nombre   = self.tf_nombre.value.strip()
        apellido = self.tf_apellido.value.strip()
        if not nombre or not apellido:
            self.snack_fn("Nombre y apellido son obligatorios.", error=True)
            return
        datos = {
            "nombre":       nombre,
            "apellido":     apellido,
            "dni":          self.tf_dni.value.strip() or None,
            "fecha_nac":    self.tf_fec_nac.value.strip() or None,
            "telefono":     self.tf_telefono.value.strip() or None,
            "email":        self.tf_email.value.strip() or None,
            "direccion":    self.tf_direccion.value.strip() or None,
            "obra_social":  self.tf_obra.value.strip() or None,
            "nro_afiliado": self.tf_afiliado.value.strip() or None,
            "grupo_sangre": self.dd_sangre.value or None,
            "alergias":     self.tf_alergias.value.strip() or None,
        }
        try:
            if self.paciente_id:
                actualizar_paciente(self.paciente_id, datos)
                self.snack_fn("Ficha actualizada correctamente.")
            else:
                crear_paciente(datos)
                self.snack_fn("Paciente creado correctamente.")
        except Exception as ex:
            self.snack_fn(f"Error: {ex}", error=True)


# ═══════════════════════════════════════════════════════════════════════════
#  PESTAÑA: ANAMNESIS + CONSTANTES VITALES
# ═══════════════════════════════════════════════════════════════════════════

class _AnamnesisView(ft.Column):
    def __init__(self, paciente_id: str, snack_fn):
        super().__init__(spacing=8, expand=True, scroll=ft.ScrollMode.AUTO)
        self.paciente_id  = paciente_id
        self.snack_fn     = snack_fn
        self._historia: dict = {}
        self._sw_map: dict[str, ft.Switch] = {}
        self._ant_visible = False   # colapsado por defecto para ganar espacio
        self._panel_ant: ft.Container | None = None
        self._icono_toggle: ft.Icon | None = None
        self._construir()

    # ── Toggle expandir/colapsar antecedentes ─────────────────────────────
    def _toggle_ant(self, e):
        self._ant_visible = not self._ant_visible
        if self._panel_ant:
            self._panel_ant.visible = self._ant_visible
            if self._panel_ant.page:
                self._panel_ant.update()
        if self._icono_toggle:
            self._icono_toggle.name = (
                ft.Icons.EXPAND_LESS if self._ant_visible else ft.Icons.EXPAND_MORE
            )
            if self._icono_toggle.page:
                self._icono_toggle.update()

    def _construir(self):
        try:
            self._historia = obtener_historia_clinica(self.paciente_id) or {}
        except Exception:
            self._historia = {}

        h   = self._historia
        sv  = h.get("signos_vitales") or {}
        ant = h.get("antecedentes") or {}

        # ── 21 switches ───────────────────────────────────────────────────
        self._sw_map = {}
        col_izq = ft.Column(spacing=1)
        col_der = ft.Column(spacing=1)
        mitad   = (len(ANTECEDENTES) + 1) // 2

        positivos = sum(1 for key, _ in ANTECEDENTES if ant.get(key, False))

        for i, (key, label) in enumerate(ANTECEDENTES):
            activo = bool(ant.get(key, False))
            sw = ft.Switch(
                value=activo,
                active_color=ft.Colors.BLUE_700,
            )
            self._sw_map[key] = sw
            fila = ft.Row(controls=[
                sw,
                ft.Text(label, size=11, expand=True,
                        color="#C62828" if activo else "#424242"),
            ], spacing=2, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            (col_izq if i < mitad else col_der).controls.append(fila)

        self._icono_toggle = ft.Icon(
            ft.Icons.EXPAND_MORE, size=20, color="#FFFFFF"
        )
        resumen_txt = (f"{positivos} positivo(s)"
                       if positivos else "ninguno positivo")
        cabecera_ant = ft.Container(
            content=ft.Row(controls=[
                ft.Icon(ft.Icons.HEALTH_AND_SAFETY, size=16, color="#FFFFFF"),
                ft.Text(f"ANTECEDENTES MÉDICOS Y ODONTOLÓGICOS — {resumen_txt}",
                        size=12, weight=ft.FontWeight.BOLD, color="#FFFFFF",
                        expand=True),
                self._icono_toggle,
            ], spacing=8),
            bgcolor="#1565C0", border_radius=5,
            padding=ft.padding.symmetric(horizontal=12, vertical=7),
            margin=ft.margin.only(top=8, bottom=0),
            on_click=self._toggle_ant,
            ink=True,
        )

        self._panel_ant = ft.Container(
            visible=self._ant_visible,
            content=ft.Row(controls=[
                ft.Container(content=col_izq, expand=True),
                ft.VerticalDivider(width=1, color="#E0E0E0"),
                ft.Container(content=col_der, expand=True),
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.START),
            border=ft.border.all(1, "#BBDEFB"),
            border_radius=ft.border_radius.only(
                bottom_left=6, bottom_right=6
            ),
            padding=10,
            margin=ft.margin.only(bottom=4),
        )

        # ── Constantes vitales ─────────────────────────────────────────────
        self.tf_presion = _tf("Presión (mmHg)", sv.get("tension_arterial",""),
                               width=150, hint="120/80")
        self.tf_peso    = _tf("Peso (kg)",  sv.get("peso",""),      width=110)
        self.tf_talla   = _tf("Talla (cm)", sv.get("estatura",""),  width=110)
        self.tf_pulso   = _tf("Pulso (bpm)", sv.get("pulso",""),    width=110)
        self.tf_temp    = _tf("Temp. (°C)", sv.get("temperatura",""), width=110)
        self.tf_fr      = _tf("F.R. (rpm)", sv.get("frecuencia_resp",""), width=110)
        self.lbl_imc    = ft.Text("IMC: —", size=13, color="#1565C0",
                                  weight=ft.FontWeight.W_600)

        def calc_imc(e):
            try:
                p = float(self.tf_peso.value.replace(",", "."))
                t = float(self.tf_talla.value.replace(",", ".")) / 100
                imc = p / (t * t)
                cat = ("Bajo peso" if imc < 18.5 else
                       "Normal"    if imc < 25   else
                       "Sobrepeso" if imc < 30   else "Obesidad")
                self.lbl_imc.value = f"IMC: {imc:.1f} — {cat}"
            except Exception:
                self.lbl_imc.value = "IMC: —"
            if self.lbl_imc.page:
                self.lbl_imc.update()

        self.tf_peso.on_blur  = calc_imc
        self.tf_talla.on_blur = calc_imc

        self.controls = [
            cabecera_ant,
            self._panel_ant,
            _titulo("CONSTANTES VITALES", ft.Icons.MONITOR_HEART),
            ft.Row(controls=[
                self.tf_presion, self.tf_pulso, self.tf_temp, self.tf_fr,
            ], spacing=8, wrap=True),
            ft.Row(controls=[
                self.tf_peso, self.tf_talla, self.lbl_imc,
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Container(
                content=ft.FilledButton("Guardar Anamnesis",
                                        icon=ft.Icons.SAVE,
                                        on_click=self._guardar),
                padding=ft.padding.symmetric(vertical=10),
            ),
        ]

    def _guardar(self, e):
        antecedentes = {key: self._sw_map[key].value for key, _ in ANTECEDENTES}
        sv = {
            "tension_arterial": self.tf_presion.value.strip(),
            "pulso":            self.tf_pulso.value.strip(),
            "temperatura":      self.tf_temp.value.strip(),
            "frecuencia_resp":  self.tf_fr.value.strip(),
            "peso":             self.tf_peso.value.strip(),
            "estatura":         self.tf_talla.value.strip(),
        }
        datos_existentes = dict(self._historia)
        datos_existentes["antecedentes"]   = antecedentes
        datos_existentes["signos_vitales"] = sv
        try:
            guardar_historia_clinica(self.paciente_id, datos_existentes)
            # Registrar constante en tabla constantes_vitales
            try:
                p = float(self.tf_peso.value.replace(",", ".") or 0)
                t = float(self.tf_talla.value.replace(",", ".") or 0)
                if p > 0 and t > 0:
                    pa = self.tf_presion.value.strip()
                    sys_v = int(pa.split("/")[0]) if "/" in pa else None
                    dia_v = int(pa.split("/")[1]) if "/" in pa else None
                    registrar_constante({
                        "paciente_id":  self.paciente_id,
                        "peso_kg":      p,
                        "altura_cm":    t,
                        "presion_sys":  sys_v,
                        "presion_dia":  dia_v,
                    })
            except Exception:
                pass
            self.snack_fn("Anamnesis y constantes guardadas.")
        except Exception as ex:
            self.snack_fn(f"Error: {ex}", error=True)


# ═══════════════════════════════════════════════════════════════════════════
#  PESTAÑA: EXPLORACIÓN CLÍNICA
# ═══════════════════════════════════════════════════════════════════════════

class _ExploracionView(ft.Column):
    def __init__(self, paciente_id: str, snack_fn):
        super().__init__(spacing=8, expand=True, scroll=ft.ScrollMode.AUTO)
        self.paciente_id = paciente_id
        self.snack_fn    = snack_fn
        self._historia: dict = {}
        self._construir()

    def _construir(self):
        try:
            self._historia = obtener_historia_clinica(self.paciente_id) or {}
        except Exception:
            self._historia = {}

        h = self._historia
        self.tf_hist_no   = _tf("N° Historia", h.get("historia_no",""), width=160)
        self.tf_odontologo= _tf("Odontólogo responsable", h.get("odontologo",""), expand=True)
        self.tf_fecha     = _tf("Fecha", h.get("fecha_elaboracion","") or str(datetime.date.today()),
                                 width=140)
        self.tf_motivo    = _tf("Motivo de consulta",
                                 h.get("motivo_consulta",""),
                                 multiline=True, min_lines=3, expand=True)
        self.tf_enf       = _tf("Enfermedad actual / Hallazgos clínicos",
                                 h.get("enfermedad_actual",""),
                                 multiline=True, min_lines=4, expand=True)
        self.tf_obs       = _tf("Observaciones y plan de tratamiento",
                                 h.get("observaciones",""),
                                 multiline=True, min_lines=3, expand=True)

        self.controls = [
            _titulo("DATOS DE LA CONSULTA", ft.Icons.INFO_OUTLINE),
            ft.Row(controls=[self.tf_hist_no, self.tf_odontologo, self.tf_fecha],
                   spacing=10, wrap=True),
            _titulo("ANAMNESIS DE LA CONSULTA", ft.Icons.NOTES),
            self.tf_motivo,
            self.tf_enf,
            _titulo("OBSERVACIONES", ft.Icons.EDIT_NOTE),
            self.tf_obs,
            ft.Container(
                content=ft.FilledButton("Guardar Exploración",
                                        icon=ft.Icons.SAVE,
                                        on_click=self._guardar),
                padding=ft.padding.symmetric(vertical=10),
            ),
        ]

    def _guardar(self, e):
        datos = dict(self._historia)
        datos.update({
            "historia_no":       self.tf_hist_no.value.strip(),
            "odontologo":        self.tf_odontologo.value.strip(),
            "fecha_elaboracion": self.tf_fecha.value.strip() or str(datetime.date.today()),
            "motivo_consulta":   self.tf_motivo.value.strip(),
            "enfermedad_actual": self.tf_enf.value.strip(),
            "observaciones":     self.tf_obs.value.strip(),
        })
        try:
            guardar_historia_clinica(self.paciente_id, datos)
            self.snack_fn("Exploración guardada correctamente.")
        except Exception as ex:
            self.snack_fn(f"Error: {ex}", error=True)


# ═══════════════════════════════════════════════════════════════════════════
#  HistoriaClinicaView — vista compacta para Módulo de Tratamientos
# ═══════════════════════════════════════════════════════════════════════════

class HistoriaClinicaView(ft.Column):
    """Vista compacta de HC importada por modulo_tratamientos."""

    def __init__(self, paciente_id: str, snack_fn=None):
        super().__init__(spacing=0, expand=True)
        self.paciente_id = paciente_id
        self._snack_fn   = snack_fn
        self.controls    = [
            ft.Container(
                content=ft.Column(controls=[
                    _ExploracionView(paciente_id, self._snack),
                ], expand=True, scroll=ft.ScrollMode.AUTO),
                expand=True, padding=ft.padding.all(8),
            )
        ]

    def _snack(self, msg: str, error: bool = False):
        if self._snack_fn:
            self._snack_fn(msg, error)
        elif self.page:
            _snack_page(self.page, msg, error)


# Alias para retrocompatibilidad
OdontogramaDiagnosticoView = OdontogramaView


# ═══════════════════════════════════════════════════════════════════════════
#  VISTA PRINCIPAL — PacientesView
# ═══════════════════════════════════════════════════════════════════════════

_TABS = [
    ("Ficha",        ft.Icons.PERSON),
    ("Anamnesis",    ft.Icons.HEALTH_AND_SAFETY),
    ("Exploración",  ft.Icons.NOTES),
    ("Odontograma",  ft.Icons.MEDICAL_SERVICES),
]


class PacientesView(ft.Column):
    """
    Vista principal del módulo Pacientes.
    Selector de paciente → 4 pestañas: Ficha | Anamnesis | Exploración | Odontograma.
    Guarda paciente_id en page.session para otros módulos.
    """

    def __init__(self):
        super().__init__(spacing=0, expand=True)
        self.paciente_id: str | None = None
        self._tab_activo = 0
        self._tab_btns: list[ft.ElevatedButton] = []
        self._area = ft.Container(
            expand=True, padding=ft.padding.all(16),
            content=ft.Column(controls=[
                ft.Icon(ft.Icons.PERSON_SEARCH, size=48, color="#BDBDBD"),
                ft.Text("Seleccioná un paciente para ver su historia clínica",
                        color="#9E9E9E", size=14, italic=True),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
               alignment=ft.MainAxisAlignment.CENTER,
               expand=True),
        )
        self._barra_tabs = ft.Container(
            visible=False,
            content=ft.Row(spacing=6),
            padding=ft.padding.symmetric(horizontal=16, vertical=8),
            bgcolor="#F5F5F5",
            border=ft.border.only(bottom=ft.BorderSide(1, "#E0E0E0")),
        )
        self._construir()

    def _construir(self):
        try:
            pacientes = listar_pacientes()
        except Exception:
            pacientes = []

        self.dd_selector = ft.Dropdown(
            label="Seleccionar paciente",
            hint_text="Elegí un paciente...",
            options=[
                ft.dropdown.Option(
                    p["id"],
                    f"{p.get('apellido','–')}, {p.get('nombre','')}  "
                    f"({'DNI: '+p['dni'] if p.get('dni') else 'sin DNI'})",
                )
                for p in sorted(pacientes, key=lambda x: x.get("apellido",""))
            ],
            on_select=self._on_selector,
            width=500,
        )

        # Botones de pestañas
        self._tab_btns = []
        for i, (lbl, icn) in enumerate(_TABS):
            btn = ft.ElevatedButton(
                lbl,
                icon=icn,
                on_click=lambda e, idx=i: self._sel_tab(idx),
                style=ft.ButtonStyle(
                    bgcolor=ft.Colors.BLUE_700 if i == 0 else ft.Colors.GREY_200,
                    color=ft.Colors.WHITE if i == 0 else ft.Colors.GREY_800,
                ),
            )
            self._tab_btns.append(btn)
        self._barra_tabs.content = ft.Row(
            controls=self._tab_btns, spacing=6
        )

        self.controls = [
            ft.Container(
                content=ft.Column(controls=[
                    ft.Text("Historia Clínica de Pacientes",
                            size=18, weight=ft.FontWeight.BOLD,
                            color="#1565C0"),
                    self.dd_selector,
                ], spacing=10),
                padding=ft.padding.symmetric(horizontal=16, vertical=12),
            ),
            ft.Divider(height=1, color="#E0E0E0"),
            self._barra_tabs,
            self._area,
        ]

    def _on_selector(self, e):
        pid = self.dd_selector.value
        if not pid:
            return
        self.paciente_id = pid
        if self.page:
            try:
                self.page.session.set("paciente_id", pid)
            except Exception:
                pass
        self._tab_activo = 0
        self._barra_tabs.visible = True
        self._actualizar_tabs()
        self._cargar_area()
        if self.controls[0].page:
            self.controls[0].update()

    def _sel_tab(self, idx: int):
        if idx == self._tab_activo:
            return
        self._tab_activo = idx
        self._actualizar_tabs()
        self._cargar_area()

    def _actualizar_tabs(self):
        for i, btn in enumerate(self._tab_btns):
            activa = (i == self._tab_activo)
            btn.style = ft.ButtonStyle(
                bgcolor=ft.Colors.BLUE_700 if activa else ft.Colors.GREY_200,
                color=ft.Colors.WHITE if activa else ft.Colors.GREY_800,
            )
            if btn.page:
                btn.update()
        if self._barra_tabs.page:
            self._barra_tabs.update()

    def _cargar_area(self):
        if not self.paciente_id:
            return
        pid = self.paciente_id
        snack = self._snack
        if self._tab_activo == 0:
            contenido = _FichaView(pid, snack)
        elif self._tab_activo == 1:
            contenido = _AnamnesisView(pid, snack)
        elif self._tab_activo == 2:
            contenido = _ExploracionView(pid, snack)
        else:
            try:
                h   = obtener_historia_clinica(pid) or {}
                dd  = h.get("diagnostico_dental") or {}
            except Exception:
                dd = {}
            contenido = OdontogramaView(pid, dd, snack)

        self._area.content = ft.Container(
            content=contenido, expand=True,
            padding=ft.padding.all(16),
        )
        if self._area.page:
            self._area.update()

    def _snack(self, msg: str, error: bool = False):
        if self.page:
            _snack_page(self.page, msg, error)
