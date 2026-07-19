"""Lógica pura de estadísticas de salud y deporte para la página Métricas.

Módulo puro (no depende de Streamlit ni de Plotly, aunque sí usa Pandas para
dar forma a los datos para los gráficos) que filtra registros por período,
construye las series temporales de salud, calcula el resumen con deltas del
último registro y agrupa los minutos de actividad deportiva por semana.

Al ser independiente de la UI, este módulo sigue el patrón "agent-ready" de
`filtros.py` y `planificacion.py` (decisión D9 de docs/decisiones.md): un
agente de IA podría llamar a estas mismas funciones para analizar la
evolución de las métricas de salud o del entrenamiento sin depender de
Streamlit.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

MESES_CORTOS_ES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


def _parsear_fecha(valor: str | None) -> date | None:
    """Extrae la parte de fecha (date) de una cadena ISO, con o sin hora.

    Devuelve None si `valor` es None o no se puede interpretar como fecha.
    """
    if not valor:
        return None
    try:
        return date.fromisoformat(str(valor)[:10])
    except ValueError:
        return None


def filtrar_por_periodo(
    registros: list[dict], dias: int | None, hoy: date
) -> list[dict]:
    """Filtra una lista de registros a los que caen en los últimos `dias` días.

    Args:
        registros: lista de diccionarios con una clave "fecha" (cadena ISO,
            con o sin componente de hora, p. ej. "2026-07-18" o
            "2026-07-18T10:00:00+00:00").
        dias: tamaño de la ventana hacia atrás desde `hoy`. Si es None, se
            devuelven todos los registros sin filtrar.
        hoy: fecha considerada "hoy" (se pasa explícitamente para que la
            función sea pura y fácil de testear).

    Returns:
        La sublista de `registros` cuya fecha cae en el intervalo cerrado
        [hoy - dias, hoy]. Los registros sin fecha interpretable se excluyen.
    """
    if dias is None:
        return list(registros)

    desde = hoy - timedelta(days=dias)
    resultado = []
    for registro in registros:
        fecha = _parsear_fecha(registro.get("fecha"))
        if fecha is not None and desde <= fecha <= hoy:
            resultado.append(registro)
    return resultado


def series_salud(metricas: list[dict]) -> pd.DataFrame:
    """Construye el DataFrame de series temporales de salud para los gráficos.

    Args:
        metricas: lista de registros de `metricas_salud` (con claves "fecha",
            "peso", "porcentaje_grasa", "perimetro_cintura").

    Returns:
        DataFrame con columnas "Fecha" (datetime64), "Peso",
        "Porcentaje_Grasa" y "Cintura" (float, NaN si el dato falta),
        ordenado por "Fecha" ascendente.
    """
    columnas = ["Fecha", "Peso", "Porcentaje_Grasa", "Cintura"]
    filas = [
        {
            "Fecha": m.get("fecha"),
            "Peso": m.get("peso"),
            "Porcentaje_Grasa": m.get("porcentaje_grasa"),
            "Cintura": m.get("perimetro_cintura"),
        }
        for m in metricas
    ]
    if not filas:
        return pd.DataFrame(columns=columnas)

    df = pd.DataFrame(filas, columns=columnas)
    df["Fecha"] = pd.to_datetime(df["Fecha"])
    for columna in ("Peso", "Porcentaje_Grasa", "Cintura"):
        df[columna] = pd.to_numeric(df[columna], errors="coerce")
    return df.sort_values("Fecha").reset_index(drop=True)


def _valor_y_delta(
    ordenados: list[dict], indice_actual: int, campo: str
) -> tuple[float | None, float | None]:
    """Devuelve (valor actual, delta) de `campo` para el registro en `indice_actual`.

    El delta se calcula contra el valor de ese mismo campo en el registro
    anterior más reciente que lo tenga informado (no necesariamente el
    registro inmediatamente anterior). Si el actual no tiene el campo, o
    ningún registro anterior lo tiene, el elemento correspondiente es None.
    """
    valor_actual = ordenados[indice_actual].get(campo)
    if valor_actual is None:
        return None, None

    for anterior in reversed(ordenados[:indice_actual]):
        valor_anterior = anterior.get(campo)
        if valor_anterior is not None:
            return valor_actual, valor_actual - valor_anterior
    return valor_actual, None


def resumen_salud(metricas: list[dict]) -> dict | None:
    """Resume el registro de salud más reciente junto con sus deltas.

    Args:
        metricas: lista de registros de `metricas_salud` (no necesita venir
            ordenada; esta función ordena internamente por "fecha").

    Returns:
        None si `metricas` está vacía. En caso contrario, un dict con:
            "fecha", "peso", "delta_peso", "porcentaje_grasa", "delta_grasa",
            "perimetro_cintura", "delta_cintura".
        Cada delta es `valor_actual - valor_del_registro_anterior_más_reciente
        _que_tenga_ese_campo`, o None si no existe tal registro anterior o si
        el propio registro actual no tiene ese campo.
    """
    if not metricas:
        return None

    ordenados = sorted(metricas, key=lambda m: m.get("fecha") or "")
    ultimo_indice = len(ordenados) - 1

    peso, delta_peso = _valor_y_delta(ordenados, ultimo_indice, "peso")
    grasa, delta_grasa = _valor_y_delta(ordenados, ultimo_indice, "porcentaje_grasa")
    cintura, delta_cintura = _valor_y_delta(
        ordenados, ultimo_indice, "perimetro_cintura"
    )

    return {
        "fecha": ordenados[ultimo_indice].get("fecha"),
        "peso": peso,
        "delta_peso": delta_peso,
        "porcentaje_grasa": grasa,
        "delta_grasa": delta_grasa,
        "perimetro_cintura": cintura,
        "delta_cintura": delta_cintura,
    }


def etiqueta_semana(lunes: date) -> str:
    """Formatea el rango de una semana natural (lunes a domingo) en español.

    Args:
        lunes: fecha del lunes de la semana a etiquetar.

    Returns:
        Si el lunes y el domingo caen en el mismo mes: "13-19 jul" (para
        `date(2026, 7, 13)`). Si la semana cruza de mes: "29 jun - 5 jul"
        (para `date(2026, 6, 29)`). Funciona igual si además cruza de año:
        "29 dic - 4 ene" (para `date(2025, 12, 29)`).
    """
    domingo = lunes + timedelta(days=6)
    mes_lunes = MESES_CORTOS_ES[lunes.month - 1]
    if lunes.month == domingo.month:
        return f"{lunes.day}-{domingo.day} {mes_lunes}"
    mes_domingo = MESES_CORTOS_ES[domingo.month - 1]
    return f"{lunes.day} {mes_lunes} - {domingo.day} {mes_domingo}"


def minutos_por_semana(
    actividades: list[dict], hoy: date, num_semanas: int = 12
) -> pd.DataFrame:
    """Agrupa los minutos de actividad deportiva por semana natural y tipo.

    Args:
        actividades: lista de registros de `actividad_deporte` (con claves
            "fecha", "tipo_actividad", "duracion_minutos").
        hoy: fecha considerada "hoy"; fija la semana final del rango.
        num_semanas: número de semanas naturales (lunes a domingo) a cubrir,
            terminando en la semana de `hoy`.

    Returns:
        DataFrame con columnas "Semana" (date del lunes de cada semana, para
        ordenar), "Semana_Etiqueta" (str con el rango de la semana, ver
        `etiqueta_semana`), "Tipo_Actividad" y "Minutos" (suma de
        duracion_minutos), con una fila por combinación (semana, tipo) que
        tenga alguna actividad, ordenado por "Semana" ascendente.

        Decisión de diseño: las semanas sin ninguna actividad (de ningún
        tipo) simplemente no generan fila; no se rellenan con ceros. El eje
        del gráfico es categórico ("Semana_Etiqueta"), así que no hace falta
        que este DataFrame contenga filas "vacías" para mantener continuidad.
    """
    columnas = ["Semana", "Semana_Etiqueta", "Tipo_Actividad", "Minutos"]

    lunes_actual = hoy - timedelta(days=hoy.weekday())
    lunes_inicio = lunes_actual - timedelta(weeks=num_semanas - 1)

    filas = []
    for actividad in actividades:
        fecha = _parsear_fecha(actividad.get("fecha"))
        if fecha is None:
            continue
        lunes_semana = fecha - timedelta(days=fecha.weekday())
        if lunes_inicio <= lunes_semana <= lunes_actual:
            filas.append(
                {
                    "Semana": lunes_semana,
                    "Semana_Etiqueta": etiqueta_semana(lunes_semana),
                    "Tipo_Actividad": actividad.get("tipo_actividad"),
                    "Minutos": actividad.get("duracion_minutos") or 0,
                }
            )

    if not filas:
        return pd.DataFrame(columns=columnas)

    df = pd.DataFrame(filas, columns=columnas)
    agrupado = df.groupby(
        ["Semana", "Semana_Etiqueta", "Tipo_Actividad"], as_index=False
    )["Minutos"].sum()
    return agrupado.sort_values(["Semana", "Tipo_Actividad"]).reset_index(drop=True)
