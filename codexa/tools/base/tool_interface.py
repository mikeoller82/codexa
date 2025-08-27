"""
Base tool interface and result classes for Codexa tool system.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union, Callable
import logging


class ToolStatus(Enum):
    """Tool execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"


class ToolPriority(Enum):
    """Tool execution priority."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ToolContext:
    """Context object for tool execution with shared state."""
    
    # Core context
    request_id: str
    user_request: str
    session_id: Optional[str] = None
    
    # Execution context
    current_dir: Optional[str] = None
    project_info: Dict[str, Any] = field(default_factory=dict)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    
    # Tool coordination
    shared_state: Dict[str, Any] = field(default_factory=dict)
    previous_results: Dict[str, Any] = field(default_factory=dict)
    tool_chain: List[str] = field(default_factory=list)
    
    # Configuration
    config: Optional[Any] = None
    mcp_service: Optional[Any] = None
    provider: Optional[Any] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def update_state(self, key: str, value: Any) -> None:
        """Update shared state."""
        self.shared_state[key] = value
        self.updated_at = datetime.now()
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """Get shared state value."""
        return self.shared_state.get(key, default)
    
    def add_result(self, tool_name: str, result: Any) -> None:
        """Add tool result to context."""
        self.previous_results[tool_name] = result
        self.updated_at = datetime.now()
    
    def get_result(self, tool_name: str) -> Any:
        """Get previous tool result."""
        return self.previous_results.get(tool_name)


@dataclass
class ToolResult:
    """Result object for tool execution."""
    
    # Core result data
    success: bool
    data: Any = None
    error: Optional[str] = None
    
    # Metadata
    tool_name: str = ""
    execution_time: float = 0.0
    status: ToolStatus = ToolStatus.SUCCESS
    
    # Output information
    output: Optional[str] = None
    files_created: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    
    # Context updates
    state_updates: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    
    # Performance metrics
    memory_used: Optional[int] = None
    tokens_used: Optional[int] = None
    
    def __post_init__(self):
        """Set status based on success."""
        if self.status == ToolStatus.SUCCESS and not self.success:
            self.status = ToolStatus.ERROR
    
    @classmethod
    def success_result(cls, data: Any = None, **kwargs) -> 'ToolResult':
        """Create successful result."""
        return cls(success=True, data=data, status=ToolStatus.SUCCESS, **kwargs)
    
    @classmethod
    def error_result(cls, error: str, **kwargs) -> 'ToolResult':
        """Create error result."""
        return cls(success=False, error=error, status=ToolStatus.ERROR, **kwargs)


class Tool(ABC):
    """
    Abstract base class for all Codexa tools.
    
    Each tool represents a single capability that can be dynamically
    loaded and executed by the agent based on request requirements.
    """
    
    def __init__(self):
        """Initialize base tool."""
        self.logger = logging.getLogger(f"codexa.tools.{self.name}")
        self._is_initialized = False
        self._execution_count = 0
        self._error_count = 0
        self._total_execution_time = 0.0
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name (must be unique)."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for help and routing."""
        pass
    
    @property
    @abstractmethod
    def category(self) -> str:
        """Tool category (filesystem, mcp, enhanced, etc)."""
        pass
    
    @property
    def capabilities(self) -> Set[str]:
        """Set of capabilities this tool provides."""
        return {self.name}
    
    @property
    def dependencies(self) -> Set[str]:
        """Set of tool names this tool depends on."""
        return set()
    
    @property
    def required_context(self) -> Set[str]:
        """Required context keys for tool execution."""
        return set()
    
    @property
    def priority(self) -> ToolPriority:
        """Tool execution priority."""
        return ToolPriority.NORMAL
    
    @property
    def is_async(self) -> bool:
        """Whether tool supports async execution."""
        return True
    
    @property
    def max_concurrent_executions(self) -> int:
        """Maximum concurrent executions (0 = unlimited)."""
        return 0
    
    @property
    def timeout_seconds(self) -> float:
        """Execution timeout in seconds (0 = no timeout)."""
        return 30.0
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """
        Determine if tool can handle request.
        
        Returns:
            Float between 0.0-1.0 indicating confidence/priority.
            0.0 = cannot handle, 1.0 = perfect match
        """
        return 0.0
    
    async def initialize(self, context: ToolContext) -> bool:
        """
        Initialize tool with context.
        
        Called once when tool is first loaded.
        
        Returns:
            True if initialization successful
        """
        self._is_initialized = True
        return True
    
    @abstractmethod
    async def execute(self, context: ToolContext) -> ToolResult:
        """
        Execute tool with given context.
        
        This is the main method that performs the tool's functionality.
        
        Args:
            context: Tool execution context with request and shared state
            
        Returns:
            ToolResult with execution results and metadata
        """
        pass
    
    async def validate_context(self, context: ToolContext) -> bool:
        """
        Validate that context contains required information.
        
        Args:
            context: Tool execution context
            
        Returns:
            True if context is valid
        """
        # Check required context keys
        for key in self.required_context:
            if not hasattr(context, key) or getattr(context, key) is None:
                self.logger.error(f"Required context key missing: {key}")
                return False
        return True
    
    async def cleanup(self, context: ToolContext) -> None:
        """
        Cleanup after tool execution.
        
        Called after execute() regardless of success/failure.
        """
        pass
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get tool usage statistics."""
        return {
            "execution_count": self._execution_count,
            "error_count": self._error_count,
            "success_rate": (self._execution_count - self._error_count) / max(1, self._execution_count),
            "average_execution_time": self._total_execution_time / max(1, self._execution_count),
            "total_execution_time": self._total_execution_time,
            "is_initialized": self._is_initialized
        }
    
    def _record_execution(self, execution_time: float, success: bool) -> None:
        """Record execution statistics."""
        self._execution_count += 1
        self._total_execution_time += execution_time
        if not success:
            self._error_count += 1
    
    async def safe_execute(self, context: ToolContext) -> ToolResult:
        """
        Safe execution wrapper with error handling and metrics.
        
        This method wraps execute() with standardized error handling,
        timeout management, and performance metrics collection.
        """
        start_time = datetime.now()
        
        try:
            # Validate context
            if not await self.validate_context(context):
                return ToolResult.error_result(
                    error=f"Context validation failed for tool: {self.name}",
                    tool_name=self.name
                )
            
            # Initialize if needed
            if not self._is_initialized:
                if not await self.initialize(context):
                    return ToolResult.error_result(
                        error=f"Tool initialization failed: {self.name}",
                        tool_name=self.name
                    )
            
            # Execute with timeout
            if self.timeout_seconds > 0:
                result = await asyncio.wait_for(
                    self.execute(context),
                    timeout=self.timeout_seconds
                )
            else:
                result = await self.execute(context)
            
            # Set tool name if not set
            if not result.tool_name:
                result.tool_name = self.name
            
            # Record metrics
            execution_time = (datetime.now() - start_time).total_seconds()
            result.execution_time = execution_time
            self._record_execution(execution_time, result.success)
            
            return result
            
        except asyncio.TimeoutError:
            error_msg = f"Tool execution timeout ({self.timeout_seconds}s): {self.name}"
            self.logger.error(error_msg)
            self._record_execution(self.timeout_seconds, False)
            return ToolResult.error_result(error=error_msg, tool_name=self.name)
            
        except Exception as e:
            error_msg = f"Tool execution error: {self.name} - {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            execution_time = (datetime.now() - start_time).total_seconds()
            self._record_execution(execution_time, False)
            return ToolResult.error_result(
                error=error_msg,
                tool_name=self.name,
                execution_time=execution_time
            )
        finally:
            try:
                await self.cleanup(context)
            except Exception as e:
                self.logger.warning(f"Tool cleanup error: {self.name} - {str(e)}")
    
    def __str__(self) -> str:
        """String representation."""
        return f"{self.name} ({self.category})"
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return f"Tool(name='{self.name}', category='{self.category}', capabilities={self.capabilities})"