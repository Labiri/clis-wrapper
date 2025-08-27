"""
Confidence-based XML format detection for Claude responses.
Uses scoring system for nuanced and flexible detection.
"""

import re
import logging
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)


class XMLDetector:
    """Confidence-based XML detection for nuanced scenarios."""
    
    def __init__(self, confidence_threshold: float = 5.0):
        self.confidence_threshold = confidence_threshold
        
    def _strip_markdown_code_blocks(self, text: str) -> str:
        """Remove markdown code blocks to avoid false positives."""
        # Remove fenced code blocks (```...```)
        text = re.sub(r'```[^`]*```', '', text, flags=re.DOTALL)
        # Remove inline code (`...`)
        text = re.sub(r'`[^`]+`', '', text)
        return text
    
    def _count_lines_in_code_blocks(self, text: str) -> int:
        """Count lines within code blocks."""
        code_blocks = re.findall(r'```[^`]*```', text, flags=re.DOTALL)
        total_lines = 0
        for block in code_blocks:
            total_lines += block.count('\n')
        return total_lines
    
    def is_primarily_code_discussion(self, messages: List[Dict]) -> bool:
        """Check if messages are primarily about code/examples."""
        for msg in messages:
            content = ""
            if isinstance(msg, dict):
                content = msg.get('content', '')
            elif hasattr(msg, 'content'):
                content = msg.content
                
            if isinstance(content, str):
                # Count code blocks
                code_block_count = content.count('```')
                
                # If more than 2 code blocks, check percentage
                if code_block_count > 2:
                    total_lines = content.count('\n') + 1
                    code_lines = self._count_lines_in_code_blocks(content)
                    # If more than 50% is code blocks, it's likely a code discussion
                    if code_lines > total_lines * 0.5:
                        return True
        return False
    
    def _check_for_tool_definition_structure(self, content: str) -> float:
        """
        Check for actual tool definition structure and return confidence score.
        Tool definitions have:
        - Opening and closing tags
        - Description or usage instructions
        - Consistent formatting
        """
        score = 0.0
        
        # Remove code blocks first
        clean_content = self._strip_markdown_code_blocks(content)
        
        # Look for structured tool definitions with descriptions
        tool_def_pattern = r'<(\w+)>\s*(?:Use this tool|This tool|Used for|Description:).*?</\1>'
        matches = re.findall(tool_def_pattern, clean_content, re.DOTALL | re.IGNORECASE)
        score += len(matches) * 2.0  # 2 points per structured tool definition
        
        # Look for parameter definitions within tools
        param_pattern = r'<(?:parameter|param|arg|argument)>.*?</(?:parameter|param|arg|argument)>'
        param_matches = re.findall(param_pattern, clean_content, re.DOTALL | re.IGNORECASE)
        score += len(param_matches) * 1.0  # 1 point per parameter definition
        
        return score
    
    def calculate_confidence(self, messages: List[Dict]) -> Tuple[float, List[str]]:
        """Calculate confidence score for XML requirement."""
        confidence_score = 0.0
        detected_patterns = []
        
        # Combine all message content
        combined_content = ""
        system_message_content = ""
        
        for msg in messages:
            content = ""
            role = ""
            
            if isinstance(msg, dict):
                content = msg.get('content', '')
                role = msg.get('role', '')
            elif hasattr(msg, 'content'):
                content = msg.content
                role = getattr(msg, 'role', '')
                
            if isinstance(content, str):
                combined_content += " " + content
                if role == 'system':
                    system_message_content += " " + content
        
        # Process content without code blocks
        clean_content = self._strip_markdown_code_blocks(combined_content)
        clean_system = self._strip_markdown_code_blocks(system_message_content)
        
        # High confidence indicators (3 points each)
        high_confidence_patterns = [
            (r'You must use tools to respond', 3.0, "Mandatory tool usage directive"),
            (r'Tool uses are formatted using XML-style tags', 3.0, "XML format specification"),
            (r'<tool_name>.*?</tool_name>', 3.0, "Tool name definitions"),
            (r'respond using (?:the )?<\w+> tool', 3.0, "Specific tool response format"),
        ]
        
        for pattern, points, description in high_confidence_patterns:
            if re.search(pattern, clean_content, re.IGNORECASE | re.DOTALL):
                confidence_score += points
                detected_patterns.append(description)
        
        # Medium confidence indicators (2 points each)
        medium_patterns = [
            (r'<attempt_completion>', 2.0, "attempt_completion tool"),
            (r'<ask_followup_question>', 2.0, "ask_followup_question tool"),
            (r'Use this tool to', 2.0, "Tool usage instructions"),
            (r'Available tools?:', 2.0, "Tool list header"),
        ]
        
        for pattern, points, description in medium_patterns:
            if re.search(pattern, clean_content, re.IGNORECASE):
                confidence_score += points
                detected_patterns.append(description)
        
        # Low confidence indicators (1 point each)
        low_patterns = [
            (r'<\w+_\w+>', 1.0, "Compound XML tags"),
            (r'tool', 1.0, "Tool mentions"),
            (r'XML', 1.0, "XML mentions"),
        ]
        
        for pattern, points, description in low_patterns:
            matches = re.findall(pattern, clean_content, re.IGNORECASE)
            if matches:
                confidence_score += points * min(len(matches), 3)  # Cap at 3 occurrences
                detected_patterns.append(f"{description} ({len(matches)}x)")
        
        # Check for tool definition structure
        structure_score = self._check_for_tool_definition_structure(combined_content)
        if structure_score > 0:
            confidence_score += structure_score
            detected_patterns.append(f"Tool definition structure ({structure_score:.1f} points)")
        
        # Negative indicators (subtract points)
        negative_patterns = [
            (r'how to use XML', -3.0, "Discussion about XML"),
            (r'\.xml\b', -2.0, "XML file extension"),
            (r'\.html\b', -2.0, "HTML file extension"),
            (r'example of XML', -2.0, "XML example discussion"),
        ]
        
        for pattern, points, description in negative_patterns:
            if re.search(pattern, clean_content, re.IGNORECASE):
                confidence_score += points  # points are negative
                detected_patterns.append(f"NEGATIVE: {description}")
        
        # Bonus for system messages (multiply system message indicators by 1.5)
        if system_message_content:
            system_bonus = 0.0
            for pattern, points, _ in high_confidence_patterns + medium_patterns:
                if re.search(pattern, clean_system, re.IGNORECASE | re.DOTALL):
                    system_bonus += points * 0.5  # 50% bonus for system messages
            
            if system_bonus > 0:
                confidence_score += system_bonus
                detected_patterns.append(f"System message bonus (+{system_bonus:.1f})")
        
        return confidence_score, detected_patterns
    
    def detect(self, messages: List[Dict]) -> Tuple[bool, float, List[str]]:
        """
        Detect XML requirement with confidence scoring.
        Returns: (requires_xml, confidence_score, detected_patterns)
        """
        # First check if it's primarily a code discussion
        if self.is_primarily_code_discussion(messages):
            logger.debug("Confidence-based detection: Primarily code discussion, skipping XML enforcement")
            return False, 0.0, ["Primarily code discussion"]
        
        # Calculate confidence
        confidence, patterns = self.calculate_confidence(messages)
        
        # Make decision based on threshold
        requires_xml = confidence >= self.confidence_threshold
        
        if requires_xml:
            logger.info(f"📊 Confidence-based XML detection: YES (score: {confidence:.1f}/{self.confidence_threshold})")
            logger.info(f"   Patterns: {', '.join(patterns)}")
        else:
            logger.debug(f"Confidence-based XML detection: NO (score: {confidence:.1f}/{self.confidence_threshold})")
            
        return requires_xml, confidence, patterns