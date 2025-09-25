"""
Tool manager for Codexa tool system.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass
import logging

from .tool_interface import Tool, ToolResult, ToolContext, ToolStatus, ToolPriority, CoordinationConfig
from .tool_registry import ToolRegistry, ToolInfo
from .tool_context import ToolContextManager, RequestAnalyzer, ContextualRequest
from .tool_performance_monitor import ToolPerformanceMonitor
from .tool_coordinator import ToolCoordinator
from .ai_error_handler import AIErrorHandler

# Claude Code integration
try:
    from ..claude_code.claude_code_registry import claude_code_registry
    CLAUDE_CODE_AVAILABLE = True
except ImportError:
    CLAUDE_CODE_AVAILABLE = False
    claude_code_registry = None


@dataclass
class ExecutionPlan:
    """Plan for executing tools to handle a request."""
    
    request_id: str
    tools: List[str]  # Ordered list of tool names
    parallel_groups: List[List[str]]  # Tools that can run in parallel
    estimated_time: float
    estimated_complexity: float
    requires_user_input: bool = False
    
    def get_total_tools(self) -> int:
        """Get total number of tools in plan."""
        return len(self.tools)
    
    def get_parallel_efficiency(self) -> float:
        """Calculate parallel execution efficiency."""
        total_tools = self.get_total_tools()
        if total_tools == 0:
            return 0.0
        
        parallel_tools = sum(len(group) for group in self.parallel_groups)
        return parallel_tools / total_tools


class ToolManager:
    """
    Central tool management system for Codexa.
    
    Manages tool discovery, selection, execution, and coordination.
    Provides intelligent routing and execution planning.
    """
    
    def __init__(self, registry: Optional[ToolRegistry] = None, auto_discover: bool = True, enable_performance_monitoring: bool = True, enable_coordination: bool = True):
        """
        Initialize tool manager.
        
        Args:
            registry: Optional existing tool registry to use
            auto_discover: Whether to automatically discover tools
            enable_performance_monitoring: Whether to enable advanced performance monitoring
            enable_coordination: Whether to enable tool coordination and dependency resolution
        """
        self.logger = logging.getLogger("codexa.tools.manager")
        
        # Core components
        self.registry = registry if registry is not None else ToolRegistry()
        self.context_manager = ToolContextManager()
        self.request_analyzer = RequestAnalyzer()
        
        # Performance monitoring
        self.performance_monitor = ToolPerformanceMonitor() if enable_performance_monitoring else None
        if self.performance_monitor:
            self.performance_monitor.start_monitoring()
            self.logger.info("Performance monitoring enabled")
        
        # Tool coordination
        self.coordinator = ToolCoordinator(self.registry) if enable_coordination else None
        if self.coordinator:
            self.logger.info("Tool coordination enabled")
        
        # AI-aware error handling
        self.error_handler = AIErrorHandler()
        self.logger.info("AI-aware error handling enabled")
        
        # Execution state
        self._active_executions: Dict[str, asyncio.Task] = {}
        self._execution_history: List[Dict[str, Any]] = []
        self._max_concurrent_executions = 5
        self._max_history = 1000
        
        # Performance tracking (legacy - replaced by performance_monitor)
        self._total_executions = 0
        self._successful_executions = 0
        self._failed_executions = 0
        self._total_execution_time = 0.0
        
        # Auto-discover tools if requested
        if auto_discover:
            self.discover_tools()
        
        # Register Claude Code tools if available
        if CLAUDE_CODE_AVAILABLE and claude_code_registry:
            try:
                claude_code_registry.register_claude_code_tools(self.registry)
                self.logger.info("Claude Code tools registered successfully")
            except Exception as e:
                self.logger.warning(f"Failed to register Claude Code tools: {e}")
    
    def discover_tools(self) -> int:
        """
        Discover and register all available tools.
        
        Returns:
            Number of tools discovered
        """
        self.logger.info("Discovering tools...")
        
        # Discover from standard locations
        total_discovered = 0
        
        discovery_paths = [
            "codexa.tools.filesystem",
            "codexa.tools.mcp", 
            "codexa.tools.ai_providers",
            "codexa.tools.enhanced",
            "codexa.tools.system",
            "codexa.tools.claude_code"
        ]
        
        for path in discovery_paths:
            try:
                discovered = self.registry.discover_tools(path)
                total_discovered += discovered
                self.logger.debug(f"Discovered {discovered} tools from {path}")
            except Exception as e:
                self.logger.warning(f"Failed to discover tools from {path}: {e}")
        
        self.logger.info(f"Tool discovery complete: {total_discovered} tools registered")
        return total_discovered

    def _extract_bash_command(self, request: str) -> str:
        """Extract bash command from request string."""
        import re

        # Debug log
        self.logger.debug(f"Extracting bash command from: '{request}'")

        # Remove common prefixes
        original_request = request
        request = request.lower()
        for prefix in ["run ", "execute ", "bash ", "shell ", "command "]:
            if request.startswith(prefix):
                prefix_len = len(prefix)
                request = request[prefix_len:]
                original_request = original_request[prefix_len:]

        # If the command has quotes, preserve the entire command including the quote content
        # This handles cases like "echo 'Hello World'"
        if "'" in original_request or '"' in original_request:
            # Just return the entire command after removing the prefix
            result = original_request.strip()
            self.logger.debug(f"Extracted command with quotes: '{result}'")
            return result

        # If no quotes, take the rest of the command after the prefix
        result = original_request.strip()
        self.logger.debug(f"Extracted command: '{result}'")
        return result

    def _extract_directory_path(self, request: str) -> str:
        """Extract directory path from request string."""
        import re

        # Look for directory patterns
        patterns = [
            r'["\']([^"\']+)["\']',  # Quoted paths
            r'directory\s+([^\s]+)',  # "directory path"
            r'folder\s+([^\s]+)',     # "folder path"
            r'ls\s+([^\s]+)',         # "ls path"
            r'([a-zA-Z0-9_/.-]+/)',  # Paths ending with /
        ]

        for pattern in patterns:
            matches = re.findall(pattern, request, re.IGNORECASE)
            if matches:
                return matches[0]

        return ""

    def _extract_file_path(self, request: str) -> str:
        """Extract file path from request string."""
        import re

        # Look for file paths in quotes
        patterns = [
            r'["\']([^"\']+)["\']',  # Quoted paths
            r'file\s+([^\s]+)',      # "file path"
            r'read\s+([^\s]+)',      # "read path"
            r'([a-zA-Z0-9_/.-]+\.[a-zA-Z0-9]+)'  # Files with extensions
        ]

        for pattern in patterns:
            matches = re.findall(pattern, request, re.IGNORECASE)
            if matches:
                return matches[0]

        return ""
    
    async def process_request(self, 
                            request: str,
                            context: Optional[ToolContext] = None,
                            session_id: Optional[str] = None,
                            current_dir: Optional[str] = None,
                            config: Optional[Any] = None,
                            mcp_service: Optional[Any] = None,
                            provider: Optional[Any] = None,
                            max_tools: int = 3,
                            allow_parallel: bool = True,
                            enable_coordination: bool = True,
                            coordination_config: Optional[CoordinationConfig] = None,
                            verbose: bool = False,
                            **kwargs) -> ToolResult:
        """
        Process user request using appropriate tools.
        
        Args:
            request: User request string
            session_id: Optional session identifier
            current_dir: Current working directory
            config: Configuration object
            mcp_service: MCP service instance
            provider: AI provider instance
            max_tools: Maximum number of tools to use
            allow_parallel: Whether to allow parallel execution
            **kwargs: Additional context data
            
        Returns:
            Consolidated tool result
        """
        try:
            # Import console for verbose output
            from rich.console import Console
            console = Console()
            
            # Create execution context if not provided
            if context is None:
                if verbose:
                    console.print("[dim]📋 Creating execution context...[/dim]")
                context = self.context_manager.create_context(
                    user_request=request,
                    session_id=session_id,
                    current_dir=current_dir,
                    config=config,
                    mcp_service=mcp_service,
                    provider=provider,
                    **kwargs
                )
            
            # Analyze request
            if verbose:
                console.print("[dim]🔍 Analyzing request structure...[/dim]")
            contextual_request = self.request_analyzer.analyze_request(request)
            
            if verbose:
                console.print(f"[dim]   • Request type: {contextual_request.request_type}[/dim]")
                console.print(f"[dim]   • Complexity: {contextual_request.estimated_complexity:.1f}/1.0[/dim]")
                if hasattr(contextual_request, 'entities') and contextual_request.entities:
                    console.print(f"[dim]   • Entities: {', '.join(contextual_request.entities)}[/dim]")
                if contextual_request.mentioned_files:
                    console.print(f"[dim]   • Files: {', '.join(contextual_request.mentioned_files[:3])}{'...' if len(contextual_request.mentioned_files) > 3 else ''}[/dim]")
            
            # Check if coordination is enabled and beneficial
            use_coordination = (enable_coordination and 
                              self.coordinator is not None and
                              max_tools > 1)
            
            if verbose:
                console.print(f"[dim]🎯 Using {'coordinated' if use_coordination else 'sequential'} execution[/dim]")
            
            if use_coordination:
                # Use coordinated execution
                if verbose:
                    console.print("[dim]⚙️ Starting tool coordination...[/dim]")
                return await self._process_request_coordinated(
                    contextual_request,
                    context,
                    max_tools,
                    coordination_config,
                    verbose=verbose
                )
            else:
                # Use legacy execution plan
                if verbose:
                    console.print("[dim]📝 Creating execution plan...[/dim]")
                plan = await self._create_execution_plan(
                    contextual_request, 
                    context, 
                    max_tools,
                    allow_parallel,
                    verbose=verbose
                )
                
                if not plan.tools:
                    if verbose:
                        console.print("[red]❌ No suitable tools found[/red]")
                    return ToolResult.error_result(
                        error="No suitable tools found for request",
                        tool_name="tool_manager"
                    )
                
                if verbose:
                    console.print(f"[dim]📋 Plan: {len(plan.tools)} tools, estimated {plan.estimated_time:.1f}s[/dim]")
                    for i, tool_name in enumerate(plan.tools, 1):
                        console.print(f"[dim]   {i}. {tool_name}[/dim]")
                
                # Execute plan
                if verbose:
                    console.print("[dim]⚡ Executing plan...[/dim]")
                result = await self._execute_plan(plan, context, verbose=verbose)
                
                # Update context with results
                context.add_result("final_result", result)
                self.context_manager.update_context(context)
                
                # Record execution
                self._record_execution(plan, result)
                
                if verbose:
                    status = "✅ Success" if result.success else "❌ Failed"
                    console.print(f"[dim]🏁 Execution complete: {status}[/dim]")
                
                return result
            
        except Exception as e:
            self.logger.error(f"Request processing failed: {e}", exc_info=True)
            return ToolResult.error_result(
                error=f"Request processing failed: {str(e)}",
                tool_name="tool_manager"
            )
    
    async def execute_tool(self, 
                          tool_name: str, 
                          context: ToolContext) -> ToolResult:
        """
        Execute a single tool.
        
        Args:
            tool_name: Name of tool to execute
            context: Execution context
            
        Returns:
            Tool execution result
        """
        try:
            # Get tool
            tool = self.registry.get_tool(tool_name)
            if not tool:
                return ToolResult.error_result(
                    error=f"Tool not found: {tool_name}",
                    tool_name=tool_name
                )
            
            # Extract parameters for basic tools and Claude Code tools
            user_request = context.user_request or ""

            # Handle Claude Code tools
            if (CLAUDE_CODE_AVAILABLE and claude_code_registry and
                hasattr(tool, 'category') and tool.category == "claude_code"):
                try:
                    extracted_params = claude_code_registry.extract_parameters_from_request(
                        tool_name, user_request, context
                    )

                    # Validate and set parameters in context with enhanced error handling
                    validation = claude_code_registry.validate_parameters(tool_name, extracted_params)
                    if validation["valid"]:
                        for key, value in validation["parameters"].items():
                            # Only set non-None values to avoid overriding defaults
                            if value is not None:
                                context.update_state(key, value)

                        # Log successful validation with security status
                        security_status = "with security validation" if validation.get("security_validated") else "legacy validation"
                        self.logger.debug(f"Parameters validated for {tool_name} {security_status}")
                    else:
                        # Enhanced error logging and user guidance
                        error_msg = validation.get('error', 'Unknown validation error')
                        self.logger.warning(f"Claude Code parameter validation failed for {tool_name}: {error_msg}")

                        # For natural language requests, be more forgiving
                        is_natural_language = (
                            len(user_request.split()) > 3 and
                            not any(user_request.startswith(prefix) for prefix in ['/', '--', '-'])
                        )

                        if is_natural_language:
                            # For natural language, don't fail on parameter validation
                            # Instead, try to continue with available parameters
                            self.logger.info(f"Natural language request - proceeding despite parameter validation failure for {tool_name}")
                            context.update_state("parameter_warnings",
                                               context.get_state("parameter_warnings", []) + [error_msg])
                        else:
                            # For structured requests, suggest upgrade and continue
                            if not validation.get("security_validated", True):
                                self.logger.info(f"Tool {tool_name} using legacy validation - consider upgrading to unified_validator")

                            # Don't fail execution but log the issue
                            context.update_state("validation_warnings",
                                               context.get_state("validation_warnings", []) + [error_msg])

                except Exception as e:
                    self.logger.debug(f"Claude Code parameter extraction failed for {tool_name}: {e}")

                    # For natural language requests, don't let parameter extraction failures stop execution
                    is_natural_language = (
                        len(user_request.split()) > 3 and
                        not any(user_request.startswith(prefix) for prefix in ['/', '--', '-'])
                    )

                    if is_natural_language:
                        self.logger.info(f"Natural language request - proceeding despite parameter extraction failure for {tool_name}")
                        context.update_state("extraction_warnings",
                                           context.get_state("extraction_warnings", []) + [str(e)])
                        
                        # For natural language requests, try to infer parameters from the request
                        # This helps with Claude Code tools that might need specific parameters
                        if hasattr(tool, 'required_context') and tool.required_context:
                            for param in tool.required_context:
                                # Only try to infer if parameter is not already set
                                if context.get_state(param) is None:
                                    inferred_value = self._infer_parameter_from_natural_language(
                                        param, user_request, tool_name
                                    )
                                    if inferred_value is not None:
                                        context.update_state(param, inferred_value)
                                        self.logger.info(f"Inferred parameter {param}={inferred_value} for {tool_name}")
                    # Continue with execution - not critical

            # Handle basic and system tools parameter extraction
            elif hasattr(tool, 'category') and tool.category in ["basic", "system"]:
                try:
                    # Extract parameters for basic tools based on tool name
                    if tool_name == "bash":
                        command = self._extract_bash_command(user_request)
                        if command:
                            context.update_state("command", command)
                            self.logger.debug(f"Extracted bash command: {command}")

                    elif tool_name == "list":
                        directory_path = self._extract_directory_path(user_request)
                        if directory_path:
                            context.update_state("directory_path", directory_path)
                            self.logger.debug(f"Extracted directory path: {directory_path}")

                    elif tool_name == "read":
                        file_path = self._extract_file_path(user_request)
                        if file_path:
                            context.update_state("file_path", file_path)
                            self.logger.debug(f"Extracted file path: {file_path}")

                except Exception as e:
                    self.logger.debug(f"Basic tool parameter extraction failed for {tool_name}: {e}")
                    # Continue with execution - not critical
            
            # Check concurrent execution limits
            if tool.max_concurrent_executions > 0:
                active_count = sum(
                    1 for task_name, task in self._active_executions.items()
                    if task_name.startswith(f"{tool_name}:") and not task.done()
                )
                
                if active_count >= tool.max_concurrent_executions:
                    return ToolResult.error_result(
                        error=f"Tool concurrent execution limit exceeded: {tool_name}",
                        tool_name=tool_name
                    )
            
            # Create execution task
            task_id = f"{tool_name}:{context.request_id}"
            task = asyncio.create_task(tool.safe_execute(context))
            self._active_executions[task_id] = task
            
            try:
                # Execute tool
                result = await task
                
                # Update context with result
                context.add_result(tool_name, result)
                
                return result
                
            finally:
                # Cleanup task
                self._active_executions.pop(task_id, None)
        
        except Exception as e:
            self.logger.error(f"Tool execution failed: {tool_name} - {e}", exc_info=True)
            
            # Use AI-aware error handler for recovery
            try:
                recovery_result = await self.error_handler.handle_error(tool_name, e, context)
                
                # Check if error handler suggests retry or fallback
                if recovery_result.success and recovery_result.data:
                    if recovery_result.data.get("retry_requested"):
                        # Retry the tool execution
                        self.logger.info(f"Retrying {tool_name} as suggested by error handler")
                        return await self.execute_tool(tool_name, context)
                    
                    elif recovery_result.data.get("fallback_requested"):
                        # Suggest fallback tools to the calling system
                        fallback_tools = recovery_result.data.get("fallback_tools", [])
                        self.logger.info(f"Error handler suggests fallback tools: {fallback_tools}")
                        
                        # Try the first fallback tool if available
                        for fallback_tool in fallback_tools:
                            if self.registry.get_tool(fallback_tool):
                                self.logger.info(f"Attempting fallback to {fallback_tool}")
                                fallback_result = await self.execute_tool(fallback_tool, context)
                                if fallback_result.success:
                                    return fallback_result
                
                # If error handler provided a graceful response, use it
                if recovery_result.success and recovery_result.data.get("degraded_mode"):
                    return recovery_result
                    
            except Exception as handler_error:
                self.logger.error(f"Error handler failed: {handler_error}")
            
            # Fallback to basic error result
            return ToolResult.error_result(
                error=f"Tool execution error: {str(e)}",
                tool_name=tool_name
            )
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names."""
        return list(self.registry.get_all_tools().keys())
    
    def get_tools_by_category(self, category: str) -> List[str]:
        """Get tools in a specific category."""
        return self.registry.get_tools_by_category(category)
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool information dictionary or None
        """
        tool_info = self.registry.get_tool_info(tool_name)
        if not tool_info:
            return None
        
        # Get usage stats if tool is loaded
        usage_stats = {}
        if tool_info.instance:
            usage_stats = tool_info.instance.get_usage_stats()
        
        return {
            "name": tool_info.name,
            "description": tool_info.description,
            "category": tool_info.category,
            "capabilities": list(tool_info.capabilities),
            "dependencies": list(tool_info.dependencies),
            "priority": tool_info.priority.value,
            "is_loaded": tool_info.is_loaded,
            "load_count": tool_info.load_count,
            "last_used": tool_info.last_used.isoformat() if tool_info.last_used else None,
            "error_count": tool_info.error_count,
            "usage_stats": usage_stats
        }
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """Get tool manager statistics."""
        registry_stats = self.registry.get_registry_stats()
        context_stats = self.context_manager.get_context_stats()
        
        success_rate = 0.0
        if self._total_executions > 0:
            success_rate = self._successful_executions / self._total_executions
        
        avg_execution_time = 0.0
        if self._successful_executions > 0:
            avg_execution_time = self._total_execution_time / self._successful_executions
        
        return {
            "registry": registry_stats,
            "context_manager": context_stats,
            "executions": {
                "total": self._total_executions,
                "successful": self._successful_executions,
                "failed": self._failed_executions,
                "success_rate": success_rate,
                "average_execution_time": avg_execution_time,
                "active_executions": len(self._active_executions),
                "max_concurrent": self._max_concurrent_executions
            },
            "history_size": len(self._execution_history)
        }
    
    async def _create_execution_plan(self, 
                                   contextual_request: ContextualRequest,
                                   context: ToolContext,
                                   max_tools: int,
                                   allow_parallel: bool,
                                   verbose: bool = False) -> ExecutionPlan:
        """Create execution plan for request."""
        # Find candidate tools
        candidates = self.registry.find_tools_for_request(
            contextual_request, 
            context, 
            max_tools * 2  # Get more candidates for better selection
        )
        
        # Select best tools with adaptive threshold for better coverage
        selected_tools = []

        # Check if this is a natural language request
        user_request = context.user_request or ""
        is_natural_language = (
            len(user_request.split()) > 3 and
            not any(user_request.startswith(prefix) for prefix in ['/', '--', '-'])
        )

        # Use adaptive confidence threshold
        min_confidence = 0.01 if is_natural_language else 0.05  # Much lower for natural language

        for tool_name, confidence in candidates[:max_tools]:
            if confidence > min_confidence:
                # Check if tool can actually execute with current context
                tool = self.registry.get_tool(tool_name)
                if tool and self._can_tool_execute(tool, context, check_parameters=not is_natural_language):
                    selected_tools.append(tool_name)
                    if is_natural_language:
                        self.logger.debug(f"Selected tool {tool_name} for natural language request (confidence: {confidence:.3f})")
                else:
                    self.logger.debug(f"Skipping tool {tool_name} due to context validation")
            elif is_natural_language and confidence > 0.001:
                # For natural language, be even more permissive for very low confidence tools
                tool = self.registry.get_tool(tool_name)
                if tool and self._can_tool_execute(tool, context, check_parameters=False):
                    selected_tools.append(tool_name)
                    self.logger.debug(f"Selected low-confidence tool {tool_name} for natural language request (confidence: {confidence:.3f})")

        # If still no tools found, be more permissive
        if not selected_tools and candidates:
            # Try to find any tool that can execute, even with very low confidence
            for tool_name, confidence in candidates:
                tool = self.registry.get_tool(tool_name)
                if tool and self._can_tool_execute(tool, context, check_parameters=False):
                    selected_tools.append(tool_name)
                    self.logger.warning(f"Using very low-confidence tool {tool_name} (confidence: {confidence:.3f}) as fallback")
                    break
        
        # CRITICAL: Ensure we always have at least one tool available
        # This prevents "no suitable tools found" errors
        if not selected_tools:
            # Try to get the universal fallback tool
            fallback_tool = self.registry.get_tool("universal_fallback")
            if fallback_tool:
                selected_tools.append("universal_fallback")
                self.logger.info("Using universal fallback tool as last resort")
            else:
                # If fallback tool not available, use any tool with lowest confidence
                if candidates:
                    selected_tools.append(candidates[0][0])
                    self.logger.warning(f"Using low-confidence tool {candidates[0][0]} as fallback")
                else:
                    # This should never happen, but if it does, we need to handle it
                    self.logger.error("No tools available at all - this indicates a serious system issue")
                    # Try to register the fallback tool dynamically
                    try:
                        from ..enhanced.universal_fallback_tool import UniversalFallbackTool
                        self.registry.register_tool(UniversalFallbackTool)
                        selected_tools.append("universal_fallback")
                        self.logger.info("Dynamically registered universal fallback tool")
                    except Exception as e:
                        self.logger.error(f"Failed to register fallback tool: {e}")
                        # Last resort - use conversational tool if available
                        if "conversational_tool" in self.registry.get_all_tools():
                            selected_tools.append("conversational_tool")
        
        # Resolve dependencies
        ordered_tools = self.registry.resolve_dependencies(selected_tools)
        
        # Create parallel groups if allowed
        parallel_groups = []
        if allow_parallel:
            parallel_groups = self._identify_parallel_groups(ordered_tools)
        
        # Estimate execution time and complexity
        estimated_time = self._estimate_execution_time(ordered_tools)
        estimated_complexity = contextual_request.estimated_complexity
        
        return ExecutionPlan(
            request_id=context.request_id,
            tools=ordered_tools,
            parallel_groups=parallel_groups,
            estimated_time=estimated_time,
            estimated_complexity=estimated_complexity,
            requires_user_input=contextual_request.requires_user_input
        )
    
    async def _execute_plan(self, plan: ExecutionPlan, context: ToolContext, verbose: bool = False) -> ToolResult:
        """Execute the execution plan."""
        self.logger.info(f"Executing plan with {len(plan.tools)} tools")
        
        results = []
        errors = []
        files_created = []
        files_modified = []
        total_execution_time = 0.0
        
        try:
            # Execute tools in order
            for tool_name in plan.tools:
                self.logger.debug(f"Executing tool: {tool_name}")
                
                # Execute tool
                result = await self.execute_tool(tool_name, context)
                results.append(result)
                
                # Track metrics
                total_execution_time += result.execution_time
                
                if result.success:
                    files_created.extend(result.files_created)
                    files_modified.extend(result.files_modified)
                else:
                    errors.append(f"{tool_name}: {result.error}")
                    
                    # Decide whether to continue on error
                    if self._should_stop_on_error(result, plan):
                        break
            
            # Determine overall success
            successful_results = [r for r in results if r.success]
            overall_success = len(successful_results) > 0 and len(errors) == 0
            
            # Combine results
            combined_data = {
                "tool_results": results,
                "successful_tools": len(successful_results),
                "total_tools": len(results),
                "execution_plan": {
                    "tools": plan.tools,
                    "estimated_time": plan.estimated_time,
                    "actual_time": total_execution_time
                }
            }
            
            # Create final result
            if overall_success:
                return ToolResult.success_result(
                    data=combined_data,
                    tool_name="tool_manager",
                    execution_time=total_execution_time,
                    files_created=files_created,
                    files_modified=files_modified,
                    output=self._format_execution_output(results)
                )
            else:
                return ToolResult.error_result(
                    error=f"Execution failed: {'; '.join(errors)}",
                    tool_name="tool_manager",
                    execution_time=total_execution_time
                )
        
        except Exception as e:
            self.logger.error(f"Plan execution failed: {e}", exc_info=True)
            return ToolResult.error_result(
                error=f"Plan execution error: {str(e)}",
                tool_name="tool_manager",
                execution_time=total_execution_time
            )
    
    def _identify_parallel_groups(self, tools: List[str]) -> List[List[str]]:
        """Identify tools that can run in parallel."""
        # For now, return empty list (sequential execution)
        # TODO: Implement dependency analysis for parallel execution
        return []
    
    def _estimate_execution_time(self, tools: List[str]) -> float:
        """Estimate total execution time for tools."""
        total_time = 0.0
        
        for tool_name in tools:
            tool_info = self.registry.get_tool_info(tool_name)
            if tool_info and tool_info.instance:
                # Use average execution time if available
                stats = tool_info.instance.get_usage_stats()
                avg_time = stats.get("average_execution_time", 1.0)
                total_time += avg_time
            else:
                # Default estimate
                total_time += 1.0
        
        return total_time
    
    def _can_tool_execute(self, tool: Tool, context: ToolContext, check_parameters: bool = True) -> bool:
        """Check if a tool can execute with the given context.

        Args:
            tool: Tool to check
            context: Tool context
            check_parameters: If True, strictly validate all parameters are present.
                              If False, only check if tool is generally available.
        """
        try:
            # For fallback tools, be more lenient
            if hasattr(tool, 'name') and tool.name in ['universal_fallback', 'conversational_tool']:
                return True

            # For AI provider tool, be lenient if no other tools are available
            if hasattr(tool, 'name') and tool.name == 'ai_provider':
                return True

            # Special validation for shell execution tools
            if hasattr(tool, 'name') and tool.name == 'serena_shell_execution':
                # For shell execution tools, we need to validate that there's actually a command to run
                if hasattr(tool, '_extract_command'):
                    try:
                        extracted_command = tool._extract_command(context)
                        if not extracted_command:
                            self.logger.debug(f"Shell execution tool cannot extract command from request: {context.user_request}")
                            return False
                        # Additional validation: check if the command looks valid
                        if hasattr(tool, '_looks_like_command') and not tool._looks_like_command(extracted_command):
                            self.logger.debug(f"Extracted command doesn't look like a valid command: {extracted_command}")
                            return False
                    except Exception as e:
                        self.logger.debug(f"Error validating shell command extraction: {e}")
                        return False

            # For natural language requests, be much more lenient with parameter validation
            # Only check parameters if explicitly required and we have a clear indication they're needed
            if check_parameters and hasattr(tool, 'required_context') and tool.required_context:
                # Check if this looks like a natural language request that might not have explicit parameters
                user_request = context.user_request or ""
                is_natural_language = len(user_request.split()) > 3 and not any(user_request.startswith(prefix) for prefix in ['/', '--', '-'])

                # For Claude Code tools, be extremely lenient
                if hasattr(tool, 'category') and tool.category == "claude_code":
                    # For Claude Code tools, don't block execution due to missing parameters
                    # We'll try to infer them during execution
                    return True
                
                # For Serena tools, also be very lenient
                if hasattr(tool, 'category') and tool.category == "serena":
                    # For Serena tools, don't block execution due to missing parameters
                    # We'll try to infer them during execution
                    return True
                
                # For shell execution tools, be extremely lenient
                if hasattr(tool, 'name') and any(name in tool.name.lower() for name in ['shell', 'bash', 'command', 'execute']):
                    # For shell execution tools, don't block execution due to missing parameters
                    # We'll try to infer them during execution
                    return True

                if is_natural_language:
                    # For natural language, be extremely lenient - we'll try to infer parameters during execution
                    # Only check for truly essential parameters that can't be inferred
                    essential_params = []  # Empty list - we'll try to infer all parameters
                    
                    # For other tools, try to infer all parameters
                    for required_key in tool.required_context:
                        # Check if the key exists as an attribute (legacy support)
                        if hasattr(context, required_key):
                            attr_value = getattr(context, required_key)
                            if attr_value is None:
                                # Try to infer the parameter
                                inferred_value = self._infer_parameter_from_natural_language(
                                    required_key, user_request, tool.name if hasattr(tool, 'name') else "unknown"
                                )
                                if inferred_value is not None:
                                    # Set the inferred value
                                    context.update_state(required_key, inferred_value)
                                elif required_key in essential_params:
                                    # Only fail if this is truly essential
                                    return False

                        # Enhanced validation: Check actual parameter values in shared_state
                        param_value = context.get_state(required_key)
                        if param_value is None:
                            # Try to infer the parameter
                            inferred_value = self._infer_parameter_from_natural_language(
                                required_key, user_request, tool.name if hasattr(tool, 'name') else "unknown"
                            )
                            if inferred_value is not None:
                                # Set the inferred value
                                context.update_state(required_key, inferred_value)
                            elif required_key in essential_params:
                                # Only fail if this is truly essential
                                return False
                        elif isinstance(param_value, str) and not param_value.strip():
                            # For empty string parameters, try to infer
                            inferred_value = self._infer_parameter_from_natural_language(
                                required_key, user_request, tool.name if hasattr(tool, 'name') else "unknown"
                            )
                            if inferred_value is not None:
                                # Set the inferred value
                                context.update_state(required_key, inferred_value)
                            elif required_key in essential_params:
                                # Only fail if this is truly essential
                                return False
                    
                    # For natural language, always try to execute the tool
                    return True
                else:
                    # For structured requests, be more lenient than before
                    for required_key in tool.required_context:
                        # Check if the key exists as an attribute (legacy support)
                        if hasattr(context, required_key):
                            attr_value = getattr(context, required_key)
                            if attr_value is None:
                                # Try to infer the parameter first
                                inferred_value = self._infer_parameter_from_natural_language(
                                    required_key, user_request, tool.name if hasattr(tool, 'name') else "unknown"
                                )
                                if inferred_value is not None:
                                    # Set the inferred value
                                    context.update_state(required_key, inferred_value)
                                # For tools that require specific context, be more strict
                                elif required_key in ['file_path', 'pattern', 'directory_path']:
                                    return False

                        # Enhanced validation: Check actual parameter values in shared_state
                        param_value = context.get_state(required_key)
                        if param_value is None:
                            # Try to infer the parameter first
                            inferred_value = self._infer_parameter_from_natural_language(
                                required_key, user_request, tool.name if hasattr(tool, 'name') else "unknown"
                            )
                            if inferred_value is not None:
                                # Set the inferred value
                                context.update_state(required_key, inferred_value)
                            # For tools that require specific parameters, be more strict
                            elif required_key in ['file_path', 'pattern', 'directory_path', 'content']:
                                return False
                        elif isinstance(param_value, str) and not param_value.strip():
                            # Try to infer the parameter first
                            inferred_value = self._infer_parameter_from_natural_language(
                                required_key, user_request, tool.name if hasattr(tool, 'name') else "unknown"
                            )
                            if inferred_value is not None:
                                # Set the inferred value
                                context.update_state(required_key, inferred_value)
                            # Empty string parameters are also invalid for critical tools
                            # Exception: content can be empty for write operations (creating empty files)
                            elif required_key in ['file_path', 'pattern', 'directory_path']:
                                return False
                            elif required_key == 'content' and hasattr(tool, 'name') and tool.name not in ['Write', 'write_file']:
                                return False

            # Check if tool has validate_context method
            if hasattr(tool, 'validate_context'):
                # We can't call the async method here, so we'll be conservative
                # and assume it might work if basic context is available
                pass

            return True
        except Exception as e:
            self.logger.debug(f"Error checking tool execution capability: {e}")
            return False
    
    def _should_stop_on_error(self, result: ToolResult, plan: ExecutionPlan) -> bool:
        """Determine if execution should stop on error."""
        # For now, continue on non-critical errors
        # TODO: Implement error severity analysis
        return False
    
    def _infer_parameter_from_natural_language(self, param_name: str, request: str, tool_name: str) -> Any:
        """
        Attempt to infer parameter values from natural language requests.
        This helps tools work better with conversational inputs.
        
        Args:
            param_name: The parameter name to infer
            request: The natural language request
            tool_name: The name of the tool being executed
            
        Returns:
            Inferred parameter value or None if no inference could be made
        """
        request_lower = request.lower()
        
        # Enhanced parameter patterns for different parameter types
        file_patterns = [
            # Explicit file references
            r'(?:file|path)(?:\s+named|\s+called|\s+at|\s+in|\s+is|\s+of|\s*:)?\s+["\']?([^"\'<>\n]+\.[a-zA-Z0-9]+)["\']?',
            # Action-based file references
            r'(?:open|read|write|edit|modify|update|create)\s+["\']?([^"\'<>\n]+\.[a-zA-Z0-9]+)["\']?',
            # Preposition-based file references
            r'(?:in|to|from|the)\s+["\']?([^"\'<>\n]+\.[a-zA-Z0-9]+)["\']?',
            # Quoted file paths
            r'["\']([^"\'<>\n]+\.[a-zA-Z0-9]+)["\']',
            # File paths with extensions
            r'\b([/\w\-\.]+\.[a-zA-Z0-9]{1,5})\b',
            # File paths with directories
            r'\b((?:\.{1,2})?/[/\w\-\.]+\.[a-zA-Z0-9]{1,5})\b',
            # File references with "the file"
            r'the\s+file\s+["\']?([^"\'<>\n]+)["\']?',
            # File references with "named"
            r'named\s+["\']?([^"\'<>\n]+\.[a-zA-Z0-9]+)["\']?'
        ]
        
        directory_patterns = [
            # Explicit directory references
            r'(?:directory|folder|dir)(?:\s+named|\s+called|\s+at|\s+in|\s+is|\s+of|\s*:)?\s+["\']?([^"\'<>\n]+/?)["\']?',
            # Action-based directory references
            r'(?:cd|navigate|browse|list|change\s+to)\s+["\']?([^"\'<>\n]+/?)["\']?',
            # Directory paths with slashes
            r'\b((?:\.{1,2})?/[/\w\-\.]+/)\b',
            # Quoted directory paths
            r'["\']([^"\'<>\n]+/)["\']',
            # Directory references with "the directory"
            r'the\s+(?:directory|folder|dir)\s+["\']?([^"\'<>\n]+)["\']?',
            # Directory references with "in"
            r'in\s+the\s+["\']?([^"\'<>\n]+/?)["\']?'
        ]
        
        pattern_patterns = [
            # Explicit pattern references
            r'(?:pattern|regex|expression|search for|find)(?:\s+is|\s+of|\s*:)?\s+["\']?([^"\'<>\n]{2,})["\']?',
            # Content-based pattern references
            r'(?:matching|matches|containing|contains)\s+["\']?([^"\'<>\n]{2,})["\']?',
            # Quoted patterns
            r'["\']([^"\'<>\n]{2,})["\']',
            # Pattern references with "the pattern"
            r'the\s+(?:pattern|regex|expression)\s+["\']?([^"\'<>\n]{2,})["\']?',
            # Pattern references with "for"
            r'for\s+["\']?([^"\'<>\n]{2,})["\']?',
            # Pattern references with "text"
            r'text\s+["\']?([^"\'<>\n]{2,})["\']?'
        ]
        
        content_patterns = [
            # Explicit content references
            r'(?:content|text|data)(?:\s+is|\s+of|\s+as|\s*:)?\s+["\']?([^"\']{5,})["\']?',
            # Content references with prepositions
            r'(?:with|containing|contains)\s+(?:content|text|data)(?:\s+is|\s+of|\s+as|\s*:)?\s+["\']?([^"\']{5,})["\']?',
            # Quoted content
            r'["\']([^"\']{5,})["\']',
            # Content references with "the content"
            r'the\s+(?:content|text|data)\s+["\']?([^"\']{5,})["\']?',
            # Content after "write" or "add"
            r'(?:write|add)\s+["\']?([^"\']{5,})["\']?'
        ]
        
        command_patterns = [
            # Explicit command references
            r'(?:command|run|execute)(?:\s+is|\s+of|\s*:)?\s+["\']?([^"\'<>\n]+)["\']?',
            # Command references with "the command"
            r'the\s+command\s+["\']?([^"\'<>\n]+)["\']?',
            # Quoted commands
            r'["\']([^"\'<>\n]+)["\']',
            # Commands after "run" or "execute"
            r'(?:run|execute)\s+["\']?([^"\'<>\n]+)["\']?',
            # Commands with "bash" or "shell"
            r'(?:bash|shell):\s*["\']?([^"\'<>\n]+)["\']?'
        ]
        
        # Parameter-specific inference with enhanced matching
        if param_name in ['file_path', 'path', 'file', 'source_file', 'target_file', 'filename']:
            # Try all file patterns
            for pattern in file_patterns:
                matches = re.findall(pattern, request)
                if matches:
                    # Return the first match that looks like a file path
                    for match in matches:
                        if '.' in match and not match.endswith('/'):
                            return match.strip()
            
            # If no match found, look for any word that might be a filename
            words = request.split()
            for word in words:
                if '.' in word and not word.endswith('/') and not word.startswith(('http://', 'https://')):
                    return word.strip()
        
        elif param_name in ['directory_path', 'dir', 'folder', 'directory']:
            # Try all directory patterns
            for pattern in directory_patterns:
                matches = re.findall(pattern, request)
                if matches:
                    return matches[0].strip()
            
            # If no match found, look for any word that might be a directory
            words = request.split()
            for word in words:
                if word.endswith('/') or word in ['.', '..', 'src', 'dist', 'build', 'public', 'app', 'test', 'docs']:
                    return word.strip()
        
        elif param_name in ['pattern', 'regex', 'search_pattern', 'query', 'search']:
            # Try all pattern patterns
            for pattern in pattern_patterns:
                matches = re.findall(pattern, request)
                if matches:
                    return matches[0].strip()
            
            # Look for words after search-related terms
            search_terms = re.findall(r'(?:search|find|look for|containing|matches|grep)\s+(\w+)', request_lower)
            if search_terms:
                return search_terms[0].strip()
        
        elif param_name in ['content', 'text', 'data']:
            # Try all content patterns
            for pattern in content_patterns:
                matches = re.findall(pattern, request)
                if matches:
                    return matches[0].strip()
            
            # Look for content after write-related terms
            write_terms = re.findall(r'(?:write|add|put|insert)\s+["\']?([^"\']{5,})["\']?', request_lower)
            if write_terms:
                return write_terms[0].strip()
        
        elif param_name in ['command', 'cmd', 'shell_command', 'bash_command']:
            # Try all command patterns
            for pattern in command_patterns:
                matches = re.findall(pattern, request)
                if matches:
                    return matches[0].strip()
            
            # Look for common command prefixes
            command_prefixes = [
                'npm', 'pip', 'python', 'node', 'git', 'make', 'docker',
                'curl', 'wget', 'ls', 'cd', 'mkdir', 'cp', 'mv', 'rm',
                'find', 'grep', 'cat', 'touch', 'echo', 'ps', 'df', 'free'
            ]
            
            words = request_lower.split()
            for i, word in enumerate(words):
                if word in command_prefixes and i < len(words) - 1:
                    # Extract the command and up to 5 arguments
                    end_idx = min(i + 6, len(words))
                    return ' '.join(words[i:end_idx])
        
        # Tool-specific parameter inference with enhanced matching
        if tool_name in ['file_search', 'FileSearch', 'search_files']:
            if param_name in ['filePattern', 'pattern', 'file_pattern']:
                # Look for file extensions or patterns
                ext_matches = re.findall(r'\.([a-zA-Z0-9]{1,5})\b', request_lower)
                if ext_matches:
                    return f"*.{ext_matches[0]}"
                
                # Look for specific file types mentioned
                file_types = {
                    'python': '*.py', 'javascript': '*.js', 'typescript': '*.ts',
                    'html': '*.html', 'css': '*.css', 'java': '*.java',
                    'c': '*.c', 'cpp': '*.cpp', 'csharp': '*.cs', 'c#': '*.cs',
                    'go': '*.go', 'rust': '*.rs', 'ruby': '*.rb',
                    'php': '*.php', 'swift': '*.swift', 'kotlin': '*.kt',
                    'markdown': '*.md', 'json': '*.json', 'xml': '*.xml',
                    'yaml': '*.yml', 'text': '*.txt', 'config': '*.config',
                    'dockerfile': 'Dockerfile*', 'makefile': 'Makefile*'
                }
                
                for file_type, pattern in file_types.items():
                    if file_type in request_lower:
                        return pattern
        
        elif tool_name in ['fulltext_search', 'FulltextSearch', 'search_text', 'grep']:
            if param_name in ['pattern', 'search_pattern', 'query']:
                # Extract potential search terms
                # Look for quoted text first
                quoted = re.findall(r'["\']([^"\']+)["\']', request)
                if quoted:
                    return quoted[0]
                
                # Look for words after search-related terms
                search_terms = re.findall(r'(?:search|find|look for|containing|matches|grep)\s+(\w+)', request_lower)
                if search_terms:
                    return search_terms[0]
                
                # Look for words after "for"
                for_terms = re.findall(r'for\s+["\']?([^"\'<>\n]{2,})["\']?', request_lower)
                if for_terms:
                    return for_terms[0].strip()
            
            elif param_name == 'path':
                # Look for directory specifications
                path_terms = re.findall(r'(?:in|from|within)\s+(?:directory|folder|dir)?\s*["\']?([^"\'<>\n]+)["\']?', request_lower)
                if path_terms:
                    return path_terms[0].strip()
                
                # Default to current directory if no path specified
                return '.'
        
        elif tool_name in ['serena_shell_execution', 'ShellExecutionTool', 'execute_shell_command']:
            if param_name == 'command':
                # Try to extract a command from the request
                command_prefixes = [
                    'npm', 'pip', 'python', 'node', 'git', 'make', 'docker',
                    'curl', 'wget', 'ls', 'cd', 'mkdir', 'cp', 'mv', 'rm',
                    'find', 'grep', 'cat', 'touch', 'echo', 'ps', 'df', 'free'
                ]
                
                words = request_lower.split()
                for i, word in enumerate(words):
                    if word in command_prefixes and i < len(words) - 1:
                        # Extract the command and up to 5 arguments
                        end_idx = min(i + 6, len(words))
                        return ' '.join(words[i:end_idx])
                
                # Look for commands after specific keywords
                command_patterns = [
                    r'(?:run|execute)\s+(.+)',
                    r'\$\s*(.+)',
                    r'shell:\s*(.+)',
                    r'bash:\s*(.+)',
                    r'command:\s*(.+)'
                ]
                
                for pattern in command_patterns:
                    match = re.search(pattern, request, re.IGNORECASE)
                    if match:
                        return match.group(1).strip()
        
        # Default parameter inference based on common patterns
        return None

    def _format_execution_output(self, results: List[ToolResult]) -> str:
        """Format execution results for display."""
        output_parts = []
        
        for result in results:
            if result.success and result.output:
                output_parts.append(f"**{result.tool_name}:**\n{result.output}")
        
        return "\n\n".join(output_parts) if output_parts else None
    
    def _record_execution(self, plan: ExecutionPlan, result: ToolResult) -> None:
        """Record execution for analytics."""
        self._total_executions += 1
        
        if result.success:
            self._successful_executions += 1
        else:
            self._failed_executions += 1
        
        self._total_execution_time += result.execution_time
        
        # Add to history
        execution_record = {
            "timestamp": datetime.now().isoformat(),
            "request_id": plan.request_id,
            "tools_used": plan.tools,
            "success": result.success,
            "execution_time": result.execution_time,
            "estimated_time": plan.estimated_time,
            "tool_count": len(plan.tools)
        }
        
        self._execution_history.append(execution_record)
        
        # Maintain history limit
        if len(self._execution_history) > self._max_history:
            self._execution_history.pop(0)
    
    async def _process_request_coordinated(self,
                                         contextual_request: ContextualRequest,
                                         context: ToolContext,
                                         max_tools: int,
                                         coordination_config: Optional[CoordinationConfig],
                                         verbose: bool = False) -> ToolResult:
        """Process request using coordinated execution."""
        try:
            # Import console for verbose output
            from rich.console import Console
            console = Console()
            
            if verbose:
                console.print("[dim]🎯 Starting coordinated tool execution...[/dim]")
            
            # Find candidate tools
            if verbose:
                console.print(f"[dim]🔍 Finding candidate tools (max {max_tools})...[/dim]")
            candidates = self.registry.find_tools_for_request(
                contextual_request, 
                context, 
                max_tools * 2  # Get more candidates for better coordination
            )
            
            if verbose:
                console.print(f"[dim]   Found {len(candidates)} candidate tools[/dim]")
            
            # Select best tools with improved threshold logic
            selected_tools = []
            if verbose:
                console.print("[dim]⚙️ Selecting best tools for coordination...[/dim]")
            for tool_name, confidence in candidates[:max_tools]:
                if confidence > 0.05:  # Lowered minimum confidence threshold
                    # Check if tool can actually execute with current context
                    tool = self.registry.get_tool(tool_name)
                    if tool and self._can_tool_execute(tool, context, check_parameters=False):
                        selected_tools.append(tool_name)
                        if verbose:
                            console.print(f"[dim]   ✓ {tool_name} (confidence: {confidence:.2f})[/dim]")
                    else:
                        if verbose:
                            console.print(f"[dim]   ✗ {tool_name} (failed validation)[/dim]")
                        self.logger.debug(f"Skipping tool {tool_name} due to context validation in coordination")
            
            # If still no tools found, be more permissive
            if not selected_tools and candidates:
                # Try to find any tool that can execute, even with low confidence
                for tool_name, confidence in candidates:
                    tool = self.registry.get_tool(tool_name)
                    if tool and self._can_tool_execute(tool, context, check_parameters=False):
                        selected_tools.append(tool_name)
                        self.logger.warning(f"Using low-confidence tool {tool_name} with confidence {confidence:.3f}")
                        break
            
            # CRITICAL: Ensure we always have at least one tool available for coordinated execution
            if not selected_tools:
                # Try to get the universal fallback tool
                fallback_tool = self.registry.get_tool("universal_fallback")
                if fallback_tool:
                    selected_tools.append("universal_fallback")
                    self.logger.info("Using universal fallback tool for coordinated execution")
                else:
                    # If fallback tool not available, use any tool with lowest confidence
                    if candidates:
                        selected_tools.append(candidates[0][0])
                        self.logger.warning(f"Using low-confidence tool {candidates[0][0]} as coordinated fallback")
                    else:
                        # This should never happen, but if it does, we need to handle it
                        self.logger.error("No tools available for coordinated execution - this indicates a serious system issue")
                        # Try to register the fallback tool dynamically
                        try:
                            from ..enhanced.universal_fallback_tool import UniversalFallbackTool
                            self.registry.register_tool(UniversalFallbackTool)
                            selected_tools.append("universal_fallback")
                            self.logger.info("Dynamically registered universal fallback tool for coordination")
                        except Exception as e:
                            self.logger.error(f"Failed to register fallback tool for coordination: {e}")
                            return ToolResult.error_result(
                                error="No suitable tools found for coordinated request and fallback registration failed",
                                tool_name="tool_manager"
                            )
            
            # Create coordination plan
            coordination_plan = await self.coordinator.create_coordination_plan(
                selected_tools,
                context,
                coordination_config
            )
            
            # Execute coordinated plan
            coordination_result = await self.coordinator.execute_coordinated_plan(
                coordination_plan,
                context
            )
            
            # Convert coordination result to tool result
            if coordination_result.success:
                # Combine all successful tool results
                combined_data = {
                    "coordination_result": coordination_result,
                    "tool_results": coordination_result.tool_results,
                    "execution_order": coordination_result.execution_order,
                    "successful_tools": coordination_result.successful_tools,
                    "parallel_efficiency": coordination_result.parallel_efficiency
                }
                
                return ToolResult.success_result(
                    data=combined_data,
                    tool_name="tool_manager_coordinated",
                    execution_time=coordination_result.total_execution_time,
                    output=self._format_coordination_output(coordination_result)
                )
            else:
                return ToolResult.error_result(
                    error=f"Coordinated execution failed: {'; '.join(coordination_result.errors)}",
                    tool_name="tool_manager_coordinated",
                    execution_time=coordination_result.total_execution_time
                )
        
        except Exception as e:
            self.logger.error(f"Coordinated request processing failed: {e}")
            return ToolResult.error_result(
                error=f"Coordinated processing error: {str(e)}",
                tool_name="tool_manager_coordinated"
            )
    
    def _format_coordination_output(self, coordination_result) -> str:
        """Format coordination results for display - focus on user-facing content."""
        # Extract the actual user response from tool results
        user_response = self._extract_user_response(coordination_result.tool_results)
        if user_response:
            return user_response
        
        # Fallback to simple tool outputs if no clear user response
        output_parts = []
        for tool_name in coordination_result.execution_order:
            result = coordination_result.tool_results.get(tool_name)
            if result and result.success and result.output:
                output_parts.append(result.output)
        
        return "\n\n".join(output_parts) if output_parts else "Task completed successfully."
    
    def _extract_user_response(self, tool_results: dict) -> str:
        """Extract clean user-facing response from tool results."""
        for tool_name, tool_result in tool_results.items():
            if not tool_result or not tool_result.success:
                continue
            
            # Check for conversational response in data
            if hasattr(tool_result, 'data') and isinstance(tool_result.data, dict):
                data = tool_result.data
                if 'response' in data and isinstance(data['response'], str):
                    return data['response']
                elif 'message' in data and isinstance(data['message'], str):
                    return data['message']
            
            # Check for direct output
            if hasattr(tool_result, 'output') and tool_result.output:
                output = str(tool_result.output).strip()
                # Avoid generic or technical outputs
                if output and not any(phrase in output.lower() for phrase in [
                    'coordination summary', 'tools executed', 'execution order', 
                    'parallel efficiency', 'total time', '→'
                ]):
                    return output
        
        return None
    
    def get_coordination_stats(self) -> Optional[Dict[str, Any]]:
        """Get coordination statistics."""
        if self.coordinator:
            return self.coordinator.get_coordination_stats()
        return None