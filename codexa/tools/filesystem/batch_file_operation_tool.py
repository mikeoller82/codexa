"""
Batch File Operation Tool for Codexa.
"""

from pathlib import Path
from typing import Set, List, Dict, Any
import re

from ..base.tool_interface import Tool, ToolResult, ToolContext


class BatchFileOperationTool(Tool):
    """Tool for performing batch operations on multiple files."""
    
    @property
    def name(self) -> str:
        return "batch_file_operation"
    
    @property
    def description(self) -> str:
        return "Perform batch operations on multiple files (copy, move, delete, etc.)"
    
    @property
    def category(self) -> str:
        return "filesystem"
    
    @property
    def capabilities(self) -> Set[str]:
        return {"batch", "bulk", "multi_file", "file_management"}
    
    @property
    def required_context(self) -> Set[str]:
        return {"operation", "file_paths"}
    
    @property
    def dependencies(self) -> Set[str]:
        return {"copy_file", "move_file", "delete_file"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit batch operations
        if any(phrase in request_lower for phrase in [
            "batch", "bulk", "all files", "multiple files",
            "mass", "batch operation", "bulk operation"
        ]):
            return 0.9
        
        # Medium confidence for operations on multiple files
        file_count = len(re.findall(r'[a-zA-Z0-9_/.-]+\.[a-zA-Z0-9]+', request))
        if file_count > 1 and any(word in request_lower for word in [
            "copy", "move", "delete", "rename", "modify"
        ]):
            return 0.7
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute batch file operation."""
        try:
            # Get parameters from context
            operation = context.get_state("operation")
            file_paths = context.get_state("file_paths", [])
            target_directory = context.get_state("target_directory")
            
            # Try to extract from request if not in context
            if not operation or not file_paths:
                extracted = self._extract_batch_parameters(context.user_request)
                operation = operation or extracted.get("operation")
                file_paths = file_paths or extracted.get("file_paths", [])
                target_directory = target_directory or extracted.get("target_directory")
            
            if not operation:
                return ToolResult.error_result(
                    error="No operation specified",
                    tool_name=self.name
                )
            
            if not file_paths:
                return ToolResult.error_result(
                    error="No file paths specified",
                    tool_name=self.name
                )
            
            # Execute batch operation
            results = await self._execute_batch_operation(
                operation, file_paths, target_directory, context
            )
            
            successful_ops = sum(1 for r in results if r["success"])
            failed_ops = len(results) - successful_ops
            
            return ToolResult.success_result(
                data={
                    "operation": operation,
                    "total_files": len(file_paths),
                    "successful": successful_ops,
                    "failed": failed_ops,
                    "results": results
                },
                tool_name=self.name,
                files_modified=[r["file"] for r in results if r["success"] and operation != "delete"],
                output=f"Batch {operation}: {successful_ops} successful, {failed_ops} failed"
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Failed to execute batch operation: {str(e)}",
                tool_name=self.name
            )
    
    async def _execute_batch_operation(self, operation: str, file_paths: List[str],
                                     target_directory: str, context: ToolContext) -> List[Dict[str, Any]]:
        """Execute batch operation on files."""
        results = []
        
        for file_path in file_paths:
            result = {
                "file": file_path,
                "operation": operation,
                "success": False,
                "error": None
            }
            
            try:
                if operation.lower() in ["copy", "cp"]:
                    if not target_directory:
                        result["error"] = "Target directory required for copy operation"
                    else:
                        success = await self._copy_file(file_path, target_directory, context)
                        result["success"] = success
                        if success:
                            result["target"] = str(Path(target_directory) / Path(file_path).name)
                
                elif operation.lower() in ["move", "mv"]:
                    if not target_directory:
                        result["error"] = "Target directory required for move operation"
                    else:
                        success = await self._move_file(file_path, target_directory, context)
                        result["success"] = success
                        if success:
                            result["target"] = str(Path(target_directory) / Path(file_path).name)
                
                elif operation.lower() in ["delete", "rm", "del"]:
                    success = await self._delete_file(file_path, context)
                    result["success"] = success
                
                else:
                    result["error"] = f"Unsupported operation: {operation}"
            
            except Exception as e:
                result["error"] = str(e)
            
            results.append(result)
        
        return results
    
    async def _copy_file(self, source: str, target_dir: str, context: ToolContext) -> bool:
        """Copy file to target directory."""
        try:
            from .copy_file_tool import CopyFileTool
            copy_tool = CopyFileTool()
            
            target_path = str(Path(target_dir) / Path(source).name)
            
            # Create context for copy operation
            copy_context = ToolContext(
                request_id=context.request_id,
                user_request=f"copy {source} to {target_path}",
                session_id=context.session_id,
                current_dir=context.current_dir,
                config=context.config,
                mcp_service=context.mcp_service,
                provider=context.provider
            )
            copy_context.update_state("source", source)
            copy_context.update_state("destination", target_path)
            
            result = await copy_tool.execute(copy_context)
            return result.success
            
        except Exception as e:
            self.logger.error(f"Copy failed: {e}")
            return False
    
    async def _move_file(self, source: str, target_dir: str, context: ToolContext) -> bool:
        """Move file to target directory."""
        try:
            from .move_file_tool import MoveFileTool
            move_tool = MoveFileTool()
            
            target_path = str(Path(target_dir) / Path(source).name)
            
            # Create context for move operation
            move_context = ToolContext(
                request_id=context.request_id,
                user_request=f"move {source} to {target_path}",
                session_id=context.session_id,
                current_dir=context.current_dir,
                config=context.config,
                mcp_service=context.mcp_service,
                provider=context.provider
            )
            move_context.update_state("source", source)
            move_context.update_state("destination", target_path)
            
            result = await move_tool.execute(move_context)
            return result.success
            
        except Exception as e:
            self.logger.error(f"Move failed: {e}")
            return False
    
    async def _delete_file(self, file_path: str, context: ToolContext) -> bool:
        """Delete file."""
        try:
            from .delete_file_tool import DeleteFileTool
            delete_tool = DeleteFileTool()
            
            # Create context for delete operation
            delete_context = ToolContext(
                request_id=context.request_id,
                user_request=f"delete {file_path}",
                session_id=context.session_id,
                current_dir=context.current_dir,
                config=context.config,
                mcp_service=context.mcp_service,
                provider=context.provider
            )
            delete_context.update_state("file_path", file_path)
            
            result = await delete_tool.execute(delete_context)
            return result.success
            
        except Exception as e:
            self.logger.error(f"Delete failed: {e}")
            return False
    
    def _extract_batch_parameters(self, request: str) -> Dict[str, Any]:
        """Extract batch operation parameters from request."""
        result = {
            "operation": "",
            "file_paths": [],
            "target_directory": ""
        }
        
        # Detect operation
        request_lower = request.lower()
        if any(word in request_lower for word in ["copy", "cp"]):
            result["operation"] = "copy"
        elif any(word in request_lower for word in ["move", "mv"]):
            result["operation"] = "move"
        elif any(word in request_lower for word in ["delete", "rm", "del"]):
            result["operation"] = "delete"
        
        # Extract file paths
        file_pattern = r'([a-zA-Z0-9_/.-]+\.[a-zA-Z0-9]+)'
        result["file_paths"] = re.findall(file_pattern, request)
        
        # Extract target directory
        target_patterns = [
            r'to\s+([a-zA-Z0-9_/.-]+)',
            r'into\s+([a-zA-Z0-9_/.-]+)',
            r'destination\s+([a-zA-Z0-9_/.-]+)'
        ]
        
        for pattern in target_patterns:
            matches = re.findall(pattern, request, re.IGNORECASE)
            if matches:
                result["target_directory"] = matches[0]
                break
        
        return result