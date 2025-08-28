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
            "codexa.tools.system"
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
            # Create execution context if not provided
            if context is None:
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
            contextual_request = self.request_analyzer.analyze_request(request)
            
            # Check if coordination is enabled and beneficial
            use_coordination = (enable_coordination and 
                              self.coordinator is not None and
                              max_tools > 1)
            
            if use_coordination:
                # Use coordinated execution
                return await self._process_request_coordinated(
                    contextual_request,
                    context,
                    max_tools,
                    coordination_config
                )
            else:
                # Use legacy execution plan
                plan = await self._create_execution_plan(
                    contextual_request, 
                    context, 
                    max_tools,
                    allow_parallel
                )
                
                if not plan.tools:
                    return ToolResult.error_result(
                        error="No suitable tools found for request",
                        tool_name="tool_manager"
                    )
                
                # Execute plan
                result = await self._execute_plan(plan, context)
                
                # Update context with results
                context.add_result("final_result", result)
                self.context_manager.update_context(context)
                
                # Record execution
                self._record_execution(plan, result)
                
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
                                   allow_parallel: bool) -> ExecutionPlan:
        """Create execution plan for request."""
        # Find candidate tools
        candidates = self.registry.find_tools_for_request(
            contextual_request, 
            context, 
            max_tools * 2  # Get more candidates for better selection
        )
        
        # Select best tools
        selected_tools = []
        for tool_name, confidence in candidates[:max_tools]:
            if confidence > 0.1:  # Minimum confidence threshold
                selected_tools.append(tool_name)
        
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
    
    async def _execute_plan(self, plan: ExecutionPlan, context: ToolContext) -> ToolResult:
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
    
    def _should_stop_on_error(self, result: ToolResult, plan: ExecutionPlan) -> bool:
        """Determine if execution should stop on error."""
        # For now, continue on non-critical errors
        # TODO: Implement error severity analysis
        return False
    
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
                                         coordination_config: Optional[CoordinationConfig]) -> ToolResult:
        """Process request using coordinated execution."""
        try:
            # Find candidate tools
            candidates = self.registry.find_tools_for_request(
                contextual_request, 
                context, 
                max_tools * 2  # Get more candidates for better coordination
            )
            
            # Select best tools
            selected_tools = []
            for tool_name, confidence in candidates[:max_tools]:
                if confidence > 0.1:  # Minimum confidence threshold
                    selected_tools.append(tool_name)
            
            if not selected_tools:
                return ToolResult.error_result(
                    error="No suitable tools found for coordinated request",
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
        """Format coordination results for display."""
        output_parts = []
        
        # Add execution summary
        output_parts.append(f"**Coordination Summary:**")
        output_parts.append(f"- Tools executed: {len(coordination_result.successful_tools)}/{len(coordination_result.tool_results)}")
        output_parts.append(f"- Execution order: {' → '.join(coordination_result.execution_order)}")
        output_parts.append(f"- Parallel efficiency: {coordination_result.parallel_efficiency:.1%}")
        output_parts.append(f"- Total time: {coordination_result.total_execution_time:.3f}s")
        
        # Add tool outputs
        for tool_name in coordination_result.execution_order:
            result = coordination_result.tool_results.get(tool_name)
            if result and result.success and result.output:
                output_parts.append(f"**{tool_name}:**\n{result.output}")
        
        return "\n\n".join(output_parts) if output_parts else None
    
    def get_coordination_stats(self) -> Optional[Dict[str, Any]]:
        """Get coordination statistics."""
        if self.coordinator:
            return self.coordinator.get_coordination_stats()
        return None