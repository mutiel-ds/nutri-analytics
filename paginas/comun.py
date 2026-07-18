"""Utilidades compartidas por las páginas de la UI.

Incluye wrappers cacheados sobre las lecturas de `database.py` (para no
golpear Supabase en cada rerun de Streamlit) y helpers de fecha en español
que no dependen del locale del sistema operativo (poco fiable en Windows).
"""

from datetime import date, timedelta

import streamlit as st

import database

# Orden lógico de los días de la semana en español (weekday(): 0 = Lunes).
DIAS_SEMANA_ES: list[str] = [
    "Lunes",
    "Martes",
    "Miércoles",
    "Jueves",
    "Viernes",
    "Sábado",
    "Domingo",
]

MESES_ES: list[str] = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]


@st.cache_data(ttl=60)
def recetas_cacheadas(categoria: str | None = None) -> list[dict]:
    """Wrapper cacheado de `database.obtener_recetas`.

    El TTL corto (60s) evita golpear Supabase en cada rerun de Streamlit.
    Tras cualquier escritura sobre recetas hay que llamar a `limpiar_cache()`
    para que el siguiente rerun refleje los cambios.
    """
    return database.obtener_recetas(categoria)


@st.cache_data(ttl=60)
def menu_rango_cacheado(desde: date, hasta: date) -> list[dict]:
    """Wrapper cacheado de `database.obtener_menu_rango`.

    El TTL corto (60s) evita golpear Supabase en cada rerun de Streamlit.
    Tras cualquier escritura sobre el menú hay que llamar a `limpiar_cache()`
    para que el siguiente rerun refleje los cambios.
    """
    return database.obtener_menu_rango(desde.isoformat(), hasta.isoformat())


def limpiar_cache() -> None:
    """Invalida toda la caché de lecturas; llamar tras cualquier escritura en la BD."""
    st.cache_data.clear()


def fecha_larga(d: date) -> str:
    """Formatea una fecha en español largo, p. ej. 'Sábado, 18 de julio de 2026'."""
    dia_semana = DIAS_SEMANA_ES[d.weekday()]
    mes = MESES_ES[d.month - 1]
    return f"{dia_semana}, {d.day} de {mes} de {d.year}"


def lunes_de_la_semana(d: date) -> date:
    """Devuelve la fecha del lunes de la semana natural a la que pertenece `d`."""
    return d - timedelta(days=d.weekday())
