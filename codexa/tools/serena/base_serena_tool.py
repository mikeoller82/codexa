"""
Base tool wrapper for Serena MCP server integration.
"""

import logging
from typing import Dict, Any, Set, Optional, List
from abc import abstractmethod

from ..base.tool_interface import Tool, ToolResult, ToolContext, ToolPriority, ToolDependency, DependencyType
from ...mcp.serena_client import SerenaClient, SerenaProjectConfig


class BaseSerenaTool(Tool):
    """Base class for all Serena MCP server tools."""
    
    def __init__(self):
        """Initialize base Serena tool."""
        super().__init__()
        self._serena_client: Optional[SerenaClient] = None
        self._project_activated = False
    
    @property 
    def category(self) -> str:
        """Tool category."""
        return "serena"
    
    @property
    def dependencies(self) -> List[ToolDependency]:
        """Serena tools depend on MCP connection."""
        return [
            ToolDependency(
                name="mcp_connection",
                dependency_type=DependencyType.REQUIRED,
                condition="Serena MCP server must be connected",
                fallback_tools=["filesystem_tools"]
            )
        ]
    
    @property
    def priority(self) -> ToolPriority:
        """Serena tools have high priority for semantic operations."""
        return ToolPriority.HIGH
    
    @property
    def timeout_seconds(self) -> float:
        """Increased timeout for language server operations."""
        return 45.0
    
    @property 
    def required_context(self) -> Set[str]:
        """Required context for Serena operations."""
        return {"mcp_service"}
    
    async def initialize(self, context: ToolContext) -> bool:
        """Initialize Serena tool with MCP client."""
        try:
            # Get Serena client from MCP service
            if context.mcp_service and hasattr(context.mcp_service, 'get_serena_client'):
                self._serena_client = context.mcp_service.get_serena_client()
                
                if not self._serena_client:
                    self.logger.warning("Serena client not available in MCP service - will attempt to start")
                    # Try to start Serena servers
                    if hasattr(context.mcp_service, 'start_servers'):
                        await context.mcp_service.start_servers()
                        self._serena_client = context.mcp_service.get_serena_client()
                    
                    if not self._serena_client:
                        self.logger.info("Serena client still not available - tool will be disabled")
                        return False
                
                if not self._serena_client.is_connected():
                    self.logger.warning("Serena client not connected - attempting connection")
                    try:
                        await self._serena_client.connect()
                    except Exception as e:
                        self.logger.warning(f"Failed to connect Serena client: {e}")
                        return False
                
                # Auto-activate project if current path available
                current_path = self._get_current_path(context)
                if current_path and not self._serena_client.is_project_active():
                    try:
                        await self._activate_current_project(current_path)
                    except Exception as e:
                        self.logger.warning(f"Failed to activate project: {e}")
                        # Don't fail initialization for project activation failure
                
                return True
            else:
                self.logger.error("MCP service not available or missing Serena client")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to initialize Serena tool: {e}")
            return False
    
    async def _activate_current_project(self, project_path: str) -> bool:
        """Activate the current project in Serena."""
        try:
            project_config = SerenaProjectConfig(
                path=project_path,
                auto_index=True,
                context_mode="ide-assistant"
            )
            
            success = await self._serena_client.activate_project(project_config)
            if success:
                self._project_activated = True
                self.logger.info(f"Activated Serena project: {project_path}")
            else:
                self.logger.warning(f"Failed to activate Serena project: {project_path}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error activating project: {e}")
            return False
    
    async def validate_context(self, context: ToolContext) -> bool:
        """Validate Serena-specific context requirements."""
        if not await super().validate_context(context):
            return False

        # Basic check - we need access to MCP service to get Serena client
        if not context.mcp_service:
            self.logger.debug("No MCP service available for Serena tools")
            return False

        # Check if MCP service has Serena capabilities
        # Allow validation to pass if MCP service exists, even if Serena client isn't fully connected yet
        # The actual connection will be established during initialization
        try:
            # Check if MCP service has get_serena_client method
            if hasattr(context.mcp_service, 'get_serena_client'):
                # Try to get Serena client but don't fail validation if it's not immediately available
                serena_client = context.mcp_service.get_serena_client()
                if serena_client:
                    self.logger.debug("Serena client available in MCP service")
                    return True
                else:
                    self.logger.debug("Serena client not yet available in MCP service, but will attempt initialization")
                    return True  # Allow validation to pass - initialization will handle connection
            else:
                self.logger.debug("MCP service does not have get_serena_client method")
                return False

        except Exception as e:
            self.logger.debug(f"Error checking Serena client availability: {e}")
            # Allow validation to pass - initialization will handle connection issues
            return True
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Enhanced request matching for Serena capabilities."""
        confidence = super().can_handle_request(request, context)
        request_lower = request.lower()
        
        # Boost confidence for semantic keywords
        semantic_keywords = [
            "symbol", "function", "class", "method", "variable", "reference", 
            "definition", "semantic", "language server", "ast", "parse"
        ]
        
        for keyword in semantic_keywords:
            if keyword in request_lower:
                confidence = max(confidence, 0.8)
        
        # Boost for code editing operations
        editing_keywords = [
            "refactor", "rename", "replace", "insert", "modify", "edit code",
            "change function", "update class", "restructure"
        ]
        
        for keyword in editing_keywords:
            if keyword in request_lower:
                confidence = max(confidence, 0.7)
        
        # Boost for project operations
        project_keywords = [
            "project", "onboard", "index", "analyze codebase", "memory", 
            "project structure", "codebase analysis"
        ]
        
        for keyword in project_keywords:
            if keyword in request_lower:
                confidence = max(confidence, 0.6)
        
        return confidence
    
    async def call_serena_tool(self, tool_name: str, parameters: Dict[str, Any], 
                              timeout: Optional[float] = None) -> Any:
        """Helper method to call Serena tools with error handling."""
        try:
            if not self._serena_client:
                raise ValueError("Serena client not initialized")
            
            return await self._serena_client.call_tool(tool_name, parameters, timeout)
            
        except Exception as e:
            self.logger.error(f"Serena tool call failed {tool_name}: {e}")
            raise
    
    def get_serena_capabilities(self) -> Dict[str, Any]:
        """Get current Serena capabilities."""
        if self._serena_client:
            return self._serena_client.get_capabilities()
        return {}
    
    def _get_current_path(self, context: ToolContext) -> Optional[str]:
        """Get current path from context safely."""
        # Try multiple possible attributes
        for attr in ['current_path', 'current_dir', 'project_path']:
            path = getattr(context, attr, None)
            if path:
                return str(path)
        
        # Try from shared state
        path = context.get_state('current_path') or context.get_state('current_dir')
        if path:
            return str(path)
        
        # Try from project_info
        if context.project_info:
            path = context.project_info.get('path') or context.project_info.get('root_path')
            if path:
                return str(path)
        
        # Default fallback
        import os
        return os.getcwd()
    
    def _create_error_result(self, error: str, **kwargs) -> ToolResult:
        """Create standardized error result for Serena tools."""
        return ToolResult.error_result(
            error=f"Serena {self.name}: {error}",
            tool_name=self.name,
            **kwargs
        )
    
    def _create_success_result(self, data: Any, output: Optional[str] = None, 
                             files_modified: Optional[List[str]] = None, **kwargs) -> ToolResult:
        """Create standardized success result for Serena tools."""
        return ToolResult.success_result(
            data=data,
            tool_name=self.name,
            output=output,
            files_modified=files_modified or [],
            **kwargs
        )
    
    @property
    @abstractmethod
    def serena_tool_names(self) -> List[str]:
        """List of Serena tool names this tool uses."""
        pass
    
    def get_tool_usage_help(self) -> str:
        """Get usage help for this tool."""
        return f"""
{self.name}: {self.description}

Category: {self.category}
Capabilities: {', '.join(self.capabilities)}
Serena Tools: {', '.join(self.serena_tool_names)}
Priority: {self.priority.name}
Timeout: {self.timeout_seconds}s

Requirements:
- Serena MCP server must be connected
- Project should be activated for best results

Usage: This tool provides semantic code operations through Serena's language server integration.
        """