#!/usr/bin/env python3
"""Simple agent test for Twitter functionality."""

import asyncio
import httpx
import json
import time


async def test_simple_agent_response():
    """Test simple agent response without Twitter operations."""
    print("🤖 Testing simple agent response...")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
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

            # Test simple message
            test_message = "Hello! Can you tell me what Twitter tools are available?"

            print(f"💬 Sending: {test_message}")
            start_time = time.time()

            # Send streaming request
            async with client.stream(
                "POST",
                f"http://127.0.0.1:2024/threads/{thread_id}/runs/stream",
                json={
                    "assistant_id": assistant_id,
                    "input": {"messages": [{"role": "human", "content": test_message}]},
                },
            ) as stream_response:
                response_time = time.time() - start_time
                print(f"⏱️ Response in {response_time:.2f}s")

                if stream_response.status_code == 200:
                    content_chunks = []
                    async for line in stream_response.aiter_lines():
                        if line.strip():
                            content_chunks.append(line)

                    content_str = "\n".join(content_chunks)
                    print(f"📏 Response: {len(content_str)} chars")
                    print("✅ Agent responded successfully")

                    # Show last few lines for debugging
                    lines = content_str.split("\n")
                    relevant_lines = [
                        line
                        for line in lines[-10:]
                        if line.strip() and '"content"' in line
                    ]
                    if relevant_lines:
                        print("📝 Response preview:")
                        for line in relevant_lines[-2:]:
                            # Extract content from JSON
                            try:
                                if '"content":' in line:
                                    import re

                                    match = re.search(r'"content":"([^"]*)"', line)
                                    if match:
                                        content_text = match.group(1).replace(
                                            "\\n", " "
                                        )[:100]
                                        print(f"   {content_text}...")
                            except:
                                pass

                    return True
                else:
                    print(f"❌ HTTP Error: {stream_response.status_code}")
                    return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def main():
    """Main test function."""
    print("=== Simple Agent Functionality Test ===")

    result = await test_simple_agent_response()

    print("\n=== Results ===")
    if result:
        print("🎉 SUCCESS: Agent is responding normally!")
        print("💡 You can now try Twitter operations through the Studio UI")
        print(
            "🎨 Studio URL: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024"
        )
    else:
        print("❌ FAILED: Agent has issues responding")


if __name__ == "__main__":
    asyncio.run(main())
