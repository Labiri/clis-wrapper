#!/usr/bin/env python3
"""Test raw Qwen output to see what's being generated."""

import asyncio
import os
from qwen_cli import QwenCLI

async def test_raw_output():
    """Test raw Qwen output without filtering."""
    print("Testing raw Qwen output...")
    
    # Initialize Qwen CLI
    qwen = QwenCLI()
    
    # Test with a simple prompt
    messages = [{"role": "user", "content": "What can you do to help with coding?"}]
    
    print(f"Prompt: {messages[0]['content']}")
    print("="*60)
    print("Raw output from Qwen CLI:")
    print("="*60)
    
    full_response = ""
    try:
        async for chunk in qwen.stream_completion(
            messages=messages,
            model="qwen3-coder-plus",
            temperature=0.7,
            max_tokens=500
        ):
            full_response += chunk
            print(chunk, end='', flush=True)
    except Exception as e:
        print(f"\nError: {e}")
    
    print("\n" + "="*60)
    print("Full response collected:")
    print("="*60)
    print(full_response)
    print("="*60)
    
    # Check if XML is present
    if "<" in full_response and ">" in full_response:
        print("⚠️  XML tags detected in response")
    else:
        print("✅ No XML tags in response")
    
    # Check for thinking patterns
    if "The user is asking" in full_response or "Based on the system" in full_response:
        print("💭 Thinking content detected in response")
    else:
        print("✅ No obvious thinking patterns")

if __name__ == "__main__":
    # Set environment for testing
    os.environ['DEBUG'] = '0'
    os.environ['NODE_ENV'] = 'production'
    
    asyncio.run(test_raw_output())