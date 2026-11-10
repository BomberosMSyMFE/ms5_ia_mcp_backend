"""
api/routers/reports_router.py
Router FastAPI para el Pipeline Voice-to-Report Multimodal (CU-07):
- Ingesta de notas de voz (Faster-Whisper) y texto natural
- Generación de artefactos en 4 modalidades (PDF WeasyPrint, Excel OpenPyXL, MP3 Edge-TTS, Markdown)
- Descarga segura de reportes compilados
Semestre 2/2026 - INF512 (Ingeniería de Software II)
Responsable: Nataly Martínez (ms5_ia_mcp_backend)
"""

import os
import logging
from fastapi import APIRouter, File, UploadFile, HTTPException, Query, status, Depends
from fastapi.responses import FileResponse, PlainTextResponse

from services.reports_rag.reports_service import (
    reports_service_default,
    GenerarReporteTextoRequest,
    ReporteRespuestaDTO,
    ReporteDinamicoRequest,
    ReporteDinamicoRespuestaDTO
)
from services.security import (
    validar_operador_guard,
    UsuarioAutenticado
)

logger = logging.getLogger("reports_router")

reports_router = APIRouter(
    prefix="/api/v1/reportes",
    tags=["Reportes Multimodales por Voz"],
    dependencies=[Depends(validar_operador_guard)]
)

EXTENSIONES_AUDIO_VALIDAS = ["wav", "mp3", "m4a", "ogg", "webm", "flac"]
MAX_AUDIO_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB


# =========================================================================
# ENDPOINTS DE REPORTES DINÁMICOS (INF512 - EXAMEN ROLANDO MARTÍNEZ CANEDO)
# =========================================================================

@reports_router.get(
    "/esquemas-tablas",
    summary="Obtener catálogo de esquemas de tablas para reportes dinámicos",
    description="Retorna el catálogo de tablas ('siniestros', 'flota', 'hidrantes', 'insumos') y sus columnas con tipos de datos para poblar el selector dinámico del frontend."
)
async def obtener_esquemas_tablas(
    usuario: UsuarioAutenticado = Depends(validar_operador_guard)
):
    logger.info(f"[Reportes Dinámicos] Consulta de esquemas autorizada para {usuario.email} ({usuario.rol})")
    return reports_service_default.obtener_esquemas_tablas()


@reports_router.post(
    "/generar-dinamico",
    response_model=ReporteDinamicoRespuestaDTO,
    summary="Generar reporte dinámico a partir de prompt, texto o parámetros estructurados",
    description="Permite especificar fuente de datos, columnas deseadas, criterios de selección y formato (PDF, Excel o Ambos), ya sea estructuradamente o interpretado de un prompt."
)
async def generar_reporte_dinamico(
    payload: ReporteDinamicoRequest,
    usuario: UsuarioAutenticado = Depends(validar_operador_guard)
):
    logger.info(f"[Reportes Dinámicos] Solicitud autorizada para {usuario.email} ({usuario.rol}) | Fuente: {payload.fuente_datos}")
    try:
        respuesta = await reports_service_default.procesar_reporte_dinamico(payload)
        return respuesta
    except ValueError as e:
        logger.warning(f"[Reportes Dinámicos] Validación / Seguridad AST rechazada: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generando reporte dinámico: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error durante la generación del reporte dinámico: {str(e)}"
        )


@reports_router.post(
    "/generar-dinamico-voz",
    response_model=ReporteDinamicoRespuestaDTO,
    summary="Generar reporte dinámico a partir de nota de voz",
    description="Transcribe con Faster-Whisper la nota de voz del comandante, extrae inteligentemente fuente, columnas, criterios y formato, y compila los artefactos multimodales."
)
async def generar_reporte_dinamico_voz(
    archivo_audio: UploadFile = File(..., description="Nota de voz del comandante (WAV, MP3, OGG, WebM)"),
    voz_tts: str = Query("es-BO-MarceloNeural", description="Voz neural Edge-TTS para el briefing radial"),
    usuario: UsuarioAutenticado = Depends(validar_operador_guard)
):
    logger.info(f"[Reportes Dinámicos Voz] Solicitud autorizada para {usuario.email} ({usuario.rol})")
    filename = archivo_audio.filename or "audio.wav"
    ext = filename.split(".")[-1].lower() if "." in filename else "wav"
    if ext not in EXTENSIONES_AUDIO_VALIDAS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Extensión de audio '{ext}' no soportada. Permitidas: {', '.join(EXTENSIONES_AUDIO_VALIDAS)}"
        )

    try:
        contenido_audio = await archivo_audio.read()
        if len(contenido_audio) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El archivo de audio recibido está vacío."
            )
        if len(contenido_audio) > MAX_AUDIO_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="El archivo de audio excede los 25 MB permitidos."
            )

        respuesta = await reports_service_default.procesar_reporte_dinamico_voz(
            audio_bytes=contenido_audio,
            extension=ext,
            voz_tts=voz_tts
        )
        return respuesta
    except ValueError as e:
        logger.warning(f"[Reportes Dinámicos Voz] Validación / Seguridad AST rechazada: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generando reporte dinámico por voz: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error durante el procesamiento del reporte dinámico por voz: {str(e)}"
        )


@reports_router.post(
    "/generar-por-voz",
    response_model=ReporteRespuestaDTO,
    summary="Generar reporte táctico multimodal desde archivo de audio",
    description="Transcribe la nota de voz del comandante con Faster-Whisper, aplica RAG Grounding determinista y compila PDF, Excel, Audio y Markdown."
)
async def generar_reporte_por_voz(
    archivo_audio: UploadFile = File(..., description="Nota de voz o mensaje radial (WAV, MP3, OGG, WebM)"),
    generar_multimodal: bool = Query(True, description="Si es True, compila PDF WeasyPrint, Excel y Audio Edge-TTS"),
    voz_tts: str = Query("es-BO-MarceloNeural", description="Voz neural Edge-TTS para el briefing radial (ej. es-BO-MarceloNeural, es-BO-SofiaNeural)"),
    usuario: UsuarioAutenticado = Depends(validar_operador_guard)
):
    logger.info(f"[Voice-to-Report] Solicitud autorizada para {usuario.email} ({usuario.rol})")
    # Validar extensión del archivo
    filename = archivo_audio.filename or "audio.wav"
    ext = filename.split(".")[-1].lower() if "." in filename else "wav"
    if ext not in EXTENSIONES_AUDIO_VALIDAS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Extensión de audio '{ext}' no soportada. Permitidas: {', '.join(EXTENSIONES_AUDIO_VALIDAS)}"
        )

    try:
        contenido_audio = await archivo_audio.read()
        if len(contenido_audio) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El archivo de audio recibido está vacío."
            )
        if len(contenido_audio) > MAX_AUDIO_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="El archivo de audio excede los 25 MB permitidos."
            )

        respuesta = await reports_service_default.procesar_comando_voz(
            audio_bytes=contenido_audio,
            extension=ext,
            generar_multimodal=generar_multimodal,
            voz_tts=voz_tts
        )
        return respuesta

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error durante el procesamiento del pipeline Voice-to-Report: {str(e)}"
        )


@reports_router.post(
    "/generar-por-texto",
    response_model=ReporteRespuestaDTO,
    summary="Generar reporte táctico multimodal a partir de comando en texto",
    description="Acepta instrucciones en lenguaje natural emitidas por consola o sala de crisis, ejecutando RAG Grounding y compilación multimodal."
)
async def generar_reporte_por_texto(
    payload: GenerarReporteTextoRequest,
    usuario: UsuarioAutenticado = Depends(validar_operador_guard)
):
    logger.info(f"[Text-to-Report] Solicitud autorizada para {usuario.email} ({usuario.rol})")
    if not payload.instruccion or not payload.instruccion.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La instrucción o requerimiento de reporte no puede estar vacía."
        )

    try:
        respuesta = await reports_service_default.procesar_comando_texto(
            instruccion=payload.instruccion.strip(),
            generar_multimodal=payload.generar_multimodal,
            voz_tts=payload.voz_tts
        )
        return respuesta
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error durante la generación del reporte: {str(e)}"
        )


@reports_router.get(
    "/descargar/pdf/{id_reporte}",
    summary="Descargar reporte en formato PDF de alta fidelidad",
    response_description="Documento PDF compilado con WeasyPrint y CSS Paged Media"
)
async def descargar_pdf(id_reporte: str):
    ruta = reports_service_default.obtener_ruta_artefacto(id_reporte, "pdf")
    if not ruta or not os.path.exists(ruta):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El PDF del reporte '{id_reporte}' no existe o no fue generado."
        )
    return FileResponse(
        path=ruta,
        media_type="application/pdf",
        filename=f"Reporte_Bomberos_{id_reporte}.pdf"
    )


@reports_router.get(
    "/descargar/excel/{id_reporte}",
    summary="Descargar reporte en formato Excel (XLSX)",
    response_description="Hoja de cálculo OpenPyXL con estilos editoriales y fórmulas de autosuma"
)
async def descargar_excel(id_reporte: str):
    ruta = reports_service_default.obtener_ruta_artefacto(id_reporte, "excel")
    if not ruta or not os.path.exists(ruta):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"La hoja de cálculo Excel del reporte '{id_reporte}' no existe o no fue generada."
        )
    return FileResponse(
        path=ruta,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"Reporte_Bomberos_{id_reporte}.xlsx"
    )


@reports_router.get(
    "/reproducir/audio/{id_reporte}",
    summary="Reproducir o descargar briefing en audio MP3",
    response_description="Audio neural sintetizado con Edge-TTS para lectura en radiocomunicación"
)
async def reproducir_audio(id_reporte: str):
    ruta = reports_service_default.obtener_ruta_artefacto(id_reporte, "audio")
    if not ruta or not os.path.exists(ruta):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El briefing en audio del reporte '{id_reporte}' no existe o no fue sintetizado."
        )
    return FileResponse(
        path=ruta,
        media_type="audio/mpeg",
        filename=f"Briefing_Radial_{id_reporte}.mp3"
    )


@reports_router.get(
    "/{id_reporte}",
    summary="Obtener reporte completo en Markdown y metadatos",
    response_description="Estructura Markdown enriquecida del informe táctico"
)
async def obtener_reporte_markdown(id_reporte: str):
    contenido = reports_service_default.obtener_contenido_markdown(id_reporte)
    if not contenido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El reporte con identificador '{id_reporte}' no fue encontrado."
        )
    return {
        "id_reporte": id_reporte,
        "markdown": contenido,
        "descargas": {
            "pdf": f"/api/v1/reportes/descargar/pdf/{id_reporte}",
            "excel": f"/api/v1/reportes/descargar/excel/{id_reporte}",
            "audio": f"/api/v1/reportes/reproducir/audio/{id_reporte}"
        }
    }
