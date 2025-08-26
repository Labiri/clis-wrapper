"""
Image handler for processing and caching images in the Claude Code OpenAI wrapper.

This module handles base64 and URL images, saves them to the sandbox directory,
maintains a cache to avoid reprocessing the same images, and supports file-based
image references used by Roo/Cline clients.
"""

import base64
import hashlib
import logging
import os
import re
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Pattern
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

# Image format extensions mapping
MIME_TO_EXT = {
    'image/jpeg': 'jpg',
    'image/jpg': 'jpg',
    'image/png': 'png',
    'image/gif': 'gif',
    'image/webp': 'webp',
    'image/bmp': 'bmp',
    'image/tiff': 'tiff',
}

# Maximum image constraints (from Claude Code docs)
MAX_IMAGE_SIZE = 3.75 * 1024 * 1024  # 3.75 MB
MAX_IMAGE_DIMENSION = 8000  # 8000x8000 px max
MAX_IMAGES_PER_REQUEST = 20


class ImageHandler:
    """Handles image processing, caching, and file management."""
    
    def __init__(self, sandbox_dir: Optional[Path] = None):
        """
        Initialize the image handler.
        
        Args:
            sandbox_dir: Directory to save images. If None, uses temp directory.
                        In chat mode, this MUST be the sandbox directory created for the request.
        """
        self.sandbox_dir = Path(sandbox_dir) if sandbox_dir else Path(tempfile.gettempdir())
        self.image_cache: Dict[str, str] = {}  # cache_key -> file_path
        self.temp_files: List[Path] = []  # Track files for cleanup
        
        # Ensure sandbox directory exists
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"ImageHandler initialized with sandbox_dir: {self.sandbox_dir}")
    
    def _get_new_messages(self, messages: List[Dict]) -> List[Dict]:
        """
        Get only new messages that haven't been processed yet.
        New messages = messages after the last assistant response.
        
        Args:
            messages: List of all message dictionaries
            
        Returns:
            List of new messages to process
        """
        if not messages:
            return []
        
        # Find the index of the last assistant message
        last_assistant_idx = -1
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].get('role') == 'assistant':
                last_assistant_idx = i
                logger.debug(f"Found last assistant message at index {i} (out of {len(messages)} total)")
                break
        
        # Return messages after the last assistant message
        # If no assistant message found, all messages are new
        new_messages = messages[last_assistant_idx + 1:]
        logger.debug(f"Identified {len(new_messages)} new messages to process")
        
        return new_messages
    
    def process_messages_for_images(self, messages: List[Dict]) -> Dict[str, str]:
        """
        Process images only from new messages in the conversation.
        
        Args:
            messages: List of message dictionaries from OpenAI format
            
        Returns:
            Dictionary mapping original image URLs to local file paths
        """
        # Get only new messages to process
        new_messages = self._get_new_messages(messages)
        
        # SPECIAL CASE: If we have NO new user messages with images but the conversation
        # references images (e.g., retry scenario), check ALL user messages for images
        # This handles the case where a client retries and the image is in message history
        new_user_messages = [m for m in new_messages if m.get('role') == 'user']
        
        # Check if new messages have images
        has_new_images = False
        for msg in new_user_messages:
            content = msg.get('content', '')
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get('type') == 'image_url':
                        has_new_images = True
                        break
            if has_new_images:
                break
        
        # If no new images but conversation might reference images, check all user messages
        if not has_new_images and len(messages) > len(new_messages):
            logger.info("No images in new messages, checking entire conversation for retry scenario")
            # Check if ANY user message in the conversation has images
            all_user_messages = [m for m in messages if m.get('role') == 'user']
            for msg in all_user_messages:
                content = msg.get('content', '')
                if isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get('type') == 'image_url':
                            # Found images in history - process ALL user messages
                            logger.info("Found images in conversation history - processing all user messages for retry scenario")
                            new_messages = messages
                            break
        
        # Filter to only user messages (ignore assistant/system/tool messages)
        user_messages = [m for m in new_messages if m.get('role') == 'user']
        
        logger.info(f"Processing images from {len(user_messages)} user messages (out of {len(messages)} total)")
        
        image_mappings = {}
        total_images = 0
        
        # Process only the new user messages
        for msg_idx, message in enumerate(user_messages):
            content = message.get('content', '')
            
            # Handle array content (multimodal messages)
            if isinstance(content, list):
                for part_idx, part in enumerate(content):
                    if isinstance(part, dict) and part.get('type') == 'image_url':
                        if total_images >= MAX_IMAGES_PER_REQUEST:
                            logger.warning(f"Reached maximum image limit ({MAX_IMAGES_PER_REQUEST}), skipping remaining images")
                            return image_mappings
                        
                        image_url_obj = part.get('image_url', {})
                        url = image_url_obj.get('url', '')
                        
                        if url:
                            try:
                                # Get cache key for this image
                                cache_key = self._get_cache_key(url)
                                
                                # Check if already processed
                                if cache_key in self.image_cache:
                                    file_path = self.image_cache[cache_key]
                                    # Verify file still exists (important for sandbox isolation)
                                    if Path(file_path).exists():
                                        image_mappings[url] = file_path
                                        logger.debug(f"Using cached image: {cache_key[:8]}... -> {file_path}")
                                    else:
                                        # File was cleaned up, reprocess
                                        logger.debug(f"Cached file missing, reprocessing: {cache_key[:8]}...")
                                        file_path = self._process_single_image(url)
                                        if file_path:
                                            self.image_cache[cache_key] = file_path
                                            image_mappings[url] = file_path
                                            total_images += 1
                                else:
                                    # Process new image
                                    file_path = self._process_single_image(url)
                                    if file_path:
                                        self.image_cache[cache_key] = file_path
                                        image_mappings[url] = file_path
                                        total_images += 1
                                        logger.info(f"Processed new image {total_images}/{MAX_IMAGES_PER_REQUEST}: {cache_key[:8]}...")
                                        
                            except Exception as e:
                                logger.error(f"Failed to process image in message {msg_idx}, part {part_idx}: {e}")
                                continue
        
        logger.info(f"Processed {len(image_mappings)} unique images from {len(messages)} messages")
        return image_mappings
    
    def _get_cache_key(self, url: str) -> str:
        """
        Generate a cache key from URL or base64 data.
        
        Args:
            url: Image URL or base64 data URL
            
        Returns:
            MD5 hash as cache key
        """
        if url.startswith('data:'):
            # For base64, hash a portion of the data (not the entire thing for performance)
            # Extract the base64 data part
            if ',' in url:
                data_part = url.split(',', 1)[1][:500]  # First 500 chars of base64
            else:
                data_part = url[:500]
            return hashlib.md5(data_part.encode()).hexdigest()
        else:
            # For URLs, hash the full URL
            return hashlib.md5(url.encode()).hexdigest()
    
    def _process_single_image(self, image_url: str) -> Optional[str]:
        """
        Process a single image URL (base64 or HTTP) and save to sandbox.
        
        Args:
            image_url: Image URL or base64 data URL
            
        Returns:
            Path to saved image file, or None if processing failed
        """
        try:
            if image_url.startswith('data:'):
                return self._save_base64_image(image_url)
            elif image_url.startswith(('http://', 'https://')):
                return self._download_and_save_image(image_url)
            else:
                logger.error(f"Unsupported image URL format: {image_url[:50]}...")
                return None
        except Exception as e:
            logger.error(f"Failed to process image: {e}")
            return None
    
    def _save_base64_image(self, data_url: str) -> Optional[str]:
        """
        Extract and save base64 encoded image to sandbox.
        
        Args:
            data_url: Base64 data URL (e.g., "data:image/jpeg;base64,...")
            
        Returns:
            Path to saved image file
        """
        try:
            # Parse data URL format: data:[<mediatype>][;base64],<data>
            if ',' not in data_url:
                logger.error("Invalid data URL format: missing comma separator")
                return None
            
            header, data = data_url.split(',', 1)
            
            # Extract MIME type
            mime_match = re.match(r'data:([^;]+)', header)
            if mime_match:
                mime_type = mime_match.group(1)
                ext = MIME_TO_EXT.get(mime_type, 'jpg')  # Default to jpg
            else:
                ext = 'jpg'
                logger.warning("Could not determine MIME type from data URL, using jpg")
            
            # Decode base64 data
            try:
                image_data = base64.b64decode(data)
            except Exception as e:
                logger.error(f"Failed to decode base64 data: {e}")
                return None
            
            # Check size constraints
            if len(image_data) > MAX_IMAGE_SIZE:
                logger.error(f"Image exceeds maximum size: {len(image_data)} > {MAX_IMAGE_SIZE}")
                return None
            
            # Generate unique filename in sandbox
            filename = f"image_{uuid.uuid4().hex[:8]}.{ext}"
            file_path = self.sandbox_dir / filename
            
            # Save to sandbox directory
            file_path.write_bytes(image_data)
            self.temp_files.append(file_path)
            
            logger.debug(f"Saved base64 image to sandbox: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to save base64 image: {e}")
            return None
    
    def _download_and_save_image(self, url: str) -> Optional[str]:
        """
        Download image from URL and save to sandbox.
        
        Args:
            url: HTTP/HTTPS URL to download image from
            
        Returns:
            Path to saved image file
        """
        try:
            # Validate URL
            parsed = urlparse(url)
            if not parsed.scheme in ['http', 'https']:
                logger.error(f"Invalid URL scheme: {parsed.scheme}")
                return None
            
            # Download image with timeout and size limit
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, follow_redirects=True)
                response.raise_for_status()
                
                # Check content length
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) > MAX_IMAGE_SIZE:
                    logger.error(f"Image exceeds maximum size: {content_length} > {MAX_IMAGE_SIZE}")
                    return None
                
                image_data = response.content
                
                # Double-check actual size
                if len(image_data) > MAX_IMAGE_SIZE:
                    logger.error(f"Downloaded image exceeds maximum size: {len(image_data)} > {MAX_IMAGE_SIZE}")
                    return None
                
                # Determine file extension from content-type or URL
                content_type = response.headers.get('content-type', '')
                if ';' in content_type:
                    content_type = content_type.split(';')[0].strip()
                
                ext = MIME_TO_EXT.get(content_type)
                if not ext:
                    # Try to get extension from URL
                    path = urlparse(url).path
                    if '.' in path:
                        ext = path.split('.')[-1].lower()
                        if ext not in MIME_TO_EXT.values():
                            ext = 'jpg'  # Default
                    else:
                        ext = 'jpg'
                
                # Generate unique filename in sandbox
                filename = f"image_{uuid.uuid4().hex[:8]}.{ext}"
                file_path = self.sandbox_dir / filename
                
                # Save to sandbox directory
                file_path.write_bytes(image_data)
                self.temp_files.append(file_path)
                
                logger.debug(f"Downloaded and saved image to sandbox: {file_path}")
                return str(file_path)
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error downloading image: {e}")
            return None
        except httpx.TimeoutException:
            logger.error(f"Timeout downloading image from {url}")
            return None
        except Exception as e:
            logger.error(f"Failed to download image from {url}: {e}")
            return None
    
    def cleanup(self):
        """Remove all temporary image files created by this handler."""
        for file_path in self.temp_files:
            try:
                if file_path.exists():
                    file_path.unlink()
                    logger.debug(f"Cleaned up image file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup image file {file_path}: {e}")
        
        self.temp_files.clear()
        logger.debug(f"Cleaned up {len(self.temp_files)} image files")
    
    def get_image_references_for_prompt(self, image_mappings: Dict[str, str]) -> List[str]:
        """
        Get list of image file paths for including in prompt.
        
        Args:
            image_mappings: Dictionary mapping URLs to file paths
            
        Returns:
            List of unique file paths
        """
        # Get unique file paths (same image might be referenced multiple times)
        unique_paths = list(set(image_mappings.values()))
        return sorted(unique_paths)  # Sort for consistent ordering
    
    @staticmethod
    def detect_recent_image_placeholders(
        messages: List[Dict], 
        last_n_user_messages: int = 1
    ) -> Dict[str, Optional[str]]:
        """
        Detect image placeholders only from recent user messages.
        
        Args:
            messages: List of message dictionaries
            last_n_user_messages: Number of recent user messages to check (default: 1)
            
        Returns:
            Dictionary mapping placeholder to None (file path to be resolved)
        """
        if not messages:
            return {}
        
        # Find the last N user messages
        user_messages = []
        for msg in reversed(messages):
            if msg.get('role') == 'user':
                user_messages.append(msg)
                if len(user_messages) >= last_n_user_messages:
                    break
        
        # Use the existing detection logic but only on recent messages
        return ImageHandler.detect_image_placeholders(user_messages)
    
    @staticmethod
    def should_process_placeholders(messages: List[Dict]) -> bool:
        """
        Determine if we should process image placeholders based on conversation context.
        
        This only applies to file-based image placeholders like [Image #1].
        OpenAI-format images should always be processed.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            True if we should process placeholders, False if they were already handled
        """
        if not messages or len(messages) < 2:
            return True  # Always process for new conversations
        
        # Check the last assistant message
        for msg in reversed(messages):
            if msg.get('role') == 'assistant':
                content = msg.get('content', '')
                if isinstance(content, str):
                    content_lower = content.lower()
                    
                    # Check if assistant couldn't find images
                    error_phrases = [
                        "don't see any image",
                        "no image attached",
                        "can't find the image",
                        "unable to access",
                        "could you please share the image",
                        "please provide the image",
                        "image file not found"
                    ]
                    
                    for phrase in error_phrases:
                        if phrase in content_lower:
                            logger.debug(f"Assistant needs image help - found phrase: {phrase}")
                            return True
                    
                    # Check if assistant successfully described an image
                    success_phrases = [
                        "the image shows",
                        "i can see",
                        "this image displays",
                        "in the image",
                        "the picture shows",
                        "looking at the image"
                    ]
                    
                    for phrase in success_phrases:
                        if phrase in content_lower:
                            logger.debug(f"Assistant already processed image - found phrase: {phrase}")
                            return False
                
                break  # Only check the last assistant message
        
        return True  # Default to processing if unsure
    
    @staticmethod
    def detect_image_placeholders(messages: List[Dict]) -> Dict[str, Optional[str]]:
        """
        Detect image placeholders like [Image #1] in message content.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Dictionary mapping placeholder to None (file path to be resolved)
        """
        placeholders = {}
        # Pattern to match [Image #N] or [Image: path]
        image_pattern = re.compile(r'\[Image[:\s]+(?:#(\d+)|([^]]+))\]')
        
        for message in messages:
            content = message.get('content', '')
            
            # Handle string content
            if isinstance(content, str):
                matches = image_pattern.findall(content)
                for match in matches:
                    if match[0]:  # Numbered reference like [Image #1]
                        placeholder = f"[Image #{match[0]}]"
                        placeholders[placeholder] = None
                    elif match[1]:  # Path reference like [Image: path/to/file]
                        placeholder = f"[Image: {match[1]}]"
                        placeholders[placeholder] = None
            
            # Also check array content for text parts
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get('type') == 'text':
                        text = part.get('text', '')
                        matches = image_pattern.findall(text)
                        for match in matches:
                            if match[0]:
                                placeholder = f"[Image #{match[0]}]"
                                placeholders[placeholder] = None
                            elif match[1]:
                                placeholder = f"[Image: {match[1]}]"
                                placeholders[placeholder] = None
        
        logger.debug(f"Detected {len(placeholders)} image placeholders: {list(placeholders.keys())}")
        return placeholders
    
    def find_sandbox_images(self) -> List[Path]:
        """
        Find all image files in the sandbox directory.
        
        Returns:
            List of Path objects for image files found
        """
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff'}
        image_files = []
        
        try:
            if self.sandbox_dir.exists():
                for file_path in self.sandbox_dir.iterdir():
                    if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                        image_files.append(file_path)
                        logger.debug(f"Found image file in sandbox: {file_path.name}")
        except Exception as e:
            logger.warning(f"Error scanning sandbox directory for images: {e}")
        
        logger.info(f"Found {len(image_files)} image files in sandbox directory")
        return sorted(image_files)  # Sort for consistent ordering
    
    def resolve_image_placeholders(
        self, 
        placeholders: Dict[str, Optional[str]], 
        processed_image_paths: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Resolve image placeholders to actual file paths in sandbox.
        
        Args:
            placeholders: Dictionary of placeholders to resolve
            processed_image_paths: List of images that were just processed from OpenAI format
            
        Returns:
            Dictionary mapping placeholder to file path (or error message)
        """
        resolved = {}
        sandbox_images = self.find_sandbox_images()
        
        # If we have recently processed images from OpenAI format, prefer those
        if processed_image_paths:
            logger.debug(f"Using recently processed image paths for mapping: {processed_image_paths}")
            # Map placeholders to recently processed images in order
            placeholder_items = list(placeholders.items())
            for i, (placeholder, _) in enumerate(placeholder_items):
                if i < len(processed_image_paths):
                    resolved[placeholder] = processed_image_paths[i]
                    logger.debug(f"Mapped {placeholder} to recently processed image: {processed_image_paths[i]}")
            
            # Return early if we mapped all placeholders
            if len(resolved) == len(placeholders):
                logger.info(f"Resolved {len(resolved)} placeholders to recently processed images")
                return resolved
        
        # Fallback to scanning sandbox for existing images
        logger.debug("Using sandbox scan for image mapping")
        
        # Create a mapping of image numbers to files (by creation order)
        numbered_images = {}
        for i, img_path in enumerate(sandbox_images, 1):
            numbered_images[i] = img_path
        
        for placeholder, _ in placeholders.items():
            if placeholder in resolved:
                continue  # Already mapped above
                
            if '[Image #' in placeholder:
                # Extract number from placeholder
                match = re.search(r'#(\d+)', placeholder)
                if match:
                    num = int(match.group(1))
                    if num in numbered_images:
                        resolved[placeholder] = str(numbered_images[num])
                        logger.debug(f"Mapped {placeholder} to sandbox image: {numbered_images[num]}")
                    elif num <= len(sandbox_images):
                        # Use index if specific number not found
                        resolved[placeholder] = str(sandbox_images[num - 1])
                        logger.debug(f"Mapped {placeholder} to indexed image: {sandbox_images[num - 1]}")
                    else:
                        resolved[placeholder] = f"[No image file found for {placeholder}]"
                        logger.warning(f"Could not find image for {placeholder}")
            elif '[Image:' in placeholder:
                # Extract path from placeholder
                match = re.search(r'\[Image:\s*([^]]+)\]', placeholder)
                if match:
                    ref_path = match.group(1).strip()
                    # Check if it's a filename that exists in sandbox
                    for img_path in sandbox_images:
                        if img_path.name == ref_path or str(img_path).endswith(ref_path):
                            resolved[placeholder] = str(img_path)
                            logger.debug(f"Mapped {placeholder} to existing file: {img_path}")
                            break
                    if placeholder not in resolved:
                        # Try as absolute path
                        test_path = Path(ref_path)
                        if test_path.exists() and test_path.is_file():
                            resolved[placeholder] = str(test_path)
                            logger.debug(f"Mapped {placeholder} to absolute path: {test_path}")
                        else:
                            resolved[placeholder] = f"[Image file not found: {ref_path}]"
                            logger.warning(f"Could not find file for {placeholder}: {ref_path}")
        
        logger.info(f"Resolved {len(resolved)} image placeholders to file paths")
        return resolved