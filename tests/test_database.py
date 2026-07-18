"""Tests unitarios de database.py: simulan el cliente de Supabase con MagicMock.

No golpean la red ni requieren un `.env` válido: el cliente real (`database._client`)
se sustituye por un `unittest.mock.MagicMock` a través de la fixture `cliente_mock`,
que además restaura el valor previo del singleton al finalizar cada test. Estos
tests corren con el `uv run pytest` por defecto (no llevan el marker `integration`,
que está reservado a tests/test_database_integration.py).
"""

from unittest.mock import MagicMock

import pytest

import database

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def cliente_mock():
    """Sustituye el singleton `database._client` por un MagicMock durante el test.

    Guarda el valor previo, lo restaura al finalizar (aunque el test falle), y
    hace yield del mock para que el test configure las cadenas de llamadas
    (`.table().select()...execute()`) y haga sus aserciones sobre él.
    """
    anterior = database._client
    mock = MagicMock()
    database._client = mock
    try:
        yield mock
    finally:
        database._client = anterior


# -----------------------------------------------------------------------------
# 1. recetas
# -----------------------------------------------------------------------------


def test_crear_receta_llama_insert_con_el_payload_tal_cual(cliente_mock):
    """crear_receta inserta el dict recibido sin modificarlo y devuelve data[0]."""
    payload = {"titulo": "Tortitas de avena", "categoria": "Desayuno"}
    creada = {"id": "r1", **payload}
    cliente_mock.table.return_value.insert.return_value.execute.return_value.data = [
        creada
    ]

    resultado = database.crear_receta(payload)

    cliente_mock.table.assert_called_with("recetas")
    cliente_mock.table.return_value.insert.assert_called_with(payload)
    assert resultado == creada


def test_obtener_recetas_sin_categoria_no_llama_a_eq(cliente_mock):
    """obtener_recetas() sin categoría ordena por titulo y no filtra con .eq."""
    recetas = [{"id": "1", "titulo": "A"}, {"id": "2", "titulo": "B"}]
    consulta = cliente_mock.table.return_value.select.return_value.order.return_value
    consulta.execute.return_value.data = recetas

    resultado = database.obtener_recetas()

    cliente_mock.table.assert_called_with("recetas")
    cliente_mock.table.return_value.select.assert_called_with("*")
    cliente_mock.table.return_value.select.return_value.order.assert_called_with(
        "titulo"
    )
    consulta.eq.assert_not_called()
    assert resultado == recetas


def test_obtener_recetas_con_categoria_llama_a_eq(cliente_mock):
    """obtener_recetas(categoria=...) filtra con .eq("categoria", ...)."""
    recetas = [{"id": "1", "titulo": "A", "categoria": "Desayuno"}]
    consulta = cliente_mock.table.return_value.select.return_value.order.return_value
    consulta.eq.return_value.execute.return_value.data = recetas

    resultado = database.obtener_recetas(categoria="Desayuno")

    consulta.eq.assert_called_with("categoria", "Desayuno")
    assert resultado == recetas


def test_obtener_receta_devuelve_data_0_si_existe(cliente_mock):
    """obtener_receta devuelve el primer elemento de data cuando hay resultado."""
    receta = {"id": "r1", "titulo": "Tortitas"}
    consulta = cliente_mock.table.return_value.select.return_value.eq.return_value
    consulta.execute.return_value.data = [receta]

    resultado = database.obtener_receta("r1")

    cliente_mock.table.return_value.select.return_value.eq.assert_called_with(
        "id", "r1"
    )
    assert resultado == receta


def test_obtener_receta_devuelve_none_si_data_vacio(cliente_mock):
    """obtener_receta devuelve None cuando data está vacío (no existe la receta)."""
    consulta = cliente_mock.table.return_value.select.return_value.eq.return_value
    consulta.execute.return_value.data = []

    resultado = database.obtener_receta("no-existe")

    assert resultado is None


def test_actualizar_receta_llama_update_y_eq(cliente_mock):
    """actualizar_receta llama a .update(cambios).eq("id", receta_id)."""
    cambios = {"calorias": 400}
    actualizada = {"id": "r1", "calorias": 400}
    consulta = cliente_mock.table.return_value.update.return_value.eq.return_value
    consulta.execute.return_value.data = [actualizada]

    resultado = database.actualizar_receta("r1", cambios)

    cliente_mock.table.return_value.update.assert_called_with(cambios)
    cliente_mock.table.return_value.update.return_value.eq.assert_called_with(
        "id", "r1"
    )
    assert resultado == actualizada


def test_eliminar_receta_llama_delete_y_eq(cliente_mock):
    """eliminar_receta llama a .delete().eq("id", receta_id)."""
    database.eliminar_receta("r1")

    cliente_mock.table.assert_called_with("recetas")
    cliente_mock.table.return_value.delete.return_value.eq.assert_called_with(
        "id", "r1"
    )
    cliente_mock.table.return_value.delete.return_value.eq.return_value.execute.assert_called_once()


# -----------------------------------------------------------------------------
# 2. menus_semanales
# -----------------------------------------------------------------------------


def test_guardar_comida_hace_upsert_con_el_registro_completo(cliente_mock):
    """guardar_comida hace upsert con (fecha, tipo_comida, receta_id, nota_adicional)."""
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

    resultado = database.guardar_comida("2026-07-18", "Desayuno", receta_id="r1")

    cliente_mock.table.assert_called_with("menus_semanales")
    cliente_mock.table.return_value.upsert.assert_called_with(
        {
            "fecha": "2026-07-18",
            "tipo_comida": "Desayuno",
            "receta_id": "r1",
            "nota_adicional": None,
        },
        on_conflict="fecha,tipo_comida",
    )
    assert resultado == creada


def test_guardar_comida_tipo_invalido_lanza_valueerror_sin_tocar_cliente(
    cliente_mock,
):
    """Un tipo_comida inválido lanza ValueError sin llegar a llamar a .table()."""
    with pytest.raises(ValueError):
        database.guardar_comida("2026-07-18", "Tipo inventado")

    cliente_mock.table.assert_not_called()


def test_obtener_menu_rango_usa_select_embed_y_rango_de_fechas(cliente_mock):
    """obtener_menu_rango usa select con embed "*, recetas(*)" y .gte/.lte por fecha."""
    menu = [{"id": "m1", "fecha": "2026-07-18", "recetas": {"titulo": "X"}}]
    consulta = (
        cliente_mock.table.return_value.select.return_value.gte.return_value.lte.return_value.order.return_value
    )
    consulta.execute.return_value.data = menu

    resultado = database.obtener_menu_rango("2026-07-01", "2026-07-31")

    cliente_mock.table.assert_called_with("menus_semanales")
    cliente_mock.table.return_value.select.assert_called_with("*, recetas(*)")
    cliente_mock.table.return_value.select.return_value.gte.assert_called_with(
        "fecha", "2026-07-01"
    )
    cliente_mock.table.return_value.select.return_value.gte.return_value.lte.assert_called_with(
        "fecha", "2026-07-31"
    )
    assert resultado == menu


# -----------------------------------------------------------------------------
# 3. metricas_salud
# -----------------------------------------------------------------------------


def test_registrar_metricas_solo_peso_omite_los_campos_none(cliente_mock):
    """Con solo peso, el payload no incluye altura/grasa/cintura/notas y usa on_conflict=fecha."""
    creada = {"id": "s1", "fecha": "2026-07-18", "peso": 70.0}
    cliente_mock.table.return_value.upsert.return_value.execute.return_value.data = [
        creada
    ]

    resultado = database.registrar_metricas("2026-07-18", peso=70.0)

    llamada = cliente_mock.table.return_value.upsert.call_args
    payload = llamada.args[0]
    assert payload == {"fecha": "2026-07-18", "peso": 70.0}
    for clave in ("altura", "porcentaje_grasa", "perimetro_cintura", "notas"):
        assert clave not in payload
    assert llamada.kwargs["on_conflict"] == "fecha"
    assert resultado == creada


def test_registrar_metricas_con_todos_los_campos_los_incluye_todos(cliente_mock):
    """Cuando se pasan todos los campos, el payload los incluye todos."""
    cliente_mock.table.return_value.upsert.return_value.execute.return_value.data = [
        {}
    ]

    database.registrar_metricas(
        "2026-07-18",
        peso=70.0,
        altura=175.0,
        porcentaje_grasa=15.0,
        perimetro_cintura=80.0,
        notas="[TEST] nota",
    )

    payload = cliente_mock.table.return_value.upsert.call_args.args[0]
    assert payload == {
        "fecha": "2026-07-18",
        "peso": 70.0,
        "altura": 175.0,
        "porcentaje_grasa": 15.0,
        "perimetro_cintura": 80.0,
        "notas": "[TEST] nota",
    }


# -----------------------------------------------------------------------------
# 4. actividad_deporte
# -----------------------------------------------------------------------------


def test_registrar_actividad_sin_fecha_no_incluye_la_clave(cliente_mock):
    """Sin fecha, el payload no contiene la clave "fecha" (la BD asigna now())."""
    cliente_mock.table.return_value.insert.return_value.execute.return_value.data = [
        {}
    ]

    database.registrar_actividad(tipo_actividad="Pesas", duracion_minutos=45)

    payload = cliente_mock.table.return_value.insert.call_args.args[0]
    assert "fecha" not in payload


def test_registrar_actividad_con_fecha_incluye_la_clave(cliente_mock):
    """Con fecha explícita, el payload incluye la clave "fecha" con ese valor."""
    cliente_mock.table.return_value.insert.return_value.execute.return_value.data = [
        {}
    ]

    database.registrar_actividad(
        tipo_actividad="Pesas",
        duracion_minutos=45,
        fecha="2026-07-18T10:00:00+00:00",
    )

    payload = cliente_mock.table.return_value.insert.call_args.args[0]
    assert payload["fecha"] == "2026-07-18T10:00:00+00:00"


def test_registrar_actividad_intensidad_invalida_lanza_valueerror_sin_tocar_cliente(
    cliente_mock,
):
    """Una intensidad inválida lanza ValueError sin llegar a llamar a .table()."""
    with pytest.raises(ValueError):
        database.registrar_actividad(
            tipo_actividad="Pesas",
            duracion_minutos=30,
            intensidad="Intensidad inventada",
        )

    cliente_mock.table.assert_not_called()


# -----------------------------------------------------------------------------
# 5. lista_compra
# -----------------------------------------------------------------------------


def test_marcar_comprado_true_llama_update_y_eq(cliente_mock):
    """marcar_comprado(id, True) llama a .update({"comprado": True}).eq("id", id)."""
    actualizado = {"id": "i1", "comprado": True}
    consulta = cliente_mock.table.return_value.update.return_value.eq.return_value
    consulta.execute.return_value.data = [actualizado]

    resultado = database.marcar_comprado("i1", True)

    cliente_mock.table.assert_called_with("lista_compra")
    cliente_mock.table.return_value.update.assert_called_with({"comprado": True})
    cliente_mock.table.return_value.update.return_value.eq.assert_called_with(
        "id", "i1"
    )
    assert resultado == actualizado


def test_marcar_comprado_false_llama_update_con_false(cliente_mock):
    """marcar_comprado(id, False) llama a .update({"comprado": False})."""
    actualizado = {"id": "i1", "comprado": False}
    consulta = cliente_mock.table.return_value.update.return_value.eq.return_value
    consulta.execute.return_value.data = [actualizado]

    resultado = database.marcar_comprado("i1", False)

    cliente_mock.table.return_value.update.assert_called_with({"comprado": False})
    assert resultado == actualizado


def test_vaciar_comprados_llama_delete_y_eq(cliente_mock):
    """vaciar_comprados llama a .delete().eq("comprado", True)."""
    database.vaciar_comprados()

    cliente_mock.table.assert_called_with("lista_compra")
    cliente_mock.table.return_value.delete.return_value.eq.assert_called_with(
        "comprado", True
    )


# -----------------------------------------------------------------------------
# get_client
# -----------------------------------------------------------------------------


def test_get_client_sin_variables_de_entorno_lanza_runtimeerror(monkeypatch):
    """Sin SUPABASE_URL/SUPABASE_SECRET_KEY y sin cliente ya creado, lanza RuntimeError."""
    anterior = database._client
    database._client = None
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    try:
        with pytest.raises(RuntimeError, match=r"\.env"):
            database.get_client()
    finally:
        database._client = anterior
