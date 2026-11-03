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

logger = logging.getLogger("reports_service")

# Directorio base para artefactos generados
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "static", "generated_reports")


class GenerarReporteTextoRequest(BaseModel):
    instruccion: str
    generar_multimodal: bool = True
    voz_tts: str = "es-BO-MarceloNeural"


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


reports_service_default = ReportsService()
