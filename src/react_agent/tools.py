"""This module provides tools for web scraping, search functionality, and Twitter operations.

It includes Tavily search and comprehensive Twitter MCP integration for both
reading and writing operations on Twitter.

These tools enable complete Twitter account management through AI agents.
"""

import asyncio
import logging
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional, cast

# Load environment variables first - must be before other imports
from dotenv import load_dotenv

load_dotenv()

import httpx  # noqa: E402
from langchain_mcp_adapters.client import (
    MultiServerMCPClient,  # noqa: E402  # type: ignore[import-untyped]
)
from langchain_tavily import TavilySearch  # noqa: E402
from langgraph.runtime import get_runtime  # noqa: E402

from react_agent.context import Context  # noqa: E402
from react_agent.monitoring import (  # noqa: E402
    record_error,
    record_mcp_connection_attempt,
    track_async_tool_usage,
)

# Configure logging
logger = logging.getLogger(__name__)

# Global cache for MCP tools to avoid repeated connections
_mcp_tools_cache: Optional[dict[str, Any]] = None
_cache_timestamp: Optional[float] = None
CACHE_DURATION = 300  # 5 minutes cache

# Connection health tracking
_connection_health: dict[str, dict[str, Any]] = {}
MAX_RETRIES = 3
BASE_RETRY_DELAY = 1.0  # seconds
MAX_RETRY_DELAY = 8.0  # seconds

# Tool execution timeout settings
TOOL_EXECUTION_TIMEOUT = 30  # 30秒工具执行超时
MCP_CONNECTION_TIMEOUT = 20  # 20秒MCP连接超时

# Circuit breaker for failed connections
_circuit_breaker: dict[str, dict[str, Any]] = {}
CIRCUIT_BREAKER_THRESHOLD = 3  # 连续失败3次后开启断路器
CIRCUIT_BREAKER_TIMEOUT = 300  # 5分钟后重置断路器


def _update_connection_health(server_name: str, success: bool) -> None:
    """Update connection health status for a server."""
    if server_name not in _connection_health:
        _connection_health[server_name] = {
            "success_count": 0,
            "failure_count": 0,
            "last_success": None,
            "last_failure": None,
        }

    current_time = time.time()
    if success:
        _connection_health[server_name]["success_count"] += 1
        _connection_health[server_name]["last_success"] = current_time
        # Reset circuit breaker on success
        if server_name in _circuit_breaker:
            del _circuit_breaker[server_name]
    else:
        _connection_health[server_name]["failure_count"] += 1
        _connection_health[server_name]["last_failure"] = current_time
        # Update circuit breaker
        _update_circuit_breaker(server_name)


def _update_circuit_breaker(server_name: str) -> None:
    """Update circuit breaker state for a server."""
    if server_name not in _circuit_breaker:
        _circuit_breaker[server_name] = {
            "failure_count": 0,
            "last_failure": None,
            "is_open": False,
        }

    _circuit_breaker[server_name]["failure_count"] += 1
    _circuit_breaker[server_name]["last_failure"] = time.time()

    if _circuit_breaker[server_name]["failure_count"] >= CIRCUIT_BREAKER_THRESHOLD:
        _circuit_breaker[server_name]["is_open"] = True
        logger.warning(
            f"🔥 Circuit breaker opened for {server_name} after {CIRCUIT_BREAKER_THRESHOLD} failures"
        )


def _is_circuit_breaker_open(server_name: str) -> bool:
    """Check if circuit breaker is open for a server."""
    if server_name not in _circuit_breaker:
        return False

    breaker = _circuit_breaker[server_name]
    if not breaker["is_open"]:
        return False

    # Check if timeout period has passed
    if (
        breaker["last_failure"]
        and (time.time() - breaker["last_failure"]) > CIRCUIT_BREAKER_TIMEOUT
    ):
        # Reset circuit breaker
        _circuit_breaker[server_name]["is_open"] = False
        _circuit_breaker[server_name]["failure_count"] = 0
        logger.info(f"🔄 Circuit breaker reset for {server_name}")
        return False

    return True


async def _execute_tool_with_timeout(
    tool_func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any
) -> Any:
    """Execute a tool function with timeout protection."""
    try:
        return await asyncio.wait_for(
            tool_func(*args, **kwargs), timeout=TOOL_EXECUTION_TIMEOUT
        )
    except TimeoutError:
        logger.error(f"⏱️ Tool execution timed out after {TOOL_EXECUTION_TIMEOUT}s")
        return {
            "error": f"Tool execution timed out after {TOOL_EXECUTION_TIMEOUT}s",
            "status": "timeout",
        }
    except Exception as e:
        logger.error(f"❌ Tool execution failed: {e}")
        return {"error": f"Tool execution failed: {e}", "status": "error"}


async def _connect_server_with_retry(
    server: dict[str, Any], tools_dict: dict[str, Any]
) -> bool:
    """Connect to MCP server with exponential backoff retry logic."""
    server_name = server["name"]

    # Check circuit breaker
    if _is_circuit_breaker_open(server_name):
        logger.warning(
            f"🔥 Circuit breaker is open for {server_name}, skipping connection attempt"
        )
        return False

    for attempt in range(MAX_RETRIES):
        try:
            logger.info(
                f"Attempting to connect to {server_name} server (attempt {attempt + 1}/{MAX_RETRIES})..."
            )

            # Calculate retry delay with exponential backoff
            if attempt > 0:
                delay = min(BASE_RETRY_DELAY * (2 ** (attempt - 1)), MAX_RETRY_DELAY)
                logger.info(f"Waiting {delay:.1f}s before retry...")
                await asyncio.sleep(delay)

            # Timeout per server (8 seconds)
            async def connect_with_enhanced_timeout() -> List[Any]:
                client = MultiServerMCPClient({server_name: server["config"]})
                return await client.get_tools()

            tools = await asyncio.wait_for(
                connect_with_enhanced_timeout(), timeout=MCP_CONNECTION_TIMEOUT
            )

            # Success - add tools and update health
            for tool in tools:
                tools_dict[tool.name] = tool

            logger.info(
                f"✅ Successfully connected to {server_name}, loaded {len(tools)} tools"
            )
            _update_connection_health(server_name, True)
            record_mcp_connection_attempt(server_name, True)
            return True

        except TimeoutError:
            logger.warning(
                f"⏱️ Connection to {server_name} timed out (attempt {attempt + 1})"
            )
            if attempt == MAX_RETRIES - 1:
                logger.error(
                    f"❌ Failed to connect to {server_name} after {MAX_RETRIES} attempts"
                )
                _update_connection_health(server_name, False)
        except (
            httpx.ReadTimeout,
            httpx.ConnectTimeout,
            httpx.TimeoutException,
            httpx.ReadError,
        ) as e:
            logger.warning(
                f"🌐 HTTP error connecting to {server_name} (attempt {attempt + 1}): {type(e).__name__}"
            )
            if attempt == MAX_RETRIES - 1:
                logger.error(
                    f"❌ HTTP connection to {server_name} failed after {MAX_RETRIES} attempts"
                )
                _update_connection_health(server_name, False)
        except Exception as e:
            logger.warning(
                f"⚠️ Unexpected error connecting to {server_name} (attempt {attempt + 1}): {e}"
            )
            if attempt == MAX_RETRIES - 1:
                logger.error(f"❌ Connection to {server_name} failed with error: {e}")
                _update_connection_health(server_name, False)
                record_mcp_connection_attempt(server_name, False, str(e))

    return False


async def _get_connection_status() -> dict[str, Any]:
    """Get current connection status for all MCP servers."""
    return {
        "health": _connection_health,
        "cache_status": {
            "has_cache": _mcp_tools_cache is not None,
            "cache_age": time.time() - _cache_timestamp if _cache_timestamp else None,
            "cache_tools_count": len(_mcp_tools_cache) if _mcp_tools_cache else 0,
        },
    }


async def _preload_mcp_tools() -> None:
    """Preload MCP tools in background to improve responsiveness."""
    try:
        logger.info("Preloading MCP tools in background...")
        await _get_all_mcp_tools()
        logger.info("MCP tools preloading completed")
    except Exception as e:
        logger.warning(f"MCP tools preloading failed: {e}")


async def _get_all_mcp_tools() -> dict[str, Any]:
    """Initialize multi-MCP servers and return filtered tools dictionary with enhanced retry logic."""
    try:
        # Reduce timeout to 15 seconds to prevent hanging
        return await asyncio.wait_for(_get_all_mcp_tools_impl(), timeout=15.0)
    except TimeoutError:
        logger.warning(
            "MCP tools initialization timed out after 15 seconds, using cached tools if available"
        )
        # Fallback to cached tools if available
        if _mcp_tools_cache is not None:
            logger.info("Using stale cached MCP tools as fallback")
            return _mcp_tools_cache
        return {}
    except Exception as e:
        logger.warning(f"MCP tools initialization failed: {e}")
        # Fallback to cached tools if available
        if _mcp_tools_cache is not None:
            logger.info("Using cached MCP tools as fallback after error")
            return _mcp_tools_cache
        return {}


async def _get_all_mcp_tools_impl() -> dict[str, Any]:
    """Load MCP tools with enhanced caching and health checking."""
    global _mcp_tools_cache, _cache_timestamp

    current_time = time.time()

    # Check cache first - use fresher cache in case of recent failures
    if (
        _mcp_tools_cache is not None
        and _cache_timestamp is not None
        and current_time - _cache_timestamp < CACHE_DURATION
    ):
        # Check if we should refresh cache due to recent failures
        recent_failures = any(
            (health.get("last_failure") or 0) > (health.get("last_success") or 0)
            for health in _connection_health.values()
        )
        if not recent_failures:
            logger.info("Using cached MCP tools (connections healthy)")
            return _mcp_tools_cache
        else:
            logger.info("Recent connection failures detected, refreshing MCP tools...")

    tools_dict: Dict[str, Any] = {}

    # Define server configurations - let MCP client handle its own timeouts
    servers = [
        {
            "name": "twitter",
            "config": {
                "url": "http://103.149.46.64:8000/protocol/mcp/",
                "transport": "streamable_http",
            },
        },
        {
            "name": "remote_server",
            "config": {
                "url": "https://twitter-mcp.gc.rrrr.run/sse",
                "transport": "sse",
            },
        },
    ]

    # Pre-warm connection health tracking
    for server in servers:
        if server["name"] not in _connection_health:
            _connection_health[server["name"]] = {
                "success_count": 0,
                "failure_count": 0,
                "last_success": None,
                "last_failure": None,
            }

    # Initialize each server with enhanced retry logic
    for server in servers:
        success = await _connect_server_with_retry(server, tools_dict)
        if not success:
            _update_connection_health(server["name"], False)

    # Smart filtering: keep only 10 core tools
    required_tools = {
        "post_tweet",
        "delete_tweet",
        "like_tweet",
        "retweet",  # Write operations (4)
        "advanced_search_twitter",
        "get_trends",
        "get_tweets_by_IDs",  # Read operations (6)
        "get_tweet_replies",
        "get_tweet_quotations",
        "get_tweet_thread_context",
    }

    filtered_tools = {
        name: tool for name, tool in tools_dict.items() if name in required_tools
    }

    # Log missing tools - will be available in filtered_tools if servers are reachable
    missing_tools = required_tools - set(filtered_tools.keys())
    if missing_tools:
        logger.warning(f"Missing Twitter tools (services unavailable): {missing_tools}")

    # Enhanced status reporting
    if not filtered_tools:
        logger.warning("No MCP tools available - falling back to search-only mode")
        logger.info(f"Connection health: {_connection_health}")
    else:
        logger.info(f"Successfully loaded {len(filtered_tools)} MCP tools")
        available_services = [
            name
            for name, health in _connection_health.items()
            if health.get("last_success")
        ]
        logger.info(f"Available services: {available_services}")

        # Log connection quality
        for server_name, health in _connection_health.items():
            success_rate = (
                health["success_count"]
                / (health["success_count"] + health["failure_count"])
                if (health["success_count"] + health["failure_count"]) > 0
                else 0
            )
            logger.info(
                f"{server_name} connection quality: {success_rate:.1%} success rate"
            )

    # Cache results (even if partial success)
    if filtered_tools or _mcp_tools_cache is None:
        _mcp_tools_cache = filtered_tools
        _cache_timestamp = current_time
        logger.info(f"Cached {len(filtered_tools)} tools for future fallback")

        # Log detailed cache status
        cache_status = await _get_connection_status()
        logger.debug(f"Cache status: {cache_status}")

    return filtered_tools


@track_async_tool_usage("search")
async def search(query: str) -> Dict[str, Any]:
    """Search for general web results.

    This function performs a search using the Tavily search engine, which is designed
    to provide comprehensive, accurate, and trusted results. It's particularly useful
    for answering questions about current events.
    """
    runtime = get_runtime(Context)
    wrapped = TavilySearch(max_results=runtime.context.max_search_results)

    async def _search_impl() -> Dict[str, Any]:
        return cast(dict[str, Any], await wrapped.ainvoke({"query": query}))

    result = await _execute_tool_with_timeout(_search_impl)
    return cast(Dict[str, Any], result)


# === Twitter Write Operations ===


@track_async_tool_usage("post_tweet")
async def post_tweet(
    text: str, media_inputs: Optional[List[str]] = None
) -> dict[str, Any]:
    """Send a tweet with enhanced error handling and retry logic.

    Args:
        text: Tweet content (up to 280 characters)
        media_inputs: Optional list of media URLs or file paths

    Returns:
        dict: Tweet posting result with tweet ID and status
    """
    global _mcp_tools_cache
    runtime = get_runtime(Context)

    # Retry tool loading if needed
    for attempt in range(2):  # Try twice
        tools = await _get_all_mcp_tools()

        if "post_tweet" in tools:
            try:

                async def _post_impl() -> Any:
                    return await tools["post_tweet"].ainvoke(
                        {
                            "text": text,
                            "user_id": runtime.context.twitter_user_id,
                            "media_inputs": media_inputs or [],
                        }
                    )

                result = await _execute_tool_with_timeout(_post_impl)
                return cast(dict[str, Any], result)
            except Exception as e:
                logger.error(f"Twitter posting failed (attempt {attempt + 1}): {e}")
                if attempt == 0:
                    # Clear cache and retry
                    _mcp_tools_cache = None
                    await asyncio.sleep(1)
                else:
                    return {"error": f"Twitter posting failed: {e}", "status": "failed"}
        else:
            logger.warning(
                f"Twitter posting service unavailable (attempt {attempt + 1})"
            )
            if attempt == 0:
                # Clear cache and retry
                _mcp_tools_cache = None
                await asyncio.sleep(1)

    # Final fallback
    connection_status = await _get_connection_status()
    return {
        "error": "Twitter posting service unavailable after retries",
        "status": "failed",
        "debug_info": connection_status,
    }


async def delete_tweet(tweet_id: str) -> dict[str, Any]:
    """Delete a tweet with enhanced error handling.

    Args:
        tweet_id: The ID of the tweet to delete

    Returns:
        dict: Deletion result
    """
    runtime = get_runtime(Context)
    tools = await _get_all_mcp_tools()

    if "delete_tweet" not in tools:
        connection_status = await _get_connection_status()
        return {
            "error": "Twitter delete service unavailable",
            "status": "failed",
            "debug_info": connection_status,
        }

    try:
        result = await tools["delete_tweet"].ainvoke(
            {"tweet_id": tweet_id, "user_id": runtime.context.twitter_user_id}
        )
        return cast(dict[str, Any], result)
    except Exception as e:
        logger.error(f"Tweet deletion failed: {e}")
        return {"error": f"Tweet deletion failed: {e}", "status": "failed"}


async def like_tweet(tweet_id: str) -> dict[str, Any]:
    """Like a tweet with enhanced error handling.

    Args:
        tweet_id: The ID of the tweet to like

    Returns:
        dict: Like result
    """
    runtime = get_runtime(Context)
    tools = await _get_all_mcp_tools()

    if "like_tweet" not in tools:
        connection_status = await _get_connection_status()
        return {
            "error": "Twitter like service unavailable",
            "status": "failed",
            "debug_info": connection_status,
        }

    try:
        result = await tools["like_tweet"].ainvoke(
            {"tweet_id": tweet_id, "user_id": runtime.context.twitter_user_id}
        )
        return cast(dict[str, Any], result)
    except Exception as e:
        logger.error(f"Tweet liking failed: {e}")
        return {"error": f"Tweet liking failed: {e}", "status": "failed"}


async def retweet(tweet_id: str) -> dict[str, Any]:
    """Retweet a tweet with enhanced error handling.

    Args:
        tweet_id: The ID of the tweet to retweet

    Returns:
        dict: Retweet result
    """
    runtime = get_runtime(Context)
    tools = await _get_all_mcp_tools()

    if "retweet" not in tools:
        connection_status = await _get_connection_status()
        return {
            "error": "Twitter retweet service unavailable",
            "status": "failed",
            "debug_info": connection_status,
        }

    try:
        result = await tools["retweet"].ainvoke(
            {"tweet_id": tweet_id, "user_id": runtime.context.twitter_user_id}
        )
        return cast(dict[str, Any], result)
    except Exception as e:
        logger.error(f"Retweeting failed: {e}")
        return {"error": f"Retweeting failed: {e}", "status": "failed"}


# === Twitter Read Operations ===


async def advanced_search_twitter(query: str) -> dict[str, Any]:
    """Twitter advanced search with enhanced error handling.

    Supported search syntax:
    - from:username - Search specific user tweets
    - to:username - Search tweets mentioning specific users
    - #hashtag - Search hashtags
    - since:date - Search tweets after specified date
    - Combined search: "from:openai #ChatGPT since:2025-01-01"

    Args:
        query: Natural language query or query with search operators

    Returns:
        dict: Search results with matching tweets
    """
    tools = await _get_all_mcp_tools()

    if "advanced_search_twitter" not in tools:
        connection_status = await _get_connection_status()
        return {
            "error": "Twitter search service unavailable",
            "status": "failed",
            "debug_info": connection_status,
        }

    try:

        async def _search_impl() -> Any:
            return await tools["advanced_search_twitter"].ainvoke({"llm_text": query})

        result = await _execute_tool_with_timeout(_search_impl)
        return cast(dict[str, Any], result)
    except Exception as e:
        logger.error(f"Twitter search failed: {e}")
        return {"error": f"Twitter search failed: {e}", "status": "failed"}


async def get_trends(woeid: int = 1) -> dict[str, Any]:
    """Get trending topics - discover hot content for creative inspiration.

    Args:
        woeid: Geographic location ID (1=global, 23424977=USA)

    Returns:
        dict: List of current trending topics and hashtags
    """
    tools = await _get_all_mcp_tools()
    result = await tools["get_trends"].ainvoke({"woeid": woeid})
    return cast(dict[str, Any], result)


async def get_tweets_by_IDs(tweet_ids: List[str]) -> dict[str, Any]:
    """Batch get tweet details - analyze specific tweet content and data."""
    tools = await _get_all_mcp_tools()
    result = await tools["get_tweets_by_IDs"].ainvoke({"tweetIds": tweet_ids})
    return cast(dict[str, Any], result)


async def get_tweet_replies(tweet_id: str) -> dict[str, Any]:
    """Get tweet replies - monitor user interactions on your tweets."""
    tools = await _get_all_mcp_tools()
    result = await tools["get_tweet_replies"].ainvoke({"tweetId": tweet_id})
    return cast(dict[str, Any], result)


async def get_tweet_quotations(tweet_id: str) -> dict[str, Any]:
    """Get quote tweets - track tweet propagation and discussion."""
    tools = await _get_all_mcp_tools()
    result = await tools["get_tweet_quotations"].ainvoke({"tweetId": tweet_id})
    return cast(dict[str, Any], result)


async def get_tweet_thread_context(tweet_id: str) -> dict[str, Any]:
    """Get tweet thread context - understand complete conversation flow."""
    tools = await _get_all_mcp_tools()

    if "get_tweet_thread_context" not in tools:
        return {
            "error": "Twitter thread context service unavailable",
            "status": "failed",
        }

    try:
        result = await tools["get_tweet_thread_context"].ainvoke({"tweetId": tweet_id})
        return cast(dict[str, Any], result)
    except Exception as e:
        logger.error(f"Getting tweet thread context failed: {e}")
        return {
            "error": f"Getting tweet thread context failed: {e}",
            "status": "failed",
        }


async def check_twitter_connection_status() -> dict[str, Any]:
    """Check Twitter MCP connection status and health metrics.

    Returns:
        dict: Detailed connection status and health information
    """
    logger.info("Checking Twitter MCP connection status...")

    try:
        # Force refresh tools to get current status
        global _mcp_tools_cache
        _mcp_tools_cache = None
        tools = await _get_all_mcp_tools()

        twitter_tools = [name for name in tools.keys() if "tweet" in name]
        connection_status = await _get_connection_status()

        return {
            "status": "healthy" if twitter_tools else "degraded",
            "available_twitter_tools": twitter_tools,
            "total_tools": len(tools),
            "connection_health": connection_status,
            "user_id": "76d4a28f-7a35-4d45-a3a3-c64a1637207e",
        }
    except Exception as e:
        logger.error(f"Connection status check failed: {e}")
        record_error("connection_check_failed", str(e))
        return {
            "status": "error",
            "error": str(e),
            "connection_health": _connection_health,
        }


async def get_system_health() -> dict[str, Any]:
    """Get comprehensive system health status including monitoring data.
    
    Returns:
        dict: Comprehensive health information from monitoring system
    """
    from react_agent.monitoring import health_check
    return await health_check()


TOOLS: List[Callable[..., Any]] = [
    # Core tools (7)
    search,
    post_tweet,
    delete_tweet,
    like_tweet,
    retweet,
    check_twitter_connection_status,
    get_system_health,
    # Read tools (6)
    advanced_search_twitter,
    get_trends,
    get_tweets_by_IDs,
    get_tweet_replies,
    get_tweet_quotations,
    get_tweet_thread_context,
]
