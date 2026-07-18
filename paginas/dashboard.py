"""Página Dashboard: resumen de las comidas de hoy y exportación de contexto para IA."""

from datetime import date, timedelta

import streamlit as st

import exporter
from paginas import comun

ORDEN_TIPOS_COMIDA = ("Desayuno", "Almuerzo", "Merienda", "Cena")


def render() -> None:
    """Renderiza la página Dashboard."""
    st.title("🥗 Nutri Analytics")
    hoy = date.today()
    st.caption(comun.fecha_larga(hoy))

    _seccion_comidas_de_hoy(hoy)

    st.divider()

    _seccion_exportar_contexto(hoy)


def _seccion_comidas_de_hoy(hoy: date) -> None:
    """Muestra un `st.container` por tipo de comida con lo planificado para hoy."""
    st.subheader("Comidas de hoy")

    try:
        comidas_hoy = comun.menu_rango_cacheado(hoy, hoy)
    except Exception as error:
        comidas_hoy = []
        st.caption(f"No se pudo cargar el menú de hoy ({error}).")

    comidas_por_tipo = {c.get("tipo_comida"): c for c in comidas_hoy}

    total_kcal = 0
    hay_calorias = False

    for tipo in ORDEN_TIPOS_COMIDA:
        comida = comidas_por_tipo.get(tipo)
        with st.container(border=True):
            st.markdown(f"**{tipo}**")
            receta = comida.get("recetas") if comida else None
            if receta:
                st.write(receta.get("titulo", ""))
                calorias = receta.get("calorias")
                if calorias is not None:
                    st.caption(f"{calorias} kcal")
                    total_kcal += calorias
                    hay_calorias = True
            elif comida and comida.get("nota_adicional"):
                st.write(comida["nota_adicional"])
            else:
                st.caption("— Sin planificar —")

    if hay_calorias:
        st.markdown(f"**Total planificado: {total_kcal} kcal**")

    if not comidas_hoy:
        st.info(
            "Todavía no has planificado ninguna comida para hoy. "
            "Usa el Planificador para organizar tu semana."
        )


def _seccion_exportar_contexto(hoy: date) -> None:
    """Formulario de rango de fechas + generación/descarga del ZIP de contexto para IA."""
    st.subheader("Exportar contexto para IA")

    lunes = comun.lunes_de_la_semana(hoy)
    domingo = lunes + timedelta(days=6)

    desde = st.date_input("Desde", value=lunes)
    hasta = st.date_input("Hasta", value=domingo)

    if st.button("🤖 Generar exportación", type="primary", use_container_width=True):
        try:
            zip_bytes = exporter.generar_zip_contexto(desde.isoformat(), hasta.isoformat())
            st.session_state["dashboard_zip_bytes"] = zip_bytes
            st.session_state["dashboard_zip_nombre"] = (
                f"contexto_ia_{desde:%Y%m%d}_{hasta:%Y%m%d}.zip"
            )
        except Exception as error:
            st.error(f"No se pudo generar la exportación: {error}")

    if "dashboard_zip_bytes" in st.session_state:
        st.download_button(
            "⬇️ Descargar ZIP",
            data=st.session_state["dashboard_zip_bytes"],
            file_name=st.session_state.get("dashboard_zip_nombre", "contexto_ia.zip"),
            mime="application/zip",
            use_container_width=True,
        )
        st.caption(
            "Incluye: recetas.md, menus_actuales.csv, historico_salud.csv, "
            "historico_deporte.csv y lista_compra_base.csv."
        )
