# nutri-analytics

App personal (PWA) de planificación de menús, recetas y seguimiento de salud/deporte. Construida con **Python + Streamlit + Supabase (PostgreSQL)**, con exportadores de contexto (Markdown/CSV) para usar con LLMs.

## Descripción

nutri-analytics es una aplicación web progresiva diseñada para gestionar de forma integral tu alimentación, actividad física y métricas de salud. Permite planificar menús semanales, mantener un catálogo de recetas personalizado, registrar métricas de salud (peso, composición corporal) y seguimiento de entrenamientos, con capacidad de exportar contextos limpios en formatos estándar (Markdown, CSV, XLSX) para análisis con modelos de lenguaje.

## Stack Tecnológico

- **Frontend & UI:** [Streamlit](https://streamlit.io/) — interfaz web moderna optimizada para móvil (PWA)
- **Backend:** [Supabase](https://supabase.com/) — PostgreSQL en la nube con cliente Python nativo
- **Procesamiento de Datos:** [Pandas](https://pandas.pydata.org/) — manipulación y transformación de dataframes
- **Visualización:** [Plotly](https://plotly.com/) — gráficos interactivos
- **Gestión de Configuración:** [python-dotenv](https://github.com/theskumar/python-dotenv) — variables de entorno

## Estructura del Proyecto

```
nutri-analytics/
├── README.md                    # Este archivo
├── LICENSE                      # Licencia del proyecto
├── pyproject.toml               # Configuración de proyecto y dependencias (uv)
├── uv.lock                      # Archivo de bloqueo de dependencias
├── .env.example                 # Plantilla de variables de entorno
├── .env                         # Configuración (no commiteado)
├── .venv/                       # Entorno virtual Python (generado por uv)
├── docs/
│   ├── plan_app_personal.md    # Especificación de diseño y arquitectura
│   └── decisiones.md            # Registro de decisiones de diseño
├── db/
│   └── 001_esquema_inicial.sql # Migración SQL del esquema de Supabase
├── tests/                       # Tests unitarios y de integración (pytest)
├── paginas/                     # Páginas de la UI (módulos Streamlit)
├── app.py                       # Interfaz Streamlit
├── database.py                  # Operaciones CRUD con Supabase
├── exporter.py                  # Exportadores de contexto Markdown/CSV
└── filtros.py                   # Sistema de filtros de recetas (lógica pura)
```

Ver [docs/plan_app_personal.md](docs/plan_app_personal.md) para la especificación completa de arquitectura, modelo de datos (tablas SQL) y hoja de ruta de desarrollo. Consulta también [docs/decisiones.md](docs/decisiones.md) para el registro de decisiones de diseño.

## Puesta en Marcha

### 1. Clonar el repositorio
```bash
git clone <repo-url>
cd nutri-analytics
```

### 2. Instalar uv (si no lo tienes)
Instala el gestor de dependencias `uv` desde [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/).

### 3. Sincronizar dependencias
```bash
uv sync
```

Esto crea el entorno virtual y instala todas las dependencias definidas en `pyproject.toml`.

### 4. Configurar variables de entorno
Copia `.env.example` a `.env` en la raíz del proyecto y rellena las credenciales de Supabase:

```bash
cp .env.example .env
```

Edita `.env` con tus valores:
```env
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_SECRET_KEY=sb_secret_...
```

**Importante:** No commitearlo. El archivo `.env` está en `.gitignore`.

### 5. Ejecutar la aplicación
```bash
uv run streamlit run app.py
```

La app estará disponible en `http://localhost:8501`.

#### Acceso desde el móvil en red local (opcional)
Si aún no has desplegado la app en la nube, puedes probarla desde el móvil dentro de tu WiFi:
1. Ejecutar Streamlit en tu red: `uv run streamlit run app.py --server.address 0.0.0.0`
2. Acceder desde Chrome en Android: `http://[tu-ip-local]:8501`
3. Menú de Chrome → "Añadir a pantalla de inicio" para tenerla como acceso directo.

## Tests

### Tests unitarios
```bash
uv run pytest
```

Ejecuta todos los tests unitarios (sin tocar base de datos ni red). Cubre la lógica pura de los módulos raíz (`filtros.py`, `exporter.py`, helpers de `paginas/comun.py`...).

### Tests de integración
```bash
uv run pytest -m integration
```

Ejecuta solo los tests de integración contra Supabase (requieren `.env` configurado con credenciales válidas). Utilizan datos con prefijo `[TEST]` y limpian automáticamente todo lo que crean.

## Despliegue en Streamlit Community Cloud

Siguiendo el modelo de distribución de la decisión [D7](docs/decisiones.md#d7--hosting-streamlit-community-cloud-con-app-privada-y-repo-público): la app es **auto-desplegable**, cada persona despliega su propia instancia con su propio proyecto de Supabase. No hay una instancia compartida ni datos que se crucen entre usuarios.

### Requisitos

- Una cuenta de GitHub con el repositorio (fork o clon propio).
- Un proyecto propio de Supabase con la migración [`db/001_esquema_inicial.sql`](db/001_esquema_inicial.sql) ya ejecutada en su editor SQL.

### Pasos

1. Entra en [share.streamlit.io](https://share.streamlit.io) e inicia sesión con tu cuenta de GitHub.
2. Pulsa **"Create app"** y elige tu repositorio, la rama `main` y el archivo `app.py`.
3. En **"Advanced settings"**, selecciona la versión de Python del proyecto y pega tus secretos en formato TOML (*Tom's Obvious Minimal Language*, el formato de configuración que usa Streamlit):
   ```toml
   SUPABASE_URL = "https://tu-proyecto.supabase.co"
   SUPABASE_SECRET_KEY = "sb_secret_..."
   ```
4. Pulsa **Deploy** y espera a que termine el build.
5. **IMPORTANTE:** si el repositorio es público, la app nace pública. Ve a **Settings → Sharing** y marca **"Only specific people can view this app"**, añadiendo tu email — así tus datos de salud solo los ves tú.
6. En el móvil, abre la URL de tu app en Chrome y usa el menú → **"Añadir a pantalla de inicio"** para tenerla como una app nativa.

### Nota

La app gratuita "se duerme" tras unos días sin uso y se despierta con un solo click al volver a abrirla. Tus datos están siempre a salvo en Supabase, independientemente de si la app o el proyecto de Supabase están dormidos.

## Servidor MCP (usar la app desde un agente de IA)

La lógica de negocio de nutri-analytics se expone como un servidor [MCP](https://modelcontextprotocol.io/) (*Model Context Protocol*, estándar abierto para conectar herramientas a LLMs) que permite a agentes de IA como Claude automatizar tareas complejas directamente sobre tus datos. Ejemplo: *"Planifícame la semana con mis recetas habituales y hazme la lista de la compra"* — el agente lee tu catálogo, consulta tu menú y escribe los ítems de compra en la base de datos sin pasar por la interfaz Streamlit.

### Características

- **Local-first**: el servidor corre en tu máquina con `uv run python mcp_server.py`; tus credenciales de Supabase viven en `.env` y nunca salen de ahí.
- **13 tools disponibles** para consultar, crear y actualizar:

| Tool | Descripción |
|------|-------------|
| `fecha_actual` | Fecha de hoy y límites de la semana actual/siguiente (para resolver fechas relativas como "la semana que viene") |
| `listar_recetas` | Consultar el catálogo de recetas con filtros opcionales (macros, ingredientes, etc.) |
| `crear_receta` | Crear una nueva receta con macros y ingredientes |
| `consultar_menu` | Ver el menú semanal de un rango de fechas |
| `planificar_comida` | Asignar una receta a una comida (desayuno/almuerzo/cena) en una fecha |
| `consultar_lista_compra` | Ver la lista de la compra actual con estado de ítems |
| `agregar_item_compra` | Añadir un ítem a la lista de la compra |
| `marcar_item_comprado` | Marcar un ítem como comprado |
| `registrar_metricas` | Registrar peso, composición corporal y otras métricas de salud |
| `historico_salud` | Consultar el histórico de métricas de salud |
| `registrar_actividad` | Registrar una actividad deportiva (tipo, duración, calorías) |
| `historico_deporte` | Consultar el histórico de actividades registradas |
| `exportar_contexto` | Exportar datos (recetas, menú, métricas) en formato Markdown para análisis con LLMs |

**Nota sobre seguridad:** no se exponen tools de borrado (`eliminar_receta`, `eliminar_comida`, etc.). El agente puede consultar, crear y actualizar, pero los borrados son siempre explícitos desde la app.

### Configuración en un cliente MCP

Para registrar el servidor en un cliente MCP local (ej. [Claude Desktop](https://claude.ai/download) o [Claude Code](https://github.com/anthropics/claude-code)):

1. Abre el archivo de configuración MCP de tu cliente (`~/.claude/claude_desktop_config.json` en Desktop, o `.claude/settings.json` en Code).
2. Añade la entrada del servidor nutri-analytics:

```json
{
  "mcpServers": {
    "nutri-analytics": {
      "command": "uv",
      "args": ["run", "--directory", "C:/ruta/a/nutri-analytics", "python", "mcp_server.py"]
    }
  }
}
```

Reemplaza `C:/ruta/a/nutri-analytics` con la ruta completa a tu clon del repositorio.

3. Reinicia el cliente; el servidor aparecerá en la lista de herramientas disponibles.

## Privacidad y Datos Sensibles

Los datos de salud personales exportados se mantienen fuera del repositorio:

- Carpeta `data/` — archivos CSV/XLSX generados localmente
- Carpeta `exports/` — contextos exportados para LLMs
- Archivos `.md` generados en tiempo de ejecución

Todas estas rutas están excluidas en `.gitignore`. El repositorio contiene únicamente código, especificación y configuración (sin credenciales ni datos personales).

## Especificación Completa

Consulta [docs/plan_app_personal.md](docs/plan_app_personal.md) para:
- Arquitectura del sistema y flujo de datos
- Modelo de datos SQL (esquema relacional)
- Estrategia de exportación para IA
- Diseño de interfaz de usuario
- Hoja de ruta de desarrollo con Claude Code
