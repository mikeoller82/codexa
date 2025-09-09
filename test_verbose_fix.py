#!/usr/bin/env python3
"""
Quick test to verify the verbose parameter fix for tool manager.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from codexa.enhanced_core import EnhancedCodexaAgent
    from rich.console import Console
    
    console = Console()
    
    async def test_verbose_fix():
        """Test that verbose parameter is now accepted."""
        
        console.print("\n[bold cyan]🧪 Testing Verbose Parameter Fix[/bold cyan]")
        console.print("="*50)
        
        # Check environment
        if not (os.getenv('OPENROUTER_API_KEY') or os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY')):
            console.print("[red]❌ No API keys found. Set at least one API key first.[/red]")
            return False
        
        try:
            # Initialize enhanced agent
            console.print("[yellow]🤖 Initializing agent...[/yellow]")
            agent = EnhancedCodexaAgent()
            
            # Test simple request processing (should not trigger agentic mode)
            console.print("[yellow]📋 Testing simple request with verbose feedback...[/yellow]")
            
            # This should use direct processing with verbose feedback enabled
            simple_request = "list current directory"
            console.print(f"Request: {simple_request}")
            
            # This will call the fixed _process_request_direct method
            await agent._process_request_direct(simple_request)
            
            console.print("[green]✅ Verbose parameter fix working correctly![/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Test failed: {e}[/red]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            return False
    
    async def main():
        """Main test function."""
        try:
            success = await test_verbose_fix()
            
            if success:
                console.print("\n[bold green]🎉 Fix validated successfully![/bold green]")
                console.print("[green]The verbose parameter issue has been resolved.[/green]")
                return True
            else:
                console.print("\n[bold red]❌ Fix validation failed.[/bold red]")
                return False
                
        except KeyboardInterrupt:
            console.print("\n[yellow]Test interrupted by user.[/yellow]")
            return False
        except Exception as e:
            console.print(f"[red]❌ Test failed: {e}[/red]")
            return False
    
    if __name__ == "__main__":
        # Run the test
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
        
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("Please ensure Codexa is installed: pip install -e .")
    sys.exit(1)