"""Página Métricas: registro y visualización de salud y de actividad deportiva."""

from datetime import date

import plotly.express as px
import streamlit as st

import database
import estadisticas
from paginas import comun

SUGERENCIAS_TIPO_ACTIVIDAD = [
    "Fuerza",
    "Running",
    "Ciclismo",
    "Natación",
    "Caminata",
    "Fútbol",
    "Yoga",
]
INTENSIDADES = ["Alta", "Media", "Baja"]

PERIODOS: dict[str, int | None] = {
    "Últimos 30 días": 30,
    "Últimos 90 días": 90,
    "Último año": 365,
    "Todo": None,
}


def render() -> None:
    """Renderiza la página Métricas, con pestañas Salud y Deporte."""
    st.title("📈 Métricas")

    tab_salud, tab_deporte = st.tabs(["🩺 Salud", "🏋️ Deporte"])
    with tab_salud:
        _tab_salud()
    with tab_deporte:
        _tab_deporte()


# -----------------------------------------------------------------------------
# Pestaña Salud
# -----------------------------------------------------------------------------


def _tab_salud() -> None:
    _form_registrar_metricas()

    try:
        metricas = comun.historico_salud_cacheado()
    except Exception as error:
        metricas = []
        st.error(f"No se pudo cargar el histórico de salud: {error}")

    if not metricas:
        st.info(
            "Todavía no tienes métricas registradas. "
            "¡Registra la primera con el formulario de arriba!"
        )
        return

    _resumen_metricas(metricas)

    etiqueta_periodo = st.selectbox(
        "Período", list(PERIODOS.keys()), key="metricas_salud_periodo"
    )
    dias = PERIODOS[etiqueta_periodo]
    filtradas = estadisticas.filtrar_por_periodo(metricas, dias, date.today())

    _graficos_salud(filtradas)

    _registros_recientes_salud(metricas)


def _form_registrar_metricas() -> None:
    with st.expander("➕ Registrar métricas"):
        with st.form(key="metricas_form_salud", clear_on_submit=True):
            fecha = st.date_input(
                "Fecha", value=date.today(), key="metricas_salud_fecha"
            )
            peso = st.number_input(
                "Peso (kg)",
                value=None,
                min_value=0.0,
                step=0.1,
                format="%.1f",
                key="metricas_salud_peso",
            )
            porcentaje_grasa = st.number_input(
                "Porcentaje de grasa (%)",
                value=None,
                min_value=0.0,
                step=0.1,
                format="%.1f",
                key="metricas_salud_grasa",
            )
            perimetro_cintura = st.number_input(
                "Perímetro de cintura (cm)",
                value=None,
                min_value=0.0,
                step=0.1,
                format="%.1f",
                key="metricas_salud_cintura",
            )
            altura = st.number_input(
                "Altura (m)",
                value=None,
                step=0.01,
                format="%.2f",
                help="Rara vez cambia; normalmente basta con registrarla una vez.",
                key="metricas_salud_altura",
            )
            notas = st.text_input("Notas", key="metricas_salud_notas")

            enviado = st.form_submit_button(
                "💾 Registrar", type="primary", use_container_width=True
            )

        if enviado:
            hay_contenido = any(
                valor is not None and valor != ""
                for valor in (peso, porcentaje_grasa, perimetro_cintura, altura, notas)
            )
            if not hay_contenido:
                st.error("Informa al menos un campo.")
            else:
                try:
                    database.registrar_metricas(
                        fecha.isoformat(),
                        peso=peso,
                        altura=altura,
                        porcentaje_grasa=porcentaje_grasa,
                        perimetro_cintura=perimetro_cintura,
                        notas=notas.strip() or None,
                    )
                    comun.limpiar_cache()
                    st.success("Métricas registradas correctamente.")
                    st.rerun()
                except Exception as error:
                    st.error(f"No se pudieron registrar las métricas: {error}")


def _formato_delta(delta: float | None) -> str | None:
    """Formatea un delta como "+0.3" / "-0.5", o None si no hay delta."""
    if delta is None:
        return None
    return f"{delta:+.1f}"


def _resumen_metricas(metricas: list[dict]) -> None:
    """Fila de st.metric con el último registro y sus deltas (estadisticas.resumen_salud)."""
    resumen = estadisticas.resumen_salud(metricas)
    if resumen is None:
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        if resumen["peso"] is not None:
            st.metric(
                "Peso",
                f"{resumen['peso']:.1f} kg",
                _formato_delta(resumen["delta_peso"]),
                delta_color="inverse",
            )
    with col2:
        if resumen["porcentaje_grasa"] is not None:
            st.metric(
                "% Grasa",
                f"{resumen['porcentaje_grasa']:.1f}%",
                _formato_delta(resumen["delta_grasa"]),
                delta_color="inverse",
            )
    with col3:
        if resumen["perimetro_cintura"] is not None:
            st.metric(
                "Cintura",
                f"{resumen['perimetro_cintura']:.1f} cm",
                _formato_delta(resumen["delta_cintura"]),
                delta_color="inverse",
            )


def _graficos_salud(registros: list[dict]) -> None:
    """Un gráfico Plotly por medida (Peso, % Grasa, Cintura), sin ejes duales ni leyenda."""
    if not registros:
        st.info("No hay registros en el período seleccionado.")
        return

    df = estadisticas.series_salud(registros)
    medidas = [
        ("Peso", "Peso (kg)"),
        ("Porcentaje_Grasa", "% Grasa corporal"),
        ("Cintura", "Cintura (cm)"),
    ]
    for columna, titulo in medidas:
        serie = df[["Fecha", columna]].dropna(subset=[columna])
        if len(serie) < 2:
            continue
        fig = px.line(serie, x="Fecha", y=columna, markers=True, title=titulo)
        fig.update_traces(line=dict(width=2))
        fig.update_layout(showlegend=False, yaxis_title=None, xaxis_title=None)
        st.plotly_chart(fig, width="stretch")


def _registros_recientes_salud(metricas: list[dict]) -> None:
    with st.expander("Registros recientes"):
        recientes = sorted(
            metricas, key=lambda m: m.get("fecha") or "", reverse=True
        )[:10]
        for registro in recientes:
            _fila_metrica(registro)


def _fila_metrica(registro: dict) -> None:
    fecha = registro["fecha"]
    partes = [fecha]
    peso = registro.get("peso")
    grasa = registro.get("porcentaje_grasa")
    cintura = registro.get("perimetro_cintura")
    if peso is not None:
        partes.append(f"{peso:.1f} kg")
    if grasa is not None:
        partes.append(f"{grasa:.1f}%")
    if cintura is not None:
        partes.append(f"{cintura:.0f} cm")
    texto = " · ".join(partes)

    col1, col2 = st.columns([6, 1])
    with col1:
        st.write(texto)
        notas = registro.get("notas")
        if notas:
            st.caption(notas)
    with col2:
        eliminar = st.button("🗑️", key=f"metricas_salud_eliminar_{fecha}")

    if eliminar:
        try:
            database.eliminar_metricas(fecha)
            comun.limpiar_cache()
            st.rerun()
        except Exception as error:
            st.error(f"No se pudo eliminar el registro: {error}")


# -----------------------------------------------------------------------------
# Pestaña Deporte
# -----------------------------------------------------------------------------


def _tab_deporte() -> None:
    try:
        actividades = comun.historico_deporte_cacheado()
    except Exception as error:
        actividades = []
        st.error(f"No se pudo cargar el histórico de deporte: {error}")

    opciones_tipo = _tipos_actividad_opciones(actividades)
    _form_registrar_actividad(opciones_tipo)

    _grafico_minutos_semana(actividades)

    _actividades_recientes(actividades)


def _tipos_actividad_opciones(actividades: list[dict]) -> list[str]:
    """Sugerencias fijas + tipos ya usados en el histórico, sin duplicados."""
    opciones = list(SUGERENCIAS_TIPO_ACTIVIDAD)
    existentes = sorted(
        {a["tipo_actividad"] for a in actividades if a.get("tipo_actividad")}
    )
    for tipo in existentes:
        if tipo not in opciones:
            opciones.append(tipo)
    return opciones


def _form_registrar_actividad(opciones_tipo: list[str]) -> None:
    with st.expander("➕ Registrar actividad"):
        with st.form(key="metricas_form_deporte", clear_on_submit=True):
            tipo = st.selectbox(
                "Tipo de actividad *",
                options=opciones_tipo,
                index=None,
                accept_new_options=True,
                key="metricas_deporte_tipo",
            )
            duracion = st.number_input(
                "Duración (min) *",
                min_value=1,
                step=5,
                value=None,
                key="metricas_deporte_duracion",
            )
            fecha = st.date_input(
                "Fecha", value=date.today(), key="metricas_deporte_fecha"
            )
            intensidad = st.selectbox(
                "Intensidad",
                options=INTENSIDADES,
                index=None,
                key="metricas_deporte_intensidad",
            )
            volumen = st.number_input(
                "Volumen total (kg)",
                value=None,
                help="Útil para fuerza.",
                key="metricas_deporte_volumen",
            )
            comentarios = st.text_input("Comentarios", key="metricas_deporte_comentarios")

            enviado = st.form_submit_button(
                "💾 Registrar", type="primary", use_container_width=True
            )

        if enviado:
            if not tipo or duracion is None:
                st.error("El tipo de actividad y la duración son obligatorios.")
            else:
                try:
                    database.registrar_actividad(
                        tipo,
                        int(duracion),
                        fecha=fecha.isoformat(),
                        intensidad=intensidad,
                        volumen_total_kg=volumen,
                        comentarios=comentarios.strip() or None,
                    )
                    comun.limpiar_cache()
                    st.success("Actividad registrada correctamente.")
                    st.rerun()
                except Exception as error:
                    st.error(f"No se pudo registrar la actividad: {error}")


def _grafico_minutos_semana(actividades: list[dict]) -> None:
    """Barras apiladas de minutos por semana y tipo (últimas 12 semanas)."""
    df = estadisticas.minutos_por_semana(actividades, date.today(), num_semanas=12)
    if df.empty:
        return

    tipos_ordenados = sorted(df["Tipo_Actividad"].unique())
    semanas_ordenadas = df["Semana_Etiqueta"].unique().tolist()
    fig = px.bar(
        df,
        x="Semana_Etiqueta",
        y="Minutos",
        color="Tipo_Actividad",
        category_orders={
            "Semana_Etiqueta": semanas_ordenadas,
            "Tipo_Actividad": tipos_ordenados,
        },
        title="Minutos de actividad por semana",
    )
    fig.update_layout(xaxis_title=None)
    if len(tipos_ordenados) >= 2:
        fig.update_layout(
            legend=dict(
                orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5,
                title=None,
            )
        )
    else:
        fig.update_layout(showlegend=False)
    st.plotly_chart(fig, width="stretch")


def _actividades_recientes(actividades: list[dict]) -> None:
    st.subheader("Actividades recientes")
    if not actividades:
        st.info(
            "Todavía no has registrado actividades. "
            "¡Registra la primera con el formulario de arriba!"
        )
        return
    for actividad in actividades[:10]:
        _fila_actividad(actividad)


def _fecha_corta(fecha_iso: str) -> str:
    """Formatea una fecha ISO (con hora) como "DD/MM"."""
    d = date.fromisoformat(str(fecha_iso)[:10])
    return f"{d.day:02d}/{d.month:02d}"


def _fila_actividad(actividad: dict) -> None:
    actividad_id = actividad["id"]
    partes = [_fecha_corta(actividad["fecha"]), actividad.get("tipo_actividad", "")]
    duracion = actividad.get("duracion_minutos")
    if duracion is not None:
        partes.append(f"{duracion} min")
    intensidad = actividad.get("intensidad")
    if intensidad:
        partes.append(intensidad)
    volumen = actividad.get("volumen_total_kg")
    if volumen is not None:
        partes.append(f"{volumen:.0f} kg")
    texto = " · ".join(p for p in partes if p)

    col1, col2 = st.columns([6, 1])
    with col1:
        st.write(texto)
        comentarios = actividad.get("comentarios")
        if comentarios:
            st.caption(comentarios)
    with col2:
        eliminar = st.button("🗑️", key=f"metricas_deporte_eliminar_{actividad_id}")

    if eliminar:
        try:
            database.eliminar_actividad(actividad_id)
            comun.limpiar_cache()
            st.rerun()
        except Exception as error:
            st.error(f"No se pudo eliminar la actividad: {error}")
