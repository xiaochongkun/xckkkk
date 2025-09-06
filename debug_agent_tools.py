#!/usr/bin/env python3
"""Debug Twitter tools loading specifically in agent context."""

import asyncio
import logging
import sys
import os

# Add src to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from react_agent.tools import _get_all_mcp_tools, post_tweet
from react_agent.context import Context
from langgraph.runtime import Runtime

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_tools_in_agent_context():
    """Test MCP tools loading in agent context vs standalone."""
    logger.info("=== Testing Tools in Agent Context ===")

    try:
        # Test 1: Direct tools loading (like standalone test)
        logger.info("--- Test 1: Direct MCP Tools Loading ---")
        tools_direct = await _get_all_mcp_tools()
        logger.info(f"Direct loading: {len(tools_direct)} tools")
        logger.info(f"Available tools: {list(tools_direct.keys())}")

        # Test 2: Simulate agent runtime context
        logger.info("--- Test 2: Agent Runtime Context ---")

        # Create a mock runtime similar to what agent uses
        context = Context()
        logger.info(f"Context twitter_user_id: {context.twitter_user_id}")

        # Test post_tweet function directly
        if "post_tweet" in tools_direct:
            logger.info("--- Test 3: Direct post_tweet Tool Call ---")
            post_tool = tools_direct["post_tweet"]

            try:
                # Test the tool directly
                result = await post_tool.ainvoke(
                    {
                        "text": "Test tweet from debug script",
                        "user_id": context.twitter_user_id,
                        "media_inputs": [],
                    }
                )
                logger.info(f"Direct tool result: {result}")
            except Exception as e:
                logger.error(f"Direct tool call failed: {e}")
        else:
            logger.warning("post_tweet tool not available in direct loading")

    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")


async def main():
    """Main debug function."""
    logger.info("🐛 Starting agent tools debugging...")
    await test_tools_in_agent_context()
    logger.info("🏁 Agent tools debugging complete")


if __name__ == "__main__":
    asyncio.run(main())
