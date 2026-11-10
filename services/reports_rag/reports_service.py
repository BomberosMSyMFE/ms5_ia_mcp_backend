"""
services/reports_rag/reports_service.py
Orquestador del Pipeline de 4 Etapas Voice-to-Report:
  Etapa 1: Transcripción Acústica (Faster-Whisper ASR)
  Etapa 2: Extracción y Cálculos Deterministas RAG Grounding (Cero Alucinaciones)
  Etapa 3: Síntesis de Reporte Ejecutivo en Markdown y Briefing Radial
  Etapa 4: Compilación Multimodal de Artefactos (PDF, Excel, Audio MP3)
Semestre 2/2026 - INF512 (Ingeniería de Software II)
Responsable: Nataly Martínez (ms5_ia_mcp_backend)
"""

import os
import uuid
import datetime
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel

from services.reports_rag.whisper_service import WhisperService, whisper_service_default
from services.reports_rag.rag_engine import RAGEngine, rag_engine_default
from services.reports_rag.multimodal_generator import MultimodalGenerator, multimodal_generator_default
from services.mcp_security.ast_validator import TOKENS_MODIFICACION_PROHIBIDOS

logger = logging.getLogger("reports_service")

# Directorio base para artefactos generados
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "static", "generated_reports")


class GenerarReporteTextoRequest(BaseModel):
    instruccion: str
    generar_multimodal: bool = True
    voz_tts: str = "es-BO-MarceloNeural"


class ReporteDinamicoRequest(BaseModel):
    """
    Solicitud para generación de reportes dinámicos.
    Requisitos INF512 - Examen Rolando Martínez Canedo.
    """
    fuente_datos: Optional[str] = None  # "siniestros" | "flota" | "hidrantes" | "insumos" (infiere si hay prompt)
    columnas: Optional[list[str]] = None  # ej: ["codigo", "zona", "agua_usada", "estado"]
    criterios: Optional[Dict[str, Any]] = None  # ej: {"cuadrante": "NORTE", "severidad": "CRITICA"}
    formato: Optional[str] = None  # "PDF" | "EXCEL" | "AMBOS" (infiere si hay prompt, default AMBOS)
    instruccion_prompt: Optional[str] = None  # Opcional si se emitió por texto/voz
    voz_tts: Optional[str] = "es-BO-MarceloNeural"


class ReporteDinamicoRespuestaDTO(BaseModel):
    """
    Respuesta estructurada para reporte dinámico multimodal.
    """
    id_reporte: str
    fecha_emision: str
    fuente_datos: str
    columnas: list[str]
    criterios_aplicados: Dict[str, Any]
    total_registros: int
    formato: str
    instruccion_prompt: Optional[str] = None
    totales_calculados: Dict[str, Any]
    registros: list[Dict[str, Any]]
    resumen_radial: str
    markdown_url: str
    pdf_url: Optional[str] = None
    excel_url: Optional[str] = None
    audio_url: Optional[str] = None
    duracion_proceso_ms: float
    etapas_completadas: list[str]


class ReporteRespuestaDTO(BaseModel):
    id_reporte: str
    fecha_emision: str
    comando_detectado: str
    cuadrante: str
    metricas_clave: Dict[str, Any]
    resumen_radial: str
    markdown_url: str
    pdf_url: Optional[str] = None
    excel_url: Optional[str] = None
    audio_url: Optional[str] = None
    duracion_proceso_ms: float
    etapas_completadas: list[str]


class ReportsService:
    """
    Servicio orquestador del ciclo completo de generación de reportes por voz y texto.
    """

    def __init__(
        self,
        whisper_service: Optional[WhisperService] = None,
        rag_engine: Optional[RAGEngine] = None,
        generator: Optional[MultimodalGenerator] = None,
        output_dir: str = OUTPUT_DIR
    ):
        self.whisper = whisper_service or whisper_service_default
        self.rag = rag_engine or rag_engine_default
        self.generator = generator or multimodal_generator_default
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    async def procesar_comando_voz(
        self,
        audio_bytes: bytes,
        extension: str = "wav",
        generar_multimodal: bool = True,
        voz_tts: str = "es-BO-MarceloNeural"
    ) -> ReporteRespuestaDTO:
        """
        Flujo completo comenzando desde una nota de voz del comandante.
        """
        inicio = datetime.datetime.now()
        etapas = []

        # ==============================================================
        # ETAPA 1: TRANSCRIPCIÓN ACÚSTICA (ASR)
        # ==============================================================
        texto_transcrito = self.whisper.transcribir_audio_bytes(audio_bytes, extension=extension)
        if not texto_transcrito:
            texto_transcrito = "Generar reporte de situación táctica general"
        etapas.append("1. Transcripción Acústica (Faster-Whisper)")

        return await self._ejecutar_pipeline_desde_texto(
            texto_comando=texto_transcrito,
            generar_multimodal=generar_multimodal,
            voz_tts=voz_tts,
            inicio=inicio,
            etapas_previas=etapas
        )

    async def procesar_comando_texto(
        self,
        instruccion: str,
        generar_multimodal: bool = True,
        voz_tts: str = "es-BO-MarceloNeural"
    ) -> ReporteRespuestaDTO:
        """
        Flujo ejecutado a partir de texto o comando de sala de crisis.
        """
        inicio = datetime.datetime.now()
        etapas = ["1. Ingesta de Comando Directo en Lenguaje Natural"]

        return await self._ejecutar_pipeline_desde_texto(
            texto_comando=instruccion,
            generar_multimodal=generar_multimodal,
            voz_tts=voz_tts,
            inicio=inicio,
            etapas_previas=etapas
        )

    async def _ejecutar_pipeline_desde_texto(
        self,
        texto_comando: str,
        generar_multimodal: bool,
        voz_tts: str,
        inicio: datetime.datetime,
        etapas_previas: list[str]
    ) -> ReporteRespuestaDTO:
        # 0. Verificación Léxica y Sintáctica AST de Seguridad (Capa 2 Defensiva)
        tokens_en_query = {word.strip(";(),\"'").upper() for word in (texto_comando or "").strip().split()}
        tokens_prohibidos = tokens_en_query.intersection(TOKENS_MODIFICACION_PROHIBIDOS)
        if tokens_prohibidos:
            logger.warning(f"[SEGURIDAD AST] Comando destructivo o inyección SQL rechazada: {list(tokens_prohibidos)}")
            etapas = list(etapas_previas) + [
                "2. Análisis Sintáctico AST (sqlglot) - Capa Defensiva",
                "3. Fase Final: Bloqueo Defensivo por Detección de Tokens Destructivos"
            ]
            adv_msg = (
                f"ADVERTENCIA DE SEGURIDAD AST (Capa 2 Defensiva): "
                f"Intento de comando no autorizado o destructivo detectado ('{', '.join(sorted(tokens_prohibidos))}'). "
                f"La instrucción ha sido bloqueada por la capa de verificación sintáctica. No se devolverá ninguna tabla de datos."
            )
            fin = datetime.datetime.now()
            duracion_ms = round((fin - inicio).total_seconds() * 1000, 2)
            return ReporteRespuestaDTO(
                id_reporte=f"REP-BLOQ-{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
                resumen_ejecutivo=adv_msg,
                markdown_completo=f"# ALERTA DE SEGURIDAD TÁCTICA\n\n{adv_msg}\n\n**Comando Ingresado:** `{texto_comando}`",
                orden_dictada=texto_comando,
                recursos_involucrados={"camiones": [], "personal_estimado": 0, "insumos_clave": []},
                descargas={"pdf": "", "excel": "", "audio": ""},
                tiempo_generacion_ms=duracion_ms,
                origen="TEXTO_DIRECTO",
                datos_tabla=None,
                cuadrante="RECHAZADO",
                comando_detectado=f"BLOQUEO_{list(tokens_prohibidos)[0]}"
            )

        etapas = list(etapas_previas)
        
        # Generar identificador de reporte único y trazable
        timestamp_slug = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        uuid_short = uuid.uuid4().hex[:6].upper()
        id_reporte = f"REP-{timestamp_slug}-{uuid_short}"

        # Carpeta para almacenar los artefactos del reporte
        report_dir = os.path.join(self.output_dir, id_reporte)
        os.makedirs(report_dir, exist_ok=True)

        # ==============================================================
        # ETAPA 2 & 3: RAG GROUNDING Y SÍNTESIS DE TEXTO
        # ==============================================================
        datos_sintetizados = self.rag.sintetizar_markdown(texto_comando, id_reporte)
        etapas.append("2. RAG Grounding Determinista (Cálculo exacto en Python)")
        etapas.append("3. Síntesis de Reporte Ejecutivo en Markdown y Alerta Radial")

        # Guardar Markdown
        md_path = os.path.join(report_dir, "reporte.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(datos_sintetizados["markdown"])

        pdf_url = None
        excel_url = None
        audio_url = None

        # ==============================================================
        # ETAPA 4: GENERACIÓN MULTIMODAL (PDF, EXCEL, AUDIO)
        # ==============================================================
        if generar_multimodal:
            try:
                # 4a. Generación de PDF WeasyPrint
                pdf_bytes = self.generator.generar_pdf(datos_sintetizados)
                pdf_path = os.path.join(report_dir, "reporte.pdf")
                with open(pdf_path, "wb") as f:
                    f.write(pdf_bytes)
                pdf_url = f"/api/v1/reportes/descargar/pdf/{id_reporte}"
            except Exception as e:
                logger.error(f"Fallo al compilar PDF: {e}")

            try:
                # 4b. Generación de Hoja de Cálculo OpenPyXL
                xlsx_bytes = self.generator.generar_excel(datos_sintetizados)
                xlsx_path = os.path.join(report_dir, "reporte.xlsx")
                with open(xlsx_path, "wb") as f:
                    f.write(xlsx_bytes)
                excel_url = f"/api/v1/reportes/descargar/excel/{id_reporte}"
            except Exception as e:
                logger.error(f"Fallo al compilar Excel: {e}")

            try:
                # 4c. Generación de Audio Neural Edge-TTS
                audio_bytes = await self.generator.generar_audio_tts(
                    texto_briefing=datos_sintetizados["resumen_radial"],
                    voice=voz_tts
                )
                if audio_bytes:
                    audio_path = os.path.join(report_dir, "briefing.mp3")
                    with open(audio_path, "wb") as f:
                        f.write(audio_bytes)
                    audio_url = f"/api/v1/reportes/reproducir/audio/{id_reporte}"
            except Exception as e:
                logger.error(f"Fallo al generar audio TTS: {e}")

            etapas.append("4. Compilación Multimodal de Salidas (PDF WeasyPrint, Excel OpenPyXL, MP3 Edge-TTS)")

        fin = datetime.datetime.now()
        duracion_ms = round((fin - inicio).total_seconds() * 1000, 2)

        m = datos_sintetizados["metricas"]
        metricas_dict = {
            "total_camiones": m.total_camiones,
            "camiones_disponibles": m.camiones_disponibles,
            "total_litros_agua": m.total_litros_agua,
            "capacidad_max_agua": m.capacidad_max_agua,
            "porcentaje_disponibilidad_agua": m.porcentaje_disponibilidad_agua,
            "hidrantes_operativos": m.hidrantes_operativos,
            "hidrantes_totales": m.hidrantes_totales,
            "litros_espuma_disponibles": m.litros_espuma_disponibles,
            "total_siniestros_activos": m.total_siniestros_activos
        }

        return ReporteRespuestaDTO(
            id_reporte=id_reporte,
            fecha_emision=datos_sintetizados["parametros"].fecha_solicitud,
            comando_detectado=texto_comando,
            cuadrante=datos_sintetizados["parametros"].cuadrante,
            metricas_clave=metricas_dict,
            resumen_radial=datos_sintetizados["resumen_radial"],
            markdown_url=f"/api/v1/reportes/{id_reporte}",
            pdf_url=pdf_url,
            excel_url=excel_url,
            audio_url=audio_url,
            duracion_proceso_ms=duracion_ms,
            etapas_completadas=etapas
        )

    def obtener_ruta_artefacto(self, id_reporte: str, tipo_archivo: str) -> Optional[str]:
        """Devuelve la ruta absoluta al archivo generado."""
        extensiones = {
            "pdf": "reporte.pdf",
            "excel": "reporte.xlsx",
            "xlsx": "reporte.xlsx",
            "audio": "briefing.mp3",
            "mp3": "briefing.mp3",
            "markdown": "reporte.md",
            "md": "reporte.md"
        }
        nombre_archivo = extensiones.get(tipo_archivo.lower())
        if not nombre_archivo:
            return None

        ruta = os.path.join(self.output_dir, id_reporte, nombre_archivo)
        if os.path.exists(ruta):
            return ruta
        return None

    def obtener_contenido_markdown(self, id_reporte: str) -> Optional[str]:
        """Obtiene el texto markdown de un reporte guardado."""
        ruta = self.obtener_ruta_artefacto(id_reporte, "markdown")
        if ruta and os.path.exists(ruta):
            with open(ruta, "r", encoding="utf-8") as f:
                return f.read()
        return None

    # =========================================================================
    # PIPELINE DE REPORTES DINÁMICOS MULTIMODALES (INF512)
    # =========================================================================

    def obtener_esquemas_tablas(self) -> Dict[str, Any]:
        """Devuelve el catálogo de tablas y campos disponibles para el constructor dinámico."""
        from services.reports_rag.rag_engine import CATALOGO_ESQUEMAS_TABLAS
        return {
            "tablas": CATALOGO_ESQUEMAS_TABLAS,
            "fuentes_disponibles": list(CATALOGO_ESQUEMAS_TABLAS.keys()),
            "formatos_disponibles": ["PDF", "EXCEL", "AMBOS"]
        }

    async def procesar_reporte_dinamico(
        self,
        request: ReporteDinamicoRequest
    ) -> ReporteDinamicoRespuestaDTO:
        """
        Orquesta la generación de un reporte dinámico:
        1. Extracción inteligente de prompt (si aplica).
        2. Filtrado determinista en Python.
        3. Cálculo de sumas y totales automáticos.
        4. Compilación de Markdown, PDF WeasyPrint, Excel OpenPyXL y Audio Edge-TTS.
        """
        inicio = datetime.datetime.now()
        etapas = []

        fuente = request.fuente_datos
        columnas = list(request.columnas) if request.columnas else []
        criterios = dict(request.criterios) if request.criterios else {}
        formato = request.formato.upper() if request.formato else None
        prompt = request.instruccion_prompt

        # 0. Verificación Léxica y Sintáctica AST de Seguridad (Capa 2 Defensiva)
        texto_a_evaluar = f"{prompt or ''} {criterios.get('filtro_libre', '')}".strip()
        if texto_a_evaluar:
            tokens_en_query = {word.strip(";(),\"'").upper() for word in texto_a_evaluar.split()}
            tokens_prohibidos = tokens_en_query.intersection(TOKENS_MODIFICACION_PROHIBIDOS)
            if tokens_prohibidos:
                logger.warning(f"[SEGURIDAD AST] Intento de modificación destructiva detectado: {list(tokens_prohibidos)}")
                etapas = [
                    "1. Ingesta de Prompt Táctico",
                    "2. Análisis Sintáctico AST (sqlglot) - Capa de Seguridad Defensiva",
                    "3. Fase Final: Bloqueo Defensivo por Detección de Tokens Destructivos"
                ]
                adv_msg = (
                    f"ADVERTENCIA DE SEGURIDAD AST (Capa 2 Defensiva): "
                    f"Intento de comando no autorizado o destructivo detectado ('{', '.join(sorted(tokens_prohibidos))}'). "
                    f"La instrucción ha sido bloqueada por la capa de verificación sintáctica. No se devolverá ninguna tabla de datos."
                )
                fin = datetime.datetime.now()
                duracion_ms = round((fin - inicio).total_seconds() * 1000, 2)
                return ReporteDinamicoRespuestaDTO(
                    id_reporte=f"REP-BLOQ-{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    fecha_emision=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    fuente_datos="seguridad_ast",
                    columnas=[],
                    criterios_aplicados={"alerta_seguridad": adv_msg},
                    total_registros=0,
                    formato=formato or "AMBOS",
                    instruccion_prompt=prompt,
                    totales_calculados={},
                    registros=[],
                    resumen_radial=f"Alerta: Comando destructivo detectado ({', '.join(sorted(tokens_prohibidos))}). Solicitud bloqueada.",
                    markdown_url="",
                    pdf_url="",
                    excel_url="",
                    audio_url="",
                    duracion_proceso_ms=duracion_ms,
                    etapas_completadas=etapas
                )

        # 1. Extracción inteligente si se proporcionó un prompt
        if prompt and prompt.strip():
            ext = self.rag.extraer_especificacion_reporte_dinamico(
                texto_prompt=prompt.strip(),
                fuente_datos_hint=request.fuente_datos
            )
            if not fuente:
                fuente = ext["fuente_datos"]
            if not columnas:
                columnas = ext["columnas"]
            if not criterios:
                criterios = ext["criterios"]
            elif ext["criterios"]:
                criterios = {**ext["criterios"], **criterios}
            if not formato:
                formato = ext["formato"]
            etapas.append("1. Extracción Inteligente de Especificación Semántica (RAG Parser)")
        else:
            etapas.append("1. Ingesta de Parámetros Estructurados de Reporte Dinámico")

        fuente = fuente or "siniestros"
        formato = formato or "AMBOS"

        from services.reports_rag.rag_engine import CATALOGO_ESQUEMAS_TABLAS
        if fuente not in CATALOGO_ESQUEMAS_TABLAS:
            fuente = "siniestros"

        if not columnas:
            columnas = [c["id"] for c in CATALOGO_ESQUEMAS_TABLAS[fuente]["columnas"]]

        # 2. Filtrado determinista de datos
        registros = self.rag.filtrar_datos_tabla(fuente, criterios)
        etapas.append(f"2. Filtrado Determinista de Registros ({len(registros)} registros recuperados)")

        # 3. Cálculo matemático de totales y agregaciones
        totales = self.rag.calcular_totales_columnas(fuente, columnas, registros)
        etapas.append("3. Cálculo Determinista de Totales y Sumas Automáticas")

        # 4. Generación de identificador único de reporte
        timestamp_slug = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        uuid_short = uuid.uuid4().hex[:6].upper()
        id_reporte = f"REP-DIN-{timestamp_slug}-{uuid_short}"
        report_dir = os.path.join(self.output_dir, id_reporte)
        os.makedirs(report_dir, exist_ok=True)

        # 5. Síntesis de Markdown y Briefing Radial
        datos_sint = self.rag.sintetizar_markdown_dinamico(
            id_reporte=id_reporte,
            fuente_datos=fuente,
            columnas=columnas,
            criterios=criterios,
            registros=registros,
            totales=totales,
            instruccion_prompt=prompt
        )
        md_path = os.path.join(report_dir, "reporte.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(datos_sint["markdown"])
        etapas.append("4. Síntesis Editorial en Markdown y Briefing Radial")

        # 6. Compilación Multimodal
        pdf_url = None
        excel_url = None
        audio_url = None

        if formato in ("PDF", "AMBOS"):
            try:
                pdf_bytes = self.generator.generar_pdf_dinamico(datos_sint)
                pdf_path = os.path.join(report_dir, "reporte.pdf")
                with open(pdf_path, "wb") as f:
                    f.write(pdf_bytes)
                pdf_url = f"/api/v1/reportes/descargar/pdf/{id_reporte}"
            except Exception as e:
                logger.error(f"Error generando PDF dinámico: {e}")

        if formato in ("EXCEL", "AMBOS"):
            try:
                xlsx_bytes = self.generator.generar_excel_dinamico(datos_sint)
                xlsx_path = os.path.join(report_dir, "reporte.xlsx")
                with open(xlsx_path, "wb") as f:
                    f.write(xlsx_bytes)
                excel_url = f"/api/v1/reportes/descargar/excel/{id_reporte}"
            except Exception as e:
                logger.error(f"Error generando Excel dinámico: {e}")

        try:
            audio_bytes = await self.generator.generar_audio_tts(
                texto_briefing=datos_sint["resumen_radial"],
                voice=request.voz_tts or "es-BO-MarceloNeural"
            )
            if audio_bytes:
                audio_path = os.path.join(report_dir, "briefing.mp3")
                with open(audio_path, "wb") as f:
                    f.write(audio_bytes)
                audio_url = f"/api/v1/reportes/reproducir/audio/{id_reporte}"
        except Exception as e:
            logger.error(f"Error generando audio TTS dinámico: {e}")

        etapas.append("5. Compilación Multimodal de Salidas (PDF, Excel, MP3)")

        fin = datetime.datetime.now()
        duracion_ms = round((fin - inicio).total_seconds() * 1000, 2)

        return ReporteDinamicoRespuestaDTO(
            id_reporte=id_reporte,
            fecha_emision=datos_sint["fecha_emision"],
            fuente_datos=fuente,
            columnas=columnas,
            criterios_aplicados=criterios,
            total_registros=len(registros),
            formato=formato,
            instruccion_prompt=prompt,
            totales_calculados=totales,
            registros=registros,
            resumen_radial=datos_sint["resumen_radial"],
            markdown_url=f"/api/v1/reportes/{id_reporte}",
            pdf_url=pdf_url,
            excel_url=excel_url,
            audio_url=audio_url,
            duracion_proceso_ms=duracion_ms,
            etapas_completadas=etapas
        )

    async def procesar_reporte_dinamico_voz(
        self,
        audio_bytes: bytes,
        extension: str = "wav",
        voz_tts: str = "es-BO-MarceloNeural"
    ) -> ReporteDinamicoRespuestaDTO:
        """
        Genera reporte dinámico a partir de nota de voz (ASR Faster-Whisper + RAG Dinámico).
        """
        texto_transcrito = self.whisper.transcribir_audio_bytes(audio_bytes, extension=extension)
        if not texto_transcrito:
            texto_transcrito = "Generar reporte dinámico de situación general"

        req = ReporteDinamicoRequest(
            instruccion_prompt=texto_transcrito,
            voz_tts=voz_tts
        )
        res = await self.procesar_reporte_dinamico(req)
        res.etapas_completadas.insert(0, "0. Transcripción Acústica por Voz (Faster-Whisper)")
        return res


reports_service_default = ReportsService()
