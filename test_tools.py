#!/usr/bin/env python3
"""
Simple test script to verify tool functionality.
"""

import sys
import asyncio
import logging
from pathlib import Path

# Add codexa to path
sys.path.insert(0, str(Path(__file__).parent))

from codexa.tools.base.tool_registry import ToolRegistry
from codexa.tools.base.tool_manager import ToolManager
from codexa.tools.base.tool_context import ToolContext
from codexa.tools.basic import BashTool, ReadTool, ListTool

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)


async def test_basic_tools():
    """Test the basic tools we created."""
    print("🧪 Testing basic tools...")

    # Create tool registry and manager
    registry = ToolRegistry()
    tool_manager = ToolManager(registry=registry)

    # Register basic system tools for testing (with different names to avoid conflicts)
    print("📝 Registering system tools for testing...")
    from codexa.tools.basic import BashTool as BasicBashTool
    registry.register_tool(BasicBashTool)

    # Check registered tools
    available_tools = registry.get_all_tools()
    print(f"✅ Registered tools: {list(available_tools.keys())}")

    # Let tool manager create its own context
    context = None

    # Debug info
    print(f"Debug - Current working directory: {Path.cwd()}")

    # Test list tool
    print("\n📂 Testing list tool...")
    try:
        result = await tool_manager.process_request("list current directory", context)
        if result.success:
            print(f"✅ List tool succeeded: {result.output}")
            print(f"   Found {result.data.get('entry_count', 0)} entries")
        else:
            print(f"❌ List tool failed: {result.error}")
    except Exception as e:
        print(f"❌ List tool exception: {e}")

    # Test read tool
    print("\n📖 Testing read tool...")
    try:
        # Try to read this test file
        result = await tool_manager.process_request("read test_tools.py", context)
        if result.success:
            print(f"✅ Read tool succeeded: {result.output}")
            print(f"   File size: {result.data.get('size', 0)} bytes")
        else:
            print(f"❌ Read tool failed: {result.error}")
    except Exception as e:
        print(f"❌ Read tool exception: {e}")

    # Test bash tool
    print("\n💻 Testing bash tool...")
    try:
        # Test with different bash command formats
        result = await tool_manager.process_request("bash echo 'Hello World'", context)
        if result.success:
            print(f"✅ Bash tool succeeded: {result.output}")
            print(f"   Output: {result.data.get('stdout', '')}")
            print(f"   Full data: {result.data}")
        else:
            print(f"❌ Bash tool failed: {result.error}")
    except Exception as e:
        print(f"❌ Bash tool exception: {e}")

    print("\n🎯 Tool test completed!")


if __name__ == "__main__":
    asyncio.run(test_basic_tools())