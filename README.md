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
├── docs/
│   └── plan_app_personal.md    # Especificación de diseño y arquitectura
├── .env                         # Configuración (no commiteado)
├── .venv/                       # Entorno virtual Python
├── app.py                       # Interfaz Streamlit (planificado)
├── database.py                  # Operaciones CRUD con Supabase (planificado)
├── exporter.py                  # Exportadores de contexto Markdown/CSV (planificado)
└── requirements.txt             # Dependencias Python
```

Ver [docs/plan_app_personal.md](docs/plan_app_personal.md) para la especificación completa de arquitectura, modelo de datos (tablas SQL) y hoja de ruta de desarrollo.

## Puesta en Marcha

### 1. Clonar el repositorio
```bash
git clone <repo-url>
cd nutri-analytics
```

### 2. Crear y activar entorno virtual
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/macOS
python -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

Las dependencias incluyen: `streamlit`, `supabase`, `pandas`, `plotly`, `python-dotenv`.

### 4. Configurar variables de entorno
Crear un archivo `.env` en la raíz del proyecto con las credenciales de Supabase:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anonymous-key
```

**Importante:** No commitearlo. El archivo `.env` está en `.gitignore`.

### 5. Ejecutar la aplicación
```bash
streamlit run app.py
```

La app estará disponible en `http://localhost:8501`.

#### Instalar como PWA en Android
1. Ejecutar Streamlit en tu red: `streamlit run app.py --server.address 0.0.0.0`
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
