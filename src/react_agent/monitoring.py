"""Monitoring and observability utilities for the React Agent."""

import logging
import time
from functools import wraps
from typing import Any, Awaitable, Callable, Dict, Optional, TypeVar

# Type variable for decorated functions
F = TypeVar("F", bound=Callable[..., Any])
AsyncF = TypeVar("AsyncF", bound=Callable[..., Awaitable[Any]])

# Metrics storage (in production, this would be replaced with proper metrics backend)
_metrics: Dict[str, Any] = {
    "tool_calls": {},
    "mcp_connections": {},
    "errors": {},
    "performance": {},
}

logger = logging.getLogger(__name__)


def track_tool_usage(tool_name: str) -> Callable[[F], F]:
    """Decorator to track tool usage metrics."""
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            
            # Initialize metrics for this tool if needed
            if tool_name not in _metrics["tool_calls"]:
                _metrics["tool_calls"][tool_name] = {
                    "count": 0,
                    "errors": 0,
                    "total_time": 0.0,
                    "avg_time": 0.0,
                }
            
            try:
                result = func(*args, **kwargs)
                
                # Record success
                execution_time = time.time() - start_time
                _metrics["tool_calls"][tool_name]["count"] += 1
                _metrics["tool_calls"][tool_name]["total_time"] += execution_time
                _metrics["tool_calls"][tool_name]["avg_time"] = (
                    _metrics["tool_calls"][tool_name]["total_time"] / 
                    _metrics["tool_calls"][tool_name]["count"]
                )
                
                logger.debug(f"Tool {tool_name} executed successfully in {execution_time:.3f}s")
                return result
                
            except Exception as e:
                # Record error
                _metrics["tool_calls"][tool_name]["errors"] += 1
                logger.error(f"Tool {tool_name} failed: {e}")
                raise
                
        return wrapper  # type: ignore
    return decorator


def track_async_tool_usage(tool_name: str) -> Callable[[AsyncF], AsyncF]:
    """Decorator to track async tool usage metrics."""
    def decorator(func: AsyncF) -> AsyncF:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            
            # Initialize metrics for this tool if needed
            if tool_name not in _metrics["tool_calls"]:
                _metrics["tool_calls"][tool_name] = {
                    "count": 0,
                    "errors": 0,
                    "total_time": 0.0,
                    "avg_time": 0.0,
                }
            
            try:
                result = await func(*args, **kwargs)
                
                # Record success
                execution_time = time.time() - start_time
                _metrics["tool_calls"][tool_name]["count"] += 1
                _metrics["tool_calls"][tool_name]["total_time"] += execution_time
                _metrics["tool_calls"][tool_name]["avg_time"] = (
                    _metrics["tool_calls"][tool_name]["total_time"] / 
                    _metrics["tool_calls"][tool_name]["count"]
                )
                
                logger.debug(f"Async tool {tool_name} executed successfully in {execution_time:.3f}s")
                return result
                
            except Exception as e:
                # Record error
                _metrics["tool_calls"][tool_name]["errors"] += 1
                logger.error(f"Async tool {tool_name} failed: {e}")
                raise
                
        return wrapper  # type: ignore
    return decorator


def record_mcp_connection_attempt(server_name: str, success: bool, error: Optional[str] = None) -> None:
    """Record MCP connection attempt for monitoring."""
    if server_name not in _metrics["mcp_connections"]:
        _metrics["mcp_connections"][server_name] = {
            "attempts": 0,
            "successes": 0,
            "failures": 0,
            "success_rate": 0.0,
            "last_error": None,
            "last_success": None,
            "last_failure": None,
        }
    
    stats = _metrics["mcp_connections"][server_name]
    stats["attempts"] += 1
    
    current_time = time.time()
    
    if success:
        stats["successes"] += 1
        stats["last_success"] = current_time
        logger.info(f"✅ MCP connection to {server_name} succeeded")
    else:
        stats["failures"] += 1
        stats["last_failure"] = current_time
        stats["last_error"] = error
        logger.warning(f"❌ MCP connection to {server_name} failed: {error}")
    
    # Calculate success rate
    stats["success_rate"] = stats["successes"] / stats["attempts"] if stats["attempts"] > 0 else 0.0


def record_error(error_type: str, error_message: str, context: Optional[Dict[str, Any]] = None) -> None:
    """Record error for monitoring and alerting."""
    if error_type not in _metrics["errors"]:
        _metrics["errors"][error_type] = {
            "count": 0,
            "last_occurrence": None,
            "recent_messages": [],
        }
    
    stats = _metrics["errors"][error_type]
    stats["count"] += 1
    stats["last_occurrence"] = time.time()
    
    # Keep only last 10 error messages
    stats["recent_messages"].append({
        "message": error_message,
        "timestamp": time.time(),
        "context": context or {},
    })
    if len(stats["recent_messages"]) > 10:
        stats["recent_messages"] = stats["recent_messages"][-10:]
    
    logger.error(f"Error recorded: {error_type} - {error_message}", extra={"context": context})


def get_health_status() -> Dict[str, Any]:
    """Get comprehensive health status of the system."""
    current_time = time.time()
    
    # Calculate overall health score
    total_tools = len(_metrics["tool_calls"])
    failed_tools = sum(1 for stats in _metrics["tool_calls"].values() if stats["errors"] > 0)
    tool_health_score = (total_tools - failed_tools) / total_tools if total_tools > 0 else 1.0
    
    # Calculate MCP health score
    total_mcp_servers = len(_metrics["mcp_connections"])
    if total_mcp_servers > 0:
        mcp_health_score = sum(
            stats["success_rate"] for stats in _metrics["mcp_connections"].values()
        ) / total_mcp_servers
    else:
        mcp_health_score = 1.0
    
    # Calculate overall health score
    overall_health_score = (tool_health_score + mcp_health_score) / 2
    
    # Determine status
    if overall_health_score >= 0.9:
        status = "healthy"
    elif overall_health_score >= 0.7:
        status = "degraded"
    else:
        status = "unhealthy"
    
    # Recent errors (last 1 hour)
    recent_errors = []
    hour_ago = current_time - 3600
    
    for error_type, stats in _metrics["errors"].items():
        for error_msg in stats["recent_messages"]:
            if error_msg["timestamp"] > hour_ago:
                recent_errors.append({
                    "type": error_type,
                    "message": error_msg["message"],
                    "timestamp": error_msg["timestamp"],
                    "context": error_msg["context"],
                })
    
    return {
        "status": status,
        "overall_health_score": overall_health_score,
        "tool_health_score": tool_health_score,
        "mcp_health_score": mcp_health_score,
        "timestamp": current_time,
        "tools": {
            "total": total_tools,
            "failed": failed_tools,
            "statistics": _metrics["tool_calls"],
        },
        "mcp_connections": {
            "total": total_mcp_servers,
            "statistics": _metrics["mcp_connections"],
        },
        "errors": {
            "recent_count": len(recent_errors),
            "recent_errors": recent_errors[:10],  # Last 10 recent errors
            "total_by_type": {
                error_type: stats["count"] 
                for error_type, stats in _metrics["errors"].items()
            },
        },
    }


def get_performance_metrics() -> Dict[str, Any]:
    """Get performance metrics for the system."""
    current_time = time.time()
    
    # Tool performance summary
    tool_performance = {}
    for tool_name, stats in _metrics["tool_calls"].items():
        tool_performance[tool_name] = {
            "calls": stats["count"],
            "avg_time": stats["avg_time"],
            "total_time": stats["total_time"],
            "error_rate": stats["errors"] / stats["count"] if stats["count"] > 0 else 0.0,
        }
    
    # MCP connection performance
    mcp_performance = {}
    for server_name, stats in _metrics["mcp_connections"].items():
        mcp_performance[server_name] = {
            "attempts": stats["attempts"],
            "success_rate": stats["success_rate"],
            "last_success_ago": (
                current_time - stats["last_success"] if stats["last_success"] else None
            ),
            "last_failure_ago": (
                current_time - stats["last_failure"] if stats["last_failure"] else None
            ),
        }
    
    return {
        "timestamp": current_time,
        "tools": tool_performance,
        "mcp_connections": mcp_performance,
    }


def reset_metrics() -> None:
    """Reset all metrics (useful for testing or periodic cleanup)."""
    global _metrics
    _metrics = {
        "tool_calls": {},
        "mcp_connections": {},
        "errors": {},
        "performance": {},
    }
    logger.info("All metrics have been reset")


# Health check endpoint function
async def health_check() -> Dict[str, Any]:
    """Perform comprehensive health check."""
    logger.info("Performing health check...")
    
    try:
        # Get basic health status
        health_status = get_health_status()
        
        # Add system-level checks
        health_status["system"] = {
            "timestamp": time.time(),
            "python_version": "3.13+",
            "dependencies": {
                "langchain": "available",
                "langgraph": "available", 
                "httpx": "available",
            },
        }
        
        # Add recommendations based on health
        recommendations = []
        if health_status["mcp_health_score"] < 0.8:
            recommendations.append("Consider checking MCP server connectivity")
        if health_status["tool_health_score"] < 0.8:
            recommendations.append("Some tools are experiencing errors - check logs")
        if health_status["errors"]["recent_count"] > 10:
            recommendations.append("High error rate detected - investigate recent errors")
        
        health_status["recommendations"] = recommendations
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": time.time(),
        }