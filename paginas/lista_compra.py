"""Página Lista de la compra: alta de items, marcado de comprados y vaciado."""

import streamlit as st

import database
import planificacion
from paginas import comun

SUGERENCIAS_CATEGORIA = [
    "Frutas",
    "Verduras",
    "Carnes",
    "Pescados",
    "Lácteos",
    "Despensa",
    "Congelados",
    "Otros",
]


def render() -> None:
    """Renderiza la página Lista de la compra."""
    st.title("🛒 Lista de la compra")

    hubo_error_carga = False
    try:
        items = comun.lista_compra_cacheada()
    except Exception as error:
        items = []
        hubo_error_carga = True
        st.error(f"No se pudo cargar la lista de la compra: {error}")

    categorias_opciones = _categorias_opciones(items)

    _seccion_anadir_item(categorias_opciones)

    st.divider()

    if hubo_error_carga:
        return

    if not items:
        st.info(
            "Todavía no tienes items en la lista de la compra. "
            "¡Añade el primero con el formulario de arriba!"
        )
        return

    solo_pendientes = st.checkbox(
        "Mostrar solo pendientes", value=False, key="lista_compra_solo_pendientes"
    )

    pendientes = [item for item in items if not item.get("comprado")]
    st.caption(f"{len(pendientes)} pendientes de {len(items)} items")

    items_mostrados = pendientes if solo_pendientes else items
    if not items_mostrados:
        st.info("No hay items pendientes. ¡Buen trabajo!")
    else:
        _listado(items_mostrados)

    comprados = [item for item in items if item.get("comprado")]
    if comprados:
        st.divider()
        _seccion_vaciar_comprados()


def _categorias_opciones(items: list[dict]) -> list[str]:
    """Categorías sugeridas + categorías ya usadas en la lista, sin duplicados."""
    opciones = list(SUGERENCIAS_CATEGORIA)
    categorias_existentes = sorted({i["categoria"] for i in items if i.get("categoria")})
    for categoria in categorias_existentes:
        if categoria not in opciones:
            opciones.append(categoria)
    return opciones


def _seccion_anadir_item(categorias_opciones: list[str]) -> None:
    with st.expander("➕ Añadir item"):
        with st.form(key="lista_compra_form_nuevo", clear_on_submit=False):
            item = st.text_input("Item *", key="lista_compra_nuevo_item")
            cantidad = st.text_input(
                "Cantidad",
                placeholder="500g, 2 uds...",
                key="lista_compra_nuevo_cantidad",
            )
            categoria = st.selectbox(
                "Categoría",
                options=categorias_opciones,
                index=None,
                accept_new_options=True,
                key="lista_compra_nuevo_categoria",
            )
            enviado = st.form_submit_button(
                "➕ Añadir", type="primary", use_container_width=True
            )

        if enviado:
            item_limpio = item.strip()
            if not item_limpio:
                st.error("El item es obligatorio.")
            else:
                try:
                    database.agregar_item(item_limpio, cantidad.strip() or None, categoria)
                    comun.limpiar_cache()
                    _limpiar_claves_formulario_nuevo_item()
                    st.success("Item añadido correctamente.")
                    st.rerun()
                except Exception as error:
                    st.error(f"No se pudo añadir el item: {error}")


def _limpiar_claves_formulario_nuevo_item() -> None:
    """Elimina del session_state los valores de los widgets del formulario de alta de item."""
    for clave in (
        "lista_compra_nuevo_item",
        "lista_compra_nuevo_cantidad",
        "lista_compra_nuevo_categoria",
    ):
        st.session_state.pop(clave, None)


def _listado(items: list[dict]) -> None:
    """Renderiza los items agrupados por categoría con `planificacion.agrupar_lista_compra`."""
    grupos = planificacion.agrupar_lista_compra(items)
    for categoria, items_categoria in grupos.items():
        st.markdown(f"**{categoria}**")
        for item in items_categoria:
            _fila_item(item)


def _fila_item(item: dict) -> None:
    item_id = item["id"]
    nombre = item.get("item", "")
    cantidad = item.get("cantidad")
    etiqueta = f"{nombre} · {cantidad}" if cantidad else nombre
    comprado_bd = bool(item.get("comprado"))

    col1, col2 = st.columns([6, 1])
    with col1:
        comprado_marcado = st.checkbox(
            etiqueta, value=comprado_bd, key=f"lista_compra_check_{item_id}"
        )
    with col2:
        eliminar = st.button("🗑️", key=f"lista_compra_eliminar_{item_id}")

    if comprado_marcado != comprado_bd:
        try:
            database.marcar_comprado(item_id, comprado_marcado)
            comun.limpiar_cache()
            st.rerun()
        except Exception as error:
            st.error(f"No se pudo actualizar el item: {error}")

    if eliminar:
        try:
            database.eliminar_item(item_id)
            comun.limpiar_cache()
            st.rerun()
        except Exception as error:
            st.error(f"No se pudo eliminar el item: {error}")


def _seccion_vaciar_comprados() -> None:
    """Botón de vaciado con confirmación en dos pasos (patrón de recetario)."""
    pendiente = st.session_state.get("lista_compra_vaciar_pendiente", False)

    if pendiente:
        st.caption("Se eliminarán todos los items marcados como comprados.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "⚠️ ¿Seguro? Sí, vaciar",
                key="lista_compra_confirmar_vaciar",
                type="primary",
                use_container_width=True,
            ):
                try:
                    database.vaciar_comprados()
                    comun.limpiar_cache()
                    st.session_state["lista_compra_vaciar_pendiente"] = False
                    st.success("Items comprados eliminados.")
                    st.rerun()
                except Exception as error:
                    st.error(f"No se pudo vaciar la lista: {error}")
        with col2:
            if st.button(
                "Cancelar", key="lista_compra_cancelar_vaciar", use_container_width=True
            ):
                st.session_state["lista_compra_vaciar_pendiente"] = False
                st.rerun()
    else:
        if st.button(
            "🧹 Vaciar comprados",
            key="lista_compra_boton_vaciar",
            use_container_width=True,
        ):
            st.session_state["lista_compra_vaciar_pendiente"] = True
            st.rerun()
