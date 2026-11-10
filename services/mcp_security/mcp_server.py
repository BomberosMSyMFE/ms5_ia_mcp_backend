"""
services/mcp_security/mcp_server.py
Servidor MCP (Model Context Protocol) para el Cuerpo de Bomberos.
Expone herramientas tipadas en Pydantic y ejecución de consultas analíticas protegidas por AST.
Conecta de forma segura a PostgreSQL (MS-03 Inventario) usando el usuario de menor privilegio `mcp_readonly_user`.
Semestre 2/2026 - INF512 (Ingeniería de Software II)
Autores: Nataly Martínez & Jael Mamani (ms5_ia_mcp_backend)
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None
    RealDictCursor = None

from .ast_validator import validar_consulta_ast, ASTValidator

logger = logging.getLogger("mcp_server")

# =========================================================================
# CONFIGURACIÓN DE CONEXIÓN POSTGRESQL (CAPA 3: MENOR PRIVILEGIO)
# =========================================================================
MCP_DB_HOST = os.getenv("MCP_DB_HOST", "127.0.0.1")
MCP_DB_PORT = int(os.getenv("MCP_DB_PORT", "5435"))
MCP_DB_NAME = os.getenv("MCP_DB_NAME", "inventario_db")
MCP_DB_USER = os.getenv("MCP_DB_USER", "mcp_readonly_user")
MCP_DB_PASSWORD = os.getenv("MCP_DB_PASSWORD", "mcp_read_secret_2026")


def obtener_conexion_mcp_readonly():
    """
    Establece conexión a PostgreSQL con el usuario dedicado de solo lectura.
    Fuerza la sesión en readonly para garantizar defensa en profundidad.
    """
    try:
        conn = psycopg2.connect(
            host=MCP_DB_HOST,
            port=MCP_DB_PORT,
            dbname=MCP_DB_NAME,
            user=MCP_DB_USER,
            password=MCP_DB_PASSWORD,
            connect_timeout=2
        )
        conn.set_session(readonly=True, autocommit=True)
        return conn
    except Exception as e:
        logger.warning(f"[MCP-POSTGRES] Base de datos no disponible ({MCP_DB_HOST}:{MCP_DB_PORT}): {e}. Operando en modo fallback.")
        return None


# Base de datos simulada en memoria para contingencias offline (Mock de Respaldo)
BASE_DATOS_SOLO_LECTURA_MOCK = {
    "hidrantes": [
        {"id": "HID-SCZ-101", "latitud": -17.7654, "longitud": -63.1432, "caudal_litros_min": 1800, "estado": "OPERATIVO", "zona": "NORTE"},
        {"id": "HID-SCZ-102", "latitud": -17.7680, "longitud": -63.1410, "caudal_litros_min": 2200, "estado": "OPERATIVO", "zona": "NORTE"},
        {"id": "HID-SCZ-103", "latitud": -17.7712, "longitud": -63.1815, "caudal_litros_min": 0, "estado": "FUERA_DE_SERVICIO", "zona": "CENTRO"},
        {"id": "HID-SCZ-104", "latitud": -17.7850, "longitud": -63.1790, "caudal_litros_min": 2500, "estado": "OPERATIVO", "zona": "CENTRO"},
        {"id": "HID-SCZ-105", "latitud": -17.8010, "longitud": -63.1650, "caudal_litros_min": 1900, "estado": "OPERATIVO", "zona": "SUR"},
    ],
    "camiones": [
        {"id": "CAM-B01", "tipo": "Cisterna Pesada", "capacidad_agua": 10000, "agua_actual": 8500, "estado": "DISPONIBLE", "cuadrante": "NORTE"},
        {"id": "CAM-B02", "tipo": "Ataque Rápido", "capacidad_agua": 3500, "agua_actual": 3500, "estado": "EN_ESCENA", "cuadrante": "CENTRO"},
        {"id": "CAM-B03", "tipo": "Escala Telescópica", "capacidad_agua": 2000, "agua_actual": 1800, "estado": "DISPONIBLE", "cuadrante": "NORTE"},
        {"id": "CAM-B04", "tipo": "Cisterna Táctica", "capacidad_agua": 8000, "agua_actual": 7800, "estado": "DISPONIBLE", "cuadrante": "SUR"},
    ],
    "insumos": [
        {"id": "INS-ESPUMA-AFFF", "nombre": "Espumógeno AFFF 3%", "categoria": "QUIMICO", "litros_disponibles": 1450, "estacion": "Central"},
        {"id": "INS-TRAJE-NIVEL-A", "nombre": "Traje Encapsulado HazMat Nivel A", "categoria": "EPP", "unidades_disponibles": 6, "estacion": "Central"},
        {"id": "INS-KIT-EPP-300BAR", "nombre": "Equipo de Respiración Autónoma 300 Bar", "categoria": "EPP", "unidades_disponibles": 14, "estacion": "Norte"},
        {"id": "INS-MANGUERA-2PULG", "nombre": "Manguera de Alta Presión 2.5 pulgadas", "categoria": "MATERIAL", "unidades_disponibles": 30, "estacion": "Central"},
    ],
    "stock": [
        {"estacion_id": 1, "estacion_nombre": "Central", "insumo": "Espumógeno AFFF 3%", "disponible": 1450},
        {"estacion_id": 1, "estacion_nombre": "Central", "insumo": "Traje Nivel A", "disponible": 6},
        {"estacion_id": 2, "estacion_nombre": "Estación Norte", "insumo": "Equipos ERA 300 Bar", "disponible": 14},
    ],
    "incidentes": [
        {"id": "INC-2026-SCZ-001", "tipo": "QUIMICO", "severidad": "CRITICA", "estado": "EN_COMBATE", "zona": "NORTE", "agua_despachada": 8500},
        {"id": "INC-2026-SCZ-002", "tipo": "ESTRUCTURAL", "severidad": "ALTA", "estado": "CONTROLADO", "zona": "CENTRO", "agua_despachada": 12000},
    ]
}


# =========================================================================
# CAPA 1: TOOL CALLING TIPADO (PYDANTIC SCHEMAS)
# =========================================================================

class HidrantesInput(BaseModel):
    latitud: float = Field(..., description="Latitud GPS de la emergencia")
    longitud: float = Field(..., description="Longitud GPS de la emergencia")
    radio_metros: int = Field(500, description="Radio de búsqueda en metros")


class StockInput(BaseModel):
    nombre_estacion: str = Field(..., description="Nombre de la estación (ej. 'Central', 'Norte', 'EST-01')")
    categoria: str = Field(..., description="Categoría del insumo: EPP, QUIMICO, HERRAMIENTA, MATERIAL o TODOS")


class CamionesInput(BaseModel):
    cuadrante: Optional[str] = Field("TODOS", description="Cuadrante operativo: NORTE, CENTRO, SUR, TODOS")


class ConsultaAnaliticaInput(BaseModel):
    consulta_sql: str = Field(..., description="Consulta SQL de solo lectura (debe pasar el validador AST)")


# =========================================================================
# HERRAMIENTAS MCP EJECUTABLES
# =========================================================================

def verificar_hidrantes_cercanos(latitud: float, longitud: float, radio_metros: int = 500) -> List[Dict[str, Any]]:
    """
    Herramienta MCP: Busca hidrantes presurizados cercanos a una coordenada.
    Usa parámetros tipados, imposibilitando inyecciones SQL.
    """
    resultados = []
    for h in BASE_DATOS_SOLO_LECTURA_MOCK["hidrantes"]:
        dx = (h["longitud"] - longitud) * 111000 * 0.95
        dy = (h["latitud"] - latitud) * 111000
        distancia = round((dx**2 + dy**2)**0.5, 1)

        if distancia <= radio_metros:
            operativo = (h["estado"] == "OPERATIVO")
            resultados.append({
                "id": h["id"],
                "latitud": float(h["latitud"]),
                "longitud": float(h["longitud"]),
                "caudal_litros_min": h["caudal_litros_min"],
                "caudalLitrosMinuto": h["caudal_litros_min"],
                "estado": h["estado"],
                "operativo": operativo,
                "distancia_metros": distancia,
                "distanciaMetros": distancia,
                "presionPsi": 65.0,
                "zona": h["zona"]
            })
    return sorted(resultados, key=lambda x: x["distancia_metros"])


def consultar_stock_estacion(nombre_estacion: str, categoria: str) -> List[Dict[str, Any]]:
    """
    Herramienta MCP: Consulta existencias de insumos en la base de datos PostgreSQL real de Inventario
    utilizando el usuario de solo lectura `mcp_readonly_user`.
    """
    cat_upper = categoria.upper()
    conn = obtener_conexion_mcp_readonly()

    if conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                resultados = []

                # 1. Consultar Químicos en PostgreSQL
                if cat_upper in ["QUIMICO", "TODOS"]:
                    cur.execute("""
                        SELECT sq.codigo as id, sq.nombre, 'QUIMICO' as categoria,
                               sq.litros_disponibles, COALESCE(e.nombre, sq.estacion_id) as estacion
                        FROM suministros_quimicos sq
                        LEFT JOIN estaciones_inventario e ON sq.estacion_id = e.id
                        WHERE (%s = 'TODOS' OR e.nombre ILIKE %s OR sq.estacion_id ILIKE %s);
                    """, (nombre_estacion, f"%{nombre_estacion}%", f"%{nombre_estacion}%"))
                    for r in cur.fetchall():
                        resultados.append({
                            "id": r["id"],
                            "nombre": r["nombre"],
                            "categoria": r["categoria"],
                            "litros_disponibles": float(r["litros_disponibles"]),
                            "estacion": r["estacion"]
                        })

                # 2. Consultar Kits EPP en PostgreSQL
                if cat_upper in ["EPP", "TODOS"]:
                    cur.execute("""
                        SELECT k.codigo as id, 'Equipo ERA Autónomo' as nombre, 'EPP' as categoria,
                               k.presion_oxigeno_bares, k.estado, COALESCE(e.nombre, k.estacion_id) as estacion
                        FROM kits_epp k
                        LEFT JOIN estaciones_inventario e ON k.estacion_id = e.id
                        WHERE (%s = 'TODOS' OR e.nombre ILIKE %s OR k.estacion_id ILIKE %s);
                    """, (nombre_estacion, f"%{nombre_estacion}%", f"%{nombre_estacion}%"))
                    for r in cur.fetchall():
                        resultados.append({
                            "id": r["id"],
                            "nombre": f"{r['nombre']} ({r['presion_oxigeno_bares']} Bares)",
                            "categoria": r["categoria"],
                            "presion_oxigeno_bares": r["presion_oxigeno_bares"],
                            "estado": r["estado"],
                            "estacion": r["estacion"]
                        })

                # 3. Consultar Herramientas en PostgreSQL
                if cat_upper in ["HERRAMIENTA", "MATERIAL", "TODOS"]:
                    cur.execute("""
                        SELECT h.codigo as id, h.nombre, 'HERRAMIENTA' as categoria,
                               h.horas_uso, h.estado, COALESCE(e.nombre, h.estacion_id) as estacion
                        FROM herramientas_equipos h
                        LEFT JOIN estaciones_inventario e ON h.estacion_id = e.id
                        WHERE (%s = 'TODOS' OR e.nombre ILIKE %s OR h.estacion_id ILIKE %s);
                    """, (nombre_estacion, f"%{nombre_estacion}%", f"%{nombre_estacion}%"))
                    for r in cur.fetchall():
                        resultados.append({
                            "id": r["id"],
                            "nombre": r["nombre"],
                            "categoria": r["categoria"],
                            "horas_uso": float(r["horas_uso"]),
                            "estado": r["estado"],
                            "estacion": r["estacion"]
                        })

                if resultados:
                    return resultados
        except Exception as e:
            logger.error(f"[MCP-STOCK] Error al consultar PostgreSQL: {e}")
        finally:
            conn.close()

    # Fallback de respaldo en memoria si la BD PostgreSQL estuviera desconectada
    est_lower = nombre_estacion.lower()
    return [
        i for i in BASE_DATOS_SOLO_LECTURA_MOCK["insumos"]
        if (est_lower == "todos" or est_lower in i["estacion"].lower()) and (cat_upper in i["categoria"] or cat_upper == "TODOS")
    ]


def consultar_camiones_disponibles(cuadrante: str = "TODOS") -> List[Dict[str, Any]]:
    """
    Herramienta MCP: Retorna la flota de camiones cisterna y ataque con sus niveles de agua.
    Si USE_MOCKS=false: Consulta en vivo el contrato MS-02 (/api/v1/flotas/unidades/activas).
    Si USE_MOCKS=true o fallo de red: Retorna datos deterministas del mock local.
    """
    use_mocks = os.getenv("USE_MOCKS", "true").lower() in ("true", "1", "yes")
    if not use_mocks:
        ms02_url = os.getenv("MS02_FLOTAS_URL", "http://localhost:8080")
        urls_a_probar = [ms02_url]
        if ":8080" in ms02_url:
            urls_a_probar.append(ms02_url.replace(":8080", ":8082"))
        elif ":8082" in ms02_url:
            urls_a_probar.append(ms02_url.replace(":8082", ":8080"))

        for url_candidata in urls_a_probar:
            try:
                import httpx
                with httpx.Client(timeout=1.5) as client:
                    resp = client.get(f"{url_candidata}/api/v1/flotas/unidades/activas")
                    if resp.status_code == 200:
                        camiones_vivos = []
                        for c in resp.json():
                            lat = float(c.get("latitud", -17.78))
                            cuad = "NORTE" if lat > -17.77 else ("SUR" if lat < -17.80 else "CENTRO")
                            camiones_vivos.append({
                                "id": str(c.get("id", "CAM-01")),
                                "placa": str(c.get("placa", "0000-SCZ")),
                                "tipo": str(c.get("tipo", "Cisterna")).replace("_", " ").title(),
                                "capacidad_agua": int(c.get("capacidadMaximaAgua", 10000)),
                                "agua_actual": int(c.get("litrosAguaActual", 8000)),
                                "estado": str(c.get("estadoOperativo", c.get("estado", "DISPONIBLE"))),
                                "cuadrante": str(c.get("cuadrante", cuad)),
                                "combustible_porcentaje": int(c.get("combustiblePorcentaje", 100))
                            })
                        if camiones_vivos:
                            cuad_upper = cuadrante.upper()
                            if cuad_upper == "TODOS":
                                return camiones_vivos
                            return [c for c in camiones_vivos if c["cuadrante"] == cuad_upper]
            except Exception:
                continue

    cuad_upper = cuadrante.upper()
    if cuad_upper == "TODOS":
        return BASE_DATOS_SOLO_LECTURA_MOCK["camiones"]
    return [c for c in BASE_DATOS_SOLO_LECTURA_MOCK["camiones"] if c["cuadrante"] == cuad_upper]


def ejecutar_consulta_analitica_segura(consulta_sql: str) -> Dict[str, Any]:
    """
    Herramienta MCP: Valida sintácticamente mediante AST (sqlglot) y ejecuta
    la consulta en PostgreSQL real en modo estricto de solo lectura.
    """
    validacion = validar_consulta_ast(consulta_sql)

    if not validacion.valido:
        return {
            "exito": False,
            "error_seguridad": validacion.motivo_rechazo,
            "tipo_sentencia": validacion.tipo_sentencia,
            "sql_rechazado": consulta_sql,
            "transaccion": "ABORTADA_DEFENSIVAMENTE"
        }

    # Intentar ejecutar en PostgreSQL real con mcp_readonly_user
    conn = obtener_conexion_mcp_readonly()
    if conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Transacción forzada de solo lectura a nivel de sesión
                cur.execute(ASTValidator.forzar_transaccion_solo_lectura())
                cur.execute(validacion.sql_sanitizado)
                filas = cur.fetchall()
                datos = [dict(f) for f in filas]

                return {
                    "exito": True,
                    "origen": "POSTGRESQL_REAL (puerto 5435)",
                    "usuario_bd": "mcp_readonly_user",
                    "transaccion": "SET TRANSACTION READ ONLY;",
                    "tablas_consultadas": validacion.tablas_detectadas,
                    "filas_retornadas": len(datos),
                    "datos": datos,
                    "sql_ejecutado": validacion.sql_sanitizado
                }
        except Exception as e:
            logger.warning(f"[MCP-AST] Error ejecutando SQL en PostgreSQL real: {e}")
        finally:
            conn.close()

    # Fallback con base simulada si la BD estuviera desconectada
    tabla_detectada = validacion.tablas_detectadas[0] if validacion.tablas_detectadas else "hidrantes"
    datos_retorno = BASE_DATOS_SOLO_LECTURA_MOCK.get(tabla_detectada, [])

    return {
        "exito": True,
        "origen": "BASE_SIMULADA_FALLBACK",
        "usuario_bd": "mcp_readonly_user",
        "transaccion": ASTValidator.forzar_transaccion_solo_lectura(),
        "tablas_consultadas": validacion.tablas_detectadas,
        "filas_retornadas": len(datos_retorno),
        "datos": datos_retorno,
        "sql_ejecutado": validacion.sql_sanitizado
    }


CATALOGO_HERRAMIENTAS_MCP = [
    {
        "nombre": "verificar_hidrantes_cercanos",
        "descripcion": "Busca hidrantes presurizados cercanos a una coordenada geográfica (lat/lng).",
        "parametros": HidrantesInput.model_json_schema(),
    },
    {
        "nombre": "consultar_stock_estacion",
        "descripcion": "Consulta stock de insumos críticos (EPP, espumógeno, mangueras) por estación en PostgreSQL real.",
        "parametros": StockInput.model_json_schema(),
    },
    {
        "nombre": "consultar_camiones_disponibles",
        "descripcion": "Consulta flota de camiones cisterna y volumen de agua disponible por cuadrante.",
        "parametros": CamionesInput.model_json_schema(),
    },
    {
        "nombre": "ejecutar_consulta_analitica_segura",
        "descripcion": "Ejecuta consultas SQL analíticas dinámicas validadas por el parser AST con sqlglot contra PostgreSQL real.",
        "parametros": ConsultaAnaliticaInput.model_json_schema(),
    },
]
