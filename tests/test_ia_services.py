import pytest
import io
from PIL import Image
from services.nlp_triage.nlp_triage import clasificar_urgencia_texto
from services.computer_vision.vision_service import inferir_evidencia_imagen

def test_nlp_clasificacion_incendio_estructural():
    res = clasificar_urgencia_texto("Hay fuego en fabrica de plasticos sale mucho humo negro y llamas")
    assert res["categoria_predicha"] == "CRITICO_ESTRUCTURAL"
    assert res["severidad"] == "CRITICA"
    assert res["confianza"] > 0.40
    assert len(res["palabras_clave"]) > 0

def test_nlp_clasificacion_incendio_forestal():
    res = clasificar_urgencia_texto("Quema descontrolada de pastizales en cordon ecologico")
    assert res["categoria_predicha"] == "ALTO_FORESTAL"
    assert res["severidad"] == "ALTA"
    assert res["confianza"] > 0.50

def test_nlp_clasificacion_fuga_gas():
    res = clasificar_urgencia_texto("Fuga de gas licuado en garrafa de cocina")
    assert res["categoria_predicha"] == "CRITICO_GAS"
    assert res["severidad"] == "CRITICA"

def test_nlp_clasificacion_accidente_vehicular():
    res = clasificar_urgencia_texto("Accidente vehicular camion choco contra poste")
    assert res["categoria_predicha"] == "ALTO_VEHICULAR"
    assert res["severidad"] == "ALTA"

def test_vision_inferencia_imagen_sintetica_fuego():
    # Crear imagen sintética en memoria con píxeles rojos (simulando fuego)
    img = Image.new("RGB", (100, 100), color=(255, 60, 20))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    img_bytes = buffer.getvalue()

    res = inferir_evidencia_imagen(img_bytes)
    assert "verificado_por_ia" in res
    assert "nivel_confianza" in res
    assert res["verificado_por_ia"] is True
    assert res["nivel_confianza"] >= 0.50

def test_vision_inferencia_imagen_sintetica_sin_fuego():
    # Crear imagen sintética azul (cielo/agua)
    img = Image.new("RGB", (100, 100), color=(20, 50, 220))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    img_bytes = buffer.getvalue()

    res = inferir_evidencia_imagen(img_bytes)
    assert res["verificado_por_ia"] is False
    assert res["nivel_confianza"] <= 0.30
