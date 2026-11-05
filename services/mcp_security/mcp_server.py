"""
services/mcp_security/mcp_server.py
Servidor MCP (Model Context Protocol) para el Cuerpo de Bomberos.
Expone herramientas tipadas en Pydantic y ejecución de consultas analíticas protegidas por AST.
Semestre 2/2026 - INF512 (Ingeniería de Software II)
Responsable: Nataly Martínez (ms5_ia_mcp_backend)
"""

import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from .ast_validator import validar_consulta_ast, ASTValidator

# Base de datos simulada en memoria para consultas analíticas seguras (Mock Realista)
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
    nombre_estacion: str = Field(..., description="Nombre de la estación (ej. 'Central', 'Norte')")
    categoria: str = Field(..., description="Categoría del insumo: EPP, QUIMICO, MATERIAL")


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
    # Simula cálculo de distancia euclidiana simplificada para el mock local
    resultados = []
    for h in BASE_DATOS_SOLO_LECTURA_MOCK["hidrantes"]:
        # Distancia aproximada en metros (1 grado ~ 111,000 m)
        dx = (h["longitud"] - longitud) * 111000 * 0.95
        dy = (h["latitud"] - latitud) * 111000
        distancia = round((dx**2 + dy**2)**0.5, 1)

        if distancia <= radio_metros:
            resultados.append({
                "id": h["id"],
                "caudal_litros_min": h["caudal_litros_min"],
                "estado": h["estado"],
                "distancia_metros": distancia,
                "zona": h["zona"]
            })
    return sorted(resultados, key=lambda x: x["distancia_metros"])


def consultar_stock_estacion(nombre_estacion: str, categoria: str) -> List[Dict[str, Any]]:
    """
    Herramienta MCP: Consulta existencias de material crítico en una estación.
    """
    cat_upper = categoria.upper()
    est_lower = nombre_estacion.lower()
    return [
        i for i in BASE_DATOS_SOLO_LECTURA_MOCK["insumos"]
        if est_lower in i["estacion"].lower() and (cat_upper in i["categoria"] or cat_upper == "TODOS")
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
    la consulta en modo estricto de solo lectura.
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

    # Si pasa el AST, se simula la ejecución con transacción forzada READ ONLY
    sql_upper = consulta_sql.upper()
    tabla_detectada = validacion.tablas_detectadas[0] if validacion.tablas_detectadas else "hidrantes"

    datos_retorno = BASE_DATOS_SOLO_LECTURA_MOCK.get(tabla_detectada, [])

    return {
        "exito": True,
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
        "descripcion": "Consulta stock de insumos críticos (EPP, espumógeno, mangueras) por estación.",
        "parametros": StockInput.model_json_schema(),
    },
    {
        "nombre": "consultar_camiones_disponibles",
        "descripcion": "Consulta flota de camiones cisterna y volumen de agua disponible por cuadrante.",
        "parametros": CamionesInput.model_json_schema(),
    },
    {
        "nombre": "ejecutar_consulta_analitica_segura",
        "descripcion": "Ejecuta consultas SQL analíticas dinámicas validadas por el parser AST con sqlglot.",
        "parametros": ConsultaAnaliticaInput.model_json_schema(),
    },
]
