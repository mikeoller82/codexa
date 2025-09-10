"""
Serena-based project management and memory tools.
"""

from typing import Dict, Any, Set, List, Optional
import os
from pathlib import Path

from ..base.tool_interface import ToolResult, ToolContext
from .base_serena_tool import BaseSerenaTool


class ProjectManagementTool(BaseSerenaTool):
    """Tool for project activation and management using Serena."""
    
    @property
    def name(self) -> str:
        return "serena_project_management"
    
    @property
    def description(self) -> str:
        return "Activate projects, perform onboarding, and manage project context in Serena"
    
    @property
    def capabilities(self) -> Set[str]:
        return {
            "project-activation", "project-onboarding", "project-management",
            "context-setup", "project-indexing", "codebase-analysis"
        }
    
    @property
    def serena_tool_names(self) -> List[str]:
        return ["activate_project", "onboarding", "check_onboarding_performed"]
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute project management operations."""
        try:
            request = context.user_request or ""
            request_lower = request.lower()
            
            # Determine operation type
            if any(word in request_lower for word in ["activate", "setup", "initialize"]):
                return await self._activate_project(context)
            elif any(word in request_lower for word in ["onboard", "index", "analyze"]):
                return await self._perform_onboarding(context)
            elif any(word in request_lower for word in ["status", "check", "info"]):
                return await self._check_project_status(context)
            else:
                # Default to activation if project path provided
                project_path = self._extract_project_path(context)
                if project_path:
                    return await self._activate_project(context)
                else:
                    return await self._check_project_status(context)
                    
        except Exception as e:
            return self._create_error_result(f"Project management failed: {e}")
    
    async def _activate_project(self, context: ToolContext) -> ToolResult:
        """Activate a project in Serena."""
        try:
            project_path = self._extract_project_path(context) or context.current_path or os.getcwd()
            
            # Convert to absolute path
            project_path = os.path.abspath(project_path)
            
            # Check if path exists and is a directory
            if not os.path.exists(project_path):
                return self._create_error_result(f"Project path does not exist: {project_path}")
            
            if not os.path.isdir(project_path):
                return self._create_error_result(f"Project path is not a directory: {project_path}")
            
            # Activate project via Serena client
            if self._serena_client and hasattr(self._serena_client, 'active_project'):
                # Check if project is already active
                if (self._serena_client.active_project and 
                    self._serena_client.active_project.path == project_path):
                    return self._create_success_result(
                        data={
                            "project_path": project_path,
                            "already_active": True
                        },
                        output=f"Project already active: {project_path}"
                    )
            
            # Call Serena activate_project tool
            result = await self.call_serena_tool("activate_project", {
                "project_path": project_path
            })
            
            if not result or not result.get("success", False):
                return self._create_error_result(f"Failed to activate project: {project_path}")
            
            # Check onboarding status
            onboarding_result = await self.call_serena_tool("check_onboarding_performed", {})
            onboarding_completed = onboarding_result.get("performed", False)
            
            output = f"Successfully activated project: {project_path}"
            if not onboarding_completed:
                output += "\nNote: Project onboarding has not been performed. Consider running onboarding for better semantic analysis."
            
            return self._create_success_result(
                data={
                    "project_path": project_path,
                    "activated": True,
                    "onboarding_completed": onboarding_completed
                },
                output=output
            )
            
        except Exception as e:
            return self._create_error_result(f"Project activation failed: {e}")
    
    async def _perform_onboarding(self, context: ToolContext) -> ToolResult:
        """Perform project onboarding/indexing."""
        try:
            # Check if project is active
            if not self._serena_client or not self._serena_client.is_project_active():
                return self._create_error_result("No active project. Please activate a project first.")
            
            # Check if onboarding already performed
            onboarding_result = await self.call_serena_tool("check_onboarding_performed", {})
            if onboarding_result.get("performed", False):
                return self._create_success_result(
                    data={"onboarding_completed": True, "already_performed": True},
                    output="Project onboarding has already been performed."
                )
            
            # Perform onboarding
            result = await self.call_serena_tool("onboarding", {}, timeout=120.0)  # Extended timeout
            
            if not result or not result.get("success", False):
                return self._create_error_result("Project onboarding failed")
            
            project_path = self._serena_client.active_project.path if self._serena_client.active_project else "Unknown"
            
            return self._create_success_result(
                data={
                    "project_path": project_path,
                    "onboarding_completed": True,
                    "just_performed": True
                },
                output=f"Successfully completed project onboarding for: {project_path}\nThe project is now indexed for semantic analysis and operations."
            )
            
        except Exception as e:
            return self._create_error_result(f"Project onboarding failed: {e}")
    
    async def _check_project_status(self, context: ToolContext) -> ToolResult:
        """Check current project status."""
        try:
            if not self._serena_client:
                return self._create_error_result("Serena client not available")
            
            # Get Serena capabilities
            capabilities = self._serena_client.get_capabilities()
            
            # Check onboarding status if project active
            onboarding_completed = False
            if capabilities.get("project_active", False):
                onboarding_result = await self.call_serena_tool("check_onboarding_performed", {})
                onboarding_completed = onboarding_result.get("performed", False)
            
            # Format status output
            output = ["Serena Project Status:"]
            output.append(f"  Connected: {capabilities.get('connected', False)}")
            output.append(f"  Project Active: {capabilities.get('project_active', False)}")
            
            if capabilities.get('project_active', False):
                project_path = self._serena_client.active_project.path if self._serena_client.active_project else "Unknown"
                output.append(f"  Project Path: {project_path}")
                output.append(f"  Onboarding Completed: {onboarding_completed}")
            
            output.append(f"  Available Tools: {len(capabilities.get('available_tools', []))}")
            
            # Tool categories
            tool_categories = capabilities.get('tool_categories', {})
            if tool_categories:
                output.append("  Tool Categories:")
                for category, count in tool_categories.items():
                    output.append(f"    {category}: {count} tools")
            
            return self._create_success_result(
                data={
                    "capabilities": capabilities,
                    "onboarding_completed": onboarding_completed,
                    "status": "active" if capabilities.get('project_active', False) else "inactive"
                },
                output="\n".join(output)
            )
            
        except Exception as e:
            return self._create_error_result(f"Status check failed: {e}")
    
    def _extract_project_path(self, context: ToolContext) -> Optional[str]:
        """Extract project path from request or context."""
        request = context.user_request or ""
        
        # Look for explicit path in request
        words = request.split()
        for word in words:
            if os.path.exists(word) and os.path.isdir(word):
                return word
            # Check for path-like structures
            if '/' in word and not word.startswith('-'):
                if os.path.exists(word):
                    return word
        
        # Look for common path indicators
        path_keywords = ["project", "path", "directory", "folder", "in"]
        for i, word in enumerate(words):
            if word.lower() in path_keywords and i + 1 < len(words):
                potential_path = words[i + 1]
                if os.path.exists(potential_path):
                    return potential_path
        
        return None


class MemoryManagementTool(BaseSerenaTool):
    """Tool for managing Serena's project memories."""
    
    @property
    def name(self) -> str:
        return "serena_memory_management"
    
    @property
    def description(self) -> str:
        return "Manage project memories for storing and retrieving project-specific knowledge"
    
    @property
    def capabilities(self) -> Set[str]:
        return {
            "memory-management", "knowledge-storage", "project-memory",
            "context-storage", "memory-retrieval"
        }
    
    @property
    def serena_tool_names(self) -> List[str]:
        return ["write_memory", "read_memory", "list_memories", "delete_memory"]
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute memory management operations."""
        try:
            request = context.user_request or ""
            request_lower = request.lower()
            
            # Determine memory operation
            if any(word in request_lower for word in ["write", "save", "store", "create memory"]):
                return await self._write_memory(context)
            elif any(word in request_lower for word in ["read", "get", "retrieve", "load"]):
                return await self._read_memory(context)
            elif any(word in request_lower for word in ["list", "show", "display"]):
                return await self._list_memories(context)
            elif any(word in request_lower for word in ["delete", "remove", "clear"]):
                return await self._delete_memory(context)
            else:
                # Default to listing memories
                return await self._list_memories(context)
                
        except Exception as e:
            return self._create_error_result(f"Memory management failed: {e}")
    
    async def _write_memory(self, context: ToolContext) -> ToolResult:
        """Write a memory to storage."""
        try:
            name, content = self._extract_memory_data(context)
            if not name:
                return self._create_error_result("Memory name not provided")
            if not content:
                return self._create_error_result("Memory content not provided")
            
            # Write memory
            success = await self.call_serena_tool("write_memory", {
                "name": name,
                "content": content
            })
            
            if not success:
                return self._create_error_result(f"Failed to write memory: {name}")
            
            return self._create_success_result(
                data={
                    "memory_name": name,
                    "content": content,
                    "operation": "write"
                },
                output=f"Successfully wrote memory: {name}\nContent length: {len(content)} characters"
            )
            
        except Exception as e:
            return self._create_error_result(f"Memory write failed: {e}")
    
    async def _read_memory(self, context: ToolContext) -> ToolResult:
        """Read a memory from storage."""
        try:
            name = self._extract_memory_name(context)
            if not name:
                return self._create_error_result("Memory name not provided")
            
            # Read memory
            content = await self.call_serena_tool("read_memory", {
                "name": name
            })
            
            if content is None:
                return self._create_error_result(f"Memory not found: {name}")
            
            output = f"Memory: {name}\n"
            output += "=" * 50 + "\n"
            output += content
            
            return self._create_success_result(
                data={
                    "memory_name": name,
                    "content": content,
                    "operation": "read"
                },
                output=output
            )
            
        except Exception as e:
            return self._create_error_result(f"Memory read failed: {e}")
    
    async def _list_memories(self, context: ToolContext) -> ToolResult:
        """List all available memories."""
        try:
            memories = await self.call_serena_tool("list_memories", {})
            
            if not memories:
                return self._create_success_result(
                    data={"memories": [], "count": 0},
                    output="No memories found."
                )
            
            output = f"Available memories ({len(memories)} total):"
            for memory in memories:
                output += f"\n  - {memory}"
            
            return self._create_success_result(
                data={
                    "memories": memories,
                    "count": len(memories),
                    "operation": "list"
                },
                output=output
            )
            
        except Exception as e:
            return self._create_error_result(f"Memory list failed: {e}")
    
    async def _delete_memory(self, context: ToolContext) -> ToolResult:
        """Delete a memory from storage."""
        try:
            name = self._extract_memory_name(context)
            if not name:
                return self._create_error_result("Memory name not provided")
            
            # Delete memory
            success = await self.call_serena_tool("delete_memory", {
                "name": name
            })
            
            if not success:
                return self._create_error_result(f"Failed to delete memory: {name}")
            
            return self._create_success_result(
                data={
                    "memory_name": name,
                    "operation": "delete"
                },
                output=f"Successfully deleted memory: {name}"
            )
            
        except Exception as e:
            return self._create_error_result(f"Memory deletion failed: {e}")
    
    def _extract_memory_data(self, context: ToolContext) -> tuple:
        """Extract memory name and content from request."""
        request = context.user_request or ""
        
        # Look for name and content patterns
        import re
        
        # Pattern: write memory "name" with "content"
        pattern1 = r'write\s+memory\s+["\']([^"\']+)["\'].*?with\s+["\']([^"\']*)["\']'
        match = re.search(pattern1, request, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1), match.group(2)
        
        # Pattern: save "name" "content" 
        pattern2 = r'save\s+["\']([^"\']+)["\'].*?["\']([^"\']*)["\']'
        match = re.search(pattern2, request, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1), match.group(2)
        
        # Look for name after memory keywords
        name_pattern = r'(?:memory|save|store)\s+["\']?([^"\']+)["\']?'
        name_match = re.search(name_pattern, request, re.IGNORECASE)
        name = name_match.group(1) if name_match else None
        
        # Look for content in quotes or after "with"/"content"
        content_patterns = [
            r'with\s+["\']([^"\']*)["\']',
            r'content\s+["\']([^"\']*)["\']',
            r'["\']([^"\']{20,})["\']'  # Long quoted strings
        ]
        
        content = None
        for pattern in content_patterns:
            match = re.search(pattern, request, re.DOTALL)
            if match:
                content = match.group(1)
                break
        
        return name, content
    
    def _extract_memory_name(self, context: ToolContext) -> Optional[str]:
        """Extract memory name from request."""
        request = context.user_request or ""
        
        # Look for quoted names
        import re
        quoted = re.findall(r'["\']([^"\']+)["\']', request)
        if quoted:
            return quoted[0]
        
        # Look for name after memory keywords
        name_patterns = [
            r'(?:read|get|load|delete|remove)\s+memory\s+(\w+)',
            r'(?:memory)\s+(\w+)',
            r'(?:read|get|load|delete|remove)\s+(\w+)'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, request, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Use last word as potential name
        words = [word for word in request.split() if word.isalnum()]
        if words:
            return words[-1]
        
        return None