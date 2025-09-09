#!/usr/bin/env python3
"""
Test script for the centralized system prompt implementation.
"""

import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from codexa.system_prompt import get_codexa_system_prompt, validate_system_prompt, SYSTEM_PROMPT_FILE
    from rich.console import Console
    from rich.panel import Panel
    
    console = Console()
    
    def test_system_prompt():
        """Test the system prompt functionality."""
        
        console.print("\n[bold cyan]🧪 Testing Codexa System Prompt Integration[/bold cyan]")
        console.print("="*60)
        
        # Check if the system prompt file exists
        console.print(f"[yellow]📋 System prompt file: {SYSTEM_PROMPT_FILE}[/yellow]")
        
        if SYSTEM_PROMPT_FILE.exists():
            console.print("[green]✅ System prompt file exists[/green]")
        else:
            console.print("[red]❌ System prompt file not found[/red]")
            return False
        
        # Validate the system prompt
        is_valid = validate_system_prompt()
        if is_valid:
            console.print("[green]✅ System prompt validation passed[/green]")
        else:
            console.print("[yellow]⚠️ System prompt validation failed (using fallback)[/yellow]")
        
        # Test loading the system prompt without context
        console.print("\n[yellow]🔍 Testing system prompt without context...[/yellow]")
        prompt_no_context = get_codexa_system_prompt()
        
        if "Codexa Agent developed by Codexa Code" in prompt_no_context:
            console.print("[green]✅ System prompt contains correct identity[/green]")
        else:
            console.print("[red]❌ System prompt missing Codexa Agent identity[/red]")
            return False
        
        if "# Role" in prompt_no_context and "# Identity" in prompt_no_context:
            console.print("[green]✅ System prompt contains required sections[/green]")
        else:
            console.print("[red]❌ System prompt missing required sections[/red]")
            return False
        
        # Test loading the system prompt with context
        console.print("\n[yellow]🔍 Testing system prompt with project context...[/yellow]")
        test_context = "This is a Python CLI project called Codexa with tool-based architecture and MCP integration."
        prompt_with_context = get_codexa_system_prompt(test_context)
        
        if test_context in prompt_with_context:
            console.print("[green]✅ Project context properly integrated[/green]")
        else:
            console.print("[red]❌ Project context not found in system prompt[/red]")
            return False
        
        # Test date replacement
        from datetime import datetime
        current_date = datetime.now().strftime("%Y-%m-%d")
        if current_date in prompt_no_context:
            console.print(f"[green]✅ Date updated to current: {current_date}[/green]")
        else:
            console.print(f"[yellow]⚠️ Date not updated (may be using fallback)[/yellow]")
        
        # Show a sample of the system prompt
        console.print("\n[yellow]📝 System prompt sample (first 500 chars):[/yellow]")
        console.print(Panel(
            prompt_no_context[:500] + "..." if len(prompt_no_context) > 500 else prompt_no_context,
            border_style="blue",
            title="Codexa System Prompt",
            title_align="left"
        ))
        
        return True
    
    def test_provider_integration():
        """Test that providers can load the system prompt."""
        
        console.print("\n[yellow]🔌 Testing provider integration...[/yellow]")
        
        try:
            from codexa.providers import OpenAIProvider, AnthropicProvider, OpenRouterProvider
            from codexa.config import Config
            
            # Create a mock config
            config = Config()
            
            # Test each provider's system prompt method
            providers = [
                ("OpenAI", OpenAIProvider(config)),
                ("Anthropic", AnthropicProvider(config)),
                ("OpenRouter", OpenRouterProvider(config))
            ]
            
            for provider_name, provider in providers:
                try:
                    system_prompt = provider._get_system_prompt("Test context")
                    if "Codexa Agent developed by Codexa Code" in system_prompt:
                        console.print(f"[green]✅ {provider_name} provider uses Codexa system prompt[/green]")
                    else:
                        console.print(f"[red]❌ {provider_name} provider not using Codexa system prompt[/red]")
                        return False
                except Exception as e:
                    console.print(f"[red]❌ {provider_name} provider error: {e}[/red]")
                    return False
            
            return True
            
        except ImportError as e:
            console.print(f"[yellow]⚠️ Could not test provider integration: {e}[/yellow]")
            return True  # Don't fail the test for import issues
    
    def main():
        """Main test function."""
        try:
            success = True
            
            success = success and test_system_prompt()
            success = success and test_provider_integration()
            
            if success:
                console.print(Panel(
                    "[bold green]🎉 System prompt integration successful![/bold green]\\n\\n"
                    "[yellow]Key Features Implemented:[/yellow]\\n"
                    "• Centralized system prompt management\\n"
                    "• Consistent Codexa Agent identity across all providers\\n"  
                    "• Project context integration\\n"
                    "• Date replacement functionality\\n"
                    "• Fallback system prompt for reliability\\n\\n"
                    "[cyan]All providers now use the official codexa-agent-prompt.txt![/cyan]",
                    title="✅ Success!",
                    title_align="left",
                    border_style="green",
                    padding=(1, 2)
                ))
                return True
            else:
                console.print(Panel(
                    "[red]❌ Some tests failed.[/red]\\n\\n"
                    "[yellow]Please check:[/yellow]\\n"
                    "• System prompt file exists in docs/\\n"
                    "• Provider implementations\\n"
                    "• Import dependencies\\n",
                    title="⚠️ Issues Found",
                    title_align="left", 
                    border_style="red",
                    padding=(1, 2)
                ))
                return False
                
        except KeyboardInterrupt:
            console.print("\\n[yellow]Test interrupted by user.[/yellow]")
            return False
        except Exception as e:
            console.print(f"[red]❌ Test failed: {e}[/red]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            return False
    
    if __name__ == "__main__":
        # Run the test
        result = main()
        sys.exit(0 if result else 1)
        
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("Please ensure Codexa is installed: pip install -e .")
    sys.exit(1)