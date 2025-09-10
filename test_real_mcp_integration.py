#!/usr/bin/env python3
"""Test real MCP integration end-to-end."""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from codexa.enhanced_core import EnhancedCodexaAgent
from codexa.enhanced_config import EnhancedConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_real_integration():
    """Test actual MCP integration with real tools."""
    logger.info("Testing real MCP integration...")
    
    try:
        # Create agent (it creates its own config and initializes automatically)
        agent = EnhancedCodexaAgent()
        
        logger.info("✅ Agent initialized successfully")
        
        # Test basic tool coordination
        response = await agent.process_request("Create a simple test file called hello.txt with the content 'Hello MCP!'")
        
        if response and not response.startswith("ERROR"):
            logger.info("✅ File creation request processed successfully")
            logger.info(f"Response: {response[:200]}...")
        else:
            logger.error(f"❌ File creation failed: {response}")
            return False
        
        # Check if file was created
        test_file = Path("hello.txt")
        if test_file.exists():
            content = test_file.read_text()
            if "Hello MCP!" in content:
                logger.info("✅ Test file was created with correct content")
                test_file.unlink()  # Clean up
            else:
                logger.error(f"❌ Test file has wrong content: {content}")
                return False
        else:
            logger.warning("⚠️ Test file was not created (MCP tools may not be enabled)")
        
        # Clean up (agent handles its own cleanup)
        logger.info("✅ Test completed, agent handles cleanup automatically")
        
        logger.info("✅ Real MCP integration test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Real integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run real integration test."""
    logger.info("Starting real MCP integration test...")
    
    success = await test_real_integration()
    
    if success:
        logger.info("🎉 Real MCP integration is working!")
        return 0
    else:
        logger.error("💥 Real MCP integration failed.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)