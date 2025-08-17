"""
Chat mode implementation for Claude Code OpenAI wrapper.

This module provides secure sandboxed execution when chat mode is activated
via model name suffix (-chat), disabling file system access and limiting 
available tools. Sessions created in chat mode are automatically cleaned up 
to prevent them from appearing in Claude Code's /resume command.
"""

import os
import tempfile
import shutil
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ChatMode:
    """Core chat mode functionality."""
    
    @staticmethod
    def get_allowed_tools() -> List[str]:
        """Get the list of tools allowed in chat mode."""
        # Only web-based tools - no file system access
        return ["WebSearch", "WebFetch"]
    
    @staticmethod
    def get_allowed_tools_for_request(messages: List[Dict[str, Any]], is_chat_mode: bool) -> Optional[List[str]]:
        """
        Conditionally determine allowed tools based on message content.
        
        Args:
            messages: List of message dictionaries from the request
            is_chat_mode: Whether chat mode is active
            
        Returns:
            List of allowed tools if in chat mode, None otherwise (no restrictions)
        """
        if not is_chat_mode:
            return None  # No tool restrictions in normal mode
        
        # Start with base chat mode tools
        base_tools = ["WebSearch", "WebFetch"]
        
        # Check if any message contains images
        has_images = ChatMode._check_messages_for_images(messages)
        
        if has_images:
            # Enable Read tool for image analysis
            logger.info("Images detected in chat mode - temporarily enabling Read tool for image analysis")
            return base_tools + ["Read"]
        
        return base_tools
    
    @staticmethod
    def _check_messages_for_images(messages: List[Dict[str, Any]]) -> bool:
        """
        Check if any message in the conversation contains images.
        
        This checks for:
        1. OpenAI-format image_url content parts
        2. File-based image placeholders like [Image #1]
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            True if images are found, False otherwise
        """
        import re
        
        # Pattern to match [Image #N] or [Image: path]
        image_placeholder_pattern = re.compile(r'\[Image[:\s]+(?:#\d+|[^]]+)\]')
        
        for message in messages:
            content = message.get('content', '')
            
            # Check for array content (multimodal messages with image_url)
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get('type') == 'image_url':
                        return True
                    # Also check text parts for placeholders
                    if isinstance(part, dict) and part.get('type') == 'text':
                        text = part.get('text', '')
                        if image_placeholder_pattern.search(text):
                            logger.debug("Found image placeholder in text content part")
                            return True
            
            # Check string content for image placeholders
            elif isinstance(content, str):
                if image_placeholder_pattern.search(content):
                    logger.debug(f"Found image placeholder in string content: {content[:100]}...")
                    return True
        
        return False
    
    @staticmethod
    def create_sandbox() -> str:
        """Create a temporary sandbox directory for isolated execution."""
        sandbox_dir = tempfile.mkdtemp(prefix="claude_chat_sandbox_")
        logger.debug(f"Created sandbox directory: {sandbox_dir}")
        return sandbox_dir
    
    @staticmethod
    def cleanup_sandbox(path: str) -> None:
        """Remove sandbox directory and all contents."""
        try:
            if os.path.exists(path) and path.startswith(tempfile.gettempdir()):
                shutil.rmtree(path, ignore_errors=True)
                logger.debug(f"Cleaned up sandbox directory: {path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup sandbox {path}: {e}")


@contextmanager
def sanitized_environment():
    """
    Context manager to temporarily remove sensitive environment variables.
    
    Removes path-revealing variables during execution and restores them after.
    """
    original_env = {}
    
    # Variables that might reveal system paths
    sensitive_vars = ['PWD', 'OLDPWD', 'HOME', 'USER', 'LOGNAME']
    
    # Claude-specific variables that might contain paths
    claude_vars = [k for k in os.environ.keys() if k.startswith('CLAUDE_') and 'DIR' in k]
    
    # Store and remove sensitive variables
    for var in sensitive_vars + claude_vars:
        if var in os.environ:
            original_env[var] = os.environ.pop(var)
            logger.debug(f"Temporarily removed environment variable: {var}")
    
    try:
        yield
    finally:
        # Restore original environment
        for var, value in original_env.items():
            os.environ[var] = value
            logger.debug(f"Restored environment variable: {var}")


def get_chat_mode_info(is_chat_mode: bool = False) -> Dict[str, Any]:
    """Get current chat mode configuration and status.
    
    Args:
        is_chat_mode: Whether chat mode is currently active for the request
        
    Returns:
        Dict containing chat mode configuration
    """
    return {
        "enabled": is_chat_mode,
        "allowed_tools": ChatMode.get_allowed_tools(),
        "sandbox_enabled": True,
        "sessions_disabled": True,
        "file_operations_disabled": True
    }