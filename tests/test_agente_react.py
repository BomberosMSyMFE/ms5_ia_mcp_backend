import pytest
from services.tactical_agents.despachador_react import agente_despachador

def test_agente_despachador_react_ciclo():
    # Siniestro en el Parque Industrial de Santa Cruz
    resultado = agente_despachador.ejecutar_ciclo_react(
        incidente_id="INC-TEST-SCZ-01",
        tipo_incidente="INDUSTRIAL",
        latitud=-17.7550,
        longitud=-63.1601,
        litros_minimos=4000,
        descripcion_siniestro="Incendio estructural en galpón de plásticos"
    )

    assert resultado["incidenteId"] == "INC-TEST-SCZ-01"
    assert resultado["gobernanza"]["patron"] == "Human-in-the-Loop"
    assert "trazasReAct" in resultado
    assert len(resultado["trazasReAct"]) >= 5
    
    # Comprobar ciclo Thought -> Action -> Observation
    tipos_pasos = [t["tipo"] for t in resultado["trazasReAct"]]
    assert "THOUGHT" in tipos_pasos
    assert "ACTION" in tipos_pasos
    assert "OBSERVATION" in tipos_pasos

    # Comprobar recomendación
    rec = resultado["propuestaGenerada"]["unidadRecomendada"]
    assert "camionId" in rec
    assert rec["litrosAguaActual"] >= 4000
