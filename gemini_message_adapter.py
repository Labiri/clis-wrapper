import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class GeminiMessageAdapter:
    """Adapter to convert between OpenAI and Gemini CLI message formats."""
    
    @staticmethod
    def prepare_streaming_chunk(text: str, finish_reason: Optional[str] = None) -> Dict[str, Any]:
        """Prepare a streaming chunk in OpenAI format."""
        return {
            'choices': [{
                'delta': {
                    'content': text,
                    'role': 'assistant' if text else None
                },
                'index': 0,
                'finish_reason': finish_reason
            }]
        }
    
    @staticmethod
    def validate_messages(messages: List[Dict[str, Any]]) -> tuple[bool, Optional[str]]:
        """
        Validate message format for Gemini compatibility.
        Returns (is_valid, error_message).
        """
        if not messages:
            return False, "Messages list cannot be empty"
        
        # Check for valid roles
        valid_roles = {'user', 'assistant', 'system'}
        for i, msg in enumerate(messages):
            role = msg.get('role')
            if role not in valid_roles:
                return False, f"Invalid role '{role}' in message {i}"
            
            # Check content exists
            if 'content' not in msg:
                return False, f"Missing content in message {i}"
        
        return True, None