"""
tests/test_reports_rag.py
Pruebas Unitarias e Integración para el Pipeline Voice-to-Report Multimodal (CU-07).
Semestre 2/2026 - INF512 (Ingeniería de Software II)
Responsable: Nataly Martínez (ms5_ia_mcp_backend)
"""

import io
import os
import pytest
from httpx import AsyncClient, ASGITransport
import openpyxl

from services.reports_rag.rag_engine import RAGEngine, ReporteParametros
from services.reports_rag.multimodal_generator import MultimodalGenerator
from services.reports_rag.whisper_service import WhisperService
from services.reports_rag.reports_service import ReportsService
from services.security import crear_token_prueba, COOKIE_NAME
from api.main_ia import app_ia


@pytest.fixture
def rag():
    return RAGEngine()


@pytest.fixture
def generator():
    return MultimodalGenerator()


def test_rag_extraccion_parametros(rag):
    # Prueba detección de cuadrante Norte y foco en agua
    p1 = rag.extraer_parametros("Por favor emitir informe hídrico y camiones en Cuadrante Norte")
    assert p1.cuadrante == "NORTE"
    assert "AGUA" in p1.enfasis_recursos
    assert "FLOTA" in p1.enfasis_recursos

    # Prueba detección de cuadrante Centro
    p2 = rag.extraer_parametros("Estado de hidrantes e insumos en cuadrante Centro")
    assert p2.cuadrante == "CENTRO"
    assert "HIDRANTES" in p2.enfasis_recursos

    # Prueba por defecto cuadrante TODOS
    p3 = rag.extraer_parametros("Situación general del cuerpo de bomberos")
    assert p3.cuadrante == "TODOS"


def test_rag_calculo_metricas_zero_hallucinations(rag):
    """
    Verifica que las operaciones numéricas sean 100% exactas y calculadas en Python.
    Flota Norte en mock:
      CAM-B01: agua_actual=8500, cap_max=10000, estado=DISPONIBLE
      CAM-B03: agua_actual=1800, cap_max=2000, estado=DISPONIBLE
    Esperado:
      total_camiones = 2
      camiones_disponibles = 2
      total_litros_agua = 10300
      capacidad_max_agua = 12000
      pct_agua = round(10300 / 12000 * 100, 1) = 85.8%
    """
    params = ReporteParametros(cuadrante="NORTE", tipo_reporte="RECURSOS_HIDRICOS")
    datos = rag.calcular_metricas(params)
    m = datos["metricas"]

    assert m.total_camiones == 2
    assert m.camiones_disponibles == 2
    assert m.total_litros_agua == 10300
    assert m.capacidad_max_agua == 12000
    assert m.porcentaje_disponibilidad_agua == 85.8
    assert m.hidrantes_totales == 2
    assert m.hidrantes_operativos == 2
    assert m.litros_espuma_disponibles == 1450


def test_rag_sintesis_markdown_estructura(rag):
    resultado = rag.sintetizar_markdown(
        instruccion_voz="Requerimiento urgente de situación en Cuadrante Norte",
        id_reporte="REP-TEST-123"
    )
    assert resultado["id_reporte"] == "REP-TEST-123"
    assert "Cuadrante NORTE" in resultado["resumen_radial"]
    assert "10.300 litros de agua" in resultado["resumen_radial"] or "10300 litros de agua" in resultado["resumen_radial"]

    md = resultado["markdown"]
    assert "# CUERPO DE BOMBEROS — INFORME EJECUTIVO DE SITUACIÓN" in md
    assert "## 1. Resumen Ejecutivo (Briefing Radial)" in md
    assert "## 2. Indicadores Clave de Desempeño (KPIs de Emergencia)" in md
    assert "## 3. Estado de la Flota Vehicular Asignada" in md
    assert "CAM-B01" in md or "B-01-SCZ" in md


def test_generador_pdf_weasyprint(rag, generator):
    datos = rag.sintetizar_markdown("Reporte táctico cuadrante centro", "REP-PDF-001")
    pdf_bytes = generator.generar_pdf(datos)
    
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 5000
    # Validación del magic header estándar de PDF (%PDF)
    assert pdf_bytes.startswith(b"%PDF")


def test_generador_excel_openpyxl(rag, generator):
    datos = rag.sintetizar_markdown("Reporte cuadrante norte", "REP-XLS-001")
    excel_bytes = generator.generar_excel(datos)

    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 2000

    # Cargar el libro en memoria para verificar hojas y fórmulas
    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes), data_only=False)
    sheet_names = wb.sheetnames
    assert "Resumen Táctico" in sheet_names
    assert "Flota y Camiones" in sheet_names
    assert "Hidrantes e Insumos" in sheet_names

    ws_flota = wb["Flota y Camiones"]
    # Verificar existencia de la fórmula =SUM(...)
    encontro_formula = False
    for row in ws_flota.iter_rows(values_only=True):
        for cell_val in row:
            if isinstance(cell_val, str) and cell_val.startswith("=SUM"):
                encontro_formula = True
                break
    assert encontro_formula is True, "La hoja de Flota debe contener al menos una fórmula =SUM de agregación contable."


def test_whisper_service_manejo_audio_vacio():
    ws = WhisperService()
    res = ws.transcribir_audio_bytes(b"")
    assert res == ""


@pytest.mark.asyncio
async def test_reports_service_end_to_end():
    service = ReportsService()
    res = await service.procesar_comando_texto(
        instruccion="Situación de camiones y agua en Cuadrante Norte",
        generar_multimodal=True,
        voz_tts="es-BO-MarceloNeural"
    )

    assert res.id_reporte.startswith("REP-")
    assert res.cuadrante == "NORTE"
    assert res.metricas_clave["total_litros_agua"] == 10300
    assert res.pdf_url is not None
    assert res.excel_url is not None
    assert len(res.etapas_completadas) == 4

    # Verificar existencia física de archivos compilados
    pdf_path = service.obtener_ruta_artefacto(res.id_reporte, "pdf")
    excel_path = service.obtener_ruta_artefacto(res.id_reporte, "excel")
    md_content = service.obtener_contenido_markdown(res.id_reporte)

    assert pdf_path is not None and os.path.exists(pdf_path)
    assert excel_path is not None and os.path.exists(excel_path)
    assert md_content is not None and len(md_content) > 100


# =========================================================================
# PRUEBAS DE INTEGRACIÓN DE ENDPOINTS API (HTTPX) Y SEGURIDAD SSO
# =========================================================================

@pytest.mark.asyncio
async def test_api_generar_reporte_por_texto_con_token_operador():
    token_operador = crear_token_prueba(rol="OPERADOR")
    transport = ASGITransport(app=app_ia)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "instruccion": "Informe táctico de abastecimiento en Cuadrante Centro",
            "generar_multimodal": True
        }
        headers = {"Authorization": f"Bearer {token_operador}"}
        resp = await client.post("/api/v1/reportes/generar-por-texto", json=payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "id_reporte" in data
        assert data["cuadrante"] == "CENTRO"
        assert "pdf_url" in data
        assert "excel_url" in data

        id_reporte = data["id_reporte"]

        # Descargar PDF compilado con token
        pdf_resp = await client.get(f"/api/v1/reportes/descargar/pdf/{id_reporte}", headers=headers)
        assert pdf_resp.status_code == 200
        assert pdf_resp.headers["content-type"] == "application/pdf"
        assert len(pdf_resp.content) > 5000

        # Descargar Excel compilado con token
        excel_resp = await client.get(f"/api/v1/reportes/descargar/excel/{id_reporte}", headers=headers)
        assert excel_resp.status_code == 200
        assert "spreadsheetml" in excel_resp.headers["content-type"]

        # Consultar Markdown con token
        md_resp = await client.get(f"/api/v1/reportes/{id_reporte}", headers=headers)
        assert md_resp.status_code == 200
        assert "markdown" in md_resp.json()


@pytest.mark.asyncio
async def test_api_reportes_sin_autenticacion_retorna_401():
    """Verifica que el acceso anónimo sea rechazado inmediatamente con HTTP 401."""
    transport = ASGITransport(app=app_ia)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/reportes/generar-por-texto",
            json={"instruccion": "Intento no autorizado de generación", "generar_multimodal": False}
        )
        assert resp.status_code == 401
        assert "Acceso no autorizado" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_api_reportes_token_invalido_retorna_401():
    """Verifica que un token alterado o malformado retorne HTTP 401."""
    transport = ASGITransport(app=app_ia)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": "Bearer token_falsificado_y_manipulado_123"}
        resp = await client.post(
            "/api/v1/reportes/generar-por-texto",
            json={"instruccion": "Prueba de token invalido", "generar_multimodal": False},
            headers=headers
        )
        assert resp.status_code == 401
        assert "inválido" in resp.json()["detail"] or "alterado" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_api_reportes_token_expirado_retorna_401():
    """Verifica que un token vencido retorne HTTP 401."""
    token_expirado = crear_token_prueba(rol="OPERADOR", exp_seconds=-3600)
    transport = ASGITransport(app=app_ia)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token_expirado}"}
        resp = await client.post(
            "/api/v1/reportes/generar-por-texto",
            json={"instruccion": "Prueba de token expirado", "generar_multimodal": False},
            headers=headers
        )
        assert resp.status_code == 401
        assert "expirada" in resp.json()["detail"] or "vencido" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_api_reportes_rol_bombero_retorna_403():
    """
    Control RBAC: Rol 'BOMBERO' tiene prohibido emitir reportes tácticos de comando.
    Debe retornar HTTP 403 Forbidden.
    """
    token_bombero = crear_token_prueba(rol="BOMBERO")
    transport = ASGITransport(app=app_ia)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token_bombero}"}
        resp = await client.post(
            "/api/v1/reportes/generar-por-texto",
            json={"instruccion": "Intento de bombero de emitir reporte", "generar_multimodal": False},
            headers=headers
        )
        assert resp.status_code == 403
        assert "Acceso denegado" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_api_reportes_autenticado_por_cookie_httponly():
    """Verifica que la cookie HttpOnly 'token_sesion' (emitida por MS-01) sea aceptada."""
    token_admin = crear_token_prueba(rol="ADMINISTRADOR")
    transport = ASGITransport(app=app_ia)
    async with AsyncClient(transport=transport, base_url="http://test", cookies={COOKIE_NAME: token_admin}) as client:
        payload = {
            "instruccion": "Resumen por administrador via Cookie HttpOnly",
            "generar_multimodal": False
        }
        resp = await client.post("/api/v1/reportes/generar-por-texto", json=payload)
        assert resp.status_code == 200
        assert resp.json()["id_reporte"] is not None


@pytest.mark.asyncio
async def test_api_mcp_validar_sql():
    transport = ASGITransport(app=app_ia)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Consulta válida
        resp_valida = await client.post(
            "/api/v1/mcp/validar-sql",
            json={"sql": "SELECT id, caudal_litros_min FROM hidrantes WHERE estado = 'OPERATIVO'"}
        )
        assert resp_valida.status_code == 200
        assert resp_valida.json()["valido"] is True

        # 2. Inyección destructiva bloqueada
        resp_invalida = await client.post(
            "/api/v1/mcp/validar-sql",
            json={"sql": "DROP TABLE hidrantes;"}
        )
        assert resp_invalida.status_code == 200
        assert resp_invalida.json()["valido"] is False


@pytest.mark.asyncio
async def test_api_mcp_ejecutar_sql_seguro_y_herramientas():
    transport = ASGITransport(app=app_ia)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Ejecución segura permitida
        resp_ok = await client.post(
            "/api/v1/mcp/ejecutar-sql-seguro",
            json={"consulta_sql": "SELECT * FROM camiones WHERE cuadrante = 'NORTE'"}
        )
        assert resp_ok.status_code == 200
        assert resp_ok.json()["exito"] is True
        assert resp_ok.json()["transaccion"] == "SET TRANSACTION READ ONLY;"

        # Ejecución rechazada (403 Forbidden)
        resp_bloqueada = await client.post(
            "/api/v1/mcp/ejecutar-sql-seguro",
            json={"consulta_sql": "UPDATE camiones SET agua_actual = 0;"}
        )
        assert resp_bloqueada.status_code == 403

        # Listado de catálogo de herramientas
        resp_cat = await client.get("/api/v1/mcp/herramientas")
        assert resp_cat.status_code == 200
        assert resp_cat.json()["total_herramientas"] >= 4

        # Invocación de herramienta tipada
        resp_tool = await client.post(
            "/api/v1/mcp/herramientas/verificar_hidrantes_cercanos/ejecutar",
            json={"parametros": {"latitud": -17.7654, "longitud": -63.1432, "radio_metros": 500}}
        )
        assert resp_tool.status_code == 200
        assert resp_tool.json()["exito"] is True
        assert len(resp_tool.json()["resultados"]) >= 1
