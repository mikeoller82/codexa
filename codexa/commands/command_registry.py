"""
Command registry system for Codexa slash commands.
"""

import inspect
import logging
from typing import Dict, List, Optional, Callable, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod


class CommandCategory(Enum):
    """Command categories for organization."""
    CORE = "core"
    MCP = "mcp"
    PROJECT = "project"
    PROVIDER = "provider"
    DEVELOPMENT = "development"
    HELP = "help"
    CUSTOM = "custom"


@dataclass
class CommandParameter:
    """Command parameter definition."""
    name: str
    type: type = str
    required: bool = False
    default: Any = None
    description: str = ""
    choices: Optional[List[str]] = None
    
    def validate(self, value: Any) -> bool:
        """Validate parameter value."""
        if self.required and value is None:
            return False
        
        if value is not None:
            # Type validation
            try:
                if self.type == bool and isinstance(value, str):
                    value = value.lower() in ('true', '1', 'yes', 'on')
                else:
                    self.type(value)
            except (ValueError, TypeError):
                return False
            
            # Choice validation
            if self.choices and value not in self.choices:
                return False
        
        return True


@dataclass
class CommandContext:
    """Context passed to command execution."""
    user_input: str
    parsed_args: Dict[str, Any]
    codexa_agent: Any  # Reference to main agent
    mcp_service: Optional[Any] = None
    config: Optional[Any] = None
    session_data: Dict[str, Any] = field(default_factory=dict)


class Command(ABC):
    """Abstract base class for Codexa commands."""
    
    def __init__(self):
        self.name: str = ""
        self.description: str = ""
        self.category: CommandCategory = CommandCategory.CUSTOM
        self.parameters: List[CommandParameter] = []
        self.aliases: List[str] = []
        self.enabled: bool = True
        self.admin_only: bool = False
    
    @abstractmethod
    async def execute(self, context: CommandContext) -> str:
        """Execute the command."""
        pass
    
    def validate_parameters(self, args: Dict[str, Any]) -> List[str]:
        """Validate command parameters."""
        errors = []
        
        for param in self.parameters:
            value = args.get(param.name)
            
            if not param.validate(value):
                if param.required and value is None:
                    errors.append(f"Required parameter '{param.name}' is missing")
                elif value is not None:
                    if param.choices:
                        errors.append(f"Parameter '{param.name}' must be one of: {', '.join(param.choices)}")
                    else:
                        errors.append(f"Parameter '{param.name}' has invalid value")
        
        return errors
    
    def get_help_text(self) -> str:
        """Get help text for the command."""
        help_lines = [f"/{self.name} - {self.description}"]
        
        if self.aliases:
            help_lines.append(f"Aliases: {', '.join('/' + alias for alias in self.aliases)}")
        
        if self.parameters:
            help_lines.append("\nParameters:")
            for param in self.parameters:
                param_line = f"  {param.name}"
                if not param.required:
                    param_line += " (optional)"
                if param.default is not None:
                    param_line += f" [default: {param.default}]"
                if param.choices:
                    param_line += f" [choices: {', '.join(param.choices)}]"
                param_line += f" - {param.description}"
                help_lines.append(param_line)
        
        return "\n".join(help_lines)


class FunctionCommand(Command):
    """Command that wraps a function."""
    
    def __init__(self, func: Callable, name: str = "", description: str = "",
                 category: CommandCategory = CommandCategory.CUSTOM):
        super().__init__()
        self.func = func
        self.name = name or func.__name__
        self.description = description or (func.__doc__ or "").strip().split('\n')[0]
        self.category = category
        
        # Extract parameters from function signature
        self._extract_parameters()
    
    def _extract_parameters(self):
        """Extract parameters from function signature."""
        sig = inspect.signature(self.func)
        
        for param_name, param in sig.parameters.items():
            if param_name == 'context':
                continue  # Skip context parameter
            
            param_def = CommandParameter(
                name=param_name,
                type=param.annotation if param.annotation != inspect.Parameter.empty else str,
                required=param.default == inspect.Parameter.empty,
                default=param.default if param.default != inspect.Parameter.empty else None
            )
            
            self.parameters.append(param_def)
    
    async def execute(self, context: CommandContext) -> str:
        """Execute the wrapped function."""
        # Prepare arguments for function call
        sig = inspect.signature(self.func)
        kwargs = {}
        
        for param_name in sig.parameters.keys():
            if param_name == 'context':
                kwargs['context'] = context
            elif param_name in context.parsed_args:
                kwargs[param_name] = context.parsed_args[param_name]
        
        # Call function
        if inspect.iscoroutinefunction(self.func):
            result = await self.func(**kwargs)
        else:
            result = self.func(**kwargs)
        
        return str(result) if result is not None else "Command executed successfully"


class CommandRegistry:
    """Registry for managing Codexa commands."""
    
    def __init__(self):
        self.commands: Dict[str, Command] = {}
        self.aliases: Dict[str, str] = {}  # alias -> command_name
        self.categories: Dict[CommandCategory, List[str]] = {}
        self.logger = logging.getLogger("codexa.commands")
    
    def register(self, command: Command):
        """Register a command."""
        if not command.name:
            raise ValueError("Command must have a name")
        
        if command.name in self.commands:
            self.logger.warning(f"Command '{command.name}' already registered, overwriting")
        
        self.commands[command.name] = command
        
        # Register aliases
        for alias in command.aliases:
            if alias in self.aliases:
                self.logger.warning(f"Alias '{alias}' already exists, overwriting")
            self.aliases[alias] = command.name
        
        # Update category index
        if command.category not in self.categories:
            self.categories[command.category] = []
        if command.name not in self.categories[command.category]:
            self.categories[command.category].append(command.name)
        
        self.logger.info(f"Registered command: {command.name}")
    
    def register_function(self, func: Callable, name: str = "", description: str = "",
                         category: CommandCategory = CommandCategory.CUSTOM,
                         aliases: Optional[List[str]] = None):
        """Register a function as a command."""
        command = FunctionCommand(func, name, description, category)
        if aliases:
            command.aliases = aliases
        self.register(command)
        return command
    
    def unregister(self, name: str):
        """Unregister a command."""
        if name not in self.commands:
            return False
        
        command = self.commands[name]
        
        # Remove aliases
        for alias in command.aliases:
            self.aliases.pop(alias, None)
        
        # Remove from category
        if command.category in self.categories:
            self.categories[command.category].remove(name)
            if not self.categories[command.category]:
                del self.categories[command.category]
        
        # Remove command
        del self.commands[name]
        
        self.logger.info(f"Unregistered command: {name}")
        return True
    
    def get_command(self, name: str) -> Optional[Command]:
        """Get a command by name or alias."""
        # Check direct name
        if name in self.commands:
            return self.commands[name]
        
        # Check aliases
        if name in self.aliases:
            return self.commands[self.aliases[name]]
        
        return None
    
    def list_commands(self, category: Optional[CommandCategory] = None,
                     enabled_only: bool = True) -> List[str]:
        """List available commands."""
        if category:
            command_names = self.categories.get(category, [])
        else:
            command_names = list(self.commands.keys())
        
        if enabled_only:
            command_names = [name for name in command_names 
                           if self.commands[name].enabled]
        
        return sorted(command_names)
    
    def get_command_names(self) -> List[str]:
        """Get list of all registered command names."""
        return list(self.commands.keys())
    
    def get_command_help(self, name: str) -> Optional[str]:
        """Get help text for a command."""
        command = self.get_command(name)
        return command.get_help_text() if command else None
    
    def get_all_help(self, category: Optional[CommandCategory] = None) -> str:
        """Get help text for all commands in a category."""
        commands = self.list_commands(category)
        
        help_sections = []
        current_category = None
        
        for cmd_name in commands:
            command = self.commands[cmd_name]
            
            # Add category header if changed
            if command.category != current_category:
                current_category = command.category
                help_sections.append(f"\n== {current_category.value.upper()} COMMANDS ==")
            
            help_sections.append(command.get_help_text())
        
        return "\n\n".join(help_sections)
    
    def enable_command(self, name: str) -> bool:
        """Enable a command."""
        command = self.get_command(name)
        if command:
            command.enabled = True
            return True
        return False
    
    def disable_command(self, name: str) -> bool:
        """Disable a command."""
        command = self.get_command(name)
        if command:
            command.enabled = False
            return True
        return False
    
    def get_suggestions(self, partial_name: str, limit: int = 5) -> List[str]:
        """Get command name suggestions for partial input."""
        suggestions = []
        
        # Exact matches first
        for name in self.commands.keys():
            if name.startswith(partial_name):
                suggestions.append(name)
        
        # Alias matches
        for alias in self.aliases.keys():
            if alias.startswith(partial_name):
                suggestions.append(alias)
        
        # Fuzzy matches (contains)
        if len(suggestions) < limit:
            for name in self.commands.keys():
                if partial_name in name and name not in suggestions:
                    suggestions.append(name)
        
        return suggestions[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_commands": len(self.commands),
            "enabled_commands": len([c for c in self.commands.values() if c.enabled]),
            "categories": {cat.value: len(commands) for cat, commands in self.categories.items()},
            "total_aliases": len(self.aliases)
        }