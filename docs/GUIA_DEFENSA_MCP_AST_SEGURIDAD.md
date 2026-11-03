# GUÍA DE DEFENSA TÉCNICA: SERVIDOR MCP Y PARSER SINTÁCTICO AST (SEGURIDAD DEFENSIVA)

**Módulo:** `ms5_ia_mcp_backend`  
**Semestre:** 2/2026 - INF512 (Ingeniería de Software II - UAGRM)  
**Docente:** M.Sc. Ing. Rolando Antonio Martinez Canedo  
**Responsable:** Nataly Martínez  
**Rol:** Subagente Especialista en IA Cognitiva y Seguridad Defensiva  

---

## 1. ¿QUÉ ES MODEL CONTEXT PROTOCOL (MCP) Y POR QUÉ ES VITAL?

**Model Context Protocol (MCP)** es un estándar abierto desarrollado para permitir que los modelos de lenguaje (LLMs y Agentes de IA) interactúen de forma segura, estructurada y bidireccional con bases de datos, APIs de negocio y herramientas operativas.

En el sistema de bomberos, un modelo de lenguaje no debe tener acceso directo ni credenciales de administrador a las bases de datos transaccionales de PostgreSQL, Spring Boot o DynamoDB. MCP actúa como un **puente seguro y auditado** que expone un catálogo de herramientas tipadas:

```
+---------------------------------------------------------------------------------------------------+
|                        ARQUITECTURA DE INTEGRACIÓN MODEL CONTEXT PROTOCOL (MCP)                   |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|   +-----------------------+              JSON-RPC / HTTP POST            +--------------------+   |
|   |                       | -------------------------------------------> |                    |   |
|   |  AGENTE COGNITIVO     |                                              |  MS-05 IA CORE     |   |
|   |  O COMANDANTE POR VOZ | <------------------------------------------- |  (SERVIDOR MCP)    |   |
|   |                       |              Resultados Estructurados        |                    |   |
|   +-----------------------+                                              +---------+----------+   |
|                                                                                    |              |
|                                                                                    v              |
|                                                                          +--------------------+   |
|                                                                          | CATÁLOGO DE        |   |
|                                                                          | HERRAMIENTAS       |   |
|                                                                          +---------+----------+   |
|                                                                                    |              |
|         +----------------------------------+----------------------------------+----+              |
|         |                                  |                                  |                   |
|         v                                  v                                  v                   |
|   [ Tool 1 ]                         [ Tool 2 ]                         [ Tool 3 ]                |
|   verificar_hidrantes_cercanos       consultar_stock_estacion           ejecutar_consulta_segura  |
|   (lat, lng, radio_metros)           (estacion, categoria)              (consulta_sql)            |
|         |                                  |                                  |                   |
|         | [ Tipado Pydantic ]              | [ Tipado Pydantic ]              |                   |
|         v                                  v                                  v                   |
|   +---------------------------------------------------------------------------+----------------+  |
|   |              CAPA 2: VALIDADOR SINTÁCTICO AST (SQLGLOT)                   |                |  |
|   +---------------------------------------------------------------------------+                |  |
|                                         |                                                      |  |
|                                         v [ Solo SELECT / Lista Blanca ]                       |  |
|   +--------------------------------------------------------------------------------------------+  |
|   |              CAPA 3: TRANSACCIÓN FORZADA READ ONLY                                         |  |
|   |              SET TRANSACTION READ ONLY;                                                    |  |
|   +--------------------------------------------------------------------------------------------+  |
|                                         |                                                         |
|                                         v                                                         |
|                          [ Bases de Datos Operativas ]                                            |
|                                                                                                   |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. EL MODELO DE DEFENSA EN PROFUNDIDAD (3 CAPAS)

Cuando un agente de IA genera consultas dinámicas en lenguaje SQL (Text-to-SQL) para responder preguntas analíticas del comandante, existe el riesgo crítico de **Inyecciones SQL Indirectas** (Prompt Injection hacia SQL Injection).

Para neutralizar cualquier vector de ataque, Nataly diseñó una arquitectura de **Defensa en Profundidad en 3 Capas**:

```
+---------------------------------------------------------------------------------------------------+
|                            LAS 3 CAPAS DE DEFENSA EN PROFUNDIDAD                                  |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|   CAPA 1: TOOL CALLING TIPADO (PYDANTIC SCHEMAS)                                                  |
|   • Los parámetros son fuertemente tipados (float, int, enum).                                    |
|   • Imposibilita la concatenación de cadenas arbitrarias en los endpoints de búsqueda.           |
|                                                                                                   |
|                                  |                                                                |
|                                  v                                                                |
|   CAPA 2: AUDITORÍA SINTÁCTICA AST (ABSTRACT SYNTAX TREE CON SQLGLOT)                             |
|   • Bloqueador de Tokens Destructivos: DROP, TRUNCATE, UPDATE, DELETE, ALTER, GRANT, EXEC.       |
|   • Bloqueador de Multi-sentencias: Prohíbe múltiples queries separadas por ';'.                  |
|   • Verificación de Sentencia Raíz: Solo permite instancias de exp.Select.                        |
|   • Lista Blanca Estricta de Tablas: Solo tablas operativas autorizadas (hidrantes, camiones...). |
|   • Aislamiento de Schemas Sensibles: Bloqueo explícito de usuarios, contraseñas y pg_catalog.    |
|                                                                                                   |
|                                  |                                                                |
|                                  v                                                                |
|   CAPA 3: FORZADO DE TRANSACCIÓN READ ONLY EN EL MOTOR DE BASE DE DATOS                           |
|   • Ejecución obligatoria de: SET TRANSACTION READ ONLY;                                          |
|   • Incluso si una vulnerabilidad de día cero atravesara el AST, el motor de base de datos        |
|     rechazará a nivel de kernel cualquier operación de escritura I/O.                             |
|                                                                                                   |
+---------------------------------------------------------------------------------------------------+
```

---

## 3. BANCO DE PRUEBAS CONTRA INYECCIONES REALES

A continuación se detallan los vectores de ataque probados y verificados en los tests unitarios automatizados (`tests/test_ast_validator.py`):

### Caso 1: Inyección Clásica Multi-sentencia (Piggybacking)
* **Payload Atacante:** `SELECT * FROM hidrantes; DROP TABLE hidrantes;`
* **Resultado del AST:** ❌ **RECHAZADA AUTOMÁTICAMENTE**
* **Motivo:** Multi-sentencias detectadas en el árbol sintáctico. Solo se permite una única consulta atómica.

### Caso 2: Intento de Sabotaje Operativo (Manipulación de Datos)
* **Payload Atacante:** `UPDATE camiones SET agua_actual = 0 WHERE id = 'CAM-B01';`
* **Resultado del AST:** ❌ **RECHAZADA CON HTTP 403 FORBIDDEN**
* **Motivo:** Token `UPDATE` denegado. La raíz de la sentencia no es `exp.Select`.

### Caso 3: Robo de Credenciales y Hash de Contraseñas
* **Payload Atacante:** `SELECT username, password_hash FROM tb_usuarios_sso;`
* **Resultado del AST:** ❌ **RECHAZADA POR SCHEMA RESTRINGIDO**
* **Motivo:** Acceso denegado a tablas protegidas de autenticación (`tb_usuarios_sso`). La tabla no figura en la lista blanca de telemetría bomberil.

### Caso 4: Reconocimiento del Sistema (Reconnaissance)
* **Payload Atacante:** `SELECT tablename FROM pg_catalog.pg_tables;`
* **Resultado del AST:** ❌ **RECHAZADA POR TABLA DEL SISTEMA**
* **Motivo:** Intento de inspección de metadatos internos del motor (`pg_catalog`).

### Caso 5: Consulta Analítica Legítima (Happy Path)
* **Payload del Comandante:** `SELECT id, caudal_litros_min, zona FROM hidrantes WHERE zona = 'NORTE' AND estado = 'OPERATIVO'`
* **Resultado del AST:** ✅ **VALIDADA Y EJECUTADA CON ÉXITO**
* **Transacción:** `SET TRANSACTION READ ONLY;`
* **Datos Devueltos:** Hidrantes HID-SCZ-101 y HID-SCZ-102 con telemetría en tiempo real.

---

## 4. PREGUNTAS CLAVE PARA LA DEFENSA ANTE EL DOCENTE

### P1: ¿Por qué no usar simplemente expresiones regulares (RegEx) para sanitizar el SQL?
> **Respuesta de Nataly:** *"Las expresiones regulares operan a nivel léxico plano y son trivialmente vulnerables a bypass mediante comentarios SQL (`SELECT/**/FROM`), concatenaciones (`CONCAT`), ofuscación hexadecimal o saltos de línea. El enfoque con `sqlglot` parsea la consulta en un **Árbol de Sintaxis Abstracta (AST)**, analizando la semántica gramatical del lenguaje SQL formal. Esto permite verificar la estructura matemática del árbol y comprobar rigurosamente que el nodo raíz sea una proyección `exp.Select` y que las hojas de tablas pertenezcan únicamente a la lista blanca."*

### P2: ¿Qué sucede si el modelo de lenguaje intenta hacer un `UNION SELECT` para leer contraseñas?
> **Respuesta de Nataly:** *"El AST recorre todos los nodos de tipo `exp.Table`. Si se inyecta un `UNION SELECT ... FROM tb_usuarios_sso`, el validador extrae de inmediato el nombre de la tabla inyectada (`tb_usuarios_sso`), detecta que pertenece al conjunto de `TABLAS_SISTEMA_PROHIBIDAS` y rechaza la consulta antes de que toque la base de datos."*

### P3: ¿Por qué es necesario forzar la transacción `SET TRANSACTION READ ONLY` si el AST ya validó la consulta?
> **Respuesta de Nataly:** *"Porque en ingeniería de software crítica para emergencias aplicamos el principio de **Defensa en Profundidad**. Ninguna capa de software debe considerarse infalible. Si se descubriera una técnica de evasión desconocida en el parser sintáctico, la Capa 3 delega la protección al propio motor de almacenamiento relacional, impidiendo físicamente cualquier alteración de registros en disco."*

---

## 5. RADIOGRAFÍA LÍNEA POR LÍNEA: DÓNDE VIVEN LAS 3 CAPAS EN EL CÓDIGO

A continuación se detallan los fragmentos de código exactos de cada archivo y la explicación de qué hace cada bloque:

### A. Capa 1: Tool Calling Tipado (`services/mcp_security/mcp_server.py`)
En lugar de permitir que un agente envíe texto libre hacia la base de datos, definimos esquemas fuertemente tipados con Pydantic:

```python
# Capa 1: Validación de Tipos Estricta antes de invocar la lógica
class HidrantesInput(BaseModel):
    latitud: float = Field(..., description="Latitud GPS de la emergencia")
    longitud: float = Field(..., description="Longitud GPS de la emergencia")
    radio_metros: int = Field(500, description="Radio de búsqueda en metros")

def verificar_hidrantes_cercanos(latitud: float, longitud: float, radio_metros: int = 500):
    # La entrada ya viene casteada como float e int.
    # Es físicamente imposible inyectar comillas o sentencias SQL maliciosas aquí.
    ...
```
* **¿Qué hace cada línea?** Pydantic intercepta la petición. Si alguien intenta mandar `latitud: "105 OR 1=1"`, FastAPI y Pydantic arrojan un error `422 Unprocessable Entity` antes de que la función se ejecute.

---

### B. Capa 2: Parser Sintáctico AST con `sqlglot` (`services/mcp_security/ast_validator.py`)
Cuando el agente o comandante requiere consultas dinámicas (Text-to-SQL), entra en acción el validador gramatical:

```python
class ASTValidator:
    def validar(self, sql_query: str) -> ASTValidationResult:
        # 1. Filtro Léxico Rápido: Bloquea tokens destructivos de antemano
        sql_clean = re.sub(r"--.*?$|/\*.*?\*/", "", sql_query, flags=re.MULTILINE)
        tokens_encontrados = [t for t in TOKENS_MODIFICACION_PROHIBIDOS if re.search(r'\b' + t + r'\b', sql_clean, re.IGNORECASE)]
        if tokens_encontrados:
            return ASTValidationResult(valido=False, motivo_rechazo="Tokens no permitidos: " + str(tokens_encontrados))

        # 2. Bloqueo de Multi-sentencias: Prohíbe queries separadas por ';'
        expresiones = sqlglot.parse(sql_query, read="postgres")
        if len(expresiones) != 1:
            return ASTValidationResult(valido=False, motivo_rechazo="Multi-sentencias no permitidas")

        expresion = expresiones[0]

        # 3. Verificación de Nodo Raíz: OBLIGATORIAMENTE exp.Select
        if not isinstance(expresion, exp.Select):
            return ASTValidationResult(valido=False, motivo_rechazo="Solo se permiten consultas SELECT")

        # 4. Inspección de Hojas del Árbol (Nodos exp.Table):
        # Recorre todos los nodos de tablas del árbol sintáctico (incluso subconsultas y UNION)
        tablas_consultadas = {t.name.lower() for t in expresion.find_all(exp.Table)}

        # 5. Aislamiento de Tablas Protegidas (Credenciales / Sistema)
        if any(t in TABLAS_SISTEMA_PROHIBIDAS for t in tablas_consultadas):
            return ASTValidationResult(valido=False, motivo_rechazo="Acceso denegado a tablas protegidas")

        # 6. Lista Blanca Estricta
        if not tablas_consultadas.issubset(self.tablas_permitidas):
            return ASTValidationResult(valido=False, motivo_rechazo="Tablas fuera de la lista blanca")

        # Éxito: Retorna el SQL normalizado de solo lectura
        return ASTValidationResult(valido=True, tipo_sentencia="SELECT", ...)
```

---

### C. Capa 3: Forzado de Transacción READ ONLY (`services/mcp_security/ast_validator.py`)
Incluso si el AST valida la consulta, la capa de base de datos impone la restricción física a nivel de sesión:

```python
    @staticmethod
    def forzar_transaccion_solo_lectura() -> str:
        # Capa 3: Impide operaciones de I/O de escritura en el motor relacional
        return "SET TRANSACTION READ ONLY;"
```
* **¿Qué hace?** Cualquier intento de escritura generará un fallo nativo en el motor de base de datos (`ERROR: cannot execute INSERT/UPDATE in a read-only transaction`).

---

### D. RAG Grounding Determinista (`services/reports_rag/rag_engine.py`)
Garantiza cero alucinaciones contables en los reportes:

```python
    def calcular_metricas(self, params: ReporteParametros) -> Dict[str, Any]:
        datos_sistema = self.obtener_datos_actualizados()
        flota = datos_sistema["flota"]
        if params.cuadrante != "TODOS":
            flota = [c for c in flota if c["cuadrante"] == params.cuadrante]

        # Cero Alucinaciones: Sumas aritméticas exactas en Python
        total_camiones = len(flota)
        camiones_disp = sum(1 for c in flota if c["estado"] == "DISPONIBLE")
        total_agua = sum(c["agua_actual"] for c in flota)
        cap_max_agua = sum(c["capacidad_max"] for c in flota)
        pct_agua = round((total_agua / cap_max_agua * 100), 1) if cap_max_agua > 0 else 0.0

        return {"metricas": ReporteMetricasCalculadas(...), ...}
```
* **¿Qué hace?** Nunca le pide al LLM calcular `8500 + 1800`. El motor Python realiza la agregación matemática exacta y la inyecta al informe.

---

### E. Compilador Multimodal (`services/reports_rag/multimodal_generator.py`)
Compila el informe a tres artefactos físicos:
* **PDF (WeasyPrint):** Utiliza CSS Paged Media (`@page { size: A4; @bottom-right { content: counter(page); } }`) para producir un documento editorial de alta fidelidad.
* **Excel (OpenPyXL):** Genera libros con estilos corporativos en rojo oscuro (`#8B0000`) y fórmulas nativas `=SUM(E4:E5)` para auditoría contable.
* **Audio (Edge-TTS):** Sintetiza la locución radial con la voz neural en español boliviano `es-BO-MarceloNeural`.

---

## 6. ¿PUEDE MAIKOL REUSAR `mcp_security` PARA SUS AGENTES TÁCTICOS?

**SÍ, con una distinción arquitectónica fundamental:**

```
+---------------------------------------------------------------------------------------------------+
|                        CÓMO SE INTEGRA EL MÓDULO MCP DE MAIKOL Y NATALY                           |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|   1. ACCIONES DE LECTURA / CONSULTA (READ-ONLY):                                                  |
|      Maikol puede reusar exactamente ast_validator.py y mcp_server.py.                            |
|      Si su agente ReAct necesita consultar hidrantes o camiones, llama a las herramientas         |
|      validadas por el AST.                                                                        |
|                                                                                                   |
|   2. ACCIONES QUE MODIFICAN ESTADO (CREATE / UPDATE):                                             |
|      REGLA DE ORO DE SEGURIDAD EN AGENTES: Un agente NUNCA ejecuta strings SQL de UPDATE directos.|
|      En su lugar, Maikol registra una herramienta tipada en el catálogo MCP:                     |
|                                                                                                   |
|         @mcp_tool                                                                                 |
|         def proponer_asignacion_camion(incidente_id: str, camion_id: str):                        |
|             # HITL: Requiere confirmación humana del Operador en pantalla                         |
|             return solicitar_aprobacion_operador(...)                                             |
|                                                                                                   |
|      La mutación se realiza a través de la API oficial (ej. Spring Boot o NestJS),                |
|      NUNCA inyectando SQL suelto en la base de datos.                                             |
|                                                                                                   |
+---------------------------------------------------------------------------------------------------+
```

Por lo tanto:
1. Maikol **sí puede y debe importar** `services/mcp_security/ast_validator.py` para todas las consultas que su agente ReAct genere.
2. Para las acciones que alteren datos, Maikol agregará sus propias herramientas en `services/mcp_security/mcp_server.py` utilizando esquemas Pydantic y el patrón **Human-in-the-Loop (HITL)** exigido en el Punto 4 de la materia.



  #### ¿Dónde vive cada una de las 3 Capas de Defensa en el código?
  
    +---------------------------------------------------------------------------------------------------+
    |                        LAS 3 CAPAS DE DEFENSA EN EL CÓDIGO FUENTE                                 |
    +---------------------------------------------------------------------------------------------------+
    |                                                                                                   |
    |  CAPA 1: TOOL CALLING TIPADO (PYDANTIC SCHEMAS)                                                   |
    |  • Archivo: services/mcp_security/mcp_server.py                                                   |
    |  • Código:                                                                                        |
    |      class HidrantesInput(BaseModel):                                                             |
    |          latitud: float = Field(..., description="GPS")                                           |
    |          radio_metros: int = Field(500)                                                           |
    |  • Explicación: Pydantic intercepta la petición. Si alguien inyecta "105 OR 1=1", FastAPI          |
    |    aborta con HTTP 422 antes de que la función se ejecute.                                        |
    |                                                                                                   |
    |                                     |                                                             |
    |                                     v                                                             |
    |  CAPA 2: AUDITORÍA SINTÁCTICA AST CON SQLGLOT                                                     |
    |  • Archivo: services/mcp_security/ast_validator.py                                                |
    |  • Código:                                                                                        |
    |      # 1. Filtro rápido de tokens destructivos                                                    |
    |      tokens = [t for t in TOKENS_PROHIBIDOS if re.search(r'\b' + t + r'\b', sql)]			|
    |      # 2. Bloqueo de multi-sentencias ';'                                                         |
    |      exprs = sqlglot.parse(sql, read="postgres")                                                  |
    |      # 3. Solo SELECT en la raíz                                                                  |
    |      if not isinstance(exprs[0], exp.Select): return RECHAZADA                                    |
    |      # 4. Inspección de tablas en el árbol                                                        |
    |      tablas = {t.name.lower() for t in exprs[0].find_all(exp.Table)}				|
    |      if not tablas.issubset(TABLAS_PERMITIDAS): return RECHAZADA                                  |
    |                                                                                                   |
    |                                     |                                                             |
    |                                     v                                                             |
    |  CAPA 3: FORZADO DE TRANSACCIÓN READ ONLY                                                         |
    |  • Archivo: services/mcp_security/ast_validator.py                                                |
    |  • Código:                                                                                        |
    |      def forzar_transaccion_solo_lectura():                                                       |
    |          return "SET TRANSACTION READ ONLY;"                                                      |
    |  • Explicación: Cualquier intento de escritura arroja un error nativo a nivel de kernel I/O      |
    |    en el motor relacional de base de datos.                                                       |
    |                                                                                                   |
    +---------------------------------------------------------------------------------------------------+
      

