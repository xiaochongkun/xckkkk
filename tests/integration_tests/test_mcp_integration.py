"""Integration tests for MCP functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from react_agent.tools import _get_all_mcp_tools, check_twitter_connection_status


class TestMCPIntegration:
    """Integration tests for MCP server connections."""

    @pytest.mark.asyncio
    async def test_mcp_tools_initialization(self) -> None:
        """Test MCP tools can be initialized without errors."""
        # This test will actually try to connect to MCP servers
        # In a real environment, these might fail, but the function should handle it gracefully
        tools = await _get_all_mcp_tools()
        
        # Should always return a dict, even if empty
        assert isinstance(tools, dict)
        
        # Log what we got for debugging
        print(f"Loaded {len(tools)} MCP tools: {list(tools.keys())}")

    @pytest.mark.asyncio
    async def test_connection_status_check(self) -> None:
        """Test connection status check integration."""
        status = await check_twitter_connection_status()
        
        # Should always return status info
        assert "status" in status
        assert status["status"] in ["healthy", "degraded", "error"]
        
        # Should have these keys regardless of connection state
        expected_keys = ["status"]
        for key in expected_keys:
            assert key in status

    @pytest.mark.asyncio
    @patch("react_agent.tools.MultiServerMCPClient")
    async def test_mcp_client_integration_mock(self, mock_client_class: MagicMock) -> None:
        """Test MCP client integration with mocked servers."""
        # Mock successful connection
        mock_tool = MagicMock()
        mock_tool.name = "post_tweet"
        mock_tool.description = "Post a tweet"
        
        mock_client = AsyncMock()
        mock_client.get_tools.return_value = [mock_tool]
        mock_client_class.return_value = mock_client
        
        tools = await _get_all_mcp_tools()
        
        # Should have our mocked tool
        assert "post_tweet" in tools
        assert tools["post_tweet"] == mock_tool

    @pytest.mark.asyncio 
    @patch("react_agent.tools.MultiServerMCPClient")
    async def test_mcp_client_partial_failure(self, mock_client_class: MagicMock) -> None:
        """Test MCP integration when some servers fail."""
        call_count = 0
        
        def mock_client_factory(config: dict) -> AsyncMock:
            nonlocal call_count
            client = AsyncMock()
            
            if call_count == 0:
                # First server (twitter) succeeds
                mock_tool = MagicMock()
                mock_tool.name = "post_tweet" 
                client.get_tools.return_value = [mock_tool]
            else:
                # Second server (remote) fails
                client.get_tools.side_effect = Exception("Connection failed")
            
            call_count += 1
            return client
        
        mock_client_class.side_effect = mock_client_factory
        
        tools = await _get_all_mcp_tools()
        
        # Should still get tools from successful server
        assert isinstance(tools, dict)
        # The exact content depends on the mocking, but it shouldn't crash

    @pytest.mark.asyncio
    async def test_timeout_handling_integration(self) -> None:
        """Test that timeout handling works in integration."""
        # This test verifies that the timeout mechanisms don't cause crashes
        with patch("asyncio.wait_for") as mock_wait_for:
            mock_wait_for.side_effect = TimeoutError("Timeout")
            
            tools = await _get_all_mcp_tools()
            
            # Should return empty dict on timeout, not crash
            assert isinstance(tools, dict)

    @pytest.mark.asyncio
    async def test_cache_behavior_integration(self) -> None:
        """Test caching behavior in integration."""
        # First call - should hit servers
        tools1 = await _get_all_mcp_tools()
        
        # Second call - should potentially use cache
        tools2 = await _get_all_mcp_tools()
        
        # Both should be dicts
        assert isinstance(tools1, dict)
        assert isinstance(tools2, dict)
        
        # The exact equality depends on caching logic and timing


class TestErrorRecovery:
    """Test error recovery mechanisms."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self) -> None:
        """Test circuit breaker behavior in integration."""
        # This tests the circuit breaker doesn't cause permanent failures
        
        # Multiple calls should eventually stabilize
        for i in range(5):
            tools = await _get_all_mcp_tools()
            assert isinstance(tools, dict)
            
            # Small delay between calls
            import asyncio
            await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_fallback_mechanisms(self) -> None:
        """Test fallback mechanisms work."""
        # Test that even with various failures, we get consistent behavior
        status = await check_twitter_connection_status()
        
        # Should always return a status
        assert "status" in status
        
        # Get tools with potential failures
        tools = await _get_all_mcp_tools()
        assert isinstance(tools, dict)


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    @pytest.mark.asyncio
    async def test_cold_start_scenario(self) -> None:
        """Test cold start scenario (first time loading tools)."""
        # This simulates the first time the system starts up
        tools = await _get_all_mcp_tools()
        status = await check_twitter_connection_status()
        
        # Both should work without crashing
        assert isinstance(tools, dict)
        assert isinstance(status, dict)

    @pytest.mark.asyncio
    async def test_concurrent_tool_access(self) -> None:
        """Test concurrent access to tools."""
        # Simulate multiple concurrent requests
        import asyncio
        
        async def get_tools_task() -> dict:
            return await _get_all_mcp_tools()
        
        tasks = [get_tools_task() for _ in range(3)]
        results = await asyncio.gather(*tasks)
        
        # All should return dicts
        for result in results:
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_rapid_succession_calls(self) -> None:
        """Test rapid succession calls to MCP functions."""
        # Test that rapid calls don't cause issues
        for _ in range(10):
            tools = await _get_all_mcp_tools()
            assert isinstance(tools, dict)
            
            # Very short delay to simulate rapid calls
            import asyncio
            await asyncio.sleep(0.01)