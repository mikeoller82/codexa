#!/usr/bin/env python3
"""
Direct test script for individual Claude Code tools.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from codexa.tools.base.tool_manager import ToolManager
from codexa.tools.base.tool_context import ToolContext


async def test_individual_claude_code_tools():
    """Test each Claude Code tool individually."""
    print("🎯 Testing Individual Claude Code Tools")
    print("=" * 50)
    
    # Create tool manager
    tool_manager = ToolManager(auto_discover=True)
    
    # Test cases: (tool_name, request, expected_parameters)
    test_cases = [
        ("Bash", "echo 'Hello Claude Code'", {"command": "echo 'Hello Claude Code'"}),
        ("Glob", "find all Python files", {"pattern": "**/*.py"}),
        ("Grep", "search for 'claude_code' in files", {"pattern": "claude_code"}),
        ("LS", "list files in current directory", {"path": str(project_root)}),
        ("Read", "read setup.py", {"file_path": "setup.py"}),
    ]
    
    for tool_name, request, expected_params in test_cases:
        print(f"\n⚡ Testing {tool_name}")
        print(f"   Request: {request}")
        
        try:
            # Create context
            context = ToolContext(
                user_request=request,
                current_path=str(project_root)
            )
            
            # Test tool confidence
            tool = tool_manager.registry.get_tool(tool_name)
            if tool:
                confidence = tool.can_handle_request(request, context)
                print(f"   Confidence: {confidence:.3f}")
                
                if confidence > 0.0:
                    # Execute tool directly
                    result = await tool_manager.execute_tool(tool_name, context)
                    
                    if result.success:
                        print(f"   ✅ Success")
                        if result.output and len(result.output) > 0:
                            # Show first 100 characters of output
                            output_preview = result.output[:100] + "..." if len(result.output) > 100 else result.output
                            print(f"   📤 Output: {output_preview}")
                    else:
                        print(f"   ❌ Failed: {result.error}")
                else:
                    print(f"   ⚠️  Zero confidence - tool won't handle this request")
            else:
                print(f"   ❌ Tool not found: {tool_name}")
                
        except Exception as e:
            print(f"   💥 Exception: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Individual tool testing completed!")


async def test_parameter_extraction():
    """Test parameter extraction from Claude Code registry."""
    print("\n🔧 Testing Parameter Extraction")
    print("-" * 30)
    
    try:
        from codexa.tools.claude_code.claude_code_registry import claude_code_registry
        
        test_cases = [
            ("Bash", "echo 'Hello Claude Code'"),
            ("Glob", "find all Python files"),
            ("Grep", "search for 'claude_code' in files"),
            ("LS", "list files in current directory"),
        ]
        
        context = ToolContext(
            current_path=str(project_root)
        )
        
        for tool_name, request in test_cases:
            print(f"\n🔍 {tool_name}: {request}")
            
            # Extract parameters
            params = claude_code_registry.extract_parameters_from_request(
                tool_name, request, context
            )
            
            # Validate parameters
            validation = claude_code_registry.validate_parameters(tool_name, params)
            
            print(f"   Parameters: {params}")
            print(f"   Valid: {validation['valid']}")
            if not validation['valid']:
                print(f"   Error: {validation.get('error')}")
    
    except ImportError:
        print("⚠️  Claude Code registry not available")
    except Exception as e:
        print(f"💥 Error: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(test_individual_claude_code_tools())
        asyncio.run(test_parameter_extraction())
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted")
    except Exception as e:
        print(f"💥 Test failed: {e}")
        sys.exit(1)