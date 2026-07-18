"""Punto de entrada de la app: configuración de página y navegación multipágina.

Usa `st.navigation` / `st.Page` (API moderna de Streamlit) en lugar de
`st.tabs`, según la decisión D8 de docs/decisiones.md.
"""

import streamlit as st

from paginas import dashboard, stubs

st.set_page_config(page_title="Nutri Analytics", page_icon="🥗", layout="centered")

paginas = [
    st.Page(dashboard.render, title="Dashboard", icon="🏠", default=True),
    st.Page(stubs.planificador, title="Planificador", icon="📅"),
    st.Page(stubs.recetario, title="Recetario", icon="🍳"),
    st.Page(stubs.lista_compra, title="Lista de la compra", icon="🛒"),
    st.Page(stubs.metricas, title="Métricas", icon="📈"),
]

pagina_activa = st.navigation(paginas)
pagina_activa.run()
