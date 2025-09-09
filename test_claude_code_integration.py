#!/usr/bin/env python3
"""
Test script for Claude Code tools integration.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from codexa.tools.base.tool_manager import ToolManager
from codexa.tools.base.tool_context import ToolContext


async def test_claude_code_integration():
    """Test Claude Code tools integration."""
    print("🧪 Testing Claude Code Tools Integration")
    print("=" * 50)
    
    # Create tool manager with auto-discovery
    tool_manager = ToolManager(auto_discover=True)
    
    # Check available tools
    available_tools = tool_manager.get_available_tools()
    claude_code_tools = [tool for tool in available_tools if tool.startswith(('Task', 'Bash', 'Glob', 'Grep', 'LS', 'Read', 'Write', 'Edit', 'MultiEdit', 'WebFetch', 'WebSearch', 'TodoWrite', 'NotebookEdit', 'BashOutput', 'KillBash'))]
    
    print(f"📊 Total tools available: {len(available_tools)}")
    print(f"🔧 Claude Code tools: {len(claude_code_tools)}")
    print(f"   {', '.join(claude_code_tools)}")
    print()
    
    # Test tool discovery for different categories
    categories = {}
    for tool_name in available_tools:
        tool_info = tool_manager.get_tool_info(tool_name)
        if tool_info:
            category = tool_info.get('category', 'unknown')
            if category not in categories:
                categories[category] = []
            categories[category].append(tool_name)
    
    print("📋 Tools by category:")
    for category, tools in categories.items():
        print(f"   {category}: {len(tools)} tools")
        if category == "claude_code":
            for tool in tools:
                print(f"     - {tool}")
    print()
    
    # Test simple tool requests
    test_requests = [
        ("LS tool test", "list files in current directory"),
        ("Glob tool test", "find all Python files"),
        ("Grep tool test", "search for 'claude_code' in files"),
        ("Bash tool test", "echo 'Hello Claude Code'"),
    ]
    
    print("🔄 Testing tool requests:")
    
    for test_name, request in test_requests:
        print(f"\n⚡ {test_name}")
        print(f"   Request: {request}")
        
        try:
            # Create context
            context = ToolContext(
                tool_manager=tool_manager,
                current_path=str(project_root),
                user_request=request
            )
            
            # Process request
            result = await tool_manager.process_request(request, context)
            
            if result.success:
                print(f"   ✅ Success: {result.tool_name}")
                if result.output:
                    # Show first 100 characters of output
                    output_preview = result.output[:100] + "..." if len(result.output) > 100 else result.output
                    print(f"   📤 Output: {output_preview}")
            else:
                print(f"   ❌ Failed: {result.error}")
                
        except Exception as e:
            print(f"   💥 Exception: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Claude Code integration test completed!")


async def test_specific_claude_code_tool():
    """Test a specific Claude Code tool directly."""
    print("\n🎯 Testing specific Claude Code tool")
    print("-" * 30)
    
    try:
        from codexa.tools.claude_code import LSTool
        
        # Create tool instance
        ls_tool = LSTool()
        print(f"Tool: {ls_tool.name} ({ls_tool.category})")
        print(f"Description: {ls_tool.description}")
        
        # Create context
        context = ToolContext(
            current_path=str(project_root)
        )
        context.update_state("path", str(project_root))
        
        # Execute tool
        result = await ls_tool.execute(context)
        
        if result.success:
            print("✅ Direct tool execution successful")
            print(f"📊 Found {result.data.get('count', 0)} entries")
        else:
            print(f"❌ Direct tool execution failed: {result.error}")
            
    except ImportError as e:
        print(f"⚠️  Could not import Claude Code tools: {e}")
    except Exception as e:
        print(f"💥 Error testing specific tool: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(test_claude_code_integration())
        asyncio.run(test_specific_claude_code_tool())
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted")
    except Exception as e:
        print(f"💥 Test failed: {e}")
        sys.exit(1)