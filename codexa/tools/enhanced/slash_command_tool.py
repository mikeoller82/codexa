"""
Slash Command Tool - Handles slash command registration and execution for Codexa
"""

import re
import inspect
from typing import Dict, Any, Optional, List, Callable, Tuple
from dataclasses import dataclass

from ..base.tool_interface import Tool, ToolResult, ToolContext, ToolStatus


@dataclass
class SlashCommand:
    """Represents a slash command"""
    name: str
    description: str
    handler: Callable
    aliases: List[str] = None
    category: str = "general"
    requires_args: bool = False
    hidden: bool = False
    
    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []


class SlashCommandTool(Tool):
    """Tool for managing and executing slash commands"""
    
    def __init__(self):
        super().__init__()
        self.commands: Dict[str, SlashCommand] = {}
        self._register_built_in_commands()
    
    @property
    def name(self) -> str:
        return "slash_command"
    
    @property
    def description(self) -> str:
        return "Handles slash command registration and execution for enhanced user interaction"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def capabilities(self) -> List[str]:
        return [
            "register_command",
            "execute_command",
            "list_commands",
            "get_command_help",
            "unregister_command",
            "command_aliases",
            "command_categories",
            "command_validation",
            "autocomplete_support",
            "command_history"
        ]
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the slash command request"""
        request_stripped = request.strip()
        
        # High confidence for slash commands
        if request_stripped.startswith('/'):
            return 0.95
            
        # Medium confidence for command-related requests
        request_lower = request.lower()
        if any(word in request_lower for word in [
            'slash command', 'command', '/help', 'list commands',
            'register command', 'execute command'
        ]):
            return 0.7
            
        return 0.0
    
    def execute(self, request: str, context: ToolContext) -> ToolResult:
        """Execute slash command or handle command management"""
        try:
            request = request.strip()
            
            if request.startswith('/'):
                # Execute slash command
                return self._execute_slash_command(request, context)
            else:
                # Handle command management
                return self._handle_command_management(request, context)
                
        except Exception as e:
            return ToolResult(
                success=False,
                data={'error': str(e)},
                message=f"Slash command execution failed: {str(e)}",
                status=ToolStatus.ERROR
            )
    
    def _execute_slash_command(self, command_line: str, context: ToolContext) -> ToolResult:
        """Execute a slash command"""
        # Parse command and arguments
        parts = command_line[1:].split(' ', 1)  # Remove leading /
        command_name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        # Find command (check aliases too)
        command = self._find_command(command_name)
        if not command:
            return ToolResult(
                success=False,
                data={'error': f'Unknown command: /{command_name}'},
                message=f"Command '/{command_name}' not found. Use /help to see available commands.",
                status=ToolStatus.ERROR
            )
        
        # Validate arguments
        if command.requires_args and not args.strip():
            return ToolResult(
                success=False,
                data={'error': f'Command /{command_name} requires arguments'},
                message=f"Command '/{command_name}' requires arguments. Use /help {command_name} for usage.",
                status=ToolStatus.ERROR
            )
        
        # Execute command
        try:
            result = command.handler(args, context)
            
            return ToolResult(
                success=True,
                data=result,
                message=f"Command /{command_name} executed successfully",
                status=ToolStatus.SUCCESS
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                data={'error': str(e)},
                message=f"Command /{command_name} execution failed: {str(e)}",
                status=ToolStatus.ERROR
            )
    
    def _handle_command_management(self, request: str, context: ToolContext) -> ToolResult:
        """Handle command management requests"""
        request_lower = request.lower()
        
        if 'list commands' in request_lower or 'available commands' in request_lower:
            result = self._list_commands()
        elif 'register command' in request_lower:
            result = {'message': 'Command registration requires code-level integration'}
        elif 'help' in request_lower:
            result = self._get_help()
        else:
            result = {'message': 'Unknown command management request'}
        
        return ToolResult(
            success=True,
            data=result,
            message="Command management operation completed",
            status=ToolStatus.SUCCESS
        )
    
    def _find_command(self, command_name: str) -> Optional[SlashCommand]:
        """Find command by name or alias"""
        # Direct match
        if command_name in self.commands:
            return self.commands[command_name]
        
        # Check aliases
        for cmd in self.commands.values():
            if command_name in cmd.aliases:
                return cmd
        
        return None
    
    def register_command(self, name: str, handler: Callable, description: str = "",
                        aliases: List[str] = None, category: str = "custom",
                        requires_args: bool = False, hidden: bool = False) -> bool:
        """Register a new slash command"""
        try:
            if name in self.commands:
                return False  # Command already exists
            
            command = SlashCommand(
                name=name,
                description=description,
                handler=handler,
                aliases=aliases or [],
                category=category,
                requires_args=requires_args,
                hidden=hidden
            )
            
            self.commands[name] = command
            return True
            
        except Exception:
            return False
    
    def unregister_command(self, name: str) -> bool:
        """Unregister a slash command"""
        if name in self.commands:
            del self.commands[name]
            return True
        return False
    
    def _register_built_in_commands(self):
        """Register built-in slash commands"""
        
        def help_command(args: str, context: ToolContext) -> Dict[str, Any]:
            """Show help for commands"""
            if args.strip():
                # Help for specific command
                command_name = args.strip().lower()
                command = self._find_command(command_name)
                if command:
                    return {
                        'command': command.name,
                        'description': command.description,
                        'aliases': command.aliases,
                        'category': command.category,
                        'requires_args': command.requires_args
                    }
                else:
                    return {'error': f'Command not found: {command_name}'}
            else:
                # General help
                return self._list_commands()
        
        def version_command(args: str, context: ToolContext) -> Dict[str, Any]:
            """Show Codexa version"""
            return {
                'codexa_version': '1.0.0',
                'tool_version': self.version,
                'enhanced_features': True
            }
        
        def status_command(args: str, context: ToolContext) -> Dict[str, Any]:
            """Show system status"""
            return {
                'tool_manager': 'active' if context.tool_manager else 'inactive',
                'mcp_service': 'active' if context.mcp_service else 'inactive',
                'commands_registered': len(self.commands),
                'context_available': bool(context)
            }
        
        def clear_command(args: str, context: ToolContext) -> Dict[str, Any]:
            """Clear terminal/output"""
            import os
            os.system('cls' if os.name == 'nt' else 'clear')
            return {'message': 'Screen cleared'}
        
        def tools_command(args: str, context: ToolContext) -> Dict[str, Any]:
            """List available tools"""
            if context.tool_manager:
                tools = context.tool_manager.get_available_tools()
                return {
                    'available_tools': list(tools.keys()),
                    'tool_count': len(tools)
                }
            else:
                return {'error': 'Tool manager not available'}
        
        def config_command(args: str, context: ToolContext) -> Dict[str, Any]:
            """Show configuration"""
            return {
                'tool_name': self.name,
                'capabilities': self.capabilities,
                'commands_count': len(self.commands)
            }
        
        def history_command(args: str, context: ToolContext) -> Dict[str, Any]:
            """Show command history"""
            # This would integrate with session management
            return {
                'message': 'Command history not implemented yet',
                'suggestion': 'Use shell history or implement session management'
            }
        
        def search_command(args: str, context: ToolContext) -> Dict[str, Any]:
            """Search through available commands"""
            if not args.strip():
                return {'error': 'Search term required'}
            
            search_term = args.strip().lower()
            matches = []
            
            for name, command in self.commands.items():
                if (search_term in name.lower() or 
                    search_term in command.description.lower() or
                    any(search_term in alias.lower() for alias in command.aliases)):
                    matches.append({
                        'name': name,
                        'description': command.description,
                        'category': command.category
                    })
            
            return {
                'search_term': search_term,
                'matches': matches,
                'match_count': len(matches)
            }
        
        def alias_command(args: str, context: ToolContext) -> Dict[str, Any]:
            """Show command aliases"""
            aliases = {}
            for name, command in self.commands.items():
                if command.aliases:
                    aliases[name] = command.aliases
            
            return {
                'command_aliases': aliases,
                'total_aliases': sum(len(aliases) for aliases in aliases.values())
            }
        
        # Register built-in commands
        commands_to_register = [
            ('help', help_command, 'Show help for commands', ['h', '?'], 'core'),
            ('version', version_command, 'Show Codexa version', ['v', 'ver'], 'core'),
            ('status', status_command, 'Show system status', ['stat'], 'core'),
            ('clear', clear_command, 'Clear terminal screen', ['cls'], 'utility'),
            ('tools', tools_command, 'List available tools', ['t'], 'core'),
            ('config', config_command, 'Show configuration', ['cfg'], 'core'),
            ('history', history_command, 'Show command history', ['hist'], 'utility'),
            ('search', search_command, 'Search commands', ['find'], 'utility', True),
            ('aliases', alias_command, 'Show command aliases', ['alias'], 'utility')
        ]
        
        for cmd_data in commands_to_register:
            name, handler, desc = cmd_data[:3]
            aliases = cmd_data[3] if len(cmd_data) > 3 else []
            category = cmd_data[4] if len(cmd_data) > 4 else 'general'
            requires_args = cmd_data[5] if len(cmd_data) > 5 else False
            
            self.register_command(name, handler, desc, aliases, category, requires_args)
    
    def _list_commands(self) -> Dict[str, Any]:
        """List all available commands"""
        categories = {}
        
        for name, command in self.commands.items():
            if command.hidden:
                continue
                
            if command.category not in categories:
                categories[command.category] = []
            
            categories[command.category].append({
                'name': name,
                'description': command.description,
                'aliases': command.aliases,
                'requires_args': command.requires_args
            })
        
        return {
            'commands_by_category': categories,
            'total_commands': len([cmd for cmd in self.commands.values() if not cmd.hidden])
        }
    
    def _get_help(self) -> Dict[str, Any]:
        """Get general help information"""
        return {
            'help_info': {
                'usage': 'Type /command or /command arguments',
                'help_command': 'Use /help or /help <command> for specific help',
                'list_commands': 'Use /help to see all available commands',
                'search_commands': 'Use /search <term> to find commands'
            },
            'available_commands': len(self.commands)
        }
    
    def get_command_suggestions(self, partial_command: str) -> List[str]:
        """Get command suggestions for autocomplete"""
        partial = partial_command.lower()
        suggestions = []
        
        for name, command in self.commands.items():
            if command.hidden:
                continue
                
            if name.startswith(partial):
                suggestions.append(name)
            
            # Check aliases
            for alias in command.aliases:
                if alias.startswith(partial):
                    suggestions.append(alias)
        
        return sorted(suggestions)
    
    def get_status(self) -> Dict[str, Any]:
        """Get slash command tool status"""
        categories = {}
        for command in self.commands.values():
            categories[command.category] = categories.get(command.category, 0) + 1
        
        return {
            'tool_name': self.name,
            'version': self.version,
            'registered_commands': len(self.commands),
            'categories': categories,
            'capabilities': self.capabilities
        }