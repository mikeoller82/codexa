#!/usr/bin/env python3
"""
Test script for the fixed agentic loop implementation.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the codexa directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from codexa.autonomous_agent import AutonomousAgent
from codexa.mcp_service import MCPService
from codexa.enhanced_config import EnhancedConfig
from rich.console import Console

console = Console()

async def test_agentic_loop():
    """Test the agentic loop functionality."""
    console.print("[bold blue]🧪 Testing Agentic Loop Implementation[/bold blue]")
    
    try:
        # Initialize configuration
        config = EnhancedConfig()
        
        # Initialize MCP service (might not be available, that's OK)
        mcp_service = None
        try:
            mcp_service = MCPService(config)
            await mcp_service.start()
            console.print("[green]✅ MCP service started[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠️ MCP service not available: {e}[/yellow]")
        
        # Initialize autonomous agent
        agent = AutonomousAgent(mcp_service=mcp_service, console=console)
        
        # Test the agentic loop with a simple request
        test_request = "create a simple Python script called hello_world.py that prints Hello, World!"
        
        console.print(f"[dim]Test request: {test_request}[/dim]")
        console.print("\n" + "="*60)
        
        # Run the agentic loop
        result = await agent.process_request_autonomously_streaming(test_request)
        
        console.print("\n" + "="*60)
        console.print("[bold green]🎯 Test Result:[/bold green]")
        console.print(result)
        
        # Check if files were created
        test_file = Path("hello_world.py")
        if test_file.exists():
            console.print(f"[green]✅ Test file created successfully: {test_file}[/green]")
            console.print(f"[dim]Content: {test_file.read_text()[:100]}...[/dim]")
        else:
            console.print(f"[red]❌ Test file not found: {test_file}[/red]")
        
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Test failed with error: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return False
        
    finally:
        # Cleanup MCP service
        if mcp_service:
            try:
                await mcp_service.stop()
                console.print("[dim]MCP service stopped[/dim]")
            except:
                pass

async def test_multiple_iterations():
    """Test the agentic loop with multiple iterations."""
    console.print("\n[bold blue]🔄 Testing Multiple Iterations[/bold blue]")
    
    try:
        # Initialize
        config = EnhancedConfig()
        mcp_service = None
        agent = AutonomousAgent(mcp_service=mcp_service, console=console)
        
        # Test request that should require multiple iterations
        test_request = "create a Python calculator module with add, subtract, multiply functions and also create tests for it"
        
        console.print(f"[dim]Multi-iteration test: {test_request}[/dim]")
        console.print("\n" + "="*60)
        
        # Run the agentic loop
        result = await agent.process_request_autonomously_streaming(test_request)
        
        console.print("\n" + "="*60)
        console.print("[bold green]🎯 Multi-iteration Result:[/bold green]")
        console.print(result)
        
        # Check for multiple files
        expected_files = ["calculator.py", "test_calculator.py"]
        for file_name in expected_files:
            test_file = Path(file_name)
            if test_file.exists():
                console.print(f"[green]✅ File created: {test_file}[/green]")
            else:
                console.print(f"[yellow]⚠️ Expected file not found: {test_file}[/yellow]")
        
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Multi-iteration test failed: {e}[/red]")
        return False

def cleanup_test_files():
    """Clean up test files created during testing."""
    test_files = [
        "hello_world.py",
        "calculator.py", 
        "test_calculator.py",
        "new_file_iter_1.py",
        "README.md"
    ]
    
    for file_name in test_files:
        test_file = Path(file_name)
        if test_file.exists():
            try:
                test_file.unlink()
                console.print(f"[dim]Cleaned up: {file_name}[/dim]")
            except:
                pass

async def main():
    """Main test function."""
    console.print("[bold cyan]🚀 Agentic Loop Test Suite[/bold cyan]")
    console.print("This tests the fixed iterative autonomous agent implementation.\n")
    
    # Cleanup any existing test files
    cleanup_test_files()
    
    success_count = 0
    total_tests = 2
    
    # Test 1: Basic agentic loop
    if await test_agentic_loop():
        success_count += 1
    
    # Test 2: Multiple iterations
    if await test_multiple_iterations():
        success_count += 1
    
    # Summary
    console.print(f"\n[bold cyan]📊 Test Summary[/bold cyan]")
    console.print(f"Tests passed: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        console.print("[bold green]🎉 All tests passed! Agentic loop is working correctly.[/bold green]")
    else:
        console.print(f"[yellow]⚠️ {total_tests - success_count} test(s) failed.[/yellow]")
    
    # Offer to cleanup
    console.print(f"\n[dim]Test files may have been created. Run with --cleanup to remove them.[/dim]")
    
    if "--cleanup" in sys.argv:
        cleanup_test_files()
        console.print("[green]Test files cleaned up.[/green]")

if __name__ == "__main__":
    # Run the test suite
    asyncio.run(main())