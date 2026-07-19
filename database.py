"""
Módulo de acceso a datos (Supabase) para la app personal de menús, recetas y salud.

Este módulo NO depende de Streamlit ni de ninguna capa de UI: expone únicamente
funciones CRUD sobre las 5 tablas del esquema (ver db/001_esquema_inicial.sql),
usando el cliente oficial `supabase-py`. Las excepciones de la API (APIError)
se propagan sin capturar; solo se valida en local lo que los CHECK del esquema
ya restringen, para fallar rápido con un mensaje claro antes de golpear la red.
"""

import os

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

# Valores permitidos por los CHECK del esquema (db/001_esquema_inicial.sql)
TIPOS_COMIDA = ("Desayuno", "Almuerzo", "Merienda", "Cena")
INTENSIDADES = ("Alta", "Media", "Baja")

_client: Client | None = None


def _validar_rango_fechas(fecha_desde: str | None, fecha_hasta: str | None) -> None:
    """Valida que fecha_desde no sea posterior a fecha_hasta cuando ambas están presentes.

    Las fechas usadas en este módulo siempre llegan en formato ISO 8601
    (YYYY-MM-DD o timestamp ISO), donde el orden lexicográfico de los strings
    coincide con el orden cronológico: comparar los strings directamente
    (fecha_desde > fecha_hasta) es válido y evita tener que parsear fechas.
    """
    if fecha_desde is not None and fecha_hasta is not None and fecha_desde > fecha_hasta:
        raise ValueError(
            f"Rango de fechas inválido: fecha_desde ({fecha_desde!r}) es posterior "
            f"a fecha_hasta ({fecha_hasta!r})."
        )


def get_client() -> Client:
    """Devuelve el cliente de Supabase, creándolo una sola vez (singleton de módulo)."""
    global _client
    if _client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SECRET_KEY")
        if not url or not key:
            raise RuntimeError(
                "Faltan las variables de entorno SUPABASE_URL y/o SUPABASE_SECRET_KEY. "
                "Copia .env.example a .env y rellena tus credenciales de Supabase."
            )
        _client = create_client(url, key)
    return _client


# -----------------------------------------------------------------------------
# 1. recetas
# -----------------------------------------------------------------------------

def crear_receta(receta: dict) -> dict:
    """Inserta una nueva receta y devuelve el registro creado."""
    respuesta = get_client().table("recetas").insert(receta).execute()
    return respuesta.data[0]


def obtener_recetas(categoria: str | None = None) -> list[dict]:
    """Devuelve las recetas ordenadas por título, opcionalmente filtradas por categoría."""
    consulta = get_client().table("recetas").select("*").order("titulo")
    if categoria is not None:
        consulta = consulta.eq("categoria", categoria)
    return consulta.execute().data


def obtener_receta(receta_id: str) -> dict | None:
    """Devuelve una receta por id, o None si no existe."""
    respuesta = get_client().table("recetas").select("*").eq("id", receta_id).execute()
    return respuesta.data[0] if respuesta.data else None


def actualizar_receta(receta_id: str, cambios: dict) -> dict:
    """Actualiza los campos indicados de una receta y devuelve el registro actualizado."""
    respuesta = (
        get_client().table("recetas").update(cambios).eq("id", receta_id).execute()
    )
    if not respuesta.data:
        raise ValueError(f"No existe ninguna receta con id {receta_id!r}.")
    return respuesta.data[0]


def eliminar_receta(receta_id: str) -> None:
    """Elimina una receta por id (los menús que la referencian quedan con receta_id=null)."""
    get_client().table("recetas").delete().eq("id", receta_id).execute()


# -----------------------------------------------------------------------------
# 2. menus_semanales
# -----------------------------------------------------------------------------

def guardar_comida(
    fecha: str,
    tipo_comida: str,
    receta_id: str | None = None,
    nota_adicional: str | None = None,
) -> dict:
    """Asigna (o reasigna) una comida para una fecha y tipo de comida dados.

    Hace upsert sobre la constraint unique(fecha, tipo_comida): si ya existe
    una comida planificada para esa fecha y tipo, la sobrescribe.
    """
    if tipo_comida not in TIPOS_COMIDA:
        raise ValueError(
            f"tipo_comida inválido: {tipo_comida!r}. Debe ser uno de {TIPOS_COMIDA}."
        )
    registro = {
        "fecha": fecha,
        "tipo_comida": tipo_comida,
        "receta_id": receta_id,
        "nota_adicional": nota_adicional,
    }
    respuesta = (
        get_client()
        .table("menus_semanales")
        .upsert(registro, on_conflict="fecha,tipo_comida")
        .execute()
    )
    return respuesta.data[0]


def obtener_menu_rango(fecha_desde: str, fecha_hasta: str) -> list[dict]:
    """Devuelve las comidas planificadas entre dos fechas (incluidas), con su receta asociada."""
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    respuesta = (
        get_client()
        .table("menus_semanales")
        .select("*, recetas(*)")
        .gte("fecha", fecha_desde)
        .lte("fecha", fecha_hasta)
        .order("fecha")
        .execute()
    )
    return respuesta.data


def eliminar_comida(fecha: str, tipo_comida: str) -> None:
    """Elimina la comida planificada para una fecha y tipo de comida concretos."""
    (
        get_client()
        .table("menus_semanales")
        .delete()
        .eq("fecha", fecha)
        .eq("tipo_comida", tipo_comida)
        .execute()
    )


# -----------------------------------------------------------------------------
# 3. lista_compra
# -----------------------------------------------------------------------------

def agregar_item(
    item: str, cantidad: str | None = None, categoria: str | None = None
) -> dict:
    """Añade un nuevo item a la lista de la compra y devuelve el registro creado."""
    registro = {"item": item, "cantidad": cantidad, "categoria": categoria}
    respuesta = get_client().table("lista_compra").insert(registro).execute()
    return respuesta.data[0]


def obtener_lista(solo_pendientes: bool = False) -> list[dict]:
    """Devuelve la lista de la compra ordenada por categoría e item.

    Si solo_pendientes es True, excluye los items ya marcados como comprados.
    """
    consulta = get_client().table("lista_compra").select("*").order("categoria").order("item")
    if solo_pendientes:
        consulta = consulta.eq("comprado", False)
    return consulta.execute().data


def marcar_comprado(item_id: str, comprado: bool = True) -> dict:
    """Marca (o desmarca) un item de la lista como comprado."""
    respuesta = (
        get_client()
        .table("lista_compra")
        .update({"comprado": comprado})
        .eq("id", item_id)
        .execute()
    )
    if not respuesta.data:
        raise ValueError(f"No existe ningún item de la lista de la compra con id {item_id!r}.")
    return respuesta.data[0]


def eliminar_item(item_id: str) -> None:
    """Elimina un item de la lista de la compra."""
    get_client().table("lista_compra").delete().eq("id", item_id).execute()


def vaciar_comprados() -> None:
    """Elimina todos los items de la lista de la compra ya marcados como comprados."""
    get_client().table("lista_compra").delete().eq("comprado", True).execute()


# -----------------------------------------------------------------------------
# 4. metricas_salud
# -----------------------------------------------------------------------------

def registrar_metricas(
    fecha: str,
    peso: float | None = None,
    altura: float | None = None,
    porcentaje_grasa: float | None = None,
    perimetro_cintura: float | None = None,
    notas: str | None = None,
) -> dict:
    """Registra (o actualiza) las métricas de salud de un día.

    Hace upsert sobre la columna unique "fecha": un único registro por día.
    Los campos con valor None no se incluyen en el payload, para no
    sobrescribir con null valores ya existentes al reregistrar el mismo día.
    """
    registro = {"fecha": fecha}
    opcionales = {
        "peso": peso,
        "altura": altura,
        "porcentaje_grasa": porcentaje_grasa,
        "perimetro_cintura": perimetro_cintura,
        "notas": notas,
    }
    registro.update({k: v for k, v in opcionales.items() if v is not None})

    respuesta = (
        get_client()
        .table("metricas_salud")
        .upsert(registro, on_conflict="fecha")
        .execute()
    )
    return respuesta.data[0]


def eliminar_metricas(fecha: str) -> None:
    """Elimina el registro de métricas de salud de una fecha concreta."""
    get_client().table("metricas_salud").delete().eq("fecha", fecha).execute()


def obtener_historico_salud(
    fecha_desde: str | None = None, fecha_hasta: str | None = None
) -> list[dict]:
    """Devuelve el histórico de métricas de salud ordenado por fecha, con filtros opcionales."""
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    consulta = get_client().table("metricas_salud").select("*").order("fecha")
    if fecha_desde is not None:
        consulta = consulta.gte("fecha", fecha_desde)
    if fecha_hasta is not None:
        consulta = consulta.lte("fecha", fecha_hasta)
    return consulta.execute().data


# -----------------------------------------------------------------------------
# 5. actividad_deporte
# -----------------------------------------------------------------------------

def registrar_actividad(
    tipo_actividad: str,
    duracion_minutos: int,
    fecha: str | None = None,
    intensidad: str | None = None,
    volumen_total_kg: float | None = None,
    comentarios: str | None = None,
) -> dict:
    """Registra una nueva sesión de actividad deportiva.

    Si fecha es None, no se envía en el payload y la BD asigna now() por defecto.
    """
    if intensidad is not None and intensidad not in INTENSIDADES:
        raise ValueError(
            f"intensidad inválida: {intensidad!r}. Debe ser una de {INTENSIDADES}."
        )
    registro = {
        "tipo_actividad": tipo_actividad,
        "duracion_minutos": duracion_minutos,
        "intensidad": intensidad,
        "volumen_total_kg": volumen_total_kg,
        "comentarios": comentarios,
    }
    if fecha is not None:
        registro["fecha"] = fecha

    respuesta = get_client().table("actividad_deporte").insert(registro).execute()
    return respuesta.data[0]


def obtener_historico_deporte(
    fecha_desde: str | None = None, fecha_hasta: str | None = None
) -> list[dict]:
    """Devuelve el histórico de actividad deportiva ordenado por fecha descendente."""
    _validar_rango_fechas(fecha_desde, fecha_hasta)
    consulta = get_client().table("actividad_deporte").select("*").order("fecha", desc=True)
    if fecha_desde is not None:
        consulta = consulta.gte("fecha", fecha_desde)
    if fecha_hasta is not None:
        consulta = consulta.lte("fecha", fecha_hasta)
    return consulta.execute().data


def eliminar_actividad(actividad_id: str) -> None:
    """Elimina una sesión de actividad deportiva por id."""
    get_client().table("actividad_deporte").delete().eq("id", actividad_id).execute()
