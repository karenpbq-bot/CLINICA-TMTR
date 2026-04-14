"""
Generador de Historia Clínica en PDF.
Secciones: Ficha | Anamnesis | Odontograma.
Usa ReportLab (Platypus + canvas directo).
"""

import os
import tempfile
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, black, Color
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Flowable, KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from database import obtener_paciente, obtener_historia_clinica, obtener_odontograma

# ── Paleta ────────────────────────────────────────────────────────────────────
_AZUL_OSC  = HexColor("#1565C0")
_AZUL_CLAR = HexColor("#E3F2FD")
_GRIS_BG   = HexColor("#FAFAFA")
_GRIS_LIN  = HexColor("#E0E0E0")
_TEXTO_OSC = HexColor("#212121")
_TEXTO_GRI = HexColor("#616161")

_COL_ESTADO = {
    "sano":      HexColor("#FFFFFF"),
    "caries":    HexColor("#E53935"),
    "obturado":  HexColor("#1E88E5"),
    "ausente":   HexColor("#37474F"),
    "corona":    HexColor("#FDD835"),
    "fractura":  HexColor("#FF6D00"),
    "extraccion":HexColor("#37474F"),
    "implante":  HexColor("#81C784"),
}
_BORDE_SANO = HexColor("#BDBDBD")
_BORDE_MOD  = HexColor("#333333")

# ── Grupos dentales ───────────────────────────────────────────────────────────
_SUP_ADULT = [18,17,16,15,14,13,12,11,21,22,23,24,25,26,27,28]
_INF_ADULT = [48,47,46,45,44,43,42,41,31,32,33,34,35,36,37,38]
_SUP_DECID = [55,54,53,52,51,61,62,63,64,65]
_INF_DECID = [85,84,83,82,81,71,72,73,74,75]

ANTECEDENTES = [
    ("tratamiento_medico",       "Tratamiento médico actual"),
    ("medicamentos",             "Medicamentos"),
    ("alergias_med",             "Alergias a medicamentos"),
    ("cardiopatias",             "Cardiopatías"),
    ("presion_arterial_alt",     "Alt. presión arterial"),
    ("embarazo",                 "Embarazo"),
    ("diabetes",                 "Diabetes"),
    ("hepatitis",                "Hepatitis"),
    ("irradiaciones",            "Irradiaciones previas"),
    ("discrasias",               "Discrasias sanguíneas"),
    ("fiebre_reumatica",         "Fiebre reumática"),
    ("enf_renales",              "Enf. renales"),
    ("inmunosupresion",          "Inmunosupresión / VIH"),
    ("trastornos_emocionales",   "Trast. emocionales"),
    ("trastornos_respiratorios", "Trast. respiratorios"),
    ("trastornos_gastricos",     "Trast. gástricos"),
    ("epilepsia",                "Epilepsia"),
    ("cirugias",                 "Cirugías previas"),
    ("enf_orales",               "Enf. orales previas"),
    ("otras_alteraciones",       "Otras alt. sistémicas"),
    ("fuma_licor",               "Tabaquismo / Alcohol"),
]


# ═══════════════════════════════════════════════════════════════════════════════
#  Flowable: Odontograma
# ═══════════════════════════════════════════════════════════════════════════════

class _OdontogramaFlowable(Flowable):
    """
    Dibuja el odontograma completo (adulto + deciduo) como flowable Platypus.
    Cada diente = 5 superficies coloreadas + número.
    """
    TW   = 11.5   # pt, ancho de cada diente
    SEP  =  1.0   # pt, separación entre dientes
    VH   =  3.5   # pt, alto de vestibular/lingual
    MOH  =  4.0   # pt, alto de mesial/oclusal/distal
    MO_W =  3.8   # pt, ancho de mesial y distal
    NUM_H=  6.0   # pt, espacio para el número debajo
    FILA_H = None # calculado

    def __init__(self, datos: dict, available_width: float):
        super().__init__()
        self.__class__.FILA_H = self.VH * 2 + self.MOH + self.NUM_H + 4
        self.datos = datos
        self._avail = available_width
        # Calcular escala para que 16 dientes adultos quepan
        self._escala = min(1.0, (available_width - 40) / (16 * (self.TW + self.SEP)))

    def _sc(self, v):
        return v * self._escala

    def wrap(self, aW, aH):
        # Altura: 4 filas (adulto sup/inf, deciduo sup/inf) + labels
        alturas = (
            self._sc(self.FILA_H) * 4  # 4 filas de dientes
            + 14 * 2                   # 2 labels "PERMANENTES / DECIDUOS"
            + 8                        # separación central
            + 20                       # leyenda
        )
        return (aW, alturas)

    def draw(self):
        c = self.canv
        sc = self._sc
        TW = sc(self.TW); SEP = sc(self.SEP); VH = sc(self.VH)
        MOH = sc(self.MOH); MO_W = sc(self.MO_W); NH = sc(self.NUM_H)
        FH = VH * 2 + MOH + NH

        page_w = self._avail
        # Centrar filas adulto (16 dientes)
        adult_row_w = 16 * (TW + SEP)
        x_adult_start = (page_w - adult_row_w) / 2
        # Centrar filas deciduo (10 dientes)
        decid_row_w = 10 * (TW + SEP)
        x_decid_start = (page_w - decid_row_w) / 2

        # y positions desde arriba (flip: reportlab y crece hacia arriba)
        cur_y = self.height  # empezar desde arriba

        # ── PERMANENTES ──────────────────────────────────────────────────
        cur_y -= 11
        c.setFont("Helvetica-Bold", 7)
        c.setFillColor(_AZUL_OSC)
        c.drawString(0, cur_y, "PERMANENTES")
        cur_y -= 3

        # Superior adulto
        cur_y -= FH
        self._draw_fila(c, _SUP_ADULT, x_adult_start, cur_y, TW, SEP, VH, MOH, MO_W, NH)
        cur_y -= 2

        # Línea de separación superior/inferior (entre filas)
        c.setStrokeColor(_GRIS_LIN)
        c.setLineWidth(0.5)
        c.line(0, cur_y + 1, page_w, cur_y + 1)

        # Inferior adulto
        cur_y -= FH
        self._draw_fila(c, _INF_ADULT, x_adult_start, cur_y, TW, SEP, VH, MOH, MO_W, NH)
        cur_y -= 8

        # ── DECIDUOS ─────────────────────────────────────────────────────
        c.setFont("Helvetica-Bold", 7)
        c.setFillColor(_AZUL_OSC)
        c.drawString(0, cur_y, "DECIDUOS")
        cur_y -= 3

        # Superior deciduo
        cur_y -= FH
        self._draw_fila(c, _SUP_DECID, x_decid_start, cur_y, TW, SEP, VH, MOH, MO_W, NH)
        cur_y -= 2

        # Inferior deciduo
        cur_y -= FH
        self._draw_fila(c, _INF_DECID, x_decid_start, cur_y, TW, SEP, VH, MOH, MO_W, NH)
        cur_y -= 8

        # ── Leyenda ───────────────────────────────────────────────────────
        leyenda_items = [
            ("Sano", "#FFFFFF"), ("Caries", "#E53935"),
            ("Obturado", "#1E88E5"), ("Ausente", "#37474F"),
            ("Corona", "#FDD835"), ("Fractura", "#FF6D00"),
            ("Implante", "#81C784"),
        ]
        lx = 0
        for lbl, clr in leyenda_items:
            c.setFillColor(HexColor(clr))
            c.setStrokeColor(_BORDE_SANO)
            c.setLineWidth(0.4)
            c.rect(lx, cur_y, 7, 7, fill=1, stroke=1)
            c.setFillColor(_TEXTO_GRI)
            c.setFont("Helvetica", 5.5)
            c.drawString(lx + 9, cur_y + 1.5, lbl)
            lx += 7 + c.stringWidth(lbl, "Helvetica", 5.5) + 12

    def _draw_fila(self, c, numeros, x_start, y, TW, SEP, VH, MOH, MO_W, NH):
        OC_W = TW - 2 * MO_W
        for n in numeros:
            caras = self.datos.get(n, {})
            x = x_start

            # Vestibular (arriba)
            self._rect(c, x, y + NH + MOH + VH, TW, VH, caras.get("vestibular","sano"))
            # Mesial
            self._rect(c, x, y + NH + VH, MO_W, MOH, caras.get("mesial","sano"))
            # Oclusal
            self._rect(c, x + MO_W, y + NH + VH, OC_W, MOH, caras.get("oclusal","sano"))
            # Distal
            self._rect(c, x + MO_W + OC_W, y + NH + VH, MO_W, MOH, caras.get("distal","sano"))
            # Lingual (abajo)
            self._rect(c, x, y + NH, TW, VH, caras.get("lingual","sano"))

            # Número
            c.setFillColor(_TEXTO_OSC)
            c.setFont("Helvetica", 5)
            c.drawCentredString(x + TW / 2, y, str(n))

            x_start += TW + SEP

    def _rect(self, c, x, y, w, h, estado):
        color = _COL_ESTADO.get(estado, _COL_ESTADO["sano"])
        borde = _BORDE_SANO if estado == "sano" else _BORDE_MOD
        c.setFillColor(color)
        c.setStrokeColor(borde)
        c.setLineWidth(0.4)
        c.rect(x, y, w, h, fill=1, stroke=1)


# ═══════════════════════════════════════════════════════════════════════════════
#  Helpers de estilo
# ═══════════════════════════════════════════════════════════════════════════════

def _estilos():
    ss = getSampleStyleSheet()
    base = ss["Normal"]
    return {
        "titulo_sec": ParagraphStyle(
            "titulo_sec", parent=base,
            fontSize=9, fontName="Helvetica-Bold",
            textColor=white, backColor=_AZUL_OSC,
            leftIndent=6, rightIndent=6,
            spaceBefore=8, spaceAfter=4,
            leading=14,
        ),
        "campo_lbl": ParagraphStyle(
            "campo_lbl", parent=base,
            fontSize=7, fontName="Helvetica-Bold",
            textColor=_TEXTO_GRI,
        ),
        "campo_val": ParagraphStyle(
            "campo_val", parent=base,
            fontSize=8, fontName="Helvetica",
            textColor=_TEXTO_OSC,
            spaceAfter=1,
        ),
        "campo_val_ml": ParagraphStyle(
            "campo_val_ml", parent=base,
            fontSize=8, fontName="Helvetica",
            textColor=_TEXTO_OSC,
            spaceAfter=2,
        ),
        "header_titulo": ParagraphStyle(
            "header_titulo", parent=base,
            fontSize=14, fontName="Helvetica-Bold",
            textColor=_AZUL_OSC,
            alignment=TA_CENTER,
        ),
        "header_sub": ParagraphStyle(
            "header_sub", parent=base,
            fontSize=9, fontName="Helvetica",
            textColor=_TEXTO_GRI,
            alignment=TA_CENTER,
        ),
        "ant_pos": ParagraphStyle(
            "ant_pos", parent=base,
            fontSize=7, fontName="Helvetica-Bold",
            textColor=HexColor("#C62828"),
        ),
        "ant_neg": ParagraphStyle(
            "ant_neg", parent=base,
            fontSize=7, fontName="Helvetica",
            textColor=_TEXTO_GRI,
        ),
    }


def _campo(lbl: str, val: str, estilos: dict) -> list:
    val = (val or "").strip() or "—"
    return [
        Paragraph(lbl.upper(), estilos["campo_lbl"]),
        Paragraph(val, estilos["campo_val"]),
    ]


def _campo_ml(lbl: str, val: str, estilos: dict) -> list:
    """Campo con texto largo (multilinea)."""
    val = (val or "").strip() or "—"
    return [
        Paragraph(lbl.upper(), estilos["campo_lbl"]),
        Paragraph(val.replace("\n", "<br/>"), estilos["campo_val_ml"]),
        Spacer(1, 2),
    ]


def _titulo_seccion(texto: str, estilos: dict) -> Paragraph:
    return Paragraph(f"  {texto}", estilos["titulo_sec"])


def _tabla_ficha(datos: list[list], col_widths: list[float]) -> Table:
    """Tabla limpia de campos: label arriba, valor abajo."""
    t = Table(datos, colWidths=col_widths, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("VALIGN",    (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 2),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [_GRIS_BG, white]),
        ("BOX",  (0, 0), (-1, -1), 0.5, _GRIS_LIN),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, _GRIS_LIN),
    ]))
    return t


# ═══════════════════════════════════════════════════════════════════════════════
#  FUNCIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def exportar_historia_clinica(paciente_id: str, output_dir: str | None = None) -> str:
    """
    Genera el PDF de historia clínica y devuelve la ruta al archivo.
    Lanza excepción si falla.
    output_dir: carpeta de destino (si es None usa /tmp).
    """
    # ── Obtener datos ─────────────────────────────────────────────────────
    paciente  = obtener_paciente(paciente_id) or {}
    historia  = obtener_historia_clinica(paciente_id) or {}
    odonto_rs = obtener_odontograma(paciente_id) or []
    odonto    = {r["diente"]: r.get("caras", {}) for r in odonto_rs}

    nombre_pac = f"{paciente.get('apellido','').upper()}, {paciente.get('nombre','')}"
    fecha_hoy  = datetime.today().strftime("%d/%m/%Y  %H:%M")

    # ── Ruta del archivo ──────────────────────────────────────────────────
    if output_dir is None:
        output_dir = tempfile.gettempdir()
    os.makedirs(output_dir, exist_ok=True)
    safe_name = "".join(c if c.isalnum() else "_" for c in nombre_pac)[:40]
    ruta_pdf  = os.path.join(output_dir, f"HC_{safe_name}.pdf")

    # ── Documento ─────────────────────────────────────────────────────────
    margen_h = 18 * mm
    margen_v = 14 * mm
    doc = SimpleDocTemplate(
        ruta_pdf,
        pagesize=A4,
        leftMargin=margen_h, rightMargin=margen_h,
        topMargin=margen_v,  bottomMargin=margen_v,
    )
    W = A4[0] - 2 * margen_h   # ancho útil
    st = _estilos()
    historia_items = []

    # ── ENCABEZADO ────────────────────────────────────────────────────────
    historia_items += [
        Paragraph("CONSULTORIO ODONTOLÓGICO", st["header_titulo"]),
        Paragraph("Historia Clínica Odontológica", st["header_sub"]),
        Spacer(1, 3),
        HRFlowable(width=W, thickness=1.5, color=_AZUL_OSC),
        Spacer(1, 4),
        Table(
            [[
                Paragraph(f"<b>Paciente:</b>  {nombre_pac}", st["campo_val"]),
                Paragraph(f"<b>Generado:</b>  {fecha_hoy}", st["campo_val"]),
            ]],
            colWidths=[W * 0.6, W * 0.4],
            hAlign="LEFT",
        ),
        Spacer(1, 6),
    ]

    # ══════════════════════════════════════════════════════════════════════
    # SECCIÓN 1: FICHA DEL PACIENTE
    # ══════════════════════════════════════════════════════════════════════
    historia_items.append(_titulo_seccion("1. FICHA DEL PACIENTE", st))

    C4 = W / 4    # 4 columnas iguales

    def _p_lbl(txt):
        return Paragraph(txt.upper(), st["campo_lbl"])

    def _p_val(txt):
        return Paragraph((txt or "—").strip(), st["campo_val"])

    ficha_data = [
        # Fila 1: labels
        [_p_lbl("Apellido"), _p_lbl("Nombre"), _p_lbl("DNI / Cédula"), _p_lbl("Fec. Nacimiento")],
        # Fila 1: valores
        [
            _p_val(paciente.get("apellido","")),
            _p_val(paciente.get("nombre","")),
            _p_val(paciente.get("dni","")),
            _p_val(paciente.get("fecha_nac","")),
        ],
        # Fila 2: labels
        [_p_lbl("Grupo Sanguíneo"), _p_lbl("Teléfono"), _p_lbl("Correo electrónico"), _p_lbl("Obra Social")],
        # Fila 2: valores
        [
            _p_val(paciente.get("grupo_sangre","")),
            _p_val(paciente.get("telefono","")),
            _p_val(paciente.get("email","")),
            _p_val(paciente.get("obra_social","")),
        ],
        # Fila 3: labels
        [_p_lbl("Nro. Afiliado"), _p_lbl("Dirección"), _p_lbl("Alergias conocidas"), _p_lbl("Nro Afiliado")],
        # Fila 3: valores
        [
            _p_val(paciente.get("nro_afiliado","")),
            _p_val(paciente.get("direccion","")),
            _p_val(paciente.get("alergias","")),
            _p_val(""),
        ],
    ]

    # Unir celdas para que dirección y alergias abarquen más
    ficha_table = Table(
        [
            [_p_lbl("Apellido"), _p_lbl("Nombre"), _p_lbl("DNI"), _p_lbl("Fec. nacimiento")],
            [
                _p_val(paciente.get("apellido","")),
                _p_val(paciente.get("nombre","")),
                _p_val(paciente.get("dni","")),
                _p_val(paciente.get("fecha_nac","")),
            ],
            [_p_lbl("Grupo sang."), _p_lbl("Teléfono"), _p_lbl("Email"), _p_lbl("Obra social")],
            [
                _p_val(paciente.get("grupo_sangre","")),
                _p_val(paciente.get("telefono","")),
                _p_val(paciente.get("email","")),
                _p_val(paciente.get("obra_social","")),
            ],
            [_p_lbl("Nro. afiliado"), _p_lbl("Dirección"), _p_lbl("Alergias"), _p_lbl("")],
            [
                _p_val(paciente.get("nro_afiliado","")),
                _p_val(paciente.get("direccion","")),
                _p_val(paciente.get("alergias","")),
                _p_val(""),
            ],
        ],
        colWidths=[C4, C4, C4, C4],
        hAlign="LEFT",
    )
    ficha_table.setStyle(TableStyle([
        ("VALIGN",    (0, 0), (-1, -1), "TOP"),
        ("FONTNAME",  (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",  (0, 0), (-1, -1), 8),
        ("LEFTPADDING",  (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
        # Filas pares (labels) fondo azul claro
        ("BACKGROUND", (0, 0), (-1, 0), _AZUL_CLAR),
        ("BACKGROUND", (0, 2), (-1, 2), _AZUL_CLAR),
        ("BACKGROUND", (0, 4), (-1, 4), _AZUL_CLAR),
        ("BOX",  (0, 0), (-1, -1), 0.5, _GRIS_LIN),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, _GRIS_LIN),
        # Span dirección y alergias en fila 5 (índice 4,5)
        ("SPAN", (1, 4), (2, 4)),
        ("SPAN", (1, 5), (2, 5)),
    ]))
    historia_items += [ficha_table, Spacer(1, 8)]

    # ══════════════════════════════════════════════════════════════════════
    # SECCIÓN 2: ANAMNESIS
    # ══════════════════════════════════════════════════════════════════════
    historia_items.append(_titulo_seccion("2. ANAMNESIS", st))

    # ── 2a. Antecedentes ──────────────────────────────────────────────────
    ant_dict = historia.get("antecedentes") or {}
    historia_items.append(
        Paragraph("ANTECEDENTES MÉDICOS Y ODONTOLÓGICOS", st["campo_lbl"])
    )
    historia_items.append(Spacer(1, 2))

    # Tabla de antecedentes: 3 columnas (7 + 7 + 7 = 21 items)
    COLS_ANT = 3
    ant_rows = []
    fila = []
    for i, (key, label) in enumerate(ANTECEDENTES):
        positivo = bool(ant_dict.get(key, False))
        simbolo  = "✓" if positivo else "○"
        est      = "ant_pos" if positivo else "ant_neg"
        fila.append(Paragraph(f"{simbolo}  {label}", st[est]))
        if len(fila) == COLS_ANT:
            ant_rows.append(fila)
            fila = []
    if fila:
        while len(fila) < COLS_ANT:
            fila.append(Paragraph("", st["ant_neg"]))
        ant_rows.append(fila)

    ant_table = Table(ant_rows, colWidths=[W / COLS_ANT] * COLS_ANT, hAlign="LEFT")
    ant_table.setStyle(TableStyle([
        ("VALIGN",    (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING",   (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 2),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [_GRIS_BG, white]),
        ("BOX",  (0, 0), (-1, -1), 0.4, _GRIS_LIN),
        ("INNERGRID", (0, 0), (-1, -1), 0.2, _GRIS_LIN),
    ]))
    historia_items += [ant_table, Spacer(1, 6)]

    # ── 2b. Constantes vitales ────────────────────────────────────────────
    sv  = historia.get("signos_vitales") or {}
    try:
        p  = float(sv.get("peso","0").replace(",",".") or 0)
        ta = float(sv.get("estatura","0").replace(",",".") or 0)
        imc_val = f"{p/(ta/100)**2:.1f}" if p > 0 and ta > 0 else "—"
    except Exception:
        imc_val = "—"

    sv_data = [
        [_p_lbl("Presión"), _p_lbl("Pulso"), _p_lbl("Temperatura"),
         _p_lbl("F. Respiratoria"), _p_lbl("Peso"), _p_lbl("Talla"), _p_lbl("IMC")],
        [
            _p_val(sv.get("tension_arterial","")),
            _p_val(sv.get("pulso","")),
            _p_val(sv.get("temperatura","")),
            _p_val(sv.get("frecuencia_resp","")),
            _p_val(sv.get("peso","") + " kg" if sv.get("peso") else "—"),
            _p_val(sv.get("estatura","") + " cm" if sv.get("estatura") else "—"),
            _p_val(imc_val),
        ],
    ]
    sv_table = Table(sv_data, colWidths=[W/7]*7, hAlign="LEFT")
    sv_table.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
        ("BACKGROUND",   (0, 0), (-1, 0), _AZUL_CLAR),
        ("BOX",  (0, 0), (-1, -1), 0.5, _GRIS_LIN),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, _GRIS_LIN),
    ]))
    historia_items += [
        Paragraph("CONSTANTES VITALES", st["campo_lbl"]),
        Spacer(1, 2),
        sv_table,
        Spacer(1, 6),
    ]

    # ── 2c. Datos de la consulta (Exploración) ────────────────────────────
    historia_items.append(Paragraph("DATOS DE LA CONSULTA", st["campo_lbl"]))
    historia_items.append(Spacer(1, 2))

    consul_data = [
        [_p_lbl("N° Historia"), _p_lbl("Odontólogo responsable"), _p_lbl("Fecha")],
        [
            _p_val(historia.get("historia_no","")),
            _p_val(historia.get("odontologo","")),
            _p_val(historia.get("fecha_elaboracion","")),
        ],
    ]
    consul_table = Table(consul_data, colWidths=[W*0.2, W*0.5, W*0.3], hAlign="LEFT")
    consul_table.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
        ("BACKGROUND",   (0, 0), (-1, 0), _AZUL_CLAR),
        ("BOX",  (0, 0), (-1, -1), 0.5, _GRIS_LIN),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, _GRIS_LIN),
    ]))
    historia_items += [consul_table, Spacer(1, 4)]

    for lbl, key in [
        ("Motivo de consulta",                   "motivo_consulta"),
        ("Enfermedad actual / Hallazgos clínicos","enfermedad_actual"),
        ("Observaciones y plan de tratamiento",   "observaciones"),
    ]:
        val = (historia.get(key) or "").strip() or "—"
        ml_table = Table(
            [
                [Paragraph(lbl.upper(), st["campo_lbl"])],
                [Paragraph(val.replace("\n", "<br/>"), st["campo_val_ml"])],
            ],
            colWidths=[W],
            hAlign="LEFT",
        )
        ml_table.setStyle(TableStyle([
            ("LEFTPADDING",  (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING",   (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
            ("BACKGROUND",   (0, 0), (-1, 0), _AZUL_CLAR),
            ("BOX",  (0, 0), (-1, -1), 0.5, _GRIS_LIN),
        ]))
        historia_items += [ml_table, Spacer(1, 4)]

    historia_items.append(Spacer(1, 4))

    # ══════════════════════════════════════════════════════════════════════
    # SECCIÓN 3: ODONTOGRAMA
    # ══════════════════════════════════════════════════════════════════════
    historia_items.append(_titulo_seccion("3. ODONTOGRAMA", st))
    historia_items.append(Spacer(1, 4))
    historia_items.append(_OdontogramaFlowable(odonto, W))

    # ── Pie de página inline ──────────────────────────────────────────────
    historia_items += [
        Spacer(1, 10),
        HRFlowable(width=W, thickness=0.5, color=_GRIS_LIN),
        Spacer(1, 3),
        Paragraph(
            f"Documento generado el {fecha_hoy}  ·  Confidencial — uso exclusivo del profesional",
            ParagraphStyle("pie", fontSize=6, textColor=_TEXTO_GRI, alignment=TA_CENTER),
        ),
    ]

    # ── Construir PDF ─────────────────────────────────────────────────────
    doc.build(historia_items)
    return ruta_pdf


# ═══════════════════════════════════════════════════════════════════════════════
#  REPORTES GENERALES
# ═══════════════════════════════════════════════════════════════════════════════

def _doc_reporte(nombre_archivo: str, titulo: str, subtitulo: str,
                 output_dir: str) -> tuple:
    """Crea un SimpleDocTemplate y devuelve (doc, items_iniciales, ancho_util, estilos)."""
    margen_h = 15 * mm
    margen_v = 12 * mm
    ruta     = os.path.join(output_dir, nombre_archivo)
    os.makedirs(output_dir, exist_ok=True)
    doc = SimpleDocTemplate(
        ruta,
        pagesize=A4,
        leftMargin=margen_h, rightMargin=margen_h,
        topMargin=margen_v,  bottomMargin=margen_v,
    )
    W    = A4[0] - 2 * margen_h
    st   = _estilos()
    hoy  = datetime.today().strftime("%d/%m/%Y  %H:%M")

    items = [
        Paragraph("CONSULTORIO ODONTOLÓGICO", st["header_titulo"]),
        Paragraph(titulo, st["header_sub"]),
        Paragraph(subtitulo, ParagraphStyle(
            "sub2", fontSize=8, textColor=_TEXTO_GRI, alignment=TA_CENTER)),
        Spacer(1, 4),
        HRFlowable(width=W, thickness=1.5, color=_AZUL_OSC),
        Paragraph(
            f"Generado: {hoy}",
            ParagraphStyle("gen_date", fontSize=7, textColor=_TEXTO_GRI,
                           alignment=TA_RIGHT),
        ),
        Spacer(1, 6),
    ]
    return doc, items, W, st


def _tabla_reporte(encabezados: list[str], filas_data: list[list],
                   col_widths: list[float]) -> Table:
    """Tabla de datos estándar para reportes."""
    from reportlab.lib.colors import HexColor as HC
    def _p(txt, bold=False):
        return Paragraph(str(txt) if txt is not None else "—",
                         ParagraphStyle(
                             "tc", fontSize=7.5,
                             fontName="Helvetica-Bold" if bold else "Helvetica",
                             textColor=_TEXTO_OSC if not bold else HC("#FFFFFF"),
                         ))

    cabecera = [_p(h, bold=True) for h in encabezados]
    datos    = [[_p(c) for c in fila] for fila in filas_data]
    tabla    = Table([cabecera] + datos, colWidths=col_widths, repeatRows=1)
    n        = len(datos)
    estilos  = [
        ("BACKGROUND", (0, 0), (-1, 0), _AZUL_OSC),
        ("TEXTCOLOR",  (0, 0), (-1, 0), HexColor("#FFFFFF")),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 7.5),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ("BOX",  (0, 0), (-1, -1), 0.5, _GRIS_LIN),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, _GRIS_LIN),
    ]
    for i in range(n):
        if i % 2 == 0:
            estilos.append(("BACKGROUND", (0, i+1), (-1, i+1), _AZUL_CLAR))
        else:
            estilos.append(("BACKGROUND", (0, i+1), (-1, i+1), HexColor("#FFFFFF")))
    tabla.setStyle(TableStyle(estilos))
    return tabla


def _fmt_fecha_pdf(iso: str) -> str:
    if not iso:
        return "—"
    try:
        return datetime.fromisoformat(
            iso.replace("Z", "+00:00")).strftime("%d/%m/%Y")
    except Exception:
        return str(iso)[:10]


def _fmt_monto_pdf(v) -> str:
    try:
        return f"$ {float(v):,.2f}"
    except Exception:
        return "$ 0,00"


def _pie_reporte(hoy: str, W: float) -> list:
    return [
        Spacer(1, 8),
        HRFlowable(width=W, thickness=0.5, color=_GRIS_LIN),
        Spacer(1, 3),
        Paragraph(
            f"Documento generado el {hoy}  ·  Confidencial — uso exclusivo del profesional",
            ParagraphStyle("pie_r", fontSize=6, textColor=_TEXTO_GRI,
                           alignment=TA_CENTER),
        ),
    ]


# ── REPORTE DE CITAS ──────────────────────────────────────────────────────────

def exportar_reporte_citas(datos: list[dict], fecha_desde: str, fecha_hasta: str,
                            output_dir: str | None = None) -> str:
    output_dir = output_dir or os.path.join(os.path.dirname(__file__), "pdfs")
    nombre = f"Reporte_Citas_{fecha_desde}_al_{fecha_hasta}.pdf".replace("/","")
    hoy    = datetime.today().strftime("%d/%m/%Y  %H:%M")

    doc, items, W, st = _doc_reporte(
        nombre,
        "Reporte de Citas",
        f"Período: {fecha_desde}  →  {fecha_hasta}",
        output_dir,
    )

    encabezados = ["Fecha", "Hora", "Paciente", "Especialista", "Motivo", "Estado"]
    col_w = [W*0.1, W*0.07, W*0.2, W*0.2, W*0.28, W*0.15]

    filas = []
    est_count: dict[str, int] = {}
    for c in datos:
        pac = (c.get("pacientes") or {})
        esp = (c.get("especialistas") or {})
        nom_pac = f"{pac.get('apellido','')} {pac.get('nombre','')}".strip()
        nom_esp = f"{esp.get('apellido','')} {esp.get('nombre','')}".strip()
        iso = c.get("fecha_hora","")
        try:
            dt    = datetime.fromisoformat(iso.replace("Z","+00:00"))
            fecha = dt.strftime("%d/%m/%Y")
            hora  = dt.strftime("%H:%M")
        except Exception:
            fecha = iso[:10]; hora = ""
        estado = c.get("estado","")
        est_count[estado] = est_count.get(estado, 0) + 1
        filas.append([fecha, hora, nom_pac or "—", nom_esp or "—",
                      c.get("motivo","") or "—", estado.capitalize()])

    items.append(_tabla_reporte(encabezados, filas, col_w))
    items.append(Spacer(1, 8))

    resumen_txt = "  |  ".join(f"{n} {est}" for est, n in sorted(est_count.items()))
    items.append(Paragraph(
        f"Total: {len(datos)} citas  —  {resumen_txt}",
        ParagraphStyle("tot_c", fontSize=8, fontName="Helvetica-Bold",
                       textColor=_AZUL_OSC),
    ))
    items += _pie_reporte(hoy, W)

    doc.build(items)
    return os.path.join(output_dir, nombre)


# ── REPORTE DE INGRESOS ───────────────────────────────────────────────────────

def exportar_reporte_ingresos(datos: list[dict], fecha_desde: str, fecha_hasta: str,
                               output_dir: str | None = None) -> str:
    output_dir = output_dir or os.path.join(os.path.dirname(__file__), "pdfs")
    nombre = f"Reporte_Ingresos_{fecha_desde}_al_{fecha_hasta}.pdf".replace("/","")
    hoy    = datetime.today().strftime("%d/%m/%Y  %H:%M")

    doc, items, W, st = _doc_reporte(
        nombre,
        "Reporte de Ingresos",
        f"Período: {fecha_desde}  →  {fecha_hasta}",
        output_dir,
    )

    encabezados = ["Fecha", "Paciente", "Tratamiento", "Monto", "Método", "Comprobante"]
    col_w = [W*0.1, W*0.22, W*0.28, W*0.12, W*0.14, W*0.14]

    total   = 0.0
    met_tot: dict[str, float] = {}
    filas   = []
    for p in datos:
        pac  = (p.get("pacientes") or {})
        tra  = (p.get("tratamientos") or {})
        nom  = f"{pac.get('apellido','')} {pac.get('nombre','')}".strip()
        met  = p.get("metodo","") or "—"
        monto = float(p.get("monto", 0))
        total += monto
        met_tot[met] = met_tot.get(met, 0) + monto
        filas.append([
            _fmt_fecha_pdf(p.get("fecha","")),
            nom or "—",
            tra.get("descripcion","") or "—",
            _fmt_monto_pdf(monto),
            met.replace("_"," ").capitalize(),
            p.get("comprobante","") or "—",
        ])

    items.append(_tabla_reporte(encabezados, filas, col_w))
    items.append(Spacer(1, 8))

    met_txt = "  |  ".join(
        f"{m.replace('_',' ').capitalize()}: {_fmt_monto_pdf(v)}"
        for m, v in sorted(met_tot.items())
    )
    items.append(Paragraph(
        f"TOTAL RECAUDADO: {_fmt_monto_pdf(total)}",
        ParagraphStyle("tot_ing", fontSize=10, fontName="Helvetica-Bold",
                       textColor=HexColor("#1B5E20")),
    ))
    if met_txt:
        items.append(Paragraph(
            met_txt,
            ParagraphStyle("met_t", fontSize=7.5, textColor=_TEXTO_GRI),
        ))
    items += _pie_reporte(hoy, W)

    doc.build(items)
    return os.path.join(output_dir, nombre)


# ── REPORTE DE TRATAMIENTOS ───────────────────────────────────────────────────

def exportar_reporte_tratamientos(datos: list[dict], estado_filtro: str = "",
                                   output_dir: str | None = None) -> str:
    output_dir = output_dir or os.path.join(os.path.dirname(__file__), "pdfs")
    sufijo  = f"_{estado_filtro}" if estado_filtro else "_todos"
    nombre  = f"Reporte_Tratamientos{sufijo}.pdf"
    hoy     = datetime.today().strftime("%d/%m/%Y  %H:%M")
    subtitulo = f"Estado: {estado_filtro.capitalize()}" if estado_filtro else "Todos los estados"

    doc, items, W, st = _doc_reporte(
        nombre, "Reporte de Tratamientos", subtitulo, output_dir,
    )

    resumen: dict[str, dict] = {"presupuestado":{"n":0,"total":0},
                                 "aprobado":{"n":0,"total":0},
                                 "realizado":{"n":0,"total":0}}
    for t in datos:
        est = t.get("estado","")
        if est in resumen:
            resumen[est]["n"]     += 1
            resumen[est]["total"] += float(t.get("costo", 0))

    etiq = {"presupuestado":"Presupuestados","aprobado":"Aprobados","realizado":"Realizados"}
    res_data = [
        [etiq.get(e, e), str(v["n"]), _fmt_monto_pdf(v["total"])]
        for e, v in resumen.items()
    ]
    items.append(Paragraph("RESUMEN POR ESTADO", ParagraphStyle(
        "sec_h", fontSize=9, fontName="Helvetica-Bold",
        textColor=_AZUL_OSC, spaceBefore=2, spaceAfter=4)))
    items.append(_tabla_reporte(
        ["Estado","Cantidad","Total"],
        res_data,
        [W*0.4, W*0.2, W*0.4],
    ))
    items.append(Spacer(1, 10))

    encabezados = ["Fecha","Paciente","Descripción","Diente","Especialista","Costo","Estado"]
    col_w = [W*0.09, W*0.18, W*0.24, W*0.06, W*0.18, W*0.12, W*0.13]
    filas = []
    for t in datos:
        pac = (t.get("pacientes") or {})
        esp = (t.get("especialistas") or {})
        nom_pac = f"{pac.get('apellido','')} {pac.get('nombre','')}".strip()
        nom_esp = f"{esp.get('apellido','')} {esp.get('nombre','')}".strip()
        filas.append([
            _fmt_fecha_pdf(t.get("fecha","")),
            nom_pac or "—",
            t.get("descripcion","") or "—",
            str(t.get("diente","")) if t.get("diente") else "—",
            nom_esp or "—",
            _fmt_monto_pdf(t.get("costo",0)),
            (t.get("estado","")).capitalize(),
        ])

    items.append(Paragraph("DETALLE DE TRATAMIENTOS", ParagraphStyle(
        "sec_h2", fontSize=9, fontName="Helvetica-Bold",
        textColor=_AZUL_OSC, spaceBefore=2, spaceAfter=4)))
    items.append(_tabla_reporte(encabezados, filas, col_w))
    items.append(Spacer(1, 6))
    gran_total = sum(float(t.get("costo",0)) for t in datos)
    items.append(Paragraph(
        f"TOTAL GENERAL: {_fmt_monto_pdf(gran_total)}  ({len(datos)} tratamientos)",
        ParagraphStyle("tot_tr", fontSize=9, fontName="Helvetica-Bold",
                       textColor=_AZUL_OSC),
    ))
    items += _pie_reporte(hoy, W)

    doc.build(items)
    return os.path.join(output_dir, nombre)
