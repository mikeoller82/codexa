"""
Command parser for Codexa slash commands.
"""

import re
import shlex
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum


class ParseError(Exception):
    """Command parsing error."""
    pass


@dataclass
class ParsedCommand:
    """Result of command parsing."""
    command: str
    args: List[str]
    kwargs: Dict[str, Any]
    flags: List[str]
    raw_input: str
    
    def get_arg(self, index: int, default: Any = None) -> Any:
        """Get positional argument by index."""
        return self.args[index] if index < len(self.args) else default
    
    def get_kwarg(self, key: str, default: Any = None) -> Any:
        """Get keyword argument by key."""
        return self.kwargs.get(key, default)
    
    def has_flag(self, flag: str) -> bool:
        """Check if flag is present."""
        return flag in self.flags


class CommandParser:
    """Parser for Codexa slash commands."""
    
    def __init__(self):
        # Regex patterns for parsing
        self.command_pattern = re.compile(r'^/(\w+)')
        self.flag_pattern = re.compile(r'--(\w+)(?:=([^"\s]+|"[^"]*"))?')
        self.short_flag_pattern = re.compile(r'-([a-zA-Z])')
        self.quoted_string_pattern = re.compile(r'"([^"]*)"')
        
        # Flag aliases (short form -> long form)
        self.flag_aliases = {
            'h': 'help',
            'v': 'verbose',
            'q': 'quiet',
            's': 'safe',
            'f': 'force',
            't': 'type',
            'o': 'output'
        }
    
    def parse(self, input_text: str) -> ParsedCommand:
        """Parse command input text."""
        if not input_text.strip():
            raise ParseError("Empty input")
        
        if not input_text.startswith('/'):
            raise ParseError("Commands must start with '/'")
        
        # Extract command name
        command_match = self.command_pattern.match(input_text)
        if not command_match:
            raise ParseError("Invalid command format")
        
        command_name = command_match.group(1)
        remaining_text = input_text[command_match.end():].strip()
        
        # Parse the remaining text
        args, kwargs, flags = self._parse_arguments(remaining_text)
        
        return ParsedCommand(
            command=command_name,
            args=args,
            kwargs=kwargs,
            flags=flags,
            raw_input=input_text
        )
    
    def _parse_arguments(self, text: str) -> Tuple[List[str], Dict[str, Any], List[str]]:
        """Parse command arguments, keyword arguments, and flags."""
        if not text:
            return [], {}, []
        
        args = []
        kwargs = {}
        flags = []
        
        # First pass: extract flags and quoted strings
        processed_text = text
        
        # Extract long flags (--flag or --flag=value)
        for match in self.flag_pattern.finditer(text):
            flag_name = match.group(1)
            flag_value = match.group(2)
            
            if flag_value:
                # Flag with value: --key=value
                kwargs[flag_name] = self._parse_value(flag_value)
            else:
                # Boolean flag: --flag
                flags.append(flag_name)
        
        # Remove flags from text
        processed_text = self.flag_pattern.sub('', processed_text)
        
        # Extract short flags (-f)
        for match in self.short_flag_pattern.finditer(processed_text):
            short_flag = match.group(1)
            long_flag = self.flag_aliases.get(short_flag, short_flag)
            flags.append(long_flag)
        
        # Remove short flags from text
        processed_text = self.short_flag_pattern.sub('', processed_text)
        
        # Parse remaining arguments using shlex for proper quoting
        try:
            remaining_args = shlex.split(processed_text)
            
            # Process key=value pairs and positional arguments
            for arg in remaining_args:
                if '=' in arg and not arg.startswith('"'):
                    # Keyword argument
                    key, value = arg.split('=', 1)
                    kwargs[key] = self._parse_value(value)
                else:
                    # Positional argument
                    args.append(self._parse_value(arg))
        
        except ValueError as e:
            raise ParseError(f"Failed to parse arguments: {e}")
        
        return args, kwargs, flags
    
    def _parse_value(self, value: str) -> Any:
        """Parse and convert argument value to appropriate type."""
        if not isinstance(value, str):
            return value
        
        # Remove quotes if present
        if value.startswith('"') and value.endswith('"'):
            return value[1:-1]
        
        # Try to convert to appropriate type
        lower_value = value.lower()
        
        # Boolean values
        if lower_value in ('true', '1', 'yes', 'on'):
            return True
        elif lower_value in ('false', '0', 'no', 'off'):
            return False
        
        # Numeric values
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def suggest_completion(self, partial_input: str, 
                          available_commands: List[str]) -> List[str]:
        """Suggest command completions for partial input."""
        if not partial_input.startswith('/'):
            return []
        
        if partial_input == '/':
            return available_commands[:10]  # Show top 10 commands
        
        # Extract partial command name
        parts = partial_input[1:].split(' ', 1)
        partial_command = parts[0]
        
        if len(parts) == 1:
            # Completing command name
            suggestions = [cmd for cmd in available_commands 
                          if cmd.startswith(partial_command)]
            return suggestions[:10]
        
        # TODO: Add parameter completion for specific commands
        return []
    
    def validate_syntax(self, input_text: str) -> List[str]:
        """Validate command syntax and return error messages."""
        errors = []
        
        if not input_text.strip():
            errors.append("Empty command")
            return errors
        
        if not input_text.startswith('/'):
            errors.append("Commands must start with '/'")
            return errors
        
        try:
            self.parse(input_text)
        except ParseError as e:
            errors.append(str(e))
        
        return errors
    
    def format_help(self, command_name: str, description: str, 
                   parameters: List[Dict[str, Any]] = None) -> str:
        """Format help text for a command."""
        help_lines = [f"/{command_name} - {description}"]
        
        if parameters:
            help_lines.append("\nUsage:")
            usage_parts = [f"/{command_name}"]
            
            for param in parameters:
                name = param['name']
                required = param.get('required', False)
                param_type = param.get('type', 'str')
                
                if required:
                    usage_parts.append(f"<{name}>")
                else:
                    usage_parts.append(f"[{name}]")
            
            help_lines.append("  " + " ".join(usage_parts))
            
            help_lines.append("\nParameters:")
            for param in parameters:
                param_line = f"  {param['name']}"
                if param.get('type'):
                    param_line += f" ({param['type']})"
                if not param.get('required', False):
                    param_line += " [optional]"
                if param.get('default'):
                    param_line += f" [default: {param['default']}]"
                param_line += f" - {param.get('description', 'No description')}"
                help_lines.append(param_line)
        
        return "\n".join(help_lines)
    
    def extract_mentions(self, text: str) -> List[str]:
        """Extract @mentions from command text."""
        mention_pattern = re.compile(r'@(\w+)')
        return [match.group(1) for match in mention_pattern.finditer(text)]
    
    def extract_file_paths(self, text: str) -> List[str]:
        """Extract file paths from command text."""
        # Simple file path extraction (can be enhanced)
        file_pattern = re.compile(r'([./][\w./\-]+\.\w+)')
        return [match.group(1) for match in file_pattern.finditer(text)]
    
    def is_valid_command_name(self, name: str) -> bool:
        """Check if command name is valid."""
        return bool(re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', name))
    
    def escape_argument(self, arg: str) -> str:
        """Escape argument for safe shell usage."""
        if ' ' in arg or '"' in arg or "'" in arg:
            return f'"{arg.replace('"', '\\"')}"'
        return arg