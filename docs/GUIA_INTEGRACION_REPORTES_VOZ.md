# GUÍA DE INTEGRACIÓN Y PRUEBAS: PIPELINE VOICE-TO-REPORT MULTIMODAL (CU-07)

**Módulo:** `ms5_ia_mcp_backend`  
**Semestre:** 2/2026 - INF512 (Ingeniería de Software II - UAGRM)  
**Responsable:** Nataly Martínez  
**Rol:** Subagente Especialista en IA Cognitiva y Seguridad Defensiva  

---

## 1. ARQUITECTURA DEL PIPELINE DE 4 ETAPAS

El caso de uso **CU-07 (Reportes Tácticos por Voz)** permite a la Comandancia y maquinistas en la Sala de Crisis emitir instrucciones habladas o escritas para generar informes ejecutivos consolidados en 4 formatos simultáneos: **Markdown en vivo**, **PDF de alta fidelidad editorial**, **Excel analítico con fórmulas de autosuma** y **Audio MP3 con síntesis neural**.

```
+---------------------------------------------------------------------------------------------------+
|                        PIPELINE VOICE-TO-REPORT (MS-05 IA CORE)                                   |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|   [ Nota de Voz WAV/MP3 ]               [ Comando en Texto ]                                      |
|              |                                    |                                               |
|              v                                    |                                               |
|   +-----------------------+                       |                                               |
|   |  ETAPA 1: ASR STT     |                       |                                               |
|   |  (Faster-Whisper      |                       |                                               |
|   |   CTranslate2 int8)   |                       |                                               |
|   +-----------+-----------+                       |                                               |
|               | (Texto Transcrito)                |                                               |
|               +-------------------> + <-----------+                                               |
|                                     |                                                             |
|                                     v                                                             |
|                   +-----------------------------------+                                           |
|                   |  ETAPA 2: RAG GROUNDING           |                                           |
|                   |  - Extracción de Cuadrante/Filtro |                                           |
|                   |  - Consulta a Bases de Datos      |                                           |
|                   |  - Cálculo Determinista Python    | <--- [ CERO ALUCINACIONES ]               |
|                   |    (Sumas, Porcentajes, Stock)    |                                           |
|                   +-----------------+-----------------+                                           |
|                                     | (Métricas Validadas)                                        |
|                                     v                                                             |
|                   +-----------------------------------+                                           |
|                   |  ETAPA 3: SÍNTESIS DE TEXTO       |                                           |
|                   |  - Markdown Estructurado Formal   |                                           |
|                   |  - Briefing Radial Sintético      |                                           |
|                   +-----------------+-----------------+                                           |
|                                     |                                                             |
|                                     v                                                             |
|                   +-----------------------------------+                                           |
|                   |  ETAPA 4: COMPILACIÓN MULTIMODAL  |                                           |
|                   +-----------------------------------+                                           |
|                       |            |            |                                                 |
|          +------------+            |            +------------+                                    |
|          v                         v                         v                                    |
|   +--------------+          +--------------+          +--------------+                            |
|   |  WeasyPrint  |          |   OpenPyXL   |          |   Edge-TTS   |                            |
|   |  PDF Paged   |          |   Libro XLSX |          |   es-BO      |                            |
|   |  Media CSS   |          |  (=SUM Form) |          |  Marcelo     |                            |
|   +--------------+          +--------------+          +--------------+                            |
|          |                         |                         |                                    |
|          v                         v                         v                                    |
|   Reporte.pdf               Reporte.xlsx              Briefing.mp3                                |
|                                                                                                   |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. GARANTÍA DE CERO ALUCINACIONES NUMÉRICAS

En situaciones de combate contra siniestros, una cifra incorrecta de agua o camiones puede costar vidas. Por ello, el subsistema implementa la regla de **cero cálculo por LLM**:

1. **Extracción Semántica:** El analizador heurístico extrae el ámbito de la consulta (`cuadrante: "NORTE"`, `enfoque: "AGUA"`).
2. **Computación Aritmética Determinista:** Todas las métricas (volumen hídrico total, porcentaje de capacidad, camiones listos, hidrantes activos) se calculan en código Python puro mediante funciones de suma y filtrado exactas:
   $$\text{pct\_agua} = \text{round}\left(\frac{\sum \text{agua\_actual}}{\sum \text{capacidad\_max}} \times 100, 1\right)$$
3. **Inyección en Plantillas Editoriales:** Los números exactos se formatean con separadores de miles y se insertan tanto en el informe Markdown como en el PDF y el guion radial de Edge-TTS.

---

## 3. ESPECIFICACIÓN DE ENDPOINTS DISPONIBLES

| Método | Endpoint | Descripción | Formato Retorno |
|---|---|---|---|
| `POST` | `/api/v1/reportes/generar-por-voz` | Ingesta de nota de voz grabada por radio | JSON (`ReporteRespuestaDTO`) |
| `POST` | `/api/v1/reportes/generar-por-texto` | Ingesta de comando directo en texto | JSON (`ReporteRespuestaDTO`) |
| `GET` | `/api/v1/reportes/{id_reporte}` | Vista del informe estructurado en Markdown | JSON con texto Markdown |
| `GET` | `/api/v1/reportes/descargar/pdf/{id}` | Descarga de documento editorial compilado | Archivo binario `application/pdf` |
| `GET` | `/api/v1/reportes/descargar/excel/{id}`| Descarga de hoja de cálculo con fórmulas | Archivo binario `.xlsx` |
| `GET` | `/api/v1/reportes/reproducir/audio/{id}`| Streaming / descarga de briefing de voz neural | Archivo binario `audio/mpeg` |

---

## 4. GUÍA DE PRUEBAS PASO A PASO

### Prueba 1: Generación de Reporte por Texto (Swagger UI)

1. Abre el navegador en: `http://localhost:8005/docs`.
2. Ubica la sección **Reportes Multimodales por Voz** y despliega `POST /api/v1/reportes/generar-por-texto`.
3. Haz clic en **Try it out** y envía el siguiente JSON:

```json
{
  "instruccion": "Generar informe táctico de agua y camiones disponibles en Cuadrante Norte",
  "generar_multimodal": true,
  "voz_tts": "es-BO-MarceloNeural"
}
```

4. **Respuesta Esperada (200 OK):**
```json
{
  "id_reporte": "REP-20261102_203000-A1B2C3",
  "fecha_emision": "2026-11-02 20:30:00",
  "comando_detectado": "Generar informe táctico de agua y camiones disponibles en Cuadrante Norte",
  "cuadrante": "NORTE",
  "metricas_clave": {
    "total_camiones": 2,
    "camiones_disponibles": 2,
    "total_litros_agua": 10300,
    "capacidad_max_agua": 12000,
    "porcentaje_disponibilidad_agua": 85.8,
    "hidrantes_operativos": 2,
    "hidrantes_totales": 2,
    "litros_espuma_disponibles": 1450,
    "total_siniestros_activos": 2
  },
  "resumen_radial": "Informe de Situación Bomberos: En el Cuadrante NORTE, disponemos de 10.300 litros de agua en 2 camiones listos, con una capacidad hídrica operativa del 85.8 por ciento. Se reportan 2 hidrantes presurizados y 1.450 litros de espumógeno químico en depósito central.",
  "markdown_url": "/api/v1/reportes/REP-20261102_203000-A1B2C3",
  "pdf_url": "/api/v1/reportes/descargar/pdf/REP-20261102_203000-A1B2C3",
  "excel_url": "/api/v1/reportes/descargar/excel/REP-20261102_203000-A1B2C3",
  "audio_url": "/api/v1/reportes/reproducir/audio/REP-20261102_203000-A1B2C3",
  "duracion_proceso_ms": 2850.4,
  "etapas_completadas": [
    "1. Ingesta de Comando Directo en Lenguaje Natural",
    "2. RAG Grounding Determinista (Cálculo exacto en Python)",
    "3. Síntesis de Reporte Ejecutivo en Markdown y Alerta Radial",
    "4. Compilación Multimodal de Salidas (PDF WeasyPrint, Excel OpenPyXL, MP3 Edge-TTS)"
  ]
}
```

---

### Prueba 2: Descargar y Verificar los Artefactos

Copia el `id_reporte` devuelto y prueba las descargas:

1. **Descarga de PDF (WeasyPrint):**
   ```bash
   curl -O http://localhost:8005/api/v1/reportes/descargar/pdf/REP-20261102_203000-A1B2C3
   ```
   *Verificación:* Abre el PDF descargado. Notarás la cabecera oficial en rojo oscuro (`#8B0000`), el cuadro de resumen radial, los 4 cuadros de KPIs, las tablas formateadas con zebra striping y el bloque de firmas para la Cap. Nataly Martínez y el maquinista.

2. **Descarga de Hoja de Cálculo (OpenPyXL):**
   ```bash
   curl -O http://localhost:8005/api/v1/reportes/descargar/excel/REP-20261102_203000-A1B2C3
   ```
   *Verificación:* Abre el archivo `.xlsx`. Verifica las 3 pestañas:
   - `Resumen Táctico`
   - `Flota y Camiones`: Ubica la última fila de **TOTALES** y comprueba que la celda de agua contiene la fórmula `=SUM(E4:E5)`.
   - `Hidrantes e Insumos`

3. **Reproducción de Audio MP3 (Edge-TTS):**
   ```bash
   curl -O http://localhost:8005/api/v1/reportes/reproducir/audio/REP-20261102_203000-A1B2C3
   ```
   *Verificación:* Reproduce el archivo `.mp3`. Escucharás una locución fluida y natural en español boliviano (`es-BO-MarceloNeural`) leyendo las cifras consolidadas.

---

### Prueba 3: Generación por Nota de Voz (cURL)

Para enviar un archivo de audio grabado desde un micrófono o terminal:

```bash
curl -X POST "http://localhost:8005/api/v1/reportes/generar-por-voz" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "archivo_audio=@nota_comandante.wav;type=audio/wav" \
  -F "generar_multimodal=true" \
  -F "voz_tts=es-BO-MarceloNeural"
```

El subsistema transcribirá el audio en milisegundos con Faster-Whisper y ejecutará el resto del pipeline automáticamente.

---

## 5. GUÍA DE PRUEBAS EN SWAGGER: SEGURIDAD DEFENSIVA AST Y FASTMCP (LOS 5 CASOS DE ESTUDIO)

Para probar la capa de seguridad defensiva en la documentación interactiva:
1. Abre `http://localhost:8005/docs` en tu navegador.
2. Despliega la sección **Seguridad AST y Servidor FastMCP**.

Dispones de dos endpoints principales para evaluar:
* `POST /api/v1/mcp/validar-sql`: Audita el Árbol de Sintaxis Abstracta (AST con `sqlglot`) e informa si la consulta es permitida o el motivo de rechazo.
* `POST /api/v1/mcp/ejecutar-sql-seguro`: Ejecuta la consulta si supera el AST bajo la transacción forzada `SET TRANSACTION READ ONLY;`, o arroja `HTTP 403 Forbidden` si detecta cualquier intento de inyección o modificación.

---

### Caso de Prueba 1: Inyección Clásica Multi-sentencia (Piggybacking con ';')
* **Vector de Ataque:** Un atacante intenta concatenar un comando destructivo detrás de un `SELECT` válido para vaciar la tabla de hidrantes.
* **Endpoint en Swagger:** `POST /api/v1/mcp/validar-sql` o `POST /api/v1/mcp/ejecutar-sql-seguro`
* **JSON a Pegar en `Request Body`:**
  ```json
  {
    "sql": "SELECT * FROM hidrantes; DROP TABLE hidrantes;"
  }
  ```
  *(Para `ejecutar-sql-seguro`, usar clave `"consulta_sql"`)*
* **Resultado Obtenido:**
  * En `/validar-sql`: HTTP 200 con `"valido": false`
    ```json
    {
      "valido": false,
      "tipo_sentencia": "DESTRUCTIVE_TOKEN",
      "motivo_rechazo": "Intento de modificación destructiva detectado. Tokens no permitidos: ['DROP']",
      "tablas_detectadas": [],
      "sql_sanitizado": null,
      "transaccion_recomendada": "SET TRANSACTION READ ONLY;"
    }
    ```
  * En `/ejecutar-sql-seguro`: **HTTP 403 Forbidden** (Ejecución abortada inmediatamente).

---

### Caso de Prueba 2: Intento de Sabotaje Operativo (Modificación de Datos con UPDATE)
* **Vector de Ataque:** Un agente o atacante genera un `UPDATE` malicioso para vaciar los niveles de agua de los camiones cisterna.
* **Endpoint en Swagger:** `POST /api/v1/mcp/ejecutar-sql-seguro`
* **JSON a Pegar:**
  ```json
  {
    "consulta_sql": "UPDATE camiones SET agua_actual = 0 WHERE id = 'CAM-B01';"
  }
  ```
* **Resultado Obtenido:**
  * **HTTP 403 Forbidden**
  * Respuesta de Bloqueo:
    ```json
    {
      "detail": {
        "error": "INYECCION_O_SENTENCIA_NO_PERMITIDA",
        "motivo": "Intento de modificación destructiva detectado. Tokens no permitidos: ['UPDATE']",
        "tipo_sentencia": "DESTRUCTIVE_TOKEN",
        "sql_rechazado": "UPDATE camiones SET agua_actual = 0 WHERE id = 'CAM-B01';"
      }
    }
    ```

---

### Caso de Prueba 3: Extracción de Credenciales y Contraseñas (Aislamiento de Schemas)
* **Vector de Ataque:** Intento de consultar tablas del sistema de autenticación única SSO (`tb_usuarios_sso` o `usuarios`) para extraer hashes de contraseñas.
* **Endpoint en Swagger:** `POST /api/v1/mcp/validar-sql`
* **JSON a Pegar:**
  ```json
  {
    "sql": "SELECT username, password_hash FROM tb_usuarios_sso;"
  }
  ```
* **Resultado Obtenido:**
  * HTTP 200 con `"valido": false`
  * Respuesta Defensiva:
    ```json
    {
      "valido": false,
      "tipo_sentencia": "SELECT",
      "motivo_rechazo": "Acceso denegado a tablas protegidas o de credenciales: ['tb_usuarios_sso']",
      "tablas_detectadas": [
        "tb_usuarios_sso"
      ],
      "sql_sanitizado": null,
      "transaccion_recomendada": "SET TRANSACTION READ ONLY;"
    }
    ```

---

### Caso de Prueba 4: Reconocimiento del Motor de Base de Datos (Reconnaissance Interno)
* **Vector de Ataque:** Intento de inspeccionar las tablas internas del catálogo del motor (`pg_catalog` o `information_schema`).
* **Endpoint en Swagger:** `POST /api/v1/mcp/validar-sql`
* **JSON a Pegar:**
  ```json
  {
    "sql": "SELECT tablename FROM pg_catalog.pg_tables;"
  }
  ```
* **Resultado Obtenido:**
  * HTTP 200 con `"valido": false`
  * Respuesta Defensiva:
    ```json
    {
      "valido": false,
      "tipo_sentencia": "SELECT",
      "motivo_rechazo": "Tablas fuera de la lista blanca permitida: ['pg_tables']",
      "tablas_detectadas": [
        "pg_tables"
      ],
      "sql_sanitizado": null,
      "transaccion_recomendada": "SET TRANSACTION READ ONLY;"
    }
    ```

---

### Caso de Prueba 5: Consulta Analítica Legítima (Happy Path con Transacción READ ONLY)
* **Escenario Normal:** La Comandancia solicita listar los hidrantes operativos en el sector Norte.
* **Endpoint en Swagger:** `POST /api/v1/mcp/ejecutar-sql-seguro`
* **JSON a Pegar:**
  ```json
  {
    "consulta_sql": "SELECT id, caudal_litros_min, zona FROM hidrantes WHERE zona = 'NORTE' AND estado = 'OPERATIVO';"
  }
  ```
* **Resultado Obtenido:**
  * **HTTP 200 OK**
  * Respuesta Exitosa Auditada:
    ```json
    {
      "exito": true,
      "transaccion": "SET TRANSACTION READ ONLY;",
      "tablas_consultadas": [
        "hidrantes"
      ],
      "filas_retornadas": 2,
      "datos": [
        {
          "id": "HID-SCZ-101",
          "latitud": -17.7654,
          "longitud": -63.1432,
          "caudal_litros_min": 1800,
          "estado": "OPERATIVO",
          "zona": "NORTE"
        },
        {
          "id": "HID-SCZ-102",
          "latitud": -17.768,
          "longitud": -63.141,
          "caudal_litros_min": 2200,
          "estado": "OPERATIVO",
          "zona": "NORTE"
        }
      ],
      "sql_ejecutado": "SELECT id, caudal_litros_min, zona FROM hidrantes WHERE zona = 'NORTE' AND estado = 'OPERATIVO'"
    }
    ```

