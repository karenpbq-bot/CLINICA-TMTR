import os
import threading
import flet as ft
from modulo_pacientes import PacientesView
from especialistas import EspecialistasView
from modulo_agenda import AgendaView
from modulo_tratamientos import TratamientosView
from modulo_pagos import PagosView

INACTIVIDAD_SEGUNDOS = 300  # 5 minutos
PORT = int(os.environ.get("PORT", 8000))


async def main(page: ft.Page):
    page.title = "Consultorio Odontológico"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0

    inactividad_timer = None

    def reiniciar_timer():
        nonlocal inactividad_timer
        if inactividad_timer:
            inactividad_timer.cancel()
        inactividad_timer = threading.Timer(INACTIVIDAD_SEGUNDOS, cerrar_sesion)
        inactividad_timer.daemon = True
        inactividad_timer.start()

    def cerrar_sesion():
        page.go("/login")
        page.update()

    def on_route_change(e: ft.RouteChangeEvent):
        reiniciar_timer()
        page.views.clear()

        if page.route in ("/login", "/"):
            page.views.append(login_view(page))
        else:
            page.views.append(app_shell(page.route, page))

        page.update()

    def on_view_pop(e):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    page.on_route_change = on_route_change
    page.on_view_pop = on_view_pop
    page.on_keyboard_event = lambda _: reiniciar_timer()

    await page.push_route("/login")


def login_view(page: ft.Page):
    def ingresar(e):
        page.go("/pacientes")

    return ft.View(
        route="/login",
        controls=[
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(ft.Icons.LOCAL_HOSPITAL, size=72, color=ft.Colors.BLUE_700),
                        ft.Text(
                            "Consultorio Odontológico",
                            size=26,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_900,
                        ),
                        ft.Text(
                            "Sistema de Gestión",
                            size=14,
                            color=ft.Colors.GREY_600,
                        ),
                        ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                        ft.TextField(
                            label="Usuario",
                            autofocus=True,
                            prefix_icon=ft.Icons.PERSON,
                            width=320,
                        ),
                        ft.TextField(
                            label="Contraseña",
                            password=True,
                            can_reveal_password=True,
                            prefix_icon=ft.Icons.LOCK,
                            width=320,
                            on_submit=ingresar,
                        ),
                        ft.FilledButton(
                            "Ingresar",
                            width=320,
                            height=44,
                            icon=ft.Icons.LOGIN,
                            on_click=ingresar,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=14,
                ),
                alignment=ft.Alignment.CENTER,
                expand=True,
                bgcolor=ft.Colors.WHITE,
            )
        ],
        bgcolor=ft.Colors.BLUE_GREY_50,
    )


MODULOS = [
    ("/pacientes",     "Pacientes",     ft.Icons.PEOPLE),
    ("/especialistas", "Especialistas", ft.Icons.MEDICAL_SERVICES),
    ("/agenda",        "Agenda",        ft.Icons.CALENDAR_TODAY),
    ("/tratamientos",  "Tratamientos",  ft.Icons.MEDICAL_INFORMATION),
    ("/pagos",         "Pagos",         ft.Icons.PAYMENT),
]

VISTAS = {
    "/pacientes":     lambda: PacientesView(),
    "/especialistas": lambda: EspecialistasView(),
    "/agenda":        lambda: AgendaView(),
    "/tratamientos":  lambda: TratamientosView(),
    "/pagos":         lambda: PagosView(),
}


def app_shell(route: str, page: ft.Page):
    rutas = [r for r, _, _ in MODULOS]
    idx = rutas.index(route) if route in rutas else 0

    def navegar(e):
        ruta_destino = rutas[e.control.selected_index]
        page.go(ruta_destino)

    rail = ft.NavigationRail(
        selected_index=idx,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=80,
        destinations=[
            ft.NavigationRailDestination(icon=icon, label=nombre)
            for _, nombre, icon in MODULOS
        ],
        on_change=navegar,
        bgcolor=ft.Colors.BLUE_GREY_50,
    )

    vista_fn = VISTAS.get(route, VISTAS["/pacientes"])
    contenido = vista_fn()

    return ft.View(
        route=route,
        controls=[
            ft.Row(
                controls=[
                    rail,
                    ft.VerticalDivider(width=1),
                    ft.Container(content=contenido, expand=True),
                ],
                expand=True,
            )
        ],
        padding=0,
        bgcolor=ft.Colors.WHITE,
    )


ft.run(main, view=ft.AppView.WEB_BROWSER, port=PORT, host="0.0.0.0")
