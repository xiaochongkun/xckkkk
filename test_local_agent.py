#!/usr/bin/env python3
"""
测试本地LangGraph Agent的简单脚本
直接使用API而不依赖LangSmith Studio
"""

import asyncio
import requests
import json
from datetime import datetime

API_BASE = "http://127.0.0.1:2024"

def test_api_health():
    """测试API服务器健康状态"""
    try:
        response = requests.get(f"{API_BASE}/docs")
        if response.status_code == 200:
            print("✅ API服务器运行正常")
            return True
        else:
            print(f"❌ API服务器响应异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 无法连接到API服务器: {e}")
        return False

def create_assistant():
    """创建助手实例"""
    try:
        payload = {
            "graph_id": "agent",
            "config": {},
            "metadata": {
                "name": "Twitter MCP Agent",
                "description": "ReAct agent with Twitter MCP integration"
            }
        }
        
        response = requests.post(
            f"{API_BASE}/assistants",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code in [200, 201]:
            assistant = response.json()
            print(f"✅ 助手创建成功: {assistant['assistant_id']}")
            return assistant['assistant_id']
        else:
            print(f"❌ 创建助手失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 创建助手时出错: {e}")
        return None

def create_thread(assistant_id):
    """创建对话线程"""
    try:
        payload = {}
        response = requests.post(
            f"{API_BASE}/assistants/{assistant_id}/threads",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code in [200, 201]:
            thread = response.json()
            print(f"✅ 对话线程创建成功: {thread['thread_id']}")
            return thread['thread_id']
        else:
            print(f"❌ 创建线程失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 创建线程时出错: {e}")
        return None

def send_message(assistant_id, thread_id, message):
    """发送消息给agent"""
    try:
        payload = {
            "input": {"messages": [{"role": "user", "content": message}]},
            "config": {},
            "metadata": {}
        }
        
        response = requests.post(
            f"{API_BASE}/assistants/{assistant_id}/threads/{thread_id}/runs",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code in [200, 201]:
            run = response.json()
            print(f"✅ 消息发送成功: {run['run_id']}")
            return run['run_id']
        else:
            print(f"❌ 发送消息失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 发送消息时出错: {e}")
        return None

def main():
    print("🔧 测试Twitter MCP LangGraph Agent")
    print("=" * 50)
    
    # 1. 测试API健康状态
    print("\n1️⃣ 检查API服务器状态...")
    if not test_api_health():
        return
    
    # 2. 创建助手
    print("\n2️⃣ 创建助手实例...")
    assistant_id = create_assistant()
    if not assistant_id:
        return
    
    # 3. 创建对话线程
    print("\n3️⃣ 创建对话线程...")
    thread_id = create_thread(assistant_id)
    if not thread_id:
        return
    
    # 4. 发送测试消息
    print("\n4️⃣ 发送测试消息...")
    test_message = "Hello! Can you help me search for information about Python programming?"
    run_id = send_message(assistant_id, thread_id, test_message)
    if not run_id:
        return
    
    print(f"""
🎉 测试完成！

助手ID: {assistant_id}
线程ID: {thread_id}  
运行ID: {run_id}

你可以在浏览器中打开以下URL来查看对话:
{API_BASE}/assistants/{assistant_id}/threads/{thread_id}/runs/{run_id}

或直接访问API文档页面:
{API_BASE}/docs
""")

if __name__ == "__main__":
    main()