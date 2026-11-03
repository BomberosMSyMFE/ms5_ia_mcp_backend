# MS-05: Inferencia Cognitiva, Machine Learning y Visión Artificial (IA Core)
**Plataforma Distribuida Cuerpo de Bomberos — INF512 (Ingeniería de Software II)**  
**Semestre:** 2/2026 — UAGRM  
**Responsable:** Jael Sandoval  
**Stack Tecnológico:** Python 3.11+ | FastAPI 0.111+ | PyTorch 2.2+ | Ultralytics YOLOv8 Nano | Scikit-Learn 1.4+ | Pillow 10.3+ | Uvicorn 0.30+ | Pytest 8.2+  
**Patrón Arquitectónico:** Service-Oriented In-Memory Layered Architecture (Inferencia Offline / Edge AI)  
**Mecanismo de Exposición:** REST API de Inferencia Cognitiva Asíncrona (HTTP Multipart / JSON) en puerto 8005  

---

## 1. Encabezado Técnico

* **Microservicio:** `MS-05: Inferencia Cognitiva, Machine Learning y Visión Artificial (IA Core)`
* **Ecosistema:** Plataforma Distribuida Integral de Gestión de Emergencias y Bomberos
* **Semestre Académico:** Semestre 2/2026 — UAGRM
* **Versiones Detectadas en Código:**
  * Python: `3.11+`
  * FastAPI: `^0.111.0`
  * PyTorch (Torch): `^2.2.0`
  * Ultralytics YOLOv8: `^8.2.0` (Modelo: `yolov8n.pt`)
  * Scikit-Learn: `^1.4.0` (TF-IDF Vectorizer + Random Forest Classifier)
  * Pillow (PIL): `^10.3.0`
  * Uvicorn: `^0.30.0`
  * Pytest / Pytest-Asyncio: `^8.2.0` / `^0.23.0`
* **Patrón de Arquitectura:** Layered Architecture especializada en Servicios de Inferencia Offline y Modelos Pre-entrenados en memoria (cumpliendo directivas de los Puntos 05 y 06 del sistema distribuido).
* **Mecanismo de Comunicación:** REST API HTTP asíncrona sobre el puerto 8005. Provee endpoints para procesamiento de binarios multimedia (Multipart) y payloads JSON para clasificación semántica de texto en lenguaje natural.

---

## 2. Arquitectura de Código

Estructura por capas de inferencia implementada en el repositorio:

```text
+---------------------------------------------------------------------------------------+
|                                    API ENTRYPOINT                                     |
|  - FastAPI Gateway (api/main_ia.py:app_ia)                                            |
|    * Filtro de seguridad MIME (JPEG, PNG, WebP, MP4, WebM)                            |
|    * Límite estricto de carga (20 MB máximo por archivo)                              |
|    * Health Check & CORS Middleware                                                   |
|  +---------------------------------------------------------------------------------+  |
|  |                         COGNITIVE SERVICES LAYER                                |  |
|  |  +---------------------------------------------------------------------------+  |  |
|  |  |                 COMPUTER VISION & DEEP LEARNING                           |  |  |
|  |  |  - services/computer_vision/vision_service.py                             |  |  |
|  |  |    * Inferencia Convolucional YOLOv8 Nano (YOLO('yolov8n.pt'))            |  |  |
|  |  |    * Detección de objetos de riesgo: fire, smoke, car, truck, bus         |  |  |
|  |  |    * Bounding Boxes [x1, y1, x2, y2] con score de confianza              |  |  |
|  |  |    * Analizador Cromático y Térmico complementario por muestreo de pixel  |  |  |
|  |  +---------------------------------------------------------------------------+  |  |
|  |  |               NATURAL LANGUAGE PROCESSING (NLP TRIAJE)                    |  |  |
|  |  |  - services/nlp_triage/nlp_triage.py                                      |  |  |
|  |  |    * NLPEmergencyClassifier (Singleton en memoria RAM)                    |  |  |
|  |  |    * Vectorizador TF-IDF con N-Gramas (1, 2) y normalización minúscula    |  |  |
|  |  |    * Random Forest Classifier (30 estimadores, balance de clases)         |  |  |
|  |  |    * Mapeo taxonómico: CRITICO_ESTRUCTURAL, ALTO_FORESTAL, CRITICO_GAS... |  |  |
|  |  +---------------------------------------------------------------------------+  |  |
|  +---------------------------------------------------------------------------------+  |
|  [Automated Verification Layer]                                                       |
|   - tests/test_ia_services.py: Tests determinísticos de clasificación y visión        |
|   - pytest.ini: Resolución automática de dependencias locales en PYTHONPATH           |
+---------------------------------------------------------------------------------------+
```

---

## 3. Modelo de Persistencia

El microservicio MS-05 es **stateless** y no requiere base de datos persistente relacional ni NoSQL. Opera bajo el principio de **In-Memory Machine Learning Inference**:

| Componente en Memoria | Estructura | Tamaño / Huella | Propósito en el Negocio |
| :--- | :--- | :--- | :--- |
| **Modelo YOLOv8 Nano** | Red neuronal convolucional (`yolov8n.pt`) | ~6.5 MB en disco / ~120 MB en RAM | Inferencia visual ultrarrápida (<150 ms) para detección de fuego activo, humo denso y vehículos colisionados. |
| **TF-IDF Vectorizer** | Matriz de vocabulario n-gramas sparse | <1 MB en RAM | Extracción de características léxicas y ponderación de términos de emergencia ciudadana. |
| **Random Forest Classifier** | Ensamble de 30 árboles de decisión (`sklearn`) | <5 MB en RAM | Clasificación instantánea (<10 ms) del tipo de incidente y cálculo de severidad para triaje. |

---

## 4. Integración Distribuida y Flujos de Negocio

### Diagrama de Inferencia Distribuida (ASCII)

```text
 MS-04 Portal Ciudadano        MS-05 IA Core (Puerto 8005)
(FastAPI Hexagonal)            (YOLOv8 + Scikit-Learn NLP)
        |                                   |
        |--- 1. POST /nlp/clasificar ------>|
        |    {"texto": "Fuego en nave..."}  |-- TF-IDF Feature Extraction
        |                                   |-- Random Forest Inference
        |<-- 2. Retorna Categoría & Score --|   (CRITICO_ESTRUCTURAL, Severidad: CRITICA)
        |                                   |
        |--- 3. POST /vision/validar ------>|
        |    (Multipart / Stream imagen)    |-- Inferencia Red YOLOv8
        |                                   |-- Bounding Box & Confianza
        |                                   |-- Detección Térmica de Llamas
        |<-- 4. {verificado_por_ia: true, --|
        |        confianza: 0.94, boxes}    |
        v                                   v
```

### Operaciones Críticas de API

#### 1. Validar Evidencia con Visión Computacional (`POST /api/v1/vision/validar-evidencia`)
* **Entrada:** `multipart/form-data` con campo `archivo` (imagen JPEG/PNG/WebP o video MP4/WebM).
* **Validaciones:** Límite de 20 MB y validación estricta de encabezados MIME.
* **Procesamiento:** Ejecuta YOLOv8 Nano buscando clases críticas (`fire`, `smoke`, `car`, `truck`) y análisis térmico de píxeles incandescentes.
* **Respuesta:**
  ```json
  {
    "verificado_por_ia": true,
    "nivel_confianza": 0.92,
    "total_objetos_detectados": 1,
    "detecciones": [
      {
        "clase": "fire",
        "confianza": 0.92,
        "bounding_box": [120.5, 45.0, 310.2, 280.0]
      }
    ],
    "motor": "YOLOv8 Nano (Deep Learning PyTorch) + Analizador Térmico"
  }
  ```

#### 2. Clasificar Urgencia por NLP (`POST /api/v1/nlp/clasificar-urgencia`)
* **Entrada:** `application/json` (`{"texto": "Fuga de gas en garrafa de cocina"}`).
* **Procesamiento:** Vectorización TF-IDF e inferencia probabilística con Random Forest.
* **Respuesta:**
  ```json
  {
    "categoria_predicha": "CRITICO_GAS",
    "severidad": "CRITICA",
    "confianza": 0.95,
    "palabras_clave": ["fuga", "gas", "garrafa"]
  }
  ```

#### 3. Health Check (`GET /health`)
* **Respuesta:** HTTP 200 (`{"status": "HEALTHY", "service": "ms5_ia_mcp_backend", "version": "1.0.0"}`).

---

## 5. Comandos de Inicialización y Ejecución

### Paso 1: Instalar Dependencias
```bash
# Crear y activar entorno virtual
python -m venv venv
# En Windows:
.\venv\Scripts\activate
# En Linux/macOS:
source venv/bin/activate

# Instalar dependencias requeridas
pip install -r requirements.txt
```

### Paso 2: Configurar Variables de Entorno
```bash
cp .env.example .env
```
Contenido de `.env`:
```dotenv
APP_NAME="MS-05 Inferencia IA Core"
APP_ENV=development
PORT=8005
YOLO_MODEL_PATH=yolov8n.pt
```

### Paso 3: Iniciar Servidor de Inferencia
```bash
# Iniciar con Uvicorn en localhost (Puerto 8005)
python -m uvicorn api.main_ia:app_ia --host 127.0.0.1 --port 8005 --reload
```
> [!NOTE]
> Al ingresar a `http://localhost:8005/` o `http://127.0.0.1:8005/` en el navegador, el microservicio redirige automáticamente a Swagger UI (`/docs`). Evite abrir `http://0.0.0.0:8005` directamente en navegadores Windows.

### Paso 4: Ejecución de Tests Automatizados
```bash
pytest
```
*Nota: El archivo `pytest.ini` configura automáticamente la inclusión del directorio raíz en `PYTHONPATH`.*

---

## 6. Enlaces y Documentación de Pruebas

* **Swagger UI Interactivo:** `http://localhost:8005/docs`
* **Especificación ReDoc:** `http://localhost:8005/redoc`
* **Health Check Endpoint:** `http://localhost:8005/health`
* **Suite de Pruebas de Modelos:** [test_ia_services.py](file:///C:/Users/Usuario/Documents/U/Semestre%20II-2026/SW2/SegundoParcial/ms5_ia_mcp_backend/tests/test_ia_services.py)
