"""Página Recetario: alta, búsqueda/filtrado, edición y borrado de recetas."""

import streamlit as st

import database
import filtros
from paginas import comun

SUGERENCIAS_CATEGORIA = ["Desayuno", "Almuerzo", "Merienda", "Cena", "Snack"]


def render() -> None:
    """Renderiza la página Recetario."""
    st.title("🍳 Recetario")

    hubo_error_carga = False
    try:
        recetas = comun.recetas_cacheadas()
    except Exception as error:
        recetas = []
        hubo_error_carga = True
        st.error(f"No se pudieron cargar las recetas: {error}")

    categorias_opciones = _categorias_opciones(recetas)

    _seccion_nueva_receta(categorias_opciones)

    st.divider()

    if hubo_error_carga:
        return

    _seccion_buscador_listado(recetas, categorias_opciones)


def _categorias_opciones(recetas: list[dict]) -> list[str]:
    """Categorías existentes en las recetas cargadas + sugerencias base, sin duplicados."""
    opciones = list(SUGERENCIAS_CATEGORIA)
    categorias_existentes = sorted({r["categoria"] for r in recetas if r.get("categoria")})
    for categoria in categorias_existentes:
        if categoria not in opciones:
            opciones.append(categoria)
    return opciones


# -----------------------------------------------------------------------------
# Sección: nueva receta
# -----------------------------------------------------------------------------

def _seccion_nueva_receta(categorias_opciones: list[str]) -> None:
    with st.expander("➕ Añadir receta"):
        datos = _formulario_receta(
            prefix="nueva",
            categorias_opciones=categorias_opciones,
            valores=None,
            texto_submit="Guardar receta",
        )
        if datos is not None:
            try:
                database.crear_receta(datos)
                comun.limpiar_cache()
                _limpiar_claves_formulario("nueva")
                st.success("Receta creada correctamente.")
                st.rerun()
            except Exception as error:
                st.error(f"No se pudo crear la receta: {error}")


# -----------------------------------------------------------------------------
# Sección: buscador / listado
# -----------------------------------------------------------------------------

def _seccion_buscador_listado(recetas: list[dict], categorias_opciones: list[str]) -> None:
    if not recetas:
        st.info("Todavía no tienes recetas guardadas. ¡Añade la primera con el formulario de arriba!")
        return

    busqueda = st.text_input(
        "Buscar recetas",
        placeholder="🔍 Buscar por título o ingrediente...",
        label_visibility="collapsed",
        key="recetario_busqueda",
    )

    filtros_activos = st.session_state.setdefault("recetario_filtros", [])

    titulo_expander = "Filtros"
    if filtros_activos:
        titulo_expander = f"Filtros ({len(filtros_activos)})"

    with st.expander(titulo_expander):
        _constructor_filtro(recetas, categorias_opciones)
        _lista_filtros_activos()

    resultado = recetas

    if busqueda and busqueda.strip():
        consulta = busqueda.strip().lower()

        def _coincide(receta: dict) -> bool:
            if consulta in (receta.get("titulo") or "").lower():
                return True
            return any(consulta in ing.lower() for ing in (receta.get("ingredientes") or []))

        resultado = [r for r in resultado if _coincide(r)]

    filtradas = filtros.aplicar_filtros(resultado, st.session_state["recetario_filtros"])

    st.caption(f"{len(filtradas)} recetas")

    for receta in filtradas:
        _mostrar_receta(receta, categorias_opciones)


def _opciones_enum(campo: str, recetas: list[dict]) -> list[str]:
    """Valores existentes (no vacíos) de un campo enum en las recetas cargadas."""
    return sorted({r[campo] for r in recetas if r.get(campo)})


def _constructor_filtro(recetas: list[dict], categorias_opciones: list[str]) -> None:
    """Renderiza el formulario para construir y añadir un nuevo filtro."""
    etiquetas_por_campo = {info["etiqueta"]: campo for campo, info in filtros.CAMPOS_FILTRO.items()}
    etiquetas = list(etiquetas_por_campo.keys())

    etiqueta_elegida = st.selectbox("Campo", options=etiquetas, key="recetario_nuevo_campo")
    campo = etiquetas_por_campo[etiqueta_elegida]
    tipo = filtros.CAMPOS_FILTRO[campo]["tipo"]

    valor: object = None
    operador: str | None = None

    if tipo == "enum":
        opciones_valor = categorias_opciones if campo == "categoria" else _opciones_enum(campo, recetas)
        col1, col2 = st.columns(2)
        with col1:
            operador = st.selectbox(
                "Condición",
                options=filtros.OPERADORES_ENUM,
                format_func=lambda op: filtros.etiqueta_operador(campo, op),
                key="recetario_nuevo_operador_enum",
            )
        with col2:
            if opciones_valor:
                valor = st.selectbox(
                    "Valor", options=opciones_valor, key="recetario_nuevo_valor_enum"
                )
            else:
                st.selectbox("Valor", options=[], key="recetario_nuevo_valor_enum", disabled=True)
                valor = None
    elif tipo == "numerico":
        col1, col2 = st.columns(2)
        with col1:
            operador = st.selectbox(
                "Condición",
                options=filtros.OPERADORES_NUMERICOS,
                format_func=lambda op: filtros.etiqueta_operador(campo, op),
                key="recetario_nuevo_operador_num",
            )
        with col2:
            valor = st.number_input(
                "Valor", min_value=0, value=0, step=1, key="recetario_nuevo_valor_num"
            )
    else:  # ingredientes
        col1, col2 = st.columns(2)
        with col1:
            operador = st.selectbox(
                "Condición",
                options=filtros.OPERADORES_INGREDIENTES,
                format_func=lambda op: filtros.etiqueta_operador(campo, op),
                key="recetario_nuevo_operador_ing",
            )
        with col2:
            valor = st.text_input("Valor", key="recetario_nuevo_valor_ing")

    if st.button("➕ Añadir filtro", key="recetario_anadir_filtro", use_container_width=True):
        nuevo_filtro = {"campo": campo, "operador": operador, "valor": valor}
        try:
            filtros.validar_filtro(nuevo_filtro)
        except ValueError as error:
            st.error(str(error))
        else:
            if nuevo_filtro in st.session_state["recetario_filtros"]:
                st.error("Ese filtro ya está añadido.")
            else:
                st.session_state["recetario_filtros"].append(nuevo_filtro)
                st.rerun()


def _lista_filtros_activos() -> None:
    """Renderiza la lista de filtros activos con botón para quitarlos."""
    filtros_activos = st.session_state["recetario_filtros"]
    if not filtros_activos:
        return

    st.divider()

    for indice, filtro in enumerate(filtros_activos):
        col1, col2 = st.columns([5, 1])
        with col1:
            st.write(filtros.describir_filtro(filtro))
        with col2:
            if st.button("✖", key=f"recetario_quitar_filtro_{indice}"):
                st.session_state["recetario_filtros"].pop(indice)
                st.rerun()

    if len(filtros_activos) > 1:
        if st.button("Quitar todos los filtros", key="recetario_quitar_todos_filtros"):
            st.session_state["recetario_filtros"] = []
            st.rerun()


def _mostrar_receta(receta: dict, categorias_opciones: list[str]) -> None:
    receta_id = receta["id"]
    titulo = receta.get("titulo", "")
    calorias = receta.get("calorias")
    encabezado = f"{titulo} · {calorias} kcal" if calorias is not None else titulo

    editando = st.session_state.get("recetario_editando_id") == receta_id
    eliminar_pendiente = st.session_state.get("recetario_eliminar_pendiente_id") == receta_id

    with st.expander(encabezado):
        if editando:
            _seccion_editar_receta(receta, categorias_opciones)
            return

        if receta.get("descripcion"):
            st.write(receta["descripcion"])

        partes_macros = []
        if calorias is not None:
            partes_macros.append(f"🔥 {calorias} kcal")
        if receta.get("proteinas") is not None:
            partes_macros.append(f"P: {receta['proteinas']}g")
        if receta.get("carbohidratos") is not None:
            partes_macros.append(f"C: {receta['carbohidratos']}g")
        if receta.get("grasas") is not None:
            partes_macros.append(f"G: {receta['grasas']}g")
        if partes_macros:
            st.caption(" · ".join(partes_macros))

        detalles = []
        if receta.get("categoria"):
            detalles.append(receta["categoria"])
        if receta.get("tiempo_preparacion") is not None:
            detalles.append(f"⏱️ {receta['tiempo_preparacion']} min")
        if detalles:
            st.caption(" · ".join(detalles))

        if receta.get("ingredientes"):
            st.markdown("**Ingredientes**")
            for ingrediente in receta["ingredientes"]:
                st.markdown(f"- {ingrediente}")

        if receta.get("instrucciones"):
            st.markdown("**Instrucciones**")
            st.write(receta["instrucciones"])

        if eliminar_pendiente:
            st.caption("Los menús que la referencian quedarán sin receta asignada.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button(
                    "⚠️ ¿Seguro? Sí, eliminar",
                    key=f"confirmar_eliminar_{receta_id}",
                    type="primary",
                    use_container_width=True,
                ):
                    try:
                        database.eliminar_receta(receta_id)
                        comun.limpiar_cache()
                        st.session_state.pop("recetario_eliminar_pendiente_id", None)
                        st.success("Receta eliminada.")
                        st.rerun()
                    except Exception as error:
                        st.error(f"No se pudo eliminar la receta: {error}")
            with col2:
                if st.button(
                    "Cancelar", key=f"cancelar_eliminar_{receta_id}", use_container_width=True
                ):
                    st.session_state.pop("recetario_eliminar_pendiente_id", None)
                    st.rerun()
        else:
            col1, col2 = st.columns(2)
            with col1:
                if st.button(
                    "✏️ Editar", key=f"editar_{receta_id}", use_container_width=True
                ):
                    st.session_state["recetario_editando_id"] = receta_id
                    st.rerun()
            with col2:
                if st.button(
                    "🗑️ Eliminar", key=f"eliminar_{receta_id}", use_container_width=True
                ):
                    st.session_state["recetario_eliminar_pendiente_id"] = receta_id
                    st.rerun()


def _seccion_editar_receta(receta: dict, categorias_opciones: list[str]) -> None:
    receta_id = receta["id"]
    prefix = f"editar_{receta_id}"

    opciones = categorias_opciones
    if receta.get("categoria") and receta["categoria"] not in opciones:
        opciones = opciones + [receta["categoria"]]

    datos = _formulario_receta(
        prefix=prefix,
        categorias_opciones=opciones,
        valores=receta,
        texto_submit="Guardar cambios",
    )

    if datos is not None:
        try:
            database.actualizar_receta(receta_id, datos)
            comun.limpiar_cache()
            _limpiar_claves_formulario(prefix)
            st.session_state.pop("recetario_editando_id", None)
            st.success("Receta actualizada.")
            st.rerun()
        except Exception as error:
            st.error(f"No se pudo actualizar la receta: {error}")

    if st.button("Cancelar", key=f"cancelar_{prefix}", use_container_width=True):
        _limpiar_claves_formulario(prefix)
        st.session_state.pop("recetario_editando_id", None)
        st.rerun()


def _limpiar_claves_formulario(prefix: str) -> None:
    """Elimina del session_state los valores de los widgets de un formulario de receta."""
    prefijo_widget = f"{prefix}_"
    for clave in [k for k in st.session_state.keys() if k.startswith(prefijo_widget)]:
        del st.session_state[clave]


# -----------------------------------------------------------------------------
# Formulario reutilizado (alta y edición)
# -----------------------------------------------------------------------------

def _formulario_receta(
    prefix: str,
    categorias_opciones: list[str],
    valores: dict | None,
    texto_submit: str,
) -> dict | None:
    """Renderiza el formulario de alta/edición de una receta.

    Devuelve el diccionario de datos (listo para `crear_receta`/`actualizar_receta`)
    si el formulario se envía y pasa la validación; devuelve None si aún no se ha
    enviado o si hay errores (ya mostrados con `st.error`).
    """
    valores = valores or {}

    categoria_actual = valores.get("categoria")
    indice_categoria = (
        categorias_opciones.index(categoria_actual) if categoria_actual in categorias_opciones else None
    )

    with st.form(key=f"form_{prefix}", clear_on_submit=False):
        titulo = st.text_input(
            "Título *", value=valores.get("titulo", ""), key=f"{prefix}_titulo"
        )
        descripcion = st.text_area(
            "Descripción",
            value=valores.get("descripcion") or "",
            height=68,
            key=f"{prefix}_descripcion",
        )
        categoria = st.selectbox(
            "Categoría",
            options=categorias_opciones,
            index=indice_categoria,
            accept_new_options=True,
            key=f"{prefix}_categoria",
        )
        tiempo_preparacion = st.number_input(
            "Tiempo de preparación (min)",
            min_value=0,
            value=int(valores.get("tiempo_preparacion") or 0),
            step=5,
            key=f"{prefix}_tiempo",
        )

        calorias = st.number_input(
            "Calorías (kcal)",
            min_value=0,
            value=valores.get("calorias"),
            step=10,
            key=f"{prefix}_calorias",
        )
        proteinas = st.number_input(
            "Proteínas (g)",
            min_value=0,
            value=valores.get("proteinas"),
            step=1,
            key=f"{prefix}_proteinas",
        )
        carbohidratos = st.number_input(
            "Carbohidratos (g)",
            min_value=0,
            value=valores.get("carbohidratos"),
            step=1,
            key=f"{prefix}_carbohidratos",
        )
        grasas = st.number_input(
            "Grasas (g)",
            min_value=0,
            value=valores.get("grasas"),
            step=1,
            key=f"{prefix}_grasas",
        )

        ingredientes_texto = st.text_area(
            "Ingredientes *",
            value="\n".join(valores.get("ingredientes") or []),
            help="Un ingrediente por línea",
            height=120,
            key=f"{prefix}_ingredientes",
        )
        instrucciones = st.text_area(
            "Instrucciones",
            value=valores.get("instrucciones") or "",
            key=f"{prefix}_instrucciones",
        )

        enviado = st.form_submit_button(texto_submit, type="primary", use_container_width=True)

    if not enviado:
        return None

    errores = []
    titulo_limpio = titulo.strip()
    if not titulo_limpio:
        errores.append("El título es obligatorio.")

    ingredientes = [linea.strip() for linea in ingredientes_texto.splitlines() if linea.strip()]
    if not ingredientes:
        errores.append("Debes indicar al menos un ingrediente.")

    if errores:
        for error in errores:
            st.error(error)
        return None

    return {
        "titulo": titulo_limpio,
        "descripcion": descripcion.strip() or None,
        "categoria": categoria,
        "tiempo_preparacion": int(tiempo_preparacion) or None,
        "calorias": int(calorias) if calorias is not None else None,
        "proteinas": int(proteinas) if proteinas is not None else None,
        "carbohidratos": int(carbohidratos) if carbohidratos is not None else None,
        "grasas": int(grasas) if grasas is not None else None,
        "ingredientes": ingredientes,
        "instrucciones": instrucciones.strip() or None,
    }
