"""Tests de integración de database.py: golpean la base de datos real de Supabase.

Todos los tests de este módulo están marcados con `@pytest.mark.integration`
(vía `pytestmark` a nivel de módulo) y quedan excluidos por defecto
(`uv run pytest`); se ejecutan explícitamente con `uv run pytest -m integration`.

Requieren un `.env` válido con SUPABASE_URL y SUPABASE_SECRET_KEY: si faltan,
el módulo completo se omite (skip) en la colección. Todos los datos que crean
usan el prefijo "[TEST]" y fechas de 1999, y se limpian con fixtures/bloques
try-finally para no dejar residuos en la base de datos real.
"""

import os

import pytest

import database  # el import dispara load_dotenv() dentro de database.py

pytestmark = pytest.mark.integration

if not os.environ.get("SUPABASE_URL") or not os.environ.get("SUPABASE_SECRET_KEY"):
    pytest.skip(
        "Faltan las variables de entorno SUPABASE_URL y/o SUPABASE_SECRET_KEY: "
        "se omiten los tests de integración (requieren un .env válido).",
        allow_module_level=True,
    )


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def receta_de_prueba():
    """Crea una receta [TEST] y garantiza su borrado al finalizar el test."""
    receta = database.crear_receta(
        {
            "titulo": "[TEST] Receta de prueba",
            "ingredientes": ["[TEST] ingrediente A", "[TEST] ingrediente B"],
            "categoria": "Desayuno",
            "tiempo_preparacion": 5,
            "calorias": 200,
            "proteinas": 15,
            "carbohidratos": 20,
            "grasas": 5,
        }
    )
    try:
        yield receta
    finally:
        database.eliminar_receta(receta["id"])


# -----------------------------------------------------------------------------
# 1. recetas: ciclo CRUD completo
# -----------------------------------------------------------------------------


def test_ciclo_crud_recetas():
    """Crea, lee, actualiza y elimina una receta [TEST], verificando cada paso."""
    receta_creada = database.crear_receta(
        {
            "titulo": "[TEST] Receta CRUD",
            "ingredientes": ["[TEST] harina", "[TEST] huevo"],
            "categoria": "Desayuno",
            "tiempo_preparacion": 10,
            "calorias": 300,
            "proteinas": 10,
            "carbohidratos": 40,
            "grasas": 5,
        }
    )
    receta_id = receta_creada["id"]
    try:
        assert receta_creada["titulo"] == "[TEST] Receta CRUD"

        leida = database.obtener_receta(receta_id)
        assert leida is not None
        assert leida["calorias"] == 300

        actualizada = database.actualizar_receta(receta_id, {"calorias": 350})
        assert actualizada["calorias"] == 350
        assert database.obtener_receta(receta_id)["calorias"] == 350

        recetas_desayuno = database.obtener_recetas(categoria="Desayuno")
        assert any(r["id"] == receta_id for r in recetas_desayuno)
    finally:
        database.eliminar_receta(receta_id)

    assert database.obtener_receta(receta_id) is None


# -----------------------------------------------------------------------------
# 2. menus_semanales: upsert sobre (fecha, tipo_comida)
# -----------------------------------------------------------------------------


def test_upsert_menu_mismo_id_al_reasignar(receta_de_prueba):
    """guardar_comida hace upsert: reasignar (fecha, tipo_comida) conserva el mismo id."""
    fecha = "1999-01-04"
    tipo_comida = "Desayuno"
    try:
        primero = database.guardar_comida(
            fecha, tipo_comida, receta_id=receta_de_prueba["id"]
        )
        assert primero["receta_id"] == receta_de_prueba["id"]

        segundo = database.guardar_comida(
            fecha, tipo_comida, nota_adicional="[TEST] nota alternativa"
        )
        assert segundo["id"] == primero["id"]
        assert segundo["receta_id"] is None
        assert segundo["nota_adicional"] == "[TEST] nota alternativa"

        menu_rango = database.obtener_menu_rango(fecha, fecha)
        assert len(menu_rango) == 1
        assert menu_rango[0]["id"] == primero["id"]
    finally:
        database.eliminar_comida(fecha, tipo_comida)

    assert database.obtener_menu_rango(fecha, fecha) == []


def test_guardar_comida_tipo_invalido_no_toca_la_red(monkeypatch):
    """Un tipo_comida inválido lanza ValueError antes de llegar a golpear la red."""

    def _get_client_no_deberia_llamarse():
        raise AssertionError(
            "get_client() no debería invocarse cuando tipo_comida es inválido: "
            "la validación local debe fallar antes de tocar la red."
        )

    monkeypatch.setattr(database, "get_client", _get_client_no_deberia_llamarse)

    with pytest.raises(ValueError):
        database.guardar_comida("1999-01-04", "Tipo inventado")


# -----------------------------------------------------------------------------
# 3. metricas_salud: upsert que conserva campos no enviados
# -----------------------------------------------------------------------------


def test_upsert_metricas_conserva_campos_no_enviados():
    """registrar_metricas en una segunda llamada no sobrescribe con null los
    campos que no se envían explícitamente."""
    fecha = "1999-02-01"
    try:
        primero = database.registrar_metricas(
            fecha, peso=70.5, notas="[TEST] nota inicial"
        )
        assert primero["peso"] == 70.5
        assert primero["notas"] == "[TEST] nota inicial"

        segundo = database.registrar_metricas(fecha, porcentaje_grasa=15.5)
        assert segundo["porcentaje_grasa"] == 15.5
        # Campos no enviados en la segunda llamada: deben conservar su valor previo.
        assert segundo["peso"] == 70.5
        assert segundo["notas"] == "[TEST] nota inicial"

        historico = database.obtener_historico_salud(fecha, fecha)
        assert len(historico) == 1
        assert historico[0]["peso"] == 70.5
    finally:
        # database.py no expone una función de borrado para metricas_salud;
        # se limpia directamente vía el cliente para no dejar residuos [TEST].
        database.get_client().table("metricas_salud").delete().eq(
            "fecha", fecha
        ).execute()


# -----------------------------------------------------------------------------
# 4. actividad_deporte: registrar y eliminar
# -----------------------------------------------------------------------------


def test_registrar_y_eliminar_actividad():
    """Registra una sesión de actividad [TEST], la localiza en el histórico y la elimina."""
    actividad = database.registrar_actividad(
        tipo_actividad="[TEST] Pesas",
        duracion_minutos=45,
        fecha="1999-03-01T10:00:00+00:00",
        intensidad="Alta",
        volumen_total_kg=1000.0,
        comentarios="[TEST] sesión de prueba",
    )
    actividad_id = actividad["id"]
    eliminada = False
    try:
        historico = database.obtener_historico_deporte("1999-01-01", "1999-12-31")
        assert any(a["id"] == actividad_id for a in historico)

        database.eliminar_actividad(actividad_id)
        eliminada = True

        historico_tras_borrar = database.obtener_historico_deporte(
            "1999-01-01", "1999-12-31"
        )
        assert not any(a["id"] == actividad_id for a in historico_tras_borrar)
    finally:
        if not eliminada:
            database.eliminar_actividad(actividad_id)


def test_registrar_actividad_intensidad_invalida_no_toca_la_red(monkeypatch):
    """Una intensidad inválida lanza ValueError antes de llegar a golpear la red."""

    def _get_client_no_deberia_llamarse():
        raise AssertionError(
            "get_client() no debería invocarse cuando intensidad es inválida."
        )

    monkeypatch.setattr(database, "get_client", _get_client_no_deberia_llamarse)

    with pytest.raises(ValueError):
        database.registrar_actividad(
            tipo_actividad="[TEST] Actividad",
            duracion_minutos=30,
            intensidad="Intensidad inventada",
        )


# -----------------------------------------------------------------------------
# 5. lista_compra: marcar comprado y vaciar
# -----------------------------------------------------------------------------


def test_item_lista_compra_marcado_comprado_y_vaciado():
    """Marca un item [TEST] como comprado y comprueba que vaciar_comprados lo elimina.

    Nota de seguridad: `vaciar_comprados()` borra en la BD real TODOS los items
    marcados como comprados, sin filtrar por prefijo ni fecha (ver hallazgo en
    el informe de la tarea). Para no arriesgar datos reales del usuario si este
    test se ejecuta contra una base con contenido real, se guarda una copia de
    los items comprados preexistentes y se restauran (mejor esfuerzo) al
    finalizar.
    """
    preexistentes_comprados = [
        i for i in database.obtener_lista() if i.get("comprado")
    ]

    item = database.agregar_item(
        "[TEST] item de prueba", cantidad="1 ud", categoria="[TEST]"
    )
    item_id = item["id"]
    vaciado_ejecutado = False
    try:
        marcado = database.marcar_comprado(item_id, True)
        assert marcado["comprado"] is True

        pendientes = database.obtener_lista(solo_pendientes=True)
        assert not any(i["id"] == item_id for i in pendientes)

        database.vaciar_comprados()
        vaciado_ejecutado = True

        lista_tras_vaciar = database.obtener_lista()
        assert not any(i["id"] == item_id for i in lista_tras_vaciar)
    finally:
        if not vaciado_ejecutado:
            database.eliminar_item(item_id)
        for i in preexistentes_comprados:
            restaurado = database.agregar_item(
                i.get("item"), cantidad=i.get("cantidad"), categoria=i.get("categoria")
            )
            database.marcar_comprado(restaurado["id"], True)
