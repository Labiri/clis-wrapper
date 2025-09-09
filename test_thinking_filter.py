#!/usr/bin/env python3
"""Test script for Qwen thinking block filtering."""

import asyncio
import os
import sys
from qwen_cli import QwenCLI

async def test_thinking_filter():
    """Test that thinking blocks are properly filtered."""
    print("Testing Qwen thinking block filtering...")
    
    # Initialize Qwen CLI
    qwen = QwenCLI()
    
    # Test prompts that should trigger thinking
    test_prompts = [
        {
            "messages": [{"role": "user", "content": "What can you do?"}],
            "description": "Simple capability question"
        },
        {
            "messages": [{"role": "user", "content": "Help me write a Python function to calculate fibonacci numbers"}],
            "description": "Code generation request"
        },
        {
            "messages": [{"role": "user", "content": "Explain the concept of recursion"}],
            "description": "Explanation request"
        }
    ]
    
    for test_case in test_prompts:
        print(f"\n{'='*60}")
        print(f"Test: {test_case['description']}")
        print(f"Prompt: {test_case['messages'][0]['content']}")
        print(f"{'='*60}")
        
        response_text = ""
        try:
            async for chunk in qwen.stream_completion(
                messages=test_case['messages'],
                model="qwen3-coder-plus",
                temperature=0.7,
                max_tokens=500
            ):
                response_text += chunk
                print(chunk, end='', flush=True)
        except Exception as e:
            print(f"\nError: {e}")
            continue
        
        print(f"\n{'='*60}")
        
        # Check if common thinking patterns are in the response
        thinking_indicators = [
            "The user is asking",
            "The user wants",
            "Based on the system information",
            "available tools",
            "I need to",
            "I should"
        ]
        
        found_thinking = False
        for indicator in thinking_indicators:
            if indicator.lower() in response_text.lower():
                print(f"⚠️  WARNING: Found thinking pattern in response: '{indicator}'")
                found_thinking = True
        
        if not found_thinking:
            print("✅ No thinking patterns detected - filtering successful!")
        else:
            print("❌ Thinking patterns found - filtering may need adjustment")
    
    print("\n" + "="*60)
    print("Test completed!")

if __name__ == "__main__":
    # Set environment for testing
    os.environ['DEBUG'] = '0'
    os.environ['NODE_ENV'] = 'production'
    
    asyncio.run(test_thinking_filter())