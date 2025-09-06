#!/usr/bin/env python3
"""Debug script to test MCP tools connection and response times."""

import asyncio
import logging
import time
from react_agent.tools import _get_all_mcp_tools, search

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_mcp_tools():
    """Test MCP tools connection and response times."""
    logger.info("Starting MCP tools test...")

    start_time = time.time()
    try:
        tools = await _get_all_mcp_tools()
        connection_time = time.time() - start_time
        logger.info(f"MCP tools loaded in {connection_time:.2f}s")
        logger.info(f"Available tools: {list(tools.keys())}")

        # Test each tool availability
        for tool_name, tool in tools.items():
            logger.info(f"Tool '{tool_name}' loaded successfully")

    except Exception as e:
        logger.error(f"Failed to load MCP tools: {e}", exc_info=True)
        return False

    return True


async def test_search_tool():
    """Test the basic search tool."""
    logger.info("Testing search tool...")

    try:
        # Test Tavily search directly without runtime context
        from langchain_tavily import TavilySearch

        tavily = TavilySearch(max_results=5)

        start_time = time.time()
        result = await tavily.ainvoke({"query": "test query"})
        search_time = time.time() - start_time
        logger.info(f"Direct Tavily search completed in {search_time:.2f}s")
        logger.info(f"Search result type: {type(result)}")
        return True
    except Exception as e:
        logger.error(f"Search tool failed: {e}", exc_info=True)
        return False


async def main():
    """Main test function."""
    logger.info("=== Starting MCP Debug Tests ===")

    # Test MCP tools connection
    mcp_success = await test_mcp_tools()

    # Test search tool
    search_success = await test_search_tool()

    logger.info("=== Test Results ===")
    logger.info(f"MCP Tools: {'✓' if mcp_success else '✗'}")
    logger.info(f"Search Tool: {'✓' if search_success else '✗'}")


if __name__ == "__main__":
    asyncio.run(main())
