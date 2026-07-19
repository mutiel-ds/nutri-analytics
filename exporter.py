"""
Módulo de exportación de contexto limpio para agentes de IA (LLMs).

Transforma los datos de las 5 tablas del esquema (ver db/001_esquema_inicial.sql)
en Markdown y DataFrames de pandas, siguiendo el formato descrito en
docs/plan_app_personal.md (sección 4), ajustado al esquema real documentado en
docs/decisiones.md (D2: menús con una sola columna "fecha"; D3: macros de
recetas como columnas planas calorias/proteinas/carbohidratos/grasas).

Diseño en dos capas:
  - Capa 1: funciones puras de transformación (list[dict] -> str / DataFrame).
    No tocan la red ni la base de datos; con listas vacías devuelven salidas
    vacías pero bien formadas.
  - Capa 2: orquestación, que llama a las funciones de lectura de database.py
    y vuelca el resultado a disco (exportar_contexto) o a un ZIP en memoria
    (generar_zip_contexto).

Este módulo no depende de Streamlit y deja propagar cualquier excepción.
"""

import io
import zipfile
from datetime import date, datetime
from pathlib import Path

import pandas as pd

import database

# Orden lógico de los días de la semana en español (weekday(): 0 = Lunes).
# Se deriva manualmente para no depender del locale del sistema operativo
# (en Windows, la configuración regional de locale es poco fiable).
DIAS_SEMANA_ES: list[str] = [
    "Lunes",
    "Martes",
    "Miércoles",
    "Jueves",
    "Viernes",
    "Sábado",
    "Domingo",
]

# Orden lógico de los tipos de comida, coherente con el CHECK del esquema.
ORDEN_TIPOS_COMIDA: list[str] = ["Desayuno", "Almuerzo", "Merienda", "Cena"]


def _neutralizar_formula(valor: object) -> object:
    """Neutraliza la inyección de fórmulas CSV (CSV formula injection) en
    campos de texto libre.

    Si un CSV se abre en Excel (u otra hoja de cálculo) y una celda empieza
    por "=", "+", "-" o "@", el programa la interpreta como una fórmula y la
    ejecuta, lo que permite inyectar comandos a través de texto libre
    guardado por la persona usuaria (p. ej. en una nota o un comentario).
    Para evitarlo, a los valores `str` que empiecen por uno de esos
    caracteres se les antepone un apóstrofo, que fuerza a la hoja de cálculo
    a tratarlos como texto literal.

    Solo actúa sobre `str`; cualquier otro tipo (None, números, booleanos...)
    se devuelve sin modificar.

    Args:
        valor: valor de una celda de texto libre.

    Returns:
        El valor original, o con un apóstrofo antepuesto si es un `str` que
        empieza por "=", "+", "-" o "@".
    """
    if isinstance(valor, str) and valor and valor[0] in ("=", "+", "-", "@"):
        return "'" + valor
    return valor


def _parse_fecha(valor: str | date | datetime) -> date:
    """Normaliza un valor de fecha (str 'YYYY-MM-DD', str ISO con hora, date o
    datetime, tal como pueden llegar desde Supabase) a un objeto `date`."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str):
        # Puede venir como fecha pura ("2026-07-18") o timestamp ISO completo
        # ("2026-07-18T10:23:45+00:00"); los primeros 10 caracteres bastan.
        return date.fromisoformat(valor[:10])
    raise TypeError(f"Tipo de fecha no soportado: {type(valor)!r}")


# -----------------------------------------------------------------------------
# Capa 1 — Funciones puras de transformación
# -----------------------------------------------------------------------------


def recetas_a_markdown(recetas: list[dict]) -> str:
    """Genera el catálogo Markdown de recetas (docs/plan_app_personal.md, sección 4.A).

    Cada receta se representa con su ID corto (5 primeros caracteres del uuid),
    los campos opcionales (descripción, categoría, tiempo) se omiten si son
    None, y los macros (columnas planas, decisión D3) muestran "?" cuando
    falta algún valor.
    """
    lineas = ["# Catálogo de Recetas Disponibles", ""]

    for receta in recetas:
        id_corto = str(receta.get("id", ""))[:5]
        titulo = receta.get("titulo", "")
        lineas.append(f"## [ID: {id_corto}] {titulo}")

        descripcion = receta.get("descripcion")
        if descripcion:
            # Colapsamos los saltos de línea internos a un espacio: una
            # descripción multilínea, tal cual, rompería el bullet Markdown
            # (la segunda línea quedaría fuera de la lista). Las
            # instrucciones sí conservan sus saltos de línea, en su propia
            # sección, porque ahí son legítimos (pasos numerados, etc.).
            descripcion_una_linea = descripcion.replace("\r\n", " ").replace(
                "\r", " "
            ).replace("\n", " ")
            lineas.append(f"* **Descripción:** {descripcion_una_linea}")

        categoria = receta.get("categoria")
        if categoria:
            lineas.append(f"* **Categoría:** {categoria}")

        tiempo = receta.get("tiempo_preparacion")
        if tiempo is not None:
            lineas.append(f"* **Tiempo:** {tiempo} min")

        def _o_interrogante(valor: object) -> str:
            return str(valor) if valor is not None else "?"

        calorias = _o_interrogante(receta.get("calorias"))
        proteinas = _o_interrogante(receta.get("proteinas"))
        carbohidratos = _o_interrogante(receta.get("carbohidratos"))
        grasas = _o_interrogante(receta.get("grasas"))
        lineas.append(
            f"* **Macros:** {calorias} kcal | P: {proteinas}g | "
            f"C: {carbohidratos}g | G: {grasas}g"
        )

        lineas.append("### Ingredientes")
        for ingrediente in receta.get("ingredientes") or []:
            lineas.append(f"- {ingrediente}")

        instrucciones = receta.get("instrucciones")
        if instrucciones:
            lineas.append("### Instrucciones")
            lineas.append(instrucciones)

        lineas.append("---")

    return "\n".join(lineas) + "\n"


def menus_a_dataframe(menus: list[dict]) -> pd.DataFrame:
    """Convierte las comidas planificadas (con receta embebida, tal como las
    devuelve `database.obtener_menu_rango`) en un DataFrame tabular.

    Columnas: Fecha, Dia, Tipo_Comida, Nombre_Receta, Calorias, Nota.
    Si `receta_id` es null, `Nombre_Receta` cae al valor de `nota_adicional`
    (si existe) o a cadena vacía. Orden: por Fecha y, dentro del día, por el
    orden lógico de comidas (Desayuno, Almuerzo, Merienda, Cena).
    """
    columnas = ["Fecha", "Dia", "Tipo_Comida", "Nombre_Receta", "Calorias", "Nota"]
    if not menus:
        return pd.DataFrame(columns=columnas)

    filas = []
    for menu in menus:
        fecha_obj = _parse_fecha(menu["fecha"])
        nota = menu.get("nota_adicional")
        receta = menu.get("recetas")

        if receta:
            nombre_receta = receta.get("titulo", "")
            calorias = receta.get("calorias")
        else:
            nombre_receta = nota or ""
            calorias = None

        filas.append(
            {
                "Fecha": fecha_obj.isoformat(),
                "Dia": DIAS_SEMANA_ES[fecha_obj.weekday()],
                "Tipo_Comida": menu.get("tipo_comida"),
                "Nombre_Receta": _neutralizar_formula(nombre_receta),
                "Calorias": calorias,
                "Nota": _neutralizar_formula(nota),
            }
        )

    df = pd.DataFrame(filas, columns=columnas)
    df["Tipo_Comida"] = pd.Categorical(
        df["Tipo_Comida"], categories=ORDEN_TIPOS_COMIDA, ordered=True
    )
    df = df.sort_values(["Fecha", "Tipo_Comida"], kind="stable").reset_index(drop=True)
    df["Tipo_Comida"] = df["Tipo_Comida"].astype(str)
    return df


def salud_a_dataframe(metricas: list[dict]) -> pd.DataFrame:
    """Convierte el histórico de métricas de salud en un DataFrame tabular.

    Columnas: Fecha, Peso, Porcentaje_Grasa, Cintura, Notas. Orden por Fecha
    ascendente.
    """
    columnas = ["Fecha", "Peso", "Porcentaje_Grasa", "Cintura", "Notas"]
    if not metricas:
        return pd.DataFrame(columns=columnas)

    filas = [
        {
            "Fecha": _parse_fecha(m["fecha"]).isoformat(),
            "Peso": m.get("peso"),
            "Porcentaje_Grasa": m.get("porcentaje_grasa"),
            "Cintura": m.get("perimetro_cintura"),
            "Notas": _neutralizar_formula(m.get("notas")),
        }
        for m in metricas
    ]
    df = pd.DataFrame(filas, columns=columnas)
    return df.sort_values("Fecha", kind="stable").reset_index(drop=True)


def deporte_a_dataframe(actividades: list[dict]) -> pd.DataFrame:
    """Convierte el histórico de actividad deportiva en un DataFrame tabular.

    Columnas: Fecha (solo fecha, aunque la BD guarda timestamp), Tipo_Actividad,
    Duracion, Intensidad, Volumen_Kg, Comentarios. Orden por Fecha ascendente.
    """
    columnas = [
        "Fecha",
        "Tipo_Actividad",
        "Duracion",
        "Intensidad",
        "Volumen_Kg",
        "Comentarios",
    ]
    if not actividades:
        return pd.DataFrame(columns=columnas)

    filas = [
        {
            "Fecha": _parse_fecha(a["fecha"]).isoformat(),
            "Tipo_Actividad": _neutralizar_formula(a.get("tipo_actividad")),
            "Duracion": a.get("duracion_minutos"),
            "Intensidad": _neutralizar_formula(a.get("intensidad")),
            "Volumen_Kg": a.get("volumen_total_kg"),
            "Comentarios": _neutralizar_formula(a.get("comentarios")),
        }
        for a in actividades
    ]
    df = pd.DataFrame(filas, columns=columnas)
    return df.sort_values("Fecha", kind="stable").reset_index(drop=True)


def lista_compra_a_dataframe(items: list[dict]) -> pd.DataFrame:
    """Convierte la lista de la compra en un DataFrame tabular.

    Columnas: Item, Cantidad, Categoria, Comprado.
    """
    columnas = ["Item", "Cantidad", "Categoria", "Comprado"]
    if not items:
        return pd.DataFrame(columns=columnas)

    filas = [
        {
            "Item": _neutralizar_formula(i.get("item")),
            "Cantidad": _neutralizar_formula(i.get("cantidad")),
            "Categoria": _neutralizar_formula(i.get("categoria")),
            "Comprado": i.get("comprado"),
        }
        for i in items
    ]
    return pd.DataFrame(filas, columns=columnas)


# -----------------------------------------------------------------------------
# Capa 2 — Orquestación (lee de database.py y escribe la exportación)
# -----------------------------------------------------------------------------


def exportar_contexto(
    fecha_desde: str, fecha_hasta: str, directorio: str | Path = "exports"
) -> dict[str, Path]:
    """Genera el paquete completo de contexto para IA y lo escribe en `directorio`.

    Crea el directorio si no existe y escribe: recetas.md (todas las recetas),
    menus_actuales.csv (menús en [fecha_desde, fecha_hasta]), historico_salud.csv
    e historico_deporte.csv (históricos completos) y lista_compra_base.csv
    (lista completa). Devuelve un dict nombre_archivo -> Path escrito.
    """
    directorio = Path(directorio)
    directorio.mkdir(parents=True, exist_ok=True)

    recetas = database.obtener_recetas()
    menus = database.obtener_menu_rango(fecha_desde, fecha_hasta)
    salud = database.obtener_historico_salud()
    deporte = database.obtener_historico_deporte()
    compra = database.obtener_lista()

    rutas: dict[str, Path] = {}

    ruta_recetas = directorio / "recetas.md"
    ruta_recetas.write_text(recetas_a_markdown(recetas), encoding="utf-8")
    rutas["recetas.md"] = ruta_recetas

    ruta_menus = directorio / "menus_actuales.csv"
    menus_a_dataframe(menus).to_csv(ruta_menus, index=False, encoding="utf-8")
    rutas["menus_actuales.csv"] = ruta_menus

    ruta_salud = directorio / "historico_salud.csv"
    salud_a_dataframe(salud).to_csv(ruta_salud, index=False, encoding="utf-8")
    rutas["historico_salud.csv"] = ruta_salud

    ruta_deporte = directorio / "historico_deporte.csv"
    deporte_a_dataframe(deporte).to_csv(ruta_deporte, index=False, encoding="utf-8")
    rutas["historico_deporte.csv"] = ruta_deporte

    ruta_compra = directorio / "lista_compra_base.csv"
    lista_compra_a_dataframe(compra).to_csv(ruta_compra, index=False, encoding="utf-8")
    rutas["lista_compra_base.csv"] = ruta_compra

    return rutas


def generar_zip_contexto(fecha_desde: str, fecha_hasta: str) -> bytes:
    """Genera el mismo paquete de contexto que `exportar_contexto`, pero como
    ZIP construido en memoria (sin tocar disco), listo para un
    `st.download_button` en la UI.
    """
    recetas = database.obtener_recetas()
    menus = database.obtener_menu_rango(fecha_desde, fecha_hasta)
    salud = database.obtener_historico_salud()
    deporte = database.obtener_historico_deporte()
    compra = database.obtener_lista()

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("recetas.md", recetas_a_markdown(recetas))
        zip_file.writestr(
            "menus_actuales.csv", menus_a_dataframe(menus).to_csv(index=False)
        )
        zip_file.writestr(
            "historico_salud.csv", salud_a_dataframe(salud).to_csv(index=False)
        )
        zip_file.writestr(
            "historico_deporte.csv", deporte_a_dataframe(deporte).to_csv(index=False)
        )
        zip_file.writestr(
            "lista_compra_base.csv", lista_compra_a_dataframe(compra).to_csv(index=False)
        )

    return buffer.getvalue()
