import asyncio
import json
import os
import subprocess
from typing import AsyncGenerator, Dict, Any, Optional, List
from pathlib import Path
import logging
import shlex

logger = logging.getLogger(__name__)


class GeminiCLI:
    """Gemini CLI integration for OpenAI-compatible API wrapper."""
    
    def __init__(self, timeout: int = 600000, cwd: Optional[str] = None):
        """Initialize Gemini CLI with configuration."""
        self.timeout = timeout / 1000  # Convert ms to seconds
        self.cwd = Path(cwd) if cwd else Path.cwd()
        
        # Model configuration
        self.default_model = os.getenv('GEMINI_MODEL', 'gemini-2.5-pro')
        self.enable_sandbox = os.getenv('GEMINI_SANDBOX', 'false').lower() == 'true'
        self.yolo_mode = os.getenv('GEMINI_YOLO', 'false').lower() == 'true'
        
        # Gemini CLI path
        self.gemini_path = os.getenv('GEMINI_CLI_PATH', 'gemini')
        
        logger.info(f"Initialized Gemini CLI with model: {self.default_model}")
    
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
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.cwd)
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
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream a completion from Gemini CLI."""
        try:
            model_name = model or self.default_model
            
            # Convert messages to a single prompt
            prompt = self._messages_to_prompt(messages)
            
            # Build command
            cmd = [self.gemini_path]
            cmd.extend(['-m', model_name])
            cmd.extend(['-p', prompt])
            
            if self.enable_sandbox:
                cmd.append('-s')
            
            if self.yolo_mode:
                cmd.append('-y')
            
            logger.debug(f"Executing Gemini CLI: {' '.join(cmd[:4])}...")  # Log partial command
            
            # Start the process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.cwd)
            )
            
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
                            yield line + '\n'
                            
                except asyncio.TimeoutError:
                    # Check if process is still running
                    if process.returncode is not None:
                        break
                    continue
            
            # Yield any remaining buffer
            if buffer.strip():
                yield buffer
            
            # Wait for process to complete
            await process.wait()
            
            if process.returncode != 0:
                stderr = await process.stderr.read()
                error_msg = stderr.decode('utf-8', errors='ignore')
                logger.error(f"Gemini CLI error: {error_msg}")
                yield f"\n[Error: {error_msg}]"
                
        except Exception as e:
            logger.error(f"Error in Gemini stream_completion: {e}")
            yield f"Error: {str(e)}"
    
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