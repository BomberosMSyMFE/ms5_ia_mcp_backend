import numpy as np
from sklearn.cluster import DBSCAN
from typing import List, Dict, Any

def calcular_hotspots_espaciales(
    coordenadas_gps: List[List[float]],
    eps_km: float = 1.5,
    min_samples: int = 4
) -> Dict[str, Any]:
    """
    ML No Supervisado (DBSCAN con Métrica Haversine):
    Agrupa coordenadas geográficas de incidentes para detectar zonas críticas (hotspots).
    
    Parámetros:
    - coordenadas_gps: Lista de pares [latitud, longitud] en grados decimales.
    - eps_km: Radio de vecindad máximo en kilómetros (por defecto 1.5 km).
    - min_samples: Cantidad mínima de incidentes para constituir un cluster de alta densidad (por defecto 4).
    
    Retorna:
    - total_puntos: Cantidad de coordenadas procesadas.
    - total_clusters: Cantidad de zonas calientes identificadas.
    - puntos_ruido: Focos aislados descartados como anomalías/ruido.
    - clusters: Lista detallada con centroides, radio y puntos asignados.
    """
    if not coordenadas_gps or len(coordenadas_gps) < min_samples:
        return {
            "algoritmo": "DBSCAN (Density-Based Spatial Clustering of Applications with Noise)",
            "metrica": "Haversine",
            "radio_epsilon_km": eps_km,
            "muestras_minimas": min_samples,
            "total_puntos_procesados": len(coordenadas_gps) if coordenadas_gps else 0,
            "total_clusters_detectados": 0,
            "total_focos_aislados_ruido": len(coordenadas_gps) if coordenadas_gps else 0,
            "focos_aislados": coordenadas_gps or [],
            "zonas_criticas": [],
            "mensaje": f"Se requieren al menos {min_samples} coordenadas para ejecutar DBSCAN espacial."
        }

    # 1. Conversión de coordenadas a array numpy
    coords_np = np.array(coordenadas_gps)
    
    # 2. Conversión a radianes (obligatorio para la fórmula de Haversine sobre esfera terrestre)
    coords_rad = np.radians(coords_np)
    
    # 3. Cálculo de epsilon en radianes: Radio Tierra R = 6371.0088 km
    radio_tierra_km = 6371.0088
    epsilon_radianes = eps_km / radio_tierra_km
    
    # 4. Ajuste del modelo DBSCAN
    db = DBSCAN(eps=epsilon_radianes, min_samples=min_samples, metric='haversine')
    etiquetas = db.fit_predict(coords_rad)
    
    clusters_dict: Dict[int, List[List[float]]] = {}
    ruido_puntos: List[List[float]] = []
    
    for idx, label in enumerate(etiquetas):
        coord_original = [float(coords_np[idx][0]), float(coords_np[idx][1])]
        if label == -1:
            # -1 indica Ruido según DBSCAN (focos aislados / no sistemáticos)
            ruido_puntos.append(coord_original)
        else:
            if label not in clusters_dict:
                clusters_dict[label] = []
            clusters_dict[label].append(coord_original)
            
    # 5. Estructurar reporte de zonas críticas con centroides
    clusters_resumen = []
    for cluster_id, puntos in clusters_dict.items():
        arr_pts = np.array(puntos)
        centroide_lat = float(np.mean(arr_pts[:, 0]))
        centroide_lon = float(np.mean(arr_pts[:, 1]))
        
        clusters_resumen.append({
            "cluster_id": int(cluster_id),
            "cantidad_incidentes": len(puntos),
            "centroide": {
                "latitud": round(centroide_lat, 6),
                "longitud": round(centroide_lon, 6)
            },
            "puntos_coordenadas": puntos,
            "clasificacion_riesgo": "CRITICO" if len(puntos) >= 10 else "ALTO" if len(puntos) >= 6 else "MEDIO"
        })
        
    # Ordenar de mayor a menor criticidad
    clusters_resumen.sort(key=lambda c: c["cantidad_incidentes"], reverse=True)
    
    return {
        "algoritmo": "DBSCAN (Density-Based Spatial Clustering of Applications with Noise)",
        "metrica": "Haversine (Distancia sobre la curvatura terrestre)",
        "radio_epsilon_km": eps_km,
        "muestras_minimas": min_samples,
        "total_puntos_procesados": len(coordenadas_gps),
        "total_clusters_detectados": len(clusters_resumen),
        "total_focos_aislados_ruido": len(ruido_puntos),
        "focos_aislados": ruido_puntos,
        "zonas_criticas": clusters_resumen
    }
