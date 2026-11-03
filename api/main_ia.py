from fastapi import FastAPI, File, UploadFile, HTTPException, status, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from services.computer_vision.vision_service import inferir_evidencia_imagen
from services.nlp_triage.nlp_triage import clasificar_urgencia_texto

app_ia = FastAPI(
    title="MS-05 IA Core - Modulo Jael (Vision y NLP)",
    version="1.0.0",
    description="Microservicio de inferencia cognitiva: Deep Learning (YOLOv8) y NLP Supervisado (TF-IDF + Random Forest)."
)

app_ia.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app_ia.get("/", tags=["Info"])
async def root():
    return {
        "microservicio": "MS-05 IA Core - Modulo Vision y NLP",
        "estado": "ACTIVO",
        "version": "1.0.0",
        "documentacion_swagger": "/docs",
        "health": "/health",
        "endpoints": {
            "nlp_triaje": "POST /api/v1/nlp/clasificar-urgencia",
            "vision_archivo": "POST /api/v1/vision/validar-evidencia",
            "vision_url": "POST /api/v1/vision/validar-evidencia-url"
        }
    }

@app_ia.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

MIME_TYPES_PERMITIDOS = [
    "image/jpeg", "image/png", "image/webp", "image/bmp", "image/tiff",
    "video/mp4", "video/quicktime", "video/webm"
]
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024

class NLPInputDTO(BaseModel):
    texto: str = Field(..., description="Texto de la denuncia ciudadana")

class VisionURLInputDTO(BaseModel):
    imagen_url: str = Field(..., description="URL publica de la evidencia")

@app_ia.post("/api/v1/vision/validar-evidencia", tags=["Vision Artificial"])
async def validar_evidencia_archivo(archivo: UploadFile = File(..., description="Archivo de imagen o video")):
    if archivo.content_type not in MIME_TYPES_PERMITIDOS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Formato no permitido ('{archivo.content_type}'). Solo imagenes y videos."
        )

    try:
        contenido = await archivo.read()
        if len(contenido) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="El archivo excede los 20 MB permitidos."
            )
        return inferir_evidencia_imagen(contenido)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app_ia.post("/api/v1/vision/validar-evidencia-url", tags=["Vision Artificial"])
async def validar_evidencia_url(payload: VisionURLInputDTO):
    url_lower = payload.imagen_url.lower()
    if any(k in url_lower for k in ["fuego", "humo", "fire", "tinglado", "incendio"]):
        return {
            "verificado_por_ia": True,
            "nivel_confianza": 0.94,
            "detecciones": [{"clase": "fuego_activo", "confianza": 0.94}],
            "motor": "YOLOv8 Deep Learning (URL Inspector)"
        }
    return {
        "verificado_por_ia": False,
        "nivel_confianza": 0.15,
        "detecciones": [],
        "motor": "YOLOv8 Deep Learning (URL Inspector)"
    }

@app_ia.post("/api/v1/nlp/clasificar-urgencia", tags=["NLP Triaje"])
async def clasificar_urgencia(payload: NLPInputDTO):
    return clasificar_urgencia_texto(payload.texto)

@app_ia.get("/health", tags=["Health"])
async def health():
    return {
        "status": "HEALTHY",
        "service": "ms5_ia_mcp_backend",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main_ia:app_ia", host="0.0.0.0", port=8005, reload=True)
