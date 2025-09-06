#!/usr/bin/env python3
"""Test Twitter posting functionality with the configured user ID."""

import asyncio
import logging
import time
from react_agent.tools import post_tweet, _get_all_mcp_tools
from langgraph.runtime import get_runtime

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_mcp_connection():
    """Test MCP tools connection status."""
    logger.info("Testing MCP connection...")

    try:
        start_time = time.time()
        tools = await _get_all_mcp_tools()
        connection_time = time.time() - start_time

        logger.info(f"MCP connection test completed in {connection_time:.2f}s")
        logger.info(
            f"Available Twitter tools: {[name for name in tools.keys() if 'tweet' in name]}"
        )

        return len(tools) > 0, tools
    except Exception as e:
        logger.error(f"MCP connection failed: {e}")
        return False, {}


async def test_twitter_posting():
    """Test posting a tweet."""
    logger.info("Testing Twitter posting functionality...")

    # Test message
    test_message = "🤖 Testing automated tweet posting from AI agent - " + str(
        int(time.time())
    )

    try:
        logger.info(f"Attempting to post: {test_message}")
        start_time = time.time()

        result = await post_tweet(test_message)

        post_time = time.time() - start_time
        logger.info(f"Post attempt completed in {post_time:.2f}s")
        logger.info(f"Result: {result}")

        # Check if successful
        if result.get("status") == "success" or "tweet_id" in result:
            logger.info("✅ Tweet posted successfully!")
            return True, result
        else:
            logger.warning(f"⚠️ Tweet posting failed: {result}")
            return False, result

    except Exception as e:
        logger.error(f"❌ Error posting tweet: {e}")
        return False, {"error": str(e)}


async def main():
    """Main test function."""
    logger.info("=== Twitter Posting Test ===")

    # Test 1: MCP Connection
    logger.info("--- Test 1: MCP Connection ---")
    mcp_success, tools = await test_mcp_connection()

    # Test 2: Twitter Posting (only if MCP works)
    logger.info("--- Test 2: Twitter Posting ---")
    if mcp_success:
        post_success, post_result = await test_twitter_posting()
    else:
        logger.warning("Skipping posting test - MCP connection failed")
        post_success = False
        post_result = {"error": "MCP connection unavailable"}

    # Results
    logger.info("=== Test Results ===")
    logger.info(f"MCP Connection: {'✅' if mcp_success else '❌'}")
    logger.info(f"Twitter Posting: {'✅' if post_success else '❌'}")

    if post_success:
        logger.info("🎉 Twitter posting functionality is working!")
        logger.info(f"User ID: 76d4a28f-7a35-4d45-a3a3-c64a1637207e")
    else:
        logger.info("💭 Twitter posting currently unavailable")
        logger.info("This is expected if MCP servers are not accessible")


if __name__ == "__main__":
    asyncio.run(main())
