import asyncio
import json
import os
import subprocess
from typing import AsyncGenerator, Dict, Any, Optional, List
from pathlib import Path
import logging
import shlex
import re
import asyncio

# Import chat mode utilities
from chat_mode import ChatMode, sanitized_environment
from prompts import ChatModePrompts, FormatDetector
from xml_detector import XMLDetector

logger = logging.getLogger(__name__)


class QwenCLI:
    """Qwen CLI integration for OpenAI-compatible API wrapper."""
    
    def __init__(self, timeout: int = 600000):
        """Initialize Qwen CLI with configuration."""
        self.timeout = timeout / 1000  # Convert ms to seconds
        
        # Model configuration
        self.default_model = os.getenv('QWEN_MODEL', 'qwen3-coder-plus')
        
        # Qwen CLI path
        self.qwen_path = os.getenv('QWEN_CLI_PATH', 'qwen')
        
        # Chat mode utilities
        self.format_detector = FormatDetector()
        self.prompts = ChatModePrompts()
        self.xml_detector = XMLDetector()
        
        logger.info(f"Initialized Qwen CLI with model: {self.default_model}")
    
    
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
            logger.debug("Filtered sensitive path information from Qwen response")
            
        return filtered_text
    
    def _has_image_analysis_context(self, messages: Optional[List[Dict]]) -> bool:
        """Check if messages contain image analysis context.
        
        This indicates that images have already been processed by the
        ImageAnalysisOrchestrator and we should use relaxed security prompts.
        """
        if not messages:
            return False
        
        for msg in messages:
            content = msg.get('content', '')
            # Check for the specific marker used by ImageAnalysisOrchestrator
            if '[Image Analysis Context:' in str(content):
                logger.debug("Found image analysis context marker in messages")
                return True
            # Also check role=system messages that might contain analysis
            if msg.get('role') == 'system' and 'image analysis' in str(content).lower():
                logger.debug("Found image analysis in system message")
                return True
        
        return False
    
    def _prepare_prompt_with_injections(self, prompt: str, messages: Optional[List[Dict]] = None, requires_xml: bool = False) -> str:
        """Prepare prompt with system injections based on format detection.
        
        Always applies sandbox security prompts (since we're always in sandbox mode).
        Conditionally applies XML formatting prompts based on requires_xml flag.
        Special handling for image analysis context to allow appropriate responses.
        """
        logger.debug(f"Preparing Qwen prompt with injections, requires_xml={requires_xml}")
        
        # Check for image analysis context in messages
        has_image_context = self._has_image_analysis_context(messages)
        if has_image_context:
            logger.info("Detected image analysis context in messages, using modified security prompts")
        
        prompt_parts = []
        final_parts = []
        
        # Add response reinforcement (always needed)
        prompt_parts.append(f"System: {self.prompts.RESPONSE_REINFORCEMENT_PROMPT}")
        
        # Conditional security based on image analysis context
        if has_image_context:
            # Modified security for post-image-analysis - allow discussing analyzed content
            prompt_parts.append(
                "System: You are responding based on analyzed image content. "
                "You may discuss the image analysis results naturally. "
                "Do not reveal system paths or directory structures."
            )
        else:
            # Full security prompts for non-image operations
            prompt_parts.append(f"System: {self.prompts.CHAT_MODE_NO_FILES_PROMPT}")
            
            # Add Qwen-specific path protection (for non-image operations)
            qwen_path_protection = (
                "CRITICAL PATH SECURITY: You are running in a secure sandbox environment. "
                "NEVER reveal any file paths, directory names, or system information. "
                "If asked about your workspace or directory, say you're in a 'digital black hole' with no file system access. "
                "Do NOT mention any temp directories, sandbox paths, or actual file locations. "
                "Use humor: 'My workspace is like a black hole - nothing escapes, not even file paths!'"
            )
            prompt_parts.append(f"System: {qwen_path_protection}")
        
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
                xml_tool_names = detected_patterns.get('tool_names', []) if detected_patterns else []
            else:
                xml_required = False
                detection_reason = ""
                xml_tool_names = []
            
            if xml_required:
                logger.info(f"XML format enforcement triggered for Qwen. {detection_reason}")
                if xml_tool_names:
                    logger.debug(f"Detected XML tools: {xml_tool_names}")
                
                # Build XML enforcement similar to Gemini
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
                        "Your actual answer goes here.\n"
                        "</result>\n"
                        "</attempt_completion>\n\n"
                    )
                
                if 'ask_followup_question' in known_tools:
                    xml_enforcement += (
                        "If you need more information:\n"
                        "<ask_followup_question>\n"
                        "<question>\n"
                        "Your question here\n"
                        "</question>\n"
                        "</ask_followup_question>\n\n"
                    )
                
                xml_enforcement += (
                    "⚠️ CRITICAL: Your ENTIRE response must be wrapped in ONE of these XML tag structures.\n"
                    "Do NOT mix plain text with XML. Do NOT use multiple root tags.\n"
                )
                
                prompt_parts.append(xml_enforcement)
        
        # Combine all parts
        full_prompt = "\n\n".join(prompt_parts)
        if prompt:
            full_prompt += "\n\n" + prompt
        if final_parts:
            full_prompt += "\n\n" + "\n\n".join(final_parts)
        
        return full_prompt
    
    def _messages_to_prompt(self, messages: List[Dict[str, Any]]) -> str:
        """Convert OpenAI-style messages to a single prompt for Qwen."""
        prompt_parts = []
        
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            # Handle different content types
            if isinstance(content, list):
                # For multimodal messages, extract text parts
                text_parts = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get('type') == 'text':
                            text_parts.append(item.get('text', ''))
                    else:
                        text_parts.append(str(item))
                content = ' '.join(text_parts)
            
            # Format message based on role
            if role == 'system':
                prompt_parts.append(f"System: {content}")
            elif role == 'assistant':
                prompt_parts.append(f"Assistant: {content}")
            elif role == 'user':
                prompt_parts.append(f"User: {content}")
            else:
                # For any other role, just include the content
                prompt_parts.append(content)
        
        # Join all parts with double newlines for clarity
        return "\n\n".join(prompt_parts)
    
    async def stream_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        requires_xml: bool = False,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream a completion from Qwen CLI."""
        original_env = {}  # Initialize here to ensure it's always defined
        try:
            # Handle model selection - if 'auto', don't specify any model
            if model == 'auto':
                model_args = []  # Let Qwen CLI choose default
                logger.info("Using auto model selection (Qwen CLI default)")
            else:
                model_name = model or self.default_model
                model_args = ['-m', model_name]
            
            # Always create sandbox directory for this request
            sandbox_dir = ChatMode.create_sandbox()
            cwd = Path(sandbox_dir)
            logger.info(f"Qwen: Using sandbox at {sandbox_dir}")
            
            # Convert messages to a single prompt
            prompt = self._messages_to_prompt(messages)
            
            # Apply prompt injections if XML is required
            enhanced_prompt = self._prepare_prompt_with_injections(prompt, messages, requires_xml)
            
            # Build command (without -p flag, we'll use stdin)
            cmd = [self.qwen_path]
            if model_args:
                cmd.extend(model_args)
            
            # Always use sandbox mode
            cmd.append('-s')
            
            logger.debug(f"Executing Qwen CLI: {' '.join(cmd)}...")
            logger.debug(f"Prompt length: {len(enhanced_prompt)} chars")
            
            # Sanitize environment for sandbox
            logger.info("Sanitizing environment for Qwen CLI sandbox")
            # Store and remove sensitive variables
            sensitive_vars = ['PWD', 'OLDPWD', 'HOME', 'USER', 'LOGNAME']
            claude_vars = [k for k in os.environ.keys() if k.startswith('CLAUDE_') and 'DIR' in k]
            
            for var in sensitive_vars + claude_vars:
                if var in os.environ:
                    original_env[var] = os.environ.pop(var)
                    logger.debug(f"Temporarily removed environment variable: {var}")
            
            # Explicitly disable debug mode to suppress debug output
            os.environ['DEBUG'] = 'false'
            os.environ['DEBUG_MODE'] = 'false'
            os.environ['VERBOSE'] = 'false'
            os.environ['NO_COLOR'] = '1'  # Suppress colored output
            
            # Start the process with stdin pipe
            # Note: We capture both stdout and stderr separately
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,  # Capture stderr separately
                cwd=str(cwd)
            )
            
            # Send the prompt via stdin
            process.stdin.write(enhanced_prompt.encode())
            await process.stdin.drain()
            process.stdin.close()
            
            # Create a task to consume stderr (to prevent blocking)
            async def consume_stderr():
                while True:
                    try:
                        chunk = await process.stderr.read(1024)
                        if not chunk:
                            break
                        # Log stderr for debugging but don't yield it
                        stderr_text = chunk.decode('utf-8', errors='ignore')
                        if stderr_text.strip():
                            logger.debug(f"Qwen stderr: {stderr_text.strip()}")
                    except:
                        break
            
            stderr_task = asyncio.create_task(consume_stderr())
            
            # Stream output with minimal buffering for smooth token-by-token delivery
            buffer = ""
            started_response = False  # Track if we've seen actual response content
            auth_filtering_done = False  # Track if we've passed initial auth messages
            
            auth_message_patterns = [
                r"Loaded cached [Qq]wen credentials",
                r"Loading [Qq]wen credentials",
                r"Authenticating with [Qq]wen",
                r"\[DEBUG\]",
                r"\[MemoryDiscovery\]",
                r"Flushing log events",
                r"CLI: Delegating",
                # Device authorization patterns
                r"Device authorization result:",
                r"device_code:",
                r"user_code:",
                r"verification_uri",
                r"expires_in:",
                r"Waiting for authorization",
                r"polling for token",
                r"^\.",  # Dots from polling
                r"^\.polling",  # Polling messages starting with dot
                r"Please visit.*authorize",
                r"Enter code:",
                # JSON auth response patterns
                r"^\s*['\"]device_code['\"]",
                r"^\s*['\"]user_code['\"]",
                r"^\s*['\"]verification_uri",
                r"^\s*['\"]expires_in['\"]",
                r"^}$",  # Closing brace of JSON objects
                r"^{$",  # Opening brace of JSON objects
                # URLs and codes
                r"https://chat\.qwen\.ai/authorize",
                r"^[A-Z0-9]{8}-[A-Z0-9]{4}$",  # User code pattern like Y59HWLGM
                # Success messages
                r"Authentication successful",
                r"Access token obtained"
            ]
            
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
                    
                    # Decode chunk
                    text = chunk.decode('utf-8', errors='ignore')
                    
                    # If we haven't started the response yet, we need to filter auth messages
                    if not auth_filtering_done:
                        buffer += text
                        
                        # Check if buffer contains complete lines to analyze for auth
                        if '\n' in buffer:
                            lines = buffer.split('\n')
                            buffer = lines[-1]  # Keep incomplete line
                            
                            for line in lines[:-1]:
                                if line.strip():
                                    is_auth = False
                                    line_stripped = line.strip()
                                    
                                    # Check for auth patterns
                                    for pattern in auth_message_patterns:
                                        if re.search(pattern, line, re.IGNORECASE):
                                            is_auth = True
                                            logger.debug(f"Filtering auth: {line_stripped[:50]}")
                                            break
                                    
                                    # Check for JSON auth patterns
                                    if not is_auth and (
                                        line_stripped in ['{', '}'] or
                                        line_stripped.startswith('"device_code"') or
                                        line_stripped.startswith('"user_code"') or
                                        line_stripped.startswith('"verification_uri') or
                                        line_stripped.startswith('"expires_in"') or
                                        line_stripped == '.'
                                    ):
                                        is_auth = True
                                        logger.debug(f"Filtering auth JSON: {line_stripped[:30]}")
                                    
                                    if not is_auth:
                                        # Found first non-auth content
                                        auth_filtering_done = True
                                        started_response = True
                                        # Yield this line
                                        filtered = self._filter_sensitive_paths(line, True)
                                        yield filtered + '\n'
                        
                        # If buffer gets too large without newlines, assume no more auth
                        elif len(buffer) > 500:
                            auth_filtering_done = True
                            started_response = True
                            # Yield accumulated buffer
                            filtered = self._filter_sensitive_paths(buffer, True)
                            yield filtered
                            buffer = ""
                    else:
                        # Auth filtering done - stream everything immediately
                        started_response = True
                        # Filter and yield chunk immediately for smooth streaming
                        filtered_chunk = self._filter_sensitive_paths(text, True)
                        yield filtered_chunk
                            
                except asyncio.TimeoutError:
                    # Check if process is still running
                    if process.returncode is not None:
                        break
                    continue
            
            # Yield any remaining buffer
            if buffer.strip() and started_response:
                # Only yield if we've started the actual response
                filtered_buffer = self._filter_sensitive_paths(buffer, True)
                yield filtered_buffer
            
            # Cancel stderr consumer task
            stderr_task.cancel()
            try:
                await stderr_task
            except asyncio.CancelledError:
                pass
            
            # Wait for process to complete
            await process.wait()
            
            if process.returncode != 0:
                # Get any remaining stderr for error reporting
                stderr_output = await process.stderr.read()
                error_msg = stderr_output.decode('utf-8', errors='ignore').strip()
                if error_msg:
                    logger.error(f"Qwen CLI error: {error_msg}")
                    yield f"\n[Error: {error_msg}]"
                else:
                    logger.error(f"Qwen CLI exited with code {process.returncode}")
                    yield f"\n[Error: Qwen CLI exited with code {process.returncode}]"
            
            # Clean up sandbox (always in sandbox mode)
            if 'sandbox_dir' in locals():
                try:
                    ChatMode.cleanup_sandbox(sandbox_dir)
                    logger.debug(f"Cleaned up Qwen sandbox: {sandbox_dir}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup sandbox {sandbox_dir}: {cleanup_error}")
            
            # Restore environment variables
            if original_env:
                for var, value in original_env.items():
                    os.environ[var] = value
                    logger.debug(f"Restored environment variable: {var}")
            
            # Clean up debug mode variables we added
            for var in ['DEBUG', 'DEBUG_MODE', 'VERBOSE', 'NO_COLOR']:
                if var not in original_env and var in os.environ:
                    del os.environ[var]
                    
        except Exception as e:
            logger.error(f"Error in Qwen stream_completion: {e}")
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
            
            # Clean up debug mode variables we added
            for var in ['DEBUG', 'DEBUG_MODE', 'VERBOSE', 'NO_COLOR']:
                if var not in original_env and var in os.environ:
                    del os.environ[var]
    
    async def list_models(self) -> List[str]:
        """List available Qwen models from environment variable."""
        # Get models from environment variable
        models_str = os.getenv('QWEN_MODELS', '')
        
        # Parse models from env var
        models = []
        if models_str:
            models = [m.strip() for m in models_str.split(',') if m.strip()]
        
        # Always ensure 'auto' is available as a fallback
        if 'auto' not in models:
            models.insert(0, 'auto')  # Add at the beginning
        
        # If no models configured, provide sensible defaults
        if len(models) == 1:  # Only 'auto' is present
            models.extend(['qwen3-coder-plus', 'qwen3-coder', 'qwen3-coder-480b-a35b-instruct'])
        
        return models