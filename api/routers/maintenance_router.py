"""
api/routers/maintenance_router.py
Router FastAPI para el Motor de Mantenimiento Predictivo con Machine Learning (CU-06).
Semestre 2/2026 - INF512 (Ingeniería de Software II)
Responsable: Jael Mamani (ms5_ia_mcp_backend / ms3_inventario_backend)
"""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from services.predictive_maintenance.maintenance_model import (
    EquipoTelemetriaDTO,
    PrediccionMantenimientoDTO,
    predecir_mantenimiento_equipo,
    auditar_lote_equipos,
    obtener_umbrales_referencia,
)

maintenance_router = APIRouter(
    prefix="/api/v1/mantenimiento",
    tags=["Mantenimiento Predictivo IA (Jael)"]
)


class AuditoriaLoteRequest(BaseModel):
    equipos: List[EquipoTelemetriaDTO] = Field(..., min_length=1, description="Lista de equipos a auditar")


class AuditoriaLoteResponse(BaseModel):
    total_evaluados: int
    equipos_aptos: int
    equipos_en_mantenimiento: int
    equipos_descarte: int
    detalles: List[PrediccionMantenimientoDTO]


@maintenance_router.post(
    "/predecir",
    response_model=PrediccionMantenimientoDTO,
    summary="Evaluar condición de fatiga y predecir fallo de un equipo",
    description="Aplica un ensemble supervisado de Random Forest para estimar vida útil restante y condición de combate."
)
async def predecir_equipo(payload: EquipoTelemetriaDTO):
    try:
        return predecir_mantenimiento_equipo(payload)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en la inferencia del modelo predictivo: {str(e)}"
        )


@maintenance_router.post(
    "/auditar-lote",
    response_model=AuditoriaLoteResponse,
    summary="Auditoría masiva de maquinaria bomberil para el panel de Logística",
    description="Permite a MS-03 Inventario enviar toda la flota de herramientas y clasificar automáticamente los que deben pasar a taller."
)
async def auditar_lote(payload: AuditoriaLoteRequest):
    try:
        predicciones = auditar_lote_equipos(payload.equipos)
        aptos = sum(1 for p in predicciones if p.estado_recomendado == "OPERATIVO")
        mantenimiento = sum(1 for p in predicciones if p.estado_recomendado == "REQUERIR_MANTENIMIENTO_PREVENTIVO")
        descarte = sum(1 for p in predicciones if p.estado_recomendado == "DESCARTE_INMEDIATO")

        return AuditoriaLoteResponse(
            total_evaluados=len(predicciones),
            equipos_aptos=aptos,
            equipos_en_mantenimiento=mantenimiento,
            equipos_descarte=descarte,
            detalles=predicciones
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en la auditoría en lote: {str(e)}"
        )


@maintenance_router.get(
    "/umbrales",
    summary="Consultar estándares de fatiga recomendados por normativa",
    description="Retorna los umbrales NFPA 1911/1962 aplicados por el modelo de IA."
)
async def consultar_umbrales():
    return obtener_umbrales_referencia()
