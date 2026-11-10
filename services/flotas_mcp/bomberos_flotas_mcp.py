import os
import math
import logging
try:
    import psycopg2
except ImportError:
    psycopg2 = None
import httpx
from typing import List, Dict, Any, Optional

logger = logging.getLogger("bomberos_flotas_mcp")

# Parámetros de conexión configurables por entorno
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "flotas_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
MS2_FLOTAS_URL = os.getenv("MS2_FLOTAS_URL", "http://127.0.0.1:8082")

# Flota de contingencia Santa Cruz (Mock de Respaldo Alta Disponibilidad)
UNIDADES_MOCK_SANTA_CRUZ = [
    {
        "camionId": "B-01",
        "placa": "3045-ABC",
        "tipo": "CISTERNA_PESADA",
        "estado": "DISPONIBLE",
        "litrosAguaActual": 9500,
        "capacidadMaximaAgua": 10000,
        "combustiblePorcentaje": 92,
        "estacionOrigen": "Estación Central SCZ (1er Anillo)",
        "latitud": -17.7862,
        "longitud": -63.1812
    },
    {
        "camionId": "B-04",
        "placa": "2456-XYZ",
        "tipo": "ATAQUE_RAPIDO",
        "estado": "DISPONIBLE",
        "litrosAguaActual": 3200,
        "capacidadMaximaAgua": 3500,
        "combustiblePorcentaje": 88,
        "estacionOrigen": "Estación Norte (4to Anillo)",
        "latitud": -17.7780,
        "longitud": -63.1795
    },
    {
        "camionId": "B-06",
        "placa": "1122-XZY",
        "tipo": "ESCALA_TELESCOPICA",
        "estado": "DISPONIBLE",
        "litrosAguaActual": 4000,
        "capacidadMaximaAgua": 4000,
        "combustiblePorcentaje": 90,
        "estacionOrigen": "Estación Parque Industrial",
        "latitud": -17.7650,
        "longitud": -63.1900
    },
    {
        "camionId": "B-08",
        "placa": "5567-KLM",
        "tipo": "CISTERNA_PESADA",
        "estado": "DISPONIBLE",
        "litrosAguaActual": 8000,
        "capacidadMaximaAgua": 8000,
        "combustiblePorcentaje": 85,
        "estacionOrigen": "Estación Este (Villa 1ro de Mayo)",
        "latitud": -17.7550,
        "longitud": -63.1600
    },
    {
        "camionId": "B-11",
        "placa": "9901-QWE",
        "tipo": "ATAQUE_RAPIDO",
        "estado": "DISPONIBLE",
        "litrosAguaActual": 4500,
        "capacidadMaximaAgua": 5000,
        "combustiblePorcentaje": 95,
        "estacionOrigen": "Estación Plan 3000",
        "latitud": -17.8100,
        "longitud": -63.1500
    }
]

HIDRANTES_MOCK_SANTA_CRUZ = [
    {"id": "HID-SCZ-101", "latitud": -17.7654, "longitud": -63.1432, "presionPsi": 65.0, "caudalLitrosMinuto": 1800, "operativo": True},
    {"id": "HID-SCZ-102", "latitud": -17.7680, "longitud": -63.1410, "presionPsi": 72.0, "caudalLitrosMinuto": 2200, "operativo": True},
    {"id": "HID-SCZ-104", "latitud": -17.7850, "longitud": -63.1790, "presionPsi": 80.0, "caudalLitrosMinuto": 2500, "operativo": True},
    {"id": "HID-SCZ-105", "latitud": -17.8010, "longitud": -63.1650, "presionPsi": 60.0, "caudalLitrosMinuto": 1900, "operativo": True},
    {"id": "HID-SCZ-106", "latitud": -17.8090, "longitud": -63.1520, "presionPsi": 55.0, "caudalLitrosMinuto": 1600, "operativo": True}
]

def calcular_distancia_haversine_metros(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcula la distancia sobre la esfera terrestre en metros."""
    R = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def get_db_connection():
    """Retorna conexión a PostgreSQL/PostGIS de Flotas con timeout estricto."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=DB_NAME,
        connect_timeout=2
    )

def ejecutar_sql_solo_lectura(query: str, params: tuple = None) -> List[tuple]:
    """Capa 3 de Blindaje: Ejecuta consulta forzada a READ ONLY."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY;")
            cur.execute(query, params or ())
            return cur.fetchall()

def verificar_hidrantes_cercanos(latitud: float, longitud: float, radio_metros: int = 600) -> List[Dict[str, Any]]:
    """Busca hidrantes presurizados y operativos cercanos a las coordenadas del siniestro."""
    try:
        query = """
            SELECT id, presion_psi, caudal_litros_minuto, operativo,
                   ST_Distance(ST_SetSRID(ST_MakePoint(longitud, latitud), 4326)::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography) AS distancia_m,
                   latitud, longitud
            FROM hidrantes_red
            WHERE operativo = true
              AND ST_DWithin(ST_SetSRID(ST_MakePoint(longitud, latitud), 4326)::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s)
            ORDER BY distancia_m ASC
            LIMIT 5;
        """
        filas = ejecutar_sql_solo_lectura(query, (longitud, latitud, longitud, latitud, radio_metros))
        return [
            {
                "id": f[0],
                "presionPsi": float(f[1]),
                "caudalLitrosMinuto": int(f[2]),
                "operativo": bool(f[3]),
                "distanciaMetros": round(float(f[4]), 1),
                "latitud": float(f[5]),
                "longitud": float(f[6])
            }
            for f in filas
        ]
    except Exception as e:
        logger.info(f"Fallback en memoria para hidrantes ({e})")
        cercanos = []
        for h in HIDRANTES_MOCK_SANTA_CRUZ:
            if not h["operativo"]:
                continue
            dist_m = calcular_distancia_haversine_metros(latitud, longitud, h["latitud"], h["longitud"])
            if dist_m <= radio_metros:
                cercanos.append({
                    "id": h["id"],
                    "presionPsi": h["presionPsi"],
                    "caudalLitrosMinuto": h["caudalLitrosMinuto"],
                    "operativo": h["operativo"],
                    "distanciaMetros": round(dist_m, 1),
                    "latitud": h["latitud"],
                    "longitud": h["longitud"]
                })
        cercanos.sort(key=lambda x: x["distanciaMetros"])
        return cercanos[:5]

def consultar_unidades_cercanas(
    latitud: float,
    longitud: float,
    radio_km: float = 15.0,
    tipo_fuego: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Consulta unidades bomberiles disponibles ordenadas por proximidad geoespacial."""
    try:
        radio_metros = radio_km * 1000.0
        query = """
            SELECT id, placa, tipo, estado, litros_agua_actual, capacidad_maxima_agua, 
                   combustible_porcentaje, estacion_origen,
                   ST_Distance(ST_SetSRID(ST_MakePoint(longitud, latitud), 4326)::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography) AS distancia_m,
                   latitud, longitud
            FROM unidades_flota
            WHERE estado = 'DISPONIBLE'
              AND ST_DWithin(ST_SetSRID(ST_MakePoint(longitud, latitud), 4326)::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s)
            ORDER BY distancia_m ASC;
        """
        filas = ejecutar_sql_solo_lectura(query, (longitud, latitud, longitud, latitud, radio_metros))
        unidades = []
        for f in filas:
            unidades.append({
                "camionId": f[0],
                "placa": f[1],
                "tipo": f[2],
                "estado": f[3],
                "litrosAguaActual": int(f[4]),
                "capacidadMaximaAgua": int(f[5]),
                "combustiblePorcentaje": int(f[6]),
                "estacionOrigen": f[7],
                "distanciaMetros": round(float(f[8]), 1),
                "latitud": float(f[9]),
                "longitud": float(f[10])
            })
        return unidades
    except Exception as e:
        logger.info(f"Fallback en memoria para unidades ({e})")
        radio_metros = radio_km * 1000.0
        unidades = []
        for u in UNIDADES_MOCK_SANTA_CRUZ:
            if u["estado"] != "DISPONIBLE":
                continue
            dist_m = calcular_distancia_haversine_metros(latitud, longitud, u["latitud"], u["longitud"])
            if dist_m <= radio_metros:
                u_copia = dict(u)
                u_copia["distanciaMetros"] = round(dist_m, 1)
                unidades.append(u_copia)
        unidades.sort(key=lambda x: x["distanciaMetros"])
        return unidades

def calcular_tiempo_llegada(camion_id: str, lat_destino: float, lon_destino: float) -> Dict[str, Any]:
    """Calcula distancia de desplazamiento y ETA para un camión hacia el siniestro."""
    # Buscar unidad en DB o fallback
    unidad = None
    try:
        query = "SELECT id, placa, tipo, estacion_origen, latitud, longitud FROM unidades_flota WHERE id = %s;"
        filas = ejecutar_sql_solo_lectura(query, (camion_id,))
        if filas:
            f = filas[0]
            unidad = {
                "camionId": f[0], "placa": f[1], "tipo": f[2],
                "estacionOrigen": f[3], "latitud": float(f[4]), "longitud": float(f[5])
            }
    except Exception:
        pass

    if not unidad:
        for u in UNIDADES_MOCK_SANTA_CRUZ:
            if u["camionId"] == camion_id:
                unidad = u
                break

    if not unidad:
        return {"error": f"Camión {camion_id} no encontrado"}

    distancia_plana = calcular_distancia_haversine_metros(unidad["latitud"], unidad["longitud"], lat_destino, lon_destino)
    # Factor de sinuosidad vial urbana SCZ (1.35x)
    distancia_vial = round(distancia_plana * 1.35, 1)
    velocidad_media_kmh = 45.0
    velocidad_ms = (velocidad_media_kmh * 1000.0) / 3600.0
    duracion_segundos = max(int(distancia_vial / velocidad_ms), 60)
    duracion_minutos = round(duracion_segundos / 60.0, 1)

    # Intentar enriquecer con MS-02 si está activo
    try:
        url = f"{MS2_FLOTAS_URL}/api/v1/flotas/ruta-optima?origenLat={unidad['latitud']}&origenLon={unidad['longitud']}&destinoLat={lat_destino}&destinoLon={lon_destino}"
        with httpx.Client(timeout=1.0) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                distancia_vial = float(data.get("distanciaTotalMetros", distancia_vial))
                duracion_segundos = int(data.get("duracionEstimadaSegundos", duracion_segundos))
                duracion_minutos = round(duracion_segundos / 60.0, 1)
    except Exception:
        pass

    return {
        "camionId": unidad["camionId"],
        "placa": unidad["placa"],
        "tipo": unidad["tipo"],
        "estacionOrigen": unidad["estacionOrigen"],
        "origen": {"latitud": unidad["latitud"], "longitud": unidad["longitud"]},
        "destino": {"latitud": lat_destino, "longitud": lon_destino},
        "distanciaMetros": distancia_vial,
        "velocidadMediaKmH": velocidad_media_kmh,
        "tiempoEstimadoLlegadaMinutos": duracion_minutos,
        "tiempoEstimadoSegundos": duracion_segundos
    }

def proponer_orden_despacho(
    incidente_id: str,
    tipo_fuego: str,
    latitud: float,
    longitud: float,
    litros_minimos: int = 3000
) -> Dict[str, Any]:
    """Herramienta de Despacho Táctico: Selecciona el camión óptimo y sus hidrantes de recarga."""
    unidades = consultar_unidades_cercanas(latitud, longitud, radio_km=25.0, tipo_fuego=tipo_fuego)
    if not unidades:
        return {
            "incidenteId": incidente_id,
            "propuestaExitosa": False,
            "mensaje": "Alerta crítica: No se encontraron camiones disponibles en radio de 25 km."
        }

    candidatos = [u for u in unidades if u["litrosAguaActual"] >= litros_minimos]
    unidad_seleccionada = candidatos[0] if candidatos else unidades[0]

    eta_info = calcular_tiempo_llegada(unidad_seleccionada["camionId"], latitud, longitud)
    hidrantes = verificar_hidrantes_cercanos(latitud, longitud, radio_metros=600)

    return {
        "incidenteId": incidente_id,
        "propuestaExitosa": True,
        "recomendacionTactica": {
            "unidadPropuesta": unidad_seleccionada,
            "estimacionTiempo": eta_info,
            "redHidrantesCercanos": hidrantes,
            "justificacion": (
                f"Unidad {unidad_seleccionada['camionId']} ({unidad_seleccionada['tipo']}) asignada por menor tiempo "
                f"({eta_info['tiempoEstimadoLlegadaMinutos']} min) y {unidad_seleccionada['litrosAguaActual']}L de agua."
            )
        },
        "accionPendiente": "Aprobación requerida por el Comandante en panel Human-in-the-Loop."
    }

# Definición de servidor de herramientas MCP
mcp_flotas = {
    "servidor": "Bomberos-Flotas-MCP",
    "herramientas": [
        "consultar_unidades_cercanas",
        "verificar_hidrantes_cercanos",
        "calcular_tiempo_llegada",
        "proponer_orden_despacho"
    ]
}
