# Anexo: Decisiones de diseño validadas

Registro de decisiones acordadas tras el análisis crítico del plan original ([plan_app_personal.md](plan_app_personal.md)). Ante cualquier contradicción entre ambos documentos, **prevalece este anexo**.

## D1 — Seguridad: RLS activado desde el inicio

RLS (*Row Level Security*, seguridad a nivel de fila de PostgreSQL) se activa en las 5 tablas desde la primera migración, sin políticas para la clave anónima (lo que la deja inservible). La app usa la **Secret key** (`sb_secret_...`, sucesora de la legacy service_role), que ignora RLS y solo vive en el `.env` local o en el gestor de secretos del hosting, nunca en el repositorio.

Nota: Supabase sustituyó en 2025 las claves legacy (anon / service_role) por Publishable key (`sb_publishable_...`, sujeta a RLS) y Secret key (`sb_secret_...`). Este proyecto usa exclusivamente la Secret key; las legacy quedan sin uso y pueden deshabilitarse.

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

## D9 — Diseño "agent-ready": lógica de negocio independiente de la UI

Toda la lógica de negocio (acceso a datos en `database.py`, exportación en `exporter.py`, filtrado de recetas en `filtros.py`) se implementa como funciones Python puras, tipadas, sin ninguna dependencia de Streamlit y con validaciones que lanzan errores claros en español. La UI de Streamlit es solo una capa fina que llama a esas funciones.

Motivo: permitir que en el futuro un agente de IA ejecute estas mismas operaciones (crear recetas, planificar menús, filtrar, exportar) como *tools* — vía API de LLM o como servidor MCP (*Model Context Protocol*) — sin reescribir nada. Los filtros de recetas, por ejemplo, se representan como datos (`{"campo": "calorias", "operador": "<", "valor": 1000}`): la UI los construye con widgets y un agente podría construirlos como JSON, consumiendo ambos la misma función `aplicar_filtros`.

Regla para el futuro: cualquier funcionalidad nueva separa lógica (módulo puro en la raíz) de presentación (`paginas/`).

## D10 — Política de tests

Cada nueva funcionalidad incluye **tests unitarios** en el módulo `tests/` (pytest, `uv run pytest`), centrados en la lógica pura de los módulos raíz (`filtros.py`, `exporter.py`, helpers de `paginas/comun.py`...). Las operaciones contra Supabase se cubren con **tests de integración** marcados con `@pytest.mark.integration` (`uv run pytest -m integration`): usan datos con prefijo `[TEST]`, requieren un `.env` válido y limpian todo lo que crean. Los tests unitarios no tocan red ni base de datos.

La lógica de `database.py` se cubre con tests unitarios que **simulan (mockean) el cliente de Supabase** con `unittest.mock`: verifican la construcción de payloads, los parámetros de las consultas (p. ej. `on_conflict`) y las validaciones locales, sin tocar la red y sin requerir `.env`. Los tests de integración quedan como suite complementaria opcional: detectan desviaciones reales de esquema o API que un mock no puede capturar.

Motivo: hasta ahora la verificación se hacía con scripts temporales fuera del repositorio, que se perdían tras cada validación. Un módulo `tests/` versionado convierte esas comprobaciones en una red de seguridad permanente contra regresiones.

A futuro: tests end-to-end de la app completa.

## D11 — Servidor MCP local (V1)

La lógica de la app se expone a agentes de IA mediante un servidor MCP (*Model Context Protocol*, el estándar abierto para conectar herramientas a LLMs) local por stdio: `mcp_server.py`, construido con el SDK oficial de Python (FastMCP). Materializa la decisión D9: el servidor es una capa fina (~un archivo) que registra como tools las funciones de `database.py`, `filtros.py` y `exporter.py`, sin duplicar lógica.

Decisiones de alcance (V1):

- **Local-first**: corre en la máquina del usuario con `uv run python mcp_server.py`; la Secret key de Supabase nunca sale del `.env` local. Un servidor MCP remoto (para claude.ai/móvil) queda como posible V2, con autenticación propia.
- **Lectura + escritura, sin borrados**: se exponen 12 tools que permiten consultar y crear recetas con filtros, planificar comidas, gestionar la lista de la compra, registrar métricas de salud y actividades, e exportar contexto como texto. Las tools de borrado (`eliminar_receta`, `eliminar_comida`, `eliminar_item`, `vaciar_comprados`, `eliminar_actividad`) quedan fuera deliberadamente: el agente propone cambios, pero los borrados siguen siendo acción explícita del usuario desde la app.
- Los tests unitarios mockean el cliente de Supabase (norma D10), reutilizando el patrón de `tests/test_database.py` para no tocar red ni requerir credenciales.
