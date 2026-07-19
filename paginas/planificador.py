"""Página Planificador: menú semanal por tipo de comida, con notas."""

from datetime import date, timedelta

import streamlit as st

import database
import planificacion
from paginas import comun

TIPOS_COMIDA = ("Desayuno", "Almuerzo", "Merienda", "Cena")


def render() -> None:
    """Renderiza la página Planificador."""
    st.title("📅 Planificador")

    hoy = date.today()
    if "planificador_lunes" not in st.session_state:
        st.session_state["planificador_lunes"] = comun.lunes_de_la_semana(hoy)

    _navegacion_semana(hoy)

    lunes = st.session_state["planificador_lunes"]
    domingo = lunes + timedelta(days=6)
    st.caption(_texto_rango_semana(lunes, domingo))

    try:
        recetas = comun.recetas_cacheadas()
    except Exception as error:
        recetas = []
        st.error(f"No se pudieron cargar las recetas: {error}")

    if not recetas:
        st.info(
            "Todavía no tienes recetas guardadas. Crea alguna en el Recetario "
            "para poder planificarla aquí (mientras tanto puedes seguir "
            "añadiendo notas sin receta)."
        )

    try:
        comidas_semana = comun.menu_rango_cacheado(lunes, domingo)
    except Exception as error:
        comidas_semana = []
        st.error(f"No se pudo cargar el menú de la semana: {error}")

    recetas_por_id = {r["id"]: r for r in recetas}
    comidas_por_fecha: dict[str, list[dict]] = {}
    for comida in comidas_semana:
        comidas_por_fecha.setdefault(comida["fecha"], []).append(comida)

    for dia in planificacion.dias_de_semana(lunes):
        _seccion_dia(
            dia,
            hoy,
            comidas_por_fecha.get(dia.isoformat(), []),
            recetas,
            recetas_por_id,
        )


def _navegacion_semana(hoy: date) -> None:
    """Botones de navegación entre semanas (siempre fuerzan un rerun)."""
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("← Anterior", use_container_width=True):
            st.session_state["planificador_lunes"] -= timedelta(days=7)
            st.rerun()
    with col2:
        if st.button("Hoy", use_container_width=True):
            st.session_state["planificador_lunes"] = comun.lunes_de_la_semana(hoy)
            st.rerun()
    with col3:
        if st.button("Siguiente →", use_container_width=True):
            st.session_state["planificador_lunes"] += timedelta(days=7)
            st.rerun()


def _texto_rango_semana(lunes: date, domingo: date) -> str:
    """Compone el caption "Semana del D al D de <mes> de <año>", cruzando mes/año si hace falta."""
    mes_lunes = comun.MESES_ES[lunes.month - 1]
    mes_domingo = comun.MESES_ES[domingo.month - 1]

    if lunes.year == domingo.year and lunes.month == domingo.month:
        return f"Semana del {lunes.day} al {domingo.day} de {mes_lunes} de {domingo.year}"
    if lunes.year == domingo.year:
        return (
            f"Semana del {lunes.day} de {mes_lunes} al {domingo.day} de {mes_domingo} "
            f"de {domingo.year}"
        )
    return (
        f"Semana del {lunes.day} de {mes_lunes} de {lunes.year} al "
        f"{domingo.day} de {mes_domingo} de {domingo.year}"
    )


def _seccion_dia(
    dia: date,
    hoy: date,
    comidas_dia: list[dict],
    recetas: list[dict],
    recetas_por_id: dict[str, dict],
) -> None:
    """Renderiza el expander de un día con su formulario de planificación."""
    etiqueta = planificacion.etiqueta_dia(dia, hoy)

    with st.expander(etiqueta, expanded=(dia == hoy)):
        total_kcal = planificacion.total_calorias_dia(comidas_dia)
        if total_kcal is not None:
            st.caption(f"Total planificado: {total_kcal} kcal")

        comidas_por_tipo = {c["tipo_comida"]: c for c in comidas_dia}
        opciones_recetas = [None] + [r["id"] for r in recetas]

        def _formatear_receta(receta_id: str | None) -> str:
            if receta_id is None:
                return "— Sin receta —"
            receta = recetas_por_id.get(receta_id)
            if receta is None:
                return "(receta ya no disponible)"
            titulo = receta.get("titulo", "")
            calorias = receta.get("calorias")
            return f"{titulo} ({calorias} kcal)" if calorias is not None else titulo

        valores_formulario: dict[str, dict] = {}

        with st.form(key=f"planificador_form_{dia.isoformat()}"):
            for tipo in TIPOS_COMIDA:
                comida_existente = comidas_por_tipo.get(tipo)
                receta_id_actual = (
                    comida_existente.get("receta_id") if comida_existente else None
                )
                nota_actual = (
                    comida_existente.get("nota_adicional") if comida_existente else None
                )

                indice = (
                    opciones_recetas.index(receta_id_actual)
                    if receta_id_actual in opciones_recetas
                    else 0
                )

                receta_elegida = st.selectbox(
                    tipo,
                    options=opciones_recetas,
                    index=indice,
                    format_func=_formatear_receta,
                    key=f"planificador_{dia.isoformat()}_{tipo}_receta",
                )
                nota = st.text_input(
                    "Nota (opcional)",
                    value=nota_actual or "",
                    key=f"planificador_{dia.isoformat()}_{tipo}_nota",
                )
                valores_formulario[tipo] = {
                    "receta_id": receta_elegida,
                    "nota_adicional": nota,
                }

            enviado = st.form_submit_button(
                "💾 Guardar día", type="primary", use_container_width=True
            )

        if enviado:
            _guardar_dia(dia, comidas_dia, valores_formulario)


def _guardar_dia(dia: date, comidas_dia: list[dict], nuevas: dict[str, dict]) -> None:
    """Calcula el diff con `planificacion.cambios_comidas_dia` y lo persiste en BD."""
    previas = {
        c["tipo_comida"]: {
            "receta_id": c.get("receta_id"),
            "nota_adicional": c.get("nota_adicional"),
        }
        for c in comidas_dia
    }

    a_guardar, a_eliminar = planificacion.cambios_comidas_dia(previas, nuevas)

    try:
        for cambio in a_guardar:
            database.guardar_comida(
                dia.isoformat(),
                cambio["tipo_comida"],
                cambio["receta_id"],
                cambio["nota_adicional"],
            )
        for tipo in a_eliminar:
            database.eliminar_comida(dia.isoformat(), tipo)

        comun.limpiar_cache()

        if a_guardar or a_eliminar:
            st.success(
                f"Día guardado: {len(a_guardar)} actualizadas, {len(a_eliminar)} eliminadas."
            )
        else:
            st.success("Sin cambios que guardar.")
        st.rerun()
    except Exception as error:
        st.error(f"No se pudo guardar el día: {error}")
