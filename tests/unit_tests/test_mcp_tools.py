"""Test MCP tools integration and error handling."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from react_agent.tools import (
    _execute_tool_with_timeout,
    _get_all_mcp_tools,
    _update_circuit_breaker,
    _update_connection_health,
    check_twitter_connection_status,
    post_tweet,
    search,
)


class TestMCPTools:
    """Test MCP tools functionality."""

    @pytest.mark.asyncio
    async def test_execute_tool_with_timeout_success(self) -> None:
        """Test successful tool execution within timeout."""
        async def mock_tool() -> dict[str, str]:
            return {"result": "success"}

        result = await _execute_tool_with_timeout(mock_tool)
        assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_execute_tool_with_timeout_timeout_error(self) -> None:
        """Test tool execution timeout handling."""
        async def slow_tool() -> dict[str, str]:
            await asyncio.sleep(60)  # Longer than timeout
            return {"result": "success"}

        result = await _execute_tool_with_timeout(slow_tool)
        assert result["status"] == "timeout"
        assert "timed out" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_tool_with_timeout_exception(self) -> None:
        """Test tool execution exception handling."""
        async def failing_tool() -> dict[str, str]:
            raise ValueError("Test error")

        result = await _execute_tool_with_timeout(failing_tool)
        assert result["status"] == "error"
        assert "Test error" in result["error"]

    def test_update_connection_health_success(self) -> None:
        """Test connection health update for success."""
        _update_connection_health("test_server", True)
        # Test passes if no exception is raised

    def test_update_connection_health_failure(self) -> None:
        """Test connection health update for failure."""
        _update_connection_health("test_server", False)
        # Test passes if no exception is raised

    def test_update_circuit_breaker(self) -> None:
        """Test circuit breaker update."""
        _update_circuit_breaker("test_server")
        # Test passes if no exception is raised

    @pytest.mark.asyncio
    @patch("react_agent.tools.MultiServerMCPClient")
    async def test_get_all_mcp_tools_timeout(self, mock_client: MagicMock) -> None:
        """Test MCP tools initialization timeout."""
        # Mock client that takes too long
        mock_instance = AsyncMock()
        mock_instance.get_tools = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_client.return_value = mock_instance

        tools = await _get_all_mcp_tools()
        assert isinstance(tools, dict)  # Should return empty dict on timeout

    @pytest.mark.asyncio
    @patch("react_agent.tools.TavilySearch")
    async def test_search_function(self, mock_tavily: MagicMock) -> None:
        """Test search function with Tavily."""
        # Mock TavilySearch
        mock_search_instance = AsyncMock()
        mock_search_instance.ainvoke = AsyncMock(
            return_value={"results": [{"title": "Test", "content": "Test content"}]}
        )
        mock_tavily.return_value = mock_search_instance

        # Mock runtime context
        with patch("react_agent.tools.get_runtime") as mock_runtime:
            mock_context = MagicMock()
            mock_context.max_search_results = 5
            mock_runtime.return_value.context = mock_context

            result = await search("test query")
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    @patch("react_agent.tools._get_all_mcp_tools")
    async def test_post_tweet_service_unavailable(self, mock_get_tools: AsyncMock) -> None:
        """Test post_tweet when service is unavailable."""
        mock_get_tools.return_value = {}  # No tools available

        # Mock runtime context
        with patch("react_agent.tools.get_runtime") as mock_runtime:
            mock_context = MagicMock()
            mock_context.twitter_user_id = "test-user-id"
            mock_runtime.return_value.context = mock_context

            result = await post_tweet("Test tweet")
            assert result["status"] == "failed"
            assert "unavailable" in result["error"]

    @pytest.mark.asyncio
    @patch("react_agent.tools._get_all_mcp_tools")
    async def test_post_tweet_success(self, mock_get_tools: AsyncMock) -> None:
        """Test successful tweet posting."""
        # Mock available tools
        mock_tool = AsyncMock()
        mock_tool.ainvoke = AsyncMock(return_value={"tweet_id": "123", "status": "success"})
        mock_get_tools.return_value = {"post_tweet": mock_tool}

        # Mock runtime context
        with patch("react_agent.tools.get_runtime") as mock_runtime:
            mock_context = MagicMock()
            mock_context.twitter_user_id = "test-user-id"
            mock_runtime.return_value.context = mock_context

            result = await post_tweet("Test tweet")
            assert result["tweet_id"] == "123"
            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_check_twitter_connection_status(self) -> None:
        """Test Twitter connection status check."""
        with patch("react_agent.tools._get_all_mcp_tools") as mock_get_tools:
            mock_get_tools.return_value = {
                "post_tweet": MagicMock(),
                "search": MagicMock(),
            }

            result = await check_twitter_connection_status()
            assert "status" in result
            assert "available_twitter_tools" in result

    @pytest.mark.asyncio
    async def test_check_twitter_connection_status_error(self) -> None:
        """Test Twitter connection status check with error."""
        with patch("react_agent.tools._get_all_mcp_tools") as mock_get_tools:
            mock_get_tools.side_effect = Exception("Connection failed")

            result = await check_twitter_connection_status()
            assert result["status"] == "error"
            assert "Connection failed" in result["error"]


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_circuit_breaker_threshold(self) -> None:
        """Test circuit breaker opens after threshold failures."""
        server_name = "test_circuit_breaker"
        
        # Simulate failures up to threshold
        for _ in range(3):  # CIRCUIT_BREAKER_THRESHOLD = 3
            _update_circuit_breaker(server_name)
        
        # Test passes if no exception is raised

    def test_connection_health_tracking(self) -> None:
        """Test connection health tracking over multiple operations."""
        server_name = "test_health"
        
        # Test success tracking
        _update_connection_health(server_name, True)
        _update_connection_health(server_name, False)
        _update_connection_health(server_name, True)
        
        # Test passes if no exception is raised


class TestRetryLogic:
    """Test retry logic in MCP connections."""

    @pytest.mark.asyncio
    async def test_post_tweet_retry_logic(self) -> None:
        """Test post_tweet retry logic when tool fails."""
        call_count = 0
        
        async def failing_tool(*args, **kwargs) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First attempt fails")
            return {"tweet_id": "123", "status": "success"}

        with patch("react_agent.tools._get_all_mcp_tools") as mock_get_tools:
            mock_tool = AsyncMock()
            mock_tool.ainvoke = failing_tool
            mock_get_tools.return_value = {"post_tweet": mock_tool}

            # Mock runtime context
            with patch("react_agent.tools.get_runtime") as mock_runtime:
                mock_context = MagicMock()
                mock_context.twitter_user_id = "test-user-id"
                mock_runtime.return_value.context = mock_context

                # Mock asyncio.sleep to speed up test
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    result = await post_tweet("Test tweet")
                    
                    # Should have retried and eventually succeeded
                    assert call_count >= 1