#!/usr/bin/env python3
"""Test Qwen integration through the API endpoint."""

import requests
import json
import sys

def test_qwen_api():
    """Test Qwen through the OpenAI-compatible API."""
    url = "http://localhost:8000/v1/chat/completions"
    
    # Test with different model configurations
    test_cases = [
        {
            "name": "Auto model selection",
            "model": "qwen-auto",
            "message": "What is the capital of France? Reply with just the city name."
        },
        {
            "name": "Specific model (qwen3-coder-plus)",
            "model": "qwen-qwen3-coder-plus",
            "message": "Write a Python function that returns the sum of two numbers. Just the code, no explanation."
        },
        {
            "name": "Stream test",
            "model": "qwen-auto",
            "message": "Count from 1 to 5.",
            "stream": True
        }
    ]
    
    all_passed = True
    
    for test in test_cases:
        print(f"\n{'='*60}")
        print(f"Test: {test['name']}")
        print(f"Model: {test['model']}")
        print(f"Message: {test['message']}")
        print('-'*60)
        
        payload = {
            "model": test['model'],
            "messages": [
                {"role": "user", "content": test['message']}
            ],
            "stream": test.get('stream', False)
        }
        
        # Use headers if API key is configured
        request_headers = headers.copy() if headers else {}
        
        try:
            if test.get('stream', False):
                # Test streaming
                response = requests.post(url, json=payload, headers=request_headers, stream=True)
                response.raise_for_status()
                
                print("Response (streaming):")
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            data_str = line_str[6:]
                            if data_str == '[DONE]':
                                break
                            try:
                                data = json.loads(data_str)
                                content = data['choices'][0]['delta'].get('content', '')
                                if content:
                                    print(content, end='', flush=True)
                                    full_response += content
                            except json.JSONDecodeError:
                                pass
                print()  # New line after streaming
                
                # Check for debug messages
                debug_indicators = ["[DEBUG]", "Loaded cached", "credentials", "[MemoryDiscovery]"]
                has_debug = any(indicator in full_response for indicator in debug_indicators)
                
                if has_debug:
                    print("❌ FAILED: Debug output detected in streaming response")
                    all_passed = False
                else:
                    print("✅ PASSED: Clean streaming response")
            else:
                # Test non-streaming
                response = requests.post(url, json=payload, headers=request_headers)
                response.raise_for_status()
                
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                print(f"Response: {content}")
                
                # Check for debug messages
                debug_indicators = ["[DEBUG]", "Loaded cached", "credentials", "[MemoryDiscovery]"]
                has_debug = any(indicator in content for indicator in debug_indicators)
                
                if has_debug:
                    print("❌ FAILED: Debug output detected in response")
                    all_passed = False
                else:
                    print("✅ PASSED: Clean response")
                    
        except requests.exceptions.RequestException as e:
            print(f"❌ FAILED: Request error: {e}")
            all_passed = False
        except Exception as e:
            print(f"❌ FAILED: Unexpected error: {e}")
            all_passed = False
    
    print(f"\n{'='*60}")
    if all_passed:
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
    
    return all_passed

if __name__ == "__main__":
    # Check if server is running and get API key if needed
    headers = {}
    try:
        # Try without auth first
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 401:
            # API key required - use a test key
            headers = {"Authorization": "Bearer test-api-key"}
            response = requests.get("http://localhost:8000/health", headers=headers)
        response.raise_for_status()
    except:
        print("⚠️  Server not running. Please start the server with:")
        print("   cd /Users/val/claude-code-openai-wrapper/.conductor/qwen")
        print("   poetry run uvicorn main:app --reload --port 8000")
        sys.exit(1)
    
    success = test_qwen_api()
    sys.exit(0 if success else 1)