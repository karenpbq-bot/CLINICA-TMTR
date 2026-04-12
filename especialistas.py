"""
Módulo de Especialistas: gestión de profesionales y su disponibilidad.
"""

import flet as ft
from database import (
    listar_especialistas, crear_especialista, actualizar_especialista,
    listar_disponibilidad, guardar_disponibilidad, eliminar_disponibilidad,
)

ESPECIALIDADES_DISPONIBLES = [
    "Odontología General", "Ortodoncia", "Odontopediatría", "Periodoncia",
    "Endodoncia", "Implantología", "Cirugía Maxilofacial",
    "Estética Dental", "Rehabilitación Oral", "Radiología Dental",
]
DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
CERTEZA_OPCIONES = [
    ("confirmado",    "🟢 Confirmado"),
    ("probable",      "🟡 Probable"),
    ("por_confirmar", "⚪ Por confirmar"),
]


class DisponibilidadEditor(ft.Column):
    def __init__(self, especialista_id: str, snack_fn=None):
        super().__init__(spacing=8)
        self.especialista_id = especialista_id
        self.snack_fn = snack_fn
        self.bloques: list[dict] = []
        self._filas_col = ft.Column(spacing=6)
        self.controls = [
            ft.Text("Disponibilidad Semanal", size=14, weight=ft.FontWeight.BOLD),
            self._filas_col,
            ft.TextButton("+ Agregar bloque horario", icon=ft.Icons.ADD,
                          on_click=self._agregar),
        ]

    def did_mount(self):
        try:
            self.bloques = listar_disponibilidad(self.especialista_id)
        except Exception as ex:
            if self.snack_fn:
                self.snack_fn(f"Error: {ex}", error=True)
        self._reconstruir_filas()
        self.update()

    def _reconstruir_filas(self):
        self._filas_col.controls.clear()
        for bloque in self.bloques:
            self._filas_col.controls.append(self._fila_bloque(bloque))
        if self._filas_col.page:
            self._filas_col.update()

    def _fila_bloque(self, bloque: dict):
        bid = bloque.get("id")
        dd_dia = ft.Dropdown(
            label="Día", value=str(bloque.get("dia_semana", 0)),
            options=[ft.dropdown.Option(str(i), d) for i, d in enumerate(DIAS_SEMANA)],
            width=130,
        )
        tf_ini = ft.TextField(label="Desde", value=bloque.get("hora_inicio", "08:00"), width=90)
        tf_fin = ft.TextField(label="Hasta", value=bloque.get("hora_fin", "12:00"), width=90)
        dd_cert = ft.Dropdown(
            label="Certeza", value=bloque.get("certeza", "por_confirmar"),
            options=[ft.dropdown.Option(v, l) for v, l in CERTEZA_OPCIONES],
            width=170,
        )
        return ft.Row(controls=[
            dd_dia, tf_ini, tf_fin, dd_cert,
            ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color=ft.Colors.RED_400,
                          tooltip="Eliminar bloque",
                          on_click=lambda e, b=bid: self._eliminar(b)),
        ], spacing=8, wrap=True)

    def _agregar(self, e):
        try:
            nuevo = {
                "especialista_id": self.especialista_id,
                "dia_semana": 0, "hora_inicio": "08:00",
                "hora_fin": "12:00", "certeza": "por_confirmar",
            }
            res = guardar_disponibilidad(nuevo)
            bloque = res[0] if isinstance(res, list) else res
            self.bloques.append(bloque)
            self._filas_col.controls.append(self._fila_bloque(bloque))
            self._filas_col.update()
        except Exception as ex:
            if self.snack_fn:
                self.snack_fn(f"Error: {ex}", error=True)

    def _eliminar(self, bid: str):
        if not bid:
            return
        try:
            eliminar_disponibilidad(bid)
            self.bloques = [b for b in self.bloques if b.get("id") != bid]
            self._reconstruir_filas()
        except Exception as ex:
            if self.snack_fn:
                self.snack_fn(f"Error: {ex}", error=True)


class FormularioEspecialista(ft.Column):
    def __init__(self, especialista: dict, on_guardado=None, snack_fn=None):
        super().__init__(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
        self.especialista = especialista
        self.on_guardado = on_guardado
        self.snack_fn = snack_fn
        self._construir()

    def _guardar(self, e):
        if not self.tf_nombre.value.strip() or not self.tf_apellido.value.strip():
            if self.snack_fn:
                self.snack_fn("Nombre y Apellido son obligatorios.", error=True)
            return
        especialidades = [
            esp for esp, cb in self._esp_checks.items() if cb.value
        ]
        datos = {
            "nombre":        self.tf_nombre.value.strip(),
            "apellido":      self.tf_apellido.value.strip(),
            "matricula":     self.tf_matricula.value.strip() or None,
            "telefono":      self.tf_telefono.value.strip() or None,
            "email":         self.tf_email.value.strip() or None,
            "especialidades": especialidades,
        }
        try:
            if self.especialista.get("id"):
                actualizar_especialista(self.especialista["id"], datos)
                self.especialista.update(datos)
                if self.snack_fn:
                    self.snack_fn("Especialista actualizado.")
            else:
                res = crear_especialista(datos)
                self.especialista = res[0] if isinstance(res, list) else res
                if self.snack_fn:
                    self.snack_fn("Especialista creado.")
            if self.on_guardado:
                self.on_guardado(self.especialista)
        except Exception as ex:
            if self.snack_fn:
                self.snack_fn(f"Error: {ex}", error=True)

    def _construir(self):
        e = self.especialista
        seleccionadas = e.get("especialidades") or []

        self.tf_nombre   = ft.TextField(label="Nombre *",   value=e.get("nombre", ""),   expand=True)
        self.tf_apellido = ft.TextField(label="Apellido *",  value=e.get("apellido", ""), expand=True)
        self.tf_matricula= ft.TextField(label="Matrícula",   value=e.get("matricula", ""),expand=True)
        self.tf_telefono = ft.TextField(label="Teléfono",    value=e.get("telefono", ""), expand=True)
        self.tf_email    = ft.TextField(label="Email",       value=e.get("email", ""),    expand=True)

        cbs = [
            ft.Checkbox(label=esp, value=esp in seleccionadas, col={"sm": 6, "md": 4})
            for esp in ESPECIALIDADES_DISPONIBLES
        ]
        self._esp_checks = {ESPECIALIDADES_DISPONIBLES[i]: cb for i, cb in enumerate(cbs)}

        controles = [
            ft.Text("Datos del Especialista", size=14, weight=ft.FontWeight.BOLD, color="#1565C0"),
            ft.Row(controls=[self.tf_nombre, self.tf_apellido], spacing=8),
            ft.Row(controls=[self.tf_matricula, self.tf_telefono], spacing=8),
            self.tf_email,
            ft.Divider(),
            ft.Text("Especialidades", size=14, weight=ft.FontWeight.BOLD, color="#1565C0"),
            ft.ResponsiveRow(controls=cbs),
            ft.ElevatedButton("Guardar", icon=ft.Icons.SAVE, on_click=self._guardar),
        ]
        if e.get("id"):
            controles += [ft.Divider(), DisponibilidadEditor(e["id"], snack_fn=self.snack_fn)]

        self.controls = controles


class EspecialistasView(ft.Row):
    def __init__(self):
        super().__init__(expand=True, spacing=0)
        self._todos: list[dict] = []
        self._lista_col  = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, expand=True)
        self._detalle_col = ft.Column(expand=True, visible=False, spacing=8)

        panel_izq = ft.Container(
            content=ft.Column(controls=[
                ft.Text("Especialistas", size=16, weight=ft.FontWeight.BOLD),
                ft.ElevatedButton("+ Nuevo", icon=ft.Icons.PERSON_ADD,
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
        self._cargar()

    def _snack(self, msg, error=False):
        if self.page:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(msg),
                bgcolor=ft.Colors.RED_700 if error else ft.Colors.GREEN_700,
                open=True,
            )
            self.page.update()

    def _cargar(self):
        try:
            self._todos = listar_especialistas()
        except Exception as ex:
            self._snack(f"Error: {ex}", error=True)
        self._refrescar()

    def _refrescar(self):
        self._lista_col.controls.clear()
        for esp in self._todos:
            especs = esp.get("especialidades") or []
            self._lista_col.controls.append(
                ft.ListTile(
                    title=ft.Text(f"Dr/a. {esp.get('apellido','')}, {esp.get('nombre','')}", size=13),
                    subtitle=ft.Text(", ".join(especs[:2]) or "Sin especialidad", size=11),
                    on_click=lambda e, s=esp: self._seleccionar(s),
                    content_padding=ft.padding.symmetric(horizontal=8),
                )
            )
        if self._lista_col.page:
            self._lista_col.update()

    def _seleccionar(self, esp: dict):
        self._detalle_col.visible = True
        self._detalle_col.controls = [
            ft.Text(
                "Nuevo Especialista" if not esp.get("id")
                else f"Dr/a. {esp.get('apellido','')}, {esp.get('nombre','')}",
                size=18, weight=ft.FontWeight.BOLD,
            ),
            FormularioEspecialista(esp,
                                   on_guardado=self._on_guardado,
                                   snack_fn=self._snack),
        ]
        if self._detalle_col.page:
            self._detalle_col.update()

    def _on_guardado(self, esp: dict):
        ids = [e["id"] for e in self._todos]
        if esp.get("id") not in ids:
            self._todos.insert(0, esp)
        else:
            self._todos[ids.index(esp["id"])] = esp
        self._refrescar()
        self._seleccionar(esp)
