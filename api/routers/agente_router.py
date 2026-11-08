from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from services.tactical_agents.despachador_react import agente_despachador

agente_router = APIRouter(prefix="/api/v1/agente", tags=["Agentes Autónomos ReAct (Maikol)"])

class DespachoTacticoRequest(BaseModel):
    incidenteId: str = Field(..., example="INC-2026-SCZ-101")
    tipoIncidente: str = Field(..., example="INDUSTRIAL")
    latitud: float = Field(..., example=-17.7833)
    longitud: float = Field(..., example=-63.1821)
    litrosMinimos: Optional[int] = Field(4000, example=5000)
    descripcion: Optional[str] = Field("Fuego activo en depósito de llantas con riesgo de propagación", example="Fuego activo")

@agente_router.post("/despacho-tactico")
async def proponer_despacho_tactico(request: DespachoTacticoRequest) -> Dict[str, Any]:
    """
    Endpoint del Agente Despachador Táctico (ReAct Framework).
    Ejecuta el loop cognitivo autónomo:
    Thought -> Action -> Observation -> Final Answer.
    Genera la recomendación táctica y los datos para el botón Human-in-the-Loop de Comandos.
    """
    resultado = agente_despachador.ejecutar_ciclo_react(
        incidente_id=request.incidenteId,
        tipo_incidente=request.tipoIncidente,
        latitud=request.latitud,
        longitud=request.longitud,
        litros_minimos=request.litrosMinimos or 4000,
        descripcion_siniestro=request.descripcion or ""
    )
    return resultado
