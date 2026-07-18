"""Punto de entrada de la app: configuración de página y navegación multipágina.

Usa `st.navigation` / `st.Page` (API moderna de Streamlit) en lugar de
`st.tabs`, según la decisión D8 de docs/decisiones.md.
"""

import streamlit as st

from paginas import dashboard, recetario, stubs

st.set_page_config(page_title="Nutri Analytics", page_icon="🥗", layout="centered")

# El aviso "Press Ctrl+Enter to submit form" de Streamlit se dibuja superpuesto
# sobre el texto cuando un text_area tiene varias líneas largas, tapando lo que
# el usuario ha escrito. Se oculta globalmente: los formularios ya tienen un
# botón de envío visible, así que el aviso es prescindible.
st.markdown(
    "<style>div[data-testid=\"InputInstructions\"] { visibility: hidden; }</style>",
    unsafe_allow_html=True,
)

paginas = [
    st.Page(dashboard.render, title="Dashboard", icon="🏠", default=True),
    st.Page(stubs.planificador, title="Planificador", icon="📅"),
    st.Page(recetario.render, title="Recetario", icon="🍳", url_path="recetario"),
    st.Page(stubs.lista_compra, title="Lista de la compra", icon="🛒"),
    st.Page(stubs.metricas, title="Métricas", icon="📈"),
]

pagina_activa = st.navigation(paginas)
pagina_activa.run()
