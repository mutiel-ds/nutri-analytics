"""Tests unitarios de mcp_server.py: llaman a las tools como funciones normales.

No golpean la red ni requieren un `.env` válido: para las tools que llaman a
`database.py` se reutiliza la fixture `cliente_mock` de `tests/test_database.py`,
que sustituye el singleton `database._client` por un `unittest.mock.MagicMock`.
Estos tests corren con el `uv run pytest` por defecto (no llevan el marker
`integration`).
"""

import asyncio

import pytest

import mcp_server

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def cliente_mock():
    """Sustituye el singleton `database._client` por un MagicMock durante el test.

    Idéntica a la fixture homónima de `tests/test_database.py`: guarda el
    valor previo, lo restaura al finalizar (aunque el test falle), y hace
    yield del mock para que el test configure las cadenas de llamadas.
    """
    from unittest.mock import MagicMock

    import database

    anterior = database._client
    mock = MagicMock()
    database._client = mock
    try:
        yield mock
    finally:
        database._client = anterior


# -----------------------------------------------------------------------------
# listar_recetas
# -----------------------------------------------------------------------------


def test_listar_recetas_sin_filtros_devuelve_todas(cliente_mock):
    """Sin filtros, listar_recetas devuelve el catálogo completo de database.obtener_recetas."""
    recetas = [
        {"id": "1", "titulo": "Tortitas", "calorias": 300},
        {"id": "2", "titulo": "Lasaña", "calorias": 1200},
    ]
    consulta = cliente_mock.table.return_value.select.return_value.order.return_value
    consulta.execute.return_value.data = recetas

    resultado = mcp_server.listar_recetas()

    assert resultado == recetas


def test_listar_recetas_con_filtro_calorias_aplica_el_filtrado(cliente_mock):
    """Con un filtro calorias<1000, solo se devuelven las recetas que lo cumplen."""
    recetas = [
        {"id": "1", "titulo": "Tortitas", "calorias": 300},
        {"id": "2", "titulo": "Lasaña", "calorias": 1200},
    ]
    consulta = cliente_mock.table.return_value.select.return_value.order.return_value
    consulta.execute.return_value.data = recetas

    resultado = mcp_server.listar_recetas(
        filtros=[{"campo": "calorias", "operador": "<", "valor": 1000}]
    )

    assert resultado == [recetas[0]]


def test_listar_recetas_con_filtro_invalido_lanza_valueerror(cliente_mock):
    """Un filtro con campo desconocido lanza ValueError (vía filtros.validar_filtro)."""
    recetas = [{"id": "1", "titulo": "Tortitas", "calorias": 300}]
    consulta = cliente_mock.table.return_value.select.return_value.order.return_value
    consulta.execute.return_value.data = recetas

    with pytest.raises(ValueError):
        mcp_server.listar_recetas(
            filtros=[{"campo": "no_existe", "operador": "=", "valor": "x"}]
        )


# -----------------------------------------------------------------------------
# crear_receta
# -----------------------------------------------------------------------------


def test_crear_receta_sin_titulo_lanza_valueerror_sin_tocar_cliente(cliente_mock):
    """Un título vacío (o solo espacios) lanza ValueError sin llegar a llamar a .table()."""
    with pytest.raises(ValueError):
        mcp_server.crear_receta(titulo="   ", ingredientes=["Avena"])

    cliente_mock.table.assert_not_called()


def test_crear_receta_sin_ingredientes_lanza_valueerror_sin_tocar_cliente(
    cliente_mock,
):
    """Una lista de ingredientes vacía lanza ValueError sin llegar a llamar a .table()."""
    with pytest.raises(ValueError):
        mcp_server.crear_receta(titulo="Tortitas", ingredientes=[])

    cliente_mock.table.assert_not_called()


def test_crear_receta_valida_llama_insert_con_el_payload_completo(cliente_mock):
    """Con datos válidos, crea la receta con database.crear_receta y devuelve el registro."""
    creada = {"id": "r1", "titulo": "Tortitas", "ingredientes": ["Avena", "Huevo"]}
    cliente_mock.table.return_value.insert.return_value.execute.return_value.data = [
        creada
    ]

    resultado = mcp_server.crear_receta(
        titulo="Tortitas", ingredientes=["Avena", "Huevo"]
    )

    cliente_mock.table.assert_called_with("recetas")
    payload = cliente_mock.table.return_value.insert.call_args.args[0]
    assert payload["titulo"] == "Tortitas"
    assert payload["ingredientes"] == ["Avena", "Huevo"]
    assert resultado == creada


# -----------------------------------------------------------------------------
# consultar_menu / planificar_comida
# -----------------------------------------------------------------------------


def test_consultar_menu_delega_en_obtener_menu_rango(cliente_mock):
    """consultar_menu llama a database.obtener_menu_rango con las fechas recibidas."""
    menu = [{"id": "m1", "fecha": "2026-07-18", "recetas": {"titulo": "X"}}]
    consulta = (
        cliente_mock.table.return_value.select.return_value.gte.return_value.lte.return_value.order.return_value
    )
    consulta.execute.return_value.data = menu

    resultado = mcp_server.consultar_menu("2026-07-01", "2026-07-31")

    cliente_mock.table.assert_called_with("menus_semanales")
    assert resultado == menu


def test_planificar_comida_tipo_invalido_lanza_valueerror_sin_tocar_cliente(
    cliente_mock,
):
    """Un tipo_comida inválido lanza ValueError sin llegar a llamar a .table()."""
    with pytest.raises(ValueError):
        mcp_server.planificar_comida("2026-07-18", "Tipo inventado")

    cliente_mock.table.assert_not_called()


def test_planificar_comida_valida_hace_upsert(cliente_mock):
    """Con un tipo_comida válido, planificar_comida hace upsert vía database.guardar_comida."""
    creada = {
        "id": "m1",
        "fecha": "2026-07-18",
        "tipo_comida": "Desayuno",
        "receta_id": "r1",
        "nota_adicional": None,
    }
    cliente_mock.table.return_value.upsert.return_value.execute.return_value.data = [
        creada
    ]

    resultado = mcp_server.planificar_comida(
        "2026-07-18", "Desayuno", receta_id="r1"
    )

    cliente_mock.table.assert_called_with("menus_semanales")
    assert resultado == creada


# -----------------------------------------------------------------------------
# exportar_contexto
# -----------------------------------------------------------------------------


def test_exportar_contexto_con_datos_minimos_contiene_las_secciones_esperadas(
    cliente_mock,
):
    """Con el mock devolviendo listas vacías, el string resultante contiene todas las secciones."""
    consulta_select = cliente_mock.table.return_value.select.return_value

    # obtener_recetas(): .select("*").order("titulo").execute()
    consulta_select.order.return_value.execute.return_value.data = []

    # obtener_menu_rango(): .select("*, recetas(*)").gte().lte().order().execute()
    consulta_select.gte.return_value.lte.return_value.order.return_value.execute.return_value.data = (
        []
    )

    # obtener_historico_salud() / obtener_historico_deporte(): .select("*").order("fecha").execute()
    # (mismo mock que order.return_value de arriba, ya configurado a [])

    # obtener_lista(): .select("*").order("categoria").order("item").execute()
    consulta_select.order.return_value.order.return_value.execute.return_value.data = (
        []
    )

    resultado = mcp_server.exportar_contexto("2026-07-01", "2026-07-31")

    assert "# Catálogo de Recetas Disponibles" in resultado
    assert "## Menús" in resultado
    assert "## Histórico de salud" in resultado
    assert "## Histórico de deporte" in resultado
    assert "## Lista de la compra" in resultado


# -----------------------------------------------------------------------------
# Registro de tools
# -----------------------------------------------------------------------------


def test_el_servidor_registra_las_12_tools_con_los_nombres_exactos():
    """mcp_server.mcp expone exactamente las 12 tools con los nombres acordados."""
    nombres_esperados = {
        "listar_recetas",
        "crear_receta",
        "consultar_menu",
        "planificar_comida",
        "consultar_lista_compra",
        "agregar_item_compra",
        "marcar_item_comprado",
        "registrar_metricas",
        "historico_salud",
        "registrar_actividad",
        "historico_deporte",
        "exportar_contexto",
    }

    tools = asyncio.run(mcp_server.mcp.list_tools())
    nombres = {tool.name for tool in tools}

    assert len(tools) == 12
    assert nombres == nombres_esperados
