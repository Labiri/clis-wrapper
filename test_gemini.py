#!/usr/bin/env python3
"""
Test script for Gemini CLI integration in the OpenAI-compatible wrapper.

Prerequisites:
- Install Gemini CLI: npm install -g @google/gemini-cli
- Authenticate: gemini auth login
"""

import asyncio
import aiohttp
import json
import os
from typing import AsyncGenerator

# Configuration
API_URL = "http://localhost:8000"
API_KEY = os.getenv("API_KEY")  # Optional FastAPI key (for endpoint protection, not Gemini)


async def stream_chat_completion(messages, model="gemini-2.5-flash"):
    """Test streaming chat completion with Gemini."""
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "temperature": 0.7
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_URL}/v1/chat/completions",
            json=payload,
            headers=headers
        ) as response:
            print(f"Status: {response.status}")
            
            if response.status != 200:
                error_text = await response.text()
                print(f"Error: {error_text}")
                return
            
            # Process streaming response
            async for line in response.content:
                line = line.decode('utf-8').strip()
                if line.startswith("data: "):
                    data = line[6:]  # Remove "data: " prefix
                    if data == "[DONE]":
                        print("\nStream completed.")
                        break
                    try:
                        chunk = json.loads(data)
                        if 'choices' in chunk and chunk['choices']:
                            delta = chunk['choices'][0].get('delta', {})
                            if 'content' in delta:
                                print(delta['content'], end='', flush=True)
                    except json.JSONDecodeError:
                        pass


async def non_stream_chat_completion(messages, model="gemini-2.5-flash"):
    """Test non-streaming chat completion with Gemini."""
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_URL}/v1/chat/completions",
            json=payload,
            headers=headers
        ) as response:
            print(f"Status: {response.status}")
            
            if response.status == 200:
                result = await response.json()
                print("Response:", json.dumps(result, indent=2))
                
                # Extract and display the message
                if result.get('choices'):
                    content = result['choices'][0]['message']['content']
                    print(f"\nAssistant: {content}")
            else:
                error_text = await response.text()
                print(f"Error: {error_text}")


async def list_models():
    """List available models including Gemini models."""
    headers = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{API_URL}/v1/models",
            headers=headers
        ) as response:
            print(f"Status: {response.status}")
            
            if response.status == 200:
                result = await response.json()
                
                # Separate models by provider
                gemini_models = []
                claude_models = []
                
                for model in result.get('data', []):
                    model_id = model['id']
                    owner = model.get('owned_by', 'unknown')
                    
                    if owner == 'google' or model_id.startswith('gemini'):
                        gemini_models.append(model_id)
                    else:
                        claude_models.append(model_id)
                
                print("\n=== Available Models ===")
                print(f"\nGemini Models ({len(gemini_models)}):")
                for model in sorted(gemini_models):
                    print(f"  - {model}")
                
                print(f"\nClaude Models ({len(claude_models)}):")
                for model in sorted(claude_models)[:10]:  # Show first 10
                    print(f"  - {model}")
                if len(claude_models) > 10:
                    print(f"  ... and {len(claude_models) - 10} more")
            else:
                error_text = await response.text()
                print(f"Error: {error_text}")


async def test_multimodal():
    """Test multimodal support with Gemini (if image URLs are supported)."""
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What's in this image?"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."  # Truncated for example
                    }
                }
            ]
        }
    ]
    
    print("\n=== Testing Multimodal Support ===")
    print("Note: This requires a valid base64 encoded image")
    # Uncomment to test with real image data
    # await non_stream_chat_completion(messages, model="gemini-1.5-pro")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Gemini Integration Tests")
    print("=" * 60)
    
    # Test 1: List models
    print("\n=== Test 1: List Models ===")
    await list_models()
    
    # Test 2: Non-streaming completion
    print("\n=== Test 2: Non-Streaming Completion ===")
    messages = [
        {"role": "user", "content": "What is the capital of France? Answer in one word."}
    ]
    await non_stream_chat_completion(messages)
    
    # Test 3: Streaming completion
    print("\n=== Test 3: Streaming Completion ===")
    messages = [
        {"role": "user", "content": "Write a haiku about programming."}
    ]
    await stream_chat_completion(messages)
    
    # Test 4: System message support
    print("\n=== Test 4: System Message Support ===")
    messages = [
        {"role": "system", "content": "You are a helpful assistant who speaks like a pirate."},
        {"role": "user", "content": "What is Python?"}
    ]
    await non_stream_chat_completion(messages)
    
    # Test 5: Conversation with context
    print("\n=== Test 5: Multi-turn Conversation ===")
    messages = [
        {"role": "user", "content": "My name is Alice."},
        {"role": "assistant", "content": "Nice to meet you, Alice! How can I help you today?"},
        {"role": "user", "content": "What's my name?"}
    ]
    await non_stream_chat_completion(messages)
    
    # Test 6: Different Gemini models
    print("\n=== Test 6: Testing Different Models ===")
    for model in ["gemini-2.5-flash", "gemini-2.5-pro"]:
        print(f"\nTesting {model}:")
        messages = [{"role": "user", "content": "Say hello in one word."}]
        await non_stream_chat_completion(messages, model=model)
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())