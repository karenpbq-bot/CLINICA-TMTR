import flet as ft
import threading
from modulo_pacientes import PacientesView
from especialistas import EspecialistasView
from modulo_agenda import AgendaView
from modulo_tratamientos import TratamientosView
from modulo_pagos import PagosView

INACTIVIDAD_SEGUNDOS = 300  # 5 minutos


def main(page: ft.Page):
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
        page.session.clear()
        page.go("/login")
        page.update()

    def on_route_change(e: ft.RouteChangeEvent):
        reiniciar_timer()
        page.views.clear()

        if page.route == "/login" or page.route == "/":
            page.views.append(login_view())
        else:
            page.views.append(app_shell(page.route))

        page.update()

    def on_view_pop(e):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    page.on_route_change = on_route_change
    page.on_view_pop = on_view_pop
    page.on_keyboard_event = lambda _: reiniciar_timer()

    page.go("/login")


def login_view():
    return ft.View(
        "/login",
        controls=[
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(ft.icons.LOCAL_HOSPITAL, size=64, color=ft.colors.BLUE_700),
                        ft.Text("Consultorio Odontológico", size=24, weight=ft.FontWeight.BOLD),
                        ft.TextField(label="Usuario", autofocus=True),
                        ft.TextField(label="Contraseña", password=True, can_reveal_password=True),
                        ft.ElevatedButton("Ingresar", width=200),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=16,
                ),
                alignment=ft.alignment.center,
                expand=True,
            )
        ],
    )


def app_shell(route: str):
    modulos = {
        "/pacientes": ("Pacientes", ft.icons.PEOPLE, PacientesView()),
        "/especialistas": ("Especialistas", ft.icons.MEDICAL_SERVICES, EspecialistasView()),
        "/agenda": ("Agenda", ft.icons.CALENDAR_TODAY, AgendaView()),
        "/tratamientos": ("Tratamientos", ft.icons.MEDICAL_INFORMATION, TratamientosView()),
        "/pagos": ("Pagos", ft.icons.PAYMENT, PagosView()),
    }

    rail = ft.NavigationRail(
        selected_index=list(modulos.keys()).index(route) if route in modulos else 0,
        label_type=ft.NavigationRailLabelType.ALL,
        destinations=[
            ft.NavigationRailDestination(icon=icon, label=nombre)
            for _, (nombre, icon, _) in modulos.items()
        ],
    )

    contenido = modulos.get(route, list(modulos.values())[0])[2]

    return ft.View(
        route,
        controls=[
            ft.Row(
                controls=[
                    rail,
                    ft.VerticalDivider(width=1),
                    ft.Container(content=contenido, expand=True, padding=16),
                ],
                expand=True,
            )
        ],
        padding=0,
    )


ft.app(target=main)
