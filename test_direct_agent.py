#!/usr/bin/env python3
"""
直接测试 Twitter MCP LangGraph Agent
绕过API服务器，直接调用图执行
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加src路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_agent():
    """测试智能体基本功能"""
    print("🤖 Testing Twitter MCP LangGraph Agent (Direct)")
    print("=" * 60)
    
    try:
        # 导入组件
        print("1️⃣ 导入组件...")
        from react_agent.graph import graph
        from react_agent.context import Context
        
        print("✅ 组件导入成功")
        
        # 检查环境变量
        print("\n2️⃣ 检查环境配置...")
        if not os.getenv("ANTHROPIC_API_KEY"):
            print("⚠️  警告: 未设置 ANTHROPIC_API_KEY")
        else:
            print("✅ ANTHROPIC_API_KEY 已设置")
            
        if not os.getenv("TAVILY_API_KEY"):
            print("⚠️  警告: 未设置 TAVILY_API_KEY")
        else:
            print("✅ TAVILY_API_KEY 已设置")
        
        # 测试图结构
        print("\n3️⃣ 测试图结构...")
        print(f"✅ 图类型: {type(graph)}")
        
        # 准备消息
        print("\n4️⃣ 执行简单对话测试...")
        messages = [
            {"role": "user", "content": "你好！你能做什么？"}
        ]
        
        config = {
            "configurable": {
                "model": "anthropic/claude-3-5-sonnet-20240620"
            }
        }
        
        # 异步执行
        print("📤 发送消息到智能体...")
        result = await graph.ainvoke(
            {"messages": messages},
            config=config
        )
        
        print("✅ 智能体响应成功！")
        
        # 输出结果
        if "messages" in result and result["messages"]:
            last_message = result["messages"][-1]
            print(f"\n🤖 智能体回复:")
            print(f"角色: {last_message.get('role', 'unknown')}")
            print(f"内容: {last_message.get('content', 'No content')}")
        
        print("\n✅ 直接测试完成！智能体工作正常。")
        return True
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 执行错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # 运行异步测试
    success = asyncio.run(test_agent())
    if success:
        print("\n🎉 所有测试通过！项目配置正确。")
    else:
        print("\n❌ 测试失败，请检查配置。")
        sys.exit(1)