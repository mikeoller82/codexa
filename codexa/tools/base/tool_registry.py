"""
Tool registry for Codexa tool system.
"""

import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import Dict, List, Set, Optional, Type, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging

from .tool_interface import Tool, ToolPriority, ToolContext, ContextualRequest


@dataclass
class ToolInfo:
    """Information about a registered tool."""
    
    name: str
    description: str
    category: str
    tool_class: Type[Tool]
    capabilities: Set[str]
    dependencies: Set[str]
    priority: ToolPriority
    is_loaded: bool = False
    instance: Optional[Tool] = None
    load_count: int = 0
    last_used: Optional[datetime] = None
    error_count: int = 0
    
    def can_handle(self, request: ContextualRequest, context: ToolContext) -> float:
        """Check if tool can handle the request."""
        if not self.instance:
            return 0.0
        return self.instance.can_handle_request(request.processed_request, context)


class ToolRegistry:
    """
    Registry for managing and discovering Codexa tools.
    
    Handles tool discovery, registration, dependency resolution,
    and intelligent tool selection based on requests.
    """
    
    def __init__(self):
        """Initialize tool registry."""
        self.logger = logging.getLogger("codexa.tools.registry")
        self._tools: Dict[str, ToolInfo] = {}
        self._categories: Dict[str, Set[str]] = {}
        self._capabilities: Dict[str, Set[str]] = {}
        self._loaded_modules: Set[str] = set()
    
    def register_tool(self, tool_class: Type[Tool]) -> bool:
        """
        Register a tool class.
        
        Args:
            tool_class: Tool class to register
            
        Returns:
            True if registration successful
        """
        try:
            # Create temporary instance to get metadata
            temp_instance = tool_class()
            
            # Validate tool
            if not self._validate_tool(temp_instance):
                return False
            
            # Handle name conflicts by preferring higher priority tools
            if temp_instance.name in self._tools:
                existing_tool = self._tools[temp_instance.name]
                if temp_instance.priority.value >= existing_tool.priority.value:
                    self.logger.info(f"Tool name conflict resolved: {temp_instance.name} (replacing with higher/equal priority)")
                else:
                    self.logger.warning(f"Tool name conflict: {temp_instance.name} (keeping higher priority tool)")
                    return False
            
            # Create tool info
            tool_info = ToolInfo(
                name=temp_instance.name,
                description=temp_instance.description,
                category=temp_instance.category,
                tool_class=tool_class,
                capabilities=temp_instance.capabilities,
                dependencies=temp_instance.dependencies,
                priority=temp_instance.priority
            )
            
            # Register tool
            self._tools[temp_instance.name] = tool_info
            
            # Update category mapping
            category = temp_instance.category
            if category not in self._categories:
                self._categories[category] = set()
            self._categories[category].add(temp_instance.name)
            
            # Update capability mapping
            for capability in temp_instance.capabilities:
                if capability not in self._capabilities:
                    self._capabilities[capability] = set()
                self._capabilities[capability].add(temp_instance.name)
            
            self.logger.info(f"Registered tool: {temp_instance.name} ({category})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register tool {tool_class}: {e}")
            return False
    
    def discover_tools(self, package_path: str = "codexa.tools") -> int:
        """
        Discover and register tools from package.
        
        Args:
            package_path: Python package path to search
            
        Returns:
            Number of tools discovered
        """
        discovered_count = 0
        
        try:
            # Import the tools package
            package = importlib.import_module(package_path)
            
            # Walk through all modules in package
            for importer, modname, ispkg in pkgutil.walk_packages(
                package.__path__, 
                package.__name__ + "."
            ):
                if modname in self._loaded_modules:
                    continue
                
                try:
                    # Import module
                    module = importlib.import_module(modname)
                    self._loaded_modules.add(modname)
                    
                    # Find tool classes
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, Tool) and 
                            obj != Tool and
                            not inspect.isabstract(obj)):
                            
                            if self.register_tool(obj):
                                discovered_count += 1
                                
                except Exception as e:
                    self.logger.warning(f"Failed to load module {modname}: {e}")
                    continue
        
        except Exception as e:
            self.logger.error(f"Tool discovery failed: {e}")
        
        self.logger.info(f"Discovered {discovered_count} tools")
        return discovered_count
    
    def get_tool(self, name: str, load: bool = True) -> Optional[Tool]:
        """
        Get tool instance by name.
        
        Args:
            name: Tool name
            load: Whether to load tool if not already loaded
            
        Returns:
            Tool instance or None if not found
        """
        tool_info = self._tools.get(name)
        if not tool_info:
            return None
        
        # Load tool if needed
        if not tool_info.is_loaded and load:
            try:
                tool_info.instance = tool_info.tool_class()
                tool_info.is_loaded = True
                tool_info.load_count += 1
                self.logger.debug(f"Loaded tool: {name}")
            except Exception as e:
                self.logger.error(f"Failed to load tool {name}: {e}")
                tool_info.error_count += 1
                return None
        
        # Update usage stats
        tool_info.last_used = datetime.now()
        return tool_info.instance
    
    def find_tools_for_request(self, 
                              contextual_request: ContextualRequest,
                              context: ToolContext,
                              max_tools: int = 5) -> List[Tuple[str, float]]:
        """
        Find best tools for handling a request.
        
        Args:
            contextual_request: Analyzed user request
            context: Tool execution context
            max_tools: Maximum number of tools to return
            
        Returns:
            List of (tool_name, confidence) tuples sorted by confidence
        """
        candidates = []
        
        # Check each tool
        for name, tool_info in self._tools.items():
            try:
                # Load tool if needed
                tool = self.get_tool(name, load=True)
                if not tool:
                    continue
                
                # Check if tool can handle request
                confidence = tool.can_handle_request(
                    contextual_request.processed_request, 
                    context
                )
                
                if confidence > 0.0:
                    candidates.append((name, confidence))
                    
            except Exception as e:
                self.logger.warning(f"Error checking tool {name}: {e}")
                tool_info.error_count += 1
                continue
        
        # Sort by confidence (descending)
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Return top candidates
        return candidates[:max_tools]
    
    def find_tools_by_capability(self, capability: str) -> List[str]:
        """
        Find tools that provide a specific capability.
        
        Args:
            capability: Capability name
            
        Returns:
            List of tool names that provide the capability
        """
        return list(self._capabilities.get(capability, set()))
    
    def get_tools_by_category(self, category: str) -> List[str]:
        """
        Get all tools in a category.
        
        Args:
            category: Category name
            
        Returns:
            List of tool names in the category
        """
        return list(self._categories.get(category, set()))
    
    def resolve_dependencies(self, tool_names: List[str]) -> List[str]:
        """
        Resolve tool dependencies and return execution order.
        
        Args:
            tool_names: List of tool names to resolve
            
        Returns:
            Ordered list of tool names with dependencies resolved
        """
        resolved = []
        visited = set()
        visiting = set()
        
        def visit(name: str) -> bool:
            """Visit tool and its dependencies."""
            if name in visiting:
                self.logger.error(f"Circular dependency detected: {name}")
                return False
            
            if name in visited:
                return True
            
            tool_info = self._tools.get(name)
            if not tool_info:
                self.logger.error(f"Tool not found: {name}")
                return False
            
            visiting.add(name)
            
            # Visit dependencies first
            for dep in tool_info.dependencies:
                if not visit(dep):
                    return False
            
            visiting.remove(name)
            visited.add(name)
            resolved.append(name)
            return True
        
        # Visit each requested tool
        for name in tool_names:
            if not visit(name):
                self.logger.error(f"Dependency resolution failed for: {name}")
                return []
        
        return resolved
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        total_tools = len(self._tools)
        loaded_tools = sum(1 for info in self._tools.values() if info.is_loaded)
        
        category_counts = {
            category: len(tools) 
            for category, tools in self._categories.items()
        }
        
        return {
            "total_tools": total_tools,
            "loaded_tools": loaded_tools,
            "categories": len(self._categories),
            "category_counts": category_counts,
            "capabilities": len(self._capabilities),
            "loaded_modules": len(self._loaded_modules),
            "tools_with_errors": sum(
                1 for info in self._tools.values() if info.error_count > 0
            )
        }
    
    def get_tool_info(self, name: str) -> Optional[ToolInfo]:
        """Get tool information."""
        return self._tools.get(name)
    
    def get_all_tools(self) -> Dict[str, ToolInfo]:
        """Get all registered tools."""
        return self._tools.copy()
    
    def unload_tool(self, name: str) -> bool:
        """
        Unload a tool to free memory.
        
        Args:
            name: Tool name
            
        Returns:
            True if unloaded successfully
        """
        tool_info = self._tools.get(name)
        if not tool_info or not tool_info.is_loaded:
            return False
        
        try:
            tool_info.instance = None
            tool_info.is_loaded = False
            self.logger.debug(f"Unloaded tool: {name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to unload tool {name}: {e}")
            return False
    
    def reload_tool(self, name: str) -> bool:
        """
        Reload a tool (unload and load again).
        
        Args:
            name: Tool name
            
        Returns:
            True if reloaded successfully
        """
        self.unload_tool(name)
        tool = self.get_tool(name, load=True)
        return tool is not None
    
    def _validate_tool(self, tool: Tool) -> bool:
        """
        Validate tool implementation.
        
        Args:
            tool: Tool instance to validate
            
        Returns:
            True if tool is valid
        """
        try:
            # Check required attributes
            if not tool.name or not tool.description or not tool.category:
                self.logger.error(f"Tool missing required attributes: {tool}")
                return False
            
            # Check execute method
            if not hasattr(tool, 'execute') or not callable(tool.execute):
                self.logger.error(f"Tool missing execute method: {tool.name}")
                return False
            
            # Check async compatibility
            if tool.is_async and not inspect.iscoroutinefunction(tool.execute):
                self.logger.warning(f"Tool marked as async but execute is not coroutine: {tool.name}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Tool validation failed: {e}")
            return False