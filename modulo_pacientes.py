"""
Módulo de Pacientes: Ficha Clínica completa + Odontograma Interactivo.
Flet >= 0.21: hereda de controles concretos en lugar de UserControl.
"""

import flet as ft
from database import (
    listar_pacientes,
    crear_paciente,
    actualizar_paciente,
    obtener_odontograma,
    guardar_diente,
    listar_constantes,
    registrar_constante,
)

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
ANTECEDENTES_CAMPOS = [
    ("diabetes",     "Diabetes"),
    ("hipertension", "Hipertensión"),
    ("cardiopatias", "Cardiopatías"),
    ("coagulopatias","Coagulopatías"),
    ("embarazo",     "Embarazo"),
    ("medicacion",   "Medicación habitual"),
    ("asma",         "Asma"),
    ("epilepsia",    "Epilepsia"),
]


# ── Odontograma ───────────────────────────────────────────────────────────

class DienteWidget(ft.Column):
    def __init__(self, numero: int, caras_estado: dict, on_change):
        super().__init__(spacing=1, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        self.numero = numero
        self.caras_estado = {c: caras_estado.get(c, "sano") for c in CARAS}
        self.on_change = on_change
        self._contenedores: dict[str, ft.Container] = {}
        self._construir()

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
        sig = estados[(estados.index(self.caras_estado[cara]) + 1) % len(estados)]
        self.caras_estado[cara] = sig
        cfg = ESTADOS_DIENTE[sig]
        c = self._contenedores[cara]
        c.bgcolor = cfg["color"]
        c.border = ft.border.all(1, cfg["borde"])
        c.tooltip = f"{cara.capitalize()} – {cfg['label']}"
        c.update()
        self.on_change(self.numero, dict(self.caras_estado))

    def _construir(self):
        self.controls = [
            self._hacer_cara("vestibular"),
            ft.Row(controls=[
                self._hacer_cara("mesial"),
                self._hacer_cara("oclusal"),
                self._hacer_cara("distal"),
            ], spacing=1),
            self._hacer_cara("lingual"),
            ft.Text(str(self.numero), size=8,
                    text_align=ft.TextAlign.CENTER, color="#616161"),
        ]


class OdontogramaView(ft.Column):
    def __init__(self, paciente_id: str, snack_fn=None):
        super().__init__(spacing=8, scroll=ft.ScrollMode.AUTO)
        self.paciente_id = paciente_id
        self.datos: dict[int, dict] = {}
        self.snack_fn = snack_fn
        self._fila_sup = ft.Row(spacing=6, wrap=True)
        self._fila_inf = ft.Row(spacing=6, wrap=True)
        self.controls = self._estructura()

    def did_mount(self):
        try:
            filas = obtener_odontograma(self.paciente_id)
            self.datos = {r["diente"]: r["caras"] for r in filas}
        except Exception as ex:
            if self.snack_fn:
                self.snack_fn(f"Error cargando odontograma: {ex}", error=True)
        self._poblar_filas()
        self.update()

    def _on_diente(self, numero: int, caras: dict):
        try:
            guardar_diente(self.paciente_id, numero, caras)
            self.datos[numero] = caras
        except Exception as ex:
            if self.snack_fn:
                self.snack_fn(f"Error al guardar diente {numero}: {ex}", error=True)

    def _poblar_filas(self):
        def fila(nums):
            return [
                DienteWidget(n,
                             self.datos.get(n, {c: "sano" for c in CARAS}),
                             self._on_diente)
                for n in nums
            ]
        self._fila_sup.controls = fila(DIENTES_ADULTO[0])
        self._fila_inf.controls = fila(DIENTES_ADULTO[1])

    def _leyenda(self):
        return ft.Row(
            controls=[
                ft.Row(controls=[
                    ft.Container(width=12, height=12, bgcolor=v["color"],
                                 border=ft.border.all(1, v["borde"]), border_radius=2),
                    ft.Text(v["label"], size=10),
                ], spacing=4)
                for v in ESTADOS_DIENTE.values()
            ],
            wrap=True, spacing=14,
        )

    def _estructura(self):
        return [
            ft.Text("Odontograma", size=16, weight=ft.FontWeight.BOLD),
            ft.Text("Superior (derecho → izquierdo)", size=11, color="#616161"),
            self._fila_sup,
            ft.Divider(height=8),
            ft.Text("Inferior (izquierdo → derecho)", size=11, color="#616161"),
            self._fila_inf,
            ft.Divider(height=8),
            ft.Text("Leyenda — clic en cada cara para cambiar estado:", size=11, color="#757575"),
            self._leyenda(),
        ]


# ── Constantes Vitales ────────────────────────────────────────────────────

class ConstantesView(ft.Column):
    def __init__(self, paciente_id: str, snack_fn=None):
        super().__init__(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
        self.paciente_id = paciente_id
        self.snack_fn = snack_fn
        self.historial: list[dict] = []

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
        self.tf_imc    = ft.TextField(label="IMC (calculado)", read_only=True,
                                      bgcolor="#F5F5F5", expand=True)
        self._tabla = ft.Column(spacing=4)
        self._construir()

    def did_mount(self):
        self.historial = listar_constantes(self.paciente_id)
        self._actualizar_tabla()
        self.update()

    def _calcular_imc(self, e=None):
        try:
            peso = float(self.tf_peso.value or 0)
            alt  = float(self.tf_altura.value or 0)
            if peso > 0 and alt > 0:
                self.tf_imc.value = f"{peso / ((alt / 100) ** 2):.1f}"
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
            for tf in [self.tf_psys, self.tf_pdia, self.tf_pulso,
                       self.tf_peso, self.tf_altura, self.tf_imc]:
                tf.value = ""
            self._actualizar_tabla()
            self.update()
            if self.snack_fn:
                self.snack_fn("Constantes registradas correctamente.")
        except Exception as ex:
            if self.snack_fn:
                self.snack_fn(f"Error: {ex}", error=True)

    def _actualizar_tabla(self):
        if not self.historial:
            self._tabla.controls = [ft.Text("Sin registros previos.", color="#9E9E9E", size=12)]
            return
        filas = []
        for h in self.historial[:5]:
            pa = f"{h.get('presion_sys','–')}/{h.get('presion_dia','–')}"
            filas.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(str(h.get("fecha", ""))[:10], size=11)),
                ft.DataCell(ft.Text(pa, size=11)),
                ft.DataCell(ft.Text(str(h.get("pulso", "–")), size=11)),
                ft.DataCell(ft.Text(str(h.get("peso_kg", "–")), size=11)),
                ft.DataCell(ft.Text(str(h.get("imc", "–")), size=11)),
            ]))
        self._tabla.controls = [
            ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Fecha", size=11)),
                    ft.DataColumn(ft.Text("PA (mmHg)", size=11)),
                    ft.DataColumn(ft.Text("Pulso", size=11)),
                    ft.DataColumn(ft.Text("Peso kg", size=11)),
                    ft.DataColumn(ft.Text("IMC", size=11)),
                ],
                rows=filas,
                column_spacing=16,
            )
        ]

    def _construir(self):
        self.controls = [
            ft.Text("Nuevo Registro de Constantes Vitales",
                    size=14, weight=ft.FontWeight.BOLD),
            ft.Row(controls=[self.tf_psys, self.tf_pdia, self.tf_pulso], spacing=8),
            ft.Row(controls=[self.tf_peso, self.tf_altura, self.tf_imc], spacing=8),
            ft.FilledButton("Registrar", icon=ft.Icons.MONITOR_HEART,
                              on_click=self._guardar),
            ft.Divider(),
            ft.Text("Últimos 5 registros", size=13, weight=ft.FontWeight.W_500),
            self._tabla,
        ]


# ── Ficha Clínica ─────────────────────────────────────────────────────────

class FichaClinicaView(ft.Column):
    def __init__(self, paciente: dict, on_guardado=None, snack_fn=None):
        super().__init__(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
        self.paciente = paciente
        self.on_guardado = on_guardado
        self.snack_fn = snack_fn
        self._checks: dict[str, ft.Checkbox] = {}
        self._construir()

    def _guardar(self, e):
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
                self.paciente = resultado[0] if isinstance(resultado, list) else resultado
                if self.snack_fn:
                    self.snack_fn("Paciente creado correctamente.")
            if self.on_guardado:
                self.on_guardado(self.paciente)
        except Exception as ex:
            if self.snack_fn:
                self.snack_fn(f"Error al guardar: {ex}", error=True)

    def _construir(self):
        p   = self.paciente
        ant = p.get("antecedentes") or {}

        self.tf_nombre       = ft.TextField(label="Nombre *",  value=p.get("nombre", ""),  expand=True)
        self.tf_apellido     = ft.TextField(label="Apellido *", value=p.get("apellido", ""), expand=True)
        self.tf_dni          = ft.TextField(label="DNI",        value=p.get("dni", ""),      expand=True)
        self.tf_fecha_nac    = ft.TextField(label="Fecha Nac. (YYYY-MM-DD)",
                                            value=p.get("fecha_nac") or "", expand=True)
        self.tf_telefono     = ft.TextField(label="Teléfono",   value=p.get("telefono", ""), expand=True)
        self.tf_email        = ft.TextField(label="Email",      value=p.get("email", ""),
                                            expand=True, keyboard_type=ft.KeyboardType.EMAIL)
        self.tf_obra_social  = ft.TextField(label="Obra Social",value=p.get("obra_social", ""), expand=True)
        self.tf_nro_afiliado = ft.TextField(label="Nº Afiliado",value=p.get("nro_afiliado",""), expand=True)
        self.tf_direccion    = ft.TextField(label="Dirección",  value=p.get("direccion", ""),   expand=True)
        self.tf_alergias     = ft.TextField(label="Alergias / Medicación actual",
                                            value=p.get("alergias", ""), multiline=True, min_lines=2)
        self.dd_grupo = ft.Dropdown(
            label="Grupo Sanguíneo", value=p.get("grupo_sangre"),
            options=[ft.dropdown.Option(g) for g in
                     ["A+","A−","B+","B−","AB+","AB−","O+","O−"]],
            width=160,
        )

        cbs = [
            ft.Checkbox(label=label, value=ant.get(key, False), col={"sm": 6, "md": 4})
            for key, label in ANTECEDENTES_CAMPOS
        ]
        self._checks = {key: cbs[i] for i, (key, _) in enumerate(ANTECEDENTES_CAMPOS)}

        self.controls = [
            ft.Text("Identificación", size=14, weight=ft.FontWeight.BOLD, color="#1565C0"),
            ft.Row(controls=[self.tf_nombre, self.tf_apellido], spacing=8),
            ft.Row(controls=[self.tf_dni, self.tf_fecha_nac, self.dd_grupo], spacing=8),
            ft.Row(controls=[self.tf_telefono, self.tf_email], spacing=8),
            ft.Row(controls=[self.tf_obra_social, self.tf_nro_afiliado], spacing=8),
            self.tf_direccion,
            ft.Divider(),
            ft.Text("Antecedentes Médicos", size=14, weight=ft.FontWeight.BOLD, color="#1565C0"),
            ft.ResponsiveRow(controls=cbs),
            self.tf_alergias,
            ft.Divider(),
            ft.FilledButton(
                "Guardar Ficha" if p.get("id") else "Crear Paciente",
                icon=ft.Icons.SAVE,
                on_click=self._guardar,
            ),
        ]


# ── Vista principal del módulo ────────────────────────────────────────────

class PacientesView(ft.Row):
    def __init__(self):
        super().__init__(expand=True, spacing=0)
        self._todos: list[dict] = []
        self._paciente_activo: dict | None = None

        self._lista_col  = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, expand=True)
        self._detalle_col = ft.Column(expand=True, visible=False, spacing=8)
        self._tf_buscar  = ft.TextField(
            label="Buscar por nombre, apellido o DNI",
            prefix_icon=ft.Icons.SEARCH,
            on_change=self._filtrar,
        )

        panel_izq = ft.Container(
            content=ft.Column(controls=[
                ft.Text("Pacientes", size=16, weight=ft.FontWeight.BOLD),
                self._tf_buscar,
                ft.FilledButton("+ Nuevo Paciente", icon=ft.Icons.PERSON_ADD,
                                  on_click=lambda e: self._seleccionar({})),
                ft.Divider(height=4),
                self._lista_col,
            ], spacing=8, expand=True),
            width=270, padding=12,
            border=ft.border.only(right=ft.BorderSide(1, "#E0E0E0")),
        )
        panel_der = ft.Container(content=self._detalle_col, expand=True, padding=12)
        self.controls = [panel_izq, panel_der]

    def did_mount(self):
        self._cargar_lista()

    def _snack(self, mensaje: str, error: bool = False):
        if self.page:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(mensaje),
                bgcolor=ft.Colors.RED_700 if error else ft.Colors.GREEN_700,
                open=True,
            )
            self.page.update()

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
            activo = (self._paciente_activo is not None
                      and p.get("id") == self._paciente_activo.get("id"))
            self._lista_col.controls.append(
                ft.ListTile(
                    title=ft.Text(f"{p.get('apellido','')}, {p.get('nombre','')}", size=13),
                    subtitle=ft.Text(p.get("dni", ""), size=11),
                    selected=activo,
                    on_click=lambda e, pac=p: self._seleccionar(pac),
                    content_padding=ft.padding.symmetric(horizontal=8),
                )
            )
        if self._lista_col.page:
            self._lista_col.update()

    def _filtrar(self, e):
        texto = (e.control.value or "").lower().strip()
        filtrado = self._todos if not texto else [
            p for p in self._todos
            if texto in (p.get("apellido") or "").lower()
            or texto in (p.get("nombre") or "").lower()
            or texto in (p.get("dni") or "").lower()
        ]
        self._refrescar_lista(filtrado)

    def _seleccionar(self, paciente: dict):
        self._paciente_activo = paciente
        self._mostrar_detalle(paciente)
        self._refrescar_lista(self._todos)

    def _on_guardado(self, paciente: dict):
        ids = [p["id"] for p in self._todos]
        if paciente.get("id") not in ids:
            self._todos.insert(0, paciente)
        else:
            self._todos[ids.index(paciente["id"])] = paciente
        self._paciente_activo = paciente
        self._refrescar_lista(self._todos)
        self._mostrar_detalle(paciente)

    def _mostrar_detalle(self, paciente: dict):
        tabs = [
            ft.Tab(
                text="Ficha Clínica", icon=ft.Icons.PERSON,
                content=ft.Container(
                    content=FichaClinicaView(paciente,
                                             on_guardado=self._on_guardado,
                                             snack_fn=self._snack),
                    padding=16,
                ),
            ),
        ]
        if paciente.get("id"):
            tabs += [
                ft.Tab(
                    text="Constantes Vitales", icon=ft.Icons.MONITOR_HEART,
                    content=ft.Container(
                        content=ConstantesView(paciente["id"], snack_fn=self._snack),
                        padding=16,
                    ),
                ),
                ft.Tab(
                    text="Odontograma", icon=ft.Icons.GRID_VIEW,
                    content=ft.Container(
                        content=OdontogramaView(paciente["id"], snack_fn=self._snack),
                        padding=16,
                    ),
                ),
            ]

        nombre_display = (
            "Nuevo Paciente" if not paciente.get("id")
            else f"{paciente.get('apellido','')}, {paciente.get('nombre','')}"
        )
        self._detalle_col.controls = [
            ft.Text(nombre_display, size=18, weight=ft.FontWeight.BOLD),
            ft.Tabs(tabs=tabs, expand=True),
        ]
        self._detalle_col.visible = True
        if self._detalle_col.page:
            self._detalle_col.update()
