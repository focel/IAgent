#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#
import os
from ..infrastructure.repositories.interview_repository import SupabaseInterviewRepository
from ..infrastructure.repositories.conversation_repository import ConversationRepository
from ..models.conversation import Conversation
from .context_system_service import ContextService
from ..infrastructure.repositories.questions_repository import QuestionsRepository
from .qa_context_provider import QAContextProvider

from dotenv import load_dotenv
from loguru import logger
from simli import SimliConfig
from datetime import datetime
from pathlib import Path

from pipecat.services.elevenlabs.tts import ElevenLabsTTSService  
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.audio.turn.smart_turn.base_smart_turn import SmartTurnParams
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.simli.video import SimliVideoService
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.frames.frames import EndFrame, EndTaskFrame, TTSSpeakFrame
from pipecat.processors.frame_processor import FrameDirection
from pipecat.services.llm_service import FunctionCallParams
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.processors.transcript_processor import TranscriptProcessor
from ..config.redis_config import redis_client


load_dotenv(override=True)

_interview_repository = None
_context_service = None
_qa_service = None
TRANSCRIPT_BASE_DIR = Path("storage")
_shutdown_services_callback = None
# We store functions so objects (e.g. SileroVADAnalyzer) don't get
# instantiated. The function will be called when the desired transport gets
# selected.
def get_context_service():
    """Gets the context service instance."""
    global _interview_repository, _context_service
    
    if _context_service is None:
        _interview_repository = SupabaseInterviewRepository()
        _context_service = ContextService(_interview_repository)
    
    return _context_service

def get_qa_service():
    """Gets the Q&A service instance."""
    global _qa_service
    
    if _qa_service is None:
        _qa_service = QAContextProvider(QuestionsRepository())
    
    return _qa_service


async def end_conversation(params: FunctionCallParams):
    # Optional: speak a goodbye
    await params.llm.push_frame(TTSSpeakFrame("Okay, Thank you for koining us today, I'll be ending the session now."))
    # Push an EndTaskFrame upstream to terminate gracefully
    await params.llm.push_frame(EndTaskFrame(), FrameDirection.UPSTREAM)
    # Return a result object for the LLM (optional)
    await params.result_callback({"status": "ended"})
    if _shutdown_services_callback is not None:
        await _shutdown_services_callback()

end_fn_schema = FunctionSchema(
    name="end_conversation",
    description="End the current session and say goodbye",
    properties={},
    required=[]
)

tools = ToolsSchema(standard_tools=[end_fn_schema])
# Register the tool with your LLM service


transport_params = {
    "daily": lambda: DailyParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        video_out_enabled=True,
        video_out_is_live=True,
        video_out_width=512,
        video_out_height=512,
        vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
        turn_analyzer=LocalSmartTurnAnalyzerV3(params=SmartTurnParams()),
    ),
    "webrtc": lambda: TransportParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        video_out_enabled=True,
        video_out_is_live=True,
        video_out_width=512,
        video_out_height=512,
        vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
        turn_analyzer=LocalSmartTurnAnalyzerV3(params=SmartTurnParams()),
    ),
}


async def run_bot(webrtc_connection, runner_args: RunnerArguments, interview_id: str = None, job_role: str = None):
    logger.info(f"Starting bot")

    # Create a transport using the WebRTC connection
    transport = SmallWebRTCTransport(
        webrtc_connection=webrtc_connection,
        params=TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            video_out_enabled=True,
            video_out_is_live=True,
            video_out_width=512,
            video_out_height=512,
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
            turn_analyzer=LocalSmartTurnAnalyzerV3(params=SmartTurnParams()),
        ),
    )

    # Use provided parameters or fallback to defaults
    if not interview_id:
        interview_id = "default_interview"
    if not job_role:
        job_role = "Software Engineer"
    
    logger.info(f"Running bot for interview_id: {interview_id}, job_role: {job_role}")

    # Get dynamic context and Q&A
    context_service = get_context_service()
    qa_service = get_qa_service()
    
    system_instruction = await context_service.get_dynamic_context(interview_id)
    
    # Get Q&A context using the correct methods
    context_data = await qa_service.aggregate_context_for_job(job_role)
    qa_context = qa_service.format_context_for_injection(context_data)
    
    # Combine system instruction with Q&A context
    enhanced_system_instruction = f"{system_instruction}\n\n{qa_context}"

    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY")
    )

    tts = ElevenLabsTTSService(
        api_key=os.getenv("ELEVENLABS_API_KEY", ""),
        voice_id=os.getenv("ELEVENLABS_VOICE_ID", ""),
    )

    simli_ai = SimliVideoService(
        SimliConfig(os.getenv("SIMLI_API_KEY"), os.getenv("SIMLI_FACE_ID")),
    )
    
    # LLM OpenAI para evitar errores de rate limiting de Groq
    llm = OpenAILLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o-mini",
    )
    
    llm.register_function(
        "end_conversation",
        end_conversation,
        cancel_on_interruption=True,
    )

    messages = [
        {
            "role": "system",
            "content": enhanced_system_instruction,
        },
    ]

    context = LLMContext(messages, tools=tools)
    context_aggregator = LLMContextAggregatorPair(context)

    transcript = TranscriptProcessor()
    session_timestamp = datetime.utcnow()
    session_transcript_dir = TRANSCRIPT_BASE_DIR
    transcript_path = session_transcript_dir / f"session-{session_timestamp:%Y%m%dT%H%M%SZ}.md"
    transcript_initialized = False
    services_shutdown = False

    async def shutdown_services():
        nonlocal services_shutdown
        if services_shutdown:
            return
        services_shutdown = True
        try:
            await tts.stop(EndFrame())
        except Exception:
            logger.exception("Failed to stop ElevenLabs TTS service")
        try:
            await tts.cleanup()
        except Exception:
            logger.exception("Failed to clean up ElevenLabs TTS service")

    global _shutdown_services_callback
    _shutdown_services_callback = shutdown_services

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            transcript.user(),
            context_aggregator.user(),
            llm,
            tts,
            simli_ai,
            transport.output(),
            transcript.assistant(), 
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        idle_timeout_secs=runner_args.pipeline_idle_timeout_secs,
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info(f"Client connected")
        # Start conversation - empty prompt to let LLM follow system instructions
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info(f"Client disconnected")
        
        # Guardar conversación completa en Supabase
        try:
            stream_key = f"interview:{interview_id}:transcript"
            full_conversation_text = redis_client.get_stream_content(stream_key)
            
            if full_conversation_text:
                conversation_repo = ConversationRepository()
                conversation = Conversation(
                    interview_id=interview_id,
                    full_text=full_conversation_text,
                    context_data={
                        "job_role": job_role,
                        "system_instruction": enhanced_system_instruction[:500]  # Primeros 500 chars
                    }
                )
                
                if conversation_repo.save(conversation):
                    logger.info(f"✅ Conversación guardada en Supabase para interview_id: {interview_id}")
                    # Limpiar stream de Redis después de guardar
                    redis_client.delete_stream(stream_key)
                else:
                    logger.error(f"❌ Error al guardar conversación en Supabase para interview_id: {interview_id}")
            else:
                logger.warning(f"⚠️  No se encontró conversación en Redis para interview_id: {interview_id}")
                
        except Exception as e:
            logger.error(f"❌ Error al procesar conversación al desconectar: {str(e)}")
        
        await task.cancel()
        await shutdown_services()

    @transcript.event_handler("on_transcript_update")
    async def handle_transcript_update(processor, frame):
        nonlocal transcript_initialized
        if not frame.messages:
            return
        if not transcript_initialized:
            session_transcript_dir.mkdir(parents=True, exist_ok=True)
            with transcript_path.open("w", encoding="utf-8") as md_file:
                md_file.write(
                    f"# Interview transcript ({session_timestamp:%Y-%m-%d %H:%M UTC})\n\n"
                )
            transcript_initialized = True
        lines = []
        for message in frame.messages:
            role = message.role.capitalize()
            timestamp = message.timestamp or datetime.utcnow().isoformat()
            content = message.content.strip().replace("\n", "  \n")
            lines.append(f"- **{timestamp} – {role}:** {content}")
            
            # Guardar en Redis Stream para captura de conversación completa
            stream_key = f"interview:{interview_id}:transcript"
            redis_data = {
                "role": role.lower(),
                "content": content,
                "timestamp": timestamp,
                "interview_id": interview_id
            }
            redis_client.add_to_stream(stream_key, redis_data)
            
        with transcript_path.open("a", encoding="utf-8") as md_file:
            md_file.write("\n".join(lines) + "\n")

    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)
    try:
        await runner.run(task)
    finally:
        await shutdown_services()
        if _shutdown_services_callback is shutdown_services:
            _shutdown_services_callback = None