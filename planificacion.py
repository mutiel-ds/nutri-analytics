"""Lógica pura del Planificador semanal y de la Lista de la compra.

Módulo puro (no depende de Streamlit ni de ninguna librería externa) que
calcula fechas de la semana, etiquetas de día en español, el diff de
comidas a guardar/eliminar al enviar el formulario de un día, el total de
calorías planificadas y el agrupado de la lista de la compra por categoría.

Al ser independiente de la UI, este módulo sigue el patrón "agent-ready"
de `filtros.py` (decisión D9 de docs/decisiones.md): un agente de IA podría
llamar a estas mismas funciones (p. ej. para calcular qué comidas guardar
o cómo agrupar la lista de la compra) sin depender de Streamlit.
"""

from __future__ import annotations

import unicodedata
from datetime import date, timedelta

# Nombres de los días de la semana en español (weekday(): 0 = Lunes). Se
# define aquí (y no se importa de `paginas/comun.py`) para que este módulo
# siga siendo puro stdlib, sin depender de Streamlit.
_DIAS_SEMANA_ES: tuple[str, ...] = (
    "Lunes",
    "Martes",
    "Miércoles",
    "Jueves",
    "Viernes",
    "Sábado",
    "Domingo",
)


def dias_de_semana(lunes: date) -> list[date]:
    """Devuelve los 7 días (lunes a domingo) de la semana que empieza en `lunes`.

    Args:
        lunes: fecha del lunes de la semana (no se valida que sea lunes;
            es responsabilidad de quien llama, p. ej. `comun.lunes_de_la_semana`).

    Returns:
        Lista de 7 fechas consecutivas empezando en `lunes`.
    """
    return [lunes + timedelta(days=i) for i in range(7)]


def etiqueta_dia(d: date, hoy: date) -> str:
    """Devuelve la etiqueta de un día para mostrar en la UI, p. ej. "Lunes 20/07".

    Añade el sufijo " · hoy" cuando `d` coincide con `hoy`.

    Args:
        d: fecha del día a etiquetar.
        hoy: fecha considerada "hoy" (se pasa explícitamente para que la
            función sea pura y fácil de testear).

    Returns:
        Cadena tipo "Lunes 20/07" (o "Lunes 20/07 · hoy" si `d == hoy`).
    """
    nombre_dia = _DIAS_SEMANA_ES[d.weekday()]
    etiqueta = f"{nombre_dia} {d.day:02d}/{d.month:02d}"
    if d == hoy:
        etiqueta += " · hoy"
    return etiqueta


def _normalizar_nota(nota: str | None) -> str | None:
    """Normaliza una nota: cadenas vacías o solo espacios se tratan como None."""
    if nota is None:
        return None
    nota = nota.strip()
    return nota or None


def cambios_comidas_dia(
    previas: dict[str, dict], nuevas: dict[str, dict]
) -> tuple[list[dict], list[str]]:
    """Calcula qué comidas guardar y cuáles eliminar al enviar el formulario de un día.

    Args:
        previas: dict tipo_comida -> registro existente en BD
            ({"receta_id": ..., "nota_adicional": ...}), solo con los tipos
            que ya estaban planificados para ese día.
        nuevas: dict tipo_comida -> {"receta_id": str | None, "nota_adicional": str | None}
            con el estado del formulario para los 4 tipos de comida.

    Returns:
        Tupla `(a_guardar, a_eliminar)`:
            - `a_guardar`: lista de dicts {"tipo_comida", "receta_id",
              "nota_adicional"} para los tipos cuyo estado nuevo tiene
              contenido (receta o nota) y difiere del previo.
            - `a_eliminar`: lista de tipo_comida que existían antes y
              ahora quedan vacíos (sin receta y sin nota).

        Un tipo sin contenido antes y después no genera ninguna operación;
        un tipo idéntico antes y después tampoco (evita upserts inútiles).
    """
    a_guardar: list[dict] = []
    a_eliminar: list[str] = []

    for tipo, estado in nuevas.items():
        receta_id = estado.get("receta_id")
        nota = _normalizar_nota(estado.get("nota_adicional"))
        tiene_contenido = receta_id is not None or nota is not None

        anterior = previas.get(tipo)

        if not tiene_contenido:
            if anterior is not None:
                a_eliminar.append(tipo)
            continue

        if anterior is None:
            a_guardar.append(
                {"tipo_comida": tipo, "receta_id": receta_id, "nota_adicional": nota}
            )
            continue

        receta_previa = anterior.get("receta_id")
        nota_previa = _normalizar_nota(anterior.get("nota_adicional"))
        if receta_id != receta_previa or nota != nota_previa:
            a_guardar.append(
                {"tipo_comida": tipo, "receta_id": receta_id, "nota_adicional": nota}
            )

    return a_guardar, a_eliminar


def total_calorias_dia(comidas: list[dict]) -> int | None:
    """Suma las calorías de las recetas embebidas (clave "recetas") de un día.

    Args:
        comidas: lista de comidas planificadas para un día (registros de
            `menus_semanales` con la receta asociada embebida en "recetas",
            tal como los devuelve `database.obtener_menu_rango`).

    Returns:
        La suma de calorías de las recetas que tienen ese dato, o None si
        ninguna comida tiene receta con calorías (o la lista está vacía).
    """
    total = 0
    hay_calorias = False
    for comida in comidas:
        receta = comida.get("recetas")
        if receta:
            calorias = receta.get("calorias")
            if calorias is not None:
                total += calorias
                hay_calorias = True
    return total if hay_calorias else None


def _normalizar_categoria(categoria: str) -> str:
    """Normaliza una categoría para agrupar variantes que solo difieren en
    mayúsculas o acentos (p. ej. "Frutas" y "frutas" deben ir al mismo grupo).

    Réplica local y simplificada de `filtros._normalizar` (minúsculas + sin
    acentos): este módulo es stdlib puro y no importa de `filtros.py` para
    mantenerse independiente.

    Args:
        categoria: nombre de categoría a normalizar.

    Returns:
        La cadena en minúsculas, sin espacios extremos ni diacríticos.
    """
    descompuesto = unicodedata.normalize("NFD", categoria.strip().lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def agrupar_lista_compra(items: list[dict]) -> dict[str, list[dict]]:
    """Agrupa los items de la lista de la compra por categoría.

    Args:
        items: lista de items de `lista_compra` (registros con al menos
            las claves "item" y "categoria").

    Returns:
        Dict categoria -> lista de items (ordenados por nombre de item).
        Las categorías None o vacías se agrupan bajo "Sin categoría". El
        agrupado usa una clave normalizada (minúsculas, sin acentos) para que
        variantes como "Frutas" y "frutas" caigan en un único grupo; el
        nombre mostrado del grupo es la primera variante vista (por orden de
        aparición). Las claves del dict resultante están ordenadas
        alfabéticamente por su clave normalizada, con "Sin categoría"
        siempre al final.
    """
    grupos: dict[str, dict] = {}
    for item in items:
        categoria = item.get("categoria") or "Sin categoría"
        clave = _normalizar_categoria(categoria)
        if clave not in grupos:
            grupos[clave] = {"nombre": categoria, "items": []}
        grupos[clave]["items"].append(item)

    for grupo in grupos.values():
        grupo["items"].sort(key=lambda i: (i.get("item") or "").lower())

    clave_sin_categoria = _normalizar_categoria("Sin categoría")
    claves_ordenadas = sorted(c for c in grupos if c != clave_sin_categoria)
    if clave_sin_categoria in grupos:
        claves_ordenadas.append(clave_sin_categoria)

    return {grupos[clave]["nombre"]: grupos[clave]["items"] for clave in claves_ordenadas}
