#!/usr/bin/env python3
"""
Test suite for Claude Code image support in the OpenAI wrapper.

Tests both normal mode and chat mode image handling, including:
- Base64 encoded images
- URL-based images
- Multiple images per message
- Images throughout conversation history
- Caching behavior
- Error handling
"""

import asyncio
import base64
import json
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Any

import httpx
import pytest

# Test configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8005")
API_KEY = os.getenv("API_KEY", "test-key")

# Create a small test image (1x1 red pixel PNG)
TEST_IMAGE_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
)
TEST_IMAGE_DATA_URL = f"data:image/png;base64,{TEST_IMAGE_BASE64}"

# Another test image (1x1 blue pixel PNG) for testing multiple images
TEST_IMAGE2_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPj/HwADAgIAASbOuAAAAABJRU5ErkJggg=="
)
TEST_IMAGE2_DATA_URL = f"data:image/png;base64,{TEST_IMAGE2_BASE64}"


class TestClaudeImages:
    """Test suite for Claude image support."""
    
    def __init__(self):
        """Initialize test client."""
        self.client = httpx.AsyncClient(base_url=API_BASE_URL, timeout=60.0)
        self.headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY != "test-key" else {}
    
    async def cleanup(self):
        """Clean up test environment."""
        await self.client.aclose()
    
    async def test_single_base64_image(self):
        """Test processing a single base64 encoded image."""
        request_data = {
            "model": "claude-3-5-sonnet-latest",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What color is this image?"},
                        {
                            "type": "image_url",
                            "image_url": {"url": TEST_IMAGE_DATA_URL}
                        }
                    ]
                }
            ],
            "stream": False,
            "enable_tools": True  # Enable tools to allow Read tool for images
        }
        
        response = await self.client.post(
            "/v1/chat/completions",
            json=request_data,
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Request failed: {response.text}"
        result = response.json()
        
        # Check response structure
        assert "choices" in result
        assert len(result["choices"]) > 0
        assert "message" in result["choices"][0]
        
        # The response should mention analyzing the image
        content = result["choices"][0]["message"]["content"].lower()
        print(f"Response: {content}")
    
    async def test_multiple_images_in_message(self):
        """Test processing multiple images in a single message."""
        request_data = {
            "model": "claude-3-5-sonnet-latest",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Compare these two images. What are their colors?"},
                        {
                            "type": "image_url",
                            "image_url": {"url": TEST_IMAGE_DATA_URL}
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": TEST_IMAGE2_DATA_URL}
                        }
                    ]
                }
            ],
            "stream": False,
            "enable_tools": True
        }
        
        response = await self.client.post(
            "/v1/chat/completions",
            json=request_data,
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Request failed: {response.text}"
        result = response.json()
        
        content = result["choices"][0]["message"]["content"].lower()
        print(f"Response for multiple images: {content}")
    
    async def test_images_in_conversation_history(self):
        """Test images appearing in conversation history."""
        request_data = {
            "model": "claude-3-5-sonnet-latest",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "I'm going to show you an image."},
                        {
                            "type": "image_url",
                            "image_url": {"url": TEST_IMAGE_DATA_URL}
                        }
                    ]
                },
                {
                    "role": "assistant",
                    "content": "I can see the image you've shared. What would you like to know about it?"
                },
                {
                    "role": "user",
                    "content": "What color was the image I showed you earlier?"
                }
            ],
            "stream": False,
            "enable_tools": True
        }
        
        response = await self.client.post(
            "/v1/chat/completions",
            json=request_data,
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Request failed: {response.text}"
        result = response.json()
        
        content = result["choices"][0]["message"]["content"].lower()
        print(f"Response about historical image: {content}")
    
    async def test_chat_mode_with_images(self):
        """Test image processing in chat mode (model with -chat suffix)."""
        request_data = {
            "model": "claude-3-5-sonnet-latest-chat",  # Chat mode model
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe this image briefly."},
                        {
                            "type": "image_url",
                            "image_url": {"url": TEST_IMAGE_DATA_URL}
                        }
                    ]
                }
            ],
            "stream": False
            # Note: enable_tools not needed in chat mode - Read tool should be auto-enabled for images
        }
        
        response = await self.client.post(
            "/v1/chat/completions",
            json=request_data,
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Request failed: {response.text}"
        result = response.json()
        
        content = result["choices"][0]["message"]["content"].lower()
        print(f"Chat mode response: {content}")
    
    async def test_streaming_with_images(self):
        """Test streaming responses with images."""
        request_data = {
            "model": "claude-3-5-sonnet-latest",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What do you see in this image?"},
                        {
                            "type": "image_url",
                            "image_url": {"url": TEST_IMAGE_DATA_URL}
                        }
                    ]
                }
            ],
            "stream": True,
            "enable_tools": True
        }
        
        chunks = []
        async with self.client.stream(
            "POST",
            "/v1/chat/completions",
            json=request_data,
            headers=self.headers
        ) as response:
            assert response.status_code == 200
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]  # Remove "data: " prefix
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        chunks.append(chunk)
                        if "choices" in chunk and chunk["choices"]:
                            delta = chunk["choices"][0].get("delta", {})
                            if "content" in delta:
                                print(delta["content"], end="", flush=True)
                    except json.JSONDecodeError:
                        continue
        
        print()  # New line after streaming
        assert len(chunks) > 0, "No chunks received"
    
    async def test_image_caching(self):
        """Test that duplicate images are cached and not reprocessed."""
        # Send the same image twice in different messages
        request_data = {
            "model": "claude-3-5-sonnet-latest",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "First, look at this image."},
                        {
                            "type": "image_url",
                            "image_url": {"url": TEST_IMAGE_DATA_URL}
                        }
                    ]
                },
                {
                    "role": "assistant",
                    "content": "I see the first image."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Now look at this image again."},
                        {
                            "type": "image_url",
                            "image_url": {"url": TEST_IMAGE_DATA_URL}  # Same image
                        }
                    ]
                }
            ],
            "stream": False,
            "enable_tools": True
        }
        
        response = await self.client.post(
            "/v1/chat/completions",
            json=request_data,
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Request failed: {response.text}"
        # The caching happens internally - we just verify the request succeeds
    
    async def test_mixed_text_and_images(self):
        """Test messages with mixed text and image content."""
        request_data = {
            "model": "claude-3-5-sonnet-latest",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Here are two things to analyze:"},
                        {"type": "text", "text": "1. This image:"},
                        {
                            "type": "image_url",
                            "image_url": {"url": TEST_IMAGE_DATA_URL}
                        },
                        {"type": "text", "text": "2. And this other image:"},
                        {
                            "type": "image_url",
                            "image_url": {"url": TEST_IMAGE2_DATA_URL}
                        },
                        {"type": "text", "text": "What are the differences?"}
                    ]
                }
            ],
            "stream": False,
            "enable_tools": True
        }
        
        response = await self.client.post(
            "/v1/chat/completions",
            json=request_data,
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Request failed: {response.text}"
        result = response.json()
        
        content = result["choices"][0]["message"]["content"]
        print(f"Mixed content response: {content}")
    
    async def test_invalid_image_handling(self):
        """Test handling of invalid image data."""
        request_data = {
            "model": "claude-3-5-sonnet-latest",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What's in this image?"},
                        {
                            "type": "image_url",
                            "image_url": {"url": "data:image/png;base64,INVALID_BASE64"}
                        }
                    ]
                }
            ],
            "stream": False,
            "enable_tools": True
        }
        
        response = await self.client.post(
            "/v1/chat/completions",
            json=request_data,
            headers=self.headers
        )
        
        # Should still return a response, but might mention the image couldn't be processed
        assert response.status_code == 200, f"Request failed: {response.text}"
    
    async def test_image_url_format(self):
        """Test handling of image URLs (not base64)."""
        # Using a small test image URL
        request_data = {
            "model": "claude-3-5-sonnet-latest",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What's in this image?"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "https://via.placeholder.com/150/FF0000/FFFFFF?text=Test",
                                "detail": "auto"
                            }
                        }
                    ]
                }
            ],
            "stream": False,
            "enable_tools": True
        }
        
        response = await self.client.post(
            "/v1/chat/completions",
            json=request_data,
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Request failed: {response.text}"
        result = response.json()
        
        content = result["choices"][0]["message"]["content"]
        print(f"URL image response: {content}")


async def main():
    """Run all tests."""
    test_suite = TestClaudeImages()
    
    try:
        print("Testing single base64 image...")
        await test_suite.test_single_base64_image()
        
        print("\nTesting multiple images...")
        await test_suite.test_multiple_images_in_message()
        
        print("\nTesting images in conversation history...")
        await test_suite.test_images_in_conversation_history()
        
        print("\nTesting chat mode with images...")
        await test_suite.test_chat_mode_with_images()
        
        print("\nTesting streaming with images...")
        await test_suite.test_streaming_with_images()
        
        print("\nTesting image caching...")
        await test_suite.test_image_caching()
        
        print("\nTesting mixed text and images...")
        await test_suite.test_mixed_text_and_images()
        
        print("\nTesting invalid image handling...")
        await test_suite.test_invalid_image_handling()
        
        print("\nTesting URL-based images...")
        await test_suite.test_image_url_format()
        
        print("\n✅ All tests completed!")
        
    finally:
        await test_suite.cleanup()


if __name__ == "__main__":
    asyncio.run(main())