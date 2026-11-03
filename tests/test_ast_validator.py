"""
tests/test_ast_validator.py
Pruebas Unitarias para la Capa Defensiva de Seguridad AST (sqlglot) y Servidor FastMCP.
Semestre 2/2026 - INF512 (Ingeniería de Software II)
Responsable: Nataly Martínez (ms5_ia_mcp_backend)
"""

import pytest
from services.mcp_security.ast_validator import validar_consulta_ast, ASTValidator
from services.mcp_security.mcp_server import (
    ejecutar_consulta_analitica_segura,
    verificar_hidrantes_cercanos,
    consultar_stock_estacion,
    consultar_camiones_disponibles
)


def test_ast_select_valido_hidrantes():
    sql = "SELECT id, caudal_litros_min, estado FROM hidrantes WHERE estado = 'OPERATIVO';"
    resultado = validar_consulta_ast(sql)
    assert resultado.valido is True
    assert resultado.tipo_sentencia == "SELECT"
    assert "hidrantes" in resultado.tablas_detectadas
    assert resultado.motivo_rechazo is None


def test_ast_select_valido_camiones_join():
    sql = "SELECT c.id, c.agua_actual, c.capacidad_agua FROM camiones c WHERE c.cuadrante = 'NORTE' ORDER BY c.agua_actual DESC"
    resultado = validar_consulta_ast(sql)
    assert resultado.valido is True
    assert "camiones" in resultado.tablas_detectadas


def test_ast_bloqueo_multiples_sentencias_semicolon():
    # Intento clásico de piggybacking SQL
    sql = "SELECT * FROM hidrantes; DROP TABLE hidrantes;"
    resultado = validar_consulta_ast(sql)
    assert resultado.valido is False
    assert "Multi-sentencias" in resultado.motivo_rechazo or "DROP" in resultado.motivo_rechazo


def test_ast_bloqueo_token_drop():
    sql = "DROP TABLE hidrantes;"
    resultado = validar_consulta_ast(sql)
    assert resultado.valido is False
    assert "no permitida" in resultado.motivo_rechazo or "DROP" in resultado.motivo_rechazo


def test_ast_bloqueo_token_truncate():
    sql = "TRUNCATE TABLE camiones;"
    resultado = validar_consulta_ast(sql)
    assert resultado.valido is False
    assert resultado.valido is False


def test_ast_bloqueo_token_delete():
    sql = "DELETE FROM incidentes WHERE id = 'INC-001';"
    resultado = validar_consulta_ast(sql)
    assert resultado.valido is False
    assert resultado.tipo_sentencia in ["DELETE", "DESTRUCTIVE_TOKEN", "RECHAZADA_POR_TOKEN"]


def test_ast_bloqueo_token_update():
    sql = "UPDATE camiones SET agua_actual = 0 WHERE id = 'CAM-B01';"
    resultado = validar_consulta_ast(sql)
    assert resultado.valido is False


def test_ast_bloqueo_tablas_sensibles_usuarios():
    # Intento de robo de credenciales / usuarios SSO
    sql = "SELECT username, password_hash FROM tb_usuarios_sso;"
    resultado = validar_consulta_ast(sql)
    assert resultado.valido is False
    assert "protegidas" in resultado.motivo_rechazo or "credenciales" in resultado.motivo_rechazo or "lista blanca" in resultado.motivo_rechazo


def test_ast_bloqueo_tablas_sistema_postgres():
    sql = "SELECT tablename FROM pg_catalog.pg_tables;"
    resultado = validar_consulta_ast(sql)
    assert resultado.valido is False
    assert "lista blanca" in resultado.motivo_rechazo or "sistema" in resultado.motivo_rechazo


def test_ast_forzar_transaccion_read_only():
    tx = ASTValidator.forzar_transaccion_solo_lectura()
    assert tx == "SET TRANSACTION READ ONLY;"


def test_mcp_ejecutar_consulta_segura_permitida():
    sql = "SELECT id, caudal_litros_min, zona FROM hidrantes WHERE zona = 'NORTE'"
    res = ejecutar_consulta_analitica_segura(sql)
    assert res["exito"] is True
    assert res["transaccion"] == "SET TRANSACTION READ ONLY;"
    assert len(res["datos"]) > 0


def test_mcp_ejecutar_consulta_segura_inyeccion_rechazada():
    sql = "SELECT * FROM camiones; DROP DATABASE bomberos;"
    res = ejecutar_consulta_analitica_segura(sql)
    assert res["exito"] is False
    assert "error_seguridad" in res
    assert res["transaccion"] == "ABORTADA_DEFENSIVAMENTE"


def test_mcp_herramienta_tipada_hidrantes():
    # -17.7654, -63.1432 es la coordenada del hidrante HID-SCZ-101
    cercanos = verificar_hidrantes_cercanos(latitud=-17.7654, longitud=-63.1432, radio_metros=300)
    assert len(cercanos) >= 1
    assert cercanos[0]["id"] == "HID-SCZ-101"
    assert cercanos[0]["distancia_metros"] <= 300


def test_mcp_herramienta_tipada_stock():
    stock = consultar_stock_estacion(nombre_estacion="Central", categoria="QUIMICO")
    assert len(stock) >= 1
    assert "AFFF" in stock[0]["nombre"]


def test_mcp_herramienta_tipada_camiones():
    camiones = consultar_camiones_disponibles(cuadrante="NORTE")
    assert len(camiones) >= 1
    assert all(c["cuadrante"] == "NORTE" for c in camiones)
