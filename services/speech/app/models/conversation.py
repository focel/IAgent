"""
Conversation model for capturing and managing interview conversations.
"""
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import uuid


@dataclass
class Conversation:
    """
    Model for storing complete interview conversations including context and messages.
    """
    interview_id: str
    full_text: str = ""
    context_data: Dict[str, Any] = field(default_factory=dict)
    id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Initialize default values after object creation."""
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.created_at is None:
            self.created_at = datetime.utcnow()

    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to the conversation.
        
        Args:
            role: The role of the message sender (system, user, assistant)
            content: The message content
        """
        if self.full_text:
            self.full_text += "\n"
        self.full_text += f"{role}: {content}"

    def set_initial_context(self, system_prompt: str, qa_context: str, job_role: str = "") -> None:
        """
        Set the initial context for the conversation.
        
        Args:
            system_prompt: The system instruction/prompt
            qa_context: The Q&A context for the interview
            job_role: The job role being interviewed for
        """
        self.context_data = {
            "system_prompt": system_prompt,
            "qa_context": qa_context,
            "job_role": job_role,
            "started_at": datetime.utcnow().isoformat()
        }
        
        # Add system prompt to full_text
        self.add_message("system", system_prompt)

    def add_context_info(self, key: str, value: Any) -> None:
        """
        Add additional context information.
        
        Args:
            key: The context key
            value: The context value
        """
        self.context_data[key] = value

    def get_conversation_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the conversation.
        
        Returns:
            Dictionary with conversation summary information
        """
        lines = self.full_text.split('\n') if self.full_text else []
        message_count = len([line for line in lines if line.strip()])
        
        return {
            "id": self.id,
            "interview_id": self.interview_id,
            "message_count": message_count,
            "has_context": bool(self.context_data),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "job_role": self.context_data.get("job_role", "")
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the conversation to a dictionary for database storage.
        
        Returns:
            Dictionary representation of the conversation
        """
        return {
            "id": self.id,
            "interview_id": self.interview_id,
            "full_text": self.full_text,
            "context_data": self.context_data,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Conversation':
        """
        Create a Conversation instance from a dictionary.
        
        Args:
            data: Dictionary with conversation data
            
        Returns:
            Conversation instance
        """
        # Parse datetime strings if they exist
        created_at = data.get("created_at")
        if created_at and isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except ValueError:
                created_at = None
        
        updated_at = data.get("updated_at")
        if updated_at and isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            except ValueError:
                updated_at = None
        
        return cls(
            id=data.get("id"),
            interview_id=data["interview_id"],
            full_text=data.get("full_text", ""),
            context_data=data.get("context_data", {}),
            created_at=created_at,
            updated_at=updated_at
        )

    def is_valid(self) -> bool:
        """
        Validate the conversation data.
        
        Returns:
            True if the conversation is valid, False otherwise
        """
        return bool(self.interview_id and isinstance(self.context_data, dict))