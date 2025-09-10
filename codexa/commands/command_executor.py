"""
Command executor for Codexa slash commands.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from .command_registry import CommandRegistry, Command, CommandContext
from .command_parser import CommandParser, ParsedCommand, ParseError


class CommandExecutionResult:
    """Result of command execution."""
    
    def __init__(self, success: bool, output: str = "", error: str = "",
                 execution_time: float = 0.0, metadata: Optional[Dict[str, Any]] = None):
        self.success = success
        self.output = output
        self.error = error
        self.execution_time = execution_time
        self.metadata = metadata or {}
        self.timestamp = datetime.now()


class CommandExecutor:
    """Executor for Codexa slash commands."""
    
    def __init__(self, registry: CommandRegistry, console: Optional[Console] = None):
        self.registry = registry
        self.parser = CommandParser()
        self.console = console or Console()
        self.logger = logging.getLogger("codexa.executor")
        
        # Execution state
        self.execution_history: List[CommandExecutionResult] = []
        self.current_context: Optional[Dict[str, Any]] = {}
        self.max_history = 100
    
    async def execute(self, input_text: str, codexa_agent: Any,
                     mcp_service: Optional[Any] = None,
                     config: Optional[Any] = None) -> CommandExecutionResult:
        """Execute a slash command."""
        start_time = time.time()
        
        try:
            # Parse the command
            parsed_command = self.parser.parse(input_text)
            
            # Get command from registry
            command = self.registry.get_command(parsed_command.command)
            if not command:
                suggestions = self.registry.get_suggestions(parsed_command.command)
                error_msg = f"Unknown command: {parsed_command.command}"
                if suggestions:
                    error_msg += f"\nDid you mean: {', '.join(suggestions)}?"
                return CommandExecutionResult(False, error=error_msg)
            
            # Check if command is enabled
            if not command.enabled:
                return CommandExecutionResult(
                    False, error=f"Command '{command.name}' is disabled"
                )
            
            # Map positional arguments to named parameters
            mapped_kwargs = dict(parsed_command.kwargs)
            if parsed_command.args:
                # Get required parameters in order
                required_params = [param for param in command.parameters if param.required]
                
                # Map positional args to required parameters
                for i, arg in enumerate(parsed_command.args):
                    if i < len(required_params):
                        param_name = required_params[i].name
                        if param_name not in mapped_kwargs:  # Don't override explicit kwargs
                            mapped_kwargs[param_name] = arg
            
            # Validate parameters with enhanced error handling
            validation_errors = command.validate_parameters(mapped_kwargs)
            if validation_errors:
                # For natural language requests, try to be more forgiving
                user_input_lower = input_text.lower()
                is_natural_language = (
                    len(user_input_lower.split()) > 3 and
                    not any(user_input_lower.startswith(prefix) for prefix in ['/', '--', '-']) and
                    not any(keyword in user_input_lower for keyword in ['--help', '-h', '/help'])
                )

                if is_natural_language:
                    # For natural language, only fail on truly critical validation errors
                    critical_errors = []
                    for error in validation_errors:
                        if any(critical in error.lower() for critical in [
                            'required parameter', 'missing', 'invalid type'
                        ]):
                            critical_errors.append(error)

                    if not critical_errors:
                        # Non-critical validation errors, proceed anyway
                        self.logger.warning(f"Non-critical validation errors for natural language request: {validation_errors}")
                    elif len(critical_errors) > 0:
                        return CommandExecutionResult(
                            False, error="Parameter validation failed:\n" + "\n".join(critical_errors)
                        )
                else:
                    # For structured commands, be strict about validation
                    return CommandExecutionResult(
                        False, error="Parameter validation failed:\n" + "\n".join(validation_errors)
                    )
            
            # Create execution context
            context = CommandContext(
                user_input=input_text,
                parsed_args={**mapped_kwargs, 'args': parsed_command.args, 'flags': parsed_command.flags},
                codexa_agent=codexa_agent,
                mcp_service=mcp_service,
                config=config,
                session_data=self.current_context.copy()
            )
            
            # Execute the command
            self.logger.info(f"Executing command: {command.name}")
            
            with self._create_execution_progress(command.name):
                output = await command.execute(context)
            
            execution_time = time.time() - start_time
            result = CommandExecutionResult(
                True, output=output, execution_time=execution_time,
                metadata={'command': command.name, 'category': command.category.value}
            )
            
            # Update execution history
            self._add_to_history(result)
            
            self.logger.info(f"Command '{command.name}' executed successfully in {execution_time:.2f}s")
            return result
            
        except ParseError as e:
            execution_time = time.time() - start_time
            result = CommandExecutionResult(
                False, error=f"Parse error: {str(e)}", execution_time=execution_time
            )
            self._add_to_history(result)
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Command execution failed: {e}")
            result = CommandExecutionResult(
                False, error=f"Execution error: {str(e)}", execution_time=execution_time
            )
            self._add_to_history(result)
            return result
    
    def _create_execution_progress(self, command_name: str):
        """Create progress indicator for command execution."""
        return Progress(
            SpinnerColumn(),
            TextColumn(f"[progress.description]Executing /{command_name}..."),
            console=self.console,
            transient=True
        )
    
    def _add_to_history(self, result: CommandExecutionResult):
        """Add execution result to history."""
        self.execution_history.append(result)
        
        # Maintain history size limit
        if len(self.execution_history) > self.max_history:
            self.execution_history = self.execution_history[-self.max_history:]
    
    def get_command_suggestions(self, partial_input: str) -> List[str]:
        """Get command suggestions for partial input."""
        available_commands = self.registry.list_commands()
        return self.parser.suggest_completion(partial_input, available_commands)
    
    def validate_command_syntax(self, input_text: str) -> List[str]:
        """Validate command syntax."""
        return self.parser.validate_syntax(input_text)
    
    def get_command_help(self, command_name: Optional[str] = None) -> str:
        """Get help text for command(s)."""
        if command_name:
            help_text = self.registry.get_command_help(command_name)
            return help_text or f"Command '{command_name}' not found"
        else:
            return self.registry.get_all_help()
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        if not self.execution_history:
            return {"total_executions": 0}
        
        total = len(self.execution_history)
        successful = sum(1 for r in self.execution_history if r.success)
        failed = total - successful
        
        avg_time = sum(r.execution_time for r in self.execution_history) / total
        
        # Command usage stats
        command_usage = {}
        for result in self.execution_history:
            cmd_name = result.metadata.get('command', 'unknown')
            command_usage[cmd_name] = command_usage.get(cmd_name, 0) + 1
        
        return {
            "total_executions": total,
            "successful_executions": successful,
            "failed_executions": failed,
            "success_rate": successful / total,
            "average_execution_time": avg_time,
            "most_used_commands": sorted(command_usage.items(), 
                                       key=lambda x: x[1], reverse=True)[:5]
        }
    
    def clear_history(self):
        """Clear execution history."""
        self.execution_history.clear()
        self.logger.info("Execution history cleared")
    
    def display_help_table(self, category: Optional[str] = None):
        """Display commands in a formatted table."""
        from .command_registry import CommandCategory
        
        # Convert string category to enum if provided
        cat_filter = None
        if category:
            try:
                cat_filter = CommandCategory(category.lower())
            except ValueError:
                self.console.print(f"[red]Unknown category: {category}[/red]")
                return
        
        commands = self.registry.list_commands(cat_filter)
        
        if not commands:
            self.console.print("[yellow]No commands found[/yellow]")
            return
        
        table = Table(title=f"Available Commands{f' ({category})' if category else ''}")
        table.add_column("Command", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Category", style="dim")
        
        for cmd_name in commands:
            command = self.registry.commands[cmd_name]
            table.add_row(
                f"/{cmd_name}",
                command.description or "No description",
                command.category.value
            )
        
        self.console.print(table)
    
    def display_execution_history(self, limit: int = 10):
        """Display recent execution history."""
        recent_history = self.execution_history[-limit:] if self.execution_history else []
        
        if not recent_history:
            self.console.print("[yellow]No execution history[/yellow]")
            return
        
        table = Table(title="Recent Command Executions")
        table.add_column("Time", style="dim")
        table.add_column("Command", style="cyan")
        table.add_column("Status", style="white")
        table.add_column("Duration", style="yellow")
        
        for result in recent_history:
            status = "[green]✓[/green]" if result.success else "[red]✗[/red]"
            duration = f"{result.execution_time:.2f}s"
            time_str = result.timestamp.strftime("%H:%M:%S")
            cmd_name = result.metadata.get('command', 'unknown')
            
            table.add_row(time_str, f"/{cmd_name}", status, duration)
        
        self.console.print(table)
    
    async def execute_batch(self, commands: List[str], codexa_agent: Any,
                           stop_on_error: bool = False) -> List[CommandExecutionResult]:
        """Execute multiple commands in batch."""
        results = []
        
        for i, cmd in enumerate(commands):
            self.console.print(f"[dim]Executing command {i+1}/{len(commands)}: {cmd}[/dim]")
            
            result = await self.execute(cmd, codexa_agent)
            results.append(result)
            
            if not result.success and stop_on_error:
                self.console.print(f"[red]Stopping batch execution due to error: {result.error}[/red]")
                break
        
        return results
    
    def export_history(self, format: str = "json") -> str:
        """Export execution history in specified format."""
        if format.lower() == "json":
            import json
            data = []
            for result in self.execution_history:
                data.append({
                    "timestamp": result.timestamp.isoformat(),
                    "success": result.success,
                    "output": result.output,
                    "error": result.error,
                    "execution_time": result.execution_time,
                    "metadata": result.metadata
                })
            return json.dumps(data, indent=2)
        
        elif format.lower() == "csv":
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["timestamp", "command", "success", "execution_time", "error"])
            
            for result in self.execution_history:
                writer.writerow([
                    result.timestamp.isoformat(),
                    result.metadata.get('command', 'unknown'),
                    result.success,
                    result.execution_time,
                    result.error
                ])
            
            return output.getvalue()
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def set_context(self, key: str, value: Any):
        """Set context value for command execution."""
        self.current_context[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context value."""
        return self.current_context.get(key, default)
    
    def clear_context(self):
        """Clear execution context."""
        self.current_context.clear()