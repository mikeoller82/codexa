"""
MCP (Model Context Protocol) tools for Codexa tool system.
"""

# Import all MCP tools for auto-discovery
from .mcp_query_tool import MCPQueryTool
from .mcp_documentation_tool import MCPDocumentationTool
from .mcp_code_analysis_tool import MCPCodeAnalysisTool
from .mcp_ui_generation_tool import MCPUIGenerationTool
from .mcp_testing_tool import MCPTestingTool
from .mcp_server_management_tool import MCPServerManagementTool
from .mcp_health_check_tool import MCPHealthCheckTool
from .mcp_routing_tool import MCPRoutingTool
from .mcp_connection_tool import MCPConnectionTool
from .mcp_configuration_tool import MCPConfigurationTool

__all__ = [
    'MCPQueryTool',
    'MCPDocumentationTool',
    'MCPCodeAnalysisTool',
    'MCPUIGenerationTool',
    'MCPTestingTool',
    'MCPServerManagementTool',
    'MCPHealthCheckTool',
    'MCPRoutingTool',
    'MCPConnectionTool',
    'MCPConfigurationTool'
]