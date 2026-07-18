"""Tests unitarios de los helpers de fecha de paginas/comun.py.

Importar streamlit está bien (no requiere runtime de la app; `st.cache_data`
solo decora funciones sin ejecutar nada de servidor al importar el módulo).
"""

from datetime import date

from paginas.comun import fecha_larga, lunes_de_la_semana


def test_fecha_larga_fecha_conocida():
    """fecha_larga formatea una fecha conocida en español largo."""
    assert fecha_larga(date(2026, 7, 18)) == "Sábado, 18 de julio de 2026"


def test_lunes_de_la_semana_para_un_miercoles():
    """Para un miércoles, lunes_de_la_semana devuelve el lunes de esa misma semana."""
    miercoles = date(2026, 7, 15)  # miércoles
    assert lunes_de_la_semana(miercoles) == date(2026, 7, 13)


def test_lunes_de_la_semana_para_un_lunes():
    """Para un lunes, lunes_de_la_semana se devuelve a sí mismo."""
    lunes = date(2026, 7, 13)  # lunes
    assert lunes_de_la_semana(lunes) == lunes
