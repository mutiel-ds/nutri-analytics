-- =============================================================================
-- 001_esquema_inicial.sql
--
-- Esquema inicial de la base de datos para la app personal de menús,
-- recetas y salud (Streamlit + Supabase/PostgreSQL).
--
-- Este fichero es una migración manual: no se ejecuta automáticamente.
-- Debe copiarse y ejecutarse a mano en el editor SQL de Supabase
-- (Dashboard del proyecto -> SQL Editor -> New query -> Run).
--
-- Esquema corregido según docs/decisiones.md (D1, D2, D3, D5):
--   - D1: RLS activado sin políticas (ver sección final).
--   - D2: menus_semanales usa una única columna "fecha" (no fecha_inicio/dia_semana).
--   - D3: macros de recetas como columnas planas (no jsonb).
--   - D5: metricas_salud usa "fecha" tipo date, un registro por día.
--
-- No se usa la extensión "uuid-ossp": se emplea gen_random_uuid(),
-- nativa en PostgreSQL 13+ (la versión que usa Supabase).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. tabla de recetas
-- -----------------------------------------------------------------------------
create table public.recetas (
    id uuid primary key default gen_random_uuid(),
    titulo text not null,
    descripcion text,
    ingredientes text[] not null, -- array de texto para fácil procesamiento
    instrucciones text,
    categoria text, -- e.g., 'Almuerzo', 'Desayuno', 'Snack'
    tiempo_preparacion int, -- en minutos
    -- macros como columnas planas (decisión D3, sustituye a macros_estimados jsonb)
    calorias int,
    proteinas int,
    carbohidratos int,
    grasas int,
    created_at timestamptz not null default now()
);

-- -----------------------------------------------------------------------------
-- 2. tabla de menús semanales
-- -----------------------------------------------------------------------------
create table public.menus_semanales (
    id uuid primary key default gen_random_uuid(),
    -- columna única de fecha (decisión D2, sustituye a fecha_inicio + dia_semana);
    -- el día de la semana se deriva con funciones de fecha en SQL o Pandas
    fecha date not null,
    tipo_comida text not null check (tipo_comida in ('Desayuno', 'Almuerzo', 'Merienda', 'Cena')),
    receta_id uuid references public.recetas(id) on delete set null,
    nota_adicional text, -- para variaciones rápidas sin cambiar la receta
    unique (fecha, tipo_comida)
);

-- -----------------------------------------------------------------------------
-- 3. tabla de lista de la compra
-- -----------------------------------------------------------------------------
create table public.lista_compra (
    id uuid primary key default gen_random_uuid(),
    item text not null,
    cantidad text,
    categoria text, -- 'Verduras', 'Carnes', etc.
    comprado boolean default false,
    fecha_adicion date default current_date
);

-- -----------------------------------------------------------------------------
-- 4. tabla de métricas de salud
-- -----------------------------------------------------------------------------
create table public.metricas_salud (
    id uuid primary key default gen_random_uuid(),
    -- fecha tipo date con unique (decisión D5): un único registro por día
    fecha date not null default current_date unique,
    peso numeric(5,2), -- en kg
    altura numeric(3,2), -- en metros (columna opcional)
    porcentaje_grasa numeric(4,2),
    perimetro_cintura numeric(5,2),
    notas text
);

-- -----------------------------------------------------------------------------
-- 5. tabla de actividad deportiva
-- -----------------------------------------------------------------------------
create table public.actividad_deporte (
    id uuid primary key default gen_random_uuid(),
    fecha timestamptz not null default now(),
    tipo_actividad text not null, -- 'Fuerza', 'Running', 'Ciclismo', etc.
    duracion_minutos int not null,
    intensidad text check (intensidad in ('Alta', 'Media', 'Baja')),
    volumen_total_kg numeric, -- útil para entrenamientos de fuerza
    comentarios text
);

-- =============================================================================
-- 6. row level security (decisión D1)
--
-- Se activa RLS en las 5 tablas pero, deliberadamente, no se crea ninguna
-- política. Esto deja a la clave anónima (anon key) sin ningún acceso de
-- lectura ni escritura: cualquier consulta con esa clave será rechazada.
--
-- La app se conecta con la Secret key (sb_secret_..., sucesora de la legacy service_role)
-- (solo en .env local o en el gestor de secretos del hosting, nunca en el repositorio),
-- la cual ignora RLS por completo y tiene acceso total a las tablas.
-- =============================================================================
alter table public.recetas enable row level security;
alter table public.menus_semanales enable row level security;
alter table public.lista_compra enable row level security;
alter table public.metricas_salud enable row level security;
alter table public.actividad_deporte enable row level security;
