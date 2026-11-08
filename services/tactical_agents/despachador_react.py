from typing import Dict, Any, List
import time
from services.flotas_mcp.bomberos_flotas_mcp import (
    consultar_unidades_cercanas,
    verificar_hidrantes_cercanos,
    calcular_tiempo_llegada
)

class AgenteDespachadorTacticoReAct:
    """
    Agente Inteligente Autónomo bajo el Framework ReAct (Reasoning + Acting).
    Implementa el ciclo iterativo: Thought (Pensamiento) -> Action (Acción) -> Observation (Observación).
    Genera propuestas de despacho con gobernanza táctica Human-in-the-Loop.
    """

    def __init__(self, agente_id: str = "AGENTE-TACTICO-01"):
        self.agente_id = agente_id

    def ejecutar_ciclo_react(
        self,
        incidente_id: str,
        tipo_incidente: str,
        latitud: float,
        longitud: float,
        litros_minimos: int = 4000,
        descripcion_siniestro: str = ""
    ) -> Dict[str, Any]:
        """
        Ejecuta el loop cognitivo ReAct paso a paso, registrando el razonamiento y acciones tomadas.
        """
        inicio_timestamp = time.time()
        trazas_react: List[Dict[str, Any]] = []

        # =====================================================================
        # PASO 1: RAZONAMIENTO INICIAL (THOUGHT 1)
        # =====================================================================
        pensamiento_1 = (
            f"El siniestro '{incidente_id}' reportado como '{tipo_incidente}' en ({latitud}, {longitud}) "
            f"requiere un mínimo de {litros_minimos} litros de agua. "
            f"Debo buscar en la base de datos de flotas unidades disponibles dentro de un radio táctico de 15 km."
        )
        trazas_react.append({
            "paso": 1,
            "tipo": "THOUGHT",
            "contenido": pensamiento_1
        })

        # =====================================================================
        # PASO 2: ACCIÓN 1 - CONSULTA DE UNIDADES (ACTION 1)
        # =====================================================================
        trazas_react.append({
            "paso": 2,
            "tipo": "ACTION",
            "herramienta": "consultar_unidades_cercanas",
            "parametros": {"latitud": latitud, "longitud": longitud, "radio_km": 15.0, "tipo_fuego": tipo_incidente}
        })

        unidades_disponibles = consultar_unidades_cercanas(
            latitud=latitud,
            longitud=longitud,
            radio_km=15.0,
            tipo_fuego=tipo_incidente
        )

        trazas_react.append({
            "paso": 3,
            "tipo": "OBSERVATION",
            "resultado": f"Se localizaron {len(unidades_disponibles)} unidades disponibles compatibles en el radio de búsqueda.",
            "datos": [u["camionId"] + " (" + u["tipo"] + " - " + str(u["litrosAguaActual"]) + "L)" for u in unidades_disponibles]
        })

        if not unidades_disponibles:
            return {
                "agenteId": self.agente_id,
                "incidenteId": incidente_id,
                "exito": False,
                "mensaje": "No se encontraron unidades operativas en el radio de intervención.",
                "trazasReAct": trazas_react
            }

        # Filtrar candidatos que cumplan con la capacidad hídrica
        candidatos = [u for u in unidades_disponibles if u["litrosAguaActual"] >= litros_minimos]
        unidad_elegida = candidatos[0] if candidatos else unidades_disponibles[0]

        # =====================================================================
        # PASO 3: RAZONAMIENTO INTERMEDIO (THOUGHT 2)
        # =====================================================================
        pensamiento_2 = (
            f"La unidad {unidad_elegida['camionId']} de {unidad_elegida['estacionOrigen']} es la más cercana "
            f"({unidad_elegida['distanciaMetros']} metros) con reserva hídrica de {unidad_elegida['litrosAguaActual']}L. "
            f"Debo calcular el tiempo exacto de arribo (ETA) y verificar hidrantes cercanos para garantizar recarga continua."
        )
        trazas_react.append({
            "paso": 4,
            "tipo": "THOUGHT",
            "contenido": pensamiento_2
        })

        # =====================================================================
        # PASO 4: ACCIONES EN PARALELO - ETA E HIDRANTES (ACTION 2 & 3)
        # =====================================================================
        trazas_react.append({
            "paso": 5,
            "tipo": "ACTION",
            "herramienta": "calcular_tiempo_llegada",
            "parametros": {"camion_id": unidad_elegida["camionId"], "lat_destino": latitud, "lon_destino": longitud}
        })
        eta_data = calcular_tiempo_llegada(unidad_elegida["camionId"], latitud, longitud)

        trazas_react.append({
            "paso": 6,
            "tipo": "ACTION",
            "herramienta": "verificar_hidrantes_cercanos",
            "parametros": {"latitud": latitud, "longitud": longitud, "radio_metros": 600}
        })
        hidrantes_data = verificar_hidrantes_cercanos(latitud, longitud, radio_metros=600)

        trazas_react.append({
            "paso": 7,
            "tipo": "OBSERVATION",
            "resultado": (
                f"ETA estimado: {eta_data.get('tiempoEstimadoLlegadaMinutos')} minutos. "
                f"Se detectaron {len(hidrantes_data)} hidrantes presurizados en un radio de 600 metros del siniestro."
            )
        })

        # =====================================================================
        # PASO 5: CONCLUSIÓN Y PROPUESTA FINAL (FINAL ANSWER)
        # =====================================================================
        tiempo_total_ms = round((time.time() - inicio_timestamp) * 1000, 2)
        
        recomendacion = {
            "unidadRecomendada": {
                "camionId": unidad_elegida["camionId"],
                "placa": unidad_elegida["placa"],
                "tipo": unidad_elegida["tipo"],
                "estacionOrigen": unidad_elegida["estacionOrigen"],
                "distanciaMetros": unidad_elegida["distanciaMetros"],
                "litrosAguaActual": unidad_elegida["litrosAguaActual"],
                "tiempoEstimadoMinutos": eta_data.get("tiempoEstimadoLlegadaMinutos")
            },
            "estrategiaHidrica": {
                "abastecimientoAutonomo": f"{unidad_elegida['litrosAguaActual']} Litros",
                "hidrantesSoporte": [
                    {
                        "id": h["id"],
                        "distanciaMetros": h["distanciaMetros"],
                        "presionPsi": h["presionPsi"],
                        "caudalLitrosMinuto": h["caudalLitrosMinuto"]
                    }
                    for h in hidrantes_data
                ]
            },
            "justificacionTactica": (
                f"Se propone despachar la unidad {unidad_elegida['camionId']} ({unidad_elegida['tipo']}) de "
                f"{unidad_elegida['estacionOrigen']}. Arribo estimado en {eta_data.get('tiempoEstimadoLlegadaMinutos')} minutos. "
                f"Cuenta con cobertura de recarga mediante {len(hidrantes_data)} hidrantes operativos cercanos."
            )
        }

        return {
            "agenteId": self.agente_id,
            "incidenteId": incidente_id,
            "tipoIncidente": tipo_incidente,
            "tiempoRazonamientoMs": tiempo_total_ms,
            "propuestaGenerada": recomendacion,
            "gobernanza": {
                "patron": "Human-in-the-Loop",
                "estadoAprobacion": "PENDIENTE_APROBACION_COMANDANTE",
                "nota": "La IA ha formulado la sugerencia óptima; el operador humano en MS-01 debe presionar [Aprobar Despacho] para gatillar la SAGA."
            },
            "trazasReAct": trazas_react
        }

agente_despachador = AgenteDespachadorTacticoReAct()
