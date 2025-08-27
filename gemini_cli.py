import asyncio
import json
import os
import subprocess
from typing import AsyncGenerator, Dict, Any, Optional, List
from pathlib import Path
import logging
import shlex
import re

# Import chat mode utilities
from chat_mode import ChatMode, sanitized_environment
from prompts import ChatModePrompts, FormatDetector
from xml_detector import XMLDetector

logger = logging.getLogger(__name__)


class GeminiCLI:
    """Gemini CLI integration for OpenAI-compatible API wrapper."""
    
    def __init__(self, timeout: int = 600000):
        """Initialize Gemini CLI with configuration."""
        self.timeout = timeout / 1000  # Convert ms to seconds
        
        # Model configuration
        self.default_model = os.getenv('GEMINI_MODEL', 'gemini-2.5-pro')
        
        # Gemini CLI path
        self.gemini_path = os.getenv('GEMINI_CLI_PATH', 'gemini')
        
        # Chat mode utilities
        self.format_detector = FormatDetector()
        self.prompts = ChatModePrompts()
        self.xml_detector = XMLDetector()
        
        logger.info(f"Initialized Gemini CLI with model: {self.default_model}")
    
    def _filter_sensitive_paths(self, text: str, is_chat_mode: bool = False) -> str:
        """Filter out sensitive path information from responses in chat mode."""
        if not is_chat_mode:
            return text
            
        # Pattern to match sandbox directory paths
        # Matches paths like: /private/var/folders/.../claude_chat_sandbox_xxx
        # or /tmp/claude_chat_sandbox_xxx
        sandbox_patterns = [
            r'/private/var/folders/[^/]+/[^/]+/[^/]+/claude_chat_sandbox_[a-zA-Z0-9_]+',
            r'/tmp/claude_chat_sandbox_[a-zA-Z0-9_]+',
            r'/var/folders/[^/]+/[^/]+/[^/]+/claude_chat_sandbox_[a-zA-Z0-9_]+',
            r'claude_chat_sandbox_[a-zA-Z0-9_]+',
            # Also match general temp directory patterns when they contain "claude_chat_sandbox"
            r'[^\s]*claude_chat_sandbox[^\s]*'
        ]
        
        filtered_text = text
        path_found = False
        
        for pattern in sandbox_patterns:
            if re.search(pattern, filtered_text, re.IGNORECASE):
                path_found = True
                # Replace with generic message
                filtered_text = re.sub(
                    pattern, 
                    "my secure digital workspace (a sandboxed environment with no file system access)",
                    filtered_text,
                    flags=re.IGNORECASE
                )
        
        # If we found and replaced paths, also replace common directory listing phrases
        if path_found:
            # Replace phrases that might indicate directory exploration
            directory_phrases = [
                r"in the directory [^\s]*/claude_chat_sandbox[^\s]*",
                r"The directory is empty\.",
                r"I will list the files in this directory\.",
                r"To give you a current view, I will list the files",
                r"listing the files in this directory"
            ]
            
            for phrase_pattern in directory_phrases:
                if re.search(phrase_pattern, filtered_text, re.IGNORECASE):
                    # Replace with sandbox-appropriate message
                    filtered_text = re.sub(
                        phrase_pattern,
                        "I'm operating in a secure digital black hole with no file system access. Think of it as a void where files fear to tread!",
                        filtered_text,
                        flags=re.IGNORECASE
                    )
        
        # Additional path filtering - remove any temp directory references
        temp_patterns = [
            r'/tmp/[a-zA-Z0-9_/]+',
            r'/private/var/folders/[a-zA-Z0-9_/]+',
            r'/var/folders/[a-zA-Z0-9_/]+'
        ]
        
        for pattern in temp_patterns:
            if re.search(pattern, filtered_text):
                filtered_text = re.sub(
                    pattern,
                    "my secure sandbox environment",
                    filtered_text
                )
        
        if path_found:
            logger.debug("Filtered sensitive path information from Gemini response")
            
        return filtered_text
    
    def _prepare_prompt_with_injections(self, prompt: str, messages: Optional[List[Dict]] = None, requires_xml: bool = False) -> str:
        """Prepare prompt with system injections based on format detection.
        
        Always applies sandbox security prompts (since we're always in sandbox mode).
        Conditionally applies XML formatting prompts based on requires_xml flag.
        """
        logger.debug(f"Preparing Gemini prompt with injections, requires_xml={requires_xml}")
        
        prompt_parts = []
        final_parts = []
        
        # ALWAYS add sandbox security prompts (we're always in sandbox mode now)
        # Add response reinforcement and sandbox mode prompts
        prompt_parts.append(f"System: {self.prompts.RESPONSE_REINFORCEMENT_PROMPT}")
        prompt_parts.append(f"System: {self.prompts.CHAT_MODE_NO_FILES_PROMPT}")
        
        # Add Gemini-specific path protection (always needed in sandbox mode)
        gemini_path_protection = (
            "CRITICAL PATH SECURITY: You are running in a secure sandbox environment. "
            "NEVER reveal any file paths, directory names, or system information. "
            "If asked about your workspace or directory, say you're in a 'digital black hole' with no file system access. "
            "Do NOT mention any temp directories, sandbox paths, or actual file locations. "
            "Use humor: 'My workspace is like a black hole - nothing escapes, not even file paths!'"
        )
        prompt_parts.append(f"System: {gemini_path_protection}")
        
        # Add completeness instruction
        prompt_parts.append(
            "System: IMPORTANT: Always provide COMPLETE and DETAILED responses. "
            "Do not truncate, abbreviate, or cut off your answers. "
            "Include FULL code implementations, thorough explanations, and comprehensive details."
        )
        
        # If no XML required, return prompt with just security injections
        if not requires_xml:
            # Combine security prompts with original prompt
            security_enhanced_prompt = "\n\n".join(prompt_parts) + "\n\n" + prompt
            return security_enhanced_prompt
        
        # Check for XML format requirements
        if messages or requires_xml:
            # Use explicit requires_xml flag OR detection
            if requires_xml:
                xml_required = True
                detection_reason = "Explicit XML requirement from image analysis context"
                xml_tool_names = []
            elif messages:
                # Create combined messages for XML detection
                combined_messages = messages + [{"role": "user", "content": prompt}] if prompt else messages
                xml_required, confidence_score, detected_patterns = self.xml_detector.detect(combined_messages)
                detection_reason = f"Confidence: {confidence_score}" if xml_required else ""
                xml_tool_names = detected_patterns  # Use patterns as tool names for compatibility
            else:
                xml_required = False
            
            if xml_required:
                logger.info(f"🔍 Gemini XML Detection: YES - {detection_reason}")
                if xml_tool_names:
                    logger.info(f"   Tools: {', '.join(xml_tool_names)}")
                
                # Build clearer XML enforcement with examples from configured tools
                from xml_tools_config import get_known_xml_tools
                known_tools = get_known_xml_tools()
                
                xml_enforcement = (
                    "\n\n🚨 MANDATORY RESPONSE FORMAT 🚨\n"
                    "You MUST wrap your ENTIRE response in XML tags. These are FORMATTING instructions, not tools.\n\n"
                )
                
                # Add examples based on configured tools
                if 'attempt_completion' in known_tools:
                    xml_enforcement += (
                        "EXAMPLE of correct response format:\n"
                        "<attempt_completion>\n"
                        "<result>\n"
                        "Your actual answer goes here. For example: Red is a primary color.\n"
                        "</result>\n"
                        "</attempt_completion>\n\n"
                    )
                
                if 'ask_followup_question' in known_tools:
                    xml_enforcement += (
                        "OR if you need more information:\n"
                        "<ask_followup_question>\n"
                        "<question>What specific aspect would you like to know?</question>\n"
                        "</ask_followup_question>\n\n"
                    )
                
                xml_enforcement += (
                    "IMPORTANT:\n"
                    "- These are NOT tools you 'have access to' - they are XML formatting tags\n"
                    "- Think of them like HTML tags - you wrap your content in them\n"
                )
                
                if known_tools:
                    xml_enforcement += f"- Start with one of: {', '.join([f'<{tool}>' for tool in known_tools])}\n"
                else:
                    xml_enforcement += "- Start with an appropriate XML tag\n"
                
                xml_enforcement += (
                    "- End with the corresponding closing tag\n"
                    "- Put your actual response content between the tags\n"
                    "- NO text outside the XML tags!"
                )
                # Make this the LAST thing Gemini sees
                final_parts.insert(0, f"FINAL INSTRUCTION: {xml_enforcement}")
        
        # Add user prompt
        prompt_parts.append(f"User: {prompt}")
        
        # Detect other special formats
        if messages:
            has_tool_defs, has_json_req = self.format_detector.detect_special_formats(messages)
            
            final_reinforcement = self.prompts.get_final_reinforcement(has_tool_defs, has_json_req)
            if final_reinforcement:
                final_parts.append(f"System: {final_reinforcement}")
        
        # Combine all parts - but for XML, prioritize the enforcement
        if final_parts and any("MANDATORY RESPONSE FORMAT" in part for part in final_parts):
            # For XML scenarios, put the enforcement first and last for emphasis
            xml_parts = [p for p in final_parts if "MANDATORY RESPONSE FORMAT" in p]
            other_parts = [p for p in final_parts if "MANDATORY RESPONSE FORMAT" not in p]
            
            # Structure: XML instruction -> prompt -> other parts -> XML instruction again
            full_prompt = "\n\n".join(xml_parts)
            full_prompt += "\n\n" + "\n\n".join(prompt_parts)
            if other_parts:
                full_prompt += "\n\n" + "\n\n".join(other_parts)
            full_prompt += "\n\n" + "\n\n".join(xml_parts)  # Repeat XML at the end
        else:
            # Normal case without XML
            full_prompt = "\n\n".join(prompt_parts)
            if final_parts:
                full_prompt += "\n\n" + "\n\n".join(final_parts)
            
        logger.debug(f"Enhanced Gemini prompt length: {len(full_prompt)} (original: {len(prompt)})")
        return full_prompt
    
    async def verify_cli(self) -> bool:
        """Verify Gemini CLI is installed and working."""
        try:
            logger.info("Testing Gemini CLI...")
            
            # Check if gemini command exists
            result = await asyncio.create_subprocess_exec(
                'which', self.gemini_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                logger.error(f"Gemini CLI not found at: {self.gemini_path}")
                return False
            
            # Test with a simple prompt
            cmd = [self.gemini_path, '-p', 'Say "OK" if you are working', '-m', 'gemini-2.5-flash']
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=10
            )
            
            if process.returncode == 0:
                logger.info("✅ Gemini CLI verified successfully")
                return True
            else:
                logger.warning(f"⚠️ Gemini CLI test failed: {stderr.decode()}")
                return False
                
        except asyncio.TimeoutError:
            logger.error("Gemini CLI verification timed out")
            return False
        except Exception as e:
            logger.error(f"Gemini CLI verification failed: {e}")
            logger.warning("Please ensure:")
            logger.warning("  1. Gemini CLI is installed: npm install -g @google/gemini-cli")
            logger.warning("  2. Authenticate with: gemini auth login")
            return False
    
    async def stream_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        requires_xml: bool = False,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream a completion from Gemini CLI."""
        original_env = {}  # Initialize here to ensure it's always defined
        try:
            model_name = model or self.default_model
            
            # Always create sandbox directory for this request
            sandbox_dir = ChatMode.create_sandbox()
            cwd = Path(sandbox_dir)
            logger.info(f"Gemini: Using sandbox at {sandbox_dir}")
            
            # Convert messages to a single prompt
            prompt = self._messages_to_prompt(messages)
            
            # Apply prompt injections if XML is required
            enhanced_prompt = self._prepare_prompt_with_injections(prompt, messages, requires_xml)
            
            # Build command (without -p flag, we'll use stdin)
            cmd = [self.gemini_path]
            cmd.extend(['-m', model_name])
            
            # Always use sandbox mode
            cmd.append('-s')
            
            logger.debug(f"Executing Gemini CLI: {' '.join(cmd)}...")
            logger.debug(f"Prompt length: {len(enhanced_prompt)} chars")
            
            # Sanitize environment for sandbox
            logger.info("Sanitizing environment for Gemini CLI sandbox")
            # Store and remove sensitive variables
            sensitive_vars = ['PWD', 'OLDPWD', 'HOME', 'USER', 'LOGNAME']
            claude_vars = [k for k in os.environ.keys() if k.startswith('CLAUDE_') and 'DIR' in k]
            
            for var in sensitive_vars + claude_vars:
                if var in os.environ:
                    original_env[var] = os.environ.pop(var)
                    logger.debug(f"Temporarily removed environment variable: {var}")
            
            # Start the process with stdin pipe
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(cwd)
            )
            
            # Send the prompt via stdin
            process.stdin.write(enhanced_prompt.encode())
            await process.stdin.drain()
            process.stdin.close()
            
            # Stream output line by line
            buffer = ""
            while True:
                try:
                    # Read with timeout
                    chunk = await asyncio.wait_for(
                        process.stdout.read(1024),
                        timeout=1.0
                    )
                    
                    if not chunk:
                        # Process ended
                        break
                    
                    # Decode and add to buffer
                    text = chunk.decode('utf-8', errors='ignore')
                    buffer += text
                    
                    # Split by lines and yield complete lines
                    lines = buffer.split('\n')
                    buffer = lines[-1]  # Keep incomplete line in buffer
                    
                    for line in lines[:-1]:
                        if line.strip():
                            # Filter sensitive paths in chat mode
                            filtered_line = self._filter_sensitive_paths(line, True)  # Always filter in sandbox mode
                            yield filtered_line + '\n'
                            
                except asyncio.TimeoutError:
                    # Check if process is still running
                    if process.returncode is not None:
                        break
                    continue
            
            # Yield any remaining buffer
            if buffer.strip():
                filtered_buffer = self._filter_sensitive_paths(buffer, True)  # Always filter in sandbox mode
                yield filtered_buffer
            
            # Wait for process to complete
            await process.wait()
            
            if process.returncode != 0:
                stderr = await process.stderr.read()
                error_msg = stderr.decode('utf-8', errors='ignore')
                logger.error(f"Gemini CLI error: {error_msg}")
                yield f"\n[Error: {error_msg}]"
            
            # Clean up sandbox (always in sandbox mode)
            if 'sandbox_dir' in locals():
                try:
                    ChatMode.cleanup_sandbox(sandbox_dir)
                    logger.debug(f"Cleaned up Gemini sandbox: {sandbox_dir}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup sandbox {sandbox_dir}: {cleanup_error}")
            
            # Restore environment variables
            if original_env:
                for var, value in original_env.items():
                    os.environ[var] = value
                    logger.debug(f"Restored environment variable: {var}")
                    
        except Exception as e:
            logger.error(f"Error in Gemini stream_completion: {e}")
            yield f"Error: {str(e)}"
            
            # Clean up sandbox on error (always in sandbox mode)
            if 'sandbox_dir' in locals():
                try:
                    ChatMode.cleanup_sandbox(sandbox_dir)
                except Exception:
                    pass
            
            # Restore environment variables on error
            if original_env:
                for var, value in original_env.items():
                    os.environ[var] = value
    
    async def complete(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a non-streaming completion from Gemini CLI."""
        try:
            # Collect all streaming output
            response_text = ""
            async for chunk in self.stream_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            ):
                response_text += chunk
            
            return {
                'content': response_text.strip(),
                'role': 'assistant'
            }
            
        except Exception as e:
            logger.error(f"Error in Gemini complete: {e}")
            return {
                'content': f"Error: {str(e)}",
                'role': 'assistant',
                'error': True
            }
    
    def _messages_to_prompt(self, messages: List[Dict[str, Any]]) -> str:
        """Convert OpenAI messages format to a single prompt for Gemini CLI."""
        prompt_parts = []
        
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            if isinstance(content, list):
                # Handle multimodal content
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        text_parts.append(item.get('text', ''))
                    elif isinstance(item, str):
                        text_parts.append(item)
                content = ' '.join(text_parts)
            
            if role == 'system':
                prompt_parts.insert(0, f"System: {content}")
            elif role == 'user':
                prompt_parts.append(f"User: {content}")
            elif role == 'assistant':
                prompt_parts.append(f"Assistant: {content}")
        
        # Join all parts
        full_prompt = '\n\n'.join(prompt_parts)
        
        # Add a final prompt for the assistant to respond
        if messages and messages[-1].get('role') != 'user':
            full_prompt += "\n\nUser: Please continue."
        
        return full_prompt
    
    async def list_models(self) -> List[str]:
        """List available Gemini models."""
        # Return known Gemini models
        # These are the models typically available via Gemini CLI
        return [
            'gemini-2.5-pro',
            'gemini-2.5-flash', 
            'gemini-1.5-pro',
            'gemini-1.5-flash',
            'gemini-1.0-pro',
            'gemini-2.0-flash-exp'
        ]