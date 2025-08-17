"""
Response filtering for hiding implementation details in streaming responses.

This module filters out tool usage mentions and file paths from Claude's responses
while preserving the actual image analysis content.
"""

import re
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class ResponseFilter:
    """Filters streaming responses to hide implementation details."""
    
    def __init__(self):
        # Patterns to detect and filter out
        self.tool_mention_patterns = [
            re.compile(r'I need to analyze the image.*?Let me use the Read tool.*?(?=\n|$)', re.IGNORECASE | re.DOTALL),
            re.compile(r'Let me use the Read tool.*?(?=\n|$)', re.IGNORECASE),
            re.compile(r'I\'ll use the Read tool.*?(?=\n|$)', re.IGNORECASE),
            re.compile(r'I should use the Read tool.*?(?=\n|$)', re.IGNORECASE),
            re.compile(r'Using the Read tool.*?(?=\n|$)', re.IGNORECASE),
            re.compile(r'I\'ll read the image file.*?(?=\n|$)', re.IGNORECASE),
            re.compile(r'Let me access these images.*?(?=\n|$)', re.IGNORECASE),
            # Handle numbered lists that describe technical process
            re.compile(r'I need to look at the.*?image files.*?\n\d+\.\s*\n\d+\.\s*\n.*?Let me access.*?(?=\n\n|\Z)', re.IGNORECASE | re.DOTALL),
            # Handle any numbered list that mentions looking at images with technical details
            re.compile(r'I need to look at.*?image.*?\n(?:\d+\.\s*\n)*.*?access.*?(?=\n\n|\Z)', re.IGNORECASE | re.DOTALL),
        ]
        
        # Path patterns to filter
        self.path_patterns = [
            re.compile(r'The image file path is:\s*/[^\s]+', re.IGNORECASE),
            re.compile(r'Image file path:\s*/[^\s]+', re.IGNORECASE),
            re.compile(r'File path:\s*/[^\s]+', re.IGNORECASE),
            re.compile(r'/var/folders/[^\s]+', re.IGNORECASE),
            re.compile(r'/tmp/[^\s]+\.(?:png|jpg|jpeg|gif|webp|bmp)', re.IGNORECASE),
            re.compile(r'claude_chat_sandbox_[^\s]+', re.IGNORECASE),
        ]
        
        # Replacement phrases for filtered content
        self.replacements = {
            'tool_intro': "Looking at the image, ",
            'analyzing': "I can see the image shows ",
        }
        
        # Buffer for handling multi-part text
        self.text_buffer = ""
        
    def should_filter_chunk(self, chunk: str) -> bool:
        """Check if a chunk contains content that should be filtered."""
        chunk_lower = chunk.lower()
        
        # Check for tool mentions
        tool_keywords = [
            'read tool', 'use the read', 'let me use', 'i\'ll use', 
            'file path', '/var/folders', 'claude_chat_sandbox'
        ]
        
        return any(keyword in chunk_lower for keyword in tool_keywords)
        
    def filter_text(self, text: str) -> str:
        """Filter a complete text block to remove implementation details."""
        if not text:
            return text
            
        original_text = text
        filtered_text = text
        
        # Remove tool usage mentions
        for pattern in self.tool_mention_patterns:
            filtered_text = pattern.sub('', filtered_text)
            
        # Remove file paths
        for pattern in self.path_patterns:
            filtered_text = pattern.sub('', filtered_text)
            
        # Clean up any resulting formatting issues
        filtered_text = re.sub(r'\n\s*\n\s*\n', '\n\n', filtered_text)  # Multiple newlines
        filtered_text = re.sub(r'^\s*\n', '', filtered_text)  # Leading newlines
        filtered_text = filtered_text.strip()
        
        # Handle specific case of numbered list format
        numbered_list_match = re.search(r'I need to look at.*?image.*?\n\d+\.\s*\n\d+\.\s*\n.*?access[^\n]*\n*(.*)', original_text, re.IGNORECASE | re.DOTALL)
        if numbered_list_match:
            # Get any content that comes after the technical explanation
            remaining_content = numbered_list_match.group(1).strip() if numbered_list_match.group(1) else ""
            
            if remaining_content:
                # Combine natural start with remaining content
                return f"Looking at the images, {remaining_content}"
            else:
                # Just the natural start
                return "Looking at the images, "
        
        # If we filtered out the beginning, add a natural start
        if original_text and not filtered_text:
            return "Looking at the image, "
        elif original_text and len(filtered_text) < len(original_text) * 0.3:
            # If we removed too much, start with a natural phrase
            if not filtered_text.strip():
                return "I can see the image shows "
            elif not filtered_text.startswith(('I', 'The', 'This', 'Looking')):
                filtered_text = "Looking at the image, " + filtered_text
                
        return filtered_text
        
    def filter_streaming_chunk(self, chunk: str) -> Optional[str]:
        """
        Filter a streaming chunk, handling partial text.
        
        Args:
            chunk: The streaming text chunk
            
        Returns:
            Filtered chunk or None if it should be completely filtered
        """
        # Add to buffer
        self.text_buffer += chunk
        
        # Check if buffer contains complete sentences or phrases we can evaluate
        if any(marker in self.text_buffer for marker in ['.', '\n', '?', '!']):
            # Process the buffer
            filtered = self.filter_text(self.text_buffer)
            
            # Reset buffer and return filtered content
            self.text_buffer = ""
            return filtered
            
        # Check if current buffer should be filtered entirely
        if self.should_filter_chunk(self.text_buffer):
            # Don't output anything yet, keep buffering
            return None
            
        # If it's safe content, we can pass it through
        # But still buffer in case the next chunk makes it problematic
        return None  # Keep buffering for safety
        
    def flush_buffer(self) -> Optional[str]:
        """Flush any remaining content in the buffer."""
        if self.text_buffer:
            filtered = self.filter_text(self.text_buffer)
            self.text_buffer = ""
            return filtered
        return None
        
    def reset(self):
        """Reset the filter state."""
        self.text_buffer = ""


class MessageContentFilter:
    """Filters message content in assistant responses."""
    
    def __init__(self):
        self.response_filter = ResponseFilter()
        
    def filter_assistant_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter an assistant message to remove implementation details.
        
        Args:
            message: The message dictionary to filter
            
        Returns:
            Filtered message dictionary
        """
        if message.get('role') != 'assistant':
            return message
            
        # Clone the message
        filtered_message = message.copy()
        
        # Filter content
        content = filtered_message.get('content')
        if isinstance(content, str):
            filtered_content = self.response_filter.filter_text(content)
            filtered_message['content'] = filtered_content
        elif isinstance(content, list):
            filtered_blocks = []
            for block in content:
                if isinstance(block, dict) and block.get('type') == 'text':
                    text = block.get('text', '')
                    filtered_text = self.response_filter.filter_text(text)
                    if filtered_text:  # Only add non-empty blocks
                        filtered_block = block.copy()
                        filtered_block['text'] = filtered_text
                        filtered_blocks.append(filtered_block)
                else:
                    filtered_blocks.append(block)
            filtered_message['content'] = filtered_blocks
            
        return filtered_message
        
    def should_skip_message(self, message: Dict[str, Any]) -> bool:
        """
        Check if a message should be completely skipped.
        
        Args:
            message: The message to check
            
        Returns:
            True if the message should be skipped
        """
        # Skip tool use messages in chat mode
        if message.get('type') == 'tool_use':
            return True
            
        # Skip system messages about file operations
        if message.get('type') == 'system':
            content = str(message.get('content', ''))
            if any(phrase in content.lower() for phrase in [
                'read tool', 'file path', 'sandbox', 'claude_chat'
            ]):
                return True
                
        return False