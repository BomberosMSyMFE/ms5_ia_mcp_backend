"""
Servicio de Visión por Computadora con YOLOv8.
Detección de patrones visuales de fuego, humo y vehículos en imágenes de siniestros.
"""

import io
from typing import Dict, Any, List
from PIL import Image

_modelo_yolo = None

def get_yolo_model():
    global _modelo_yolo
    if _modelo_yolo is None:
        try:
            from ultralytics import YOLO
            # Carga el modelo YOLOv8 nano oficial (pesos ligeros de 6MB)
            _modelo_yolo = YOLO("yolov8n.pt")
        except Exception as e:
            print(f"[WARN] No se pudo cargar ultralytics YOLO: {e}")
            _modelo_yolo = False
    return _modelo_yolo

def inferir_evidencia_imagen(imagen_bytes: bytes) -> Dict[str, Any]:
    """
    Ejecuta inferencia con Deep Learning sobre los bytes de una imagen.
    Retorna métricas de verificación, confianza y cajas delimitadoras (Bounding Boxes).
    """
    try:
        imagen = Image.open(io.BytesIO(imagen_bytes)).convert("RGB")
    except Exception as e:
        return {
            "verificado_por_ia": False,
            "nivel_confianza": 0.0,
            "error": f"Formato de imagen inválido: {str(e)}",
            "detecciones": []
        }

    modelo = get_yolo_model()

    if modelo and modelo is not False:
        # Inferencia con red convolucional
        resultados = modelo.predict(source=imagen, conf=0.25, imgsz=640)
        detecciones = []
        score_maximo = 0.0
        es_peligro_confirmado = False

        clases_peligro = ["fire", "smoke", "car", "truck", "bus", "motorcycle", "train"]

        for r in resultados:
            for box in r.boxes:
                clase_id = int(box.cls[0])
                nombre_clase = modelo.names[clase_id]
                confianza = float(box.conf[0])
                score_maximo = max(score_maximo, confianza)

                # Coordenadas de la caja delimitadora [x1, y1, x2, y2]
                coords = [round(float(c), 1) for c in box.xyxy[0].tolist()]

                detecciones.append({
                    "clase": nombre_clase,
                    "confianza": round(confianza, 3),
                    "bounding_box": coords
                })

                if nombre_clase in clases_peligro:
                    es_peligro_confirmado = True

        # Análisis cromático complementario para llamas, calor y humo
        ancho, alto = imagen.size
        pixeles = imagen.load()
        fuego_pixels = 0
        humo_pixels = 0
        total_muestreado = 0

        paso_x = max(1, ancho // 30)
        paso_y = max(1, alto // 30)

        for x in range(0, ancho, paso_x):
            for y in range(0, alto, paso_y):
                r, g, b = pixeles[x, y]
                total_muestreado += 1

                # 1. Detección de llama (amarillo brillante, naranja, rojo vivo o blanco incandescente)
                es_llama_naranja = (r > 150 and g > 35 and b < 120 and r > g)
                es_llama_amarilla = (r > 190 and g > 130 and b < 160 and r > (b + 20))
                es_nucleo_calor = (r > 215 and g > 190 and b < 180)

                if es_llama_naranja or es_llama_amarilla or es_nucleo_calor:
                    fuego_pixels += 1
                elif abs(r - g) < 22 and abs(g - b) < 22 and (r < 85 or r > 160):
                    # 2. Detección de humo (nubes densas oscuras o humo blanco/gris de combustión)
                    humo_pixels += 1

        ratio_fuego = fuego_pixels / max(1, total_muestreado)
        ratio_humo = humo_pixels / max(1, total_muestreado)

        if ratio_fuego >= 0.01 or (ratio_fuego >= 0.005 and ratio_humo >= 0.05):
            es_peligro_confirmado = True
            conf_fuego = min(0.96, round(0.70 + (ratio_fuego * 3.0) + (ratio_humo * 0.2), 2))
            score_maximo = max(score_maximo, conf_fuego)
            detecciones.append({
                "clase": "fuego_patron_termico",
                "confianza": conf_fuego,
                "bounding_box": [0, 0, ancho, alto]
            })
        elif ratio_humo >= 0.12:
            es_peligro_confirmado = True
            conf_humo = min(0.90, round(0.60 + ratio_humo * 0.5, 2))
            score_maximo = max(score_maximo, conf_humo)
            detecciones.append({
                "clase": "humo_denso",
                "confianza": conf_humo,
                "bounding_box": [0, 0, ancho, alto]
            })

        return {
            "verificado_por_ia": es_peligro_confirmado,
            "nivel_confianza": round(score_maximo, 3),
            "total_objetos_detectados": len(detecciones),
            "detecciones": detecciones,
            "motor": "YOLOv8 Nano (Deep Learning PyTorch) + Analizador Térmico"
        }

    # Heurística de respaldo basada en píxeles si ultralytics aún no cargó
    ancho, alto = imagen.size
    pixeles = imagen.load()
    fuego_pixels = 0
    total_muestreado = 0

    paso_x = max(1, ancho // 20)
    paso_y = max(1, alto // 20)

    for x in range(0, ancho, paso_x):
        for y in range(0, alto, paso_y):
            r, g, b = pixeles[x, y]
            total_muestreado += 1
            es_llama = (r > 150 and g > 35 and b < 130 and r > g) or (r > 200 and g > 150 and b < 160)
            if es_llama:
                fuego_pixels += 1

    ratio = fuego_pixels / max(1, total_muestreado)
    es_fuego = ratio >= 0.01
    conf = min(0.96, round(0.70 + ratio * 2.5, 2)) if es_fuego else 0.10

    return {
        "verificado_por_ia": es_fuego,
        "nivel_confianza": conf if es_fuego else 0.10,
        "total_objetos_detectados": 1 if es_fuego else 0,
        "detecciones": [{"clase": "patron_fuego", "confianza": conf}] if es_fuego else [],
        "motor": "Vision Heuristic Fallback (Deep Learning Standby)"
    }
