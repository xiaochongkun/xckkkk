#!/usr/bin/env python3
"""Simulate Studio UI conversation to identify hang points."""

import asyncio
import httpx
import json
import time


async def test_agent_conversation():
    """Test complete agent conversation flow."""

    print("🧪 Testing agent conversation flow...")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # 1. Create thread
            print("📄 Creating thread...")
            thread_response = await client.post(
                "http://127.0.0.1:2024/threads", json={"metadata": {}}
            )
            thread_data = thread_response.json()
            thread_id = thread_data["thread_id"]
            print(f"✅ Thread created: {thread_id}")

            # 2. Create assistant
            print("🤖 Creating assistant...")
            assistant_response = await client.post(
                "http://127.0.0.1:2024/assistants",
                json={
                    "graph_id": "agent",
                    "config": {"configurable": {}},
                    "metadata": {},
                },
            )
            assistant_data = assistant_response.json()
            assistant_id = assistant_data["assistant_id"]
            print(f"✅ Assistant created: {assistant_id}")

            # 3. Send message with streaming
            print("💬 Sending message...")
            start_time = time.time()

            stream_response = await client.post(
                f"http://127.0.0.1:2024/threads/{thread_id}/runs/stream",
                json={
                    "assistant_id": assistant_id,
                    "input": {
                        "messages": [
                            {
                                "role": "human",
                                "content": "Hello! Can you search for information about Python?",
                            }
                        ]
                    },
                },
            )

            response_time = time.time() - start_time
            print(f"📊 Response received in {response_time:.2f}s")
            print(f"📊 Status: {stream_response.status_code}")

            if stream_response.status_code == 200:
                # Read streaming response
                print("📖 Reading stream...")
                content = await stream_response.aread()
                print(f"📏 Response length: {len(content)} bytes")
                return True
            else:
                print(f"❌ Error: {stream_response.status_code}")
                print(f"📄 Response: {await stream_response.aread()}")
                return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def main():
    """Main test function."""
    print("=== Studio Simulation Test ===")
    success = await test_agent_conversation()

    if success:
        print("🎉 Test PASSED: Agent conversation flow works!")
    else:
        print("💥 Test FAILED: Agent still has issues")


if __name__ == "__main__":
    asyncio.run(main())
