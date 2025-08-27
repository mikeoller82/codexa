"""
Contextual Help Tool for Codexa.
"""

from typing import Set, Dict, Any, List

from ..base.tool_interface import Tool, ToolResult, ToolContext


class ContextualHelpTool(Tool):
    """Tool for providing contextual help and guidance."""
    
    @property
    def name(self) -> str:
        return "contextual_help"
    
    @property
    def description(self) -> str:
        return "Provide contextual help, command information, and usage guidance"
    
    @property
    def category(self) -> str:
        return "enhanced"
    
    @property
    def capabilities(self) -> Set[str]:
        return {"help", "guidance", "documentation", "assistance"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit help requests
        if any(phrase in request_lower for phrase in [
            "help", "?", "how to", "usage", "guide", "documentation",
            "what can you do", "commands", "available tools"
        ]):
            return 0.9
        
        # Medium confidence for guidance requests
        if any(word in request_lower for word in ["explain", "show", "list"]):
            return 0.4
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute contextual help."""
        try:
            # Get parameters from context
            help_topic = context.get_state("help_topic", "general")
            detailed = context.get_state("detailed", False)
            
            # Extract topic from request
            topic = self._extract_help_topic(context.user_request)
            if topic:
                help_topic = topic
            
            # Generate help content
            help_content = await self._generate_help_content(help_topic, detailed, context)
            
            return ToolResult.success_result(
                data={
                    "topic": help_topic,
                    "detailed": detailed,
                    "help_content": help_content
                },
                tool_name=self.name,
                output=help_content
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Failed to provide help: {str(e)}",
                tool_name=self.name
            )
    
    async def _generate_help_content(self, topic: str, detailed: bool, context: ToolContext) -> str:
        """Generate contextual help content."""
        if topic == "tools":
            return await self._get_tools_help(context)
        elif topic == "commands":
            return await self._get_commands_help(context)
        elif topic == "mcp":
            return await self._get_mcp_help(context)
        elif topic == "filesystem":
            return await self._get_filesystem_help(context)
        else:
            return await self._get_general_help(context)
    
    async def _get_general_help(self, context: ToolContext) -> str:
        """Get general help information."""
        return """
🤖 **Codexa Tool-Based AI Agent** 

**What is Codexa?**
Codexa is an intelligent AI coding assistant that uses a dynamic tool-based architecture. 
Instead of hardcoded functionality, Codexa dynamically selects and executes the best tools for your requests.

**Key Features:**
• 🛠️  **Dynamic Tools**: Over 60+ specialized tools for different tasks
• 🔗 **MCP Integration**: Context7, Sequential, Magic, Playwright servers
• 📁 **Smart Filesystem**: Intelligent file operations with MCP fallback
• 🎯 **Contextual Routing**: Automatic tool selection based on your request
• 🔧 **Enhanced Features**: ASCII logos, animations, contextual help

**Getting Started:**
• Ask natural language questions: "read the README file"
• Use specific commands: "/help tools" for tool information
• Request file operations: "create a new Python file"
• Get documentation: "show me React documentation"

**Need More Help?**
• `/help tools` - Available tools and capabilities
• `/help commands` - Command reference
• `/help mcp` - MCP server information
• `/help filesystem` - File operation examples

Type your request naturally - Codexa will figure out which tools to use!
"""
    
    async def _get_tools_help(self, context: ToolContext) -> str:
        """Get help about available tools."""
        help_content = ["🛠️ **Available Tools**\n"]
        
        # Try to get tool information from tool manager if available
        try:
            from ...tools import ToolManager
            manager = ToolManager(auto_discover=False)  # Don't auto-discover to avoid loading everything
            
            # Manually list tool categories
            categories = {
                "filesystem": "File operations (read, write, search, etc.)",
                "mcp": "MCP server integration (documentation, analysis, UI generation)",
                "enhanced": "Enhanced features (logos, help, suggestions)",
                "system": "System operations (configuration, monitoring)"
            }
            
            for category, description in categories.items():
                help_content.append(f"**{category.title()}**: {description}")
            
            help_content.append("\n**Tool Categories:**")
            help_content.append("• **Filesystem Tools**: read_file, write_file, search_files, etc.")
            help_content.append("• **MCP Tools**: mcp_documentation, mcp_code_analysis, mcp_ui_generation")
            help_content.append("• **Enhanced Tools**: contextual_help, ascii_logo, suggestions")
            
        except Exception:
            help_content.append("Tool information not available (tool manager not initialized)")
        
        help_content.append("\n💡 **Tip**: Just describe what you want to do - Codexa will select the right tools!")
        
        return "\n".join(help_content)
    
    async def _get_commands_help(self, context: ToolContext) -> str:
        """Get help about commands."""
        return """
📋 **Command Reference**

**Natural Language Commands:**
Just describe what you want to do in plain English:
• "Read the package.json file"
• "Create a new React component called Button"
• "Search for all Python files in the src directory"
• "Show me documentation for React hooks"

**Slash Commands** (if available):
• `/help` - Show this help
• `/status` - System status
• `/tools` - List available tools

**File Operations:**
• "Read [filename]" - Read file contents
• "Write [filename] with [content]" - Create/write file
• "Copy [source] to [destination]" - Copy files
• "Search for [pattern]" - Find files by pattern
• "List files in [directory]" - Directory contents

**MCP Operations:**
• "Get documentation for [library]" - Retrieve docs
• "Analyze this code: [code]" - Code analysis
• "Generate a [component] component" - UI generation
• "Run tests" - Execute tests

**Examples:**
• "Read the README.md file"
• "Create a new Python script called app.py"
• "Search for all TypeScript files"
• "Get React documentation"
• "Generate a login form component"

Just ask naturally - no special syntax required!
"""
    
    async def _get_mcp_help(self, context: ToolContext) -> str:
        """Get help about MCP integration."""
        return """
📡 **MCP (Model Context Protocol) Integration**

**What is MCP?**
MCP enables Codexa to connect to external servers that provide specialized capabilities like documentation, code analysis, and UI generation.

**Available MCP Servers:**
• **Context7**: Documentation and API references
• **Sequential**: Complex reasoning and analysis  
• **Magic**: UI component generation
• **Playwright**: Browser automation and testing

**MCP Features:**
• 🔍 **Smart Routing**: Automatic server selection based on request type
• 🔄 **Fallback System**: Local alternatives when servers unavailable
• ⚡ **Performance**: Caching and connection pooling
• 🔧 **Management**: Enable/disable servers dynamically

**Using MCP:**
• Documentation: "Show me Express.js documentation"
• Code Analysis: "Analyze this function for issues"
• UI Generation: "Create a responsive navbar component"
• Testing: "Run end-to-end tests"

**MCP Management:**
• "Check MCP server status"
• "Enable Sequential server"
• "Test connection to Context7"
• "List available MCP servers"

**Note**: MCP servers enhance Codexa's capabilities but aren't required - local fallbacks are available!
"""
    
    async def _get_filesystem_help(self, context: ToolContext) -> str:
        """Get help about filesystem operations."""
        return """
📁 **Filesystem Operations**

**Available Operations:**
• **Read**: Get file contents
• **Write**: Create or overwrite files
• **Modify**: Find and replace text in files
• **Copy**: Duplicate files and directories
• **Move**: Relocate or rename files
• **Delete**: Remove files (with safety checks)
• **Search**: Find files by name or content
• **List**: Show directory contents
• **Info**: Get file metadata and properties

**Examples:**

**Reading Files:**
• "Read the config.json file"
• "Show me the contents of src/app.py"
• "Read multiple files: app.js, config.js, package.json"

**Writing Files:**
• "Create a new file called todo.md"
• "Write a Python script that prints hello world"
• "Generate a package.json for a React project"

**Searching:**
• "Find all JavaScript files in the project"
• "Search for the word 'TODO' in all Python files"
• "Look for files containing 'import React'"

**Directory Operations:**
• "List files in the current directory"
• "Show the project structure"
• "Create a new directory called 'components'"

**File Management:**
• "Copy app.js to app.backup.js"
• "Move old-file.py to archive/old-file.py"
• "Delete the temporary files"

**Smart Features:**
• 🔄 **MCP Fallback**: Uses MCP filesystem when available, falls back to local
• 🛡️ **Safety**: Prevents deletion of system files
• 🎯 **Context**: Understands project structure and file relationships
• 📊 **Validation**: Checks file integrity and format
"""
    
    def _extract_help_topic(self, request: str) -> str:
        """Extract help topic from request."""
        request_lower = request.lower()
        
        if any(word in request_lower for word in ["tools", "tool"]):
            return "tools"
        elif any(word in request_lower for word in ["commands", "command"]):
            return "commands"
        elif any(word in request_lower for word in ["mcp", "servers", "server"]):
            return "mcp"
        elif any(word in request_lower for word in ["files", "filesystem", "file"]):
            return "filesystem"
        else:
            return "general"