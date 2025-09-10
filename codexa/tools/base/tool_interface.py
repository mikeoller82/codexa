"""
Base tool interface and result classes for Codexa tool system.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union, Callable, Tuple
import logging
try:
    from packaging.version import Version
except ImportError:
    # Fallback if packaging is not available
    class Version:
        def __init__(self, version_str):
            self.version_str = version_str
        def __ge__(self, other):
            return True
        def __le__(self, other):
            return True
        def __gt__(self, other):
            return True
        def __lt__(self, other):
            return True
        def __eq__(self, other):
            return True
        @property
        def major(self):
            return 1
        @property
        def minor(self):
            return 0


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


class DependencyType(Enum):
    """Tool dependency types."""
    REQUIRED = "required"  # Must execute before this tool
    OPTIONAL = "optional"  # Should execute before if available
    CONFLICT = "conflict"  # Cannot execute with this tool
    PROVIDES = "provides"  # This tool provides capabilities


@dataclass
class ToolDependency:
    """Tool dependency specification."""
    
    name: str  # Tool name or capability
    dependency_type: DependencyType
    version_constraint: Optional[str] = None  # e.g., ">=1.0.0", "~1.2"
    condition: Optional[str] = None  # Optional condition description
    fallback_tools: List[str] = field(default_factory=list)  # Alternative tools
    
    def is_satisfied_by(self, tool_info: Dict[str, Any]) -> bool:
        """Check if dependency is satisfied by tool info."""
        if self.dependency_type == DependencyType.CONFLICT:
            return tool_info.get('name') != self.name
        
        if tool_info.get('name') != self.name:
            # Check if tool provides the required capability
            capabilities = tool_info.get('capabilities', set())
            if isinstance(capabilities, (list, set)):
                if self.name not in capabilities:
                    return False
        
        # Check version constraint if specified
        if self.version_constraint and 'version' in tool_info:
            try:
                tool_version = Version(tool_info['version'])
                constraint = self.version_constraint
                
                if constraint.startswith('>='):
                    return tool_version >= Version(constraint[2:])
                elif constraint.startswith('<='):
                    return tool_version <= Version(constraint[2:])
                elif constraint.startswith('>'):
                    return tool_version > Version(constraint[1:])
                elif constraint.startswith('<'):
                    return tool_version < Version(constraint[1:])
                elif constraint.startswith('~'):
                    base_version = Version(constraint[1:])
                    return (tool_version >= base_version and 
                           tool_version.major == base_version.major and
                           tool_version.minor == base_version.minor)
                elif constraint.startswith('=='):
                    return tool_version == Version(constraint[2:])
                else:
                    return tool_version == Version(constraint)
            except Exception:
                # If version parsing fails, assume satisfied
                return True
        
        return True


@dataclass
class CoordinationConfig:
    """Configuration for tool coordination."""
    
    # Execution preferences
    prefer_parallel: bool = True
    max_parallel_tools: int = 3
    timeout_multiplier: float = 1.0
    
    # Dependency resolution
    resolve_dependencies: bool = True
    allow_dependency_fallbacks: bool = True
    strict_version_checking: bool = False
    
    # Error handling
    fail_on_missing_dependencies: bool = False
    continue_on_optional_failure: bool = True
    max_retry_attempts: int = 2
    
    # Resource management
    share_context_between_tools: bool = True
    cache_tool_results: bool = True
    result_cache_ttl: int = 3600  # seconds


@dataclass
class ContextualRequest:
    """Enhanced request object with context awareness."""
    
    # Original request
    raw_request: str
    processed_request: str
    request_type: str  # command, question, task, etc.
    
    # Context clues
    mentioned_files: List[str] = field(default_factory=list)
    mentioned_tools: List[str] = field(default_factory=list)
    required_capabilities: Set[str] = field(default_factory=set)
    
    # Intent analysis
    intent: str = ""  # create, modify, analyze, etc.
    confidence: float = 0.0
    urgency: str = "normal"  # low, normal, high, critical


@dataclass
class ToolContext:
    """Context object for tool execution with shared state."""
    
    # Core context - make more flexible
    tool_manager: Optional[Any] = None
    mcp_service: Optional[Any] = None
    config: Optional[Any] = None
    current_path: Optional[str] = None
    history: Optional[List[Dict]] = None
    
    # Optional detailed context
    request_id: Optional[str] = None
    user_request: Optional[str] = None
    session_id: Optional[str] = None
    
    # Execution context
    current_dir: Optional[str] = None
    project_info: Dict[str, Any] = field(default_factory=dict)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    
    # Tool coordination
    shared_state: Dict[str, Any] = field(default_factory=dict)
    previous_results: Dict[str, Any] = field(default_factory=dict)
    tool_chain: List[str] = field(default_factory=list)
    
    # Provider
    provider: Optional[Any] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Initialize optional fields after construction."""
        import uuid
        
        if self.request_id is None:
            self.request_id = str(uuid.uuid4())
        
        if self.session_id is None:
            self.session_id = str(uuid.uuid4())
        
        # Use current_path if current_dir is not set
        if self.current_dir is None and self.current_path:
            self.current_dir = self.current_path
    
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
    def dependencies(self) -> List[ToolDependency]:
        """List of tool dependencies this tool requires."""
        return []
    
    @property
    def legacy_dependencies(self) -> Set[str]:
        """Legacy simple dependency names (for backward compatibility)."""
        return set()
    
    @property
    def provides_capabilities(self) -> Set[str]:
        """Capabilities this tool provides (beyond its name)."""
        return set()
    
    @property
    def coordination_config(self) -> CoordinationConfig:
        """Tool coordination configuration."""
        return CoordinationConfig()
    
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
    
    @property
    def version(self) -> str:
        """Tool version for dependency resolution."""
        return "1.0.0"
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """
        Determine if tool can handle request.
        
        Returns:
            Float between 0.0-1.0 indicating confidence/priority.
            0.0 = cannot handle, 1.0 = perfect match
        """
        # Default implementation with basic keyword matching
        request_lower = request.lower()
        confidence = 0.0
        
        # Check if any capabilities match request keywords
        for capability in self.capabilities:
            if capability.lower() in request_lower:
                confidence = max(confidence, 0.8)
        
        # Check tool name match
        if self.name.lower() in request_lower:
            confidence = max(confidence, 0.7)
        
        # Check category-specific keywords
        category_keywords = {
            'filesystem': ['file', 'directory', 'folder', 'path', 'read', 'write', 'create', 'delete'],
            'enhanced': ['help', 'animation', 'theme', 'generate', 'search', 'plan'],
            'mcp': ['mcp', 'server', 'connection', 'query', 'documentation'],
            'ai': ['generate', 'create', 'analyze', 'explain', 'code', 'text', 'ai', 'gpt']
        }
        
        if self.category in category_keywords:
            for keyword in category_keywords[self.category]:
                if keyword in request_lower:
                    confidence = max(confidence, 0.4)
        
        # General AI-related keywords that any tool might handle
        ai_keywords = ['generate', 'create', 'make', 'build', 'analyze', 'explain', 'help']
        for keyword in ai_keywords:
            if keyword in request_lower:
                confidence = max(confidence, 0.3)
        
        return min(confidence, 1.0)
    
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
            # Check both shared_state and direct attributes
            value = context.get_state(key)
            if value is None:
                # Also check direct context attributes
                value = getattr(context, key, None)
            if value is None:
                self.logger.error(f"Required context key missing: {key}")
                return False
        return True
    
    async def cleanup(self, context: ToolContext) -> None:
        """
        Cleanup after tool execution.
        
        Called after execute() regardless of success/failure.
        """
        pass
    
    def check_dependencies(self, available_tools: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Check if all dependencies are satisfied.
        
        Args:
            available_tools: Dict of tool_name -> tool_info
            
        Returns:
            Tuple of (all_satisfied, missing_dependencies)
        """
        missing_deps = []
        
        # Check new dependency system
        for dep in self.dependencies:
            satisfied = False
            
            # Check direct tool match
            if dep.name in available_tools:
                if dep.is_satisfied_by(available_tools[dep.name]):
                    satisfied = True
            
            # Check capability match
            if not satisfied:
                for tool_name, tool_info in available_tools.items():
                    capabilities = tool_info.get('capabilities', set())
                    if isinstance(capabilities, (list, set)) and dep.name in capabilities:
                        if dep.is_satisfied_by(tool_info):
                            satisfied = True
                            break
            
            # Check fallbacks
            if not satisfied and dep.fallback_tools:
                for fallback in dep.fallback_tools:
                    if fallback in available_tools:
                        if dep.is_satisfied_by(available_tools[fallback]):
                            satisfied = True
                            break
            
            # Handle missing dependency
            if not satisfied:
                if dep.dependency_type == DependencyType.REQUIRED:
                    missing_deps.append(dep.name)
                elif dep.dependency_type == DependencyType.OPTIONAL:
                    self.logger.debug(f"Optional dependency not available: {dep.name}")
        
        # Check legacy dependencies for backward compatibility
        for dep_name in self.legacy_dependencies:
            if dep_name not in available_tools:
                missing_deps.append(dep_name)
        
        return len(missing_deps) == 0, missing_deps
    
    def get_execution_order_hints(self) -> Dict[str, int]:
        """Get hints for tool execution ordering.
        
        Returns:
            Dict of dependency_name -> preference_score
            Higher scores indicate should execute earlier
        """
        hints = {}
        
        for dep in self.dependencies:
            if dep.dependency_type == DependencyType.REQUIRED:
                hints[dep.name] = 100
            elif dep.dependency_type == DependencyType.OPTIONAL:
                hints[dep.name] = 50
        
        return hints
    
    def can_run_parallel_with(self, other_tool: 'Tool') -> bool:
        """Check if this tool can run in parallel with another tool.
        
        Args:
            other_tool: Another tool instance
            
        Returns:
            True if tools can run in parallel
        """
        # Check for conflicts
        for dep in self.dependencies:
            if dep.dependency_type == DependencyType.CONFLICT:
                if (dep.name == other_tool.name or 
                    dep.name in other_tool.provides_capabilities):
                    return False
        
        # Check other tool's conflicts
        for dep in other_tool.dependencies:
            if dep.dependency_type == DependencyType.CONFLICT:
                if (dep.name == self.name or 
                    dep.name in self.provides_capabilities):
                    return False
        
        # Check coordination config
        return (self.coordination_config.prefer_parallel and 
                other_tool.coordination_config.prefer_parallel)
    
    async def prepare_for_coordination(self, context: ToolContext) -> bool:
        """Prepare tool for coordinated execution.
        
        Called before execute() in coordinated scenarios.
        Override to implement tool-specific preparation.
        
        Args:
            context: Tool execution context
            
        Returns:
            True if preparation successful
        """
        return True
    
    async def coordinate_with_dependency(self, 
                                       dependency_result: ToolResult, 
                                       context: ToolContext) -> None:
        """Handle result from a dependency tool.
        
        Called when a dependency tool completes successfully.
        Override to implement custom coordination logic.
        
        Args:
            dependency_result: Result from dependency tool
            context: Tool execution context
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