"""
Servicio de Clasificación NLP para Triaje de Emergencias.
Modelo supervisado TF-IDF + Random Forest.
"""

from typing import Dict, Any, List
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier

# Dataset sintético de entrenamiento con el lenguaje ubicuo bomberil
DATOS_ENTRENAMIENTO = [
    # CRITICO_ESTRUCTURAL
    ("fuego en fabrica de plasticos sale mucho humo negro y llamas altas", "CRITICO_ESTRUCTURAL"),
    ("tinglado en llamas en parque industrial peligro de propagacion", "CRITICO_ESTRUCTURAL"),
    ("incendio en vivienda de dos pisos personas en el techo pidiendo auxilio", "CRITICO_ESTRUCTURAL"),
    ("deposito ardiendo con fuego violento en el centro", "CRITICO_ESTRUCTURAL"),
    ("fuego en habitacion se estan quemando colchones y muebles", "CRITICO_ESTRUCTURAL"),

    # ALTO_FORESTAL
    ("quema descontrolada de pastizales en cordon ecologico rio pirai", "ALTO_FORESTAL"),
    ("chaqueo fuera de control cerca de la carretera a cotoca humo denso", "ALTO_FORESTAL"),
    ("fuego en lote baldio con pasto seco y viento fuerte avanzando a casas", "ALTO_FORESTAL"),
    ("incendio forestal consumiendo arboles en zona norte", "ALTO_FORESTAL"),

    # CRITICO_ELECTRICO
    ("chispas y corto circuito en transformador de poste de luz", "CRITICO_ELECTRICO"),
    ("cables de alta tension caidos en la calle botando chispas y fuego", "CRITICO_ELECTRICO"),
    ("explosion en tablero electrico principal de edificio residencial", "CRITICO_ELECTRICO"),

    # CRITICO_GAS
    ("fuga de gas licuado en garrafa de cocina olor insoportable", "CRITICO_GAS"),
    ("garrafa con fuego en la valvula dentro de restaurante", "CRITICO_GAS"),
    ("rotura de caneria de gas domiciliario silbido fuerte en la acera", "CRITICO_GAS"),

    # ALTO_VEHICULAR
    ("accidente vehicular camion choco contra poste chofer atrapado", "ALTO_VEHICULAR"),
    ("choque frontal de dos micros con heridos en avenida cristo redentor", "ALTO_VEHICULAR"),
    ("vuelco de cisterna de combustible con derrame en carretera", "ALTO_VEHICULAR"),

    # BAJO_AUXILIO
    ("gatito atrapado en la copa de un arbol alto", "BAJO_AUXILIO"),
    ("enjambre de abejas agresivas en la plaza del barrio", "BAJO_AUXILIO"),
    ("puerta trancada con candado en departamento sin personas en riesgo", "BAJO_AUXILIO")
]

class NLPEmergencyClassifier:
    def __init__(self):
        self.textos = [x[0] for x in DATOS_ENTRENAMIENTO]
        self.etiquetas = [x[1] for x in DATOS_ENTRENAMIENTO]
        
        # Vectorizador TF-IDF con n-gramas
        self.vectorizador = TfidfVectorizer(ngram_range=(1, 2), lowercase=True)
        X = self.vectorizador.fit_transform(self.textos)
        
        # Clasificador Random Forest supervisado
        self.clasificador = RandomForestClassifier(n_estimators=30, random_state=42)
        self.clasificador.fit(X, self.etiquetas)

    def clasificar(self, mensaje: str) -> Dict[str, Any]:
        if not mensaje or not mensaje.strip():
            return {
                "categoria_predicha": "PENDIENTE_TRIAJE",
                "severidad": "MEDIA",
                "confianza": 0.50,
                "palabras_clave": []
            }

        X_test = self.vectorizador.transform([mensaje])
        prediccion = self.clasificador.predict(X_test)[0]
        probabilidades = self.clasificador.predict_proba(X_test)[0]
        confianza = max(probabilidades)

        # Mapeo de severidad
        severidad = "ALTA"
        if prediccion.startswith("CRITICO"):
            severidad = "CRITICA"
        elif prediccion.startswith("ALTO"):
            severidad = "ALTA"
        elif prediccion.startswith("BAJO"):
            severidad = "BAJA"

        # Extraer palabras clave coincidentes
        palabras_mensaje = set(mensaje.lower().split())
        vocabulario = set(self.vectorizador.get_feature_names_out())
        coincidencias = list(palabras_mensaje.intersection(vocabulario))

        return {
            "categoria_predicha": prediccion,
            "severidad": severidad,
            "confianza": round(float(confianza), 3),
            "palabras_clave": coincidencias[:5]
        }

# Instancia singleton para reutilizar el modelo entrenado
clasificador_global = NLPEmergencyClassifier()

def clasificar_urgencia_texto(mensaje: str) -> Dict[str, Any]:
    return clasificador_global.clasificar(mensaje)
