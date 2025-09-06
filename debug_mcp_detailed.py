#!/usr/bin/env python3
"""Detailed MCP connection debugging to find the exact issue."""

import asyncio
import logging
import httpx
import traceback
from dotenv import load_dotenv

load_dotenv()

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_raw_mcp_connection():
    """Test raw HTTP connection to MCP servers."""
    logger.info("=== Testing Raw MCP Server Connections ===")

    servers = [
        {"name": "twitter", "url": "http://103.149.46.64:8000/protocol/mcp/"},
        {"name": "remote", "url": "http://gc.rrrr.run:8001/sse"},
    ]

    for server in servers:
        logger.info(f"--- Testing {server['name']} server ---")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test basic connection
                response = await client.get(server["url"])
                logger.info(f"✅ {server['name']}: HTTP {response.status_code}")
                logger.info(f"   Headers: {dict(response.headers)}")
                logger.info(f"   Content: {response.text[:200]}...")
        except Exception as e:
            logger.error(f"❌ {server['name']}: {e}")
            logger.error(f"   Traceback: {traceback.format_exc()}")


async def test_mcp_client_with_different_configs():
    """Test MCP client with different timeout configurations."""
    logger.info("=== Testing MCP Client Configurations ===")

    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient

        # Test 1: Without timeout (original issue)
        logger.info("--- Test 1: Default configuration ---")
        try:
            config_default = {
                "twitter": {
                    "url": "http://103.149.46.64:8000/protocol/mcp/",
                    "transport": "streamable_http",
                }
            }
            client1 = MultiServerMCPClient(config_default)
            tools1 = await asyncio.wait_for(client1.get_tools(), timeout=8.0)
            logger.info(f"✅ Default config: {len(tools1)} tools loaded")
        except Exception as e:
            logger.error(f"❌ Default config failed: {e}")
            logger.error(f"   Full error: {traceback.format_exc()}")

        # Test 2: With strict timeout
        logger.info("--- Test 2: With httpx timeout ---")
        try:
            timeout_config = httpx.Timeout(connect=3.0, read=5.0, write=5.0, pool=5.0)
            config_timeout = {
                "twitter": {
                    "url": "http://103.149.46.64:8000/protocol/mcp/",
                    "transport": "streamable_http",
                    "timeout": timeout_config,
                }
            }
            client2 = MultiServerMCPClient(config_timeout)
            tools2 = await asyncio.wait_for(client2.get_tools(), timeout=8.0)
            logger.info(f"✅ Timeout config: {len(tools2)} tools loaded")
        except Exception as e:
            logger.error(f"❌ Timeout config failed: {e}")
            logger.error(f"   Full error: {traceback.format_exc()}")

        # Test 3: With relaxed timeout
        logger.info("--- Test 3: With relaxed timeout ---")
        try:
            relaxed_timeout = httpx.Timeout(
                connect=10.0, read=30.0, write=30.0, pool=30.0
            )
            config_relaxed = {
                "twitter": {
                    "url": "http://103.149.46.64:8000/protocol/mcp/",
                    "transport": "streamable_http",
                    "timeout": relaxed_timeout,
                }
            }
            client3 = MultiServerMCPClient(config_relaxed)
            tools3 = await asyncio.wait_for(client3.get_tools(), timeout=35.0)
            logger.info(f"✅ Relaxed config: {len(tools3)} tools loaded")

            # If successful, list the tools
            for tool in tools3[:5]:  # Show first 5 tools
                logger.info(f"   Tool: {tool.name}")

        except Exception as e:
            logger.error(f"❌ Relaxed config failed: {e}")
            logger.error(f"   Full error: {traceback.format_exc()}")

    except ImportError as e:
        logger.error(f"❌ Import error: {e}")


async def test_mcp_protocol_directly():
    """Test MCP protocol communication directly."""
    logger.info("=== Testing Direct MCP Protocol ===")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test MCP initialization handshake
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"roots": {"listChanged": True}, "sampling": {}},
                    "clientInfo": {"name": "test-client", "version": "1.0.0"},
                },
            }

            headers = {"Content-Type": "application/json", "Accept": "application/json"}

            response = await client.post(
                "http://103.149.46.64:8000/protocol/mcp/",
                json=init_request,
                headers=headers,
            )

            logger.info(f"✅ MCP Protocol response: {response.status_code}")
            logger.info(f"   Content: {response.text}")

    except Exception as e:
        logger.error(f"❌ Direct MCP test failed: {e}")
        logger.error(f"   Traceback: {traceback.format_exc()}")


async def main():
    """Main diagnostic function."""
    logger.info("🔍 Starting detailed MCP connection diagnosis...")

    await test_raw_mcp_connection()
    await test_mcp_client_with_different_configs()
    await test_mcp_protocol_directly()

    logger.info("🏁 Diagnosis complete. Check logs above for issues.")


if __name__ == "__main__":
    asyncio.run(main())
