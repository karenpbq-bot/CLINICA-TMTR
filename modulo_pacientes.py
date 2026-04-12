"""
Módulo de Pacientes: Ficha Clínica + Odontograma Interactivo.
"""

import flet as ft
from database import (
    listar_pacientes,
    obtener_paciente,
    crear_paciente,
    actualizar_paciente,
    obtener_odontograma,
    guardar_diente,
    listar_constantes,
    registrar_constante,
)

# ── Colores por estado del diente ─────────────────────────────────────────
ESTADOS_DIENTE = {
    "sano":       {"color": ft.colors.WHITE, "borde": ft.colors.GREY_400, "label": "Sano"},
    "caries":     {"color": ft.colors.RED_300, "borde": ft.colors.RED_700, "label": "Caries"},
    "obturado":   {"color": ft.colors.BLUE_300, "borde": ft.colors.BLUE_700, "label": "Obturado"},
    "fractura":   {"color": ft.colors.ORANGE_300, "borde": ft.colors.ORANGE_700, "label": "Fractura"},
    "extraccion": {"color": ft.colors.PURPLE_300, "borde": ft.colors.PURPLE_700, "label": "Extracción"},
    "corona":     {"color": ft.colors.YELLOW_300, "borde": ft.colors.YELLOW_700, "label": "Corona"},
    "implante":   {"color": ft.colors.GREEN_300, "borde": ft.colors.GREEN_700, "label": "Implante"},
    "ausente":    {"color": ft.colors.GREY_300, "borde": ft.colors.GREY_600, "label": "Ausente"},
}

CARAS = ["oclusal", "vestibular", "lingual", "mesial", "distal"]

# Numeración FDI: adulto superior derecho → izquierdo, inferior izquierdo → derecho
DIENTES_ADULTO = [
    [18, 17, 16, 15, 14, 13, 12, 11, 21, 22, 23, 24, 25, 26, 27, 28],  # superior
    [48, 47, 46, 45, 44, 43, 42, 41, 31, 32, 33, 34, 35, 36, 37, 38],  # inferior
]


# ── Odontograma ───────────────────────────────────────────────────────────

class DienteWidget(ft.UserControl):
    """Representa un diente con 5 caras clicables."""

    def __init__(self, numero: int, caras_estado: dict, on_change):
        super().__init__()
        self.numero = numero
        self.caras_estado = {c: caras_estado.get(c, "sano") for c in CARAS}
        self.on_change = on_change

    def cara_btn(self, cara: str):
        estado = self.caras_estado[cara]
        cfg = ESTADOS_DIENTE[estado]
        return ft.Container(
            width=16, height=16,
            bgcolor=cfg["color"],
            border=ft.border.all(1, cfg["borde"]),
            border_radius=2,
            tooltip=f"{cara.capitalize()} – {cfg['label']}",
            on_click=lambda e, c=cara: self.ciclar_estado(c),
        )

    def ciclar_estado(self, cara: str):
        estados = list(ESTADOS_DIENTE.keys())
        actual = self.caras_estado[cara]
        siguiente = estados[(estados.index(actual) + 1) % len(estados)]
        self.caras_estado[cara] = siguiente
        self.on_change(self.numero, self.caras_estado.copy())
        self.update()

    def build(self):
        return ft.Column(
            controls=[
                self.cara_btn("vestibular"),
                ft.Row(
                    controls=[
                        self.cara_btn("mesial"),
                        self.cara_btn("oclusal"),
                        self.cara_btn("distal"),
                    ],
                    spacing=1,
                ),
                self.cara_btn("lingual"),
                ft.Text(str(self.numero), size=8, text_align=ft.TextAlign.CENTER),
            ],
            spacing=1,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )


class OdontogramaView(ft.UserControl):
    """Cuadrícula interactiva de 32 dientes adultos."""

    def __init__(self, paciente_id: str):
        super().__init__()
        self.paciente_id = paciente_id
        self.datos = {}

    def did_mount(self):
        filas = obtener_odontograma(self.paciente_id)
        self.datos = {r["diente"]: r["caras"] for r in filas}
        self.update()

    def on_diente_cambio(self, numero: int, caras: dict):
        guardar_diente(self.paciente_id, numero, caras)
        self.datos[numero] = caras

    def fila_dientes(self, numeros: list[int]):
        return ft.Row(
            controls=[
                DienteWidget(
                    n,
                    self.datos.get(n, {c: "sano" for c in CARAS}),
                    self.on_diente_cambio,
                )
                for n in numeros
            ],
            spacing=4,
            wrap=True,
        )

    def leyenda(self):
        return ft.Row(
            controls=[
                ft.Row(
                    controls=[
                        ft.Container(width=12, height=12, bgcolor=v["color"],
                                     border=ft.border.all(1, v["borde"])),
                        ft.Text(v["label"], size=10),
                    ],
                    spacing=4,
                )
                for v in ESTADOS_DIENTE.values()
            ],
            wrap=True,
            spacing=12,
        )

    def build(self):
        return ft.Column(
            controls=[
                ft.Text("Odontograma", size=16, weight=ft.FontWeight.BOLD),
                ft.Text("Superior", size=12, color=ft.colors.GREY_600),
                self.fila_dientes(DIENTES_ADULTO[0]),
                ft.Divider(),
                ft.Text("Inferior", size=12, color=ft.colors.GREY_600),
                self.fila_dientes(DIENTES_ADULTO[1]),
                ft.Divider(),
                ft.Text("Leyenda (clic en cada cara para cambiar estado):",
                        size=11, color=ft.colors.GREY_600),
                self.leyenda(),
            ],
            spacing=8,
        )


# ── Ficha Clínica ─────────────────────────────────────────────────────────

class FichaClinicaView(ft.UserControl):
    """Formulario de ficha clínica basado en estándares médicos."""

    def __init__(self, paciente: dict):
        super().__init__()
        self.paciente = paciente

    def build(self):
        p = self.paciente
        return ft.Column(
            controls=[
                ft.Text("Identificación", size=14, weight=ft.FontWeight.BOLD),
                ft.ResponsiveRow(controls=[
                    ft.TextField(label="Nombre", value=p.get("nombre", ""), col={"sm": 6}),
                    ft.TextField(label="Apellido", value=p.get("apellido", ""), col={"sm": 6}),
                    ft.TextField(label="DNI", value=p.get("dni", ""), col={"sm": 4}),
                    ft.TextField(label="Fecha de Nac.", value=p.get("fecha_nac", ""), col={"sm": 4}),
                    ft.TextField(label="Grupo Sanguíneo", value=p.get("grupo_sangre", ""), col={"sm": 4}),
                    ft.TextField(label="Teléfono", value=p.get("telefono", ""), col={"sm": 6}),
                    ft.TextField(label="Email", value=p.get("email", ""), col={"sm": 6}),
                    ft.TextField(label="Obra Social", value=p.get("obra_social", ""), col={"sm": 6}),
                    ft.TextField(label="Nº Afiliado", value=p.get("nro_afiliado", ""), col={"sm": 6}),
                    ft.TextField(label="Dirección", value=p.get("direccion", ""), col={"sm": 12}),
                ]),
                ft.Divider(),
                ft.Text("Antecedentes Médicos", size=14, weight=ft.FontWeight.BOLD),
                ft.ResponsiveRow(controls=[
                    ft.Checkbox(label="Diabetes", col={"sm": 4}),
                    ft.Checkbox(label="Hipertensión", col={"sm": 4}),
                    ft.Checkbox(label="Cardiopatías", col={"sm": 4}),
                    ft.Checkbox(label="Coagulopatías", col={"sm": 4}),
                    ft.Checkbox(label="Embarazo", col={"sm": 4}),
                    ft.Checkbox(label="Medicación habitual", col={"sm": 4}),
                ]),
                ft.TextField(label="Alergias / Medicamentos actuales",
                             value=p.get("alergias", ""), multiline=True, min_lines=2),
                ft.Divider(),
                ft.Text("Constantes Vitales", size=14, weight=ft.FontWeight.BOLD),
                ft.ResponsiveRow(controls=[
                    ft.TextField(label="Presión Sistólica (mmHg)", col={"sm": 4}),
                    ft.TextField(label="Presión Diastólica (mmHg)", col={"sm": 4}),
                    ft.TextField(label="Pulso (lpm)", col={"sm": 4}),
                    ft.TextField(label="Peso (kg)", col={"sm": 4}),
                    ft.TextField(label="Altura (cm)", col={"sm": 4}),
                    ft.TextField(label="IMC (calculado)", read_only=True, col={"sm": 4}),
                ]),
                ft.ElevatedButton("Guardar Ficha", icon=ft.icons.SAVE),
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
        )


# ── Vista principal del módulo ────────────────────────────────────────────

class PacientesView(ft.UserControl):
    """Vista principal: lista de pacientes + ficha + odontograma."""

    def __init__(self):
        super().__init__()
        self.paciente_seleccionado = None
        self.lista_refs = []

    def build(self):
        self.lista_column = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO)
        self.detalle = ft.Column(expand=True, visible=False)

        self.cargar_lista()

        return ft.Row(
            controls=[
                ft.Container(
                    content=ft.Column(controls=[
                        ft.TextField(
                            label="Buscar paciente",
                            prefix_icon=ft.icons.SEARCH,
                            on_change=self.filtrar,
                            expand=True,
                        ),
                        ft.ElevatedButton("+ Nuevo Paciente", on_click=self.nuevo_paciente),
                        self.lista_column,
                    ], spacing=8),
                    width=280,
                    padding=8,
                ),
                ft.VerticalDivider(width=1),
                ft.Container(content=self.detalle, expand=True, padding=8),
            ],
            expand=True,
        )

    def cargar_lista(self):
        self.lista_column.controls.clear()
        pacientes = listar_pacientes()
        for p in pacientes:
            self.lista_column.controls.append(
                ft.ListTile(
                    title=ft.Text(f"{p['apellido']}, {p['nombre']}"),
                    subtitle=ft.Text(p.get("dni", "")),
                    on_click=lambda e, pac=p: self.seleccionar_paciente(pac),
                )
            )

    def seleccionar_paciente(self, paciente: dict):
        self.paciente_seleccionado = paciente
        self.detalle.visible = True
        self.detalle.controls = [
            ft.Tabs(
                tabs=[
                    ft.Tab(text="Ficha Clínica",
                           content=FichaClinicaView(paciente)),
                    ft.Tab(text="Odontograma",
                           content=OdontogramaView(paciente["id"])),
                ],
            )
        ]
        self.update()

    def nuevo_paciente(self, e):
        self.seleccionar_paciente({})

    def filtrar(self, e):
        # TODO: implementar búsqueda local o en Supabase
        pass
