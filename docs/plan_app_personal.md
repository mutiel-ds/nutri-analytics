# Especificación de Diseño y Arquitectura: App Personal de Menús, Recetas y Salud

Este documento define la arquitectura, el modelo de datos y la estrategia de desarrollo para construir una aplicación web progresiva (PWA) personal utilizando **Python** como lenguaje principal y **Claude Code** como asistente de desarrollo. El sistema está optimizado para un perfil especializado en Backend y Ciencia de Datos, facilitando la exportación de contextos limpios para Interactuar con Modelos de Lenguaje (LLMs).

---

## 1. Stack Tecnológico Propuesto

Para maximizar tu velocidad de desarrollo utilizando tus fortalezas (Python, SQL, Datos) y minimizar el desarrollo frontend tradicional, se propone el siguiente stack:

*   **Frontend & UI (Móvil):** **Streamlit** o **Flet (Flutter para Python)**.
    *   *Recomendación:* **Streamlit** es excelente para visualización de datos y prototipado rápido. Con layouts modernos, componentes nativos y configurado como PWA (Progressive Web App), se puede añadir a la pantalla de inicio de Android como una app nativa.
*   **Persistencia de Datos:** **Supabase (PostgreSQL)**.
    *   Te ofrece un backend relacional robusto sin mantenimiento, cliente nativo de Python (`supabase-py`), autenticación sencilla si la requieres en el futuro y la posibilidad de ejecutar queries SQL directas o analítica avanzada.
*   **Procesamiento de Datos y Exportación:** **Pandas** y **Archivos Planos**.
    *   Manipulación de dataframes para generar los CSVs de salud/menús y plantillas Markdown formateadas para los LLMs.
*   **Entorno de Desarrollo:** **Claude Code CLI**.
    *   Utilizado para la generación de la estructura de ficheros, lógica de negocio en Python y scripts de migración de base de datos.

---

## 2. Arquitectura del Sistema y Flujo de Datos

El diseño es modular y desacoplado, permitiendo una transición sencilla desde exportaciones manuales de archivos hacia llamadas directas de API (OpenAI/Anthropic/LiteLLM) en el futuro.

```
+-------------------------------------------------------------+
|                      DISPOSITIVO MÓVIL                      |
|  +-------------------------------------------------------+  |
|  |             Streamlit UI (Modo PWA)                   |  |
|  |  [Planificador]  [Recetario]  [Progreso]  [Dashboard] |  |
|  +-------------------------------------------------------+  |
+------------------------------+------------------------------+
                               |
                        Cliente Python (Supabase API)
                               |
                               v
+-------------------------------------------------------------+
|                      CAPA DE DATOS                          |
|  +-------------------------------------------------------+  |
|  |           Supabase Cloud (PostgreSQL)                 |  |
|  |  - Tablas: recetas, menus, compras, metricas, deporte   |  |
|  +-------------------------------------------------------+  |
+------------------------------+------------------------------+
                               |
                 Exportadores Integrados en Python
                               |
                               v
+-------------------------------------------------------------+
|                 INTERFAZ DE CONTEXTO (LLM)                  |
|  - Recetas -> Ficheros .md (Markdown estructurado)         |
|  - Menús y Salud -> Ficheros .csv / .xlsx (Dataframes)      |
+-------------------------------------------------------------+
```

---

## 3. Modelo de Datos (Esquema SQL para Supabase)

A continuación se detalla el esquema relacional óptimo para tus necesidades. Puedes ejecutar este DDL directamente en el editor SQL de Supabase.

```sql
-- Extensiones útiles
create extension if not exists "uuid-ossp";

-- 1. TABLA DE RECETAS
create table public.recetas (
    id uuid default uuid_generate_v4() primary key,
    titulo text not null,
    descripcion text,
    ingredientes text[] not null, -- Array de texto para fácil procesamiento
    instrucciones text,
    categoria text, -- e.g., 'Almuerzo', 'Desayuno', 'Snack'
    tiempo_preparacion int, -- en minutos
    macros_estimados jsonb, -- {calorias: 600, proteinas: 40, carbohidratos: 60, grasas: 20}
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 2. TABLA DE MENÚS SEMANALES
create table public.menus_semanales (
    id uuid default uuid_generate_v4() primary key,
    fecha_inicio date not null, -- Lunes de la semana correspondiente
    dia_semana text not null, -- 'Lunes', 'Martes', etc.
    tipo_comida text not null, -- 'Desayuno', 'Almuerzo', 'Merienda', 'Cena'
    receta_id uuid references public.recetas(id) on delete set null,
    nota_adicional text, -- Para variaciones rápidas sin cambiar la receta
    unique(fecha_inicio, dia_semana, tipo_comida)
);

-- 3. TABLA DE LISTA DE LA COMPRA
create table public.lista_compra (
    id uuid default uuid_generate_v4() primary key,
    item text not null,
    cantidad text,
    categoria text, -- 'Verduras', 'Carnes', etc.
    comprado boolean default false,
    fecha_adicion date default current_date
);

-- 4. TABLA DE MÉTRICAS DE SALUD
create table public.metricas_salud (
    id uuid default uuid_generate_v4() primary key,
    fecha timestamp with time zone default timezone('utc'::text, now()) not null,
    peso numeric(5,2), -- en kg
    altura numeric(3,2), -- en metros (por si varía o inicializar)
    porcentaje_grasa numeric(4,2),
    perimetro_cintura numeric(5,2),
    notas text
);

-- 5. TABLA DE ACTIVIDAD DEPORTIVA
create table public.actividad_deporte (
    id uuid default uuid_generate_v4() primary key,
    fecha timestamp with time zone default timezone('utc'::text, now()) not null,
    tipo_actividad text not null, -- 'Fuerza', 'Running', 'Ciclismo', etc.
    duracion_minutos int not null,
    intensidad text, -- 'Alta', 'Media', 'Baja'
    volumen_total_kg numeric, -- Útil para entrenamientos de fuerza
    comentarios text
);
```

---

## 4. Estrategia de Exportación para Agentes de IA

Para asegurar que un LLM entienda el contexto a la perfección sin ruido, estructuraremos los módulos de exportación en Python de la siguiente manera:

### A. Módulo de Recetas (Formato Markdown)
El LLM procesa mejor las recetas cuando están en formato declarativo plano. Un script interno agrupará las recetas en un único archivo o cadena Markdown con este formato:

```markdown
# Catálogo de Recetas Disponibles

## [ID: 8a5c2] Pollo con Arroz y Brócoli
* **Categoría:** Almuerzo
* **Tiempo:** 25 min
* **Macros:** 550 kcal | P: 45g | C: 50g | G: 15g
### Ingredientes
- 200g de pechuga de pollo
- 80g de arroz integral
- 150g de brócoli
- 1 cda de aceite de oliva
### Instrucciones
1. Cocer el arroz.
2. Saltear el pollo con el aceite.
3. Cocinar el brócoli al vapor y mezclar todo.
---
```

### B. Módulo de Menús y Lista de Compra (Formato CSV)
Los CSV son idóneos para que el LLM entienda distribuciones tabulares temporales y genere agregaciones para la lista de la compra.
*   **`menus_actuales.csv`**: Columnas `Fecha_Inicio, Dia, Tipo_Comida, Nombre_Receta, Calorias`.
*   **`lista_compra_base.csv`**: Columnas `Item, Cantidad, Categoria, Comprado`.

### C. Módulo de Salud y Deporte (Formato CSV para Series Temporales)
Ideal para que el LLM analice tendencias (por ejemplo, correlación entre volumen de entrenamiento y pérdida de peso).
*   **`historico_salud.csv`**: Columnas `Fecha, Peso, Porcentaje_Grasa, Cintura`.
*   **`historico_deporte.csv`**: Columnas `Fecha, Tipo_Actividad, Duracion, Intensidad`.

---

## 5. Diseño de Interfaz de Usuario (UI/UX Móvil)

Al usar Streamlit, organizaremos la app mediante una barra lateral de navegación optimizada para pantallas táctiles:

1.  **Dashboard Semanal (Vista Principal):**
    *   Muestra el día actual, las comidas planificadas para hoy y un botón rápido para marcar elementos completados.
    *   Botón destacado: *"Exportar Contexto para IA"*. Genera un ZIP o descarga local los archivos procesados.
2.  **Planificador de Menús:**
    *   Matriz interactiva (días vs comidas). Selectores dinámicos cargados desde la tabla de recetas de Supabase.
3.  **Mis Recetas:**
    *   Buscador con filtros por macros o tiempo. Formulario sencillo para añadir nuevas recetas a la base de datos.
4.  **Métricas y Rendimiento:**
    *   Formularios compactos para registrar peso diario/semanal y entrenamientos.
    *   Gráficos dinámicos interactivos (usando `st.line_chart` o Plotly) con tu evolución física.

---

## 6. Hoja de Ruta para Desarrollo con Claude Code

Puedes ejecutar este orden cronológico interactuando con **Claude Code** en tu terminal para crear el proyecto de forma automática:

### Paso 1: Inicialización del Entorno
Pídele a Claude Code:
> *"Crea un entorno virtual de Python, instala `streamlit`, `supabase`, `pandas`, `plotly` y `python-dotenv`. Configura el archivo `.env` para almacenar `SUPABASE_URL` y `SUPABASE_KEY`."*

### Paso 2: Creación del Módulo de Conexión (Backend)
Crea un archivo `database.py`. Pídele a Claude Code:
> *"Escribe un módulo en Python utilizando el cliente oficial de Supabase para realizar las operaciones CRUD básicas de las tablas `recetas`, `menus_semanales` y `metricas_salud`."*

### Paso 3: Módulo de Exportación de Datos (Data Science Focus)
Crea un archivo `exporter.py`. Pídele a Claude Code:
> *"Crea funciones en Python que transformen las tablas de recetas a formato Markdown formateado para prompts, y las métricas de salud y menús a DataFrames de Pandas, listos para exportarse como CSV compactos."*

### Paso 4: Construcción de la UI con Streamlit
Crea `app.py`. Pídele a Claude Code:
> *"Diseña una interfaz multipágina en Streamlit optimizada para móvil, utilizando pestañas (`st.tabs`) o un menú lateral limpio para navegar entre el Dashboard, el Planificador de Menús, el Recetario y el histórico de Salud. Integra los formularios de inserción con el módulo `database.py`."*

### Paso 5: Prompt de Inyección para tu Agente de IA externo
Cuando quieras usar ChatGPT, Claude o DeepSeek para generar tu menú, expórtale los archivos generados y usa este prompt maestro:

> **Prompt de Contexto para tu IA:**
> *"Actúa como mi nutricionista y entrenador personal basado en datos. Te adjunto `recetas.md` (mis recetas disponibles), `menus_actuales.csv` (mi planificación) e `historico_salud.csv` (mi evolución). Sabiendo que mi objetivo actual es [Definir objetivo, ej: perder grasa / ganar fuerza], realiza las siguientes tareas:
> 1. Proponme el menú de la próxima semana utilizando principalmente mis recetas y sugiriendo máximo 2 nuevas (con su formato correspondiente).
> 2. Genera la lista de la compra necesaria consolidada en formato tabla.
> 3. Analiza brevemente mis métricas de salud en relación con mis entrenamientos de la última semana."*

---
### 7. Cómo instalarlo en tu móvil Android sin tiendas
1. Despliega la app localmente en tu red doméstica (`streamlit run app.py --server.address 0.0.0.0`).
2. Entra desde el navegador Chrome de tu Android usando la IP local de tu ordenador (ej: `http://192.168.1.50:8501`).
3. En el menú de opciones de Chrome, pulsa **"Añadir a la pantalla de inicio"** o **"Instalar aplicación"**. Streamlit generará un acceso directo nativo y ocultará la barra del navegador, comportándose como una app personal independiente.
