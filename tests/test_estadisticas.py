"""Tests unitarios (puros, sin red) de estadisticas.py."""

import math
from datetime import date

import pandas as pd

from estadisticas import (
    etiqueta_semana,
    filtrar_por_periodo,
    minutos_por_semana,
    resumen_salud,
    series_salud,
)

# -----------------------------------------------------------------------------
# filtrar_por_periodo
# -----------------------------------------------------------------------------


def test_filtrar_por_periodo_none_devuelve_todo():
    """dias=None devuelve la lista completa, sin filtrar."""
    registros = [{"fecha": "2020-01-01"}, {"fecha": "2026-07-19"}]
    assert filtrar_por_periodo(registros, None, date(2026, 7, 19)) == registros


def test_filtrar_por_periodo_incluye_el_borde_inferior():
    """Un registro justo en hoy - dias se incluye (borde inclusive)."""
    hoy = date(2026, 7, 19)
    registros = [{"fecha": "2026-06-19"}]  # exactamente 30 días antes
    assert filtrar_por_periodo(registros, 30, hoy) == registros


def test_filtrar_por_periodo_incluye_el_borde_superior_hoy():
    """Un registro con fecha=hoy se incluye (borde inclusive)."""
    hoy = date(2026, 7, 19)
    registros = [{"fecha": "2026-07-19"}]
    assert filtrar_por_periodo(registros, 30, hoy) == registros


def test_filtrar_por_periodo_excluye_fuera_de_rango():
    """Un registro anterior al límite inferior se excluye."""
    hoy = date(2026, 7, 19)
    registros = [{"fecha": "2026-06-18"}]  # 31 días antes
    assert filtrar_por_periodo(registros, 30, hoy) == []


def test_filtrar_por_periodo_admite_timestamps_con_hora():
    """Una fecha con componente de hora (timestamptz) se interpreta correctamente."""
    hoy = date(2026, 7, 19)
    registros = [{"fecha": "2026-07-18T22:15:00+00:00"}]
    assert filtrar_por_periodo(registros, 30, hoy) == registros


def test_filtrar_por_periodo_mixto():
    """Con varios registros, solo pasan los que caen dentro del rango."""
    hoy = date(2026, 7, 19)
    dentro = {"fecha": "2026-07-01"}
    fuera = {"fecha": "2026-01-01"}
    registros = [dentro, fuera]
    assert filtrar_por_periodo(registros, 30, hoy) == [dentro]


# -----------------------------------------------------------------------------
# series_salud
# -----------------------------------------------------------------------------


def test_series_salud_columnas_y_tipos():
    """El DataFrame resultante tiene las columnas esperadas y Fecha es datetime64."""
    metricas = [{"fecha": "2026-07-18", "peso": 80.5, "porcentaje_grasa": 20.1, "perimetro_cintura": 85.0}]
    df = series_salud(metricas)
    assert list(df.columns) == ["Fecha", "Peso", "Porcentaje_Grasa", "Cintura"]
    assert pd.api.types.is_datetime64_any_dtype(df["Fecha"])
    assert df.loc[0, "Peso"] == 80.5


def test_series_salud_orden_ascendente_por_fecha():
    """Los registros se devuelven ordenados por Fecha ascendente, sin importar el orden de entrada."""
    metricas = [
        {"fecha": "2026-07-18", "peso": 80.0},
        {"fecha": "2026-07-01", "peso": 81.0},
    ]
    df = series_salud(metricas)
    assert list(df["Fecha"].dt.date) == [date(2026, 7, 1), date(2026, 7, 18)]


def test_series_salud_campos_ausentes_dan_nan():
    """Un campo no informado en el registro se traduce en NaN en el DataFrame."""
    metricas = [{"fecha": "2026-07-18", "peso": 80.0}]
    df = series_salud(metricas)
    assert math.isnan(df.loc[0, "Porcentaje_Grasa"])
    assert math.isnan(df.loc[0, "Cintura"])


def test_series_salud_lista_vacia_devuelve_dataframe_vacio_con_columnas():
    """Una lista vacía devuelve un DataFrame vacío pero con las columnas correctas."""
    df = series_salud([])
    assert df.empty
    assert list(df.columns) == ["Fecha", "Peso", "Porcentaje_Grasa", "Cintura"]


# -----------------------------------------------------------------------------
# resumen_salud
# -----------------------------------------------------------------------------


def test_resumen_salud_lista_vacia_devuelve_none():
    """Sin registros, resumen_salud devuelve None."""
    assert resumen_salud([]) is None


def test_resumen_salud_primer_registro_deltas_none():
    """Con un único registro, todos los deltas son None (no hay anterior)."""
    metricas = [{"fecha": "2026-07-18", "peso": 80.0, "porcentaje_grasa": 20.0, "perimetro_cintura": 85.0}]
    resumen = resumen_salud(metricas)
    assert resumen["fecha"] == "2026-07-18"
    assert resumen["peso"] == 80.0
    assert resumen["delta_peso"] is None
    assert resumen["delta_grasa"] is None
    assert resumen["delta_cintura"] is None


def test_resumen_salud_delta_normal_contra_el_registro_inmediatamente_anterior():
    """El delta se calcula contra el registro anterior cuando este tiene el campo."""
    metricas = [
        {"fecha": "2026-07-01", "peso": 81.0},
        {"fecha": "2026-07-18", "peso": 80.0},
    ]
    resumen = resumen_salud(metricas)
    assert resumen["peso"] == 80.0
    assert round(resumen["delta_peso"], 2) == -1.0


def test_resumen_salud_delta_busca_hacia_atras_el_anterior_que_tenga_el_campo():
    """Si el registro inmediatamente anterior no tiene el campo, se busca más atrás."""
    metricas = [
        {"fecha": "2026-06-01", "porcentaje_grasa": 22.0},
        {"fecha": "2026-07-01", "peso": 81.0},  # sin porcentaje_grasa
        {"fecha": "2026-07-18", "peso": 80.0, "porcentaje_grasa": 20.0},
    ]
    resumen = resumen_salud(metricas)
    assert resumen["porcentaje_grasa"] == 20.0
    assert round(resumen["delta_grasa"], 2) == -2.0


def test_resumen_salud_campo_ausente_en_ningun_anterior_da_delta_none():
    """Si ningún registro anterior tiene el campo, el delta es None."""
    metricas = [
        {"fecha": "2026-07-01", "peso": 81.0},
        {"fecha": "2026-07-18", "peso": 80.0, "perimetro_cintura": 85.0},
    ]
    resumen = resumen_salud(metricas)
    assert resumen["perimetro_cintura"] == 85.0
    assert resumen["delta_cintura"] is None


def test_resumen_salud_campo_ausente_en_el_actual_da_valor_y_delta_none():
    """Si el registro más reciente no tiene el campo, tanto el valor como el delta son None."""
    metricas = [
        {"fecha": "2026-07-01", "peso": 81.0},
        {"fecha": "2026-07-18", "porcentaje_grasa": 20.0},  # sin peso
    ]
    resumen = resumen_salud(metricas)
    assert resumen["peso"] is None
    assert resumen["delta_peso"] is None


def test_resumen_salud_ordena_internamente_por_fecha():
    """resumen_salud no depende del orden de entrada de la lista."""
    metricas = [
        {"fecha": "2026-07-18", "peso": 80.0},
        {"fecha": "2026-07-01", "peso": 81.0},
    ]
    resumen = resumen_salud(metricas)
    assert resumen["fecha"] == "2026-07-18"
    assert round(resumen["delta_peso"], 2) == -1.0


# -----------------------------------------------------------------------------
# etiqueta_semana
# -----------------------------------------------------------------------------


def test_etiqueta_semana_mismo_mes():
    """Cuando el lunes y el domingo caen en el mismo mes, se usa el formato "13-19 jul"."""
    assert etiqueta_semana(date(2026, 7, 13)) == "13-19 jul"


def test_etiqueta_semana_cruce_de_mes():
    """Cuando la semana cruza de mes, se muestra el mes de cada extremo."""
    assert etiqueta_semana(date(2026, 6, 29)) == "29 jun - 5 jul"


def test_etiqueta_semana_cruce_de_anio():
    """El cruce de mes funciona igual si además cambia el año."""
    assert etiqueta_semana(date(2025, 12, 29)) == "29 dic - 4 ene"


# -----------------------------------------------------------------------------
# minutos_por_semana
# -----------------------------------------------------------------------------


def test_minutos_por_semana_agrupa_por_semana_y_tipo():
    """Las actividades de una misma semana natural y tipo se suman en una sola fila."""
    hoy = date(2026, 7, 19)  # domingo
    actividades = [
        {"fecha": "2026-07-13T10:00:00+00:00", "tipo_actividad": "Fuerza", "duracion_minutos": 60},
        {"fecha": "2026-07-15T10:00:00+00:00", "tipo_actividad": "Fuerza", "duracion_minutos": 45},
        {"fecha": "2026-07-16T10:00:00+00:00", "tipo_actividad": "Running", "duracion_minutos": 30},
    ]
    df = minutos_por_semana(actividades, hoy, num_semanas=12)
    lunes_semana = date(2026, 7, 13)

    fila_fuerza = df[(df["Semana"] == lunes_semana) & (df["Tipo_Actividad"] == "Fuerza")]
    assert fila_fuerza.iloc[0]["Minutos"] == 105
    assert fila_fuerza.iloc[0]["Semana_Etiqueta"] == "13-19 jul"

    fila_running = df[(df["Semana"] == lunes_semana) & (df["Tipo_Actividad"] == "Running")]
    assert fila_running.iloc[0]["Minutos"] == 30
    assert fila_running.iloc[0]["Semana_Etiqueta"] == "13-19 jul"


def test_minutos_por_semana_respeta_num_semanas():
    """Solo se incluyen actividades dentro de la ventana de num_semanas semanas."""
    hoy = date(2026, 7, 19)  # semana del 13/07 al 19/07
    dentro = {"fecha": "2026-07-13T10:00:00+00:00", "tipo_actividad": "Fuerza", "duracion_minutos": 60}
    # actividad de hace 20 semanas: fuera de una ventana de 12 semanas
    fuera = {"fecha": "2026-03-01T10:00:00+00:00", "tipo_actividad": "Fuerza", "duracion_minutos": 60}
    df = minutos_por_semana([dentro, fuera], hoy, num_semanas=12)
    assert df["Minutos"].sum() == 60


def test_minutos_por_semana_semana_etiqueta_coherente_con_semana_al_cruzar_mes():
    """Semana_Etiqueta refleja correctamente una semana que cruza de mes."""
    hoy = date(2026, 7, 5)  # domingo de la semana 29 jun - 5 jul
    actividades = [
        {"fecha": "2026-06-29T10:00:00+00:00", "tipo_actividad": "Running", "duracion_minutos": 40},
    ]
    df = minutos_por_semana(actividades, hoy, num_semanas=1)
    assert df.iloc[0]["Semana"] == date(2026, 6, 29)
    assert df.iloc[0]["Semana_Etiqueta"] == "29 jun - 5 jul"


def test_minutos_por_semana_actividades_fuera_de_rango_excluidas_devuelve_vacio():
    """Si todas las actividades quedan fuera del rango, el DataFrame resultante está vacío."""
    hoy = date(2026, 7, 19)
    actividades = [
        {"fecha": "2020-01-01T10:00:00+00:00", "tipo_actividad": "Fuerza", "duracion_minutos": 60},
    ]
    df = minutos_por_semana(actividades, hoy, num_semanas=12)
    assert df.empty
    assert list(df.columns) == ["Semana", "Semana_Etiqueta", "Tipo_Actividad", "Minutos"]


def test_minutos_por_semana_lista_vacia_devuelve_dataframe_vacio():
    """Sin actividades, devuelve un DataFrame vacío con las columnas correctas."""
    df = minutos_por_semana([], date(2026, 7, 19))
    assert df.empty
    assert list(df.columns) == ["Semana", "Semana_Etiqueta", "Tipo_Actividad", "Minutos"]
