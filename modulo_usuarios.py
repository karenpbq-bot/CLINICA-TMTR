"""
Módulo de Gestión de Usuarios.
Solo accesible para el rol Administrador.
Permite crear, editar, cambiar contraseña y activar/desactivar usuarios.
"""

import flet as ft
from database import (
    listar_usuarios, crear_usuario, actualizar_usuario,
    cambiar_password_usuario, ROLES_VALIDOS,
)

COLORES_ROL = {
    "Administrador": "#1565C0",
    "Recepcionista": "#2E7D32",
    "Especialista":  "#6A1B9A",
    "Cliente":       "#E65100",
}


def _badge_rol(rol: str) -> ft.Container:
    color = COLORES_ROL.get(rol, "#757575")
    return ft.Container(
        content=ft.Text(rol, size=11, color="#FFFFFF", weight=ft.FontWeight.W_500),
        bgcolor=color, border_radius=20, padding=ft.padding.symmetric(4, 10),
    )


def _badge_estado(activo: bool) -> ft.Container:
    return ft.Container(
        content=ft.Text(
            "Activo" if activo else "Inactivo",
            size=11, color="#FFFFFF", weight=ft.FontWeight.W_500,
        ),
        bgcolor="#2E7D32" if activo else "#9E9E9E",
        border_radius=20, padding=ft.padding.symmetric(4, 10),
    )


class UsuariosView(ft.Column):
    def __init__(self):
        super().__init__(spacing=0, expand=True)
        self._lista = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
        self._construir_base()

    # ── helpers ───────────────────────────────────────────────────────────

    def _snack(self, msg: str, error: bool = False):
        if self.page:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(msg),
                bgcolor=ft.Colors.RED_700 if error else ft.Colors.GREEN_700,
                open=True,
            )
            self.page.update()

    # ── construcción base ─────────────────────────────────────────────────

    def _construir_base(self):
        self.controls = [
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Text(
                            "Gestión de Usuarios",
                            size=18, weight=ft.FontWeight.BOLD,
                        ),
                        ft.FilledButton(
                            "Nuevo Usuario",
                            icon=ft.Icons.PERSON_ADD,
                            on_click=lambda e: self._abrir_form_crear(),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                padding=ft.padding.symmetric(16, 20),
            ),
            ft.Divider(height=1),
            ft.Container(
                content=self._lista,
                padding=ft.padding.all(16),
                expand=True,
            ),
        ]
        self._cargar_usuarios()

    # ── carga de datos ────────────────────────────────────────────────────

    def _cargar_usuarios(self):
        try:
            usuarios = listar_usuarios()
        except Exception as ex:
            self._lista.controls = [
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, size=48,
                                    color=ft.Colors.ORANGE_400),
                            ft.Text(
                                "La tabla 'usuarios' aún no existe en Supabase.",
                                size=14, weight=ft.FontWeight.W_500,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Text(
                                "Ejecutá el SQL de creación en el SQL Editor de Supabase "
                                "para habilitar la gestión de usuarios.",
                                size=12, color=ft.Colors.GREY_600,
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    padding=40,
                    alignment=ft.Alignment(0, 0),
                )
            ]
            if self._lista.page:
                self._lista.update()
            return

        if not usuarios:
            self._lista.controls = [
                ft.Text("No hay usuarios registrados.",
                        color=ft.Colors.GREY_500, size=13),
            ]
        else:
            self._lista.controls = [
                self._tarjeta_usuario(u) for u in usuarios
            ]

        if self._lista.page:
            self._lista.update()

    # ── tarjeta de usuario ────────────────────────────────────────────────

    def _tarjeta_usuario(self, u: dict) -> ft.Container:
        activo  = u.get("activo", True)
        nombre  = u.get("nombre", "") or u.get("usuario", "")
        usuario = u.get("usuario", "")
        rol     = u.get("rol", "")
        uid     = u["id"]

        ultimo = str(u.get("ultimo_acceso") or "—")[:16].replace("T", " ")

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.ACCOUNT_CIRCLE,
                        size=42,
                        color=COLORES_ROL.get(rol, "#757575"),
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(nombre, size=14, weight=ft.FontWeight.W_600),
                            ft.Text(f"@{usuario}", size=12, color="#757575"),
                            ft.Text(f"Último acceso: {ultimo}",
                                    size=11, color="#BDBDBD"),
                        ],
                        spacing=2, expand=True,
                    ),
                    ft.Column(
                        controls=[
                            _badge_rol(rol),
                            _badge_estado(activo),
                        ],
                        spacing=6,
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                    ),
                    ft.Column(
                        controls=[
                            ft.IconButton(
                                icon=ft.Icons.EDIT_OUTLINED,
                                icon_size=20, icon_color=ft.Colors.BLUE_600,
                                tooltip="Editar usuario",
                                on_click=lambda e, usr=u: self._abrir_form_editar(usr),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.LOCK_RESET,
                                icon_size=20, icon_color=ft.Colors.ORANGE_600,
                                tooltip="Cambiar contraseña",
                                on_click=lambda e, uid_=uid: self._abrir_cambio_pass(uid_),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.TOGGLE_ON if activo else ft.Icons.TOGGLE_OFF,
                                icon_size=22,
                                icon_color=ft.Colors.GREEN_600 if activo else ft.Colors.GREY_400,
                                tooltip="Desactivar" if activo else "Activar",
                                on_click=lambda e, usr=u: self._confirmar_toggle(usr),
                            ),
                        ],
                        spacing=0,
                    ),
                ],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
            ),
            padding=14,
            border_radius=10,
            bgcolor="#F5F5F5" if activo else "#FAFAFA",
            border=ft.border.all(1, "#E0E0E0" if activo else "#EEEEEE"),
            opacity=1.0 if activo else 0.65,
        )

    # ── diálogo crear ─────────────────────────────────────────────────────

    def _abrir_form_crear(self):
        tf_nombre   = ft.TextField(label="Nombre completo", autofocus=True)
        tf_usuario  = ft.TextField(label="Nombre de usuario *")
        tf_pass     = ft.TextField(label="Contraseña *", password=True, can_reveal_password=True)
        tf_pass2    = ft.TextField(label="Repetir contraseña *", password=True, can_reveal_password=True)
        dd_rol      = ft.Dropdown(
            label="Rol *",
            value="Recepcionista",
            options=[ft.dropdown.Option(r) for r in ROLES_VALIDOS],
        )
        lbl_err = ft.Text("", color=ft.Colors.RED_700, size=12, visible=False)

        def guardar(e):
            usuario_str = (tf_usuario.value or "").strip()
            pass_str    = (tf_pass.value or "").strip()
            pass2_str   = (tf_pass2.value or "").strip()

            if not usuario_str or not pass_str:
                lbl_err.value   = "Usuario y contraseña son obligatorios."
                lbl_err.visible = True
                lbl_err.update()
                return
            if pass_str != pass2_str:
                lbl_err.value   = "Las contraseñas no coinciden."
                lbl_err.visible = True
                lbl_err.update()
                return
            if len(pass_str) < 6:
                lbl_err.value   = "La contraseña debe tener al menos 6 caracteres."
                lbl_err.visible = True
                lbl_err.update()
                return

            try:
                crear_usuario({
                    "usuario":  usuario_str,
                    "password": pass_str,
                    "nombre":   (tf_nombre.value or "").strip(),
                    "rol":      dd_rol.value or "Recepcionista",
                })
                if self.page:
                    self.page.pop_dialog()
                self._snack(f"Usuario '{usuario_str}' creado correctamente.")
                self._cargar_usuarios()
            except Exception as ex:
                lbl_err.value   = f"Error: {ex}"
                lbl_err.visible = True
                lbl_err.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Nuevo Usuario"),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        tf_nombre, tf_usuario,
                        dd_rol,
                        ft.Divider(height=8, color=ft.Colors.TRANSPARENT),
                        tf_pass, tf_pass2,
                        lbl_err,
                    ],
                    spacing=10, tight=True,
                ),
                width=360,
            ),
            actions=[
                ft.TextButton("Cancelar",
                              on_click=lambda e: self.page.pop_dialog()),
                ft.FilledButton("Crear Usuario",
                                icon=ft.Icons.PERSON_ADD,
                                on_click=guardar),
            ],
        )
        if self.page:
            self.page.show_dialog(dlg)

    # ── diálogo editar ────────────────────────────────────────────────────

    def _abrir_form_editar(self, u: dict):
        uid = u["id"]
        tf_nombre = ft.TextField(
            label="Nombre completo",
            value=u.get("nombre", ""),
            autofocus=True,
        )
        dd_rol = ft.Dropdown(
            label="Rol *",
            value=u.get("rol", "Recepcionista"),
            options=[ft.dropdown.Option(r) for r in ROLES_VALIDOS],
        )
        sw_activo = ft.Switch(
            label="Usuario activo",
            value=u.get("activo", True),
        )
        lbl_err = ft.Text("", color=ft.Colors.RED_700, size=12, visible=False)

        def guardar(e):
            try:
                actualizar_usuario(uid, {
                    "nombre": (tf_nombre.value or "").strip(),
                    "rol":    dd_rol.value or u.get("rol"),
                    "activo": sw_activo.value,
                })
                if self.page:
                    self.page.pop_dialog()
                self._snack("Usuario actualizado.")
                self._cargar_usuarios()
            except Exception as ex:
                lbl_err.value   = f"Error: {ex}"
                lbl_err.visible = True
                lbl_err.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Editar: @{u.get('usuario','')}"),
            content=ft.Container(
                content=ft.Column(
                    controls=[tf_nombre, dd_rol, sw_activo, lbl_err],
                    spacing=10, tight=True,
                ),
                width=340,
            ),
            actions=[
                ft.TextButton("Cancelar",
                              on_click=lambda e: self.page.pop_dialog()),
                ft.FilledButton("Guardar", icon=ft.Icons.SAVE, on_click=guardar),
            ],
        )
        if self.page:
            self.page.show_dialog(dlg)

    # ── diálogo cambiar contraseña ────────────────────────────────────────

    def _abrir_cambio_pass(self, uid: str):
        tf_pass  = ft.TextField(label="Nueva contraseña *",
                                password=True, can_reveal_password=True, autofocus=True)
        tf_pass2 = ft.TextField(label="Repetir contraseña *",
                                password=True, can_reveal_password=True)
        lbl_err  = ft.Text("", color=ft.Colors.RED_700, size=12, visible=False)

        def guardar(e):
            p1 = (tf_pass.value or "").strip()
            p2 = (tf_pass2.value or "").strip()
            if not p1:
                lbl_err.value = "Ingresá la nueva contraseña."
                lbl_err.visible = True; lbl_err.update(); return
            if p1 != p2:
                lbl_err.value = "Las contraseñas no coinciden."
                lbl_err.visible = True; lbl_err.update(); return
            if len(p1) < 6:
                lbl_err.value = "Mínimo 6 caracteres."
                lbl_err.visible = True; lbl_err.update(); return
            try:
                cambiar_password_usuario(uid, p1)
                if self.page:
                    self.page.pop_dialog()
                self._snack("Contraseña actualizada correctamente.")
            except Exception as ex:
                lbl_err.value = f"Error: {ex}"
                lbl_err.visible = True; lbl_err.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Cambiar Contraseña"),
            content=ft.Container(
                content=ft.Column(
                    controls=[tf_pass, tf_pass2, lbl_err],
                    spacing=10, tight=True,
                ),
                width=320,
            ),
            actions=[
                ft.TextButton("Cancelar",
                              on_click=lambda e: self.page.pop_dialog()),
                ft.FilledButton("Actualizar", icon=ft.Icons.LOCK_RESET,
                                on_click=guardar),
            ],
        )
        if self.page:
            self.page.show_dialog(dlg)

    # ── confirmar activar / desactivar ────────────────────────────────────

    def _confirmar_toggle(self, u: dict):
        activo  = u.get("activo", True)
        uid     = u["id"]
        nombre  = u.get("nombre") or u.get("usuario", "")
        accion  = "desactivar" if activo else "activar"
        nuevo   = not activo

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"{'Desactivar' if activo else 'Activar'} usuario"),
            content=ft.Text(
                f"¿Querés {accion} al usuario '{nombre}'?\n"
                + ("El usuario no podrá iniciar sesión." if activo
                   else "El usuario podrá volver a iniciar sesión.")
            ),
            actions=[
                ft.TextButton("Cancelar",
                              on_click=lambda e: self.page.pop_dialog()),
                ft.FilledButton(
                    "Desactivar" if activo else "Activar",
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.RED_700 if activo else ft.Colors.GREEN_700
                    ),
                    on_click=lambda e: self._toggle_usuario(uid, nuevo),
                ),
            ],
        )
        if self.page:
            self.page.show_dialog(dlg)

    def _toggle_usuario(self, uid: str, nuevo_estado: bool):
        if self.page:
            self.page.pop_dialog()
        try:
            actualizar_usuario(uid, {"activo": nuevo_estado})
            estado_txt = "activado" if nuevo_estado else "desactivado"
            self._snack(f"Usuario {estado_txt}.")
            self._cargar_usuarios()
        except Exception as ex:
            self._snack(f"Error: {ex}", error=True)
