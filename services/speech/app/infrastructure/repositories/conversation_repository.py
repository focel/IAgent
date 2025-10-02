"""
Repository for managing conversation data in the database.
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..database.supabase_connection import get_supabase_client
from ...models.conversation import Conversation

logger = logging.getLogger(__name__)


class ConversationRepository:
    """
    Repository class for handling conversation database operations.
    """
    
    def __init__(self):
        self.table_name = "interview_full_conversations"
    
    def save(self, conversation: Conversation) -> bool:
        """
        Save a conversation to the database.
        
        Args:
            conversation: The conversation to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            client = get_supabase_client()
            if not client:
                logger.error("❌ No se pudo obtener el cliente de Supabase")
                return False
            
            # Prepare data for insertion
            conversation_data = {
                "id": conversation.id,
                "interview_id": conversation.interview_id,
                "full_text": conversation.full_text,
                "context_data": conversation.context_data,
                "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Insert or update conversation
            result = client.table(self.table_name).upsert(conversation_data).execute()
            
            if result.data:
                logger.info(f"✅ Conversación guardada exitosamente: {conversation.id}")
                return True
            else:
                logger.error(f"❌ Error al guardar conversación: {conversation.id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error en save conversation: {str(e)}")
            return False
    
    def find_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """
        Find a conversation by its ID.
        
        Args:
            conversation_id: The conversation ID to search for
            
        Returns:
            Conversation object if found, None otherwise
        """
        try:
            client = get_supabase_client()
            if not client:
                logger.error("❌ No se pudo obtener el cliente de Supabase")
                return None
            
            result = client.table(self.table_name).select("*").eq("id", conversation_id).execute()
            
            if result.data and len(result.data) > 0:
                return Conversation.from_dict(result.data[0])
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error al buscar conversación por ID {conversation_id}: {str(e)}")
            return None
    
    def find_by_interview_id(self, interview_id: str) -> Optional[Conversation]:
        """
        Find a conversation by interview ID.
        
        Args:
            interview_id: The interview ID to search for
            
        Returns:
            Conversation object if found, None otherwise
        """
        try:
            client = get_supabase_client()
            if not client:
                logger.error("❌ No se pudo obtener el cliente de Supabase")
                return None
            
            result = client.table(self.table_name).select("*").eq("interview_id", interview_id).execute()
            
            if result.data and len(result.data) > 0:
                return Conversation.from_dict(result.data[0])
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error al buscar conversación por interview_id {interview_id}: {str(e)}")
            return None
    
    def update_full_text(self, conversation_id: str, full_text: str) -> bool:
        """
        Update only the full_text field of a conversation.
        
        Args:
            conversation_id: The conversation ID to update
            full_text: The new full text content
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            client = get_supabase_client()
            if not client:
                logger.error("❌ No se pudo obtener el cliente de Supabase")
                return False
            
            update_data = {
                "full_text": full_text,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            result = client.table(self.table_name).update(update_data).eq("id", conversation_id).execute()
            
            if result.data:
                logger.info(f"✅ Texto de conversación actualizado: {conversation_id}")
                return True
            else:
                logger.error(f"❌ Error al actualizar texto de conversación: {conversation_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error en update_full_text: {str(e)}")
            return False
    
    def delete(self, conversation_id: str) -> bool:
        """
        Delete a conversation from the database.
        
        Args:
            conversation_id: The conversation ID to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            client = get_supabase_client()
            if not client:
                logger.error("❌ No se pudo obtener el cliente de Supabase")
                return False
            
            result = client.table(self.table_name).delete().eq("id", conversation_id).execute()
            
            if result.data is not None:
                logger.info(f"✅ Conversación eliminada: {conversation_id}")
                return True
            else:
                logger.error(f"❌ Error al eliminar conversación: {conversation_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error en delete conversation: {str(e)}")
            return False
    
    def get_recent_conversations(self, limit: int = 10) -> List[Conversation]:
        """
        Get recent conversations ordered by creation date.
        
        Args:
            limit: Maximum number of conversations to return
            
        Returns:
            List of Conversation objects
        """
        try:
            client = get_supabase_client()
            if not client:
                logger.error("❌ No se pudo obtener el cliente de Supabase")
                return []
            
            result = client.table(self.table_name).select("*").order("created_at", desc=True).limit(limit).execute()
            
            conversations = []
            if result.data:
                for data in result.data:
                    conversations.append(Conversation.from_dict(data))
            
            return conversations
            
        except Exception as e:
            logger.error(f"❌ Error al obtener conversaciones recientes: {str(e)}")
            return []