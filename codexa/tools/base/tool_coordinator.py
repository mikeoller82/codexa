"""
Tool Coordination System for Codexa.

Manages tool dependencies, execution planning, and coordination.
"""

import asyncio
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging
from collections import defaultdict, deque

from .tool_interface import Tool, ToolResult, ToolContext, ToolStatus, DependencyType, ToolDependency, CoordinationConfig
from .tool_registry import ToolRegistry


@dataclass
class CoordinationPlan:
    """Plan for coordinated tool execution."""
    
    request_id: str
    tools: List[str]  # All tools to execute
    execution_groups: List[List[str]]  # Sequential groups of parallel tools
    dependencies_map: Dict[str, List[str]]  # tool -> dependencies
    estimated_time: float
    coordination_config: CoordinationConfig
    
    def get_total_tools(self) -> int:
        """Get total number of tools in plan."""
        return len(self.tools)
    
    def get_parallel_efficiency(self) -> float:
        """Calculate parallel execution efficiency."""
        total_tools = self.get_total_tools()
        if total_tools == 0:
            return 0.0
        
        parallel_tools = sum(len(group) for group in self.execution_groups if len(group) > 1)
        return parallel_tools / total_tools
    
    def get_dependency_depth(self) -> int:
        """Get maximum dependency depth."""
        return len(self.execution_groups)


@dataclass
class CoordinationResult:
    """Result of coordinated tool execution."""
    
    success: bool
    tool_results: Dict[str, ToolResult]
    execution_order: List[str]
    total_execution_time: float
    parallel_efficiency: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @property
    def successful_tools(self) -> List[str]:
        """Get list of tools that executed successfully."""
        return [name for name, result in self.tool_results.items() if result.success]
    
    @property
    def failed_tools(self) -> List[str]:
        """Get list of tools that failed."""
        return [name for name, result in self.tool_results.items() if not result.success]


class ToolCoordinator:
    """
    Manages tool coordination, dependency resolution, and execution planning.
    
    Features:
    - Automatic dependency resolution
    - Parallel execution optimization
    - Conflict detection and resolution
    - Result coordination and sharing
    - Performance optimization
    """
    
    def __init__(self, registry: ToolRegistry):
        """Initialize tool coordinator."""
        self.logger = logging.getLogger("codexa.tools.coordinator")
        self.registry = registry
        
        # Coordination state
        self._coordination_cache: Dict[str, CoordinationPlan] = {}
        self._result_cache: Dict[str, ToolResult] = {}
        
        # Performance tracking
        self._coordination_count = 0
        self._successful_coordinations = 0
        self._total_coordination_time = 0.0
        
        self.logger.info("Tool coordinator initialized")
    
    async def create_coordination_plan(self,
                                     tools: List[str],
                                     context: ToolContext,
                                     coordination_config: Optional[CoordinationConfig] = None) -> CoordinationPlan:
        """
        Create coordination plan for tool execution.
        
        Args:
            tools: List of tool names to coordinate
            context: Execution context
            coordination_config: Optional coordination configuration
            
        Returns:
            Coordination plan
        """
        start_time = datetime.now()
        
        try:
            # Use default config if none provided
            if coordination_config is None:
                coordination_config = CoordinationConfig()
            
            self.logger.info(f"Creating coordination plan for {len(tools)} tools")
            
            # Get tool information
            available_tools = self._get_available_tools_info()
            
            # Resolve dependencies
            resolved_tools = await self._resolve_dependencies(tools, available_tools, coordination_config)
            
            # Check for conflicts
            conflicts = self._detect_conflicts(resolved_tools, available_tools)
            if conflicts:
                raise ValueError(f"Tool conflicts detected: {conflicts}")
            
            # Create execution groups (topological sort with parallelization)
            execution_groups = self._create_execution_groups(resolved_tools, available_tools, coordination_config)
            
            # Build dependencies map
            dependencies_map = self._build_dependencies_map(resolved_tools, available_tools)
            
            # Estimate execution time
            estimated_time = self._estimate_coordination_time(resolved_tools, available_tools, execution_groups)
            
            plan = CoordinationPlan(
                request_id=context.request_id,
                tools=resolved_tools,
                execution_groups=execution_groups,
                dependencies_map=dependencies_map,
                estimated_time=estimated_time,
                coordination_config=coordination_config
            )
            
            # Cache the plan
            cache_key = f"{context.request_id}_{hash(tuple(tools))}"
            self._coordination_cache[cache_key] = plan
            
            coordination_time = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"Coordination plan created in {coordination_time:.3f}s: "
                           f"{len(resolved_tools)} tools, {len(execution_groups)} groups, "
                           f"{plan.get_parallel_efficiency():.1%} parallel efficiency")
            
            return plan
            
        except Exception as e:
            self.logger.error(f"Failed to create coordination plan: {e}")
            raise
    
    async def execute_coordinated_plan(self,
                                     plan: CoordinationPlan,
                                     context: ToolContext) -> CoordinationResult:
        """
        Execute a coordination plan.
        
        Args:
            plan: Coordination plan to execute
            context: Execution context
            
        Returns:
            Coordination result
        """
        start_time = datetime.now()
        self._coordination_count += 1
        
        try:
            self.logger.info(f"Executing coordination plan: {plan.get_total_tools()} tools, "
                           f"{len(plan.execution_groups)} groups")
            
            tool_results: Dict[str, ToolResult] = {}
            execution_order: List[str] = []
            errors: List[str] = []
            warnings: List[str] = []
            
            # Execute tools in groups
            for group_index, tool_group in enumerate(plan.execution_groups):
                self.logger.debug(f"Executing group {group_index + 1}/{len(plan.execution_groups)}: {tool_group}")
                
                # Prepare tools for coordination
                for tool_name in tool_group:
                    tool = self.registry.get_tool(tool_name)
                    if tool:
                        try:
                            await tool.prepare_for_coordination(context)
                        except Exception as e:
                            warnings.append(f"Tool preparation warning for {tool_name}: {e}")
                
                # Execute group (parallel or sequential based on config)
                if len(tool_group) > 1 and plan.coordination_config.prefer_parallel:
                    # Parallel execution
                    group_results = await self._execute_parallel_group(tool_group, context, plan)
                else:
                    # Sequential execution
                    group_results = await self._execute_sequential_group(tool_group, context, plan)
                
                # Process group results
                for tool_name, result in group_results.items():
                    tool_results[tool_name] = result
                    execution_order.append(tool_name)
                    
                    if not result.success:
                        error_msg = f"Tool {tool_name} failed: {result.error}"
                        errors.append(error_msg)
                        
                        # Check if we should stop on error
                        if not plan.coordination_config.continue_on_optional_failure:
                            break
                    else:
                        # Coordinate with dependent tools
                        await self._coordinate_with_dependents(tool_name, result, tool_group, context)
                
                # Stop if critical errors occurred
                if errors and not plan.coordination_config.continue_on_optional_failure:
                    break
            
            # Calculate results
            total_execution_time = (datetime.now() - start_time).total_seconds()
            parallel_efficiency = plan.get_parallel_efficiency()
            success = len(errors) == 0
            
            if success:
                self._successful_coordinations += 1
            
            self._total_coordination_time += total_execution_time
            
            result = CoordinationResult(
                success=success,
                tool_results=tool_results,
                execution_order=execution_order,
                total_execution_time=total_execution_time,
                parallel_efficiency=parallel_efficiency,
                errors=errors,
                warnings=warnings
            )
            
            self.logger.info(f"Coordination completed in {total_execution_time:.3f}s: "
                           f"{'SUCCESS' if success else 'FAILURE'}, "
                           f"{len(result.successful_tools)}/{len(plan.tools)} tools successful")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Coordination execution failed: {e}")
            return CoordinationResult(
                success=False,
                tool_results={},
                execution_order=[],
                total_execution_time=(datetime.now() - start_time).total_seconds(),
                parallel_efficiency=0.0,
                errors=[f"Coordination execution error: {str(e)}"]
            )
    
    def _get_available_tools_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all available tools."""
        tools_info = {}
        
        for tool_name, tool_info in self.registry.get_all_tools().items():
            # Get tool instance to access properties
            tool = self.registry.get_tool(tool_name)
            if tool:
                tools_info[tool_name] = {
                    'name': tool.name,
                    'version': tool.version,
                    'category': tool.category,
                    'capabilities': tool.capabilities,
                    'provides_capabilities': tool.provides_capabilities,
                    'dependencies': tool.dependencies,
                    'legacy_dependencies': tool.legacy_dependencies,
                    'coordination_config': tool.coordination_config,
                    'priority': tool.priority,
                    'can_parallel': True  # Assume true unless conflicts detected
                }
        
        return tools_info
    
    async def _resolve_dependencies(self,
                                  tools: List[str],
                                  available_tools: Dict[str, Dict[str, Any]],
                                  config: CoordinationConfig) -> List[str]:
        """Resolve tool dependencies and return ordered list."""
        resolved = set()
        result = []
        visiting = set()
        
        def visit(tool_name: str) -> None:
            """Visit tool and resolve dependencies recursively."""
            if tool_name in visiting:
                raise ValueError(f"Circular dependency detected involving: {tool_name}")
            
            if tool_name in resolved:
                return
            
            if tool_name not in available_tools:
                if config.fail_on_missing_dependencies:
                    raise ValueError(f"Tool not available: {tool_name}")
                else:
                    self.logger.warning(f"Tool not available: {tool_name}")
                    return
            
            visiting.add(tool_name)
            tool_info = available_tools[tool_name]
            
            # Visit dependencies first
            for dep in tool_info['dependencies']:
                if dep.dependency_type == DependencyType.REQUIRED:
                    # Try to find satisfying tool
                    satisfying_tool = None
                    
                    # Check direct name match
                    if dep.name in available_tools:
                        if dep.is_satisfied_by(available_tools[dep.name]):
                            satisfying_tool = dep.name
                    
                    # Check capability match
                    if not satisfying_tool:
                        for candidate_name, candidate_info in available_tools.items():
                            if dep.name in candidate_info.get('capabilities', set()):
                                if dep.is_satisfied_by(candidate_info):
                                    satisfying_tool = candidate_name
                                    break
                    
                    # Check fallbacks
                    if not satisfying_tool and dep.fallback_tools:
                        for fallback in dep.fallback_tools:
                            if fallback in available_tools:
                                if dep.is_satisfied_by(available_tools[fallback]):
                                    satisfying_tool = fallback
                                    break
                    
                    if satisfying_tool:
                        visit(satisfying_tool)
                    elif config.fail_on_missing_dependencies:
                        raise ValueError(f"Required dependency not available: {dep.name} for {tool_name}")
            
            # Visit legacy dependencies
            for dep_name in tool_info['legacy_dependencies']:
                if dep_name in available_tools:
                    visit(dep_name)
                elif config.fail_on_missing_dependencies:
                    raise ValueError(f"Legacy dependency not available: {dep_name} for {tool_name}")
            
            visiting.remove(tool_name)
            resolved.add(tool_name)
            result.append(tool_name)
        
        # Visit all requested tools
        for tool_name in tools:
            visit(tool_name)
        
        return result
    
    def _detect_conflicts(self,
                         tools: List[str],
                         available_tools: Dict[str, Dict[str, Any]]) -> List[str]:
        """Detect conflicts between tools."""
        conflicts = []
        
        for i, tool_name in enumerate(tools):
            tool_info = available_tools.get(tool_name, {})
            
            for j, other_tool_name in enumerate(tools):
                if i >= j:  # Skip self and already checked pairs
                    continue
                
                other_tool_info = available_tools.get(other_tool_name, {})
                
                # Check for explicit conflicts
                for dep in tool_info.get('dependencies', []):
                    if dep.dependency_type == DependencyType.CONFLICT:
                        if (dep.name == other_tool_name or 
                            dep.name in other_tool_info.get('provides_capabilities', set())):
                            conflicts.append(f"{tool_name} conflicts with {other_tool_name}")
        
        return conflicts
    
    def _create_execution_groups(self,
                               tools: List[str],
                               available_tools: Dict[str, Dict[str, Any]],
                               config: CoordinationConfig) -> List[List[str]]:
        """Create execution groups for parallel optimization."""
        # Build dependency graph
        dependencies = defaultdict(set)
        dependents = defaultdict(set)
        
        for tool_name in tools:
            tool_info = available_tools.get(tool_name, {})
            
            # Process new dependencies
            for dep in tool_info.get('dependencies', []):
                if dep.dependency_type == DependencyType.REQUIRED:
                    # Find satisfying tool in our list
                    for candidate in tools:
                        candidate_info = available_tools.get(candidate, {})
                        if (candidate == dep.name or 
                            dep.name in candidate_info.get('capabilities', set()) or
                            dep.name in candidate_info.get('provides_capabilities', set())):
                            dependencies[tool_name].add(candidate)
                            dependents[candidate].add(tool_name)
                            break
            
            # Process legacy dependencies
            for dep_name in tool_info.get('legacy_dependencies', set()):
                if dep_name in tools:
                    dependencies[tool_name].add(dep_name)
                    dependents[dep_name].add(tool_name)
        
        # Topological sort with parallelization
        groups = []
        remaining = set(tools)
        
        while remaining:
            # Find tools with no remaining dependencies
            available_tools_in_round = []
            for tool_name in remaining:
                if not dependencies[tool_name] or dependencies[tool_name].isdisjoint(remaining):
                    available_tools_in_round.append(tool_name)
            
            if not available_tools_in_round:
                # Circular dependency - break it
                self.logger.warning(f"Circular dependency detected, breaking with: {next(iter(remaining))}")
                available_tools_in_round = [next(iter(remaining))]
            
            # Check parallel compatibility within group
            if config.prefer_parallel and len(available_tools_in_round) > 1:
                parallel_groups = self._optimize_parallel_groups(available_tools_in_round, available_tools)
                groups.extend(parallel_groups)
            else:
                # Add tools individually
                groups.extend([[tool] for tool in available_tools_in_round])
            
            # Remove processed tools
            for tool_name in available_tools_in_round:
                remaining.remove(tool_name)
        
        return groups
    
    def _optimize_parallel_groups(self,
                                tools: List[str],
                                available_tools: Dict[str, Dict[str, Any]]) -> List[List[str]]:
        """Optimize tools for parallel execution."""
        # Simple implementation - could be enhanced with graph algorithms
        parallel_compatible = []
        sequential_only = []
        
        for tool_name in tools:
            tool_info = available_tools.get(tool_name, {})
            coord_config = tool_info.get('coordination_config', CoordinationConfig())
            
            if coord_config.prefer_parallel:
                parallel_compatible.append(tool_name)
            else:
                sequential_only.append(tool_name)
        
        groups = []
        if parallel_compatible:
            groups.append(parallel_compatible)
        
        for tool_name in sequential_only:
            groups.append([tool_name])
        
        return groups
    
    def _build_dependencies_map(self,
                              tools: List[str],
                              available_tools: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
        """Build dependencies mapping for coordination."""
        dependencies_map = {}
        
        for tool_name in tools:
            tool_info = available_tools.get(tool_name, {})
            deps = []
            
            # New dependencies
            for dep in tool_info.get('dependencies', []):
                if dep.dependency_type in [DependencyType.REQUIRED, DependencyType.OPTIONAL]:
                    # Find satisfying tool
                    for candidate in tools:
                        candidate_info = available_tools.get(candidate, {})
                        if (candidate == dep.name or 
                            dep.name in candidate_info.get('capabilities', set()) or
                            dep.name in candidate_info.get('provides_capabilities', set())):
                            deps.append(candidate)
                            break
            
            # Legacy dependencies
            for dep_name in tool_info.get('legacy_dependencies', set()):
                if dep_name in tools:
                    deps.append(dep_name)
            
            dependencies_map[tool_name] = deps
        
        return dependencies_map
    
    def _estimate_coordination_time(self,
                                  tools: List[str],
                                  available_tools: Dict[str, Dict[str, Any]],
                                  execution_groups: List[List[str]]) -> float:
        """Estimate total coordination time."""
        total_time = 0.0
        
        for group in execution_groups:
            group_time = 0.0
            
            if len(group) == 1:
                # Sequential execution
                tool_name = group[0]
                tool_info = available_tools.get(tool_name, {})
                # Use default 1.0s if no historical data available
                group_time = 1.0
            else:
                # Parallel execution - use maximum time
                max_time = 0.0
                for tool_name in group:
                    tool_info = available_tools.get(tool_name, {})
                    tool_time = 1.0  # Default estimate
                    max_time = max(max_time, tool_time)
                group_time = max_time
            
            total_time += group_time
        
        return total_time
    
    async def _execute_parallel_group(self,
                                    tool_group: List[str],
                                    context: ToolContext,
                                    plan: CoordinationPlan) -> Dict[str, ToolResult]:
        """Execute a group of tools in parallel."""
        tasks = {}
        
        # Create tasks for each tool
        for tool_name in tool_group:
            tool = self.registry.get_tool(tool_name)
            if tool:
                task = asyncio.create_task(tool.safe_execute(context))
                tasks[tool_name] = task
        
        # Wait for completion
        results = {}
        for tool_name, task in tasks.items():
            try:
                results[tool_name] = await task
            except Exception as e:
                self.logger.error(f"Parallel execution failed for {tool_name}: {e}")
                results[tool_name] = ToolResult.error_result(
                    error=f"Parallel execution error: {str(e)}",
                    tool_name=tool_name
                )
        
        return results
    
    async def _execute_sequential_group(self,
                                      tool_group: List[str],
                                      context: ToolContext,
                                      plan: CoordinationPlan) -> Dict[str, ToolResult]:
        """Execute a group of tools sequentially."""
        results = {}
        
        for tool_name in tool_group:
            tool = self.registry.get_tool(tool_name)
            if tool:
                try:
                    result = await tool.safe_execute(context)
                    results[tool_name] = result
                    
                    # Stop on failure if configured
                    if not result.success and not plan.coordination_config.continue_on_optional_failure:
                        break
                        
                except Exception as e:
                    self.logger.error(f"Sequential execution failed for {tool_name}: {e}")
                    results[tool_name] = ToolResult.error_result(
                        error=f"Sequential execution error: {str(e)}",
                        tool_name=tool_name
                    )
        
        return results
    
    async def _coordinate_with_dependents(self,
                                        tool_name: str,
                                        result: ToolResult,
                                        current_group: List[str],
                                        context: ToolContext) -> None:
        """Coordinate result with dependent tools."""
        # Find tools that depend on this tool in current group
        for dependent_tool_name in current_group:
            if dependent_tool_name == tool_name:
                continue
                
            dependent_tool = self.registry.get_tool(dependent_tool_name)
            if dependent_tool:
                try:
                    await dependent_tool.coordinate_with_dependency(result, context)
                except Exception as e:
                    self.logger.warning(f"Coordination failed between {tool_name} and {dependent_tool_name}: {e}")
    
    def get_coordination_stats(self) -> Dict[str, Any]:
        """Get coordination statistics."""
        success_rate = 0.0
        if self._coordination_count > 0:
            success_rate = self._successful_coordinations / self._coordination_count
        
        avg_coordination_time = 0.0
        if self._successful_coordinations > 0:
            avg_coordination_time = self._total_coordination_time / self._successful_coordinations
        
        return {
            "total_coordinations": self._coordination_count,
            "successful_coordinations": self._successful_coordinations,
            "success_rate": success_rate,
            "average_coordination_time": avg_coordination_time,
            "cached_plans": len(self._coordination_cache),
            "cached_results": len(self._result_cache)
        }
    
    def clear_caches(self) -> None:
        """Clear coordination caches."""
        self._coordination_cache.clear()
        self._result_cache.clear()
        self.logger.info("Coordination caches cleared")