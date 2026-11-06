"""
tests/test_predictive_maintenance.py
Tests unitarios y de integración para el modelo de Machine Learning de Mantenimiento Predictivo (CU-06).
Semestre 2/2026 - INF512 UAGRM
Responsable: Jael Mamani
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.predictive_maintenance.maintenance_model import (
    EquipoTelemetriaDTO,
    predecir_mantenimiento_equipo,
    auditar_lote_equipos,
    obtener_umbrales_referencia,
)
from api.routers.maintenance_router import maintenance_router

test_app = FastAPI()
test_app.include_router(maintenance_router)
client = TestClient(test_app)


def test_equipo_optimo_predice_operativo():
    """Un equipo con pocas horas de uso e historial limpio debe clasificarse como OPERATIVO."""
    equipo = EquipoTelemetriaDTO(
        codigo="MOTO-HONDA-01",
        nombre="Motobomba Portátil Honda GX160",
        tipo_equipo="MOTOBOMBA",
        horas_uso_acumuladas=25.0,
        umbral_fatiga_horas=150.0,
        dias_desde_inspeccion=10,
        caudal_maximo_lpm=1500.0,
        historial_presiones_altas=0,
        incidentes_atendidos=3
    )

    prediccion = predecir_mantenimiento_equipo(equipo)

    assert prediccion.codigo == "MOTO-HONDA-01"
    assert prediccion.estado_recomendado == "OPERATIVO"
    assert prediccion.requiere_retiro_inmediato is False
    assert prediccion.porcentaje_fatiga < 50.0
    assert prediccion.dias_vida_util_restantes > 100.0
    assert "OPERATIVO" in prediccion.accion_recomendada or "APTO" in prediccion.accion_recomendada


def test_equipo_que_supera_umbral_predice_mantenimiento():
    """Un equipo que supera el umbral de fatiga de diseño debe derivarse a mantenimiento preventivo."""
    equipo = EquipoTelemetriaDTO(
        codigo="MOTO-ROSEN-02",
        nombre="Bomba de Alta Presión Rosenbauer UltraLight",
        tipo_equipo="MOTOBOMBA",
        horas_uso_acumuladas=165.0,
        umbral_fatiga_horas=150.0,
        dias_desde_inspeccion=90,
        caudal_maximo_lpm=1600.0,
        historial_presiones_altas=4,
        incidentes_atendidos=21
    )

    prediccion = predecir_mantenimiento_equipo(equipo)

    assert prediccion.codigo == "MOTO-ROSEN-02"
    assert prediccion.estado_recomendado in ["REQUERIR_MANTENIMIENTO_PREVENTIVO", "DESCARTE_INMEDIATO"]
    assert prediccion.requiere_retiro_inmediato is True
    assert prediccion.porcentaje_fatiga > 100.0
    assert prediccion.riesgo_fallo_porcentaje >= 50.0
    assert "TALLER" in prediccion.accion_recomendada or "DERIVACIÓN" in prediccion.accion_recomendada or "PELIGRO" in prediccion.accion_recomendada


def test_equipo_severamente_sobrecargado_predice_descarte():
    """Un equipo con sobreuso extremo y múltiples sobrepresiones debe alertar descarte inmediato."""
    equipo = EquipoTelemetriaDTO(
        codigo="MANG-PUNZ-99",
        nombre="Manguera de Ataque 2.5 pulg",
        tipo_equipo="MANGUERA_ALTA_PRESION",
        horas_uso_acumuladas=280.0,
        umbral_fatiga_horas=180.0,
        dias_desde_inspeccion=240,
        caudal_maximo_lpm=1500.0,
        historial_presiones_altas=14,
        incidentes_atendidos=45
    )

    prediccion = predecir_mantenimiento_equipo(equipo)

    assert prediccion.estado_recomendado == "DESCARTE_INMEDIATO"
    assert prediccion.requiere_retiro_inmediato is True
    assert prediccion.porcentaje_fatiga >= 130.0
    assert prediccion.dias_vida_util_restantes <= 10.0


def test_auditoria_en_lote_agrupa_correctamente():
    """Prueba la evaluación masiva de un inventario mixto."""
    lote = [
        EquipoTelemetriaDTO(
            codigo="EQ-01",
            nombre="Equipo Nuevo",
            tipo_equipo="MOTOBOMBA",
            horas_uso_acumuladas=15.0,
            umbral_fatiga_horas=150.0,
            dias_desde_inspeccion=5,
            historial_presiones_altas=0
        ),
        EquipoTelemetriaDTO(
            codigo="EQ-02",
            nombre="Equipo Fatigado",
            tipo_equipo="MOTOBOMBA",
            horas_uso_acumuladas=160.0,
            umbral_fatiga_horas=150.0,
            dias_desde_inspeccion=85,
            historial_presiones_altas=3
        )
    ]

    resultados = auditar_lote_equipos(lote)
    assert len(resultados) == 2
    assert resultados[0].estado_recomendado == "OPERATIVO"
    assert resultados[1].requiere_retiro_inmediato is True


def test_api_endpoint_predecir_post():
    """Verifica el endpoint FastAPI POST /api/v1/mantenimiento/predecir."""
    payload = {
        "codigo": "MOTO-API-01",
        "nombre": "Motobomba Ensayo",
        "tipo_equipo": "MOTOBOMBA",
        "horas_uso_acumuladas": 30.0,
        "umbral_fatiga_horas": 150.0,
        "dias_desde_inspeccion": 15,
        "caudal_maximo_lpm": 1500.0,
        "historial_presiones_altas": 0,
        "incidentes_atendidos": 2
    }

    response = client.post("/api/v1/mantenimiento/predecir", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["codigo"] == "MOTO-API-01"
    assert data["estado_recomendado"] == "OPERATIVO"
    assert "Random Forest" in data["modelo_ia"]


def test_api_endpoint_umbrales_get():
    """Verifica el endpoint GET /api/v1/mantenimiento/umbrales."""
    response = client.get("/api/v1/mantenimiento/umbrales")
    assert response.status_code == 200
    data = response.json()
    assert "NFPA" in data["normativa"]
    assert "MOTOBOMBA" in data["umbrales_recomendados_horas"]
