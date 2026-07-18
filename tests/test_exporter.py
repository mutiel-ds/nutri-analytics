"""Tests unitarios de las funciones puras (capa 1) de exporter.py.

No se llama en ningún momento a las funciones de capa 2 (exportar_contexto,
generar_zip_contexto): esas tocan red/disco y se dejan fuera de estos tests.
"""

import pandas as pd

from exporter import (
    deporte_a_dataframe,
    lista_compra_a_dataframe,
    menus_a_dataframe,
    recetas_a_markdown,
    salud_a_dataframe,
)

# -----------------------------------------------------------------------------
# recetas_a_markdown
# -----------------------------------------------------------------------------


def test_recetas_a_markdown_cabecera_y_id_corto():
    """El Markdown empieza con la cabecera del catálogo y usa un ID corto de 5 caracteres."""
    recetas = [
        {
            "id": "abcdef01-2345-6789-abcd-ef0123456789",
            "titulo": "Tortitas de avena",
            "descripcion": "Desayuno rápido",
            "categoria": "Desayuno",
            "tiempo_preparacion": 10,
            "calorias": 350,
            "proteinas": 20,
            "carbohidratos": 40,
            "grasas": 8,
            "ingredientes": ["Avena", "Huevo"],
            "instrucciones": "Mezclar y cocinar.",
        }
    ]
    md = recetas_a_markdown(recetas)
    lineas = md.splitlines()
    assert lineas[0] == "# Catálogo de Recetas Disponibles"
    assert "## [ID: abcde] Tortitas de avena" in md


def test_recetas_a_markdown_campos_opcionales_none_se_omiten():
    """Los campos opcionales (descripción, categoría, tiempo) no aparecen si son None."""
    recetas = [
        {
            "id": "12345-xxxx",
            "titulo": "Receta mínima",
            "descripcion": None,
            "categoria": None,
            "tiempo_preparacion": None,
            "calorias": 100,
            "proteinas": 10,
            "carbohidratos": 10,
            "grasas": 1,
            "ingredientes": [],
            "instrucciones": None,
        }
    ]
    md = recetas_a_markdown(recetas)
    assert "Descripción" not in md
    assert "Categoría" not in md
    assert "Tiempo" not in md
    assert "Instrucciones" not in md


def test_recetas_a_markdown_macros_faltantes_como_interrogante():
    """Si algún macro es None, se muestra como '?' en la línea de macros."""
    receta = {
        "id": "12345-xxxx",
        "titulo": "Receta sin macros",
        "calorias": None,
        "proteinas": None,
        "carbohidratos": None,
        "grasas": None,
        "ingredientes": [],
    }
    md = recetas_a_markdown([receta])
    assert "* **Macros:** ? kcal | P: ?g | C: ?g | G: ?g" in md


def test_recetas_a_markdown_separador_entre_recetas():
    """Cada receta termina con un separador '---'."""
    recetas = [
        {"id": "11111", "titulo": "Receta 1", "ingredientes": []},
        {"id": "22222", "titulo": "Receta 2", "ingredientes": []},
    ]
    md = recetas_a_markdown(recetas)
    assert md.count("---") == 2


def test_recetas_a_markdown_lista_vacia_solo_cabecera():
    """Con una lista vacía de recetas, el Markdown contiene solo la cabecera."""
    md = recetas_a_markdown([])
    assert md == "# Catálogo de Recetas Disponibles\n\n"


# -----------------------------------------------------------------------------
# menus_a_dataframe
# -----------------------------------------------------------------------------


def test_menus_a_dataframe_columnas_exactas():
    """El DataFrame de menús tiene exactamente las columnas esperadas, en orden."""
    menus = [
        {
            "fecha": "2026-07-18",
            "tipo_comida": "Desayuno",
            "nota_adicional": None,
            "recetas": {"titulo": "Tortitas", "calorias": 350},
        }
    ]
    df = menus_a_dataframe(menus)
    assert list(df.columns) == [
        "Fecha",
        "Dia",
        "Tipo_Comida",
        "Nombre_Receta",
        "Calorias",
        "Nota",
    ]


def test_menus_a_dataframe_dia_en_espanol_fecha_conocida():
    """1999-01-04 es un lunes: la columna Dia debe derivarse correctamente en español."""
    menus = [
        {
            "fecha": "1999-01-04",
            "tipo_comida": "Desayuno",
            "nota_adicional": None,
            "recetas": {"titulo": "Café", "calorias": 5},
        }
    ]
    df = menus_a_dataframe(menus)
    assert df.loc[0, "Dia"] == "Lunes"


def test_menus_a_dataframe_orden_por_fecha_y_tipo_comida():
    """El DataFrame se ordena primero por fecha y, dentro del día, por tipo de comida."""
    menus = [
        {
            "fecha": "1999-01-05",
            "tipo_comida": "Cena",
            "nota_adicional": "Cena día 2",
            "recetas": None,
        },
        {
            "fecha": "1999-01-04",
            "tipo_comida": "Cena",
            "nota_adicional": "Cena día 1",
            "recetas": None,
        },
        {
            "fecha": "1999-01-04",
            "tipo_comida": "Desayuno",
            "nota_adicional": "Desayuno día 1",
            "recetas": None,
        },
    ]
    df = menus_a_dataframe(menus)
    assert list(df["Nota"]) == ["Desayuno día 1", "Cena día 1", "Cena día 2"]


def test_menus_a_dataframe_fallback_nombre_receta_a_nota():
    """Cuando no hay receta embebida (receta_id null), Nombre_Receta cae a la nota."""
    menus = [
        {
            "fecha": "1999-01-04",
            "tipo_comida": "Almuerzo",
            "nota_adicional": "Sobras de la nevera",
            "recetas": None,
        }
    ]
    df = menus_a_dataframe(menus)
    assert df.loc[0, "Nombre_Receta"] == "Sobras de la nevera"
    assert df.loc[0, "Calorias"] is None or pd.isna(df.loc[0, "Calorias"])


def test_menus_a_dataframe_fallback_nombre_receta_cadena_vacia_sin_nota():
    """Sin receta embebida ni nota, Nombre_Receta cae a cadena vacía."""
    menus = [
        {
            "fecha": "1999-01-04",
            "tipo_comida": "Merienda",
            "nota_adicional": None,
            "recetas": None,
        }
    ]
    df = menus_a_dataframe(menus)
    assert df.loc[0, "Nombre_Receta"] == ""


def test_menus_a_dataframe_lista_vacia():
    """Con una lista vacía de menús, se devuelve un DataFrame vacío con las columnas correctas."""
    df = menus_a_dataframe([])
    assert df.empty
    assert list(df.columns) == [
        "Fecha",
        "Dia",
        "Tipo_Comida",
        "Nombre_Receta",
        "Calorias",
        "Nota",
    ]


# -----------------------------------------------------------------------------
# salud_a_dataframe
# -----------------------------------------------------------------------------


def test_salud_a_dataframe_columnas_y_orden():
    """El DataFrame de salud tiene las columnas esperadas y se ordena por fecha ascendente."""
    metricas = [
        {"fecha": "1999-01-05", "peso": 80.0, "porcentaje_grasa": 20.0, "perimetro_cintura": 90, "notas": "b"},
        {"fecha": "1999-01-04", "peso": 81.0, "porcentaje_grasa": 21.0, "perimetro_cintura": 91, "notas": "a"},
    ]
    df = salud_a_dataframe(metricas)
    assert list(df.columns) == ["Fecha", "Peso", "Porcentaje_Grasa", "Cintura", "Notas"]
    assert list(df["Fecha"]) == ["1999-01-04", "1999-01-05"]


def test_salud_a_dataframe_timestamp_iso_reducido_a_fecha():
    """Un timestamp ISO completo en 'fecha' se reduce a solo la parte de fecha."""
    metricas = [
        {
            "fecha": "1999-01-04T10:23:45+00:00",
            "peso": 80.0,
            "porcentaje_grasa": None,
            "perimetro_cintura": None,
            "notas": None,
        }
    ]
    df = salud_a_dataframe(metricas)
    assert df.loc[0, "Fecha"] == "1999-01-04"


def test_salud_a_dataframe_lista_vacia():
    """Con una lista vacía de métricas, se devuelve un DataFrame vacío con las columnas correctas."""
    df = salud_a_dataframe([])
    assert df.empty
    assert list(df.columns) == ["Fecha", "Peso", "Porcentaje_Grasa", "Cintura", "Notas"]


# -----------------------------------------------------------------------------
# deporte_a_dataframe
# -----------------------------------------------------------------------------


def test_deporte_a_dataframe_columnas_y_orden():
    """El DataFrame de deporte tiene las columnas esperadas y se ordena por fecha ascendente."""
    actividades = [
        {
            "fecha": "1999-01-05T08:00:00+00:00",
            "tipo_actividad": "Correr",
            "duracion_minutos": 30,
            "intensidad": "Media",
            "volumen_total_kg": None,
            "comentarios": "b",
        },
        {
            "fecha": "1999-01-04T08:00:00+00:00",
            "tipo_actividad": "Pesas",
            "duracion_minutos": 60,
            "intensidad": "Alta",
            "volumen_total_kg": 2000.0,
            "comentarios": "a",
        },
    ]
    df = deporte_a_dataframe(actividades)
    assert list(df.columns) == [
        "Fecha",
        "Tipo_Actividad",
        "Duracion",
        "Intensidad",
        "Volumen_Kg",
        "Comentarios",
    ]
    assert list(df["Fecha"]) == ["1999-01-04", "1999-01-05"]
    assert list(df["Comentarios"]) == ["a", "b"]


def test_deporte_a_dataframe_timestamp_iso_reducido_a_fecha():
    """El timestamp completo que guarda la BD para 'fecha' se reduce a solo la parte de fecha."""
    actividades = [
        {
            "fecha": "1999-01-04T21:15:00+00:00",
            "tipo_actividad": "Natación",
            "duracion_minutos": 45,
            "intensidad": "Baja",
            "volumen_total_kg": None,
            "comentarios": None,
        }
    ]
    df = deporte_a_dataframe(actividades)
    assert df.loc[0, "Fecha"] == "1999-01-04"


def test_deporte_a_dataframe_lista_vacia():
    """Con una lista vacía de actividades, se devuelve un DataFrame vacío con las columnas correctas."""
    df = deporte_a_dataframe([])
    assert df.empty
    assert list(df.columns) == [
        "Fecha",
        "Tipo_Actividad",
        "Duracion",
        "Intensidad",
        "Volumen_Kg",
        "Comentarios",
    ]


# -----------------------------------------------------------------------------
# lista_compra_a_dataframe
# -----------------------------------------------------------------------------


def test_lista_compra_a_dataframe_columnas_y_contenido():
    """El DataFrame de la lista de la compra tiene las columnas y el contenido esperados."""
    items = [
        {"item": "Leche", "cantidad": "2L", "categoria": "Lácteos", "comprado": False},
        {"item": "Pan", "cantidad": None, "categoria": "Panadería", "comprado": True},
    ]
    df = lista_compra_a_dataframe(items)
    assert list(df.columns) == ["Item", "Cantidad", "Categoria", "Comprado"]
    assert df.loc[0, "Item"] == "Leche"
    assert df.loc[0, "Cantidad"] == "2L"
    assert df.loc[1, "Comprado"] == True  # noqa: E712 (comprobación explícita de valor booleano)


def test_lista_compra_a_dataframe_lista_vacia():
    """Con una lista vacía de items, se devuelve un DataFrame vacío con las columnas correctas."""
    df = lista_compra_a_dataframe([])
    assert df.empty
    assert list(df.columns) == ["Item", "Cantidad", "Categoria", "Comprado"]
