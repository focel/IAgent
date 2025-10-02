#!/usr/bin/env python3
"""
Servicio de Speech - Lógica de negocio

Este módulo contiene la lógica principal para el procesamiento de voz y texto.
Recibe transmisiones del orchestrator via gRPC, guarda contenido localmente
y reenvía respuestas procesadas sin latencia adicional.
"""

import asyncio
import json
import logging
import os
from .pipecat_service import run_bot
from typing import Dict, Any, Optional
from aiortc.contrib.media import MediaRelay, MediaRecorder
from pipecat.transports.smallwebrtc.connection import IceServer, SmallWebRTCConnection
from fastapi import BackgroundTasks

logger = logging.getLogger(__name__)

# Definir la ruta para la carpeta storage
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage")

# Crear la carpeta storage si no existe
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Mapa global para almacenar conexiones WebRTC activas
pcs_map = {}

class SpeechService:
    """
    Servicio principal para procesamiento de speech.
    
    Maneja procesamiento de voz y texto a través de API REST.
    """
    
    def __init__(self):
        """Inicializar el servicio de speech"""
        self.service_name = "Speech Service"
        self.version = "1.0.0"
        self.active_sessions = {}
        self.active_connections = {}
        self.media_relay = MediaRelay()
        
        logger.info(f"Inicializando {self.service_name} v{self.version}")
        logger.info("Servicio configurado para procesamiento de voz y texto via API REST")
    
    async def get_service_info(self) -> Dict[str, Any]:
        """
        Obtener información del servicio.
        
        Returns:
            Dict con información del servicio
        """
        logger.info("Obteniendo información del servicio")
        
        return {
            "service": self.service_name,
            "version": self.version,
            "status": "active",
            "capabilities": [
                "rest-api",
                "audio-processing",
                "text-processing",
                "file-storage",
                "real-time-response"
            ],
            "endpoints": {
                "health": "/health",
                "status": "/status",
                "root": "/"
            },
            "active_sessions": len(self.active_sessions),
            "storage_location": "media_storage/"
        }
    
    async def offer(self, pc_id, sdp, type, interview_id, background_tasks: BackgroundTasks):
        # Configurar servidores ICE optimizados para conexión rápida
        # Incluye servidores STUN y TURN para mejor conectividad en redes restrictivas
        ice_servers = [
            # Servidores STUN principales (más rápidos primero)
            IceServer(urls=["stun:stun.cloudflare.com:3478"]),
            IceServer(urls=["stun:stun.l.google.com:19302"]),
            # Servidores TURN gratuitos para redes con NAT restrictivo
            IceServer(
                urls=["turn:openrelay.metered.ca:80"],
                username="openrelayproject",
                credential="openrelayproject"
            ),
            IceServer(
                urls=["turn:openrelay.metered.ca:443"],
                username="openrelayproject",
                credential="openrelayproject"
            ),
            # Servidores STUN adicionales como respaldo
            IceServer(urls=["stun:stun1.l.google.com:19302"]),
            IceServer(urls=["stun:stun2.l.google.com:19302"])
        ]
        
        import time
        start_time = time.time()
        
        try:
            if pc_id and pc_id in pcs_map:
                pipecat_connection = pcs_map[pc_id]
                logger.info(f"Reusing existing connection for pc_id: {pc_id}")
                renegotiate_start = time.time()
                await pipecat_connection.renegotiate(sdp, type)
                logger.info(f"⏱️ Renegotiation completed in {(time.time() - renegotiate_start):.3f}s")
            else:
                logger.info(f"🚀 Creating new WebRTC connection for interview_id: {interview_id}")
                connection_start = time.time()
                pipecat_connection = SmallWebRTCConnection(ice_servers)
                logger.info(f"⏱️ SmallWebRTCConnection created in {(time.time() - connection_start):.3f}s")
                
                init_start = time.time()
                await pipecat_connection.initialize(sdp, type)
                logger.info(f"⏱️ Connection initialization completed in {(time.time() - init_start):.3f}s")

                @pipecat_connection.event_handler("closed")
                async def handle_disconnected(webrtc_connection: SmallWebRTCConnection):
                    logger.info(f"Discarding peer connection for pc_id: {webrtc_connection.pc_id}")
                    pcs_map.pop(webrtc_connection.pc_id, None)

                print(f"📋 Añadiendo tarea run_bot para interview_id: {interview_id}", flush=True)
                logger.info(f"📋 Añadiendo tarea run_bot para interview_id: {interview_id}")
                
                # Crear RunnerArguments con timeout reducido para evitar cierre prematuro
                from pipecat.runner.types import RunnerArguments
                runner_args = RunnerArguments()
                runner_args.pipeline_idle_timeout_secs = 30  # Reducir a 30 segundos en lugar de 300
                
                # Pasar parámetros personalizados como argumentos adicionales
                background_tasks.add_task(run_bot, pipecat_connection, runner_args, interview_id, "Software Engineer")
                print(f"✅ Tarea run_bot añadida exitosamente para interview_id: {interview_id}", flush=True)
                logger.info(f"✅ Tarea run_bot añadida exitosamente para interview_id: {interview_id}")

            answer_start = time.time()
            answer = pipecat_connection.get_answer()
            logger.info(f"⏱️ Answer generated in {(time.time() - answer_start):.3f}s")
            
            # Updating the peer connection inside the map
            pcs_map[answer["pc_id"]] = pipecat_connection
            
            total_time = time.time() - start_time
            logger.info(f"✅ WebRTC connection established successfully for interview_id: {interview_id}")
            logger.info(f"⏱️ Total connection time: {total_time:.3f}s")
            return answer
            
        except Exception as e:
            logger.error(f"Error establishing WebRTC connection for interview_id {interview_id}: {str(e)}")
            raise
    
# Instancia global del servicio
speech_service = SpeechService()