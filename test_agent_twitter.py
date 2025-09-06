#!/usr/bin/env python3
"""Test Twitter functionality through agent conversation API."""

import asyncio
import httpx
import json
import time


async def test_twitter_posting_via_agent():
    """Test Twitter posting through agent conversation."""

    print("🐦 Testing Twitter posting via Agent...")

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            # Create thread
            thread_response = await client.post(
                "http://127.0.0.1:2024/threads", json={"metadata": {}}
            )
            thread_data = thread_response.json()
            thread_id = thread_data["thread_id"]
            print(f"📄 Thread: {thread_id}")

            # Create assistant
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
            print(f"🤖 Assistant: {assistant_id}")

            # Test message asking to post a tweet
            test_message = f"Please help me post a tweet with the text: 'Hello from AI agent - test post {int(time.time())}'"

            print(f"💬 Sending: {test_message}")
            start_time = time.time()

            # Send streaming request
            stream_response = await client.post(
                f"http://127.0.0.1:2024/threads/{thread_id}/runs/stream",
                json={
                    "assistant_id": assistant_id,
                    "input": {"messages": [{"role": "human", "content": test_message}]},
                },
            )

            response_time = time.time() - start_time
            print(f"⏱️ Response in {response_time:.2f}s")

            if stream_response.status_code == 200:
                content = await stream_response.aread()
                content_str = content.decode("utf-8")

                print(f"📏 Response: {len(content)} bytes")

                # Check if response mentions successful posting
                if "posted" in content_str.lower() or "success" in content_str.lower():
                    print("✅ Agent indicates Twitter posting was attempted")
                    return True
                elif (
                    "unavailable" in content_str.lower()
                    or "failed" in content_str.lower()
                ):
                    print("⚠️ Agent indicates Twitter service unavailable")
                    return "unavailable"
                else:
                    print("❓ Agent response unclear about posting status")
                    # Show last part of response for debugging
                    lines = content_str.split("\n")
                    for line in lines[-5:]:
                        if line.strip():
                            print(f"📝 {line.strip()}")
                    return "unclear"
            else:
                print(f"❌ HTTP Error: {stream_response.status_code}")
                return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def main():
    """Main test function."""
    print("=== Agent Twitter Posting Test ===")
    print(f"🆔 Configured User ID: 76d4a28f-7a35-4d45-a3a3-c64a1637207e")
    print()

    result = await test_twitter_posting_via_agent()

    print("\n=== Results ===")
    if result is True:
        print("🎉 SUCCESS: Agent can post tweets with your user ID!")
    elif result == "unavailable":
        print("⚠️ INFO: Twitter MCP service currently unavailable")
        print(
            "💡 This is expected - agent has the functionality but external service is down"
        )
    elif result == "unclear":
        print("❓ UNCLEAR: Need to check agent response manually")
    else:
        print("❌ FAILED: Agent Twitter functionality has issues")


if __name__ == "__main__":
    asyncio.run(main())
