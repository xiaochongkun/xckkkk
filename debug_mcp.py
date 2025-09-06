#!/usr/bin/env python3
"""Debug script to test MCP connections and identify specific errors."""

import asyncio
import logging
import traceback
from typing import Any

import httpx
from langchain_mcp_adapters.client import MultiServerMCPClient

# Configure detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def test_mcp_connections():
    """Test both MCP server connections individually with detailed error reporting."""

    # Configure timeout settings
    timeout_config = httpx.Timeout(
        connect=5.0,  # Connection timeout
        read=10.0,  # Read timeout
        write=5.0,  # Write timeout
        pool=5.0,  # Pool timeout
    )

    # Test servers individually
    servers = [
        {
            "name": "twitter",
            "config": {
                "url": "http://103.149.46.64:8000/protocol/mcp/",
                "transport": "streamable_http",
                "timeout": timeout_config,
            },
        },
        {
            "name": "remote_server",
            "config": {
                "url": "http://gc.rrrr.run:8001/sse",
                "transport": "sse",
                "timeout": timeout_config,
            },
        },
    ]

    for server in servers:
        print(f"\n{'=' * 50}")
        print(f"Testing {server['name']} server...")
        print(f"URL: {server['config']['url']}")
        print(f"Transport: {server['config']['transport']}")

        try:
            client = MultiServerMCPClient({server["name"]: server["config"]})
            print(f"✓ Client created successfully")

            tools = await client.get_tools()
            print(f"✓ Tools retrieved successfully: {len(tools)} tools found")

            # List tool names
            tool_names = [tool.name for tool in tools]
            print(f"  Available tools: {tool_names}")

        except Exception as e:
            print(f"✗ Failed to connect to {server['name']}")
            print(f"  Error type: {type(e).__name__}")
            print(f"  Error message: {str(e)}")
            print(f"  Full traceback:")
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_mcp_connections())
