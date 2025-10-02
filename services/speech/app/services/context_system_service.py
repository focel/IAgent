from typing import Optional
import logging
from ..infrastructure.repositories.interview_repository import SupabaseInterviewRepository


class ContextService:
    """Servicio para manejar la generación de contexto dinámico para entrevistas."""
    
    def __init__(self, interview_repository: SupabaseInterviewRepository):
        """Inicializa el servicio con el repositorio de entrevistas.
        
        Args:
            interview_repository: Implementación del repositorio de entrevistas
        """
        self.interview_repository = interview_repository
        # Fallback prompt usando el contenido de simli_default
        self.fallback_instruction = """You are {candidate_name} an AI agent performing structured job interviews over a WebRTC call. The current candidate ({candidate_name}) is applying for a {job_role} position at the company Anyone AI. 

{job_description}

{additional_context}

You have access to a tool called `end_conversation` 
When the user says goodbye or asks to end, you MUST call this tool using the function calling interface, not by describing it in text."""
    
    async def get_dynamic_context(self, interview_id: str) -> str:
        """Genera contexto dinámico basado en la información de la entrevista y prompts de la base de datos.
        
        Args:
            interview_id: ID de la entrevista
            
        Returns:
            Contexto dinámico personalizado para la entrevista
        """
        try:
            # Obtener información de la entrevista
            interview_context = await self.interview_repository.get_interview_context(interview_id)
            
            if not interview_context:
                logging.warning(f"No se encontró contexto para interview_id: {interview_id}")
                return self.fallback_instruction
            
            # Verificar si hay un prompt personalizado para esta entrevista
            if interview_context.get('custom_prompt'):
                # Usar el prompt personalizado y personalizarlo con datos de la entrevista
                dynamic_instruction = self._personalize_prompt(
                    interview_context['custom_prompt'], 
                    interview_context
                )
            else:
                # Usar prompt por defecto (fallback_instruction)
                dynamic_instruction = self._personalize_prompt(self.fallback_instruction, interview_context)
            
            logging.info(f"Contexto dinámico generado para interview_id: {interview_id}")
            return dynamic_instruction
            
        except Exception as e:
             logging.error(f"Error generando contexto dinámico para {interview_id}: {str(e)}")
             return self.fallback_instruction
    
    def _personalize_prompt(self, base_prompt: str, context: dict) -> str:
        """Personaliza un prompt base con información específica de la entrevista.
        
        Args:
            base_prompt: Prompt base a personalizar
            context: Diccionario con información de la entrevista
            
        Returns:
            Prompt personalizado
        """
        job_role = context.get('job_role', 'Unknown Position')
        candidate_name = context.get('candidate_name', 'Unknown Candidate')
        job_description = context.get('job_description', 'No description available')
        interview_status = context.get('interview_status', 'active')
        additional_context = context.get('additional_context', '')
        
        # Variables de reemplazo disponibles en el prompt
        replacements = {
            '{job_role}': job_role,
            '{candidate_name}': candidate_name,
            '{job_description}': job_description,
            '{interview_status}': interview_status,
            '{additional_context}': additional_context
        }
        
        # Aplicar reemplazos
        personalized_prompt = base_prompt
        for placeholder, value in replacements.items():
            personalized_prompt = personalized_prompt.replace(placeholder, value)
        
        # Si no hay placeholders, agregar contexto básico al final
        if not any(placeholder in base_prompt for placeholder in replacements.keys()):
            context_addition = f"""\n\n### Job Information\n- Position: {job_role}\n- Description: {job_description}\n- Candidate: {candidate_name}"""
            personalized_prompt += context_addition
        
        return personalized_prompt.strip()