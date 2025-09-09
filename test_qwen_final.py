#!/usr/bin/env python3
"""Final test of Qwen integration with auth filtering and thinking blocks."""

import asyncio
import os
from qwen_cli import QwenCLI

async def test_final_output():
    """Test final Qwen output with all processing."""
    print("Final Qwen Integration Test")
    print("="*60)
    
    # Initialize Qwen CLI
    qwen = QwenCLI()
    
    test_cases = [
        {
            "name": "Simple question (no XML)",
            "messages": [{"role": "user", "content": "What can you help me with?"}],
            "requires_xml": False
        },
        {
            "name": "Question with thinking expected",
            "messages": [{"role": "user", "content": "Explain how to write a fibonacci function"}],
            "requires_xml": False
        },
        {
            "name": "XML format required",
            "messages": [
                {"role": "system", "content": "Use XML format for responses"},
                {"role": "user", "content": "Help me understand recursion"}
            ],
            "requires_xml": True
        }
    ]
    
    for test_case in test_cases:
        print(f"\n{'='*60}")
        print(f"Test: {test_case['name']}")
        print(f"User message: {test_case['messages'][-1]['content']}")
        print(f"XML required: {test_case['requires_xml']}")
        print("-"*60)
        
        full_response = ""
        line_count = 0
        has_auth_issues = False
        
        try:
            async for chunk in qwen.stream_completion(
                messages=test_case['messages'],
                model="qwen3-coder-plus",
                temperature=0.7,
                max_tokens=500,
                requires_xml=test_case['requires_xml']
            ):
                full_response += chunk
                line_count += chunk.count('\n')
                
                # Check for auth leakage
                if any(pattern in chunk.lower() for pattern in [
                    'device_code', 'user_code', 'verification_uri', 
                    'polling for token', 'waiting for authorization'
                ]):
                    has_auth_issues = True
                    print(f"❌ AUTH LEAK: {chunk[:50]}")
                else:
                    print(chunk, end='', flush=True)
                    
        except Exception as e:
            print(f"\n❌ Error: {e}")
            continue
        
        print("\n" + "-"*60)
        print("Analysis:")
        
        # Check for auth issues
        if has_auth_issues:
            print("❌ Authentication prompts leaked into output")
        else:
            print("✅ No authentication prompts in output")
        
        # Check for thinking blocks (these should be present)
        thinking_indicators = [
            "The user is asking",
            "The user wants",
            "I need to",
            "I should",
            "Let me"
        ]
        
        has_thinking = any(indicator.lower() in full_response.lower() 
                          for indicator in thinking_indicators)
        
        if has_thinking:
            print("💭 Thinking blocks present (as expected)")
        else:
            print("📝 Direct response without visible thinking")
        
        # Check XML format if required
        if test_case['requires_xml']:
            if '<attempt_completion>' in full_response:
                print("✅ XML format: <attempt_completion> tags present")
            elif '<ask_followup_question>' in full_response:
                print("✅ XML format: <ask_followup_question> tags present")
            elif '<' in full_response and '>' in full_response:
                print("⚠️  XML present but not standard format")
            else:
                print("❌ XML format requested but not present")
        
        # Check response completeness
        if full_response.strip():
            print(f"✅ Response generated ({len(full_response)} chars, {line_count} lines)")
        else:
            print("❌ Empty response")
        
        # Check for truncation
        if full_response.endswith('...') or 'truncated' in full_response.lower():
            print("⚠️  Response may be truncated")

if __name__ == "__main__":
    # Set environment for testing
    os.environ['DEBUG'] = '0'
    os.environ['NODE_ENV'] = 'production'
    os.environ['XML_KNOWN_TOOLS'] = 'attempt_completion,ask_followup_question'
    
    print("Environment setup:")
    print(f"  DEBUG: {os.environ.get('DEBUG')}")
    print(f"  NODE_ENV: {os.environ.get('NODE_ENV')}")
    print(f"  XML_KNOWN_TOOLS: {os.environ.get('XML_KNOWN_TOOLS')}")
    print()
    
    asyncio.run(test_final_output())