# MS-05: Inferencia Cognitiva, Reportes Multimodales y Seguridad MCP (IA Core)

**Plataforma Distribuida Cuerpo de Bomberos — INF512 (Ingeniería de Software II)**  
**Semestre:** 2/2026 — UAGRM  
**Docente:** M.Sc. Ing. Rolando Antonio Martinez Canedo  
**Equipo Responsable:**
- **Nataly Martínez:** Reportes Multimodales por Voz y Parser Sintáctico AST (Seguridad MCP)
- **Jael Sandoval:** Visión Artificial (YOLOv8 Nano) y Triaje Semántico NLP

---

## 1. RESUMEN EJECUTIVO Y ALCANCE

El microservicio `MS-05 IA Core` opera como el cerebro cognitivo y la capa de defensa perimetral para el Sistema de Gestión de Emergencias del Cuerpo de Bomberos de Santa Cruz. Integra cuatro subsistemas de alta tecnología:

```
+---------------------------------------------------------------------------------------------------+
|                              MS-05 IA CORE & MCP SECURITY SERVER                                  |
|                                     (FastAPI - Puerto 8005)                                       |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|   +---------------------------------------+       +-------------------------------------------+   |
|   |   MÓDULO NATALY MARTÍNEZ              |       |   MÓDULO JAEL SANDOVAL                    |   |
|   +---------------------------------------+       +-------------------------------------------+   |
|   | 1. PIPELINE VOICE-TO-REPORT (CU-07)   |       | 3. VISIÓN ARTIFICIAL (YOLOv8)             |   |
|   |    • ASR Faster-Whisper (int8)        |       |    • Inferencia en imágenes y videos      |   |
|   |    • RAG Grounding determinista       |       |    • Detección de fuego, humo y vehículos |   |
|   |    • Salidas: PDF, Excel, MP3, MD     |       |    • Bounding boxes y score térmico       |   |
|   |                                       |       |                                           |   |
|   | 2. SERVIDOR FASTMCP & PARSER AST      |       | 4. TRIAJE SEMÁNTICO NLP                   |   |
|   |    • Inspección de AST con sqlglot    |       |    • TF-IDF Vectorizer + Random Forest    |   |
|   |    • Bloqueo anti-SQL Injection       |       |    • Clasificación de severidad ciudadana |   |
|   |    • Transacción READ ONLY forzada    |       |    • Mapeo taxonómico automático          |   |
|   +---------------------------------------+       +-------------------------------------------+   |
|                                                                                                   |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. ARQUITECTURA DE DIRECTORIOS

```
ms5_ia_mcp_backend/
├── api/
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── reports_router.py          # Endpoints Voice-to-Report Multimodal (Nataly)
│   │   └── mcp_router.py              # Endpoints Seguridad AST y FastMCP (Nataly)
│   ├── __init__.py
│   └── main_ia.py                     # Entrypoint FastAPI y registro de routers
├── docs/
│   ├── GUIA_INTEGRACION_REPORTES_VOZ.md    # Guía de pruebas cURL/Swagger de CU-07
│   └── GUIA_DEFENSA_MCP_AST_SEGURIDAD.md   # Defensa técnica para evaluación docente
├── services/
│   ├── computer_vision/
│   │   ├── __init__.py
│   │   └── vision_service.py          # YOLOv8 Deep Learning (Jael)
│   ├── mcp_security/
│   │   ├── __init__.py
│   │   ├── ast_validator.py           # Parser AST con sqlglot (Anti-SQLi) (Nataly)
│   │   └── mcp_server.py              # Herramientas MCP y base analítica mock (Nataly)
│   ├── nlp_triage/
│   │   ├── __init__.py
│   │   └── nlp_triage.py              # Clasificador TF-IDF + Random Forest (Jael)
│   └── reports_rag/
│       ├── __init__.py
│       ├── whisper_service.py         # Faster-Whisper ASR CTranslate2 int8 (Nataly)
│       ├── rag_engine.py              # RAG Grounding sin alucinaciones numéricas (Nataly)
│       ├── multimodal_generator.py    # Generador PDF WeasyPrint, OpenPyXL y Edge-TTS (Nataly)
│       └── reports_service.py         # Orquestador del pipeline de 4 etapas (Nataly)
├── static/
│   └── generated_reports/             # Artefactos compilados (PDF, XLSX, MP3, MD)
├── tests/
│   ├── test_ast_validator.py          # 15 tests unitarios de seguridad AST y FastMCP
│   ├── test_ia_services.py            # 6 tests de visión y NLP
│   └── test_reports_rag.py            # 10 tests unitarios y de integración de reportes
├── Dockerfile
├── pytest.ini
└── requirements.txt
```

---

## 3. CATÁLOGO COMPLETO DE ENDPOINTS REST

### Módulo Nataly: Reportes Multimodales y Seguridad MCP

| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/api/v1/reportes/generar-por-voz` | Ingesta de audio WAV/MP3, transcripción Whisper y compilación de PDF, XLSX, MP3 y MD |
| `POST` | `/api/v1/reportes/generar-por-texto` | Ingesta de comando en lenguaje natural, RAG determinista y compilación multimodal |
| `GET` | `/api/v1/reportes/{id_reporte}` | Consulta del informe estructurado en formato Markdown |
| `GET` | `/api/v1/reportes/descargar/pdf/{id}` | Descarga de documento formal compilado con WeasyPrint y CSS Paged Media |
| `GET` | `/api/v1/reportes/descargar/excel/{id}`| Descarga de hoja de cálculo OpenPyXL con estilos rojo oscuro y fórmulas `=SUM(...)` |
| `GET` | `/api/v1/reportes/reproducir/audio/{id}`| Streaming de audio neural en español boliviano (`es-BO-MarceloNeural`) vía Edge-TTS |
| `POST` | `/api/v1/mcp/validar-sql` | Auditoría sintáctica de consultas mediante Árbol de Sintaxis Abstracta (`sqlglot`) |
| `POST` | `/api/v1/mcp/ejecutar-sql-seguro` | Ejecución de consulta analítica bajo contexto forzado `SET TRANSACTION READ ONLY;` |
| `GET` | `/api/v1/mcp/herramientas` | Catálogo de herramientas tipadas MCP expuestas para agentes cognitivos |
| `POST` | `/api/v1/mcp/herramientas/{tool_name}/ejecutar` | Invocación de herramientas tipadas con esquemas Pydantic |

### Módulo Jael: Visión Computacional y Triaje NLP

| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/api/v1/vision/validar-evidencia` | Análisis con YOLOv8 de imágenes/videos (límite 20 MB) |
| `POST` | `/api/v1/vision/validar-evidencia-url` | Verificación de URLs de imágenes de siniestros |
| `POST` | `/api/v1/nlp/clasificar-urgencia` | Triaje y severidad de denuncias con TF-IDF y Random Forest |

---

## 4. GUÍA DE INSTALACIÓN Y EJECUCIÓN

### Paso 1: Configurar el Entorno Virtual

```bash
cd ms5_ia_mcp_backend

# Crear el entorno virtual con Python 3.11+
python3 -m venv .venv

# Activar el entorno virtual
source .venv/bin/activate  # En Linux/macOS
# .venv\Scripts\activate   # En Windows

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt
```

### Paso 2: Ejecutar la Suite de Pruebas Automatizadas

```bash
# Ejecutar todas las 31 pruebas unitarias e integración
pytest
```

Resultado verificado:
```text
tests/test_ast_validator.py ...............                              [ 48%]
tests/test_ia_services.py ......                                         [ 67%]
tests/test_reports_rag.py ..........                                     [100%]

============================== 31 passed in 5.94s ==============================
```

### Paso 3: Iniciar el Servidor API

```bash
uvicorn api.main_ia:app_ia --host 0.0.0.0 --port 8005 --reload
```

* **Swagger UI:** `http://localhost:8005/docs`
* **Health Check:** `http://localhost:8005/health`

---

## 5. DOCUMENTACIÓN ADICIONAL PARA EVALUACIÓN

Para consultar las explicaciones teóricas y guías paso a paso para la defensa ante el docente:
- [GUIA_INTEGRACION_REPORTES_VOZ.md](file:///home/nataly/Projects/sw2/ms5_ia_mcp_backend/docs/GUIA_INTEGRACION_REPORTES_VOZ.md)
- [GUIA_DEFENSA_MCP_AST_SEGURIDAD.md](file:///home/nataly/Projects/sw2/ms5_ia_mcp_backend/docs/GUIA_DEFENSA_MCP_AST_SEGURIDAD.md)
