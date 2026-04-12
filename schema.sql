-- ============================================================
-- ESQUEMA SUPABASE — Consultorio Odontológico
-- Ejecutar completo en: Supabase → SQL Editor → New query
-- ============================================================

-- ── PACIENTES ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pacientes (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre        TEXT NOT NULL,
    apellido      TEXT NOT NULL,
    fecha_nac     DATE,
    dni           TEXT UNIQUE,
    telefono      TEXT,
    email         TEXT,
    direccion     TEXT,
    obra_social   TEXT,
    nro_afiliado  TEXT,
    grupo_sangre  TEXT,
    alergias      TEXT,
    antecedentes  JSONB,
    creado_en     TIMESTAMPTZ DEFAULT now()
);

-- ── CONSTANTES VITALES ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS constantes_vitales (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paciente_id   UUID REFERENCES pacientes(id) ON DELETE CASCADE,
    fecha         TIMESTAMPTZ DEFAULT now(),
    presion_sys   INTEGER,
    presion_dia   INTEGER,
    pulso         INTEGER,
    peso_kg       NUMERIC(5,2),
    altura_cm     NUMERIC(5,1),
    imc           NUMERIC(5,2)
);

-- ── ODONTOGRAMA ───────────────────────────────────────────────
-- Guarda el estado de las 5 caras de cada diente en formato JSON.
-- Estados: sano | caries | obturado | fractura | extraccion | corona | implante | ausente
-- UNIQUE(paciente_id, diente) permite usar upsert para actualizar sin duplicar.
CREATE TABLE IF NOT EXISTS odontograma (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paciente_id   UUID REFERENCES pacientes(id) ON DELETE CASCADE,
    fecha         TIMESTAMPTZ DEFAULT now(),
    diente        INTEGER NOT NULL,
    caras         JSONB NOT NULL DEFAULT '{
                      "oclusal":    "sano",
                      "vestibular": "sano",
                      "lingual":    "sano",
                      "mesial":     "sano",
                      "distal":     "sano"
                  }',
    observacion   TEXT,
    UNIQUE (paciente_id, diente)
);

-- ── ESPECIALISTAS ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS especialistas (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre          TEXT NOT NULL,
    apellido        TEXT NOT NULL,
    matricula       TEXT UNIQUE,
    especialidades  JSONB,
    telefono        TEXT,
    email           TEXT,
    activo          BOOLEAN DEFAULT true
);

-- ── DISPONIBILIDAD ────────────────────────────────────────────
-- certeza: 'confirmado' (🟢) | 'probable' (🟡) | 'por_confirmar' (⚪)
CREATE TABLE IF NOT EXISTS disponibilidad (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    especialista_id UUID REFERENCES especialistas(id) ON DELETE CASCADE,
    dia_semana      SMALLINT CHECK (dia_semana BETWEEN 0 AND 6),
    hora_inicio     TIME NOT NULL,
    hora_fin        TIME NOT NULL,
    certeza         TEXT NOT NULL DEFAULT 'por_confirmar'
                    CHECK (certeza IN ('confirmado', 'probable', 'por_confirmar'))
);

-- ── CITAS ─────────────────────────────────────────────────────
-- estado: 'pendiente' | 'confirmada' | 'realizada' | 'cancelada'
CREATE TABLE IF NOT EXISTS citas (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paciente_id     UUID REFERENCES pacientes(id) ON DELETE CASCADE,
    especialista_id UUID REFERENCES especialistas(id) ON DELETE SET NULL,
    fecha_hora      TIMESTAMPTZ NOT NULL,
    duracion_min    INTEGER DEFAULT 30,
    motivo          TEXT,
    estado          TEXT NOT NULL DEFAULT 'pendiente'
                    CHECK (estado IN ('pendiente','confirmada','realizada','cancelada')),
    notas           TEXT,
    creado_en       TIMESTAMPTZ DEFAULT now()
);

-- ── TRATAMIENTOS ──────────────────────────────────────────────
-- estado: 'presupuestado' | 'aprobado' | 'realizado'
CREATE TABLE IF NOT EXISTS tratamientos (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paciente_id     UUID REFERENCES pacientes(id) ON DELETE CASCADE,
    especialista_id UUID REFERENCES especialistas(id) ON DELETE SET NULL,
    fecha           TIMESTAMPTZ DEFAULT now(),
    diente          INTEGER,
    cara            TEXT,
    descripcion     TEXT NOT NULL,
    costo           NUMERIC(10,2) NOT NULL DEFAULT 0,
    estado          TEXT NOT NULL DEFAULT 'presupuestado'
                    CHECK (estado IN ('presupuestado','aprobado','realizado'))
);

-- ── PAGOS ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pagos (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paciente_id     UUID REFERENCES pacientes(id) ON DELETE CASCADE,
    tratamiento_id  UUID REFERENCES tratamientos(id) ON DELETE SET NULL,
    fecha           TIMESTAMPTZ DEFAULT now(),
    monto           NUMERIC(10,2) NOT NULL,
    metodo          TEXT,
    comprobante     TEXT,
    notas           TEXT
);

-- ── ÍNDICES de rendimiento ────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_odontograma_paciente  ON odontograma(paciente_id);
CREATE INDEX IF NOT EXISTS idx_constantes_paciente   ON constantes_vitales(paciente_id);
CREATE INDEX IF NOT EXISTS idx_disponibilidad_esp    ON disponibilidad(especialista_id);
CREATE INDEX IF NOT EXISTS idx_citas_paciente        ON citas(paciente_id);
CREATE INDEX IF NOT EXISTS idx_citas_especialista    ON citas(especialista_id);
CREATE INDEX IF NOT EXISTS idx_citas_fecha          ON citas(fecha_hora);
CREATE INDEX IF NOT EXISTS idx_tratamientos_paciente ON tratamientos(paciente_id);
CREATE INDEX IF NOT EXISTS idx_pagos_paciente        ON pagos(paciente_id);

-- ── Row Level Security (recomendado activar luego) ────────────
-- ALTER TABLE pacientes ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE odontograma ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE citas ENABLE ROW LEVEL SECURITY;
-- (Agregar políticas según roles de usuario cuando se implemente auth)
