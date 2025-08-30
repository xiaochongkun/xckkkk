#!/usr/bin/env python3
"""Basic agent test with simplified error handling."""

import asyncio
import httpx
import json

async def test_basic_agent():
    """Test basic agent functionality with detailed error output."""
    print("🤖 Testing basic agent functionality...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Create thread
            print("📄 Creating thread...")
            thread_response = await client.post(
                "http://127.0.0.1:2024/threads",
                json={"metadata": {}}
            )
            
            if thread_response.status_code != 200:
                print(f"❌ Failed to create thread: {thread_response.status_code}")
                print(f"Response: {thread_response.text}")
                return False
                
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
                    "metadata": {}
                }
            )
            
            if assistant_response.status_code != 200:
                print(f"❌ Failed to create assistant: {assistant_response.status_code}")
                print(f"Response: {assistant_response.text}")
                return False
                
            assistant_data = assistant_response.json()
            assistant_id = assistant_data["assistant_id"]
            print(f"✅ Assistant created: {assistant_id}")
            
            # 3. Send simple message and check for any response
            print("💬 Sending message...")
            response = await client.post(
                f"http://127.0.0.1:2024/threads/{thread_id}/runs",
                json={
                    "assistant_id": assistant_id,
                    "input": {
                        "messages": [
                            {
                                "role": "human", 
                                "content": "Hello! What Twitter tools do you have available?"
                            }
                        ]
                    }
                }
            )
            
            print(f"📊 Response status: {response.status_code}")
            print(f"📏 Response size: {len(response.content)} bytes")
            
            if response.status_code == 200:
                print("✅ Agent responded successfully!")
                return True
            else:
                print(f"❌ Agent response failed: {response.text[:200]}...")
                return False
                
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_basic_agent())
    if result:
        print("\n🎉 Agent基本功能验证成功!")
        print("💡 你现在可以通过Studio UI测试Twitter功能")
        print("🎨 Studio URL: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024")
    else:
        print("\n❌ Agent基本功能测试失败")