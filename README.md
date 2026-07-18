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

#### Instalar como PWA en Android
1. Ejecutar Streamlit en tu red: `uv run streamlit run app.py --server.address 0.0.0.0`
2. Acceder desde Chrome en Android: `http://[tu-ip-local]:8501`
3. Menú de Chrome → "Instalar aplicación" para añadirla a la pantalla de inicio como app nativa.

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
