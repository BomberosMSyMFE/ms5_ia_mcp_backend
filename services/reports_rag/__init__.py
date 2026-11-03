"""
services/reports_rag/__init__.py
Módulo de Reportes Multimodales y RAG Grounding por Voz.
Semestre 2/2026 - INF512 (Ingeniería de Software II)
Responsable: Nataly Martínez (ms5_ia_mcp_backend)
"""

from .whisper_service import WhisperService, whisper_service_default
from .rag_engine import RAGEngine, rag_engine_default, ReporteParametros, ReporteMetricasCalculadas
from .multimodal_generator import MultimodalGenerator, multimodal_generator_default
from .reports_service import ReportsService, reports_service_default, ReporteRespuestaDTO, GenerarReporteTextoRequest

__all__ = [
    "WhisperService",
    "whisper_service_default",
    "RAGEngine",
    "rag_engine_default",
    "ReporteParametros",
    "ReporteMetricasCalculadas",
    "MultimodalGenerator",
    "multimodal_generator_default",
    "ReportsService",
    "reports_service_default",
    "ReporteRespuestaDTO",
    "GenerarReporteTextoRequest"
]
