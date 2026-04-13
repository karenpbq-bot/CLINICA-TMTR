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


# ── SALDO ─────────────────────────────────────────────────────────────────

def saldo_pendiente(paciente_id: str) -> float:
    tratamientos = listar_tratamientos(paciente_id)
    pagos = listar_pagos(paciente_id)
    total_tratamientos = sum(float(t.get("costo", 0)) for t in tratamientos)
    total_pagado = sum(float(p.get("monto", 0)) for p in pagos)
    return total_tratamientos - total_pagado
