"""
services/predictive_maintenance/maintenance_model.py
Modelo de Machine Learning Supervisado para Mantenimiento Predictivo de Equipos Bomberiles.
Cumple rigurosamente con:
- PUNTO_06_MACHINE_LEARNING_DEEP_LEARNING.md (Sección 3.2 - Mantenimiento Predictivo)
- Algoritmos: Ensemble de Random Forest Classifier (clasificación de estado) y
              Random Forest Regressor (predicción de días de vida útil restantes).
Responsable: Jael Mamani (ms5_ia_mcp_backend)
"""

from typing import List, Dict, Any, Optional
import numpy as np
from pydantic import BaseModel, Field
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor


# =========================================================================
# DTOs DE ENTRADA Y SALIDA (PYDANTIC SCHEMAS)
# =========================================================================

class EquipoTelemetriaDTO(BaseModel):
    codigo: str = Field(..., description="Código de inventario del equipo (ej. 'MOTO-HONDA-01')")
    nombre: str = Field(..., description="Nombre descriptivo del equipo")
    tipo_equipo: str = Field(
        "MOTOBOMBA",
        description="Categoría: MOTOBOMBA, MANGUERA_ALTA_PRESION, COMPRESOR_OXIGENO, CORTADORA_HIDRAULICA, GENERADOR"
    )
    horas_uso_acumuladas: float = Field(..., ge=0, description="Horas de bombeo u operación acumuladas")
    umbral_fatiga_horas: float = Field(..., gt=0, description="Umbral máximo de diseño del fabricante en horas")
    dias_desde_inspeccion: int = Field(30, ge=0, description="Días transcurridos desde el último mantenimiento preventivo")
    caudal_maximo_lpm: Optional[float] = Field(1500.0, description="Caudal máximo soportado en litros por minuto")
    historial_presiones_altas: int = Field(0, ge=0, description="Eventos de golpe de ariete o sobrepresión registrados")
    incidentes_atendidos: int = Field(5, ge=0, description="Cantidad total de incendios o siniestros atendidos")


class PrediccionMantenimientoDTO(BaseModel):
    codigo: str
    nombre: str
    tipo_equipo: str
    horas_uso_acumuladas: float
    umbral_fatiga_horas: float
    porcentaje_fatiga: float
    estado_recomendado: str  # OPERATIVO, REQUERIR_MANTENIMIENTO_PREVENTIVO, DESCARTE_INMEDIATO
    riesgo_fallo_porcentaje: float
    dias_vida_util_restantes: float
    requiere_retiro_inmediato: bool
    accion_recomendada: str
    modelo_ia: str
    confianza: float


# =========================================================================
# DATASET SINTÉTICO BASADO EN FÍSICA Y OPERATIVA BOMBERIL (45 REGISTROS)
# =========================================================================
# Formato: [horas_uso, umbral, dias_insp, caudal_max, sobrepresiones, incidentes]
# Target_Cat: 0: OPERATIVO, 1: REQUERIR_MANTENIMIENTO_PREVENTIVO, 2: DESCARTE_INMEDIATO
# Target_Reg: Días de vida útil restantes estimados

DATOS_ENTRENAMIENTO_X = [
    # Equipos Nuevos / Óptimos (OPERATIVO)
    [10.0, 150.0, 5, 1500.0, 0, 1],
    [25.0, 150.0, 12, 1500.0, 0, 3],
    [40.0, 200.0, 20, 2200.0, 0, 4],
    [30.0, 120.0, 15, 800.0, 0, 2],
    [50.0, 180.0, 25, 1600.0, 1, 6],
    [15.0, 100.0, 10, 600.0, 0, 1],
    [60.0, 200.0, 30, 2000.0, 1, 7],
    [45.0, 150.0, 18, 1400.0, 0, 5],
    [70.0, 250.0, 35, 2500.0, 1, 8],
    [35.0, 150.0, 14, 1500.0, 0, 4],

    # Equipos en Zona de Fatiga Media (OPERATIVO en observación)
    [85.0, 150.0, 45, 1500.0, 1, 10],
    [95.0, 150.0, 50, 1500.0, 2, 12],
    [110.0, 180.0, 55, 1800.0, 2, 13],
    [115.0, 200.0, 60, 2200.0, 2, 14],
    [90.0, 160.0, 40, 1500.0, 1, 11],

    # Equipos que Superan Umbral (REQUERIR_MANTENIMIENTO_PREVENTIVO)
    [145.0, 150.0, 80, 1500.0, 3, 18],
    [152.0, 150.0, 85, 1500.0, 4, 19],
    [160.0, 150.0, 90, 1400.0, 3, 20],
    [195.0, 200.0, 100, 2100.0, 4, 24],
    [205.0, 200.0, 110, 2000.0, 5, 25],
    [125.0, 120.0, 75, 800.0, 3, 16],
    [130.0, 120.0, 80, 800.0, 4, 17],
    [175.0, 180.0, 95, 1700.0, 4, 21],
    [185.0, 180.0, 105, 1600.0, 5, 22],
    [140.0, 140.0, 70, 1200.0, 3, 17],

    # Equipos Severamente Fatigados / Historial de Sobrepresión (MANTENIMIENTO CRÍTICO)
    [170.0, 150.0, 120, 1500.0, 6, 23],
    [180.0, 150.0, 130, 1400.0, 7, 25],
    [220.0, 200.0, 140, 2000.0, 6, 28],
    [145.0, 120.0, 115, 800.0, 5, 20],
    [210.0, 180.0, 125, 1500.0, 6, 27],

    # Equipos Dañados / Peligro Inminente (DESCARTE_INMEDIATO)
    [210.0, 150.0, 180, 1300.0, 10, 32],
    [230.0, 150.0, 200, 1200.0, 12, 35],
    [270.0, 200.0, 210, 1800.0, 11, 40],
    [170.0, 100.0, 190, 500.0, 9, 28],
    [250.0, 160.0, 220, 1400.0, 13, 38],
    [280.0, 180.0, 240, 1500.0, 14, 42],
    [300.0, 200.0, 250, 1700.0, 15, 45],
    [190.0, 120.0, 185, 700.0, 10, 30],
    [240.0, 150.0, 215, 1200.0, 12, 36],
    [260.0, 170.0, 230, 1400.0, 11, 39],
]

# 0: OPERATIVO, 1: REQUERIR_MANTENIMIENTO_PREVENTIVO, 2: DESCARTE_INMEDIATO
DATOS_ENTRENAMIENTO_Y_CAT = [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2
]

# Días de vida útil restantes antes de fallo catastrófico
DATOS_ENTRENAMIENTO_Y_REG = [
    320.0, 290.0, 260.0, 240.0, 220.0, 280.0, 210.0, 230.0, 270.0, 250.0,
    180.0, 160.0, 140.0, 135.0, 170.0,
    45.0, 35.0, 25.0, 30.0, 20.0, 40.0, 30.0, 28.0, 18.0, 32.0,
    15.0, 12.0, 14.0, 10.0, 11.0,
    3.0, 1.0, 0.0, 2.0, 1.0, 0.0, 0.0, 2.0, 1.0, 0.0
]


# =========================================================================
# CLASE PRINCIPAL: PREDICTIVE MAINTENANCE MODEL (ENSEMBLE SCIKIT-LEARN)
# =========================================================================

class PredictiveMaintenanceModel:
    """
    Motor supervisado de Machine Learning:
    - Entrena un Random Forest Classifier (clasificación de condición de combate).
    - Entrena un Random Forest Regressor (estimación cuantitativa de vida útil restante).
    """

    CATEGORIAS = {
        0: "OPERATIVO",
        1: "REQUERIR_MANTENIMIENTO_PREVENTIVO",
        2: "DESCARTE_INMEDIATO"
    }

    def __init__(self):
        self.X_train = np.array(DATOS_ENTRENAMIENTO_X)
        self.y_cat = np.array(DATOS_ENTRENAMIENTO_Y_CAT)
        self.y_reg = np.array(DATOS_ENTRENAMIENTO_Y_REG)

        # 1. Clasificador Supervisado Random Forest
        self.clasificador = RandomForestClassifier(
            n_estimators=40,
            max_depth=6,
            random_state=42
        )
        self.clasificador.fit(self.X_train, self.y_cat)

        # 2. Regresor Supervisado Random Forest
        self.regresor = RandomForestRegressor(
            n_estimators=40,
            max_depth=6,
            random_state=42
        )
        self.regresor.fit(self.X_train, self.y_reg)

    def predecir(self, equipo: EquipoTelemetriaDTO) -> PrediccionMantenimientoDTO:
        """
        Ejecuta la inferencia analítica para un equipo bomberil individual.
        """
        # Vector de características
        vector = np.array([[
            float(equipo.horas_uso_acumuladas),
            float(equipo.umbral_fatiga_horas),
            float(equipo.dias_desde_inspeccion),
            float(equipo.caudal_maximo_lpm or 1500.0),
            float(equipo.historial_presiones_altas),
            float(equipo.incidentes_atendidos),
        ]])

        # Inferencia de clasificación
        clase_idx = int(self.clasificador.predict(vector)[0])
        probabilidades = self.clasificador.predict_proba(vector)[0]
        confianza = float(np.max(probabilidades))

        estado_predicho = self.CATEGORIAS.get(clase_idx, "REQUERIR_MANTENIMIENTO_PREVENTIVO")

        # Inferencia de regresión (días vida útil)
        dias_estimados = float(self.regresor.predict(vector)[0])
        dias_estimados = max(0.0, round(dias_estimados, 1))

        # Cálculo de riesgo porcentual y fatiga
        porcentaje_fatiga = round((equipo.horas_uso_acumuladas / equipo.umbral_fatiga_horas) * 100.0, 1)

        # Probabilidad de requerir mantenimiento o descarte (clases 1 y 2)
        prob_riesgo = float(probabilidades[1] + (probabilidades[2] * 1.5 if len(probabilidades) > 2 else 0.0))
        riesgo_fallo = min(100.0, round(max(prob_riesgo * 100.0, porcentaje_fatiga * 0.8), 1))

        # Recomendaciones de acción según el protocolo de la central
        if estado_predicho == "DESCARTE_INMEDIATO" or porcentaje_fatiga >= 130.0:
            estado_predicho = "DESCARTE_INMEDIATO"
            requiere_retiro = True
            accion = (
                f"PELIGRO ESTRUCTURAL: El equipo {equipo.codigo} ({equipo.nombre}) superó en {porcentaje_fatiga}% "
                f"su fatiga admisible con {equipo.historial_presiones_altas} sobrepresiones. "
                f"Retiro definitivo del servicio y destrucción controlada para evitar accidentes en combate."
            )
        elif estado_predicho == "REQUERIR_MANTENIMIENTO_PREVENTIVO" or equipo.horas_uso_acumuladas >= equipo.umbral_fatiga_horas:
            estado_predicho = "REQUERIR_MANTENIMIENTO_PREVENTIVO"
            requiere_retiro = True
            accion = (
                f"DERIVACIÓN A TALLER: El equipo {equipo.codigo} ({equipo.nombre}) acumuló {equipo.horas_uso_acumuladas}h "
                f"de uso (Umbral: {equipo.umbral_fatiga_horas}h). Vida útil estimada restante: {dias_estimados} días. "
                f"Enviar a inspección hidráulica, cambio de sellos y prueba de carga antes del siguiente despacho."
            )
        else:
            requiere_retiro = False
            accion = (
                f"EQUIPO APTO: {equipo.codigo} ({equipo.nombre}) en condiciones operativas óptimas "
                f"({porcentaje_fatiga}% de fatiga acumulada). Habilitado para respuesta inmediata."
            )

        return PrediccionMantenimientoDTO(
            codigo=equipo.codigo,
            nombre=equipo.nombre,
            tipo_equipo=equipo.tipo_equipo,
            horas_uso_acumuladas=equipo.horas_uso_acumuladas,
            umbral_fatiga_horas=equipo.umbral_fatiga_horas,
            porcentaje_fatiga=porcentaje_fatiga,
            estado_recomendado=estado_predicho,
            riesgo_fallo_porcentaje=riesgo_fallo,
            dias_vida_util_restantes=dias_estimados,
            requiere_retiro_inmediato=requiere_retiro,
            accion_recomendada=accion,
            modelo_ia="Random Forest Regressor & Classifier Ensemble (Scikit-Learn INF512)",
            confianza=round(confianza, 3)
        )


# Singleton del modelo entrenado
maintenance_predictor_default = PredictiveMaintenanceModel()


def predecir_mantenimiento_equipo(equipo: EquipoTelemetriaDTO) -> PrediccionMantenimientoDTO:
    return maintenance_predictor_default.predecir(equipo)


def auditar_lote_equipos(equipos: List[EquipoTelemetriaDTO]) -> List[PrediccionMantenimientoDTO]:
    return [maintenance_predictor_default.predecir(e) for e in equipos]


def obtener_umbrales_referencia() -> Dict[str, Any]:
    """Retorna los estándares de ingeniería bomberil para umbrales de fatiga."""
    return {
        "normativa": "NFPA 1911 / 1962 - Inspección y Mantenimiento de Equipos Bomberiles",
        "umbrales_recomendados_horas": {
            "MOTOBOMBA": 150.0,
            "MANGUERA_ALTA_PRESION": 200.0,
            "COMPRESOR_OXIGENO": 120.0,
            "CORTADORA_HIDRAULICA": 100.0,
            "GENERADOR_ELECTRICO": 180.0
        },
        "max_dias_sin_inspeccion": 90,
        "max_sobrepresiones_toleradas": 3
    }
