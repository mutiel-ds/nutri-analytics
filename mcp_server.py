"""
Servidor MCP (Model Context Protocol) local de nutri-analytics.

Expone la lógica de negocio de la app (módulos puros `database.py`, `filtros.py`
y `exporter.py`) como *tools* que un agente de IA puede invocar directamente,
sin pasar por la interfaz de Streamlit. Esto es posible gracias a la decisión
D9 (`docs/decisiones.md`): toda la lógica de negocio se escribió desde el
principio como funciones Python puras, tipadas y sin dependencias de UI, con
validaciones que lanzan `ValueError` con mensajes en español pensados para que
los lea (y actúe en consecuencia) un agente de IA.

Alcance de esta V1 (acordado con el usuario): **lectura + escritura, SIN
borrados**. No se exponen `eliminar_receta`, `eliminar_comida`,
`eliminar_item`, `vaciar_comprados` ni `eliminar_actividad`: un agente puede
consultar, crear y actualizar datos, pero no puede borrar nada. Si en el
futuro se decide exponer borrados, se añadirán como tools nuevas y explícitas.

Patrón de diseño para testabilidad: cada tool es una función normal de
módulo (con type hints y un docstring en español que es exactamente lo que
verá el agente de IA como descripción de la tool). Las funciones se registran
sobre la instancia `mcp` con `mcp.tool()(funcion)`. Los tests unitarios
(`tests/test_mcp_server.py`) llaman a las funciones directamente, sin pasar
por el protocolo MCP, reutilizando el patrón de mocks de Supabase de
`tests/test_database.py` (fixture `cliente_mock` sobre `database._client`).

Transporte: stdio (por defecto de FastMCP), pensado para que un cliente MCP
local (p. ej. Claude Desktop, Claude Code) lance este script como subproceso.

Cómo registrar este servidor en un cliente MCP (ejemplo de configuración):

    {
      "mcpServers": {
        "nutri-analytics": {
          "command": "uv",
          "args": ["run", "--directory", "C:/ruta/a/nutri-analytics", "python", "mcp_server.py"]
        }
      }
    }
"""

from __future__ import annotations

from datetime import date, timedelta

from mcp.server.fastmcp import FastMCP

import database
import exporter
from filtros import aplicar_filtros

mcp = FastMCP("nutri-analytics")

# Nombres de los días de la semana en español (weekday(): 0 = Lunes). Se
# duplica aquí (en vez de importarse de `planificacion.py`, que la define
# como constante privada `_DIAS_SEMANA_ES`) para no depender de un símbolo
# privado de otro módulo.
_DIAS_SEMANA_ES: tuple[str, ...] = (
    "Lunes",
    "Martes",
    "Miércoles",
    "Jueves",
    "Viernes",
    "Sábado",
    "Domingo",
)


# -----------------------------------------------------------------------------
# Recetas
# -----------------------------------------------------------------------------


def listar_recetas(filtros: list[dict] | None = None) -> list[dict]:
    """Devuelve el catálogo de recetas, opcionalmente filtrado.

    Sin argumentos devuelve todas las recetas (ordenadas por título). Si se
    pasa `filtros`, se aplican en modo aditivo (AND): una receta solo
    aparece en el resultado si cumple TODOS los filtros de la lista.

    Cada filtro es un diccionario con la forma:
        {"campo": str, "operador": str, "valor": Any}

    Campos válidos (y su tipo, que determina los operadores admitidos):
        - "categoria" (enum): operadores "=", "!=". El valor debe ser texto.
        - "tiempo_preparacion", "calorias", "proteinas", "carbohidratos",
          "grasas" (numérico): operadores "<", "<=", "=", ">=", ">". El
          valor debe ser int o float.
        - "ingredientes" (ingredientes): operadores "contiene", "no contiene".
          El valor debe ser texto; se busca como subcadena (sin distinguir
          mayúsculas/minúsculas) en cada línea de ingredientes de la receta.

    Ejemplos de filtro:
        {"campo": "calorias", "operador": "<", "valor": 1000}
        {"campo": "categoria", "operador": "=", "valor": "Desayuno"}
        {"campo": "ingredientes", "operador": "no contiene", "valor": "gluten"}

    Args:
        filtros: lista de filtros a aplicar (AND aditivo), o None / lista
            vacía para no filtrar.

    Returns:
        Lista de recetas (diccionarios) que cumplen todos los filtros.

    Raises:
        ValueError: si algún filtro tiene un campo, operador o tipo de
            valor no válido (ver `filtros.validar_filtro`).
    """
    recetas = database.obtener_recetas()
    if not filtros:
        return recetas
    return aplicar_filtros(recetas, filtros)


def crear_receta(
    titulo: str,
    ingredientes: list[str],
    descripcion: str | None = None,
    categoria: str | None = None,
    tiempo_preparacion: int | None = None,
    calorias: int | None = None,
    proteinas: int | None = None,
    carbohidratos: int | None = None,
    grasas: int | None = None,
    instrucciones: str | None = None,
) -> dict:
    """Crea una nueva receta en el catálogo.

    Args:
        titulo: nombre de la receta. Obligatorio, no puede estar vacío.
        ingredientes: lista de líneas de ingrediente (texto libre, p. ej.
            "200g de avena"). Obligatoria, no puede estar vacía.
        descripcion: descripción breve opcional.
        categoria: categoría opcional (p. ej. "Desayuno", "Comida", "Cena").
        tiempo_preparacion: tiempo de preparación opcional, en minutos.
        calorias, proteinas, carbohidratos, grasas: macros opcionales de la
            receta completa (no por ración), en kcal/gramos.
        instrucciones: pasos de preparación opcionales, como texto libre.

    Returns:
        El registro de la receta creada (incluye su "id").

    Raises:
        ValueError: si `titulo` está vacío (o solo espacios) o si
            `ingredientes` está vacía.
    """
    if not titulo or not titulo.strip():
        raise ValueError("El título de la receta no puede estar vacío.")
    if not ingredientes:
        raise ValueError("La receta debe tener al menos un ingrediente.")

    receta = {
        "titulo": titulo,
        "ingredientes": ingredientes,
        "descripcion": descripcion,
        "categoria": categoria,
        "tiempo_preparacion": tiempo_preparacion,
        "calorias": calorias,
        "proteinas": proteinas,
        "carbohidratos": carbohidratos,
        "grasas": grasas,
        "instrucciones": instrucciones,
    }
    return database.crear_receta(receta)


# -----------------------------------------------------------------------------
# Contexto temporal
# -----------------------------------------------------------------------------


def _contexto_fecha(hoy: date) -> dict:
    """Calcula el contexto temporal (día de la semana y límites de semana) a partir de `hoy`.

    Función auxiliar privada (no se registra como tool): separa el cálculo
    puro de `fecha_actual` para que los tests puedan ser deterministas
    inyectando una fecha fija en lugar de depender de `date.today()`. Las
    semanas van de lunes (weekday() == 0) a domingo.

    Args:
        hoy: fecha considerada "hoy".

    Returns:
        Dict con las claves "hoy", "dia_semana", "lunes_semana_actual",
        "domingo_semana_actual", "lunes_semana_siguiente" y
        "domingo_semana_siguiente" (ver `fecha_actual`).
    """
    lunes_semana_actual = hoy - timedelta(days=hoy.weekday())
    domingo_semana_actual = lunes_semana_actual + timedelta(days=6)
    lunes_semana_siguiente = lunes_semana_actual + timedelta(days=7)
    domingo_semana_siguiente = lunes_semana_siguiente + timedelta(days=6)
    return {
        "hoy": hoy.isoformat(),
        "dia_semana": _DIAS_SEMANA_ES[hoy.weekday()],
        "lunes_semana_actual": lunes_semana_actual.isoformat(),
        "domingo_semana_actual": domingo_semana_actual.isoformat(),
        "lunes_semana_siguiente": lunes_semana_siguiente.isoformat(),
        "domingo_semana_siguiente": domingo_semana_siguiente.isoformat(),
    }


def fecha_actual() -> dict:
    """Consulta esta tool ANTES de planificar comidas o interpretar expresiones
    relativas como "hoy", "mañana" o "la semana que viene": te da la fecha
    actual y los límites de la semana actual y la siguiente (las semanas van
    de lunes a domingo).

    Sin esta tool no hay forma de saber qué día es "hoy" ni de resolver
    expresiones relativas de fecha, lo que puede llevar a planificar
    comidas en la fecha equivocada.

    Returns:
        Dict con las claves:
            - "hoy": fecha actual, formato "YYYY-MM-DD".
            - "dia_semana": nombre del día actual en español (p. ej.
              "Domingo").
            - "lunes_semana_actual": fecha del lunes de la semana en curso,
              formato "YYYY-MM-DD".
            - "domingo_semana_actual": fecha del domingo de la semana en
              curso, formato "YYYY-MM-DD".
            - "lunes_semana_siguiente": fecha del lunes de la semana
              siguiente, formato "YYYY-MM-DD".
            - "domingo_semana_siguiente": fecha del domingo de la semana
              siguiente, formato "YYYY-MM-DD".
    """
    return _contexto_fecha(date.today())


# -----------------------------------------------------------------------------
# Menús
# -----------------------------------------------------------------------------


def consultar_menu(fecha_desde: str, fecha_hasta: str) -> list[dict]:
    """Devuelve las comidas planificadas entre dos fechas (ambas incluidas).

    Cada comida incluye la receta asociada embebida bajo la clave "recetas"
    (o null si la comida no tiene receta asignada, p. ej. si solo lleva
    `nota_adicional`).

    Si `fecha_desde`/`fecha_hasta` se derivan de una expresión relativa
    (p. ej. "esta semana" o "la semana que viene"), usa antes la tool
    `fecha_actual` para resolverlas correctamente.

    Args:
        fecha_desde: fecha inicial del rango, formato "YYYY-MM-DD".
        fecha_hasta: fecha final del rango (incluida), formato "YYYY-MM-DD".

    Returns:
        Lista de comidas planificadas, ordenadas por fecha.
    """
    return database.obtener_menu_rango(fecha_desde, fecha_hasta)


def planificar_comida(
    fecha: str,
    tipo_comida: str,
    receta_id: str | None = None,
    nota_adicional: str | None = None,
) -> dict:
    """Asigna (o reasigna) una comida a una fecha y tipo de comida.

    Hace upsert sobre la pareja (fecha, tipo_comida): si esa fecha y tipo de
    comida ya tenían una comida planificada, **reasignar la sobrescribe**
    por completo (incluida la nota_adicional, que si no se pasa queda a
    null).

    Si `fecha` se deriva de una expresión relativa (p. ej. "mañana" o "el
    lunes que viene"), usa antes la tool `fecha_actual` para resolverla
    correctamente.

    Args:
        fecha: fecha de la comida, formato "YYYY-MM-DD".
        tipo_comida: uno de los 4 valores válidos: "Desayuno", "Almuerzo",
            "Merienda", "Cena".
        receta_id: id de la receta asignada, o None para no asignar receta
            (p. ej. una comida libre descrita solo en `nota_adicional`).
        nota_adicional: nota de texto libre opcional (p. ej. una guarnición
            o una comida sin receta asociada).

    Returns:
        El registro de la comida planificada (creado o actualizado).

    Raises:
        ValueError: si `tipo_comida` no es uno de los 4 valores válidos.
    """
    return database.guardar_comida(
        fecha, tipo_comida, receta_id=receta_id, nota_adicional=nota_adicional
    )


# -----------------------------------------------------------------------------
# Lista de la compra
# -----------------------------------------------------------------------------


def consultar_lista_compra(solo_pendientes: bool = False) -> list[dict]:
    """Devuelve la lista de la compra, ordenada por categoría e item.

    Args:
        solo_pendientes: si es True, excluye los items ya marcados como
            comprados. Por defecto devuelve todos los items.

    Returns:
        Lista de items de la lista de la compra.
    """
    return database.obtener_lista(solo_pendientes=solo_pendientes)


def agregar_item_compra(
    item: str, cantidad: str | None = None, categoria: str | None = None
) -> dict:
    """Añade un nuevo item a la lista de la compra.

    Args:
        item: nombre del producto a comprar (p. ej. "Avena").
        cantidad: cantidad opcional, como texto libre (p. ej. "500g", "2").
        categoria: categoría opcional para agrupar en la lista (p. ej.
            "Frutas y verduras").

    Returns:
        El registro del item creado (incluye su "id" y "comprado": False).
    """
    return database.agregar_item(item, cantidad=cantidad, categoria=categoria)


def marcar_item_comprado(item_id: str, comprado: bool = True) -> dict:
    """Marca (o desmarca) un item de la lista de la compra como comprado.

    Args:
        item_id: id del item de la lista de la compra.
        comprado: True para marcarlo como comprado, False para desmarcarlo.
            Por defecto True.

    Returns:
        El registro del item actualizado.
    """
    return database.marcar_comprado(item_id, comprado=comprado)


# -----------------------------------------------------------------------------
# Salud
# -----------------------------------------------------------------------------


def registrar_metricas(
    fecha: str,
    peso: float | None = None,
    altura: float | None = None,
    porcentaje_grasa: float | None = None,
    perimetro_cintura: float | None = None,
    notas: str | None = None,
) -> dict:
    """Registra (o actualiza) las métricas de salud de un día concreto.

    Hace upsert por fecha: solo puede existir un registro de métricas por
    día. Los parámetros que se dejan en None **no se envían** en la
    actualización, así que no sobrescriben con null valores ya guardados
    previamente para ese mismo día (p. ej. registrar solo el peso de hoy no
    borra la altura ya guardada antes).

    Args:
        fecha: fecha del registro, formato "YYYY-MM-DD".
        peso: peso corporal opcional, en kg.
        altura: altura opcional, en cm.
        porcentaje_grasa: porcentaje de grasa corporal opcional.
        perimetro_cintura: perímetro de cintura opcional, en cm.
        notas: notas de texto libre opcionales.

    Returns:
        El registro de métricas de salud resultante (creado o actualizado).
    """
    return database.registrar_metricas(
        fecha,
        peso=peso,
        altura=altura,
        porcentaje_grasa=porcentaje_grasa,
        perimetro_cintura=perimetro_cintura,
        notas=notas,
    )


def historico_salud(
    fecha_desde: str | None = None, fecha_hasta: str | None = None
) -> list[dict]:
    """Devuelve el histórico de métricas de salud, ordenado por fecha ascendente.

    Args:
        fecha_desde: fecha inicial opcional del rango, formato "YYYY-MM-DD".
            Si se omite, no hay límite inferior.
        fecha_hasta: fecha final opcional del rango (incluida), formato
            "YYYY-MM-DD". Si se omite, no hay límite superior.

    Returns:
        Lista de registros de métricas de salud.
    """
    return database.obtener_historico_salud(
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta
    )


# -----------------------------------------------------------------------------
# Deporte
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

    Args:
        tipo_actividad: nombre libre del tipo de actividad (p. ej. "Pesas",
            "Running").
        duracion_minutos: duración de la sesión, en minutos.
        fecha: fecha/hora de la sesión, formato "YYYY-MM-DD" (o timestamp
            ISO completo). Si se omite, la base de datos asigna la fecha y
            hora actuales.
        intensidad: una de "Alta", "Media", "Baja", o None si no se
            especifica.
        volumen_total_kg: volumen total opcional levantado en la sesión
            (p. ej. para entrenamientos de fuerza), en kg.
        comentarios: comentarios de texto libre opcionales.

    Returns:
        El registro de la actividad creada.

    Raises:
        ValueError: si `intensidad` no es None ni uno de los 3 valores
            válidos.
    """
    return database.registrar_actividad(
        tipo_actividad,
        duracion_minutos,
        fecha=fecha,
        intensidad=intensidad,
        volumen_total_kg=volumen_total_kg,
        comentarios=comentarios,
    )


def historico_deporte(
    fecha_desde: str | None = None, fecha_hasta: str | None = None
) -> list[dict]:
    """Devuelve el histórico de actividad deportiva, ordenado por fecha descendente.

    Args:
        fecha_desde: fecha inicial opcional del rango, formato "YYYY-MM-DD".
            Si se omite, no hay límite inferior.
        fecha_hasta: fecha final opcional del rango (incluida), formato
            "YYYY-MM-DD". Si se omite, no hay límite superior.

    Returns:
        Lista de registros de actividad deportiva, la más reciente primero.
    """
    return database.obtener_historico_deporte(
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta
    )


# -----------------------------------------------------------------------------
# Exportación de contexto
# -----------------------------------------------------------------------------


def exportar_contexto(fecha_desde: str, fecha_hasta: str) -> str:
    """Genera el contexto completo de la app en un único string de texto.

    Es el mismo contenido que exporta la app como ZIP (botón de descarga del
    Dashboard), pero devuelto como un solo string listo para pegar en el
    contexto de un LLM, en lugar de varios ficheros: el catálogo de recetas
    en Markdown seguido de los CSVs (en texto) de menús, histórico de salud,
    histórico de deporte y lista de la compra.

    Estructura del texto devuelto:
        - Catálogo de recetas en Markdown (todas las recetas).
        - Sección "## Menús": CSV de las comidas planificadas entre
          `fecha_desde` y `fecha_hasta`.
        - Sección "## Histórico de salud": CSV con el histórico completo.
        - Sección "## Histórico de deporte": CSV con el histórico completo.
        - Sección "## Lista de la compra": CSV con la lista completa.

    Args:
        fecha_desde: fecha inicial del rango de menús, formato "YYYY-MM-DD".
        fecha_hasta: fecha final del rango de menús (incluida), formato
            "YYYY-MM-DD".

    Returns:
        Un único string con todo el contexto, en Markdown + CSV.
    """
    recetas = database.obtener_recetas()
    menus = database.obtener_menu_rango(fecha_desde, fecha_hasta)
    salud = database.obtener_historico_salud()
    deporte = database.obtener_historico_deporte()
    compra = database.obtener_lista()

    partes = [exporter.recetas_a_markdown(recetas)]

    partes.append("## Menús\n")
    partes.append(exporter.menus_a_dataframe(menus).to_csv(index=False))

    partes.append("## Histórico de salud\n")
    partes.append(exporter.salud_a_dataframe(salud).to_csv(index=False))

    partes.append("## Histórico de deporte\n")
    partes.append(exporter.deporte_a_dataframe(deporte).to_csv(index=False))

    partes.append("## Lista de la compra\n")
    partes.append(exporter.lista_compra_a_dataframe(compra).to_csv(index=False))

    return "\n".join(partes)


# -----------------------------------------------------------------------------
# Registro de tools en el servidor MCP
# -----------------------------------------------------------------------------

mcp.tool()(listar_recetas)
mcp.tool()(crear_receta)
mcp.tool()(fecha_actual)
mcp.tool()(consultar_menu)
mcp.tool()(planificar_comida)
mcp.tool()(consultar_lista_compra)
mcp.tool()(agregar_item_compra)
mcp.tool()(marcar_item_comprado)
mcp.tool()(registrar_metricas)
mcp.tool()(historico_salud)
mcp.tool()(registrar_actividad)
mcp.tool()(historico_deporte)
mcp.tool()(exportar_contexto)


if __name__ == "__main__":
    mcp.run()
