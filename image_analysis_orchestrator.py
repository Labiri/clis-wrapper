"""
Image Analysis Orchestrator for Claude Code OpenAI Wrapper.

This module handles image analysis by making isolated CLI calls to Claude or Gemini
with tools enabled, then returning the analysis results to be used as context.
"""

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import uuid
import shlex

from image_handler import ImageHandler

logger = logging.getLogger(__name__)


class ImageAnalysisOrchestrator:
    """Orchestrates image analysis through isolated CLI calls."""
    
    def __init__(
        self,
        claude_cli_path: str = "claude",
        gemini_cli_path: str = "gemini",
        verbose: bool = False
    ):
        """
        Initialize the orchestrator.
        
        Args:
            claude_cli_path: Path to Claude CLI binary
            gemini_cli_path: Path to Gemini CLI binary
            verbose: Enable verbose logging
        """
        self.claude_cli_path = claude_cli_path
        self.gemini_cli_path = gemini_cli_path
        self.verbose = verbose
        
    def analyze_images_if_present(
        self, 
        messages: List[Dict], 
        model: str,
        original_prompt: Optional[str] = None
    ) -> Tuple[bool, Optional[str], List[Dict]]:
        """
        Check for images in messages and analyze them if present.
        
        Args:
            messages: List of message dictionaries in OpenAI format
            model: Model name to determine which CLI to use
            original_prompt: Optional original user prompt for context
            
        Returns:
            Tuple of (has_images, analysis_result, modified_messages)
        """
        # Create a temporary sandbox directory
        with tempfile.TemporaryDirectory() as sandbox_dir:
            sandbox_path = Path(sandbox_dir)
            
            # Initialize image handler
            image_handler = ImageHandler(sandbox_dir=sandbox_path)
            
            # Process images from messages
            image_mappings = image_handler.process_messages_for_images(messages)
            
            # Check for image placeholders
            image_placeholders = ImageHandler.detect_image_placeholders(messages)
            
            # If no images found, return original messages
            if not image_mappings and not image_placeholders:
                logger.debug("No images found in messages")
                return False, None, messages
            
            logger.info(f"Found {len(image_mappings)} images and {len(image_placeholders)} placeholders")
            
            # Get image paths for analysis
            image_paths = []
            if image_mappings:
                image_paths = image_handler.get_image_references_for_prompt(image_mappings)
            
            # Resolve placeholders if present
            if image_placeholders:
                resolved = image_handler.resolve_image_placeholders(
                    image_placeholders, 
                    image_paths
                )
                # Add resolved placeholder paths
                for placeholder, path in resolved.items():
                    if path and not path.startswith("["):  # Valid path
                        image_paths.append(path)
            
            if not image_paths:
                logger.warning("Images detected but no valid paths found")
                return False, None, messages
            
            # Perform image analysis
            analysis = self._analyze_images(
                image_paths, 
                model, 
                original_prompt,
                sandbox_dir
            )
            
            if analysis:
                # Create modified messages with analysis context
                modified_messages = self._inject_analysis_context(
                    messages, 
                    analysis,
                    image_mappings,
                    image_placeholders
                )
                return True, analysis, modified_messages
            else:
                logger.warning("Image analysis failed, proceeding without analysis")
                return True, None, messages
    
    def _analyze_images(
        self, 
        image_paths: List[str], 
        model: str,
        user_prompt: Optional[str],
        sandbox_dir: str
    ) -> Optional[str]:
        """
        Analyze images using appropriate CLI tool.
        
        Args:
            image_paths: List of paths to image files
            model: Model name to determine CLI
            user_prompt: Optional user prompt for context
            sandbox_dir: Sandbox directory for the CLI
            
        Returns:
            Analysis result as string, or None if failed
        """
        # Determine which CLI to use based on model
        if model.startswith("gemini"):
            return self._analyze_with_gemini(image_paths, user_prompt, sandbox_dir)
        else:
            # Default to Claude
            return self._analyze_with_claude(image_paths, user_prompt, sandbox_dir)
    
    def _analyze_with_claude(
        self, 
        image_paths: List[str],
        user_prompt: Optional[str],
        sandbox_dir: str
    ) -> Optional[str]:
        """
        Analyze images using Claude CLI.
        
        Args:
            image_paths: List of image file paths
            user_prompt: Optional user prompt for context
            sandbox_dir: Working directory for Claude
            
        Returns:
            Analysis result or None
        """
        try:
            # Build analysis prompt
            analysis_prompt = self._build_analysis_prompt(image_paths, user_prompt)
            
            # Build Claude CLI command
            # Use --print to get response and exit
            # Use --allowedTools to enable Read tool for images
            # Note: We don't use --output-format json to get plain text response
            cmd = [
                self.claude_cli_path,
                "--print",
                "--allowedTools", "Read"
            ]
            
            if self.verbose:
                cmd.append("--verbose")
            
            logger.info(f"Running Claude CLI for image analysis: {' '.join(cmd)}")
            logger.debug(f"Prompt: {analysis_prompt[:200]}...")
            
            # Run the command with prompt via stdin
            result = subprocess.run(
                cmd,
                input=analysis_prompt,  # Send prompt via stdin
                capture_output=True,
                text=True,
                cwd=sandbox_dir,
                timeout=90  # 90 second timeout for image analysis
            )
            
            if result.returncode != 0:
                logger.error(f"Claude CLI failed with code {result.returncode}")
                logger.error(f"Stderr: {result.stderr}")
                return None
            
            # Since we're not using JSON format, just return the plain text response
            analysis = result.stdout.strip()
            if analysis:
                logger.info(f"Successfully analyzed images with Claude (plain text, {len(analysis)} chars)")
                logger.debug(f"Analysis preview: {analysis[:200]}...")
                return analysis
            else:
                logger.error("Claude CLI returned empty response")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("Claude CLI timed out during image analysis")
            return None
        except Exception as e:
            logger.error(f"Error running Claude CLI: {e}")
            return None
    
    def _analyze_with_gemini(
        self, 
        image_paths: List[str],
        user_prompt: Optional[str],
        sandbox_dir: str
    ) -> Optional[str]:
        """
        Analyze images using Gemini CLI.
        
        Args:
            image_paths: List of image file paths
            user_prompt: Optional user prompt for context
            sandbox_dir: Working directory for Gemini
            
        Returns:
            Analysis result or None
        """
        try:
            # Build analysis prompt with @ syntax for Gemini
            prompt_parts = []
            
            # Use only filenames since Gemini runs in the sandbox directory
            filenames = [Path(path).name for path in image_paths]
            
            # Add image references using @ syntax with relative filenames
            for filename in filenames:
                prompt_parts.append(f"@{filename}")
            
            # Add analysis request
            if user_prompt:
                prompt_parts.append(f"Analyze these images and answer: {user_prompt}")
            else:
                prompt_parts.append("Please analyze and describe these images in detail.")
            
            analysis_prompt = " ".join(prompt_parts)
            
            # Build Gemini CLI command (no -q flag, use stdin)
            cmd = [
                self.gemini_cli_path
            ]
            
            logger.info(f"Running Gemini CLI for image analysis")
            logger.debug(f"Prompt: {analysis_prompt[:200]}...")
            
            # Run the command with prompt via stdin
            result = subprocess.run(
                cmd,
                input=analysis_prompt,  # Send prompt via stdin
                capture_output=True,
                text=True,
                cwd=sandbox_dir,
                timeout=60  # 60 second timeout
            )
            
            if result.returncode != 0:
                logger.error(f"Gemini CLI failed with code {result.returncode}")
                logger.error(f"Stderr: {result.stderr}")
                return None
            
            analysis = result.stdout.strip()
            if analysis:
                logger.info(f"Successfully analyzed images with Gemini ({len(analysis)} chars)")
                logger.debug(f"Analysis preview: {analysis[:200]}...")
                return analysis
            else:
                logger.warning("Gemini returned empty analysis")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("Gemini CLI timed out during image analysis")
            return None
        except Exception as e:
            logger.error(f"Error running Gemini CLI: {e}")
            return None
    
    def _build_analysis_prompt(
        self, 
        image_paths: List[str],
        user_prompt: Optional[str]
    ) -> str:
        """
        Build the analysis prompt for Claude.
        
        Args:
            image_paths: List of image file paths (absolute paths)
            user_prompt: Optional user prompt
            
        Returns:
            Formatted prompt string
        """
        prompt_parts = []
        
        # Use only filenames since Claude runs in the sandbox directory
        filenames = [Path(path).name for path in image_paths]
        
        # Add image file references using just filenames
        if len(filenames) == 1:
            prompt_parts.append(f"There is an image file named: {filenames[0]}")
        else:
            prompt_parts.append(f"There are {len(filenames)} image files:")
            for i, filename in enumerate(filenames, 1):
                prompt_parts.append(f"  {i}. {filename}")
        
        prompt_parts.append("")
        prompt_parts.append("Use the Read tool to view these image files.")
        
        # Add user's specific request if provided
        if user_prompt:
            prompt_parts.append("")
            prompt_parts.append(f"Analyze the image(s) and answer: {user_prompt}")
        else:
            prompt_parts.append("")
            prompt_parts.append("Analyze and describe what you see in the image(s) in detail.")
        
        return "\n".join(prompt_parts)
    
    def _inject_analysis_context(
        self,
        messages: List[Dict],
        analysis: str,
        image_mappings: Dict[str, str],
        image_placeholders: Dict[str, Optional[str]]
    ) -> List[Dict]:
        """
        Inject image analysis as context into messages.
        
        Args:
            messages: Original messages
            analysis: Image analysis result
            image_mappings: Mapping of image URLs to paths
            image_placeholders: Detected placeholders
            
        Returns:
            Modified messages with analysis context
        """
        # Create a copy of messages
        modified_messages = []
        
        for msg in messages:
            msg_copy = msg.copy()
            
            # If this is a user message with images, modify it
            if msg_copy.get("role") == "user":
                content = msg_copy.get("content", "")
                
                # Check if this message contains images
                has_images = False
                if isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "image_url":
                            has_images = True
                            break
                
                # Also check for placeholders in text
                if isinstance(content, str):
                    for placeholder in image_placeholders:
                        if placeholder in content:
                            has_images = True
                            break
                elif isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            text = part.get("text", "")
                            for placeholder in image_placeholders:
                                if placeholder in text:
                                    has_images = True
                                    break
                
                if has_images:
                    # Convert content to text only, removing image parts
                    new_content = self._extract_text_content(content)
                    
                    # Add analysis context
                    analysis_context = f"\n\n[Image Analysis Context: {analysis}]\n\n"
                    
                    if isinstance(new_content, str):
                        msg_copy["content"] = new_content + analysis_context
                    else:
                        # Should not happen, but handle list case
                        msg_copy["content"] = str(new_content) + analysis_context
            
            modified_messages.append(msg_copy)
        
        return modified_messages
    
    def _extract_text_content(self, content: Any) -> str:
        """
        Extract only text content from a message, removing images.
        
        Args:
            content: Message content (string or list)
            
        Returns:
            Text-only content as string
        """
        if isinstance(content, str):
            return content
        
        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                elif isinstance(part, str):
                    text_parts.append(part)
            return " ".join(text_parts)
        
        return str(content)