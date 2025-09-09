#!/usr/bin/env python3
"""Test OpenAI endpoint compatibility with Qwen thinking block filtering."""

import asyncio
import httpx
import os
import json

async def test_openai_endpoint():
    """Test that the OpenAI endpoint properly filters Qwen thinking blocks."""
    
    base_url = "http://localhost:8000"
    api_key = os.environ.get("API_KEY", "test-key")
    
    # Test cases
    test_cases = [
        {
            "name": "Simple capability question",
            "messages": [{"role": "user", "content": "What can you do?"}],
            "model": "qwen-qwen3-coder-plus",
            "check_for": ["help", "can", "tasks"],
            "should_not_contain": ["The user is asking", "Based on the system information", "available tools"]
        },
        {
            "name": "Code generation", 
            "messages": [{"role": "user", "content": "Write a simple hello world in Python"}],
            "model": "qwen-qwen3-coder-plus",
            "check_for": ["print", "hello", "world"],
            "should_not_contain": ["The user wants", "I need to", "I should"]
        }
    ]
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for test_case in test_cases:
            print(f"\n{'='*60}")
            print(f"Test: {test_case['name']}")
            print(f"Model: {test_case['model']}")
            print(f"Prompt: {test_case['messages'][0]['content']}")
            print(f"{'='*60}")
            
            # Test streaming endpoint
            print("\n📡 Testing STREAMING response:")
            headers = {"Authorization": f"Bearer {api_key}"}
            payload = {
                "model": test_case["model"],
                "messages": test_case["messages"],
                "stream": True,
                "temperature": 0.7
            }
            
            try:
                full_response = ""
                async with client.stream(
                    "POST",
                    f"{base_url}/v1/chat/completions",
                    json=payload,
                    headers=headers
                ) as response:
                    if response.status_code != 200:
                        print(f"❌ Error: Status {response.status_code}")
                        continue
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                if "choices" in data and len(data["choices"]) > 0:
                                    delta = data["choices"][0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        full_response += content
                                        print(content, end="", flush=True)
                            except json.JSONDecodeError:
                                pass
                
                print(f"\n\n📊 Response Analysis:")
                
                # Check for expected content
                found_expected = []
                for expected in test_case["check_for"]:
                    if expected.lower() in full_response.lower():
                        found_expected.append(expected)
                
                if found_expected:
                    print(f"✅ Found expected content: {', '.join(found_expected)}")
                else:
                    print(f"⚠️  Missing expected content: {test_case['check_for']}")
                
                # Check for thinking patterns that should be filtered
                found_thinking = []
                for pattern in test_case["should_not_contain"]:
                    if pattern.lower() in full_response.lower():
                        found_thinking.append(pattern)
                
                if found_thinking:
                    print(f"❌ Found thinking patterns that should be filtered: {', '.join(found_thinking)}")
                else:
                    print(f"✅ No thinking patterns found - filtering successful!")
                
            except Exception as e:
                print(f"❌ Error during streaming test: {e}")
            
            # Test non-streaming endpoint
            print("\n\n📦 Testing NON-STREAMING response:")
            payload["stream"] = False
            
            try:
                response = await client.post(
                    f"{base_url}/v1/chat/completions",
                    json=payload,
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if "choices" in data and len(data["choices"]) > 0:
                        content = data["choices"][0]["message"]["content"]
                        print(f"Response preview: {content[:200]}...")
                        
                        # Check for thinking patterns
                        found_thinking = []
                        for pattern in test_case["should_not_contain"]:
                            if pattern.lower() in content.lower():
                                found_thinking.append(pattern)
                        
                        if found_thinking:
                            print(f"❌ Found thinking patterns: {', '.join(found_thinking)}")
                        else:
                            print(f"✅ No thinking patterns - filtering successful!")
                else:
                    print(f"❌ Error: Status {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Error during non-streaming test: {e}")
    
    print(f"\n{'='*60}")
    print("OpenAI endpoint compatibility test completed!")

if __name__ == "__main__":
    print("🧪 OpenAI Endpoint Compatibility Test for Qwen")
    print("Make sure the server is running: poetry run uvicorn main:app --reload --port 8000")
    print("Press Enter to continue...")
    input()
    
    asyncio.run(test_openai_endpoint())