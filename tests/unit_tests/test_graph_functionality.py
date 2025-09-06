"""Test graph functionality and error handling."""

from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from react_agent.graph import handle_tool_error, route_model_output
from react_agent.state import State


class TestGraphFunctionality:
    """Test ReAct graph functionality."""

    def test_route_model_output_with_tool_calls(self) -> None:
        """Test routing when model output has tool calls."""
        ai_message = AIMessage(content="I'll search for that", tool_calls=[
            {"name": "search", "args": {"query": "test"}, "id": "call_123"}
        ])
        state = State(messages=[ai_message])
        
        result = route_model_output(state)
        assert result == "tools"

    def test_route_model_output_without_tool_calls(self) -> None:
        """Test routing when model output has no tool calls."""
        ai_message = AIMessage(content="Here's your answer: ...")
        state = State(messages=[ai_message])
        
        result = route_model_output(state)
        assert result == "__end__"

    def test_route_model_output_invalid_message_type(self) -> None:
        """Test routing with invalid message type raises error."""
        human_message = HumanMessage(content="Hello")
        state = State(messages=[human_message])
        
        with pytest.raises(ValueError, match="Expected AIMessage"):
            route_model_output(state)

    @pytest.mark.asyncio
    async def test_handle_tool_error_with_tool_calls(self) -> None:
        """Test error handling when last message has tool calls."""
        ai_message = AIMessage(content="I'll search", tool_calls=[
            {"name": "search", "args": {"query": "test"}, "id": "call_123"}
        ])
        state = State(messages=[ai_message])
        error = Exception("Tool failed")
        
        result = await handle_tool_error(state, error)
        
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], ToolMessage)
        assert result["messages"][0].tool_call_id == "call_123"
        assert "Tool execution failed" in result["messages"][0].content

    @pytest.mark.asyncio
    async def test_handle_tool_error_without_tool_calls(self) -> None:
        """Test error handling when last message has no tool calls."""
        ai_message = AIMessage(content="Simple response")
        state = State(messages=[ai_message])
        error = Exception("Tool failed")
        
        result = await handle_tool_error(state, error)
        
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], ToolMessage)
        assert result["messages"][0].tool_call_id == "unknown"

    @pytest.mark.asyncio
    async def test_handle_tool_error_empty_messages(self) -> None:
        """Test error handling with empty message list."""
        state = State(messages=[])
        error = Exception("Tool failed")
        
        result = await handle_tool_error(state, error)
        
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert result["messages"][0].tool_call_id == "unknown"

    @pytest.mark.asyncio
    async def test_handle_tool_error_non_ai_message(self) -> None:
        """Test error handling when last message is not AIMessage."""
        human_message = HumanMessage(content="Hello")
        state = State(messages=[human_message])
        error = Exception("Tool failed")
        
        result = await handle_tool_error(state, error)
        
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert result["messages"][0].tool_call_id == "unknown"


class TestStateManagement:
    """Test state management functionality."""

    def test_state_creation(self) -> None:
        """Test creating a new state."""
        messages = [HumanMessage(content="Hello")]
        state = State(messages=messages)
        
        assert len(state.messages) == 1
        assert state.messages[0].content == "Hello"
        assert state.is_last_step is False

    def test_state_with_last_step(self) -> None:
        """Test state with last step flag."""
        messages = [HumanMessage(content="Hello")]
        state = State(messages=messages, is_last_step=True)
        
        assert state.is_last_step is True

    def test_message_accumulation(self) -> None:
        """Test that messages can be accumulated in state."""
        initial_messages = [HumanMessage(content="Hello")]
        state = State(messages=initial_messages)
        
        # Simulate adding more messages
        new_message = AIMessage(content="Hi there!")
        state.messages.append(new_message)
        
        assert len(state.messages) == 2
        assert state.messages[1].content == "Hi there!"


class TestGraphEdgeCases:
    """Test edge cases in graph execution."""

    def test_route_model_output_empty_tool_calls(self) -> None:
        """Test routing when tool_calls is empty list."""
        ai_message = AIMessage(content="Response", tool_calls=[])
        state = State(messages=[ai_message])
        
        result = route_model_output(state)
        assert result == "__end__"

    def test_route_model_output_none_tool_calls(self) -> None:
        """Test routing when tool_calls is None."""
        ai_message = AIMessage(content="Response")
        # Ensure tool_calls is None (default)
        if hasattr(ai_message, 'tool_calls'):
            ai_message.tool_calls = None
            
        state = State(messages=[ai_message])
        
        result = route_model_output(state)
        assert result == "__end__"

    @pytest.mark.asyncio
    async def test_handle_tool_error_malformed_tool_call(self) -> None:
        """Test error handling with tool call that has missing id."""
        # Create AI message with tool call that has weird id
        ai_message = AIMessage(content="I'll search", tool_calls=[
            {"name": "search", "args": {"query": "test"}, "id": None}  # None id
        ])
        state = State(messages=[ai_message])
        error = Exception("Tool failed")
        
        # Should handle gracefully - either use the None or fallback to "unknown"
        result = await handle_tool_error(state, error)
        
        assert "messages" in result
        # The result might be None converted to string or "unknown" as fallback
        tool_call_id = result["messages"][0].tool_call_id
        assert tool_call_id is not None  # Should have some value


class TestToolIntegration:
    """Test tool integration with the graph."""

    def test_tool_message_creation(self) -> None:
        """Test creating tool messages for graph."""
        tool_message = ToolMessage(
            content="Search results: ...",
            tool_call_id="call_123"
        )
        
        assert tool_message.content == "Search results: ..."
        assert tool_message.tool_call_id == "call_123"

    def test_message_sequence(self) -> None:
        """Test typical message sequence in conversation."""
        messages = [
            HumanMessage(content="What's the weather?"),
            AIMessage(content="I'll search for weather info", tool_calls=[
                {"name": "search", "args": {"query": "weather"}, "id": "call_123"}
            ]),
            ToolMessage(content="Weather: Sunny, 75°F", tool_call_id="call_123"),
            AIMessage(content="The weather is sunny and 75°F")
        ]
        
        state = State(messages=messages)
        assert len(state.messages) == 4
        
        # Check message types
        assert isinstance(state.messages[0], HumanMessage)
        assert isinstance(state.messages[1], AIMessage)
        assert isinstance(state.messages[2], ToolMessage)
        assert isinstance(state.messages[3], AIMessage)
        
        # Check final message has no tool calls
        final_message = state.messages[-1]
        if hasattr(final_message, 'tool_calls'):
            assert not final_message.tool_calls or len(final_message.tool_calls) == 0