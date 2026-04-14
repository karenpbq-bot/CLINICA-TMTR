# Consultorio Odontológico

Aplicación de gestión clínica dental — **Python puro + Flet 0.84 + Supabase**.

## Estructura del proyecto

```
/
├── main.py                  # Entrada, auth, NavigationRail, inactividad
├── database.py              # ÚNICO gestor Supabase (anon key)
├── modulo_pacientes.py      # Historia Clínica completa (selector + formulario)
│                            #   ► Exporta: PacientesView, HistoriaClinicaView,
│                            #              OdontogramaDiagnosticoView
├── modulo_tratamientos.py   # Plan de Tratamientos (2 tabs: HC + Presupuesto)
├── modulo_agenda.py         # Citas y agenda
├── modulo_pagos.py          # Pagos y facturación
├── modulo_usuarios.py       # CRUD de usuarios del sistema
├── especialistas.py         # Gestión de especialistas
├── modulo_reportes.py       # Reportes: Resumen, Citas, Ingresos, Tratamientos
├── generar_pdf.py           # Exportación PDF: HC completa + 3 reportes
├── pdfs/                    # PDFs generados (descargables desde el explorador)
├── schema.sql               # Referencia DDL de las 10 tablas Supabase
├── pyproject.toml           # Dependencias Python
└── artifacts/mockup-sandbox # Servidor de mockups de canvas (independiente)
```

## Tablas Supabase (10)
`pacientes`, `constantes_vitales`, `odontograma`, `especialistas`,
`disponibilidad`, `citas`, `tratamientos`, `pagos`, `usuarios`, `historia_clinica`

## Módulo Pacientes (modulo_pacientes.py)
- `PacientesView` — selector de paciente + carga `HistoriaClinicaView`
- `HistoriaClinicaView` — formulario completo: info general, anamnesis, signos vitales,
  21 antecedentes, odontograma diagnóstico, observaciones
- `OdontogramaDiagnosticoView` — grilla 32 dientes interactiva con panel de detalle por pieza
- Constantes compartidas: `ESTADOS_DIENTE`, `CARAS`, `DIENTES_ADULTO`

## Módulo Tratamientos (modulo_tratamientos.py)
- Importa `HistoriaClinicaView` desde `modulo_pacientes`
- Tab 1: Historia Clínica del paciente seleccionado
- Tab 2: Plan de Tratamientos (CRUD de items, estados, presupuesto)

## Autenticación
- Usuario: `Admin` / contraseña: `Admin`
- Hash BCrypt en `.replit [userenv.shared]`
- Roles: Administrador, Recepcionista, Especialista, Cliente
- Inactividad: logout automático a los 5 minutos

## Notas técnicas Flet 0.84
- `ft.Column`/`ft.Row` usa `alignment=` (NO `main_axis_alignment=`)
- Ícono dental: `ft.Icons.MEDICAL_SERVICES` (DENTISTRY no existe)
- `Dropdown` usa `on_select=` (no `on_change`)
- Diálogos: `page.show_dialog(dlg)` / `page.pop_dialog()`
- Puerto: 8000 (workflow principal)
