"""Punto de entrada de la app: configuración de página y navegación multipágina.

Usa `st.navigation` / `st.Page` (API moderna de Streamlit) en lugar de
`st.tabs`, según la decisión D8 de docs/decisiones.md.
"""

import os

import streamlit as st

from paginas import dashboard, lista_compra, metricas, planificador, recetario

st.set_page_config(page_title="Nutri Analytics", page_icon="🥗", layout="centered")

# En Streamlit Community Cloud las credenciales viven en st.secrets (no hay .env).
# Este puente las copia al entorno para que database.py (que es puro y solo lee
# variables de entorno, decisión D9) funcione igual en local y en la nube.
# Nota: acceder a st.secrets cuando no existe secrets.toml lanza
# StreamlitSecretNotFoundError (comprobado en local), de ahí el try/except: en
# desarrollo local con .env no hay secrets.toml y no debe fallar ni avisar.
try:
    _secrets_disponibles = len(st.secrets) > 0
except Exception:
    _secrets_disponibles = False

if _secrets_disponibles:
    for _clave in ("SUPABASE_URL", "SUPABASE_SECRET_KEY"):
        if not os.getenv(_clave) and _clave in st.secrets:
            os.environ[_clave] = st.secrets[_clave]

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
    st.Page(planificador.render, title="Planificador", icon="📅", url_path="planificador"),
    st.Page(recetario.render, title="Recetario", icon="🍳", url_path="recetario"),
    st.Page(lista_compra.render, title="Lista de la compra", icon="🛒", url_path="lista-compra"),
    st.Page(metricas.render, title="Métricas", icon="📈", url_path="metricas"),
]

pagina_activa = st.navigation(paginas)
pagina_activa.run()
