"""Tests unitarios (puros, sin red) de filtros.py."""

import pytest

from filtros import (
    aplicar_filtros,
    describir_filtro,
    etiqueta_operador,
    validar_filtro,
)

# -----------------------------------------------------------------------------
# Datos de ejemplo
# -----------------------------------------------------------------------------

RECETAS = [
    {
        "id": "aaaaa-1111",
        "titulo": "Tortitas de avena",
        "categoria": "Desayuno",
        "tiempo_preparacion": 10,
        "calorias": 350,
        "proteinas": 20,
        "carbohidratos": 40,
        "grasas": 8,
        "ingredientes": ["Avena", "Huevo", "Plátano"],
    },
    {
        "id": "bbbbb-2222",
        "titulo": "Batido proteico",
        "categoria": "Desayuno",
        "tiempo_preparacion": 5,
        "calorias": 900,
        "proteinas": 100,
        "carbohidratos": 60,
        "grasas": 10,
        "ingredientes": ["Leche", "Proteína en polvo", "Brócoli al vapor"],
    },
    {
        "id": "ccccc-3333",
        "titulo": "Pollo al horno",
        "categoria": "Cena",
        "tiempo_preparacion": 45,
        "calorias": 1200,
        "proteinas": 80,
        "carbohidratos": 30,
        "grasas": 25,
        "ingredientes": ["Pollo", "Patata"],
    },
    {
        "id": "ddddd-4444",
        "titulo": "Ensalada sin datos",
        "categoria": None,
        "tiempo_preparacion": None,
        "calorias": None,
        "proteinas": None,
        "carbohidratos": None,
        "grasas": None,
        "ingredientes": None,
    },
]


# -----------------------------------------------------------------------------
# Los 3 ejemplos canónicos del usuario
# -----------------------------------------------------------------------------


def test_filtro_categoria_desayuno():
    """El filtro categoria=Desayuno devuelve solo las recetas de esa categoría."""
    filtro = {"campo": "categoria", "operador": "=", "valor": "Desayuno"}
    resultado = aplicar_filtros(RECETAS, [filtro])
    titulos = {r["titulo"] for r in resultado}
    assert titulos == {"Tortitas de avena", "Batido proteico"}


def test_filtro_calorias_menos_de_1000():
    """El filtro calorias<1000 excluye las recetas con 1000 kcal o más."""
    filtro = {"campo": "calorias", "operador": "<", "valor": 1000}
    resultado = aplicar_filtros(RECETAS, [filtro])
    titulos = {r["titulo"] for r in resultado}
    assert titulos == {"Tortitas de avena", "Batido proteico"}


def test_filtro_proteinas_mayor_igual_100():
    """El filtro proteinas>=100 solo deja pasar recetas con 100g de proteína o más."""
    filtro = {"campo": "proteinas", "operador": ">=", "valor": 100}
    resultado = aplicar_filtros(RECETAS, [filtro])
    titulos = {r["titulo"] for r in resultado}
    assert titulos == {"Batido proteico"}


# -----------------------------------------------------------------------------
# Combinación aditiva (AND) de varios filtros
# -----------------------------------------------------------------------------


def test_combinacion_aditiva_de_varios_filtros():
    """Varios filtros se combinan en AND: solo pasan las recetas que cumplen todos."""
    filtros = [
        {"campo": "categoria", "operador": "=", "valor": "Desayuno"},
        {"campo": "calorias", "operador": "<", "valor": 1000},
        {"campo": "proteinas", "operador": ">=", "valor": 100},
    ]
    resultado = aplicar_filtros(RECETAS, filtros)
    titulos = {r["titulo"] for r in resultado}
    assert titulos == {"Batido proteico"}


def test_combinacion_aditiva_sin_coincidencias():
    """Si ninguna receta cumple todos los filtros combinados, el resultado es vacío."""
    filtros = [
        {"campo": "categoria", "operador": "=", "valor": "Cena"},
        {"campo": "calorias", "operador": "<", "valor": 500},
    ]
    resultado = aplicar_filtros(RECETAS, filtros)
    assert resultado == []


# -----------------------------------------------------------------------------
# Operadores numéricos en casos frontera (valor igual al límite)
# -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("operador", "valor_limite", "pasa"),
    [
        ("<", 900, False),
        ("<=", 900, True),
        ("=", 900, True),
        (">=", 900, True),
        (">", 900, False),
    ],
)
def test_operadores_numericos_en_el_limite(operador, valor_limite, pasa):
    """En el límite exacto, <= y >= incluyen el valor; < y > lo excluyen; = lo incluye."""
    receta = {"calorias": 900}
    filtro = {"campo": "calorias", "operador": operador, "valor": valor_limite}
    resultado = aplicar_filtros([receta], [filtro])
    assert (resultado == [receta]) == pasa


def test_numerico_con_campo_none_no_pasa_el_filtro():
    """Si el campo numérico es None en la receta, no pasa ningún operador numérico."""
    receta = {"calorias": None}
    for operador in ("<", "<=", "=", ">=", ">"):
        filtro = {"campo": "calorias", "operador": operador, "valor": 500}
        assert aplicar_filtros([receta], [filtro]) == []


# -----------------------------------------------------------------------------
# Enum: = y != case-insensitive; campo None
# -----------------------------------------------------------------------------


def test_enum_igual_case_insensitive():
    """El operador '=' de enum compara ignorando mayúsculas/minúsculas."""
    receta = {"categoria": "desayuno"}
    filtro = {"campo": "categoria", "operador": "=", "valor": "DESAYUNO"}
    assert aplicar_filtros([receta], [filtro]) == [receta]


def test_enum_distinto_case_insensitive():
    """El operador '!=' de enum compara ignorando mayúsculas/minúsculas."""
    receta = {"categoria": "Cena"}
    filtro = {"campo": "categoria", "operador": "!=", "valor": "cena"}
    assert aplicar_filtros([receta], [filtro]) == []

    receta_otra = {"categoria": "Desayuno"}
    assert aplicar_filtros([receta_otra], [filtro]) == [receta_otra]


def test_enum_campo_none_no_pasa_igual_pero_si_pasa_distinto():
    """Un campo enum ausente (None) nunca pasa '=' pero siempre pasa '!='."""
    receta = {"categoria": None}
    filtro_igual = {"campo": "categoria", "operador": "=", "valor": "Desayuno"}
    filtro_distinto = {"campo": "categoria", "operador": "!=", "valor": "Desayuno"}
    assert aplicar_filtros([receta], [filtro_igual]) == []
    assert aplicar_filtros([receta], [filtro_distinto]) == [receta]


# -----------------------------------------------------------------------------
# Ingredientes: contiene / no contiene
# -----------------------------------------------------------------------------


def test_ingredientes_contiene_case_insensitive_subcadena():
    """'contiene' encuentra coincidencias de subcadena, ignorando mayúsculas."""
    receta = {"ingredientes": ["Brócoli al vapor", "Sal"]}
    filtro = {"campo": "ingredientes", "operador": "contiene", "valor": "BRÓCOLI"}
    assert aplicar_filtros([receta], [filtro]) == [receta]


def test_ingredientes_contiene_subcadena_parcial():
    """'contiene' funciona con una subcadena parcial dentro de una línea de ingrediente."""
    receta = {"ingredientes": ["200g de pollo troceado"]}
    filtro = {"campo": "ingredientes", "operador": "contiene", "valor": "pollo"}
    assert aplicar_filtros([receta], [filtro]) == [receta]


def test_ingredientes_no_contiene():
    """'no contiene' pasa solo si ninguna línea de ingredientes incluye el texto buscado."""
    receta_con = {"ingredientes": ["Brócoli", "Sal"]}
    receta_sin = {"ingredientes": ["Patata", "Sal"]}
    filtro = {"campo": "ingredientes", "operador": "no contiene", "valor": "brócoli"}
    resultado = aplicar_filtros([receta_con, receta_sin], [filtro])
    assert resultado == [receta_sin]


def test_ingredientes_lista_vacia_o_none():
    """Una receta sin ingredientes (lista vacía o None) nunca 'contiene', y siempre 'no contiene'."""
    receta_vacia = {"ingredientes": []}
    receta_none = {"ingredientes": None}
    filtro_contiene = {"campo": "ingredientes", "operador": "contiene", "valor": "sal"}
    filtro_no_contiene = {
        "campo": "ingredientes",
        "operador": "no contiene",
        "valor": "sal",
    }
    assert aplicar_filtros([receta_vacia, receta_none], [filtro_contiene]) == []
    assert aplicar_filtros([receta_vacia, receta_none], [filtro_no_contiene]) == [
        receta_vacia,
        receta_none,
    ]


# -----------------------------------------------------------------------------
# validar_filtro: casos de error
# -----------------------------------------------------------------------------


def test_validar_filtro_campo_desconocido():
    """Un campo que no existe en CAMPOS_FILTRO lanza ValueError."""
    with pytest.raises(ValueError):
        validar_filtro({"campo": "sabor", "operador": "=", "valor": "dulce"})


def test_validar_filtro_operador_ilegal_para_el_tipo():
    """Un operador válido para otro tipo pero no para este campo lanza ValueError."""
    with pytest.raises(ValueError):
        validar_filtro({"campo": "categoria", "operador": "<", "valor": "Desayuno"})

    with pytest.raises(ValueError):
        validar_filtro({"campo": "calorias", "operador": "contiene", "valor": 100})


def test_validar_filtro_valor_de_tipo_erroneo_numerico():
    """Un valor no numérico en un campo numérico lanza ValueError."""
    with pytest.raises(ValueError):
        validar_filtro({"campo": "calorias", "operador": "<", "valor": "mucho"})


def test_validar_filtro_valor_bool_como_numerico_es_invalido():
    """bool es subclase de int en Python, pero debe rechazarse como valor numérico."""
    with pytest.raises(ValueError):
        validar_filtro({"campo": "calorias", "operador": "<", "valor": True})


def test_validar_filtro_valor_de_tipo_erroneo_enum_o_ingredientes():
    """Un valor no-string (o string vacío) en enum/ingredientes lanza ValueError."""
    with pytest.raises(ValueError):
        validar_filtro({"campo": "categoria", "operador": "=", "valor": 123})

    with pytest.raises(ValueError):
        validar_filtro({"campo": "ingredientes", "operador": "contiene", "valor": "   "})


def test_validar_filtro_claves_faltantes():
    """Un filtro al que le falta alguna clave obligatoria lanza ValueError."""
    with pytest.raises(ValueError):
        validar_filtro({"operador": "=", "valor": "Desayuno"})

    with pytest.raises(ValueError):
        validar_filtro({"campo": "categoria", "valor": "Desayuno"})

    with pytest.raises(ValueError):
        validar_filtro({"campo": "categoria", "operador": "="})


def test_validar_filtro_no_dict():
    """Si el filtro no es un diccionario, lanza ValueError."""
    with pytest.raises(ValueError):
        validar_filtro(["categoria", "=", "Desayuno"])


# -----------------------------------------------------------------------------
# describir_filtro y etiqueta_operador
# -----------------------------------------------------------------------------


def test_etiqueta_operador_natural_numerico():
    """etiqueta_operador traduce el operador simbólico numérico a lenguaje natural."""
    assert etiqueta_operador("calorias", "<") == "menos de"


def test_etiqueta_operador_natural_enum():
    """etiqueta_operador traduce el operador simbólico enum a lenguaje natural."""
    assert etiqueta_operador("categoria", "=") == "igual a"


def test_etiqueta_operador_natural_ingredientes():
    """etiqueta_operador traduce el operador simbólico de ingredientes a lenguaje natural."""
    assert etiqueta_operador("ingredientes", "contiene") == "contiene"


def test_describir_filtro_numerico():
    """describir_filtro compone la frase completa para un filtro numérico."""
    filtro = {"campo": "calorias", "operador": "<", "valor": 1000}
    assert describir_filtro(filtro) == "Calorías (kcal) menos de 1000"


def test_describir_filtro_enum():
    """describir_filtro compone la frase completa para un filtro enum."""
    filtro = {"campo": "categoria", "operador": "=", "valor": "Desayuno"}
    assert describir_filtro(filtro) == "Categoría igual a 'Desayuno'"


def test_describir_filtro_ingredientes():
    """describir_filtro compone la frase completa para un filtro de ingredientes."""
    filtro = {"campo": "ingredientes", "operador": "contiene", "valor": "brócoli"}
    assert describir_filtro(filtro) == "Ingredientes contiene 'brócoli'"


# -----------------------------------------------------------------------------
# aplicar_filtros con lista de filtros vacía
# -----------------------------------------------------------------------------


def test_aplicar_filtros_lista_vacia_devuelve_todas_las_recetas():
    """Sin filtros, aplicar_filtros devuelve la lista de recetas sin modificar."""
    assert aplicar_filtros(RECETAS, []) == RECETAS
