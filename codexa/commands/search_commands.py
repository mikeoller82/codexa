"""
Search commands for Codexa CLI - comprehensive file and code search capabilities.
"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.columns import Columns
from rich.text import Text

from ..search.search_manager import SearchManager, SearchType
from ..search.file_search import SearchResult
from ..search.code_search import CodeMatch, SearchMode
from .base_command import BaseCommand, CommandResult

console = Console()

class SearchCommand(BaseCommand):
    """Main search command with various search modes."""
    
    def __init__(self, search_manager: SearchManager = None):
        super().__init__()
        self.search_manager = search_manager or SearchManager()
    
    def get_name(self) -> str:
        return "search"
    
    def get_description(self) -> str:
        return "Search files and code with advanced patterns and filters"
    
    def get_usage(self) -> str:
        return """
Usage: /search <query> [options]

Options:
  --type <type>        Search type: files, code, functions, classes, imports, todos, urls, security, duplicates, mixed (default: mixed)
  --ext <extensions>   File extensions to search (comma-separated)
  --regex              Use regex patterns
  --fuzzy              Use fuzzy matching
  --case-sensitive     Case-sensitive search
  --whole-words        Match whole words only
  --context <n>        Number of context lines (default: 2)
  --max <n>            Maximum results (default: 100)
  --lang <language>    Programming language filter
  --recent <hours>     Only search files modified in last N hours
  --export <format>    Export results (json, csv)

Examples:
  /search "TODO"                      # Find all TODO comments
  /search "*.py" --type files         # Find all Python files
  /search "function.*auth" --regex    # Find functions with 'auth' using regex
  /search "MyClass" --type classes    # Find class definitions
  /search --type security             # Find security risks
  /search --type duplicates           # Find duplicate code
        """
    
    async def execute(self, args: List[str], context: Dict[str, Any] = None) -> CommandResult:
        try:
            if not args:
                return CommandResult(success=False, error="Search query required")
            
            # Parse arguments
            query = args[0]
            search_options = self._parse_search_options(args[1:])
            
            # Determine search type
            search_type_str = search_options.get('type', 'mixed')
            try:
                search_type = SearchType(search_type_str)
            except ValueError:
                return CommandResult(success=False, error=f"Invalid search type: {search_type_str}")
            
            # Perform search
            console.print(f"[cyan]Searching for: '{query}'[/cyan]")
            
            with console.status("[bold green]Searching..."):
                result = self.search_manager.search(query, search_type, **search_options)
            
            # Display results
            output = self._format_search_results(result, search_options)
            
            # Export if requested
            if 'export' in search_options:
                export_format = search_options['export']
                exported_data = self.search_manager.export_results(result, export_format)
                export_file = f"search_results.{export_format}"
                Path(export_file).write_text(exported_data)
                output += f"\n[green]Results exported to: {export_file}[/green]"
            
            return CommandResult(success=True, output=output)
        
        except Exception as e:
            return CommandResult(success=False, error=f"Search failed: {e}")
    
    def _parse_search_options(self, args: List[str]) -> Dict[str, Any]:
        """Parse search command options."""
        options = {}
        i = 0
        
        while i < len(args):
            arg = args[i]
            
            if arg == '--type' and i + 1 < len(args):
                options['type'] = args[i + 1]
                i += 2
            elif arg == '--ext' and i + 1 < len(args):
                extensions = args[i + 1].split(',')
                options['extensions'] = set(f'.{ext.strip().lstrip(".")}' for ext in extensions)
                i += 2
            elif arg == '--regex':
                options['use_regex'] = True
                i += 1
            elif arg == '--fuzzy':
                options['fuzzy'] = True
                i += 1
            elif arg == '--case-sensitive':
                options['case_sensitive'] = True
                i += 1
            elif arg == '--whole-words':
                options['whole_words'] = True
                i += 1
            elif arg == '--context' and i + 1 < len(args):
                options['context_lines'] = int(args[i + 1])
                i += 2
            elif arg == '--max' and i + 1 < len(args):
                options['max_matches'] = int(args[i + 1])
                i += 2
            elif arg == '--lang' and i + 1 < len(args):
                options['language'] = args[i + 1]
                i += 2
            elif arg == '--recent' and i + 1 < len(args):
                options['recent_hours'] = int(args[i + 1])
                i += 2
            elif arg == '--export' and i + 1 < len(args):
                options['export'] = args[i + 1]
                i += 2
            else:
                i += 1
        
        return options
    
    def _format_search_results(self, result, options: Dict[str, Any]) -> str:
        """Format search results for display."""
        output_parts = []
        
        # Summary
        summary = f"Found {result.total_matches} matches in {result.execution_time:.2f}s"
        output_parts.append(f"[green]{summary}[/green]")
        
        # File matches
        if result.file_matches:
            output_parts.append("\n[bold]📁 File Matches:[/bold]")
            file_table = Table(show_header=True, header_style="bold blue")
            file_table.add_column("Path")
            file_table.add_column("Type")
            file_table.add_column("Size")
            file_table.add_column("Modified")
            
            for match in result.file_matches[:20]:  # Limit display
                size_str = self._format_file_size(match.size)
                modified_str = match.modified_time.strftime("%Y-%m-%d %H:%M")
                file_table.add_row(
                    match.relative_path,
                    match.file_type,
                    size_str,
                    modified_str
                )
            
            console.print(file_table)
            
            if len(result.file_matches) > 20:
                output_parts.append(f"[dim]... and {len(result.file_matches) - 20} more files[/dim]")
        
        # Code matches
        if result.code_matches:
            output_parts.append("\n[bold]🔍 Code Matches:[/bold]")
            
            for i, match in enumerate(result.code_matches[:10]):  # Limit display
                if i > 0:
                    output_parts.append("")
                
                # File and line info
                file_info = f"{match.file_path.name}:{match.line_number}"
                output_parts.append(f"[cyan]{file_info}[/cyan]")
                
                # Context before
                for ctx_line in match.context_before:
                    output_parts.append(f"[dim]  {ctx_line}[/dim]")
                
                # Matched line (highlighted)
                highlighted_line = self._highlight_match(match.line_content, match.match_text)
                output_parts.append(f"  {highlighted_line}")
                
                # Context after
                for ctx_line in match.context_after:
                    output_parts.append(f"[dim]  {ctx_line}[/dim]")
            
            if len(result.code_matches) > 10:
                output_parts.append(f"[dim]... and {len(result.code_matches) - 10} more matches[/dim]")
        
        # Duplicate results
        if 'duplicates' in result.metadata:
            duplicates = result.metadata['duplicates']
            if duplicates:
                output_parts.append("\n[bold]🔄 Duplicate Code:[/bold]")
                for i, dup in enumerate(duplicates[:5]):
                    output_parts.append(f"\n[yellow]Duplicate {i+1}:[/yellow]")
                    output_parts.append(f"  Original: {dup['original']['file']}:{dup['original']['start_line']}")
                    output_parts.append(f"  Duplicate: {dup['duplicate']['file']}:{dup['duplicate']['start_line']}")
                    output_parts.append(f"  Content: {dup['duplicate']['content'][:100]}...")
        
        return "\n".join(output_parts)
    
    def _highlight_match(self, line: str, match_text: str) -> str:
        """Highlight the matched text in a line."""
        if match_text in line:
            highlighted = line.replace(match_text, f"[bold red]{match_text}[/bold red]")
            return highlighted
        return line
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

class FindCommand(BaseCommand):
    """Quick file finding command."""
    
    def __init__(self, search_manager: SearchManager = None):
        super().__init__()
        self.search_manager = search_manager or SearchManager()
    
    def get_name(self) -> str:
        return "find"
    
    def get_description(self) -> str:
        return "Quick file finding by name or pattern"
    
    def get_usage(self) -> str:
        return """
Usage: /find <name> [options]

Options:
  --exact              Exact name match
  --ext <extensions>   File extensions (comma-separated)
  --recent <hours>     Files modified in last N hours
  --large <mb>         Files larger than N megabytes

Examples:
  /find config.json         # Find files named config.json
  /find "*.py" --recent 24  # Find Python files modified in last 24 hours
  /find myfile --exact      # Exact match for myfile
        """
    
    async def execute(self, args: List[str], context: Dict[str, Any] = None) -> CommandResult:
        try:
            if not args:
                return CommandResult(success=False, error="File name required")
            
            name = args[0]
            options = self._parse_find_options(args[1:])
            
            # Determine find method
            results = []
            
            if 'recent' in options:
                results = self.search_manager.find_recent_files(options['recent'])
                # Filter by name if provided
                if name != "*":
                    results = [r for r in results if name.lower() in r.path.name.lower()]
            
            elif 'large' in options:
                min_size_mb = options['large']
                results = self.search_manager.find_large_files(min_size_mb)
                # Filter by name if provided
                if name != "*":
                    results = [r for r in results if name.lower() in r.path.name.lower()]
            
            elif 'ext' in options:
                results = self.search_manager.find_by_extension(options['ext'])
                # Filter by name if provided
                if name != "*":
                    results = [r for r in results if name.lower() in r.path.name.lower()]
            
            else:
                # Standard name search
                exact = options.get('exact', False)
                results = self.search_manager.find_file(name, exact_match=exact)
            
            # Format output
            if not results:
                return CommandResult(success=True, output="[yellow]No files found[/yellow]")
            
            output_parts = [f"[green]Found {len(results)} files:[/green]\n"]
            
            for result in results[:20]:  # Limit display
                size_str = self._format_file_size(result.size)
                modified_str = result.modified_time.strftime("%Y-%m-%d %H:%M")
                output_parts.append(f"  {result.relative_path} ({size_str}, {modified_str})")
            
            if len(results) > 20:
                output_parts.append(f"\n[dim]... and {len(results) - 20} more files[/dim]")
            
            return CommandResult(success=True, output="\n".join(output_parts))
        
        except Exception as e:
            return CommandResult(success=False, error=f"Find failed: {e}")
    
    def _parse_find_options(self, args: List[str]) -> Dict[str, Any]:
        """Parse find command options."""
        options = {}
        i = 0
        
        while i < len(args):
            arg = args[i]
            
            if arg == '--exact':
                options['exact'] = True
                i += 1
            elif arg == '--ext' and i + 1 < len(args):
                extensions = args[i + 1].split(',')
                options['ext'] = [ext.strip() for ext in extensions]
                i += 2
            elif arg == '--recent' and i + 1 < len(args):
                options['recent'] = int(args[i + 1])
                i += 2
            elif arg == '--large' and i + 1 < len(args):
                options['large'] = int(args[i + 1])
                i += 2
            else:
                i += 1
        
        return options
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

class GrepCommand(BaseCommand):
    """Grep-like code search command."""
    
    def __init__(self, search_manager: SearchManager = None):
        super().__init__()
        self.search_manager = search_manager or SearchManager()
    
    def get_name(self) -> str:
        return "grep"
    
    def get_description(self) -> str:
        return "Search for patterns in code files (like grep)"
    
    def get_usage(self) -> str:
        return """
Usage: /grep <pattern> [options]

Options:
  --regex              Use regex patterns
  --ignore-case, -i    Case-insensitive search
  --word-regexp, -w    Match whole words only
  --context <n>, -C    Number of context lines
  --after <n>, -A      Number of lines after match
  --before <n>, -B     Number of lines before match
  --ext <extensions>   File extensions to search
  --max <n>            Maximum matches

Examples:
  /grep "import React"           # Find React imports
  /grep "function.*test" --regex # Find test functions using regex
  /grep "TODO" -i -C 2          # Find TODOs with context, case-insensitive
        """
    
    async def execute(self, args: List[str], context: Dict[str, Any] = None) -> CommandResult:
        try:
            if not args:
                return CommandResult(success=False, error="Search pattern required")
            
            pattern = args[0]
            options = self._parse_grep_options(args[1:])
            
            # Configure search
            search_kwargs = {
                'use_regex': options.get('regex', False),
                'case_sensitive': not options.get('ignore_case', False),
                'whole_words': options.get('word_regexp', False),
                'context_lines': options.get('context', 2),
                'max_matches': options.get('max', 100)
            }
            
            if 'extensions' in options:
                search_kwargs['extensions'] = set(f'.{ext.lstrip(".")}' for ext in options['extensions'])
            
            # Perform search
            console.print(f"[cyan]Grepping for: '{pattern}'[/cyan]")
            
            with console.status("[bold green]Searching..."):
                result = self.search_manager.search(pattern, SearchType.CODE, **search_kwargs)
            
            # Format results
            if not result.code_matches:
                return CommandResult(success=True, output="[yellow]No matches found[/yellow]")
            
            output_parts = [f"[green]Found {len(result.code_matches)} matches:[/green]\n"]
            
            for match in result.code_matches[:50]:  # Limit display
                # File and line
                file_line = f"{match.file_path.name}:{match.line_number}"
                output_parts.append(f"[cyan]{file_line}[/cyan]")
                
                # Context before
                for ctx in match.context_before:
                    output_parts.append(f"[dim]  {ctx}[/dim]")
                
                # Match line (highlighted)
                highlighted = match.line_content.replace(
                    match.match_text, 
                    f"[bold red]{match.match_text}[/bold red]"
                )
                output_parts.append(f"  {highlighted}")
                
                # Context after  
                for ctx in match.context_after:
                    output_parts.append(f"[dim]  {ctx}[/dim]")
                
                output_parts.append("")  # Blank line between matches
            
            return CommandResult(success=True, output="\n".join(output_parts))
        
        except Exception as e:
            return CommandResult(success=False, error=f"Grep failed: {e}")
    
    def _parse_grep_options(self, args: List[str]) -> Dict[str, Any]:
        """Parse grep command options."""
        options = {}
        i = 0
        
        while i < len(args):
            arg = args[i]
            
            if arg == '--regex':
                options['regex'] = True
                i += 1
            elif arg in ['--ignore-case', '-i']:
                options['ignore_case'] = True
                i += 1
            elif arg in ['--word-regexp', '-w']:
                options['word_regexp'] = True
                i += 1
            elif arg in ['--context', '-C'] and i + 1 < len(args):
                options['context'] = int(args[i + 1])
                i += 2
            elif arg in ['--after', '-A'] and i + 1 < len(args):
                options['after'] = int(args[i + 1])
                i += 2
            elif arg in ['--before', '-B'] and i + 1 < len(args):
                options['before'] = int(args[i + 1])
                i += 2
            elif arg == '--ext' and i + 1 < len(args):
                extensions = args[i + 1].split(',')
                options['extensions'] = [ext.strip() for ext in extensions]
                i += 2
            elif arg == '--max' and i + 1 < len(args):
                options['max'] = int(args[i + 1])
                i += 2
            else:
                i += 1
        
        return options

class ProjectOverviewCommand(BaseCommand):
    """Command to show project overview and statistics."""
    
    def __init__(self, search_manager: SearchManager = None):
        super().__init__()
        self.search_manager = search_manager or SearchManager()
    
    def get_name(self) -> str:
        return "overview"
    
    def get_description(self) -> str:
        return "Show comprehensive project overview and statistics"
    
    async def execute(self, args: List[str], context: Dict[str, Any] = None) -> CommandResult:
        try:
            console.print("[cyan]Analyzing project...[/cyan]")
            
            with console.status("[bold green]Gathering statistics..."):
                overview = self.search_manager.get_project_overview()
            
            # Display overview
            output_parts = []
            
            # Basic statistics
            output_parts.append("[bold blue]📊 Project Overview[/bold blue]\n")
            output_parts.append(f"Total files: {overview.get('total_files', 0)}")
            output_parts.append(f"Total size: {self._format_file_size(overview.get('total_size', 0))}")
            output_parts.append(f"Recent files (24h): {overview.get('recent_files', 0)}")
            
            # File type breakdown
            if 'file_types' in overview:
                output_parts.append("\n[bold]File Types:[/bold]")
                for file_type, stats in sorted(overview['file_types'].items()):
                    size_str = self._format_file_size(stats['size'])
                    output_parts.append(f"  {file_type}: {stats['count']} files ({size_str})")
            
            # Code statistics
            if 'code_stats' in overview:
                stats = overview['code_stats']
                output_parts.append("\n[bold]Code Statistics:[/bold]")
                output_parts.append(f"  Functions: {stats.get('functions', 0)}")
                output_parts.append(f"  Classes: {stats.get('classes', 0)}")
                output_parts.append(f"  Import statements: {stats.get('imports', 0)}")
                output_parts.append(f"  TODO comments: {stats.get('todos', 0)}")
            
            return CommandResult(success=True, output="\n".join(output_parts))
        
        except Exception as e:
            return CommandResult(success=False, error=f"Overview failed: {e}")
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"