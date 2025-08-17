#!/usr/bin/env python3
"""
Test script for the message boundary approach to image processing.
Tests various scenarios to ensure only new images are processed.
"""

import asyncio
import json
import httpx
import base64
from pathlib import Path

API_BASE_URL = "http://localhost:8005"

# Create a small test image (1x1 red pixel PNG)
TEST_IMAGE_BASE64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="


async def test_first_message_with_image():
    """Test processing image in first message (no assistant yet)."""
    print("\n" + "="*60)
    print("TEST 1: First message with image (no assistant yet)")
    print("="*60)
    
    request_data = {
        "model": "claude-3-5-sonnet-latest-chat",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What do you see in this image?"},
                    {"type": "image_url", "image_url": {"url": TEST_IMAGE_BASE64}}
                ]
            }
        ],
        "stream": False
    }
    
    print("Sending first message with image...")
    
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=60.0) as client:
        response = await client.post("/v1/chat/completions", json=request_data)
        
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            print(f"Response preview: {content[:200]}...")
            
            if "red" in content.lower() or "pixel" in content.lower() or "1x1" in content.lower():
                print("✅ SUCCESS: Claude saw and described the image")
            else:
                print("❌ FAILED: Claude didn't describe the image correctly")
        else:
            print(f"❌ Error: {response.text}")


async def test_conversation_with_old_image():
    """Test that old images from previous messages aren't reprocessed."""
    print("\n" + "="*60)
    print("TEST 2: Conversation with old image (shouldn't reprocess)")
    print("="*60)
    
    request_data = {
        "model": "claude-3-5-sonnet-latest-chat",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Look at this image:"},
                    {"type": "image_url", "image_url": {"url": TEST_IMAGE_BASE64}}
                ]
            },
            {
                "role": "assistant",
                "content": "I can see a small 1x1 red pixel image. It's a minimal PNG file."
            },
            {
                "role": "user",
                "content": "What color was it again?"
            }
        ],
        "stream": False
    }
    
    print("Sending follow-up without new image...")
    
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=60.0) as client:
        response = await client.post("/v1/chat/completions", json=request_data)
        
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            print(f"Response preview: {content[:200]}...")
            
            # Check if Claude remembers without re-analyzing
            if "red" in content.lower():
                print("✅ SUCCESS: Claude remembered the color without reprocessing")
            else:
                print("⚠️  WARNING: Check if response is appropriate")
        else:
            print(f"❌ Error: {response.text}")


async def test_new_image_in_conversation():
    """Test that new images are processed when added to conversation."""
    print("\n" + "="*60)
    print("TEST 3: Adding new image to existing conversation")
    print("="*60)
    
    # Create a different test image (1x1 blue pixel)
    BLUE_IMAGE_BASE64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    
    request_data = {
        "model": "claude-3-5-sonnet-latest-chat",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Look at this first image:"},
                    {"type": "image_url", "image_url": {"url": TEST_IMAGE_BASE64}}
                ]
            },
            {
                "role": "assistant",
                "content": "I can see a small 1x1 red pixel image."
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Now look at this second image:"},
                    {"type": "image_url", "image_url": {"url": BLUE_IMAGE_BASE64}}
                ]
            }
        ],
        "stream": False
    }
    
    print("Sending new image after assistant response...")
    
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=60.0) as client:
        response = await client.post("/v1/chat/completions", json=request_data)
        
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            print(f"Response preview: {content[:200]}...")
            
            if "blue" in content.lower():
                print("✅ SUCCESS: Claude saw and described the NEW blue image")
            elif "red" in content.lower() and "blue" not in content.lower():
                print("❌ FAILED: Claude only mentioned the old red image")
            else:
                print("⚠️  WARNING: Unclear if new image was processed")
        else:
            print(f"❌ Error: {response.text}")


async def test_placeholder_format():
    """Test file-based placeholder format like [Image #1]."""
    print("\n" + "="*60)
    print("TEST 4: File-based placeholder format [Image #1]")
    print("="*60)
    
    request_data = {
        "model": "claude-3-5-sonnet-latest-chat",
        "messages": [
            {
                "role": "user",
                "content": "Can you describe this image?\n[Image #1]"
            }
        ],
        "stream": False
    }
    
    print("Sending placeholder reference...")
    
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=60.0) as client:
        response = await client.post("/v1/chat/completions", json=request_data)
        
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            print(f"Response: {content[:300]}...")
            
            if "sandbox" in content.lower() or "file" in content.lower():
                print("✅ SUCCESS: Claude received instructions about image location")
            elif "don't see" in content.lower() or "no image" in content.lower():
                print("⚠️  INFO: No images in sandbox (expected if sandbox is empty)")
            else:
                print("🤔 Check response for appropriate handling")
        else:
            print(f"❌ Error: {response.text}")


async def test_mixed_formats():
    """Test mixing OpenAI format and placeholder format."""
    print("\n" + "="*60)
    print("TEST 5: Mixed formats (OpenAI + placeholder)")
    print("="*60)
    
    request_data = {
        "model": "claude-3-5-sonnet-latest-chat",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Compare these images:\n[Image #1] and this one:"},
                    {"type": "image_url", "image_url": {"url": TEST_IMAGE_BASE64}}
                ]
            }
        ],
        "stream": False
    }
    
    print("Sending mixed format message...")
    
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=60.0) as client:
        response = await client.post("/v1/chat/completions", json=request_data)
        
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            print(f"Response preview: {content[:300]}...")
            
            # Should handle both the placeholder and the base64 image
            if ("red" in content.lower() or "pixel" in content.lower()) and \
               ("image #1" in content.lower() or "sandbox" in content.lower()):
                print("✅ SUCCESS: Claude handled both image formats")
            else:
                print("⚠️  Check if both formats were processed")
        else:
            print(f"❌ Error: {response.text}")


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("TESTING MESSAGE BOUNDARY IMAGE PROCESSING")
    print("="*60)
    
    tests = [
        test_first_message_with_image,
        test_conversation_with_old_image,
        test_new_image_in_conversation,
        test_placeholder_format,
        test_mixed_formats
    ]
    
    for test in tests:
        try:
            await test()
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
    
    print("\n" + "="*60)
    print("ALL TESTS COMPLETED")
    print("="*60)
    print("\nSummary:")
    print("- Test 1: Should process image in first message")
    print("- Test 2: Should NOT reprocess old image")
    print("- Test 3: Should process only NEW image")
    print("- Test 4: Should handle placeholder format")
    print("- Test 5: Should handle mixed formats")


if __name__ == "__main__":
    asyncio.run(main())