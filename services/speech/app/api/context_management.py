"""
Context Management API Router
Maneja el contexto de conversación y estado de la aplicación
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/context", tags=["context"])

# Almacenamiento temporal del contexto (en producción usar base de datos)
context_store: Dict[str, Any] = {}

@router.get("/health")
async def health_check():
    """Verificar el estado del servicio de contexto"""
    return {"status": "ok", "service": "context_management"}

@router.get("/{session_id}")
async def get_context(session_id: str):
    """Obtener el contexto de una sesión específica"""
    try:
        context = context_store.get(session_id, {})
        return {"session_id": session_id, "context": context}
    except Exception as e:
        logger.error(f"Error obteniendo contexto para sesión {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/{session_id}")
async def update_context(session_id: str, context_data: Dict[str, Any]):
    """Actualizar el contexto de una sesión específica"""
    try:
        if session_id not in context_store:
            context_store[session_id] = {}
        
        context_store[session_id].update(context_data)
        
        return {
            "session_id": session_id, 
            "message": "Contexto actualizado exitosamente",
            "context": context_store[session_id]
        }
    except Exception as e:
        logger.error(f"Error actualizando contexto para sesión {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.delete("/{session_id}")
async def clear_context(session_id: str):
    """Limpiar el contexto de una sesión específica"""
    try:
        if session_id in context_store:
            del context_store[session_id]
            return {"session_id": session_id, "message": "Contexto eliminado exitosamente"}
        else:
            raise HTTPException(status_code=404, detail="Sesión no encontrada")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando contexto para sesión {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")