#!/usr/bin/env python3
"""Test improved MCP connection stability."""

import asyncio
import logging
import time
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from react_agent.tools import (
    _get_all_mcp_tools, 
    post_tweet, 
    check_twitter_connection_status,
    _get_connection_status
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_connection_stability():
    """Test MCP connection stability with multiple attempts."""
    logger.info("=== Testing Improved MCP Connection Stability ===")
    
    results = []
    
    # Test multiple connection attempts
    for i in range(5):
        logger.info(f"--- Connection Test {i+1}/5 ---")
        start_time = time.time()
        
        try:
            tools = await _get_all_mcp_tools()
            connection_time = time.time() - start_time
            
            twitter_tools = [name for name in tools.keys() if 'tweet' in name]
            
            result = {
                "attempt": i + 1,
                "success": len(tools) > 0,
                "twitter_tools_count": len(twitter_tools),
                "total_tools": len(tools),
                "connection_time": round(connection_time, 2),
                "available_tools": twitter_tools
            }
            
            logger.info(f"✅ Attempt {i+1}: {len(tools)} tools loaded in {connection_time:.2f}s")
            logger.info(f"   Twitter tools: {twitter_tools}")
            
        except Exception as e:
            connection_time = time.time() - start_time
            result = {
                "attempt": i + 1,
                "success": False,
                "error": str(e),
                "connection_time": round(connection_time, 2)
            }
            logger.error(f"❌ Attempt {i+1} failed: {e}")
        
        results.append(result)
        
        # Wait between attempts
        if i < 4:
            await asyncio.sleep(2)
    
    return results

async def test_connection_health_tracking():
    """Test connection health tracking functionality."""
    logger.info("=== Testing Connection Health Tracking ===")
    
    try:
        # Get initial status
        status = await _get_connection_status()
        logger.info(f"Initial connection status: {status}")
        
        # Force a connection attempt
        tools = await _get_all_mcp_tools()
        
        # Get updated status
        updated_status = await _get_connection_status()
        logger.info(f"Updated connection status: {updated_status}")
        
        return updated_status
        
    except Exception as e:
        logger.error(f"Health tracking test failed: {e}")
        return {"error": str(e)}

async def main():
    """Main test function."""
    logger.info("🔧 Testing Improved Twitter MCP Connection...")
    
    # Test 1: Connection stability
    stability_results = await test_connection_stability()
    
    # Test 2: Health tracking
    health_status = await test_connection_health_tracking()
    
    # Analysis
    logger.info("\n=== Results Analysis ===")
    
    successful_attempts = [r for r in stability_results if r.get('success', False)]
    success_rate = len(successful_attempts) / len(stability_results)
    
    logger.info(f"📊 Success Rate: {success_rate:.1%} ({len(successful_attempts)}/{len(stability_results)} attempts)")
    
    if successful_attempts:
        avg_time = sum(r['connection_time'] for r in successful_attempts) / len(successful_attempts)
        max_tools = max(r.get('total_tools', 0) for r in successful_attempts)
        logger.info(f"⚡ Average connection time: {avg_time:.2f}s")
        logger.info(f"🛠️ Maximum tools loaded: {max_tools}")
    
    # Recommendations
    if success_rate >= 0.8:
        logger.info("✅ Connection stability: GOOD")
    elif success_rate >= 0.6:
        logger.info("⚠️ Connection stability: MODERATE - may need further tuning")
    else:
        logger.info("❌ Connection stability: POOR - requires investigation")
    
    logger.info(f"🏥 Final health status: {health_status}")

if __name__ == "__main__":
    asyncio.run(main())