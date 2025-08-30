#!/usr/bin/env python3
"""Test script to verify agent responds quickly without hanging."""

import asyncio
import httpx
import json
import time

async def test_agent_response():
    """Test that agent responds to input without hanging."""
    
    # Test message
    test_message = {
        "input": {
            "messages": [
                {
                    "role": "human",
                    "content": "Hello, can you help me search for information about Python programming?"
                }
            ]
        },
        "config": {
            "configurable": {}
        }
    }
    
    print("🧪 Testing agent response...")
    print(f"📝 Message: {test_message['input']['messages'][0]['content']}")
    
    start_time = time.time()
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create a new thread
            thread_response = await client.post(
                "http://127.0.0.1:2024/threads",
                json={"metadata": {}}
            )
            thread_data = thread_response.json()
            thread_id = thread_data["thread_id"]
            print(f"📄 Created thread: {thread_id}")
            
            # Send message to agent
            response = await client.post(
                f"http://127.0.0.1:2024/threads/{thread_id}/runs",
                json=test_message
            )
            
            if response.status_code == 200:
                response_time = time.time() - start_time
                print(f"✅ Agent responded in {response_time:.2f}s")
                print(f"📊 Status: {response.status_code}")
                return True
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                print(f"📄 Response: {response.text}")
                return False
                
    except asyncio.TimeoutError:
        print("❌ Request timed out after 30 seconds")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    """Main test function."""
    print("=== Agent Response Test ===")
    success = await test_agent_response()
    
    if success:
        print("🎉 Test PASSED: Agent is responding normally!")
    else:
        print("💥 Test FAILED: Agent still has issues")

if __name__ == "__main__":
    asyncio.run(main())