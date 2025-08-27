"""
Base command class for Codexa commands.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class CommandResult:
    """Result of command execution."""
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class BaseCommand(ABC):
    """Base class for all Codexa commands."""
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the command name."""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Get the command description."""
        pass
    
    def get_usage(self) -> str:
        """Get command usage information."""
        return f"Usage: /{self.get_name()}"
    
    def get_aliases(self) -> List[str]:
        """Get command aliases."""
        return []
    
    @abstractmethod
    async def execute(self, args: List[str], context: Dict[str, Any] = None) -> CommandResult:
        """Execute the command."""
        pass
    
    def validate_args(self, args: List[str]) -> Optional[str]:
        """Validate command arguments. Return error message if invalid, None if valid."""
        return None