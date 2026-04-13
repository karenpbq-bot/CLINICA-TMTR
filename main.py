import os
import threading
import flet as ft
from modulo_pacientes import PacientesView
from especialistas import EspecialistasView
from modulo_agenda import AgendaView
from modulo_tratamientos import TratamientosView
from modulo_pagos import PagosView

INACTIVIDAD_SEGUNDOS = 300
PORT = int(os.environ.get("PORT", 8000))

RUTAS = [
    ("/pacientes",    "Pacientes",    ft.Icons.PEOPLE),
    ("/especialistas","Especialistas",ft.Icons.MEDICAL_SERVICES),
    ("/agenda",       "Agenda",       ft.Icons.CALENDAR_MONTH),
    ("/tratamientos", "Tratamientos", ft.Icons.HEALING),
    ("/pagos",        "Pagos",        ft.Icons.ATTACH_MONEY),
]

VISTAS = {
    "/pacientes":     lambda: PacientesView(),
    "/especialistas": lambda: EspecialistasView(),
    "/agenda":        lambda: AgendaView(),
    "/tratamientos":  lambda: TratamientosView(),
    "/pagos":         lambda: PagosView(),
}

INDICE_RUTA = {r[0]: i for i, r in enumerate(RUTAS)}


async def main(page: ft.Page):
    page.title = "Consultorio Odontológico"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0

    inactividad_timer = None

    def reiniciar_timer():
        nonlocal inactividad_timer
        if inactividad_timer:
            inactividad_timer.cancel()
        inactividad_timer = threading.Timer(
            INACTIVIDAD_SEGUNDOS,
            lambda: page.run_task(page.push_route("/login"))
        )
        inactividad_timer.daemon = True
        inactividad_timer.start()

    async def on_route_change(e: ft.RouteChangeEvent):
        reiniciar_timer()
        page.views.clear()
        if page.route in ("/login", "/"):
            page.views.append(_login_view(page))
        else:
            page.views.append(_app_shell(page.route, page))
        page.update()

    def on_view_pop(e):
        page.views.pop()
        top_view = page.views[-1]
        page.run_task(page.push_route(top_view.route))

    page.on_route_change = on_route_change
    page.on_view_pop = on_view_pop
    page.on_keyboard_event = lambda _: reiniciar_timer()

    await page.push_route("/login")


def _login_view(page: ft.Page) -> ft.View:
    tf_usuario   = ft.TextField(label="Usuario", autofocus=True,
                                prefix_icon=ft.Icons.PERSON, width=320)
    tf_password  = ft.TextField(label="Contraseña", password=True,
                                can_reveal_password=True,
                                prefix_icon=ft.Icons.LOCK, width=320)
    lbl_error    = ft.Text("", color=ft.Colors.RED_700, size=12, visible=False)

    def ingresar(e):
        if not tf_usuario.value or not tf_password.value:
            lbl_error.value = "Ingresá usuario y contraseña."
            lbl_error.visible = True
            lbl_error.update()
            return
        page.run_task(page.push_route("/pacientes"))

    tf_password.on_submit = ingresar

    return ft.View(
        route="/login",
        controls=[
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.LOCAL_HOSPITAL, size=72, color=ft.Colors.BLUE_700),
                        ft.Text("Consultorio Odontológico", size=26,
                                weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                        ft.Text("Sistema de Gestión", size=14, color=ft.Colors.GREY_600),
                        ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                        tf_usuario,
                        tf_password,
                        lbl_error,
                        ft.FilledButton("Ingresar", width=320, height=44,
                                        icon=ft.Icons.LOGIN, on_click=ingresar),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=14,
                ),
                alignment=ft.Alignment(0, 0),
                expand=True,
            )
        ],
        bgcolor=ft.Colors.GREY_50,
    )


def _app_shell(route: str, page: ft.Page) -> ft.View:
    ruta_activa = route if route in VISTAS else "/pacientes"
    idx_activo  = INDICE_RUTA.get(ruta_activa, 0)

    def on_nav(e):
        ruta_destino = RUTAS[e.control.selected_index][0]
        page.run_task(page.push_route(ruta_destino))

    def cerrar_sesion(e):
        page.run_task(page.push_route("/login"))

    nav = ft.NavigationRail(
        selected_index=idx_activo,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        group_alignment=-1.0,
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icon(icon),
                selected_icon=ft.Icon(icon, color=ft.Colors.BLUE_700),
                label=label,
            )
            for _, label, icon in RUTAS
        ],
        trailing=ft.IconButton(
            icon=ft.Icons.LOGOUT,
            icon_color=ft.Colors.GREY_500,
            tooltip="Cerrar sesión",
            on_click=cerrar_sesion,
        ),
        on_change=on_nav,
        bgcolor=ft.Colors.GREY_100,
    )

    vista_fn = VISTAS.get(ruta_activa, VISTAS["/pacientes"])
    contenido = vista_fn()

    return ft.View(
        route=ruta_activa,
        controls=[
            ft.Row(
                controls=[
                    nav,
                    ft.VerticalDivider(width=1, color=ft.Colors.GREY_300),
                    ft.Container(content=contenido, expand=True, padding=0),
                ],
                expand=True,
                spacing=0,
            )
        ],
        padding=0,
    )


ft.run(main, port=PORT, view=ft.AppView.WEB_BROWSER)
