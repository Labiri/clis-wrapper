#!/usr/bin/env python3
"""
Test script for image placeholder support.
Simulates how Roo/Cline send image references.
"""

import asyncio
import json
import httpx

API_BASE_URL = "http://localhost:8005"


async def test_image_placeholder():
    """Test image analysis with [Image #1] placeholder format."""
    
    # Simulate Roo/Cline format - just text with placeholder
    request_data = {
        "model": "claude-3-5-sonnet-latest-chat",  # Chat mode
        "messages": [
            {
                "role": "user",
                "content": "Describe this image:\n[Image #1]"
            }
        ],
        "stream": False
    }
    
    print("Testing image placeholder format...")
    print(f"Request: {json.dumps(request_data, indent=2)}")
    
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=60.0) as client:
        response = await client.post(
            "/v1/chat/completions",
            json=request_data
        )
        
        print(f"\nStatus: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if "choices" in result and result["choices"]:
                content = result["choices"][0]["message"]["content"]
                print(f"\nResponse:\n{content}")
                
                # Check if Claude mentioned finding the image or needing the path
                if "image file" in content.lower() or "read tool" in content.lower():
                    print("\n✅ SUCCESS: Claude received instructions about image location!")
                elif "don't see" in content.lower() or "no image" in content.lower():
                    print("\n❌ FAILED: Claude couldn't find the image")
                else:
                    print("\n🤔 UNCLEAR: Check if Claude saw the image")
        else:
            print(f"Error: {response.text}")


async def test_multiple_placeholders():
    """Test multiple image placeholders."""
    
    request_data = {
        "model": "claude-3-5-sonnet-latest-chat",
        "messages": [
            {
                "role": "user",
                "content": "Compare these images:\n[Image #1]\n[Image #2]"
            }
        ],
        "stream": False
    }
    
    print("\n" + "="*50)
    print("Testing multiple image placeholders...")
    
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=60.0) as client:
        response = await client.post(
            "/v1/chat/completions",
            json=request_data
        )
        
        if response.status_code == 200:
            result = response.json()
            if "choices" in result and result["choices"]:
                content = result["choices"][0]["message"]["content"]
                print(f"\nResponse preview: {content[:200]}...")


async def main():
    """Run all tests."""
    await test_image_placeholder()
    await test_multiple_placeholders()
    print("\n" + "="*50)
    print("Tests completed!")
    print("\nNote: For these tests to work properly, there should be")
    print("image files in the sandbox directory that Claude can read.")


if __name__ == "__main__":
    asyncio.run(main())