#!/usr/bin/env python3
"""Test Qwen output with XML format enforcement."""

import asyncio
import os
from qwen_cli import QwenCLI

async def test_xml_output():
    """Test Qwen output with XML format required."""
    print("Testing Qwen output with XML format enforcement...")
    
    # Initialize Qwen CLI
    qwen = QwenCLI()
    
    # Test with messages that should trigger XML formatting
    test_cases = [
        {
            "messages": [
                {"role": "user", "content": "What capabilities do you have for helping with code?"}
            ],
            "requires_xml": True,
            "description": "Direct XML requirement"
        },
        {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant. Use <attempt_completion> tags for responses."},
                {"role": "user", "content": "What can you help me with?"}
            ],
            "requires_xml": False,
            "description": "XML hints in system message"
        }
    ]
    
    for test_case in test_cases:
        print(f"\n{'='*60}")
        print(f"Test: {test_case['description']}")
        print(f"Messages: {test_case['messages']}")
        print(f"Requires XML: {test_case['requires_xml']}")
        print("="*60)
        print("Raw output:")
        print("-"*60)
        
        full_response = ""
        try:
            async for chunk in qwen.stream_completion(
                messages=test_case['messages'],
                model="qwen3-coder-plus",
                temperature=0.7,
                max_tokens=500,
                requires_xml=test_case['requires_xml']
            ):
                full_response += chunk
                print(chunk, end='', flush=True)
        except Exception as e:
            print(f"\nError: {e}")
            continue
        
        print("\n" + "-"*60)
        
        # Check response format
        print("\nAnalysis:")
        if "<attempt_completion>" in full_response:
            print("✅ Contains <attempt_completion> tags")
        elif "<ask_followup_question>" in full_response:
            print("✅ Contains <ask_followup_question> tags")
        elif "<" in full_response and ">" in full_response:
            print("⚠️  Contains XML tags (other than expected)")
            # Extract tag names
            import re
            tags = re.findall(r'<([^/>]+)>', full_response)
            if tags:
                print(f"   Found tags: {set(tags)}")
        else:
            print("❌ No XML tags in response")

if __name__ == "__main__":
    # Set environment for testing
    os.environ['DEBUG'] = '0'
    os.environ['NODE_ENV'] = 'production'
    os.environ['XML_KNOWN_TOOLS'] = 'attempt_completion,ask_followup_question,read_file,write_to_file'
    
    asyncio.run(test_xml_output())