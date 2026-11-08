import pytest
from services.spatial_clustering.dbscan_clustering import calcular_hotspots_espaciales

def test_dbscan_clustering_hotspots():
    # Coordenadas calibradas en Santa Cruz con 2 clusters densos y 2 puntos de ruido
    coordenadas = [
        # Cluster 1: Parque Industrial (Zona Alta Densidad)
        [-17.7550, -63.1601],
        [-17.7555, -63.1608],
        [-17.7548, -63.1595],
        [-17.7562, -63.1612],
        [-17.7540, -63.1605],
        
        # Cluster 2: Plan 3000
        [-17.8100, -63.1500],
        [-17.8105, -63.1508],
        [-17.8095, -63.1495],
        [-17.8110, -63.1512],
        
        # Ruido (Focos aislados lejanos)
        [-17.6500, -63.3000],
        [-17.9000, -63.0500]
    ]

    resultado = calcular_hotspots_espaciales(coordenadas, eps_km=1.5, min_samples=4)

    assert resultado["total_puntos_procesados"] == 11
    assert resultado["total_clusters_detectados"] == 2
    assert resultado["total_focos_aislados_ruido"] == 2
    assert len(resultado["zonas_criticas"]) == 2
    
    # Verificar que los centroides se calcularon correctamente
    for c in resultado["zonas_criticas"]:
        assert "latitud" in c["centroide"]
        assert "longitud" in c["centroide"]
        assert c["cantidad_incidentes"] >= 4
        assert c["clasificacion_riesgo"] in ["CRITICO", "ALTO", "MEDIO"]
