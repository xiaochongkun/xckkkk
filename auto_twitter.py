#!/usr/bin/env python3
"""
自动Twitter运营脚本示例
定期收集信息并发布推文
"""

import asyncio
import json
import time
from datetime import datetime

import requests

# LangGraph API配置
LANGGRAPH_API_URL = "http://127.0.0.1:2024"


async def send_message_to_agent(message: str) -> dict:
    """向Agent发送消息并获取响应"""

    payload = {
        "assistant_id": "agent",
        "input": {"messages": [{"role": "user", "content": message}]},
    }

    try:
        response = requests.post(
            f"{LANGGRAPH_API_URL}/runs/stream",
            headers={"Content-Type": "application/json"},
            json=payload,
            stream=True,
        )

        # 解析流式响应
        result = []
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line.decode("utf-8"))
                    if "event" in data and data["event"] == "data":
                        result.append(data.get("data", {}))
                except json.JSONDecodeError:
                    continue

        return {"success": True, "data": result}

    except Exception as e:
        return {"success": False, "error": str(e)}


# 自动化任务定义
AUTOMATION_TASKS = [
    {
        "name": "AI趋势分析",
        "prompt": "搜索AI和机器学习的最新趋势，创作一条有见解的推文分享给关注者",
        "interval": 3600,  # 每小时执行一次
        "last_run": 0,
    },
    {
        "name": "科技新闻总结",
        "prompt": "搜索今天的科技新闻热点，写一条简洁有趣的推文总结",
        "interval": 7200,  # 每2小时执行一次
        "last_run": 0,
    },
    {
        "name": "回复互动",
        "prompt": "检查我最近推文的回复和互动，对重要的回复进行友好回应",
        "interval": 1800,  # 每30分钟执行一次
        "last_run": 0,
    },
]


async def run_automation():
    """运行自动化任务"""

    print(f"🚀 Twitter自动化助手启动 - {datetime.now()}")

    while True:
        current_time = time.time()

        for task in AUTOMATION_TASKS:
            # 检查是否到了执行时间
            if current_time - task["last_run"] >= task["interval"]:
                print(f"\n⏰ 执行任务: {task['name']}")

                # 发送任务给Agent
                result = await send_message_to_agent(task["prompt"])

                if result["success"]:
                    print(f"✅ 任务完成: {task['name']}")
                    # 可以在这里添加日志记录
                else:
                    print(f"❌ 任务失败: {task['name']} - {result['error']}")

                task["last_run"] = current_time

                # 任务间添加延迟避免频繁调用
                await asyncio.sleep(5)

        # 每分钟检查一次任务
        await asyncio.sleep(60)


def manual_command(command: str):
    """手动执行命令"""

    print(f"🎯 执行命令: {command}")

    result = asyncio.run(send_message_to_agent(command))

    if result["success"]:
        print("✅ 命令执行成功")
        return result["data"]
    else:
        print(f"❌ 命令执行失败: {result['error']}")
        return None


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # 手动模式
        command = " ".join(sys.argv[1:])
        manual_command(command)
    else:
        # 自动模式
        try:
            asyncio.run(run_automation())
        except KeyboardInterrupt:
            print("\n👋 自动化助手已停止")
