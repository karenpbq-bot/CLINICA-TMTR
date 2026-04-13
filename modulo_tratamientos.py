"""
Módulo de Tratamientos: presupuestos detallados por diente y cara tratada.
Flet 0.84: Dropdown.on_select, page.show_dialog/pop_dialog para confirmaciones.
"""

import flet as ft
from database import (
    listar_tratamientos, crear_tratamiento, actualizar_tratamiento,
    eliminar_tratamiento, listar_pacientes, listar_especialistas,
)

CARAS_DIENTE = ["Oclusal", "Vestibular", "Lingual/Palatino", "Mesial", "Distal"]
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
DIENTES_FDI = (
    list(range(11, 19)) + list(range(21, 29)) +
    list(range(31, 39)) + list(range(41, 49))
)


def _badge_estado(estado: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(
            ESTADOS_TRATAMIENTO.get(estado, estado),
            size=10, color="#FFFFFF", weight=ft.FontWeight.W_500,
        ),
        bgcolor=ESTADO_BADGE_COLOR.get(estado, "#757575"),
        border_radius=10, padding=ft.padding.symmetric(horizontal=8, vertical=2),
    )


class FormularioTratamiento(ft.Column):
    def __init__(self, paciente_id: str, tratamiento: dict = None,
                 on_guardar=None, snack_fn=None):
        super().__init__(spacing=10)
        self.paciente_id = paciente_id
        self.tratamiento = tratamiento or {}
        self.on_guardar  = on_guardar
        self.snack_fn    = snack_fn
        self._construir()

    def _construir(self):
        t = self.tratamiento
        try:
            especialistas = listar_especialistas()
        except Exception:
            especialistas = []

        self.dd_diente = ft.Dropdown(
            label="Diente (FDI)",
            value=str(t["diente"]) if t.get("diente") else None,
            options=[ft.dropdown.Option(str(d), str(d)) for d in DIENTES_FDI],
            width=130,
        )
        self.dd_cara = ft.Dropdown(
            label="Cara",
            value=t.get("cara"),
            options=[ft.dropdown.Option(c) for c in CARAS_DIENTE],
            width=185,
        )
        self.dd_especialista = ft.Dropdown(
            label="Especialista",
            value=t.get("especialista_id"),
            options=[
                ft.dropdown.Option(e["id"], f"Dr/a. {e.get('apellido','')}, {e.get('nombre','')}")
                for e in especialistas
            ],
            expand=True,
        )
        self.dd_tipo = ft.Dropdown(
            label="Tipo de tratamiento *",
            value=t.get("descripcion"),
            options=[ft.dropdown.Option(tp) for tp in TIPOS_TRATAMIENTO],
            expand=True,
        )
        self.tf_costo = ft.TextField(
            label="Costo ($)", value=str(t.get("costo", "0")),
            keyboard_type=ft.KeyboardType.NUMBER, width=130,
        )
        self.dd_estado = ft.Dropdown(
            label="Estado",
            value=t.get("estado", "presupuestado"),
            options=[ft.dropdown.Option(k, v) for k, v in ESTADOS_TRATAMIENTO.items()],
            width=185,
        )

        titulo = "Editar Ítem" if t.get("id") else "Agregar Ítem"
        self.controls = [
            ft.Text(titulo, size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
            ft.Row(controls=[self.dd_diente, self.dd_cara, self.tf_costo], spacing=8),
            ft.Row(controls=[self.dd_tipo, self.dd_especialista], spacing=8),
            ft.Row(controls=[self.dd_estado], spacing=8),
            ft.FilledButton(
                "Guardar Ítem", icon=ft.Icons.SAVE, on_click=self._guardar,
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
            "diente":          int(self.dd_diente.value) if self.dd_diente.value else None,
            "cara":            self.dd_cara.value,
            "descripcion":     self.dd_tipo.value,
            "costo":           costo,
            "estado":          self.dd_estado.value or "presupuestado",
        }
        try:
            if self.tratamiento.get("id"):
                actualizar_tratamiento(self.tratamiento["id"], datos)
            else:
                crear_tratamiento(datos)
            if self.snack_fn:
                self.snack_fn("Tratamiento guardado correctamente.")
            if self.on_guardar:
                self.on_guardar()
        except Exception as ex:
            if self.snack_fn:
                self.snack_fn(f"Error: {ex}", error=True)


class TratamientosView(ft.Column):
    def __init__(self):
        super().__init__(spacing=16, expand=True, scroll=ft.ScrollMode.AUTO)
        self.paciente_id: str | None  = None
        self._tratamiento_activo: dict | None = None
        self._mostrar_form   = False
        self._contenido      = ft.Column(spacing=12, expand=True)
        self._construir_base()

    def _snack(self, msg, error=False):
        if self.page:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(msg),
                bgcolor=ft.Colors.RED_700 if error else ft.Colors.GREEN_700,
                open=True,
            )
            self.page.update()

    def _construir_base(self):
        try:
            pacientes = listar_pacientes()
        except Exception:
            pacientes = []

        self.dd_selector = ft.Dropdown(
            label="Seleccionar paciente",
            options=[
                ft.dropdown.Option(p["id"], f"{p.get('apellido','')}, {p.get('nombre','')}")
                for p in pacientes
            ],
            on_select=self._on_selector,
            width=380,
        )
        self.controls = [
            ft.Text("Módulo de Tratamientos", size=18, weight=ft.FontWeight.BOLD),
            self.dd_selector,
            self._contenido,
        ]

    def _on_selector(self, e):
        self._cargar_paciente(self.dd_selector.value)

    def _cargar_paciente(self, pid: str):
        self.paciente_id = pid
        self._mostrar_form = False
        self._tratamiento_activo = None
        self._actualizar_contenido()

    def _actualizar_contenido(self):
        if not self.paciente_id:
            self._contenido.controls = []
            if self._contenido.page:
                self._contenido.update()
            return

        try:
            tratamientos = listar_tratamientos(self.paciente_id)
        except Exception as ex:
            self._snack(f"Error: {ex}", error=True)
            tratamientos = []

        total_presup  = sum(float(t.get("costo", 0)) for t in tratamientos
                            if t.get("estado") == "presupuestado")
        total_aprobado = sum(float(t.get("costo", 0)) for t in tratamientos
                             if t.get("estado") == "aprobado")
        total_realizado = sum(float(t.get("costo", 0)) for t in tratamientos
                              if t.get("estado") == "realizado")
        total_global   = total_presup + total_aprobado + total_realizado

        tarjetas = ft.Row(controls=[
            self._tarjeta("Total Plan", total_global,         "#1565C0"),
            self._tarjeta("Presupuestado", total_presup,      "#E65100"),
            self._tarjeta("Aprobado",      total_aprobado,    "#0288D1"),
            self._tarjeta("Realizado",     total_realizado,   "#2E7D32"),
        ], spacing=8, wrap=True)

        items = []
        for t in tratamientos:
            estado = t.get("estado", "presupuestado")
            esp    = t.get("especialistas") or {}
            items.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Column(controls=[
                                ft.Row(controls=[
                                    ft.Text(
                                        f"Diente {t.get('diente','–')}  ·  {t.get('cara','–')}",
                                        size=12, weight=ft.FontWeight.BOLD,
                                    ),
                                    _badge_estado(estado),
                                ], spacing=8),
                                ft.Text(t.get("descripcion",""), size=13),
                                ft.Text(
                                    f"Dr/a. {esp.get('apellido','–')}, {esp.get('nombre','')}",
                                    size=11, color="#757575",
                                ),
                            ], spacing=3, expand=True),
                            ft.Column(controls=[
                                ft.Text(
                                    f"$ {float(t.get('costo',0)):.2f}",
                                    size=14, weight=ft.FontWeight.W_600,
                                ),
                                ft.Row(controls=[
                                    ft.IconButton(
                                        icon=ft.Icons.EDIT_OUTLINED,
                                        icon_size=18, icon_color=ft.Colors.BLUE_600,
                                        tooltip="Editar ítem",
                                        on_click=lambda e, tr=t: self._editar(tr),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINE,
                                        icon_size=18, icon_color=ft.Colors.RED_400,
                                        tooltip="Eliminar ítem",
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
                )
            )

        es_edicion = self._tratamiento_activo is not None and self._tratamiento_activo.get("id")
        lbl_btn   = ("- Cerrar" if self._mostrar_form else
                     ("Editar ítem" if es_edicion else "+ Agregar ítem"))
        icono_btn = (ft.Icons.REMOVE if self._mostrar_form else
                     (ft.Icons.EDIT if es_edicion else ft.Icons.ADD))

        form = (
            FormularioTratamiento(
                self.paciente_id,
                tratamiento=self._tratamiento_activo or {},
                on_guardar=self._refrescar,
                snack_fn=self._snack,
            )
            if self._mostrar_form else ft.Container()
        )

        self._contenido.controls = [
            tarjetas,
            ft.Row(controls=[
                ft.FilledButton(lbl_btn, icon=icono_btn,
                                on_click=lambda e: self._toggle_form()),
                ft.TextButton(
                    "Nuevo ítem",
                    icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                    on_click=lambda e: self._nuevo_form(),
                    visible=self._mostrar_form and bool(self._tratamiento_activo and self._tratamiento_activo.get("id")),
                ),
            ], spacing=8),
            form,
            ft.Divider(),
            ft.Column(
                controls=items if items else [
                    ft.Text("Sin tratamientos registrados.", color="#9E9E9E")
                ],
                spacing=6,
            ),
        ]
        if self._contenido.page:
            self._contenido.update()

    @staticmethod
    def _tarjeta(titulo: str, monto: float, color: str) -> ft.Container:
        return ft.Container(
            content=ft.Column(controls=[
                ft.Text(titulo, size=11, color="#FAFAFA"),
                ft.Text(f"$ {monto:.2f}", size=16,
                        weight=ft.FontWeight.BOLD, color="#FFFFFF"),
            ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=color, border_radius=8, padding=10, width=145,
        )

    def _toggle_form(self):
        self._mostrar_form = not self._mostrar_form
        if not self._mostrar_form:
            self._tratamiento_activo = None
        self._actualizar_contenido()

    def _nuevo_form(self):
        self._tratamiento_activo = None
        self._mostrar_form = True
        self._actualizar_contenido()

    def _editar(self, tratamiento: dict):
        self._tratamiento_activo = tratamiento
        self._mostrar_form = True
        self._actualizar_contenido()

    def _confirmar_eliminar(self, tratamiento: dict):
        if not self.page:
            return
        desc = tratamiento.get("descripcion", "este ítem")
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmar eliminación"),
            content=ft.Text(f"¿Eliminar «{desc}»?  Esta acción no se puede deshacer."),
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
        self._refrescar()

    def _refrescar(self):
        self._mostrar_form = False
        self._tratamiento_activo = None
        self._actualizar_contenido()
