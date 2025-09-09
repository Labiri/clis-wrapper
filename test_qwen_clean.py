#!/usr/bin/env python3
"""Test Qwen integration to verify debug output is suppressed."""

import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qwen_cli import QwenCLI

async def test_qwen_clean_output():
    """Test that Qwen returns clean output without debug messages."""
    print("Testing Qwen CLI with debug suppression...")
    
    # Initialize Qwen CLI
    qwen = QwenCLI()
    
    # Simple test messages
    messages = [
        {"role": "user", "content": "What is 2 + 2? Please respond with just the number."}
    ]
    
    print("\nSending request to Qwen...")
    print("-" * 50)
    
    # Collect response
    response_text = ""
    async for chunk in qwen.stream_completion(messages):
        response_text += chunk
        print(chunk, end="", flush=True)
    
    print("\n" + "-" * 50)
    
    # Check for debug messages
    debug_indicators = ["[DEBUG]", "[MemoryDiscovery]", "Flushing log", "Loaded cached", "CLI:", "credentials"]
    found_debug = False
    for indicator in debug_indicators:
        if indicator in response_text:
            print(f"\n❌ Found debug output: '{indicator}'")
            found_debug = True
    
    if not found_debug:
        print("\n✅ Success! No debug output detected in response.")
    else:
        print("\n❌ Failed! Debug output still present in response.")
    
    return not found_debug

if __name__ == "__main__":
    success = asyncio.run(test_qwen_clean_output())
    sys.exit(0 if success else 1)