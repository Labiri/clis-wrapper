#!/usr/bin/env python3
"""
Test script for Gemini chat mode in the OpenAI-compatible wrapper.

This tests that Gemini behaves as a general-purpose assistant in chat mode,
not as a coding tool, with sandbox restrictions and proper prompt enforcement.
"""

import asyncio
import aiohttp
import json
import os

# Configuration
API_URL = "http://localhost:8000"
API_KEY = os.getenv("API_KEY")  # Optional FastAPI key


async def test_chat_mode_behavior():
    """Test that Gemini in chat mode behaves as a general assistant."""
    print("\n=== Test 1: General Assistant Behavior ===")
    print("Testing with model: gemini-2.5-flash-chat")
    
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    
    # Test 1: Simple question (should work normally)
    payload = {
        "model": "gemini-2.5-flash-chat",  # Chat mode suffix
        "messages": [
            {"role": "user", "content": "What is the capital of France?"}
        ],
        "stream": False
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_URL}/v1/chat/completions",
            json=payload,
            headers=headers
        ) as response:
            if response.status == 200:
                result = await response.json()
                content = result['choices'][0]['message']['content']
                print(f"✅ General question response: {content[:100]}...")
            else:
                print(f"❌ Error: {response.status}")


async def test_file_system_restriction():
    """Test that file system access is restricted in chat mode."""
    print("\n=== Test 2: File System Restriction ===")
    
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    
    payload = {
        "model": "gemini-2.5-flash-chat",
        "messages": [
            {"role": "user", "content": "What files are in the current directory? Can you list them?"}
        ],
        "stream": False
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_URL}/v1/chat/completions",
            json=payload,
            headers=headers
        ) as response:
            if response.status == 200:
                result = await response.json()
                content = result['choices'][0]['message']['content']
                
                # Check if response mentions sandbox/black hole/no file access
                if any(phrase in content.lower() for phrase in ["black hole", "sandbox", "no file", "can't access"]):
                    print(f"✅ File system properly restricted: {content[:150]}...")
                else:
                    print(f"⚠️  Response may not show proper restriction: {content[:150]}...")
            else:
                print(f"❌ Error: {response.status}")


async def test_code_generation():
    """Test that code generation works but without file operations."""
    print("\n=== Test 3: Code Generation (No File Ops) ===")
    
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    
    payload = {
        "model": "gemini-2.5-flash-chat",
        "messages": [
            {"role": "user", "content": "Write a Python function to calculate factorial"}
        ],
        "stream": False
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_URL}/v1/chat/completions",
            json=payload,
            headers=headers
        ) as response:
            if response.status == 200:
                result = await response.json()
                content = result['choices'][0]['message']['content']
                
                # Check if response contains code
                if "def" in content or "factorial" in content.lower():
                    print(f"✅ Code generation works: {content[:200]}...")
                    
                    # Verify no file operations mentioned
                    if not any(word in content.lower() for word in ["save", "write", "file", "create"]):
                        print("✅ No file operations mentioned")
                    else:
                        print("⚠️  File operations might be mentioned")
                else:
                    print(f"❌ No code found in response: {content[:200]}...")
            else:
                print(f"❌ Error: {response.status}")


async def test_normal_mode_comparison():
    """Compare behavior between normal and chat mode."""
    print("\n=== Test 4: Normal vs Chat Mode Comparison ===")
    
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    
    # Test with normal mode
    print("\nTesting normal mode (gemini-2.5-flash)...")
    payload_normal = {
        "model": "gemini-2.5-flash",  # No chat suffix
        "messages": [
            {"role": "user", "content": "List files in current directory"}
        ],
        "stream": False
    }
    
    # Test with chat mode
    print("Testing chat mode (gemini-2.5-flash-chat)...")
    payload_chat = {
        "model": "gemini-2.5-flash-chat",  # Chat suffix
        "messages": [
            {"role": "user", "content": "List files in current directory"}
        ],
        "stream": False
    }
    
    async with aiohttp.ClientSession() as session:
        # Normal mode
        async with session.post(
            f"{API_URL}/v1/chat/completions",
            json=payload_normal,
            headers=headers
        ) as response:
            if response.status == 200:
                result = await response.json()
                normal_content = result['choices'][0]['message']['content']
                print(f"Normal mode: {normal_content[:150]}...")
        
        # Chat mode
        async with session.post(
            f"{API_URL}/v1/chat/completions",
            json=payload_chat,
            headers=headers
        ) as response:
            if response.status == 200:
                result = await response.json()
                chat_content = result['choices'][0]['message']['content']
                print(f"Chat mode: {chat_content[:150]}...")
                
                if "black hole" in chat_content.lower() or "sandbox" in chat_content.lower():
                    print("✅ Chat mode properly restricts file access")
                else:
                    print("⚠️  Chat mode may not be restricting properly")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Gemini Chat Mode Tests")
    print("=" * 60)
    print("\nThese tests verify that Gemini in chat mode:")
    print("- Acts as a general-purpose assistant")
    print("- Restricts file system access")
    print("- Uses sandbox environment")
    print("- Still generates code but without file operations")
    
    await test_chat_mode_behavior()
    await test_file_system_restriction()
    await test_code_generation()
    await test_normal_mode_comparison()
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
    print("\nNote: Gemini CLI must be installed and authenticated:")
    print("  npm install -g @google/gemini-cli")
    print("  gemini auth login")


if __name__ == "__main__":
    asyncio.run(main())