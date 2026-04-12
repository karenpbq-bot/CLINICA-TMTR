"""
Módulo de Pacientes: Ficha Clínica completa + Odontograma Interactivo.
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

# Numeración FDI: superior derecho→izquierdo / inferior izquierdo→derecho
DIENTES_ADULTO = [
    [18, 17, 16, 15, 14, 13, 12, 11, 21, 22, 23, 24, 25, 26, 27, 28],
    [48, 47, 46, 45, 44, 43, 42, 41, 31, 32, 33, 34, 35, 36, 37, 38],
]

ANTECEDENTES_CAMPOS = [
    ("diabetes",        "Diabetes"),
    ("hipertension",    "Hipertensión"),
    ("cardiopatias",    "Cardiopatías"),
    ("coagulopatias",   "Coagulopatías"),
    ("embarazo",        "Embarazo"),
    ("medicacion",      "Medicación habitual"),
    ("asma",            "Asma"),
    ("epilepsia",       "Epilepsia"),
]


# ── Odontograma ───────────────────────────────────────────────────────────

class DienteWidget(ft.UserControl):
    """Diente con 5 caras clicables. Clic cicla entre estados."""

    def __init__(self, numero: int, caras_estado: dict, on_change):
        super().__init__()
        self.numero = numero
        self.caras_estado = {c: caras_estado.get(c, "sano") for c in CARAS}
        self.on_change = on_change
        self._contenedores: dict[str, ft.Container] = {}

    def _hacer_cara(self, cara: str) -> ft.Container:
        estado = self.caras_estado[cara]
        cfg = ESTADOS_DIENTE[estado]
        c = ft.Container(
            width=14, height=14,
            bgcolor=cfg["color"],
            border=ft.border.all(1, cfg["borde"]),
            border_radius=2,
            tooltip=f"{cara.capitalize()} – {cfg['label']}",
            on_click=lambda e, ca=cara: self._ciclar(ca),
        )
        self._contenedores[cara] = c
        return c

    def _ciclar(self, cara: str):
        estados = list(ESTADOS_DIENTE.keys())
        actual = self.caras_estado[cara]
        sig = estados[(estados.index(actual) + 1) % len(estados)]
        self.caras_estado[cara] = sig
        cfg = ESTADOS_DIENTE[sig]
        c = self._contenedores[cara]
        c.bgcolor = cfg["color"]
        c.border = ft.border.all(1, cfg["borde"])
        c.tooltip = f"{cara.capitalize()} – {cfg['label']}"
        c.update()
        self.on_change(self.numero, dict(self.caras_estado))

    def build(self):
        return ft.Column(
            controls=[
                self._hacer_cara("vestibular"),
                ft.Row(
                    controls=[
                        self._hacer_cara("mesial"),
                        self._hacer_cara("oclusal"),
                        self._hacer_cara("distal"),
                    ],
                    spacing=1,
                ),
                self._hacer_cara("lingual"),
                ft.Text(str(self.numero), size=8,
                        text_align=ft.TextAlign.CENTER, color="#616161"),
            ],
            spacing=1,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )


class OdontogramaView(ft.UserControl):
    """Cuadrícula interactiva de 32 dientes adultos."""

    def __init__(self, paciente_id: str, snack_fn=None):
        super().__init__()
        self.paciente_id = paciente_id
        self.datos: dict[int, dict] = {}
        self.snack_fn = snack_fn

    def did_mount(self):
        filas = obtener_odontograma(self.paciente_id)
        self.datos = {r["diente"]: r["caras"] for r in filas}
        self.update()

    def _on_diente(self, numero: int, caras: dict):
        try:
            guardar_diente(self.paciente_id, numero, caras)
            self.datos[numero] = caras
        except Exception as e:
            if self.snack_fn:
                self.snack_fn(f"Error al guardar diente {numero}: {e}", error=True)

    def _fila(self, numeros: list[int]):
        return ft.Row(
            controls=[
                DienteWidget(
                    n,
                    self.datos.get(n, {c: "sano" for c in CARAS}),
                    self._on_diente,
                )
                for n in numeros
            ],
            spacing=6,
            wrap=True,
        )

    def _leyenda(self):
        return ft.Row(
            controls=[
                ft.Row(
                    controls=[
                        ft.Container(
                            width=12, height=12,
                            bgcolor=v["color"],
                            border=ft.border.all(1, v["borde"]),
                            border_radius=2,
                        ),
                        ft.Text(v["label"], size=10),
                    ],
                    spacing=4,
                )
                for v in ESTADOS_DIENTE.values()
            ],
            wrap=True,
            spacing=14,
        )

    def build(self):
        return ft.Column(
            controls=[
                ft.Text("Odontograma", size=16, weight=ft.FontWeight.BOLD),
                ft.Text("Superior (derecho → izquierdo)",
                        size=11, color="#616161"),
                self._fila(DIENTES_ADULTO[0]),
                ft.Divider(height=8),
                ft.Text("Inferior (izquierdo → derecho)",
                        size=11, color="#616161"),
                self._fila(DIENTES_ADULTO[1]),
                ft.Divider(height=8),
                ft.Text("Leyenda — clic en cada cara para cambiar estado:",
                        size=11, color="#757575"),
                self._leyenda(),
            ],
            spacing=8,
            scroll=ft.ScrollMode.AUTO,
        )


# ── Constantes Vitales ────────────────────────────────────────────────────

class ConstantesView(ft.UserControl):
    """Registro y visualización de constantes vitales con cálculo de IMC."""

    def __init__(self, paciente_id: str, snack_fn=None):
        super().__init__()
        self.paciente_id = paciente_id
        self.snack_fn = snack_fn
        self.historial: list[dict] = []

    def did_mount(self):
        self.historial = listar_constantes(self.paciente_id)
        self.update()

    def _calcular_imc(self, e=None):
        try:
            peso = float(self.tf_peso.value or 0)
            alt = float(self.tf_altura.value or 0)
            if peso > 0 and alt > 0:
                imc = peso / ((alt / 100) ** 2)
                self.tf_imc.value = f"{imc:.1f}"
                self.tf_imc.update()
        except ValueError:
            pass

    def _guardar(self, e):
        try:
            datos = {
                "paciente_id": self.paciente_id,
                "presion_sys": int(self.tf_psys.value or 0) or None,
                "presion_dia": int(self.tf_pdia.value or 0) or None,
                "pulso":       int(self.tf_pulso.value or 0) or None,
                "peso_kg":     float(self.tf_peso.value or 0) or None,
                "altura_cm":   float(self.tf_altura.value or 0) or None,
                "imc":         float(self.tf_imc.value or 0) or None,
            }
            registrar_constante(datos)
            self.historial = listar_constantes(self.paciente_id)
            # Limpiar campos
            for tf in [self.tf_psys, self.tf_pdia, self.tf_pulso,
                        self.tf_peso, self.tf_altura, self.tf_imc]:
                tf.value = ""
            if self.snack_fn:
                self.snack_fn("Constantes registradas correctamente.")
            self.update()
        except Exception as ex:
            if self.snack_fn:
                self.snack_fn(f"Error: {ex}", error=True)

    def build(self):
        self.tf_psys   = ft.TextField(label="Presión Sistólica (mmHg)",
                                      keyboard_type=ft.KeyboardType.NUMBER, expand=True)
        self.tf_pdia   = ft.TextField(label="Presión Diastólica (mmHg)",
                                      keyboard_type=ft.KeyboardType.NUMBER, expand=True)
        self.tf_pulso  = ft.TextField(label="Pulso (lpm)",
                                      keyboard_type=ft.KeyboardType.NUMBER, expand=True)
        self.tf_peso   = ft.TextField(label="Peso (kg)",
                                      keyboard_type=ft.KeyboardType.NUMBER,
                                      on_change=self._calcular_imc, expand=True)
        self.tf_altura = ft.TextField(label="Altura (cm)",
                                      keyboard_type=ft.KeyboardType.NUMBER,
                                      on_change=self._calcular_imc, expand=True)
        self.tf_imc    = ft.TextField(label="IMC (calculado)",
                                      read_only=True, expand=True,
                                      bgcolor="#F5F5F5")

        # Historial
        filas_historial = []
        for h in self.historial[:5]:
            fecha = str(h.get("fecha", ""))[:10]
            pa = f"{h.get('presion_sys','–')}/{h.get('presion_dia','–')}"
            imc_val = h.get("imc") or "–"
            filas_historial.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(fecha, size=11)),
                    ft.DataCell(ft.Text(pa, size=11)),
                    ft.DataCell(ft.Text(str(h.get("pulso", "–")), size=11)),
                    ft.DataCell(ft.Text(str(h.get("peso_kg", "–")), size=11)),
                    ft.DataCell(ft.Text(str(imc_val), size=11)),
                ])
            )

        historial_widget = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Fecha", size=11)),
                ft.DataColumn(ft.Text("PA (mmHg)", size=11)),
                ft.DataColumn(ft.Text("Pulso", size=11)),
                ft.DataColumn(ft.Text("Peso kg", size=11)),
                ft.DataColumn(ft.Text("IMC", size=11)),
            ],
            rows=filas_historial,
            column_spacing=16,
        ) if filas_historial else ft.Text("Sin registros previos.",
                                          color="#9E9E9E", size=12)

        return ft.Column(
            controls=[
                ft.Text("Nuevo Registro de Constantes Vitales",
                        size=14, weight=ft.FontWeight.BOLD),
                ft.Row(controls=[self.tf_psys, self.tf_pdia, self.tf_pulso], spacing=8),
                ft.Row(controls=[self.tf_peso, self.tf_altura, self.tf_imc], spacing=8),
                ft.ElevatedButton("Registrar", icon=ft.icons.MONITOR_HEART,
                                  on_click=self._guardar),
                ft.Divider(),
                ft.Text("Últimos 5 registros", size=13, weight=ft.FontWeight.W_500),
                historial_widget,
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
        )


# ── Ficha Clínica ─────────────────────────────────────────────────────────

class FichaClinicaView(ft.UserControl):
    """Formulario completo de ficha clínica con guardado en Supabase."""

    def __init__(self, paciente: dict, on_guardado=None, snack_fn=None):
        super().__init__()
        self.paciente = paciente
        self.on_guardado = on_guardado
        self.snack_fn = snack_fn
        self._checks: dict[str, ft.Checkbox] = {}

    def _guardar(self, e):
        # Validación mínima
        if not self.tf_nombre.value.strip() or not self.tf_apellido.value.strip():
            if self.snack_fn:
                self.snack_fn("Nombre y Apellido son obligatorios.", error=True)
            return

        antecedentes = {k: cb.value for k, cb in self._checks.items()}

        datos = {
            "nombre":       self.tf_nombre.value.strip(),
            "apellido":     self.tf_apellido.value.strip(),
            "fecha_nac":    self.tf_fecha_nac.value.strip() or None,
            "dni":          self.tf_dni.value.strip() or None,
            "telefono":     self.tf_telefono.value.strip() or None,
            "email":        self.tf_email.value.strip() or None,
            "direccion":    self.tf_direccion.value.strip() or None,
            "obra_social":  self.tf_obra_social.value.strip() or None,
            "nro_afiliado": self.tf_nro_afiliado.value.strip() or None,
            "grupo_sangre": self.dd_grupo.value or None,
            "alergias":     self.tf_alergias.value.strip() or None,
            "antecedentes": antecedentes,
        }

        try:
            if self.paciente.get("id"):
                actualizar_paciente(self.paciente["id"], datos)
                self.paciente.update(datos)
                if self.snack_fn:
                    self.snack_fn("Ficha actualizada correctamente.")
            else:
                resultado = crear_paciente(datos)
                if resultado:
                    self.paciente = resultado[0] if isinstance(resultado, list) else resultado
                if self.snack_fn:
                    self.snack_fn("Paciente creado correctamente.")

            if self.on_guardado:
                self.on_guardado(self.paciente)
        except Exception as ex:
            if self.snack_fn:
                self.snack_fn(f"Error al guardar: {ex}", error=True)

    def build(self):
        p = self.paciente
        ant = p.get("antecedentes") or {}

        self.tf_nombre       = ft.TextField(label="Nombre *", value=p.get("nombre", ""),
                                            expand=True)
        self.tf_apellido     = ft.TextField(label="Apellido *", value=p.get("apellido", ""),
                                            expand=True)
        self.tf_dni          = ft.TextField(label="DNI", value=p.get("dni", ""),
                                            expand=True)
        self.tf_fecha_nac    = ft.TextField(label="Fecha de Nacimiento (YYYY-MM-DD)",
                                            value=p.get("fecha_nac") or "", expand=True)
        self.tf_telefono     = ft.TextField(label="Teléfono", value=p.get("telefono", ""),
                                            expand=True)
        self.tf_email        = ft.TextField(label="Email", value=p.get("email", ""),
                                            expand=True, keyboard_type=ft.KeyboardType.EMAIL)
        self.tf_obra_social  = ft.TextField(label="Obra Social", value=p.get("obra_social", ""),
                                            expand=True)
        self.tf_nro_afiliado = ft.TextField(label="Nº Afiliado",
                                            value=p.get("nro_afiliado", ""), expand=True)
        self.tf_direccion    = ft.TextField(label="Dirección", value=p.get("direccion", ""),
                                            expand=True)
        self.tf_alergias     = ft.TextField(
            label="Alergias / Medicación actual",
            value=p.get("alergias", ""),
            multiline=True, min_lines=2,
        )
        self.dd_grupo = ft.Dropdown(
            label="Grupo Sanguíneo",
            value=p.get("grupo_sangre"),
            options=[ft.dropdown.Option(g) for g in
                     ["A+", "A−", "B+", "B−", "AB+", "AB−", "O+", "O−"]],
            width=160,
        )

        # Checkboxes de antecedentes
        self._checks = {}
        checks_row = ft.ResponsiveRow(
            controls=[
                ft.Checkbox(
                    label=label,
                    value=ant.get(key, False),
                    col={"sm": 6, "md": 4},
                    ref=ft.Ref(),
                )
                for key, label in ANTECEDENTES_CAMPOS
            ]
        )
        # Guardamos referencias por orden
        for i, (key, _) in enumerate(ANTECEDENTES_CAMPOS):
            self._checks[key] = checks_row.controls[i]

        return ft.Column(
            controls=[
                # — Identificación —
                ft.Text("Identificación", size=14, weight=ft.FontWeight.BOLD,
                        color="#1565C0"),
                ft.Row(controls=[self.tf_nombre, self.tf_apellido], spacing=8),
                ft.Row(controls=[self.tf_dni, self.tf_fecha_nac, self.dd_grupo], spacing=8),
                ft.Row(controls=[self.tf_telefono, self.tf_email], spacing=8),
                ft.Row(controls=[self.tf_obra_social, self.tf_nro_afiliado], spacing=8),
                self.tf_direccion,

                ft.Divider(),

                # — Antecedentes —
                ft.Text("Antecedentes Médicos", size=14, weight=ft.FontWeight.BOLD,
                        color="#1565C0"),
                checks_row,
                self.tf_alergias,

                ft.Divider(),

                ft.ElevatedButton(
                    "Guardar Ficha" if p.get("id") else "Crear Paciente",
                    icon=ft.icons.SAVE,
                    on_click=self._guardar,
                ),
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )


# ── Vista principal del módulo ────────────────────────────────────────────

class PacientesView(ft.UserControl):
    """Panel izquierdo: lista/búsqueda. Panel derecho: tabs de ficha, constantes y odontograma."""

    def __init__(self):
        super().__init__()
        self._todos: list[dict] = []
        self._paciente_activo: dict | None = None

    # — Snackbar helper —
    def _snack(self, mensaje: str, error: bool = False):
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(mensaje),
            bgcolor=ft.colors.RED_700 if error else ft.colors.GREEN_700,
            open=True,
        )
        self.page.update()

    # — Lista —
    def _cargar_lista(self):
        try:
            self._todos = listar_pacientes()
        except Exception as ex:
            self._todos = []
            self._snack(f"Error al cargar pacientes: {ex}", error=True)
        self._refrescar_lista(self._todos)

    def _refrescar_lista(self, pacientes: list[dict]):
        self._lista_col.controls.clear()
        if not pacientes:
            self._lista_col.controls.append(
                ft.Text("Sin resultados.", color="#9E9E9E", size=12)
            )
        for p in pacientes:
            nombre_completo = f"{p.get('apellido', '')}, {p.get('nombre', '')}"
            self._lista_col.controls.append(
                ft.ListTile(
                    title=ft.Text(nombre_completo, size=13),
                    subtitle=ft.Text(p.get("dni", ""), size=11),
                    selected=self._paciente_activo is not None
                              and p.get("id") == self._paciente_activo.get("id"),
                    on_click=lambda e, pac=p: self._seleccionar(pac),
                    content_padding=ft.padding.symmetric(horizontal=8),
                )
            )
        self._lista_col.update()

    def _filtrar(self, e):
        texto = (e.control.value or "").lower().strip()
        if not texto:
            self._refrescar_lista(self._todos)
            return
        filtrado = [
            p for p in self._todos
            if texto in (p.get("apellido") or "").lower()
            or texto in (p.get("nombre") or "").lower()
            or texto in (p.get("dni") or "").lower()
        ]
        self._refrescar_lista(filtrado)

    # — Detalle —
    def _seleccionar(self, paciente: dict):
        self._paciente_activo = paciente
        self._mostrar_detalle(paciente)
        self._refrescar_lista(self._todos)  # actualiza selección visual

    def _on_guardado(self, paciente_actualizado: dict):
        # Si es nuevo, agregarlo a la lista
        ids = [p["id"] for p in self._todos]
        if paciente_actualizado.get("id") not in ids:
            self._todos.insert(0, paciente_actualizado)
        else:
            idx = ids.index(paciente_actualizado["id"])
            self._todos[idx] = paciente_actualizado
        self._paciente_activo = paciente_actualizado
        self._refrescar_lista(self._todos)
        # Redibujar detalle para activar tabs de constantes/odontograma
        self._mostrar_detalle(paciente_actualizado)

    def _mostrar_detalle(self, paciente: dict):
        tabs = [
            ft.Tab(
                text="Ficha Clínica",
                icon=ft.icons.PERSON,
                content=ft.Container(
                    content=FichaClinicaView(
                        paciente,
                        on_guardado=self._on_guardado,
                        snack_fn=self._snack,
                    ),
                    padding=16,
                ),
            ),
        ]

        if paciente.get("id"):
            tabs += [
                ft.Tab(
                    text="Constantes Vitales",
                    icon=ft.icons.MONITOR_HEART,
                    content=ft.Container(
                        content=ConstantesView(
                            paciente["id"],
                            snack_fn=self._snack,
                        ),
                        padding=16,
                    ),
                ),
                ft.Tab(
                    text="Odontograma",
                    icon=ft.icons.GRID_VIEW,
                    content=ft.Container(
                        content=OdontogramaView(
                            paciente["id"],
                            snack_fn=self._snack,
                        ),
                        padding=16,
                    ),
                ),
            ]

        self._detalle_col.controls = [
            ft.Text(
                f"{'Nuevo Paciente' if not paciente.get('id') else paciente.get('apellido', '') + ', ' + paciente.get('nombre', '')}",
                size=18,
                weight=ft.FontWeight.BOLD,
            ),
            ft.Tabs(tabs=tabs, expand=True),
        ]
        self._detalle_col.visible = True
        self._detalle_col.update()

    def build(self):
        self._lista_col = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, expand=True)
        self._detalle_col = ft.Column(expand=True, visible=False, spacing=8)

        panel_izq = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Pacientes", size=16, weight=ft.FontWeight.BOLD),
                    ft.TextField(
                        label="Buscar por nombre, apellido o DNI",
                        prefix_icon=ft.icons.SEARCH,
                        on_change=self._filtrar,
                    ),
                    ft.ElevatedButton(
                        "+ Nuevo Paciente",
                        icon=ft.icons.PERSON_ADD,
                        on_click=lambda e: self._seleccionar({}),
                    ),
                    ft.Divider(height=4),
                    self._lista_col,
                ],
                spacing=8,
                expand=True,
            ),
            width=270,
            padding=12,
            border=ft.border.only(right=ft.BorderSide(1, "#E0E0E0")),
        )

        panel_der = ft.Container(
            content=self._detalle_col,
            expand=True,
            padding=12,
        )

        # Carga inicial de datos
        self._cargar_lista()

        return ft.Row(
            controls=[panel_izq, panel_der],
            expand=True,
            spacing=0,
        )
