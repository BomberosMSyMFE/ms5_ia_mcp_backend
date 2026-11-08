from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from services.spatial_clustering.dbscan_clustering import calcular_hotspots_espaciales

ml_router = APIRouter(prefix="/api/v1/ml", tags=["Machine Learning Espacial DBSCAN (Maikol)"])

class HotspotRequest(BaseModel):
    coordenadas: List[List[float]] = Field(
        ..., 
        description="Lista de coordenadas [[lat, lon], ...]",
        example=[
            [-17.7550, -63.1601],
            [-17.7555, -63.1608],
            [-17.7548, -63.1595],
            [-17.7560, -63.1610],
            [-17.8100, -63.1500]
        ]
    )
    radioEpsilonKm: Optional[float] = Field(1.5, example=1.5, description="Radio de vecindad en km")
    minSamples: Optional[int] = Field(4, example=4, description="Mínimo de puntos para formar cluster")

# Dataset histórico calibrado en Santa Cruz de la Sierra:
# Cluster 1: Parque Industrial (Zona Química de Alto Riesgo)
# Cluster 2: Plan 3000 (Zona Urbana de Alta Densidad)
# Outliers (Pastizales aislados en periferia)
PUNTOS_DEMO_SANTA_CRUZ = [
    # Cluster 1: Parque Industrial
    [-17.7550, -63.1601],
    [-17.7555, -63.1608],
    [-17.7548, -63.1595],
    [-17.7562, -63.1612],
    [-17.7540, -63.1605],
    [-17.7558, -63.1590],
    
    # Cluster 2: Plan 3000
    [-17.8100, -63.1500],
    [-17.8105, -63.1508],
    [-17.8095, -63.1495],
    [-17.8110, -63.1512],
    [-17.8102, -63.1503],
    
    # Outliers / Ruido
    [-17.7100, -63.2200],
    [-17.8500, -63.1000]
]

@ml_router.post("/hotspots")
async def analizar_hotspots_espaciales(request: HotspotRequest) -> Dict[str, Any]:
    """
    Ejecuta el clustering no supervisado DBSCAN con métrica esférica Haversine
    para detectar focos de calor y zonas críticas de incendio.
    """
    return calcular_hotspots_espaciales(
        coordenadas_gps=request.coordenadas,
        eps_km=request.radioEpsilonKm or 1.5,
        min_samples=request.minSamples or 4
    )

@ml_router.get("/hotspots/demo")
async def demo_hotspots_santa_cruz() -> Dict[str, Any]:
    """
    Ejecuta DBSCAN sobre el histórico de incendios registrados en Santa Cruz de la Sierra.
    Demuestra la detección automática de clusters y descarte de ruido.
    """
    return calcular_hotspots_espaciales(
        coordenadas_gps=PUNTOS_DEMO_SANTA_CRUZ,
        eps_km=1.5,
        min_samples=4
    )
