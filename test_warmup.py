"""Test warmup functionality."""

import asyncio
import time
import httpx
import json
import os
import sys

async def test_first_request_latency():
    """Measure first request latency with different strategies."""
    
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    api_key = os.getenv("API_KEY", "")
    
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        print("=" * 60)
        print("WARMUP SYSTEM TEST")
        print("=" * 60)
        
        # Check warmup stats first
        try:
            stats_response = await client.get(
                f"{base_url}/v1/warmup/stats",
                headers=headers
            )
            if stats_response.status_code == 200:
                stats = stats_response.json()
                print(f"Current warmup configuration:")
                print(json.dumps(stats.get("stats", {}), indent=2))
                print("-" * 40)
        except Exception as e:
            print(f"Could not fetch warmup stats: {e}")
        
        # Measure first request
        print("Testing first request latency...")
        start = time.time()
        
        try:
            response = await client.post(
                f"{base_url}/v1/chat/completions",
                json={
                    "model": "claude-3-5-sonnet-20241022",
                    "messages": [{"role": "user", "content": "Say 'hi' in one word"}],
                    "max_tokens": 10,
                    "stream": False
                },
                headers=headers
            )
            
            first_latency = time.time() - start
            
            if response.status_code == 200:
                print(f"✅ First request successful")
                print(f"   Latency: {first_latency:.2f}s")
                
                # Extract response content
                data = response.json()
                if "choices" in data and data["choices"]:
                    content = data["choices"][0]["message"]["content"]
                    print(f"   Response: {content[:50]}...")
            else:
                print(f"❌ First request failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return
                
        except Exception as e:
            print(f"❌ First request error: {e}")
            return
        
        print("-" * 40)
        
        # Wait a bit
        await asyncio.sleep(2)
        
        # Measure second request
        print("Testing second request latency...")
        start = time.time()
        
        try:
            response = await client.post(
                f"{base_url}/v1/chat/completions",
                json={
                    "model": "claude-3-5-sonnet-20241022",
                    "messages": [{"role": "user", "content": "Say 'bye' in one word"}],
                    "max_tokens": 10,
                    "stream": False
                },
                headers=headers
            )
            
            second_latency = time.time() - start
            
            if response.status_code == 200:
                print(f"✅ Second request successful")
                print(f"   Latency: {second_latency:.2f}s")
                
                # Extract response content
                data = response.json()
                if "choices" in data and data["choices"]:
                    content = data["choices"][0]["message"]["content"]
                    print(f"   Response: {content[:50]}...")
            else:
                print(f"❌ Second request failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Second request error: {e}")
            return
        
        print("=" * 60)
        print("RESULTS SUMMARY")
        print("=" * 60)
        print(f"First request:  {first_latency:.2f}s")
        print(f"Second request: {second_latency:.2f}s")
        
        if first_latency > second_latency:
            improvement = (first_latency - second_latency) / first_latency * 100
            print(f"Improvement:    {improvement:.1f}%")
        else:
            print("No improvement (warmup may already be active)")
        
        # Check final warmup stats
        try:
            stats_response = await client.get(
                f"{base_url}/v1/warmup/stats",
                headers=headers
            )
            if stats_response.status_code == 200:
                stats = stats_response.json()
                print("-" * 40)
                print("Final warmup statistics:")
                print(json.dumps(stats.get("stats", {}), indent=2))
        except Exception as e:
            print(f"Could not fetch final warmup stats: {e}")
        
        print("=" * 60)

async def test_warmup_strategies():
    """Test different warmup strategies."""
    
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    api_key = os.getenv("API_KEY", "")
    
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        print("\n" + "=" * 60)
        print("WARMUP STRATEGY TEST")
        print("=" * 60)
        
        # Get current stats
        stats_response = await client.get(
            f"{base_url}/v1/warmup/stats",
            headers=headers
        )
        
        if stats_response.status_code == 200:
            stats = stats_response.json()["stats"]
            
            print(f"Current Strategy: {stats.get('strategy', 'unknown')}")
            print(f"Warmup Count:     {stats.get('warmup_count', 0)}")
            print(f"Failures:         {stats.get('warmup_failures', 0)}")
            print(f"Avg Warmup Time:  {stats.get('average_warmup_time', 0):.3f}s")
            print(f"Last Request:     {stats.get('last_request_ago', 0):.1f}s ago")
            print(f"Current RPM:      {stats.get('current_rpm', 0)}")
            
            if stats.get('strategy') == 'adaptive':
                print(f"Persistent Mode:  {stats.get('is_persistent_mode', False)}")
        else:
            print(f"Could not fetch warmup stats: {stats_response.status_code}")
        
        print("=" * 60)

def print_usage():
    """Print usage instructions."""
    print("Usage: python test_warmup.py [test_name]")
    print("")
    print("Tests:")
    print("  latency    - Test first vs second request latency (default)")
    print("  strategies - Test warmup strategies and stats")
    print("  all        - Run all tests")
    print("")
    print("Environment variables:")
    print("  API_BASE_URL - API base URL (default: http://localhost:8000)")
    print("  API_KEY      - API key if authentication is enabled")
    print("")
    print("Example:")
    print("  API_KEY=your-key python test_warmup.py latency")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help", "help"]:
        print_usage()
        sys.exit(0)
    
    test = sys.argv[1] if len(sys.argv) > 1 else "latency"
    
    if test == "latency":
        asyncio.run(test_first_request_latency())
    elif test == "strategies":
        asyncio.run(test_warmup_strategies())
    elif test == "all":
        asyncio.run(test_first_request_latency())
        asyncio.run(test_warmup_strategies())
    else:
        print(f"Unknown test: {test}")
        print()
        print_usage()
        sys.exit(1)