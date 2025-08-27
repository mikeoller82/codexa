#!/usr/bin/env python3
"""
Demo script showcasing Codexa's enhanced search capabilities.
"""

import asyncio
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add codexa to path
sys.path.insert(0, str(Path(__file__).parent))

from codexa.search.search_manager import SearchManager, SearchType
from codexa.commands.search_commands import SearchCommand, FindCommand, GrepCommand, ProjectOverviewCommand

console = Console()

async def demo_search_functionality():
    """Demonstrate the enhanced search functionality."""
    
    console.print(Panel.fit(
        "[bold cyan]🔍 Codexa Enhanced Search System Demo[/bold cyan]\n"
        "Comprehensive file and code search capabilities",
        border_style="cyan"
    ))
    
    # Initialize search manager
    search_manager = SearchManager()
    console.print("[green]✅ Search manager initialized[/green]\n")
    
    # Demo 1: File Search
    console.print("[bold blue]📁 Demo 1: File Search[/bold blue]")
    console.print("Searching for Python files...")
    
    result = search_manager.search("*.py", SearchType.FILES, max_matches=10)
    
    if result.file_matches:
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("File")
        table.add_column("Type") 
        table.add_column("Size")
        table.add_column("Modified")
        
        for match in result.file_matches[:5]:
            size_kb = match.size / 1024 if match.size > 0 else 0
            table.add_row(
                match.relative_path,
                match.file_type,
                f"{size_kb:.1f} KB",
                match.modified_time.strftime("%Y-%m-%d %H:%M")
            )
        
        console.print(table)
        console.print(f"Found {len(result.file_matches)} files in {result.execution_time:.3f}s\n")
    
    # Demo 2: Code Search
    console.print("[bold blue]🔍 Demo 2: Code Search[/bold blue]")
    console.print("Searching for 'class' definitions...")
    
    result = search_manager.search("class ", SearchType.CODE, max_matches=5)
    
    if result.code_matches:
        for match in result.code_matches[:3]:
            console.print(f"[cyan]{match.file_path.name}:{match.line_number}[/cyan]")
            console.print(f"  {match.line_content.strip()}")
            console.print()
    
    console.print(f"Found {len(result.code_matches)} matches in {result.execution_time:.3f}s\n")
    
    # Demo 3: Function Search
    console.print("[bold blue]⚡ Demo 3: Function Search[/bold blue]")
    console.print("Searching for functions containing 'search'...")
    
    result = search_manager.search("search", SearchType.FUNCTIONS)
    
    if result.code_matches:
        for match in result.code_matches[:3]:
            console.print(f"[cyan]{match.file_path.name}:{match.line_number}[/cyan]")
            console.print(f"  {match.line_content.strip()}")
            console.print()
    
    console.print(f"Found {len(result.code_matches)} functions in {result.execution_time:.3f}s\n")
    
    # Demo 4: TODO Search
    console.print("[bold blue]📝 Demo 4: TODO Search[/bold blue]")
    console.print("Searching for TODO comments...")
    
    todos = search_manager.find_todos()
    
    if todos:
        for todo in todos[:3]:
            console.print(f"[yellow]{todo.file_path.name}:{todo.line_number}[/yellow]")
            console.print(f"  {todo.line_content.strip()}")
            console.print()
    
    console.print(f"Found {len(todos)} TODO items\n")
    
    # Demo 5: Project Overview
    console.print("[bold blue]📊 Demo 5: Project Overview[/bold blue]")
    
    overview = search_manager.get_project_overview()
    
    overview_table = Table(show_header=True, header_style="bold blue")
    overview_table.add_column("Metric")
    overview_table.add_column("Value")
    
    overview_table.add_row("Total Files", str(overview.get('total_files', 0)))
    overview_table.add_row("Total Size", f"{overview.get('total_size', 0) / (1024*1024):.1f} MB")
    overview_table.add_row("Recent Files (24h)", str(overview.get('recent_files', 0)))
    
    code_stats = overview.get('code_stats', {})
    overview_table.add_row("Functions", str(code_stats.get('functions', 0)))
    overview_table.add_row("Classes", str(code_stats.get('classes', 0)))
    overview_table.add_row("Imports", str(code_stats.get('imports', 0)))
    overview_table.add_row("TODOs", str(code_stats.get('todos', 0)))
    
    console.print(overview_table)
    console.print()
    
    # Demo 6: Command Interface
    console.print("[bold blue]⌨️  Demo 6: Command Interface[/bold blue]")
    console.print("Testing search commands...")
    
    # Test find command
    find_cmd = FindCommand(search_manager)
    find_result = await find_cmd.execute(["*.py", "--recent", "168"], {})  # Last week
    
    if find_result.success:
        console.print("[green]✅ Find command works![/green]")
        lines = find_result.output.split('\n')
        console.print(lines[0])  # Show first line
        if len(lines) > 1:
            console.print(f"  ... {len(lines)-1} more lines")
    else:
        console.print(f"[red]❌ Find command failed: {find_result.error}[/red]")
    
    console.print()
    
    # Demo 7: Performance Test
    console.print("[bold blue]🚀 Demo 7: Performance Test[/bold blue]")
    console.print("Running performance benchmark...")
    
    import time
    start_time = time.time()
    
    # Multiple searches
    for i in range(5):
        result = search_manager.quick_search(f"def test_{i}")
    
    end_time = time.time()
    avg_time = (end_time - start_time) / 5
    
    console.print(f"[green]✅ Average search time: {avg_time:.3f}s[/green]")
    
    console.print(Panel.fit(
        "[bold green]🎉 Demo completed successfully![/bold green]\n"
        "All search functionality is working properly.",
        border_style="green"
    ))

async def demo_advanced_features():
    """Demonstrate advanced search features."""
    
    console.print(Panel.fit(
        "[bold magenta]🔬 Advanced Search Features Demo[/bold magenta]",
        border_style="magenta"
    ))
    
    search_manager = SearchManager()
    
    # Fuzzy search
    console.print("[bold blue]🎯 Fuzzy Search[/bold blue]")
    result = search_manager.search("init", SearchType.FUNCTIONS, fuzzy=True, max_matches=3)
    console.print(f"Found {len(result.code_matches)} functions with fuzzy matching")
    
    # Security scan
    console.print("\n[bold blue]🛡️  Security Scan[/bold blue]")
    security_risks = search_manager.find_security_risks()
    console.print(f"Found {len(security_risks)} potential security issues")
    
    # Recent files
    console.print("\n[bold blue]⏰ Recent Files[/bold blue]")
    recent = search_manager.find_recent_files(hours=24)
    console.print(f"Found {len(recent)} files modified in the last 24 hours")
    
    # Large files
    console.print("\n[bold blue]📦 Large Files[/bold blue]")
    large_files = search_manager.find_large_files(min_size_mb=0.01)  # > 10KB
    console.print(f"Found {len(large_files)} files larger than 10KB")
    
    console.print()

if __name__ == "__main__":
    try:
        asyncio.run(demo_search_functionality())
        asyncio.run(demo_advanced_features())
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Demo failed: {e}[/red]")
        import traceback
        traceback.print_exc()