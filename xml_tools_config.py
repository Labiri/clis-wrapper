"""
Configuration module for XML tool detection.
Allows users to specify known XML tools via environment variable.
"""

import os
import logging
from typing import List

logger = logging.getLogger(__name__)


def get_known_xml_tools() -> List[str]:
    """
    Get list of known XML tools from environment variable.
    Returns empty list if not set or empty.
    
    Environment variable format:
    XML_KNOWN_TOOLS="attempt_completion,ask_followup_question,read_file,write_to_file"
    
    Returns:
        List of tool names (lowercase, trimmed)
    """
    tools_env = os.getenv('XML_KNOWN_TOOLS', '')
    
    if not tools_env:
        logger.debug("XML_KNOWN_TOOLS not set or empty - no tools will be detected")
        return []
    
    # Parse comma-separated values, trim whitespace, convert to lowercase
    tools = [tool.strip().lower() for tool in tools_env.split(',') if tool.strip()]
    
    if tools:
        logger.debug(f"Configured XML tools: {tools}")
    else:
        logger.debug("XML_KNOWN_TOOLS is set but contains no valid tools")
    
    return tools


def is_known_xml_tool(tool_name: str) -> bool:
    """
    Check if a tool name is in the list of known XML tools.
    
    Args:
        tool_name: Name of the tool to check (case-insensitive)
        
    Returns:
        True if tool is known, False otherwise
    """
    known_tools = get_known_xml_tools()
    return tool_name.lower() in known_tools