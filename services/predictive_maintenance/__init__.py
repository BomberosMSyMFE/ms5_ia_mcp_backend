"""
services/predictive_maintenance/__init__.py
Módulo de Mantenimiento Predictivo con Machine Learning para Equipos Bomberiles.
Cumple con PUNTO_06 (Machine Learning Supervisado - Sección 3.2).
Responsable: Jael Mamani (en colaboración con el equipo de Bomberos).
"""

from .maintenance_model import (
    EquipoTelemetriaDTO,
    PrediccionMantenimientoDTO,
    PredictiveMaintenanceModel,
    predecir_mantenimiento_equipo,
    auditar_lote_equipos,
    obtener_umbrales_referencia,
)

__all__ = [
    "EquipoTelemetriaDTO",
    "PrediccionMantenimientoDTO",
    "PredictiveMaintenanceModel",
    "predecir_mantenimiento_equipo",
    "auditar_lote_equipos",
    "obtener_umbrales_referencia",
]
