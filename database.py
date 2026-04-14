"""
Módulo de conexión y acceso a datos con Supabase.
Requiere: pip install supabase
"""

import os
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise EnvironmentError(
                "Configura las variables de entorno SUPABASE_URL y SUPABASE_KEY."
            )
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


# ---------------------------------------------------------------------------
# Esquema SQL de referencia (ejecutar en el SQL Editor de Supabase)
# ---------------------------------------------------------------------------
#
# -- TABLA: pacientes
# CREATE TABLE pacientes (
#     id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
#     nombre        TEXT NOT NULL,
#     apellido      TEXT NOT NULL,
#     fecha_nac     DATE,
#     dni           TEXT UNIQUE,
#     telefono      TEXT,
#     email         TEXT,
#     direccion     TEXT,
#     obra_social   TEXT,
#     nro_afiliado  TEXT,
#     grupo_sangre  TEXT,
#     alergias      TEXT,
#     antecedentes  JSONB,   -- {"diabetes": false, "hipertension": true, ...}
#     creado_en     TIMESTAMPTZ DEFAULT now()
# );
#
# -- TABLA: constantes_vitales
# CREATE TABLE constantes_vitales (
#     id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
#     paciente_id   UUID REFERENCES pacientes(id) ON DELETE CASCADE,
#     fecha         TIMESTAMPTZ DEFAULT now(),
#     presion_sys   INTEGER,
#     presion_dia   INTEGER,
#     peso_kg       NUMERIC(5,2),
#     altura_cm     NUMERIC(5,1),
#     imc           NUMERIC(5,2) GENERATED ALWAYS AS (
#                       peso_kg / ((altura_cm / 100) * (altura_cm / 100))
#                   ) STORED
# );
#
# -- TABLA: odontograma
# -- 'caras' guarda el estado de las 5 superficies por cada diente:
# --   { "oclusal": "caries", "vestibular": "sano", "lingual": "obturado",
# --     "mesial": "sano", "distal": "extraccion" }
# -- Estados posibles: sano | caries | obturado | fractura | extraccion |
# --                   corona | implante | ausente
# CREATE TABLE odontograma (
#     id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
#     paciente_id   UUID REFERENCES pacientes(id) ON DELETE CASCADE,
#     fecha         TIMESTAMPTZ DEFAULT now(),
#     diente        INTEGER NOT NULL,   -- número FDI: 11..48
#     caras         JSONB NOT NULL DEFAULT '{
#                       "oclusal": "sano",
#                       "vestibular": "sano",
#                       "lingual": "sano",
#                       "mesial": "sano",
#                       "distal": "sano"
#                   }',
#     observacion   TEXT,
#     UNIQUE (paciente_id, diente)
# );
#
# -- TABLA: especialistas
# CREATE TABLE especialistas (
#     id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
#     nombre        TEXT NOT NULL,
#     apellido      TEXT NOT NULL,
#     matricula     TEXT UNIQUE,
#     especialidades JSONB,   -- ["Ortodoncia", "Odontopediatría"]
#     telefono      TEXT,
#     email         TEXT,
#     activo        BOOLEAN DEFAULT true
# );
#
# -- TABLA: disponibilidad
# -- certeza: 'confirmado' | 'probable' | 'por_confirmar'
# CREATE TABLE disponibilidad (
#     id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
#     especialista_id UUID REFERENCES especialistas(id) ON DELETE CASCADE,
#     dia_semana      SMALLINT,   -- 0=Lunes … 6=Domingo
#     hora_inicio     TIME NOT NULL,
#     hora_fin        TIME NOT NULL,
#     certeza         TEXT NOT NULL DEFAULT 'por_confirmar'
#                     CHECK (certeza IN ('confirmado', 'probable', 'por_confirmar'))
# );
#
# -- TABLA: citas
# -- estado: 'pendiente' | 'confirmada' | 'realizada' | 'cancelada'
# CREATE TABLE citas (
#     id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
#     paciente_id     UUID REFERENCES pacientes(id) ON DELETE CASCADE,
#     especialista_id UUID REFERENCES especialistas(id) ON DELETE SET NULL,
#     fecha_hora      TIMESTAMPTZ NOT NULL,
#     duracion_min    INTEGER DEFAULT 30,
#     motivo          TEXT,
#     estado          TEXT NOT NULL DEFAULT 'pendiente'
#                     CHECK (estado IN ('pendiente','confirmada','realizada','cancelada')),
#     notas           TEXT,
#     creado_en       TIMESTAMPTZ DEFAULT now()
# );
#
# -- TABLA: tratamientos
# CREATE TABLE tratamientos (
#     id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
#     paciente_id     UUID REFERENCES pacientes(id) ON DELETE CASCADE,
#     especialista_id UUID REFERENCES especialistas(id) ON DELETE SET NULL,
#     fecha           TIMESTAMPTZ DEFAULT now(),
#     diente          INTEGER,
#     cara            TEXT,   -- superficie tratada
#     descripcion     TEXT NOT NULL,
#     costo           NUMERIC(10,2) NOT NULL DEFAULT 0,
#     estado          TEXT NOT NULL DEFAULT 'presupuestado'
#                     CHECK (estado IN ('presupuestado','aprobado','realizado'))
# );
#
# -- TABLA: pagos
# CREATE TABLE pagos (
#     id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
#     paciente_id     UUID REFERENCES pacientes(id) ON DELETE CASCADE,
#     tratamiento_id  UUID REFERENCES tratamientos(id) ON DELETE SET NULL,
#     fecha           TIMESTAMPTZ DEFAULT now(),
#     monto           NUMERIC(10,2) NOT NULL,
#     metodo          TEXT,   -- efectivo | tarjeta | transferencia | obra_social
#     comprobante     TEXT,
#     notas           TEXT
# );
# ---------------------------------------------------------------------------


# ── PACIENTES ──────────────────────────────────────────────────────────────

def listar_pacientes():
    return get_client().table("pacientes").select("*").order("apellido").execute().data


def obtener_paciente(paciente_id: str):
    return (
        get_client().table("pacientes").select("*").eq("id", paciente_id).single().execute().data
    )


def crear_paciente(datos: dict):
    return get_client().table("pacientes").insert(datos).execute().data


def actualizar_paciente(paciente_id: str, datos: dict):
    return (
        get_client().table("pacientes").update(datos).eq("id", paciente_id).execute().data
    )


def eliminar_paciente(paciente_id: str):
    return get_client().table("pacientes").delete().eq("id", paciente_id).execute().data


# ── CONSTANTES VITALES ────────────────────────────────────────────────────

def listar_constantes(paciente_id: str):
    return (
        get_client()
        .table("constantes_vitales")
        .select("*")
        .eq("paciente_id", paciente_id)
        .order("fecha", desc=True)
        .execute()
        .data
    )


def registrar_constante(datos: dict):
    return get_client().table("constantes_vitales").insert(datos).execute().data


# ── ODONTOGRAMA ───────────────────────────────────────────────────────────

def obtener_odontograma(paciente_id: str):
    return (
        get_client()
        .table("odontograma")
        .select("*")
        .eq("paciente_id", paciente_id)
        .execute()
        .data
    )


def guardar_diente(paciente_id: str, diente: int, caras: dict, observacion: str = ""):
    payload = {
        "paciente_id": paciente_id,
        "diente": diente,
        "caras": caras,
        "observacion": observacion,
    }
    return (
        get_client()
        .table("odontograma")
        .upsert(payload, on_conflict="paciente_id,diente")
        .execute()
        .data
    )


# ── ESPECIALISTAS ─────────────────────────────────────────────────────────

def listar_especialistas():
    return (
        get_client()
        .table("especialistas")
        .select("*")
        .eq("activo", True)
        .order("apellido")
        .execute()
        .data
    )


def crear_especialista(datos: dict):
    return get_client().table("especialistas").insert(datos).execute().data


def actualizar_especialista(especialista_id: str, datos: dict):
    return (
        get_client()
        .table("especialistas")
        .update(datos)
        .eq("id", especialista_id)
        .execute()
        .data
    )


# ── PACIENTE ↔ ESPECIALISTAS (N:M) ────────────────────────────────────────

def listar_especialistas_de_paciente(paciente_id: str):
    return (
        get_client()
        .table("paciente_especialistas")
        .select("*, especialistas(id, nombre, apellido, especialidades)")
        .eq("paciente_id", paciente_id)
        .execute()
        .data
    )


def asignar_especialista_a_paciente(paciente_id: str, especialista_id: str):
    return (
        get_client()
        .table("paciente_especialistas")
        .upsert({"paciente_id": paciente_id, "especialista_id": especialista_id})
        .execute()
        .data
    )


def desasignar_especialista_de_paciente(paciente_id: str, especialista_id: str):
    return (
        get_client()
        .table("paciente_especialistas")
        .delete()
        .eq("paciente_id", paciente_id)
        .eq("especialista_id", especialista_id)
        .execute()
        .data
    )


# ── DISPONIBILIDAD ────────────────────────────────────────────────────────

def listar_disponibilidad(especialista_id: str):
    return (
        get_client()
        .table("disponibilidad")
        .select("*")
        .eq("especialista_id", especialista_id)
        .execute()
        .data
    )


def guardar_disponibilidad(datos: dict):
    return get_client().table("disponibilidad").insert(datos).execute().data


def eliminar_disponibilidad(disponibilidad_id: str):
    return (
        get_client().table("disponibilidad").delete().eq("id", disponibilidad_id).execute().data
    )


# ── CITAS ─────────────────────────────────────────────────────────────────

def listar_citas(filtros: dict | None = None):
    query = get_client().table("citas").select(
        "*, pacientes(nombre, apellido), especialistas(nombre, apellido)"
    )
    if filtros:
        for campo, valor in filtros.items():
            query = query.eq(campo, valor)
    return query.order("fecha_hora").execute().data


def crear_cita(datos: dict):
    return get_client().table("citas").insert(datos).execute().data


def actualizar_cita(cita_id: str, datos: dict):
    return get_client().table("citas").update(datos).eq("id", cita_id).execute().data


def cancelar_cita(cita_id: str):
    return actualizar_cita(cita_id, {"estado": "cancelada"})


def eliminar_cita(cita_id: str):
    return get_client().table("citas").delete().eq("id", cita_id).execute().data


# ── TRATAMIENTOS ──────────────────────────────────────────────────────────

def listar_tratamientos(paciente_id: str):
    return (
        get_client()
        .table("tratamientos")
        .select("*, especialistas(nombre, apellido)")
        .eq("paciente_id", paciente_id)
        .order("fecha", desc=True)
        .execute()
        .data
    )


def crear_tratamiento(datos: dict):
    return get_client().table("tratamientos").insert(datos).execute().data


def actualizar_tratamiento(tratamiento_id: str, datos: dict):
    return (
        get_client().table("tratamientos").update(datos).eq("id", tratamiento_id).execute().data
    )


def eliminar_tratamiento(tratamiento_id: str):
    return get_client().table("tratamientos").delete().eq("id", tratamiento_id).execute().data


# ── PAGOS ─────────────────────────────────────────────────────────────────

def listar_pagos(paciente_id: str):
    return (
        get_client()
        .table("pagos")
        .select("*, tratamientos(descripcion, costo)")
        .eq("paciente_id", paciente_id)
        .order("fecha", desc=True)
        .execute()
        .data
    )


def registrar_pago(datos: dict):
    return get_client().table("pagos").insert(datos).execute().data


def eliminar_pago(pago_id: str):
    return get_client().table("pagos").delete().eq("id", pago_id).execute().data


# ── USUARIOS / AUTENTICACIÓN ──────────────────────────────────────────────

def obtener_usuario_por_nombre(usuario: str):
    """Devuelve el registro del usuario o None si no existe."""
    resultado = (
        get_client()
        .table("usuarios")
        .select("*")
        .eq("usuario", usuario)
        .eq("activo", True)
        .execute()
        .data
    )
    return resultado[0] if resultado else None


# ── HISTORIA CLÍNICA ──────────────────────────────────────────────────────

def obtener_historia_clinica(paciente_id: str) -> dict | None:
    """Devuelve la historia clínica del paciente o None si no existe."""
    res = (
        get_client()
        .table("historia_clinica")
        .select("*")
        .eq("paciente_id", paciente_id)
        .execute()
        .data
    )
    return res[0] if res else None


def guardar_historia_clinica(paciente_id: str, datos: dict) -> dict:
    """
    Upsert de historia clínica: crea si no existe, actualiza si ya existe.
    datos debe incluir todos los campos del formulario.
    """
    client = get_client()
    existente = obtener_historia_clinica(paciente_id)
    payload = {**datos, "paciente_id": paciente_id,
               "actualizado_en": "now()"}
    if existente:
        client.table("historia_clinica").update(payload).eq(
            "paciente_id", paciente_id
        ).execute()
        return {**existente, **payload}
    else:
        res = client.table("historia_clinica").insert(payload).execute()
        return res.data[0]


def actualizar_diagnostico_dental(paciente_id: str, diagnostico_dental: dict):
    """Guarda/actualiza solo el campo diagnostico_dental en historia_clinica."""
    client = get_client()
    existente = obtener_historia_clinica(paciente_id)
    if existente:
        client.table("historia_clinica").update(
            {"diagnostico_dental": diagnostico_dental, "actualizado_en": "now()"}
        ).eq("paciente_id", paciente_id).execute()
    else:
        client.table("historia_clinica").insert(
            {"paciente_id": paciente_id, "diagnostico_dental": diagnostico_dental}
        ).execute()


ROLES_VALIDOS = ("Administrador", "Recepcionista", "Especialista", "Cliente")


def registrar_acceso(usuario_id: str):
    """Actualiza el campo ultimo_acceso con la hora actual."""
    get_client().table("usuarios").update(
        {"ultimo_acceso": "now()"}
    ).eq("id", usuario_id).execute()


def listar_usuarios() -> list[dict]:
    """Lista todos los usuarios del sistema."""
    return (
        get_client()
        .table("usuarios")
        .select("id,usuario,nombre,rol,activo,creado_en,ultimo_acceso")
        .order("creado_en")
        .execute()
        .data
    )


def verificar_login(usuario: str, password: str) -> dict | None:
    """
    Busca el usuario en la tabla 'usuarios' de Supabase y verifica la contraseña.
    Devuelve el dict del usuario si las credenciales son correctas y el usuario
    está activo, o None en caso contrario.
    """
    import bcrypt as _bcrypt
    filas = (
        get_client()
        .table("usuarios")
        .select("id,usuario,nombre,rol,activo,password_hash")
        .ilike("usuario", usuario.strip())
        .limit(1)
        .execute()
        .data
    )
    if not filas:
        return None
    u = filas[0]
    if not u.get("activo", False):
        return None
    hash_guardado = (u.get("password_hash") or "").encode()
    if not hash_guardado:
        return None
    try:
        ok = _bcrypt.checkpw(password.encode(), hash_guardado)
    except Exception:
        return None
    if not ok:
        return None
    # Actualizar último acceso
    try:
        from datetime import datetime, timezone
        get_client().table("usuarios").update(
            {"ultimo_acceso": datetime.now(timezone.utc).isoformat()}
        ).eq("id", u["id"]).execute()
    except Exception:
        pass
    return {"usuario": u["usuario"], "nombre": u.get("nombre", ""), "rol": u.get("rol", "")}


def crear_usuario(datos: dict) -> dict:
    """
    Crea un nuevo usuario.
    datos: {usuario, password, nombre, rol}
    """
    import bcrypt as _bcrypt
    hash_ = _bcrypt.hashpw(datos["password"].encode(), _bcrypt.gensalt()).decode()
    payload = {
        "usuario":       datos["usuario"],
        "password_hash": hash_,
        "nombre":        datos.get("nombre", ""),
        "rol":           datos.get("rol", "Recepcionista"),
        "activo":        True,
    }
    result = get_client().table("usuarios").insert(payload).execute()
    return result.data[0]


def actualizar_usuario(usuario_id: str, datos: dict):
    """Actualiza nombre, rol o estado activo de un usuario."""
    get_client().table("usuarios").update(datos).eq("id", usuario_id).execute()


def cambiar_password_usuario(usuario_id: str, nueva_password: str):
    """Cambia la contraseña de un usuario (genera nuevo hash bcrypt)."""
    import bcrypt as _bcrypt
    hash_ = _bcrypt.hashpw(nueva_password.encode(), _bcrypt.gensalt()).decode()
    get_client().table("usuarios").update(
        {"password_hash": hash_}
    ).eq("id", usuario_id).execute()


# ── REPORTES ESPECÍFICOS ──────────────────────────────────────────────────

def obtener_datos_reporte_presupuestos(filtros: dict | None = None) -> list[dict]:
    """
    Devuelve tratamientos con saldo calculado (costo − pagos realizados).
    filtros: {especialista_id, paciente_id, saldo_minimo}
    Cada registro incluye: pacientes, especialistas, pagado, saldo.
    """
    filtros = filtros or {}
    q = get_client().table("tratamientos").select(
        "*, pacientes(id, nombre, apellido, dni, obra_social, telefono),"
        "   especialistas(nombre, apellido)"
    )
    if filtros.get("especialista_id"):
        q = q.eq("especialista_id", filtros["especialista_id"])
    if filtros.get("paciente_id"):
        q = q.eq("paciente_id", filtros["paciente_id"])
    tratamientos = q.order("fecha", desc=True).execute().data or []

    saldo_min = float(filtros.get("saldo_minimo") or 0)
    result = []
    for t in tratamientos:
        pagos_t = (
            get_client().table("pagos").select("monto")
            .eq("tratamiento_id", t["id"]).execute().data or []
        )
        pagado = sum(float(p.get("monto", 0)) for p in pagos_t)
        costo  = float(t.get("costo", 0))
        saldo  = costo - pagado
        if saldo >= saldo_min:
            result.append({**t, "pagado": pagado, "saldo": saldo})
    return result


def obtener_datos_citas(especialista_id: str | None = None,
                        periodo: str = "semana") -> list[dict]:
    """
    Citas del especialista para el período indicado a partir de hoy.
    periodo: 'semana' (7d) | 'quincena' (15d) | 'mes' (30d)
    """
    from datetime import date, timedelta
    hoy   = date.today()
    dias  = {"semana": 7, "quincena": 15, "mes": 30}.get(periodo, 7)
    hasta = hoy + timedelta(days=dias)
    q     = get_client().table("citas").select(
        "*, pacientes(nombre, apellido, telefono, email),"
        "   especialistas(nombre, apellido)"
    )
    q = q.gte("fecha_hora", f"{hoy.isoformat()}T00:00:00")
    q = q.lte("fecha_hora", f"{hasta.isoformat()}T23:59:59")
    if especialista_id:
        q = q.eq("especialista_id", especialista_id)
    return q.order("fecha_hora").execute().data or []


# ── REPORTES ──────────────────────────────────────────────────────────────

def listar_citas_rango(fecha_desde: str | None = None,
                       fecha_hasta: str | None = None,
                       especialista_id: str | None = None) -> list[dict]:
    """Devuelve todas las citas en un rango de fechas (formato ISO: YYYY-MM-DD)."""
    q = get_client().table("citas").select(
        "*, pacientes(nombre, apellido), especialistas(nombre, apellido)"
    )
    if fecha_desde:
        q = q.gte("fecha_hora", f"{fecha_desde}T00:00:00")
    if fecha_hasta:
        q = q.lte("fecha_hora", f"{fecha_hasta}T23:59:59")
    if especialista_id:
        q = q.eq("especialista_id", especialista_id)
    return q.order("fecha_hora", desc=True).execute().data


def listar_pagos_todos(fecha_desde: str | None = None,
                       fecha_hasta: str | None = None,
                       metodo: str | None = None) -> list[dict]:
    """Devuelve todos los pagos de todos los pacientes en el rango de fechas."""
    q = get_client().table("pagos").select(
        "*, pacientes(nombre, apellido), tratamientos(descripcion)"
    )
    if fecha_desde:
        q = q.gte("fecha", f"{fecha_desde}T00:00:00")
    if fecha_hasta:
        q = q.lte("fecha", f"{fecha_hasta}T23:59:59")
    if metodo:
        q = q.eq("metodo", metodo)
    return q.order("fecha", desc=True).execute().data


def listar_tratamientos_todos(estado: str | None = None) -> list[dict]:
    """Devuelve todos los tratamientos de todos los pacientes."""
    q = get_client().table("tratamientos").select(
        "*, pacientes(nombre, apellido), especialistas(nombre, apellido)"
    )
    if estado:
        q = q.eq("estado", estado)
    return q.order("fecha", desc=True).execute().data


def stats_resumen() -> dict:
    """
    Calcula estadísticas de resumen para el dashboard.
    Devuelve un dict con conteos y totales del mes actual.
    """
    from datetime import datetime, date
    hoy    = date.today()
    inicio = hoy.replace(day=1).isoformat()
    fin    = hoy.isoformat()

    c = get_client()

    pacientes   = c.table("pacientes").select("id", count="exact").execute()
    citas_mes   = c.table("citas").select("id,estado", count="exact").gte(
        "fecha_hora", f"{inicio}T00:00:00"
    ).lte("fecha_hora", f"{fin}T23:59:59").execute()
    pagos_mes   = c.table("pagos").select("monto").gte(
        "fecha", f"{inicio}T00:00:00"
    ).lte("fecha", f"{fin}T23:59:59").execute()
    trat_pend   = c.table("tratamientos").select("id", count="exact").in_(
        "estado", ["presupuestado", "aprobado"]
    ).execute()
    citas_hoy   = c.table("citas").select("id,estado", count="exact").gte(
        "fecha_hora", f"{hoy.isoformat()}T00:00:00"
    ).lte("fecha_hora", f"{hoy.isoformat()}T23:59:59").execute()

    citas_data  = citas_mes.data or []
    estados     = {}
    for cita in citas_data:
        est = cita.get("estado", "pendiente")
        estados[est] = estados.get(est, 0) + 1

    ingresos_mes = sum(float(p.get("monto", 0)) for p in (pagos_mes.data or []))

    return {
        "total_pacientes":   pacientes.count or 0,
        "citas_hoy":         len(citas_hoy.data or []),
        "citas_mes":         len(citas_data),
        "citas_realizadas":  estados.get("realizada", 0),
        "citas_canceladas":  estados.get("cancelada", 0),
        "citas_pendientes":  estados.get("pendiente", 0) + estados.get("confirmada", 0),
        "ingresos_mes":      ingresos_mes,
        "tratamientos_pend": trat_pend.count or 0,
        "mes_nombre":        datetime.today().strftime("%B %Y"),
    }


# ── SALDO ─────────────────────────────────────────────────────────────────

def saldo_pendiente(paciente_id: str) -> float:
    tratamientos = listar_tratamientos(paciente_id)
    pagos = listar_pagos(paciente_id)
    total_tratamientos = sum(float(t.get("costo", 0)) for t in tratamientos)
    total_pagado = sum(float(p.get("monto", 0)) for p in pagos)
    return total_tratamientos - total_pagado
