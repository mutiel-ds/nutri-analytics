"""Tests unitarios (puros, sin red) de planificacion.py."""

from datetime import date

from planificacion import (
    agrupar_lista_compra,
    cambios_comidas_dia,
    dias_de_semana,
    etiqueta_dia,
    total_calorias_dia,
)

# -----------------------------------------------------------------------------
# dias_de_semana
# -----------------------------------------------------------------------------


def test_dias_de_semana_devuelve_7_dias_consecutivos():
    """dias_de_semana devuelve los 7 días consecutivos empezando en el lunes dado."""
    lunes = date(2026, 7, 13)  # lunes
    resultado = dias_de_semana(lunes)
    assert resultado == [
        date(2026, 7, 13),
        date(2026, 7, 14),
        date(2026, 7, 15),
        date(2026, 7, 16),
        date(2026, 7, 17),
        date(2026, 7, 18),
        date(2026, 7, 19),
    ]


# -----------------------------------------------------------------------------
# etiqueta_dia
# -----------------------------------------------------------------------------


def test_etiqueta_dia_fecha_conocida_sin_hoy():
    """etiqueta_dia formatea un día conocido sin sufijo cuando no es hoy."""
    d = date(2026, 7, 20)  # lunes
    hoy = date(2026, 7, 18)
    assert etiqueta_dia(d, hoy) == "Lunes 20/07"


def test_etiqueta_dia_incluye_sufijo_hoy():
    """etiqueta_dia añade " · hoy" cuando la fecha coincide con hoy."""
    d = date(2026, 7, 18)  # sábado
    assert etiqueta_dia(d, d) == "Sábado 18/07 · hoy"


# -----------------------------------------------------------------------------
# cambios_comidas_dia
# -----------------------------------------------------------------------------


def test_cambios_asignacion_nueva():
    """Un tipo sin registro previo y con receta nueva genera un a_guardar."""
    previas: dict = {}
    nuevas = {"Desayuno": {"receta_id": "r1", "nota_adicional": None}}
    a_guardar, a_eliminar = cambios_comidas_dia(previas, nuevas)
    assert a_guardar == [
        {"tipo_comida": "Desayuno", "receta_id": "r1", "nota_adicional": None}
    ]
    assert a_eliminar == []


def test_cambios_cambio_de_receta():
    """Un tipo ya planificado cuya receta cambia genera un a_guardar con la receta nueva."""
    previas = {"Cena": {"receta_id": "r1", "nota_adicional": None}}
    nuevas = {"Cena": {"receta_id": "r2", "nota_adicional": None}}
    a_guardar, a_eliminar = cambios_comidas_dia(previas, nuevas)
    assert a_guardar == [
        {"tipo_comida": "Cena", "receta_id": "r2", "nota_adicional": None}
    ]
    assert a_eliminar == []


def test_cambios_cambio_solo_de_nota():
    """Un tipo con la misma receta pero nota distinta también genera un a_guardar."""
    previas = {"Almuerzo": {"receta_id": "r1", "nota_adicional": "sin sal"}}
    nuevas = {"Almuerzo": {"receta_id": "r1", "nota_adicional": "con sal"}}
    a_guardar, a_eliminar = cambios_comidas_dia(previas, nuevas)
    assert a_guardar == [
        {"tipo_comida": "Almuerzo", "receta_id": "r1", "nota_adicional": "con sal"}
    ]
    assert a_eliminar == []


def test_cambios_tipo_vaciado_que_existia_va_a_eliminar():
    """Un tipo que existía y ahora queda sin receta ni nota se marca para eliminar."""
    previas = {"Merienda": {"receta_id": "r1", "nota_adicional": None}}
    nuevas = {"Merienda": {"receta_id": None, "nota_adicional": None}}
    a_guardar, a_eliminar = cambios_comidas_dia(previas, nuevas)
    assert a_guardar == []
    assert a_eliminar == ["Merienda"]


def test_cambios_tipo_identico_no_genera_operacion():
    """Un tipo con el mismo receta_id y la misma nota no genera ninguna operación."""
    previas = {"Cena": {"receta_id": "r1", "nota_adicional": "poco hecho"}}
    nuevas = {"Cena": {"receta_id": "r1", "nota_adicional": "poco hecho"}}
    a_guardar, a_eliminar = cambios_comidas_dia(previas, nuevas)
    assert a_guardar == []
    assert a_eliminar == []


def test_cambios_tipo_vacio_antes_y_despues_no_genera_operacion():
    """Un tipo sin contenido antes y sin contenido después no genera ninguna operación."""
    previas: dict = {}
    nuevas = {"Desayuno": {"receta_id": None, "nota_adicional": None}}
    a_guardar, a_eliminar = cambios_comidas_dia(previas, nuevas)
    assert a_guardar == []
    assert a_eliminar == []


def test_cambios_tipo_vacio_con_nota_en_blanco_no_genera_operacion():
    """Una nota compuesta solo de espacios se considera vacía (sin contenido)."""
    previas: dict = {}
    nuevas = {"Desayuno": {"receta_id": None, "nota_adicional": "   "}}
    a_guardar, a_eliminar = cambios_comidas_dia(previas, nuevas)
    assert a_guardar == []
    assert a_eliminar == []


def test_cambios_comida_solo_nota_sin_receta():
    """Una comida sin receta pero con nota nueva se guarda igualmente."""
    previas: dict = {}
    nuevas = {"Cena": {"receta_id": None, "nota_adicional": "sobras de ayer"}}
    a_guardar, a_eliminar = cambios_comidas_dia(previas, nuevas)
    assert a_guardar == [
        {"tipo_comida": "Cena", "receta_id": None, "nota_adicional": "sobras de ayer"}
    ]
    assert a_eliminar == []


def test_cambios_varios_tipos_a_la_vez():
    """cambios_comidas_dia procesa correctamente varios tipos combinados en una sola llamada."""
    previas = {
        "Desayuno": {"receta_id": "r1", "nota_adicional": None},
        "Cena": {"receta_id": "r3", "nota_adicional": "sin gluten"},
    }
    nuevas = {
        "Desayuno": {"receta_id": "r1", "nota_adicional": None},  # idéntico
        "Almuerzo": {"receta_id": "r2", "nota_adicional": None},  # nuevo
        "Merienda": {"receta_id": None, "nota_adicional": None},  # vacío antes y después
        "Cena": {"receta_id": None, "nota_adicional": None},  # vaciado
    }
    a_guardar, a_eliminar = cambios_comidas_dia(previas, nuevas)
    assert a_guardar == [
        {"tipo_comida": "Almuerzo", "receta_id": "r2", "nota_adicional": None}
    ]
    assert a_eliminar == ["Cena"]


# -----------------------------------------------------------------------------
# total_calorias_dia
# -----------------------------------------------------------------------------


def test_total_calorias_dia_suma_las_recetas_con_calorias():
    """total_calorias_dia suma las calorías de todas las recetas embebidas del día."""
    comidas = [
        {"tipo_comida": "Desayuno", "recetas": {"calorias": 300}},
        {"tipo_comida": "Cena", "recetas": {"calorias": 500}},
    ]
    assert total_calorias_dia(comidas) == 800


def test_total_calorias_dia_ignora_las_que_no_tienen_calorias():
    """total_calorias_dia suma solo las recetas con calorías, ignorando el resto."""
    comidas = [
        {"tipo_comida": "Desayuno", "recetas": {"calorias": 300}},
        {"tipo_comida": "Almuerzo", "recetas": {"calorias": None}},
        {"tipo_comida": "Cena", "recetas": None},
        {"tipo_comida": "Merienda", "nota_adicional": "fruta"},
    ]
    assert total_calorias_dia(comidas) == 300


def test_total_calorias_dia_ninguna_con_calorias_devuelve_none():
    """Si ninguna comida del día tiene receta con calorías, devuelve None."""
    comidas = [
        {"tipo_comida": "Desayuno", "recetas": None},
        {"tipo_comida": "Cena", "nota_adicional": "fuera de casa"},
    ]
    assert total_calorias_dia(comidas) is None


def test_total_calorias_dia_lista_vacia_devuelve_none():
    """Una lista de comidas vacía devuelve None."""
    assert total_calorias_dia([]) is None


# -----------------------------------------------------------------------------
# agrupar_lista_compra
# -----------------------------------------------------------------------------


def test_agrupar_lista_compra_agrupa_por_categoria():
    """agrupar_lista_compra agrupa los items bajo su categoría correspondiente."""
    items = [
        {"item": "Manzanas", "categoria": "Frutas"},
        {"item": "Peras", "categoria": "Frutas"},
        {"item": "Pollo", "categoria": "Carnes"},
    ]
    grupos = agrupar_lista_compra(items)
    assert set(grupos.keys()) == {"Frutas", "Carnes"}
    assert [i["item"] for i in grupos["Frutas"]] == ["Manzanas", "Peras"]
    assert [i["item"] for i in grupos["Carnes"]] == ["Pollo"]


def test_agrupar_lista_compra_categoria_none_o_vacia_va_a_sin_categoria_al_final():
    """Categorías None o cadena vacía se agrupan como "Sin categoría", siempre al final."""
    items = [
        {"item": "Sal", "categoria": None},
        {"item": "Manzanas", "categoria": "Frutas"},
        {"item": "Azúcar", "categoria": ""},
    ]
    grupos = agrupar_lista_compra(items)
    claves = list(grupos.keys())
    assert claves == ["Frutas", "Sin categoría"]
    nombres_sin_categoria = {i["item"] for i in grupos["Sin categoría"]}
    assert nombres_sin_categoria == {"Sal", "Azúcar"}


def test_agrupar_lista_compra_categorias_ordenadas_alfabeticamente():
    """Las categorías (salvo "Sin categoría") se devuelven en orden alfabético."""
    items = [
        {"item": "Pollo", "categoria": "Carnes"},
        {"item": "Manzanas", "categoria": "Frutas"},
        {"item": "Leche", "categoria": "Lácteos"},
    ]
    grupos = agrupar_lista_compra(items)
    assert list(grupos.keys()) == ["Carnes", "Frutas", "Lácteos"]


def test_agrupar_lista_compra_items_ordenados_por_nombre_dentro_del_grupo():
    """Dentro de cada grupo, los items se ordenan alfabéticamente por su nombre."""
    items = [
        {"item": "Zanahorias", "categoria": "Verduras"},
        {"item": "Acelgas", "categoria": "Verduras"},
        {"item": "Brócoli", "categoria": "Verduras"},
    ]
    grupos = agrupar_lista_compra(items)
    assert [i["item"] for i in grupos["Verduras"]] == ["Acelgas", "Brócoli", "Zanahorias"]


def test_agrupar_lista_compra_lista_vacia_devuelve_dict_vacio():
    """Una lista de items vacía devuelve un dict vacío."""
    assert agrupar_lista_compra([]) == {}
