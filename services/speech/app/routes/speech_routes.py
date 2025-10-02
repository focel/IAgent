from fastapi import APIRouter, BackgroundTasks
from datetime import datetime
from app.services.speech_service import speech_service

router = APIRouter()

@router.post("/process")
async def process_text_endpoint(request: dict):
    """
    Endpoint de ejemplo para procesar texto.
    
    Args:
        request: Diccionario con el texto a procesar
        
    Returns:
        Resultado del procesamiento
    """
    text = request.get("text", "")
    if not text:
        return {"error": "No se proporcionó texto para procesar"}
    
    return await speech_service.process_text(text)

@router.get("/")
async def root():
    """
    Endpoint raíz del servicio Speech.
    
    Returns:
        Información básica del servicio
    """
    return {
        "service": "Speech Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "process": "/process (POST)",
            "root": "/"
        },
        "timestamp": datetime.now().isoformat()
    }
    
@router.post("/offer")
async def offer(request: dict, background_tasks: BackgroundTasks):
    """
    Endpoint para manejar ofertas SDP.
    
    Args:
        request: Diccionario con la oferta SDP y opcionalmente interview_id
        background_tasks: Tareas en segundo plano
        
    Returns:
        Respuesta SDP
    """
    pc_id = request.get("pc_id", "")
    sdp = request.get("sdp", "")
    type = request.get("type", "")
    interview_id = request.get("interview_id")

    return await speech_service.offer(pc_id, sdp, type, interview_id, background_tasks)