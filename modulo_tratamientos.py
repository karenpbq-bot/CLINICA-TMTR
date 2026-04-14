"""
Módulo de Tratamientos — Plan de Tratamientos con odontograma de referencia.
Flet 0.84 compatible.
"""

import flet as ft
from database import (
    listar_tratamientos, crear_tratamiento, actualizar_tratamiento,
    eliminar_tratamiento, listar_pacientes, listar_especialistas,
    obtener_odontograma,
)

# ── Constantes ────────────────────────────────────────────────────────────────

ESTADOS_TRATAMIENTO = {
    "presupuestado": "Presupuestado",
    "aprobado":      "Aprobado",
    "realizado":     "Realizado",
}
ESTADO_COLOR = {
    "presupuestado": "#FFF3E0",
    "aprobado":      "#E3F2FD",
    "realizado":     "#E8F5E9",
}
ESTADO_BADGE_COLOR = {
    "presupuestado": "#E65100",
    "aprobado":      "#1565C0",
    "realizado":     "#2E7D32",
}
TIPOS_TRATAMIENTO = [
    "Consulta / Revisión", "Limpieza / Profilaxis",
    "Obturación (Resina)", "Obturación (Amalgama)",
    "Endodoncia", "Extracción Simple", "Extracción Quirúrgica",
    "Corona Porcelana", "Corona Metal-Porcelana", "Implante Dental",
    "Carilla Porcelana", "Ortodoncia – Cuota mensual",
    "Blanqueamiento", "Placa Miorelajante",
    "Radiografía Periapical", "Radiografía Panorámica", "Otro",
]

# Colores del odontograma (deben coincidir con modulo_pacientes)
_ESTADOS_DIENTE = {
    "sano":      {"color": "#FFFFFF", "borde": "#BDBDBD"},
    "caries":    {"color": "#E53935", "borde": "#B71C1C"},
    "obturado":  {"color": "#1E88E5", "borde": "#0D47A1"},
    "ausente":   {"color": "#37474F", "borde": "#000000"},
    "corona":    {"color": "#FDD835", "borde": "#F57F17"},
    "fractura":  {"color": "#FF6D00", "borde": "#BF360C"},
    "extraccion":{"color": "#37474F", "borde": "#000000"},
    "implante":  {"color": "#81C784", "borde": "#2E7D32"},
}
_CARAS = ["oclusal", "vestibular", "lingual", "mesial", "distal"]
_DIENTES_ADULTO = [
    [18, 17, 16, 15, 14, 13, 12, 11, 21, 22, 23, 24, 25, 26, 27, 28],
    [48, 47, 46, 45, 44, 43, 42, 41, 31, 32, 33, 34, 35, 36, 37, 38],
]
_DIENTES_DECIDUOS = [
    [55, 54, 53, 52, 51, 61, 62, 63, 64, 65],
    [85, 84, 83, 82, 81, 71, 72, 73, 74, 75],
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _badge_estado(estado: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(
            ESTADOS_TRATAMIENTO.get(estado, estado),
            size=10, color="#FFFFFF", weight=ft.FontWeight.W_500,
        ),
        bgcolor=ESTADO_BADGE_COLOR.get(estado, "#757575"),
        border_radius=10, padding=ft.padding.symmetric(horizontal=8, vertical=2),
    )


# ── Odontograma mini (sólo lectura) ───────────────────────────────────────────

class _DienteMini(ft.Column):
    """Diente en miniatura — sólo visual, sin interacción."""
    SZ = 7   # alto de franjas (px)
    SW = 6   # ancho por cara (px)

    def __init__(self, numero: int, caras: dict):
        super().__init__(spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        self.numero = numero
        self.caras  = {c: caras.get(c, "sano") for c in _CARAS}
        self._construir()

    def _celda(self, cara: str, w: int, h: int) -> ft.Container:
        cfg = _ESTADOS_DIENTE.get(self.caras.get(cara, "sano"), _ESTADOS_DIENTE["sano"])
        return ft.Container(
            width=w, height=h,
            bgcolor=cfg["color"],
            border=ft.border.all(0.4, cfg["borde"]),
            tooltip=cara,
        )

    def _construir(self):
        W = self.SW * 3
        H = self.SZ
        rect = ft.Container(
            content=ft.Column(controls=[
                self._celda("vestibular", W, H),
                ft.Row(controls=[
                    self._celda("mesial",  self.SW, self.SW),
                    self._celda("oclusal", self.SW, self.SW),
                    self._celda("distal",  self.SW, self.SW),
                ], spacing=0),
                self._celda("lingual", W, H),
            ], spacing=0),
            border=ft.border.all(0.8, "#90A4AE"),
            border_radius=1,
        )
        self.controls = [
            rect,
            ft.Container(
                content=ft.Text(str(self.numero), size=6, color="#455A64",
                                text_align=ft.TextAlign.CENTER),
                width=W, alignment=ft.Alignment(0, 0),
            ),
        ]


class _OdontogramaRef(ft.Column):
    """
    Odontograma de referencia (sólo lectura, escala reducida).
    Siempre visible — sin toggle. Carga datos via did_mount().
    """

    def __init__(self, paciente_id: str):
        super().__init__(spacing=4)
        self.paciente_id = paciente_id
        self._datos: dict = {}
        self._cuerpo = ft.Container()

        self.controls = [
            ft.Container(
                content=ft.Row(controls=[
                    ft.Icon(ft.Icons.GRID_VIEW, size=14, color="#1565C0"),
                    ft.Text("Odontograma de referencia",
                            size=12, color="#1565C0", weight=ft.FontWeight.W_500),
                    ft.Text("(solo lectura)", size=10, color="#9E9E9E", italic=True),
                ], spacing=6),
                border=ft.border.all(1, "#BBDEFB"),
                border_radius=ft.border_radius.only(top_left=6, top_right=6),
                bgcolor="#E3F2FD",
                padding=ft.padding.symmetric(horizontal=10, vertical=6),
            ),
            self._cuerpo,
        ]

    def did_mount(self):
        try:
            filas = obtener_odontograma(self.paciente_id)
            self._datos = {r["diente"]: r.get("caras", {}) for r in filas}
        except Exception:
            self._datos = {}
        self._cuerpo.content = self._construir_grid()
        if self.page:
            self.update()

    def _fila_etiqueta(self, texto: str, color: str) -> ft.Container:
        return ft.Container(
            content=ft.Text(texto, size=8, color="#616161"),
            bgcolor=color, border_radius=2,
            padding=ft.padding.symmetric(horizontal=4, vertical=1),
            margin=ft.margin.only(bottom=1),
        )

    def _fila_dientes(self, numeros: list) -> ft.Row:
        return ft.Row(
            controls=[
                ft.Container(
                    content=_DienteMini(n, self._datos.get(n, {})),
                    padding=ft.padding.symmetric(horizontal=1),
                )
                for n in numeros
            ],
            spacing=0,
        )

    def _construir_grid(self) -> ft.Container:
        leyenda = ft.Row(controls=[
            ft.Container(width=8, height=8, bgcolor=v["color"],
                         border=ft.border.all(0.5, v["borde"]), border_radius=1,
                         tooltip=k)
            for k, v in _ESTADOS_DIENTE.items()
            if k not in ("extraccion", "implante")
        ] + [
            ft.Text("← referencia visual", size=9, color="#9E9E9E", italic=True),
        ], spacing=4)

        return ft.Container(
            content=ft.Column(controls=[
                ft.Text("PERMANENTES", size=9, color="#757575",
                        weight=ft.FontWeight.W_600),
                self._fila_etiqueta("Superior  18→11 | 21→28", "#E3F2FD"),
                ft.Container(
                    content=self._fila_dientes(_DIENTES_ADULTO[0]),
                    bgcolor="#F5F9FF", border=ft.border.all(1, "#BBDEFB"),
                    border_radius=3, padding=3,
                ),
                self._fila_etiqueta("Inferior  48→41 | 31→38", "#E8F5E9"),
                ft.Container(
                    content=self._fila_dientes(_DIENTES_ADULTO[1]),
                    bgcolor="#F5FFF5", border=ft.border.all(1, "#C8E6C9"),
                    border_radius=3, padding=3,
                ),
                ft.Divider(height=4, color="#E0E0E0"),
                ft.Text("DECIDUOS", size=9, color="#757575",
                        weight=ft.FontWeight.W_600),
                self._fila_etiqueta("Superior  55→51 | 61→65", "#FFF3E0"),
                ft.Container(
                    content=self._fila_dientes(_DIENTES_DECIDUOS[0]),
                    bgcolor="#FFFDE7", border=ft.border.all(1, "#FFE082"),
                    border_radius=3, padding=3,
                ),
                self._fila_etiqueta("Inferior  85→81 | 71→75", "#FCE4EC"),
                ft.Container(
                    content=self._fila_dientes(_DIENTES_DECIDUOS[1]),
                    bgcolor="#FFF8E1", border=ft.border.all(1, "#F8BBD0"),
                    border_radius=3, padding=3,
                ),
                ft.Divider(height=4, color="#E0E0E0"),
                leyenda,
            ], spacing=3),
            padding=ft.padding.all(8),
            bgcolor="#FAFAFA",
            border=ft.border.all(1, "#E0E0E0"),
            border_radius=6,
        )


# ── Formulario de tratamiento ─────────────────────────────────────────────────

class _FormularioInline(ft.Column):
    """
    Formulario compacto para agregar/editar un tratamiento.
    Campos: Tipo, Especialista, Costo, Estado.
    Tras guardar, limpia los campos y permanece abierto para ingresar más ítems.
    """

    def __init__(self, paciente_id: str, tratamiento: dict = None,
                 on_guardado=None, snack_fn=None):
        super().__init__(spacing=8)
        self.paciente_id   = paciente_id
        self.tratamiento   = tratamiento or {}
        self.on_guardado   = on_guardado
        self.snack_fn      = snack_fn
        self._construir()

    def _construir(self):
        t = self.tratamiento
        try:
            especialistas = listar_especialistas()
        except Exception:
            especialistas = []

        self.dd_tipo = ft.Dropdown(
            label="Tipo de tratamiento *",
            value=t.get("descripcion"),
            options=[ft.dropdown.Option(tp) for tp in TIPOS_TRATAMIENTO],
            expand=True, dense=True,
        )
        self.dd_especialista = ft.Dropdown(
            label="Especialista",
            value=t.get("especialista_id"),
            options=[
                ft.dropdown.Option(
                    e["id"],
                    f"Dr/a. {e.get('apellido','')}, {e.get('nombre','')}",
                )
                for e in especialistas
            ],
            expand=True, dense=True,
        )
        self.tf_costo = ft.TextField(
            label="Costo ($)",
            value=str(t.get("costo", "0")),
            keyboard_type=ft.KeyboardType.NUMBER,
            width=130, dense=True,
        )
        self.dd_estado = ft.Dropdown(
            label="Estado",
            value=t.get("estado", "presupuestado"),
            options=[ft.dropdown.Option(k, v) for k, v in ESTADOS_TRATAMIENTO.items()],
            width=190, dense=True,
        )

        es_edicion = bool(t.get("id"))
        lbl_guardar = "Actualizar" if es_edicion else "Guardar y agregar otro"
        icono_guardar = ft.Icons.SAVE if es_edicion else ft.Icons.ADD_TASK

        self.controls = [
            ft.Container(
                content=ft.Column(controls=[
                    ft.Text(
                        "Editar ítem" if es_edicion else "Nuevo tratamiento",
                        size=13, weight=ft.FontWeight.W_600, color="#1565C0",
                    ),
                    ft.Row([self.dd_tipo, self.dd_especialista], spacing=8),
                    ft.Row([self.tf_costo, self.dd_estado], spacing=8),
                    ft.Row(controls=[
                        ft.FilledButton(
                            lbl_guardar, icon=icono_guardar,
                            on_click=self._guardar,
                        ),
                    ], spacing=8),
                ], spacing=6),
                padding=ft.padding.all(12),
                bgcolor="#EFF6FF",
                border=ft.border.all(1, "#BBDEFB"),
                border_radius=8,
            ),
        ]

    def _guardar(self, e):
        if not self.dd_tipo.value:
            if self.snack_fn:
                self.snack_fn("Seleccioná un tipo de tratamiento.", error=True)
            return
        try:
            costo = float(
                (self.tf_costo.value or "0").strip().replace(",", ".")
            )
        except ValueError:
            if self.snack_fn:
                self.snack_fn("El costo debe ser un número.", error=True)
            return

        datos = {
            "paciente_id":     self.paciente_id,
            "especialista_id": self.dd_especialista.value,
            "descripcion":     self.dd_tipo.value,
            "costo":           costo,
            "estado":          self.dd_estado.value or "presupuestado",
            "diente":          None,
            "cara":            None,
        }
        try:
            if self.tratamiento.get("id"):
                actualizar_tratamiento(self.tratamiento["id"], datos)
                if self.snack_fn:
                    self.snack_fn("Tratamiento actualizado.")
                if self.on_guardado:
                    self.on_guardado(cerrar=True)
            else:
                crear_tratamiento(datos)
                if self.snack_fn:
                    self.snack_fn("Tratamiento agregado. Podés ingresar otro.")
                # Limpiar campos para el siguiente ítem
                self.dd_tipo.value         = None
                self.dd_especialista.value = None
                self.tf_costo.value        = "0"
                self.dd_estado.value       = "presupuestado"
                if self.page:
                    self.dd_tipo.update()
                    self.dd_especialista.update()
                    self.tf_costo.update()
                    self.dd_estado.update()
                if self.on_guardado:
                    self.on_guardado(cerrar=False)
        except Exception as ex:
            if self.snack_fn:
                self.snack_fn(f"Error: {ex}", error=True)


# ── Vista principal ───────────────────────────────────────────────────────────

class TratamientosView(ft.Column):
    """
    Vista principal del módulo Tratamientos.
    Una sola vista: Plan de Tratamientos + Odontograma de referencia.
    """

    def __init__(self):
        super().__init__(spacing=0, expand=True)
        self.paciente_id: str | None           = None
        self._mostrar_form: bool               = False
        self._tratamiento_activo: dict | None  = None
        self._area = ft.Container(expand=True)
        self._construir_base()

    # ── Snack ──────────────────────────────────────────────────────────────

    def _snack(self, msg: str, error: bool = False):
        if self.page:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(msg),
                bgcolor=ft.Colors.RED_700 if error else ft.Colors.GREEN_700,
                open=True,
            )
            self.page.update()

    # ── Construcción base ──────────────────────────────────────────────────

    def _construir_base(self):
        try:
            pacientes = listar_pacientes()
        except Exception:
            pacientes = []

        self.dd_selector = ft.Dropdown(
            label="Seleccionar paciente",
            options=[
                ft.dropdown.Option(
                    p["id"],
                    f"{p.get('apellido','')}, {p.get('nombre','')}",
                )
                for p in pacientes
            ],
            on_select=self._on_selector,
            width=380,
        )

        self.controls = [
            ft.Container(
                content=ft.Column(controls=[
                    ft.Text("Plan de Tratamientos",
                            size=18, weight=ft.FontWeight.BOLD),
                    self.dd_selector,
                ], spacing=10),
                padding=ft.padding.symmetric(horizontal=16, vertical=12),
            ),
            ft.Divider(height=1, color="#E0E0E0"),
            ft.Container(content=self._area, expand=True,
                         padding=ft.padding.all(16)),
        ]

    # ── Selección de paciente ──────────────────────────────────────────────

    def _on_selector(self, e):
        self.paciente_id         = self.dd_selector.value
        self._mostrar_form       = False
        self._tratamiento_activo = None
        self._cargar_area()
        if self.controls[0].page:
            self.controls[0].update()

    # ── Carga del área principal ───────────────────────────────────────────

    def _cargar_area(self):
        if not self.paciente_id:
            return
        self._area.content = self._construir_plan()
        if self._area.page:
            self._area.update()

    # ── Vista Plan de Tratamientos ─────────────────────────────────────────

    def _construir_plan(self) -> ft.Column:
        try:
            tratamientos = listar_tratamientos(self.paciente_id)
        except Exception as ex:
            self._snack(f"Error al cargar tratamientos: {ex}", error=True)
            tratamientos = []

        # Totales
        total_presup    = sum(float(t.get("costo", 0)) for t in tratamientos
                              if t.get("estado") == "presupuestado")
        total_aprobado  = sum(float(t.get("costo", 0)) for t in tratamientos
                              if t.get("estado") == "aprobado")
        total_realizado = sum(float(t.get("costo", 0)) for t in tratamientos
                              if t.get("estado") == "realizado")
        total_global    = total_presup + total_aprobado + total_realizado

        tarjetas = ft.Row(controls=[
            self._tarjeta("Total Plan",    total_global,    "#1565C0"),
            self._tarjeta("Presupuestado", total_presup,    "#E65100"),
            self._tarjeta("Aprobado",      total_aprobado,  "#0288D1"),
            self._tarjeta("Realizado",     total_realizado, "#2E7D32"),
        ], spacing=8)

        # ── Columna izquierda: tarjetas + formulario ──────────────────────
        btn_agregar = ft.FilledButton(
            "- Cerrar formulario" if self._mostrar_form else "+ Agregar Tratamiento",
            icon=ft.Icons.REMOVE if self._mostrar_form else ft.Icons.ADD,
            on_click=lambda e: self._toggle_form(),
        )

        if self._mostrar_form:
            form_area: ft.Control = _FormularioInline(
                self.paciente_id,
                tratamiento=self._tratamiento_activo or {},
                on_guardado=self._on_guardado,
                snack_fn=self._snack,
            )
        else:
            form_area = ft.Container(height=0)

        col_izq = ft.Column(
            controls=[tarjetas, btn_agregar, form_area],
            spacing=10,
            expand=True,
        )

        # ── Columna derecha: odontograma de referencia ────────────────────
        odonto_ref = _OdontogramaRef(self.paciente_id)
        col_der = ft.Container(
            content=odonto_ref,
            width=430,
            border=ft.border.all(1, "#E0E0E0"),
            border_radius=8,
            padding=0,
        )

        panel_superior = ft.Row(
            controls=[col_izq, col_der],
            spacing=16,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

        # ── Lista de tratamientos ──────────────────────────────────────────
        items = []
        for t in tratamientos:
            estado = t.get("estado", "presupuestado")
            esp    = t.get("especialistas") or {}
            nombre_esp = (
                f"Dr/a. {esp.get('apellido','–')}, {esp.get('nombre','')}"
                if esp else "Sin especialista asignado"
            )
            items.append(ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Column(controls=[
                            ft.Row(controls=[
                                ft.Text(t.get("descripcion", ""),
                                        size=13, weight=ft.FontWeight.W_600),
                                _badge_estado(estado),
                            ], spacing=8),
                            ft.Text(nombre_esp, size=11, color="#757575"),
                        ], spacing=3, expand=True),
                        ft.Column(controls=[
                            ft.Text(f"$ {float(t.get('costo', 0)):.2f}",
                                    size=14, weight=ft.FontWeight.W_600),
                            ft.Row(controls=[
                                ft.IconButton(
                                    icon=ft.Icons.EDIT_OUTLINED,
                                    icon_size=18, icon_color=ft.Colors.BLUE_600,
                                    tooltip="Editar",
                                    on_click=lambda e, tr=t: self._editar(tr),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    icon_size=18, icon_color=ft.Colors.RED_400,
                                    tooltip="Eliminar",
                                    on_click=lambda e, tr=t: self._confirmar_eliminar(tr),
                                ),
                            ], spacing=0),
                        ], horizontal_alignment=ft.CrossAxisAlignment.END, spacing=2),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                padding=10, border_radius=6,
                bgcolor=ESTADO_COLOR.get(estado, "#F5F5F5"),
                border=ft.border.all(1, "#E0E0E0"),
            ))

        encabezado_lista = ft.Container(
            content=ft.Row(controls=[
                ft.Icon(ft.Icons.LIST_ALT, size=14, color="#1565C0"),
                ft.Text("Tratamientos del Plan", size=12,
                        color="#1565C0", weight=ft.FontWeight.W_600),
                ft.Text(f"({len(tratamientos)} ítem{'s' if len(tratamientos) != 1 else ''})",
                        size=11, color="#9E9E9E"),
            ], spacing=6),
            bgcolor="#E3F2FD",
            border=ft.border.all(1, "#BBDEFB"),
            border_radius=6,
            padding=ft.padding.symmetric(horizontal=10, vertical=6),
        )

        lista = ft.Column(
            controls=[encabezado_lista] + (
                items or [
                    ft.Container(
                        content=ft.Text("Sin tratamientos registrados.",
                                        color="#9E9E9E", italic=True),
                        padding=ft.padding.symmetric(vertical=8, horizontal=4),
                    )
                ]
            ),
            spacing=6,
        )

        return ft.Column(
            controls=[
                panel_superior,
                ft.Divider(height=6, color="#E0E0E0"),
                lista,
            ],
            spacing=12, scroll=ft.ScrollMode.AUTO,
        )

    @staticmethod
    def _tarjeta(titulo: str, monto: float, color: str) -> ft.Container:
        return ft.Container(
            content=ft.Column(controls=[
                ft.Text(titulo, size=10, color="#FAFAFA"),
                ft.Text(f"$ {monto:.2f}", size=15,
                        weight=ft.FontWeight.BOLD, color="#FFFFFF"),
            ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=color, border_radius=8, padding=10, width=140,
        )

    # ── Acciones ───────────────────────────────────────────────────────────

    def _toggle_form(self):
        self._mostrar_form = not self._mostrar_form
        if not self._mostrar_form:
            self._tratamiento_activo = None
        self._cargar_area()

    def _editar(self, tratamiento: dict):
        self._tratamiento_activo = tratamiento
        self._mostrar_form = True
        self._cargar_area()

    def _on_guardado(self, cerrar: bool = False):
        if cerrar:
            self._mostrar_form = False
            self._tratamiento_activo = None
        self._cargar_area()

    def _confirmar_eliminar(self, tratamiento: dict):
        if not self.page:
            return
        desc = tratamiento.get("descripcion", "este ítem")
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmar eliminación"),
            content=ft.Text(f"¿Eliminar «{desc}»? Esta acción no se puede deshacer."),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.page.pop_dialog()),
                ft.FilledButton(
                    "Eliminar",
                    style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700),
                    on_click=lambda e, t=tratamiento: self._eliminar(t),
                ),
            ],
        )
        self.page.show_dialog(dlg)

    def _eliminar(self, tratamiento: dict):
        if self.page:
            self.page.pop_dialog()
        try:
            eliminar_tratamiento(tratamiento["id"])
            self._snack("Ítem eliminado.")
        except Exception as ex:
            self._snack(f"Error: {ex}", error=True)
        self._on_guardado(cerrar=False)
