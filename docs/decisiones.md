# Anexo: Decisiones de diseño validadas

Registro de decisiones acordadas tras el análisis crítico del plan original ([plan_app_personal.md](plan_app_personal.md)). Ante cualquier contradicción entre ambos documentos, **prevalece este anexo**.

## D1 — Seguridad: RLS activado desde el inicio

RLS (*Row Level Security*, seguridad a nivel de fila de PostgreSQL) se activa en las 5 tablas desde la primera migración, sin políticas para la clave anónima (lo que la deja inservible). La app usa la **service_role key**, que solo vive en el `.env` local o en el gestor de secretos del hosting, nunca en el repositorio.

## D2 — Menús: una sola columna de fecha

`menus_semanales` sustituye `fecha_inicio` + `dia_semana` (texto) por una única columna `fecha date not null`, con `unique(fecha, tipo_comida)`. El día de la semana y el lunes de la semana se derivan con funciones de fecha (SQL o Pandas). Motivo: elimina redundancia inconsistente y el problema de ordenación de días como texto.

## D3 — Recetas: macros como columnas planas

Se sustituye `macros_estimados jsonb` por columnas `calorias int`, `proteinas int`, `carbohidratos int`, `grasas int`. Motivo: la UI requiere filtros por macros y los exports incluyen calorías; columnas planas dan filtros, agregaciones y validación de tipos directos.

## D4 — Esquema versionado en el repositorio

Carpeta `db/` con migraciones SQL numeradas (`001_esquema_inicial.sql`, `002_...`). Se ejecutan manualmente en el editor SQL de Supabase, pero el fichero fuente vive en git.

## D5 — Detalles menores del esquema

- `metricas_salud.fecha` pasa a `date` con `unique(fecha)` (un registro por día); `altura` se mantiene como columna opcional.
- Limitación aceptada: una receta por comida (`unique(fecha, tipo_comida)`); las guarniciones se apuntan en `nota_adicional`.
- `ingredientes` se mantiene como `text[]` en v1; la consolidación de la lista de la compra la hace el LLM. Si en el futuro la app debe generarla automáticamente, se migrará a estructura `{item, cantidad, unidad}`.

## D6 — Persistencia: se confirma Supabase (vs. SQLite)

Al desplegarse la app en la nube (D7), una base de datos local tipo SQLite queda descartada: se necesita una base de datos accesible desde el hosting. Supabase se confirma como elección.

Riesgo conocido: el plan gratuito de Supabase pausa proyectos tras ~1 semana de inactividad; la restauración es manual (un click en el dashboard). Mitigación: uso semanal real + los CSVs del módulo exportador actúan como backup local periódico.

## D7 — Hosting: Streamlit Community Cloud con app privada y repo público

Requisitos del usuario: desarrollar en el portátil y usar la app desde el móvil **sin depender de que el portátil esté encendido**; el repositorio debe ser **público** (portfolio) manteniendo los datos de salud **totalmente privados** y sin cruce con datos de terceros.

Decisión: **Streamlit Community Cloud** (gratuito) desplegando desde el repositorio público de GitHub, con la app configurada como **privada** (solo accesible para el email del usuario, con inicio de sesión). La visibilidad de la app es independiente de la del repo. Las credenciales de Supabase van en el gestor de secretos de la plataforma, nunca en el repositorio.

Modelo de distribución: app **auto-desplegable** (self-hosted por usuario). Cada tercero que quiera usarla crea su propio proyecto de Supabase, ejecuta la migración de `db/` y despliega su propia instancia con sus propios secretos. Instancias 100% aisladas: el cruce de datos entre usuarios es imposible por diseño.

Consecuencias:
- El flujo de trabajo pasa a ser *push a GitHub → redespliegue automático → abrir URL en el móvil* (añadida a pantalla de inicio).
- El README debe incluir instrucciones de auto-despliegue para terceros.
- Licencia **MIT** (confirmada por el usuario).
- Con repo público, la higiene de secretos es crítica: nada sensible puede tocar el historial de git.

## D8 — Hoja de ruta: ajustes

- Se añade un **Paso 0**: estructura de carpetas, `requirements.txt` y `.env.example`.
- La navegación multipágina de la UI usará `st.navigation` / `st.Page` (API moderna de Streamlit) en lugar de `st.tabs`.
