"""Sistema de filtros aditivos para recetas.

Módulo puro (no depende de Streamlit ni de ninguna librería externa) que
define qué campos de una receta se pueden filtrar, valida filtros
expresados como diccionarios y los aplica a una lista de recetas.

Al ser independiente de la UI, este módulo puede reutilizarse tal cual
como "tool" de un agente de IA (p. ej. vía MCP, Model Context Protocol):
un agente puede construir filtros como JSON, validarlos con
`validar_filtro` (que da mensajes de error claros en español) y aplicarlos
con `aplicar_filtros`, sin necesidad de conocer nada de Streamlit.

Un filtro es un diccionario con la forma:
    {"campo": str, "operador": str, "valor": Any}

Ejemplos:
    {"campo": "categoria", "operador": "=", "valor": "Desayuno"}
    {"campo": "calorias", "operador": "<", "valor": 1000}
    {"campo": "ingredientes", "operador": "contiene", "valor": "brócoli"}

El operador simbólico ("<", "=", "contiene"...) es la representación estable
del filtro, pensada para agentes de IA (decisión D9): no cambia aunque cambie
la UI. Para mostrar el filtro a una persona en lenguaje natural, la capa de
presentación usa `ETIQUETAS_OPERADOR` / `etiqueta_operador` (p. ej. "<" se
muestra como "menos de") y `describir_filtro` compone la frase completa.
"""

from __future__ import annotations

from typing import Any

# -----------------------------------------------------------------------------
# Especificación declarativa de los campos filtrables
# -----------------------------------------------------------------------------

CAMPOS_FILTRO: dict[str, dict[str, str]] = {
    "categoria": {"tipo": "enum", "etiqueta": "Categoría"},
    "tiempo_preparacion": {"tipo": "numerico", "etiqueta": "Tiempo (min)"},
    "calorias": {"tipo": "numerico", "etiqueta": "Calorías (kcal)"},
    "proteinas": {"tipo": "numerico", "etiqueta": "Proteínas (g)"},
    "carbohidratos": {"tipo": "numerico", "etiqueta": "Carbohidratos (g)"},
    "grasas": {"tipo": "numerico", "etiqueta": "Grasas (g)"},
    "ingredientes": {"tipo": "ingredientes", "etiqueta": "Ingredientes"},
}

OPERADORES_NUMERICOS: tuple[str, ...] = ("<", "<=", "=", ">=", ">")
OPERADORES_ENUM: tuple[str, ...] = ("=", "!=")
OPERADORES_INGREDIENTES: tuple[str, ...] = ("contiene", "no contiene")

_OPERADORES_POR_TIPO: dict[str, tuple[str, ...]] = {
    "numerico": OPERADORES_NUMERICOS,
    "enum": OPERADORES_ENUM,
    "ingredientes": OPERADORES_INGREDIENTES,
}

# Etiquetas en lenguaje natural de cada operador, por tipo de campo. El modelo
# de datos interno del filtro sigue usando los operadores simbólicos (es la
# representación estable para agentes de IA, decisión D9); estas etiquetas son
# solo la capa de presentación que ve la persona usuaria en la UI.
ETIQUETAS_OPERADOR: dict[str, dict[str, str]] = {
    "numerico": {
        "<": "menos de",
        "<=": "como máximo",
        "=": "exactamente",
        ">=": "como mínimo",
        ">": "más de",
    },
    "enum": {
        "=": "igual a",
        "!=": "distinto de",
    },
    "ingredientes": {
        "contiene": "contiene",
        "no contiene": "no contiene",
    },
}


def etiqueta_operador(campo: str, operador: str) -> str:
    """Devuelve la etiqueta en lenguaje natural de un operador para un campo.

    Args:
        campo: clave de `CAMPOS_FILTRO`.
        operador: operador simbólico ("<", "=", "contiene"...).

    Returns:
        La etiqueta natural correspondiente (p. ej. "menos de", "igual a").

    Raises:
        ValueError: si el campo no existe o el operador no es válido para
            el tipo de ese campo.
    """
    if campo not in CAMPOS_FILTRO:
        campos_validos = ", ".join(sorted(CAMPOS_FILTRO))
        raise ValueError(
            f"Campo desconocido: '{campo}'. Campos válidos: {campos_validos}."
        )

    tipo = CAMPOS_FILTRO[campo]["tipo"]
    etiquetas = ETIQUETAS_OPERADOR[tipo]

    if operador not in etiquetas:
        raise ValueError(
            f"Operador no válido para el campo '{campo}' (tipo '{tipo}'): "
            f"'{operador}'. Operadores válidos: {', '.join(etiquetas)}."
        )

    return etiquetas[operador]


def validar_filtro(filtro: dict) -> None:
    """Valida la estructura y el contenido de un filtro.

    Comprueba que el campo exista en `CAMPOS_FILTRO`, que el operador sea
    válido para el tipo de ese campo y que el valor tenga el tipo esperado:
    los campos numéricos exigen `int` o `float`; los campos de tipo enum e
    ingredientes exigen una cadena (`str`) no vacía.

    Pensada para dar buena retroalimentación a un agente de IA que
    construya filtros como JSON: los mensajes de error son descriptivos y
    están en español.

    Args:
        filtro: diccionario con las claves "campo", "operador" y "valor".

    Raises:
        ValueError: si el filtro no es válido, con un mensaje claro sobre
            qué parte falla y por qué.
    """
    if not isinstance(filtro, dict):
        raise ValueError("El filtro debe ser un diccionario.")

    for clave in ("campo", "operador", "valor"):
        if clave not in filtro:
            raise ValueError(f"Falta la clave obligatoria '{clave}' en el filtro.")

    campo = filtro["campo"]
    operador = filtro["operador"]
    valor = filtro["valor"]

    if campo not in CAMPOS_FILTRO:
        campos_validos = ", ".join(sorted(CAMPOS_FILTRO))
        raise ValueError(
            f"Campo desconocido: '{campo}'. Campos válidos: {campos_validos}."
        )

    tipo = CAMPOS_FILTRO[campo]["tipo"]
    operadores_validos = _OPERADORES_POR_TIPO[tipo]

    if operador not in operadores_validos:
        raise ValueError(
            f"Operador no válido para el campo '{campo}' (tipo '{tipo}'): "
            f"'{operador}'. Operadores válidos: {', '.join(operadores_validos)}."
        )

    if tipo == "numerico":
        # bool es subclase de int en Python; lo excluimos explícitamente.
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            raise ValueError(
                f"El valor del filtro sobre '{campo}' debe ser numérico (int o float); "
                f"se recibió: {valor!r}."
            )
    else:  # "enum" o "ingredientes"
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError(
                f"El valor del filtro sobre '{campo}' debe ser una cadena de texto no vacía; "
                f"se recibió: {valor!r}."
            )


def aplicar_filtros(recetas: list[dict], filtros: list[dict]) -> list[dict]:
    """Aplica una lista de filtros a una lista de recetas, en modo AND aditivo.

    Cada filtro se valida primero con `validar_filtro`. Una receta pasa el
    conjunto de filtros solo si cumple TODOS ellos.

    Semántica por tipo de campo:
        - numérico: compara `receta[campo]` con `valor` usando el operador.
          Si el campo es `None` en la receta, la receta NO pasa el filtro
          (no se puede comparar un valor ausente).
        - enum: compara igualdad/desigualdad case-insensitive. Si el campo
          es `None`, la receta NO pasa "=" pero SÍ pasa "!=" (un valor
          ausente siempre es "distinto" del valor buscado).
        - ingredientes: hace una búsqueda de subcadena case-insensitive
          sobre cada línea de la lista de ingredientes de la receta.
          "contiene": pasa si alguna línea contiene el texto buscado.
          "no contiene": pasa si ninguna línea lo contiene.

    Args:
        recetas: lista de diccionarios de receta.
        filtros: lista de filtros (ver `validar_filtro` para su formato).

    Returns:
        La sublista de `recetas` que cumple todos los filtros.

    Raises:
        ValueError: si algún filtro de la lista no es válido.
    """
    for filtro in filtros:
        validar_filtro(filtro)

    resultado = recetas
    for filtro in filtros:
        resultado = [r for r in resultado if _cumple_filtro(r, filtro)]
    return resultado


def _cumple_filtro(receta: dict, filtro: dict) -> bool:
    """Determina si una única receta cumple un único filtro ya validado."""
    campo = filtro["campo"]
    operador = filtro["operador"]
    valor = filtro["valor"]
    tipo = CAMPOS_FILTRO[campo]["tipo"]

    if tipo == "numerico":
        valor_receta = receta.get(campo)
        if valor_receta is None:
            return False
        return _comparar_numerico(valor_receta, operador, valor)

    if tipo == "enum":
        valor_receta = receta.get(campo)
        if valor_receta is None:
            # None nunca es igual a un valor concreto, pero sí es "distinto".
            return operador == "!="
        coincide = str(valor_receta).strip().lower() == valor.strip().lower()
        return coincide if operador == "=" else not coincide

    # tipo == "ingredientes"
    lineas = receta.get(campo) or []
    texto_buscado = valor.strip().lower()
    alguna_coincide = any(texto_buscado in str(linea).lower() for linea in lineas)
    return alguna_coincide if operador == "contiene" else not alguna_coincide


def _comparar_numerico(valor_receta: Any, operador: str, valor: Any) -> bool:
    if operador == "<":
        return valor_receta < valor
    if operador == "<=":
        return valor_receta <= valor
    if operador == "=":
        return valor_receta == valor
    if operador == ">=":
        return valor_receta >= valor
    if operador == ">":
        return valor_receta > valor
    raise ValueError(f"Operador numérico no soportado: '{operador}'.")  # pragma: no cover


def describir_filtro(filtro: dict) -> str:
    """Devuelve una representación legible de un filtro para mostrar en la UI.

    Usa las etiquetas naturales de `ETIQUETAS_OPERADOR` en lugar de los
    operadores simbólicos, para que el texto se lea como lenguaje natural.

    Ejemplos:
        "Calorías (kcal) menos de 1000"
        "Ingredientes contiene 'brócoli'"
        "Categoría igual a 'Desayuno'"

    Args:
        filtro: diccionario de filtro (ver `validar_filtro`).

    Returns:
        Cadena de texto en español lista para mostrar al usuario.
    """
    campo = filtro["campo"]
    operador = filtro["operador"]
    valor = filtro["valor"]
    etiqueta = CAMPOS_FILTRO[campo]["etiqueta"]
    tipo = CAMPOS_FILTRO[campo]["tipo"]
    etiqueta_op = etiqueta_operador(campo, operador)

    if tipo == "numerico":
        return f"{etiqueta} {etiqueta_op} {valor}"
    return f"{etiqueta} {etiqueta_op} '{valor}'"
