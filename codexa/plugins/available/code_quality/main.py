"""
Code Quality Plugin for Codexa - provides linting, formatting, and quality analysis.
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from codexa.plugins.plugin_manager import Plugin, PluginInfo
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax


@dataclass
class QualityIssue:
    """Represents a code quality issue."""
    file_path: str
    line_number: int
    column: int
    severity: str
    message: str
    rule_id: str
    tool: str


@dataclass
class QualityReport:
    """Code quality analysis report."""
    total_files: int
    total_issues: int
    issues_by_severity: Dict[str, int]
    issues_by_tool: Dict[str, int]
    issues: List[QualityIssue]
    execution_time: float


class CodeQualityPlugin(Plugin):
    """Main code quality plugin class."""
    
    def __init__(self, info: PluginInfo):
        super().__init__(info)
        self.console = Console()
        self.supported_tools = {
            'black': self._run_black,
            'isort': self._run_isort,
            'pylint': self._run_pylint,
            'mypy': self._run_mypy,
            'flake8': self._run_flake8
        }
        self.settings = {}
    
    async def initialize(self, context: Dict[str, Any]) -> bool:
        """Initialize the plugin."""
        try:
            self.logger.info("Initializing Code Quality Plugin...")
            
            # Load settings from plugin.json
            self.settings = self.info.to_dict().get('settings', {})
            
            # Check for required tools
            missing_tools = []
            for tool in ['black', 'isort', 'pylint', 'mypy']:
                if not await self._check_tool_available(tool):
                    missing_tools.append(tool)
            
            if missing_tools:
                self.logger.warning(f"Missing code quality tools: {missing_tools}")
                self.logger.info("Install with: pip install " + " ".join(missing_tools))
                # Don't fail initialization, just warn
            
            self.logger.info("Code Quality Plugin initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Code Quality Plugin: {e}")
            return False
    
    async def shutdown(self) -> bool:
        """Shutdown the plugin."""
        self.logger.info("Code Quality Plugin shutdown")
        return True
    
    async def on_command(self, command: str, args: Dict[str, Any]) -> Optional[str]:
        """Handle plugin commands."""
        try:
            if command == "lint":
                return await self._handle_lint(args)
            elif command == "format":
                return await self._handle_format(args)
            elif command == "complexity":
                return await self._handle_complexity(args)
            elif command == "quality-check":
                return await self._handle_quality_check(args)
            elif command == "fix-quality":
                return await self._handle_fix_quality(args)
            else:
                return f"Unknown command: {command}"
                
        except Exception as e:
            self.logger.error(f"Command {command} failed: {e}")
            return f"Command failed: {e}"
    
    async def _handle_lint(self, args: Dict[str, Any]) -> str:
        """Handle lint command."""
        target = args.get('target', '.')
        tools = args.get('tools', self.settings.get('default_linters', ['pylint']))
        
        self.console.print(f"[bold cyan]🔍 Running linting analysis on: {target}[/bold cyan]")
        
        issues = []
        for tool in tools:
            if tool in self.supported_tools and await self._check_tool_available(tool):
                tool_issues = await self.supported_tools[tool](target, action='check')
                issues.extend(tool_issues)
        
        if not issues:
            return "[green]✅ No linting issues found![/green]"
        
        # Display issues in a formatted table
        table = Table(title="Linting Issues")
        table.add_column("File", style="cyan")
        table.add_column("Line", style="yellow")
        table.add_column("Severity", style="red")
        table.add_column("Message", style="white")
        table.add_column("Tool", style="dim")
        
        for issue in issues[:20]:  # Limit to first 20 issues
            table.add_row(
                issue.file_path,
                str(issue.line_number),
                issue.severity,
                issue.message[:80] + "..." if len(issue.message) > 80 else issue.message,
                issue.tool
            )
        
        if len(issues) > 20:
            table.add_row("...", "...", "...", f"({len(issues) - 20} more issues)", "...")
        
        with self.console.capture() as capture:
            self.console.print(table)
        
        return capture.get()
    
    async def _handle_format(self, args: Dict[str, Any]) -> str:
        """Handle format command."""
        target = args.get('target', '.')
        tools = args.get('tools', self.settings.get('default_formatters', ['black', 'isort']))
        dry_run = args.get('dry_run', False)
        
        action = 'check' if dry_run else 'format'
        self.console.print(f"[bold cyan]🎨 {'Checking format' if dry_run else 'Formatting code'}: {target}[/bold cyan]")
        
        results = []
        for tool in tools:
            if tool in self.supported_tools and await self._check_tool_available(tool):
                result = await self.supported_tools[tool](target, action=action)
                if result:
                    results.append(f"{tool}: {len(result)} issues")
        
        if not results:
            return "[green]✅ Code is properly formatted![/green]"
        
        return f"[yellow]Formatting {'would change' if dry_run else 'updated'}: {', '.join(results)}[/yellow]"
    
    async def _handle_complexity(self, args: Dict[str, Any]) -> str:
        """Handle complexity analysis."""
        target = args.get('target', '.')
        threshold = args.get('threshold', self.settings.get('complexity_threshold', 10))
        
        self.console.print(f"[bold cyan]📊 Analyzing code complexity: {target}[/bold cyan]")
        
        try:
            # Use radon for complexity analysis
            cmd = ['radon', 'cc', '-s', target, '--json']
            result = await self._run_command(cmd)
            
            if result.returncode == 0:
                complexity_data = json.loads(result.stdout)
                
                # Parse and display results
                high_complexity = []
                for file_path, functions in complexity_data.items():
                    for func in functions:
                        if func['complexity'] > threshold:
                            high_complexity.append({
                                'file': file_path,
                                'function': func['name'],
                                'complexity': func['complexity'],
                                'line': func['lineno']
                            })
                
                if not high_complexity:
                    return f"[green]✅ No functions exceed complexity threshold ({threshold})[/green]"
                
                table = Table(title=f"High Complexity Functions (>{threshold})")
                table.add_column("File", style="cyan")
                table.add_column("Function", style="yellow")
                table.add_column("Complexity", style="red")
                table.add_column("Line", style="dim")
                
                for item in high_complexity[:10]:
                    table.add_row(
                        item['file'],
                        item['function'],
                        str(item['complexity']),
                        str(item['line'])
                    )
                
                with self.console.capture() as capture:
                    self.console.print(table)
                
                return capture.get()
            else:
                return f"[red]Complexity analysis failed: {result.stderr}[/red]"
                
        except Exception as e:
            return f"[red]Complexity analysis error: {e}[/red]"
    
    async def _handle_quality_check(self, args: Dict[str, Any]) -> str:
        """Handle comprehensive quality check."""
        target = args.get('target', '.')
        
        self.console.print(f"[bold cyan]🏆 Running comprehensive quality check: {target}[/bold cyan]")
        
        # Run multiple checks
        results = {}
        
        # Linting
        lint_result = await self._handle_lint({'target': target})
        results['linting'] = "✅ Pass" if "No linting issues" in lint_result else "❌ Issues found"
        
        # Formatting
        format_result = await self._handle_format({'target': target, 'dry_run': True})
        results['formatting'] = "✅ Pass" if "properly formatted" in format_result else "❌ Needs formatting"
        
        # Complexity
        complexity_result = await self._handle_complexity({'target': target})
        results['complexity'] = "✅ Pass" if "No functions exceed" in complexity_result else "❌ High complexity"
        
        # Create summary
        table = Table(title="Quality Check Summary")
        table.add_column("Check", style="cyan")
        table.add_column("Status", style="white")
        
        for check, status in results.items():
            table.add_row(check.capitalize(), status)
        
        with self.console.capture() as capture:
            self.console.print(table)
        
        return capture.get()
    
    async def _handle_fix_quality(self, args: Dict[str, Any]) -> str:
        """Handle automatic quality fixes."""
        target = args.get('target', '.')
        
        self.console.print(f"[bold cyan]🔧 Automatically fixing quality issues: {target}[/bold cyan]")
        
        fixes_applied = []
        
        # Auto-format code
        format_result = await self._handle_format({'target': target, 'dry_run': False})
        if "updated" in format_result:
            fixes_applied.append("Code formatting")
        
        # Try to fix some linting issues automatically
        if await self._check_tool_available('autopep8'):
            try:
                cmd = ['autopep8', '--in-place', '--recursive', target]
                result = await self._run_command(cmd)
                if result.returncode == 0:
                    fixes_applied.append("PEP8 violations")
            except Exception:
                pass
        
        if fixes_applied:
            return f"[green]✅ Applied fixes: {', '.join(fixes_applied)}[/green]"
        else:
            return "[yellow]No automatic fixes available[/yellow]"
    
    # Tool-specific implementations
    async def _run_black(self, target: str, action: str = 'check') -> List[QualityIssue]:
        """Run black formatter."""
        issues = []
        try:
            cmd = ['black']
            if action == 'check':
                cmd.extend(['--check', '--diff'])
            cmd.append(target)
            
            result = await self._run_command(cmd)
            
            if action == 'check' and result.returncode != 0:
                # Parse black output for formatting issues
                for line in result.stdout.split('\n'):
                    if line.startswith('---') or line.startswith('+++'):
                        continue
                    if line.strip():
                        issues.append(QualityIssue(
                            file_path=target,
                            line_number=0,
                            column=0,
                            severity='style',
                            message='Formatting issue',
                            rule_id='black',
                            tool='black'
                        ))
            
        except Exception as e:
            self.logger.error(f"Black execution failed: {e}")
        
        return issues
    
    async def _run_isort(self, target: str, action: str = 'check') -> List[QualityIssue]:
        """Run isort import sorter."""
        issues = []
        try:
            cmd = ['isort']
            if action == 'check':
                cmd.extend(['--check-only', '--diff'])
            cmd.append(target)
            
            result = await self._run_command(cmd)
            
            if action == 'check' and result.returncode != 0:
                issues.append(QualityIssue(
                    file_path=target,
                    line_number=0,
                    column=0,
                    severity='style',
                    message='Import sorting issue',
                    rule_id='isort',
                    tool='isort'
                ))
            
        except Exception as e:
            self.logger.error(f"Isort execution failed: {e}")
        
        return issues
    
    async def _run_pylint(self, target: str, action: str = 'check') -> List[QualityIssue]:
        """Run pylint linter."""
        issues = []
        try:
            cmd = ['pylint', '--output-format=json', target]
            result = await self._run_command(cmd)
            
            if result.stdout:
                try:
                    pylint_output = json.loads(result.stdout)
                    for issue in pylint_output:
                        issues.append(QualityIssue(
                            file_path=issue.get('path', ''),
                            line_number=issue.get('line', 0),
                            column=issue.get('column', 0),
                            severity=issue.get('type', 'info'),
                            message=issue.get('message', ''),
                            rule_id=issue.get('message-id', ''),
                            tool='pylint'
                        ))
                except json.JSONDecodeError:
                    pass  # Ignore JSON parse errors
            
        except Exception as e:
            self.logger.error(f"Pylint execution failed: {e}")
        
        return issues
    
    async def _run_mypy(self, target: str, action: str = 'check') -> List[QualityIssue]:
        """Run mypy type checker."""
        issues = []
        try:
            cmd = ['mypy', '--no-error-summary', target]
            result = await self._run_command(cmd)
            
            for line in result.stdout.split('\n'):
                if ':' in line and ('error:' in line or 'warning:' in line):
                    parts = line.split(':', 3)
                    if len(parts) >= 4:
                        issues.append(QualityIssue(
                            file_path=parts[0],
                            line_number=int(parts[1]) if parts[1].isdigit() else 0,
                            column=int(parts[2]) if parts[2].isdigit() else 0,
                            severity='error' if 'error:' in line else 'warning',
                            message=parts[3].strip(),
                            rule_id='type-check',
                            tool='mypy'
                        ))
            
        except Exception as e:
            self.logger.error(f"Mypy execution failed: {e}")
        
        return issues
    
    async def _run_flake8(self, target: str, action: str = 'check') -> List[QualityIssue]:
        """Run flake8 linter."""
        issues = []
        try:
            cmd = ['flake8', '--format=json', target]
            result = await self._run_command(cmd)
            
            if result.stdout:
                try:
                    flake8_output = json.loads(result.stdout)
                    for file_path, file_issues in flake8_output.items():
                        for issue in file_issues:
                            issues.append(QualityIssue(
                                file_path=file_path,
                                line_number=issue.get('line_number', 0),
                                column=issue.get('column_number', 0),
                                severity='warning',
                                message=issue.get('text', ''),
                                rule_id=issue.get('code', ''),
                                tool='flake8'
                            ))
                except json.JSONDecodeError:
                    pass
            
        except Exception as e:
            self.logger.error(f"Flake8 execution failed: {e}")
        
        return issues
    
    async def _check_tool_available(self, tool: str) -> bool:
        """Check if a tool is available in the system."""
        try:
            result = await self._run_command(['which', tool])
            return result.returncode == 0
        except Exception:
            return False
    
    async def _run_command(self, cmd: List[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
        """Run a system command asynchronously."""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            stdout, stderr = await process.communicate()
            
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=process.returncode,
                stdout=stdout.decode('utf-8'),
                stderr=stderr.decode('utf-8')
            )
        except Exception as e:
            self.logger.error(f"Command execution failed: {e}")
            raise