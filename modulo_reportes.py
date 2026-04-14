"""
Módulo de Reportes — Visualización y exportación de reportes.
Pestañas: Resumen | Citas | Ingresos | Tratamientos
"""

import datetime
import os
import flet as ft

from database import (
    listar_especialistas,
    listar_citas_rango,
    listar_pagos_todos,
    listar_tratamientos_todos,
    stats_resumen,
)

# ═══════════════════════════════════════════════════════════════════════════
#  Constantes de estilo
# ═══════════════════════════════════════════════════════════════════════════

_AZUL     = "#1565C0"
_AZUL_BG  = "#E3F2FD"
_GRIS_BG  = "#F5F5F5"
_BORDE    = "#E0E0E0"

_COL_ESTADO_CITA = {
    "pendiente":  ("#FFF8E1", "#F9A825"),
    "confirmada": ("#E8F5E9", "#2E7D32"),
    "realizada":  ("#E3F2FD", "#1565C0"),
    "cancelada":  ("#FFEBEE", "#C62828"),
}
_COL_ESTADO_TRAT = {
    "presupuestado": ("#FFF8E1", "#E65100"),
    "aprobado":      ("#E8F5E9", "#1B5E20"),
    "realizado":     ("#E3F2FD", "#1565C0"),
}
_METODOS_PAGO = ["(Todos)", "efectivo", "tarjeta", "transferencia", "obra_social"]


# ═══════════════════════════════════════════════════════════════════════════
#  Helpers de UI
# ═══════════════════════════════════════════════════════════════════════════

def _badge(texto: str, bg: str, fg: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(texto.capitalize(), size=10, weight=ft.FontWeight.W_600, color=fg),
        bgcolor=bg, border_radius=20,
        padding=ft.padding.symmetric(horizontal=10, vertical=3),
    )


def _encabezado_tabla(columnas: list[tuple[str, int]]) -> ft.Container:
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Text(lbl, size=11, weight=ft.FontWeight.BOLD,
                        color=_AZUL, expand=exp)
                for lbl, exp in columnas
            ],
            spacing=0,
        ),
        bgcolor=_AZUL_BG,
        padding=ft.padding.symmetric(horizontal=14, vertical=8),
        border=ft.border.only(bottom=ft.BorderSide(1.5, "#BBDEFB")),
    )


def _fila_tabla(celdas: list[tuple], alt: bool = False) -> ft.Container:
    """
    celdas: lista de (contenido, expand) donde contenido puede ser str o ft.Control
    """
    controls = []
    for val, exp in celdas:
        if isinstance(val, ft.Control):
            controls.append(ft.Container(content=val, expand=exp))
        else:
            controls.append(ft.Text(str(val) if val else "—", size=11, expand=exp,
                                    color="#212121"))
    return ft.Container(
        content=ft.Row(controls=controls, spacing=0),
        bgcolor="#FAFAFA" if alt else ft.Colors.WHITE,
        padding=ft.padding.symmetric(horizontal=14, vertical=7),
        border=ft.border.only(bottom=ft.BorderSide(0.4, _BORDE)),
    )


def _kpi_card(titulo: str, valor: str, subtitulo: str,
              icono: str, color: str) -> ft.Container:
    return ft.Container(
        content=ft.Column(controls=[
            ft.Row(controls=[
                ft.Container(
                    content=ft.Icon(icono, size=22, color=ft.Colors.WHITE),
                    bgcolor=color, border_radius=10,
                    padding=ft.padding.all(8),
                ),
                ft.Column(controls=[
                    ft.Text(valor, size=26, weight=ft.FontWeight.BOLD, color="#212121"),
                    ft.Text(titulo, size=11, weight=ft.FontWeight.W_500, color="#616161"),
                ], spacing=0),
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Text(subtitulo, size=10, color="#9E9E9E"),
        ], spacing=6),
        bgcolor=ft.Colors.WHITE,
        border_radius=12,
        padding=16,
        border=ft.border.all(1, _BORDE),
        expand=True,
        shadow=ft.BoxShadow(blur_radius=4, color="#1212120A", offset=ft.Offset(0, 2)),
    )


def _btn_exportar(texto: str, on_click) -> ft.ElevatedButton:
    return ft.ElevatedButton(
        text=texto,
        icon=ft.Icons.PICTURE_AS_PDF,
        on_click=on_click,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.RED_800,
            color=ft.Colors.WHITE,
        ),
    )


def _titulo_modulo(texto: str) -> ft.Container:
    return ft.Container(
        content=ft.Row(controls=[
            ft.Icon(ft.Icons.ASSESSMENT, color=ft.Colors.WHITE, size=18),
            ft.Text(texto, size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
        ], spacing=10),
        bgcolor=_AZUL,
        padding=ft.padding.symmetric(horizontal=18, vertical=12),
    )


def _snack(page: ft.Page, msg: str, error: bool = False):
    page.snack_bar = ft.SnackBar(
        content=ft.Text(msg),
        bgcolor=ft.Colors.RED_700 if error else ft.Colors.GREEN_700,
        open=True,
    )
    page.update()


def _fmt_fecha(iso: str) -> str:
    if not iso:
        return "—"
    try:
        return datetime.datetime.fromisoformat(
            iso.replace("Z", "+00:00")).strftime("%d/%m/%Y")
    except Exception:
        return str(iso)[:10]


def _fmt_datetime(iso: str) -> tuple[str, str]:
    if not iso:
        return "—", "—"
    try:
        dt = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y"), dt.strftime("%H:%M")
    except Exception:
        return str(iso)[:10], ""


def _fmt_monto(v) -> str:
    try:
        return f"$ {float(v):,.2f}"
    except Exception:
        return "$ 0,00"


def _sin_datos() -> ft.Container:
    return ft.Container(
        content=ft.Column(controls=[
            ft.Icon(ft.Icons.SEARCH_OFF, size=40, color=ft.Colors.GREY_400),
            ft.Text("Sin datos para el período seleccionado.",
                    color=ft.Colors.GREY_400, size=13),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
           alignment=ft.MainAxisAlignment.CENTER),
        expand=True, alignment=ft.alignment.center,
    )


# ═══════════════════════════════════════════════════════════════════════════
#  TAB: Resumen / Dashboard
# ═══════════════════════════════════════════════════════════════════════════

class _ResumenTab(ft.Column):
    def __init__(self):
        super().__init__(
            spacing=0, expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
        self._cargando = ft.Container(
            content=ft.ProgressRing(),
            alignment=ft.alignment.center,
            expand=True,
        )
        self.controls = [self._cargando]

    def did_mount(self):
        self._cargar()

    def _cargar(self):
        try:
            stats = stats_resumen()
        except Exception as ex:
            self.controls = [ft.Text(f"Error al cargar estadísticas: {ex}",
                                     color=ft.Colors.RED_700)]
            if self.page:
                self.update()
            return

        mes = stats.get("mes_nombre", "")
        hoy = datetime.date.today().strftime("%d/%m/%Y")

        kpi_row = ft.Row(
            controls=[
                _kpi_card(
                    "Pacientes registrados",
                    str(stats["total_pacientes"]),
                    "Total en el sistema",
                    ft.Icons.PEOPLE, "#1565C0",
                ),
                _kpi_card(
                    "Citas hoy",
                    str(stats["citas_hoy"]),
                    f"Agendadas para {hoy}",
                    ft.Icons.TODAY, "#2E7D32",
                ),
                _kpi_card(
                    "Citas en el mes",
                    str(stats["citas_mes"]),
                    mes,
                    ft.Icons.CALENDAR_MONTH, "#6A1B9A",
                ),
                _kpi_card(
                    "Ingresos del mes",
                    _fmt_monto(stats["ingresos_mes"]),
                    mes,
                    ft.Icons.ATTACH_MONEY, "#E65100",
                ),
            ],
            spacing=12, expand=False,
        )

        # Desglose de citas del mes
        def _mini_stat(lbl, n, color):
            return ft.Container(
                content=ft.Column(controls=[
                    ft.Text(str(n), size=22, weight=ft.FontWeight.BOLD, color=color),
                    ft.Text(lbl, size=11, color="#616161"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   alignment=ft.MainAxisAlignment.CENTER, spacing=2),
                expand=True,
                border=ft.border.all(1, _BORDE), border_radius=10,
                padding=12, bgcolor=ft.Colors.WHITE,
                alignment=ft.alignment.center,
            )

        desglose_citas = ft.Container(
            content=ft.Column(controls=[
                ft.Text("Citas del mes — desglose",
                        size=12, weight=ft.FontWeight.BOLD, color=_AZUL),
                ft.Row(controls=[
                    _mini_stat("Realizadas",  stats["citas_realizadas"],  "#1565C0"),
                    _mini_stat("Pendientes",  stats["citas_pendientes"],  "#F9A825"),
                    _mini_stat("Canceladas",  stats["citas_canceladas"],  "#C62828"),
                ], spacing=10, expand=False),
            ], spacing=10),
            bgcolor=ft.Colors.WHITE,
            border_radius=12, padding=16,
            border=ft.border.all(1, _BORDE),
            shadow=ft.BoxShadow(blur_radius=4, color="#1212120A",
                                offset=ft.Offset(0, 2)),
        )

        trat_pend = ft.Container(
            content=ft.Column(controls=[
                ft.Text("Tratamientos activos",
                        size=12, weight=ft.FontWeight.BOLD, color=_AZUL),
                ft.Row(controls=[
                    ft.Icon(ft.Icons.HEALING, size=28, color="#E65100"),
                    ft.Text(str(stats["tratamientos_pend"]),
                            size=26, weight=ft.FontWeight.BOLD),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Text("presupuestados + aprobados (pendientes de realizar)",
                        size=10, color="#9E9E9E"),
            ], spacing=6),
            bgcolor=ft.Colors.WHITE,
            border_radius=12, padding=16,
            border=ft.border.all(1, _BORDE),
            expand=True,
            shadow=ft.BoxShadow(blur_radius=4, color="#1212120A",
                                offset=ft.Offset(0, 2)),
        )

        segunda_fila = ft.Row(
            controls=[desglose_citas, trat_pend],
            spacing=12, expand=False,
        )

        self.controls = [
            ft.Container(
                content=ft.Column(controls=[
                    ft.Text(
                        f"Panel de control  ·  {hoy}",
                        size=12, color="#616161",
                    ),
                    kpi_row,
                    segunda_fila,
                ], spacing=14, scroll=ft.ScrollMode.AUTO),
                padding=ft.padding.all(18),
                expand=True,
            )
        ]
        if self.page:
            self.update()


# ═══════════════════════════════════════════════════════════════════════════
#  TAB: Citas
# ═══════════════════════════════════════════════════════════════════════════

class _CitasTab(ft.Column):
    def __init__(self):
        super().__init__(spacing=0, expand=True)
        hoy    = datetime.date.today()
        inicio = hoy.replace(day=1).isoformat()
        self._tf_desde = ft.TextField(
            label="Desde", value=inicio, hint_text="AAAA-MM-DD",
            dense=True, expand=True,
        )
        self._tf_hasta = ft.TextField(
            label="Hasta", value=hoy.isoformat(), hint_text="AAAA-MM-DD",
            dense=True, expand=True,
        )
        self._dd_esp   = ft.Dropdown(
            label="Especialista", value=None,
            options=[ft.dropdown.Option("", "(Todos)")],
            expand=True, dense=True,
        )
        self._area = ft.Container(expand=True)
        self._datos: list[dict] = []
        self._construir_shell()

    def _construir_shell(self):
        filtros = ft.Container(
            content=ft.Row(controls=[
                ft.Row(controls=[self._tf_desde], expand=2),
                ft.Row(controls=[self._tf_hasta], expand=2),
                ft.Row(controls=[self._dd_esp],   expand=3),
                ft.ElevatedButton(
                    "Aplicar", icon=ft.Icons.FILTER_ALT,
                    on_click=lambda _: self._cargar(),
                    style=ft.ButtonStyle(bgcolor=_AZUL,
                                         color=ft.Colors.WHITE),
                ),
                _btn_exportar("Exportar PDF", self._exportar),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.END),
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            bgcolor=_GRIS_BG,
            border=ft.border.only(bottom=ft.BorderSide(1, _BORDE)),
        )
        self.controls = [filtros, self._area]

    def did_mount(self):
        try:
            esps = listar_especialistas()
            self._dd_esp.options = [ft.dropdown.Option("", "(Todos)")] + [
                ft.dropdown.Option(e["id"],
                    f"{e.get('apellido','')} {e.get('nombre','')}".strip())
                for e in esps
            ]
            if self._dd_esp.page:
                self._dd_esp.update()
        except Exception:
            pass
        self._cargar()

    def _cargar(self):
        self._area.content = ft.Container(
            content=ft.ProgressRing(),
            alignment=ft.alignment.center, expand=True,
        )
        if self._area.page:
            self._area.update()
        try:
            esp_id = self._dd_esp.value or None
            self._datos = listar_citas_rango(
                self._tf_desde.value.strip() or None,
                self._tf_hasta.value.strip() or None,
                esp_id if esp_id else None,
            )
        except Exception as ex:
            self._area.content = ft.Text(f"Error: {ex}", color=ft.Colors.RED_700)
            if self._area.page:
                self._area.update()
            return
        self._refrescar_tabla()

    def _refrescar_tabla(self):
        datos = self._datos
        if not datos:
            self._area.content = _sin_datos()
            if self._area.page:
                self._area.update()
            return

        columnas = [
            ("Fecha", 2), ("Hora", 1), ("Paciente", 4),
            ("Especialista", 3), ("Motivo", 4), ("Estado", 2),
        ]
        filas = [_encabezado_tabla(columnas)]

        est_count: dict[str, int] = {}
        for i, c in enumerate(datos):
            pac  = (c.get("pacientes") or {})
            esp  = (c.get("especialistas") or {})
            nom_pac = f"{pac.get('apellido','')} {pac.get('nombre','')}".strip()
            nom_esp = f"{esp.get('apellido','')} {esp.get('nombre','')}".strip()
            fecha, hora = _fmt_datetime(c.get("fecha_hora",""))
            estado = c.get("estado","")
            bg, fg = _COL_ESTADO_CITA.get(estado, ("#EEEEEE","#212121"))
            est_count[estado] = est_count.get(estado, 0) + 1
            filas.append(_fila_tabla([
                (fecha, 2), (hora, 1), (nom_pac or "—", 4),
                (nom_esp or "—", 3), (c.get("motivo","") or "—", 4),
                (_badge(estado, bg, fg), 2),
            ], alt=i % 2 == 1))

        # Barra de totales
        total_bar = ft.Container(
            content=ft.Row(controls=[
                ft.Text(f"Total: {len(datos)} citas", size=11,
                        weight=ft.FontWeight.BOLD),
                *[_badge(f"{n} {est}", *_COL_ESTADO_CITA.get(est, ("#EEE","#212121")))
                  for est, n in sorted(est_count.items())],
            ], spacing=10, wrap=True),
            padding=ft.padding.symmetric(horizontal=14, vertical=8),
            bgcolor=_AZUL_BG,
            border=ft.border.only(top=ft.BorderSide(1, "#BBDEFB")),
        )

        self._area.content = ft.Column(
            controls=[
                ft.Container(
                    content=ft.Column(controls=filas, spacing=0),
                    expand=True,
                ),
                total_bar,
            ],
            spacing=0, expand=True,
        )
        self._area.content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Column(controls=filas, spacing=0, scroll=None),
                        expand=True,
                    ),
                    total_bar,
                ],
                spacing=0, expand=True, scroll=ft.ScrollMode.AUTO,
            ),
            expand=True,
        )
        if self._area.page:
            self._area.update()

    def _exportar(self, e=None):
        if not self._datos:
            if self.page:
                _snack(self.page, "No hay datos para exportar.", error=True)
            return
        try:
            from generar_pdf import exportar_reporte_citas
            out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdfs")
            ruta    = exportar_reporte_citas(self._datos,
                                             self._tf_desde.value,
                                             self._tf_hasta.value,
                                             output_dir=out_dir)
            nombre = os.path.basename(ruta)
            print(f"[PDF-Citas] {ruta}", flush=True)
            if self.page:
                dlg = ft.AlertDialog(
                    title=ft.Text("Reporte de Citas generado"),
                    content=ft.Text(f"Guardado en: pdfs/{nombre}",
                                    selectable=True),
                    actions=[ft.TextButton("Cerrar",
                             on_click=lambda _: self.page.pop_dialog())],
                )
                self.page.show_dialog(dlg)
        except Exception as ex:
            import traceback; traceback.print_exc()
            if self.page:
                _snack(self.page, f"Error: {ex}", error=True)


# ═══════════════════════════════════════════════════════════════════════════
#  TAB: Ingresos
# ═══════════════════════════════════════════════════════════════════════════

class _IngresosTab(ft.Column):
    def __init__(self):
        super().__init__(spacing=0, expand=True)
        hoy    = datetime.date.today()
        inicio = hoy.replace(day=1).isoformat()
        self._tf_desde = ft.TextField(
            label="Desde", value=inicio, hint_text="AAAA-MM-DD",
            dense=True, expand=True,
        )
        self._tf_hasta = ft.TextField(
            label="Hasta", value=hoy.isoformat(), hint_text="AAAA-MM-DD",
            dense=True, expand=True,
        )
        self._dd_met = ft.Dropdown(
            label="Método de pago", value=None,
            options=[ft.dropdown.Option("", "(Todos)"),
                     ft.dropdown.Option("efectivo",      "Efectivo"),
                     ft.dropdown.Option("tarjeta",       "Tarjeta"),
                     ft.dropdown.Option("transferencia", "Transferencia"),
                     ft.dropdown.Option("obra_social",   "Obra Social")],
            expand=True, dense=True,
        )
        self._area = ft.Container(expand=True)
        self._datos: list[dict] = []
        self._construir_shell()

    def _construir_shell(self):
        filtros = ft.Container(
            content=ft.Row(controls=[
                ft.Row(controls=[self._tf_desde], expand=2),
                ft.Row(controls=[self._tf_hasta], expand=2),
                ft.Row(controls=[self._dd_met],   expand=3),
                ft.ElevatedButton(
                    "Aplicar", icon=ft.Icons.FILTER_ALT,
                    on_click=lambda _: self._cargar(),
                    style=ft.ButtonStyle(bgcolor=_AZUL,
                                         color=ft.Colors.WHITE),
                ),
                _btn_exportar("Exportar PDF", self._exportar),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.END),
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            bgcolor=_GRIS_BG,
            border=ft.border.only(bottom=ft.BorderSide(1, _BORDE)),
        )
        self.controls = [filtros, self._area]

    def did_mount(self):
        self._cargar()

    def _cargar(self):
        self._area.content = ft.Container(
            content=ft.ProgressRing(),
            alignment=ft.alignment.center, expand=True,
        )
        if self._area.page:
            self._area.update()
        try:
            met = self._dd_met.value or None
            self._datos = listar_pagos_todos(
                self._tf_desde.value.strip() or None,
                self._tf_hasta.value.strip() or None,
                met if met else None,
            )
        except Exception as ex:
            self._area.content = ft.Text(f"Error: {ex}", color=ft.Colors.RED_700)
            if self._area.page:
                self._area.update()
            return
        self._refrescar_tabla()

    def _refrescar_tabla(self):
        datos = self._datos
        if not datos:
            self._area.content = _sin_datos()
            if self._area.page:
                self._area.update()
            return

        total = sum(float(p.get("monto", 0)) for p in datos)

        columnas = [
            ("Fecha", 2), ("Paciente", 4), ("Tratamiento", 5),
            ("Monto", 2), ("Método", 2), ("Comprobante", 2),
        ]
        filas = [_encabezado_tabla(columnas)]

        met_totales: dict[str, float] = {}
        for i, p in enumerate(datos):
            pac = (p.get("pacientes") or {})
            tra = (p.get("tratamientos") or {})
            nom_pac = f"{pac.get('apellido','')} {pac.get('nombre','')}".strip()
            met = p.get("metodo","") or "—"
            monto = float(p.get("monto", 0))
            met_totales[met] = met_totales.get(met, 0) + monto
            filas.append(_fila_tabla([
                (_fmt_fecha(p.get("fecha","")), 2),
                (nom_pac or "—", 4),
                (tra.get("descripcion","") or "—", 5),
                (ft.Text(_fmt_monto(monto), size=11,
                         weight=ft.FontWeight.W_500, color="#1B5E20"), 2),
                (met.replace("_"," ").capitalize(), 2),
                (p.get("comprobante","") or "—", 2),
            ], alt=i % 2 == 1))

        total_bar = ft.Container(
            content=ft.Row(controls=[
                ft.Text(f"Total del período:", size=12,
                        weight=ft.FontWeight.BOLD),
                ft.Text(_fmt_monto(total), size=14,
                        weight=ft.FontWeight.BOLD, color="#1B5E20"),
                ft.Container(expand=True),
                *[
                    ft.Text(
                        f"{m.replace('_',' ').capitalize()}: {_fmt_monto(v)}",
                        size=10, color="#616161",
                    )
                    for m, v in sorted(met_totales.items())
                ],
            ], spacing=14, wrap=False),
            padding=ft.padding.symmetric(horizontal=14, vertical=8),
            bgcolor="#E8F5E9",
            border=ft.border.only(top=ft.BorderSide(1, "#A5D6A7")),
        )

        self._area.content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Column(controls=filas, spacing=0),
                        expand=True,
                    ),
                    total_bar,
                ],
                spacing=0, expand=True, scroll=ft.ScrollMode.AUTO,
            ),
            expand=True,
        )
        if self._area.page:
            self._area.update()

    def _exportar(self, e=None):
        if not self._datos:
            if self.page:
                _snack(self.page, "No hay datos para exportar.", error=True)
            return
        try:
            from generar_pdf import exportar_reporte_ingresos
            out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdfs")
            ruta    = exportar_reporte_ingresos(self._datos,
                                                self._tf_desde.value,
                                                self._tf_hasta.value,
                                                output_dir=out_dir)
            nombre = os.path.basename(ruta)
            print(f"[PDF-Ingresos] {ruta}", flush=True)
            if self.page:
                dlg = ft.AlertDialog(
                    title=ft.Text("Reporte de Ingresos generado"),
                    content=ft.Text(f"Guardado en: pdfs/{nombre}",
                                    selectable=True),
                    actions=[ft.TextButton("Cerrar",
                             on_click=lambda _: self.page.pop_dialog())],
                )
                self.page.show_dialog(dlg)
        except Exception as ex:
            import traceback; traceback.print_exc()
            if self.page:
                _snack(self.page, f"Error: {ex}", error=True)


# ═══════════════════════════════════════════════════════════════════════════
#  TAB: Tratamientos
# ═══════════════════════════════════════════════════════════════════════════

class _TratamientosTab(ft.Column):
    def __init__(self):
        super().__init__(spacing=0, expand=True)
        self._dd_estado = ft.Dropdown(
            label="Estado", value="",
            options=[
                ft.dropdown.Option("",             "(Todos)"),
                ft.dropdown.Option("presupuestado","Presupuestado"),
                ft.dropdown.Option("aprobado",     "Aprobado"),
                ft.dropdown.Option("realizado",    "Realizado"),
            ],
            expand=True, dense=True,
        )
        self._area = ft.Container(expand=True)
        self._datos: list[dict] = []
        self._construir_shell()

    def _construir_shell(self):
        filtros = ft.Container(
            content=ft.Row(controls=[
                ft.Row(controls=[self._dd_estado], expand=3),
                ft.ElevatedButton(
                    "Aplicar", icon=ft.Icons.FILTER_ALT,
                    on_click=lambda _: self._cargar(),
                    style=ft.ButtonStyle(bgcolor=_AZUL,
                                         color=ft.Colors.WHITE),
                ),
                _btn_exportar("Exportar PDF", self._exportar),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.END),
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            bgcolor=_GRIS_BG,
            border=ft.border.only(bottom=ft.BorderSide(1, _BORDE)),
        )
        self.controls = [filtros, self._area]

    def did_mount(self):
        self._cargar()

    def _cargar(self):
        self._area.content = ft.Container(
            content=ft.ProgressRing(),
            alignment=ft.alignment.center, expand=True,
        )
        if self._area.page:
            self._area.update()
        try:
            est = self._dd_estado.value or None
            self._datos = listar_tratamientos_todos(estado=est if est else None)
        except Exception as ex:
            self._area.content = ft.Text(f"Error: {ex}", color=ft.Colors.RED_700)
            if self._area.page:
                self._area.update()
            return
        self._refrescar_tabla()

    def _refrescar_tabla(self):
        datos = self._datos
        if not datos:
            self._area.content = _sin_datos()
            if self._area.page:
                self._area.update()
            return

        # Resumen por estado
        resumen: dict[str, dict] = {
            "presupuestado": {"n": 0, "total": 0},
            "aprobado":      {"n": 0, "total": 0},
            "realizado":     {"n": 0, "total": 0},
        }
        for t in datos:
            est   = t.get("estado","")
            costo = float(t.get("costo", 0))
            if est in resumen:
                resumen[est]["n"]     += 1
                resumen[est]["total"] += costo

        etiquetas = {"presupuestado":"Presupuestados","aprobado":"Aprobados","realizado":"Realizados"}
        resumen_row = ft.Row(
            controls=[
                ft.Container(
                    content=ft.Column(controls=[
                        ft.Text(etiquetas.get(est, est),
                                size=11, weight=ft.FontWeight.BOLD,
                                color=_COL_ESTADO_TRAT.get(est,("#EEE","#333"))[1]),
                        ft.Text(str(vals["n"]),
                                size=20, weight=ft.FontWeight.BOLD),
                        ft.Text(_fmt_monto(vals["total"]),
                                size=11, color="#616161"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                       alignment=ft.MainAxisAlignment.CENTER, spacing=3),
                    bgcolor=_COL_ESTADO_TRAT.get(est,("#EEE","#333"))[0],
                    border_radius=10, padding=14, expand=True,
                    border=ft.border.all(1, _BORDE),
                    alignment=ft.alignment.center,
                )
                for est, vals in resumen.items()
            ],
            spacing=10,
        )

        columnas = [
            ("Fecha", 2), ("Paciente", 4), ("Descripción", 5),
            ("Diente", 1), ("Especialista", 3), ("Costo", 2), ("Estado", 2),
        ]
        filas = [_encabezado_tabla(columnas)]
        for i, t in enumerate(datos):
            pac = (t.get("pacientes") or {})
            esp = (t.get("especialistas") or {})
            nom_pac = f"{pac.get('apellido','')} {pac.get('nombre','')}".strip()
            nom_esp = f"{esp.get('apellido','')} {esp.get('nombre','')}".strip()
            estado  = t.get("estado","")
            bg, fg  = _COL_ESTADO_TRAT.get(estado, ("#EEE","#333"))
            diente  = str(t.get("diente","")) if t.get("diente") else "—"
            filas.append(_fila_tabla([
                (_fmt_fecha(t.get("fecha","")), 2),
                (nom_pac or "—", 4),
                (t.get("descripcion","") or "—", 5),
                (diente, 1),
                (nom_esp or "—", 3),
                (ft.Text(_fmt_monto(t.get("costo",0)), size=11,
                         weight=ft.FontWeight.W_500), 2),
                (_badge(estado, bg, fg), 2),
            ], alt=i % 2 == 1))

        gran_total = sum(float(t.get("costo", 0)) for t in datos)
        total_bar  = ft.Container(
            content=ft.Row(controls=[
                ft.Text(f"{len(datos)} tratamientos", size=11,
                        weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                ft.Text("Total general:", size=12),
                ft.Text(_fmt_monto(gran_total), size=14,
                        weight=ft.FontWeight.BOLD, color="#1565C0"),
            ], spacing=14),
            padding=ft.padding.symmetric(horizontal=14, vertical=8),
            bgcolor=_AZUL_BG,
            border=ft.border.only(top=ft.BorderSide(1, "#BBDEFB")),
        )

        self._area.content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=resumen_row,
                        padding=ft.padding.symmetric(horizontal=14, vertical=10),
                    ),
                    ft.Container(
                        content=ft.Column(controls=filas, spacing=0),
                        expand=True,
                    ),
                    total_bar,
                ],
                spacing=0, expand=True, scroll=ft.ScrollMode.AUTO,
            ),
            expand=True,
        )
        if self._area.page:
            self._area.update()

    def _exportar(self, e=None):
        if not self._datos:
            if self.page:
                _snack(self.page, "No hay datos para exportar.", error=True)
            return
        try:
            from generar_pdf import exportar_reporte_tratamientos
            out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdfs")
            est     = self._dd_estado.value or ""
            ruta    = exportar_reporte_tratamientos(self._datos,
                                                    estado_filtro=est,
                                                    output_dir=out_dir)
            nombre = os.path.basename(ruta)
            print(f"[PDF-Tratamientos] {ruta}", flush=True)
            if self.page:
                dlg = ft.AlertDialog(
                    title=ft.Text("Reporte de Tratamientos generado"),
                    content=ft.Text(f"Guardado en: pdfs/{nombre}",
                                    selectable=True),
                    actions=[ft.TextButton("Cerrar",
                             on_click=lambda _: self.page.pop_dialog())],
                )
                self.page.show_dialog(dlg)
        except Exception as ex:
            import traceback; traceback.print_exc()
            if self.page:
                _snack(self.page, f"Error: {ex}", error=True)


# ═══════════════════════════════════════════════════════════════════════════
#  Vista principal: ReportesView
# ═══════════════════════════════════════════════════════════════════════════

_TABS = [
    ("Resumen",        ft.Icons.DASHBOARD),
    ("Citas",          ft.Icons.CALENDAR_MONTH),
    ("Ingresos",       ft.Icons.ATTACH_MONEY),
    ("Tratamientos",   ft.Icons.HEALING),
]

_TAB_VISTAS = [
    _ResumenTab,
    _CitasTab,
    _IngresosTab,
    _TratamientosTab,
]


class ReportesView(ft.Column):
    def __init__(self):
        super().__init__(spacing=0, expand=True, padding=0)
        self._tab  = 0
        self._area = ft.Container(expand=True)
        self._tab_btns: list[ft.ElevatedButton] = []
        self._construir()

    def _construir(self):
        for i, (lbl, icn) in enumerate(_TABS):
            idx = i
            btn = ft.ElevatedButton(
                text=lbl, icon=icn,
                on_click=lambda _, x=idx: self._sel(x),
                style=ft.ButtonStyle(
                    bgcolor=_AZUL if i == 0 else ft.Colors.WHITE,
                    color=ft.Colors.WHITE if i == 0 else "#212121",
                    side=ft.BorderSide(1, _BORDE),
                ),
            )
            self._tab_btns.append(btn)

        barra_tabs = ft.Container(
            content=ft.Row(
                controls=self._tab_btns,
                spacing=6,
            ),
            padding=ft.padding.symmetric(horizontal=14, vertical=8),
            bgcolor="#FAFAFA",
            border=ft.border.only(bottom=ft.BorderSide(1, _BORDE)),
        )

        self.controls = [
            _titulo_modulo("Reportes y Estadísticas"),
            barra_tabs,
            self._area,
        ]

    def did_mount(self):
        self._cargar_vista()

    def _sel(self, idx: int):
        self._tab = idx
        for i, btn in enumerate(self._tab_btns):
            btn.style = ft.ButtonStyle(
                bgcolor=_AZUL if i == idx else ft.Colors.WHITE,
                color=ft.Colors.WHITE if i == idx else "#212121",
                side=ft.BorderSide(1, _BORDE),
            )
            if btn.page:
                btn.update()
        self._cargar_vista()

    def _cargar_vista(self):
        vista = _TAB_VISTAS[self._tab]()
        self._area.content = vista
        if self._area.page:
            self._area.update()
