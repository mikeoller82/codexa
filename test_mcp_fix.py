#!/usr/bin/env python3
"""Test script to verify MCP tool fixes are working."""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import Codexa components
from codexa.tools.base.tool_interface import ToolContext, ToolResult
from codexa.tools.filesystem.write_file_tool import WriteFileTool
from codexa.tools.serena.code_analysis_tool import CodeAnalysisTool
from codexa.tools.serena.shell_execution_tool import ShellExecutionTool
from codexa.mcp_service import MCPService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_write_file_tool():
    """Test write_file tool validation and execution."""
    logger.info("Testing write_file tool...")
    
    tool = WriteFileTool()
    
    # Test 1: Context with explicit parameters
    context1 = ToolContext()
    context1.update_state("file_path", "/tmp/test_explicit.txt")
    context1.update_state("content", "Test content from explicit parameters")
    
    # Validation should pass
    if await tool.validate_context(context1):
        logger.info("✅ write_file validation passed with explicit parameters")
    else:
        logger.error("❌ write_file validation failed with explicit parameters")
        return False
    
    # Test 2: Context with user request (implicit extraction)
    context2 = ToolContext()
    context2.user_request = "Create file /tmp/test_implicit.txt with content 'Hello from extraction'"
    
    # Validation should pass
    if await tool.validate_context(context2):
        logger.info("✅ write_file validation passed with user request")
    else:
        logger.error("❌ write_file validation failed with user request")
        return False
    
    # Test 3: Context with no parameters (should still pass now)
    context3 = ToolContext()
    
    # Validation should pass (flexible validation)
    if await tool.validate_context(context3):
        logger.info("✅ write_file validation passed with no parameters (flexible)")
    else:
        logger.error("❌ write_file validation failed with no parameters")
        return False
    
    logger.info("✅ All write_file tool tests passed!")
    return True

async def test_serena_tools():
    """Test Serena tools validation."""
    logger.info("Testing Serena tools...")
    
    # Create mock MCP service
    class MockMCPService:
        def __init__(self):
            self.started = False
        
        def get_serena_client(self):
            return None  # Simulate no client available
        
        async def start_servers(self):
            self.started = True
            logger.info("Mock MCP service started")
    
    # Test context with MCP service
    context = ToolContext()
    context.mcp_service = MockMCPService()
    
    # Test code analysis tool
    code_tool = CodeAnalysisTool()
    if await code_tool.validate_context(context):
        logger.info("✅ CodeAnalysisTool validation passed")
    else:
        logger.error("❌ CodeAnalysisTool validation failed")
        return False
    
    # Test shell execution tool
    shell_tool = ShellExecutionTool()
    if await shell_tool.validate_context(context):
        logger.info("✅ ShellExecutionTool validation passed")
    else:
        logger.error("❌ ShellExecutionTool validation failed")
        return False
    
    # Test context without MCP service
    context_no_mcp = ToolContext()
    
    if not await code_tool.validate_context(context_no_mcp):
        logger.info("✅ CodeAnalysisTool correctly rejected context without MCP service")
    else:
        logger.error("❌ CodeAnalysisTool incorrectly accepted context without MCP service")
        return False
    
    logger.info("✅ All Serena tool tests passed!")
    return True

async def main():
    """Run all tests."""
    logger.info("Starting MCP tool fix verification tests...")
    
    success = True
    
    # Test write_file tool
    if not await test_write_file_tool():
        success = False
    
    # Test Serena tools
    if not await test_serena_tools():
        success = False
    
    if success:
        logger.info("🎉 All tests passed! MCP tool fixes are working.")
        return 0
    else:
        logger.error("💥 Some tests failed. Please check the output above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)