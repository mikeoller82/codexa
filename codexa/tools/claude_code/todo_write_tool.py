"""
TodoWrite tool - Create and manage a structured task list for the current coding session.
"""

import json
from typing import Set, List, Dict, Any
from ..base.tool_interface import Tool, ToolContext, ToolResult


class TodoWriteTool(Tool):
    """Create and manage a structured task list for the current coding session."""
    
    @property
    def name(self) -> str:
        return "TodoWrite"
    
    @property
    def description(self) -> str:
        return "Create and manage a structured task list for your current coding session"
    
    @property
    def category(self) -> str:
        return "claude_code"
    
    @property
    def required_context(self) -> Set[str]:
        return {"todos"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Determine if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit todo operations
        if any(phrase in request_lower for phrase in [
            "todo list", "task list", "manage tasks", "track progress", "create todo"
        ]):
            return 0.9
        
        # Medium confidence for task management
        if any(phrase in request_lower for phrase in [
            "tasks", "todo", "checklist", "progress", "organize"
        ]):
            return 0.7
        
        # Lower confidence for planning activities
        if any(phrase in request_lower for phrase in [
            "plan", "organize", "track", "manage", "list"
        ]):
            return 0.3
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute the TodoWrite tool."""
        try:
            # Extract parameters
            todos = context.get_state("todos")
            
            if not todos:
                return ToolResult.error_result(
                    error="Missing required parameter: todos",
                    tool_name=self.name
                )
            
            if not isinstance(todos, list):
                return ToolResult.error_result(
                    error="todos parameter must be a list",
                    tool_name=self.name
                )
            
            # Validate todo items
            validation_result = self._validate_todos(todos)
            if not validation_result["valid"]:
                return ToolResult.error_result(
                    error=validation_result["error"],
                    tool_name=self.name
                )
            
            # Process and store todos
            processed_todos = self._process_todos(todos)
            
            # Update context with todos
            context.update_state("current_todos", processed_todos)
            
            # Generate summary
            summary = self._generate_summary(processed_todos)
            
            return ToolResult.success_result(
                data={
                    "todos": processed_todos,
                    "total_count": len(processed_todos),
                    "status_counts": self._count_by_status(processed_todos),
                    "summary": summary
                },
                tool_name=self.name,
                output=self._format_todo_output(processed_todos, summary)
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"TodoWrite tool execution failed: {str(e)}",
                tool_name=self.name
            )
    
    def _validate_todos(self, todos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate todo items structure."""
        required_fields = ["content", "status", "activeForm"]
        valid_statuses = ["pending", "in_progress", "completed"]
        
        for i, todo in enumerate(todos):
            if not isinstance(todo, dict):
                return {
                    "valid": False,
                    "error": f"Todo item {i+1} must be a dictionary"
                }
            
            # Check required fields
            for field in required_fields:
                if field not in todo:
                    return {
                        "valid": False,
                        "error": f"Todo item {i+1} is missing required field: {field}"
                    }
            
            # Validate content
            if not todo["content"] or not isinstance(todo["content"], str):
                return {
                    "valid": False,
                    "error": f"Todo item {i+1} must have non-empty content string"
                }
            
            # Validate activeForm
            if not todo["activeForm"] or not isinstance(todo["activeForm"], str):
                return {
                    "valid": False,
                    "error": f"Todo item {i+1} must have non-empty activeForm string"
                }
            
            # Validate status
            if todo["status"] not in valid_statuses:
                return {
                    "valid": False,
                    "error": f"Todo item {i+1} has invalid status. Must be one of: {valid_statuses}"
                }
        
        # Check for exactly one in_progress item
        in_progress_count = sum(1 for todo in todos if todo["status"] == "in_progress")
        if in_progress_count > 1:
            return {
                "valid": False,
                "error": "Only one task can be in_progress at a time"
            }
        
        return {"valid": True}
    
    def _process_todos(self, todos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and normalize todo items."""
        processed = []
        
        for i, todo in enumerate(todos):
            processed_todo = {
                "id": todo.get("id", str(i + 1)),
                "content": todo["content"].strip(),
                "activeForm": todo["activeForm"].strip(),
                "status": todo["status"],
                "created_at": todo.get("created_at"),
                "updated_at": todo.get("updated_at"),
                "metadata": todo.get("metadata", {})
            }
            
            processed.append(processed_todo)
        
        return processed
    
    def _count_by_status(self, todos: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count todos by status."""
        counts = {"pending": 0, "in_progress": 0, "completed": 0}
        
        for todo in todos:
            status = todo["status"]
            if status in counts:
                counts[status] += 1
        
        return counts
    
    def _generate_summary(self, todos: List[Dict[str, Any]]) -> str:
        """Generate a summary of the todo list."""
        if not todos:
            return "No tasks in the list"
        
        counts = self._count_by_status(todos)
        total = len(todos)
        
        summary_parts = [f"Total: {total} tasks"]
        
        if counts["completed"] > 0:
            completion_rate = (counts["completed"] / total) * 100
            summary_parts.append(f"{counts['completed']} completed ({completion_rate:.0f}%)")
        
        if counts["in_progress"] > 0:
            summary_parts.append(f"{counts['in_progress']} in progress")
        
        if counts["pending"] > 0:
            summary_parts.append(f"{counts['pending']} pending")
        
        return " | ".join(summary_parts)
    
    def _format_todo_output(self, todos: List[Dict[str, Any]], summary: str) -> str:
        """Format todo list for display."""
        if not todos:
            return "Todo list is empty"
        
        output_lines = ["📋 **Task List Updated**", "", summary, ""]
        
        # Group by status
        status_groups = {
            "in_progress": [t for t in todos if t["status"] == "in_progress"],
            "pending": [t for t in todos if t["status"] == "pending"],
            "completed": [t for t in todos if t["status"] == "completed"]
        }
        
        status_icons = {
            "in_progress": "🔄",
            "pending": "📋",
            "completed": "✅"
        }
        
        for status, icon in status_icons.items():
            items = status_groups[status]
            if items:
                output_lines.append(f"**{status.replace('_', ' ').title()}:**")
                for item in items:
                    content = item["content"]
                    if len(content) > 80:
                        content = content[:80] + "..."
                    output_lines.append(f"  {icon} {content}")
                output_lines.append("")
        
        return "\n".join(output_lines)


# Claude Code schema compatibility
CLAUDE_CODE_SCHEMA = {
    "type": "object",
    "properties": {
        "todos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "minLength": 1
                    },
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed"]
                    },
                    "activeForm": {
                        "type": "string",
                        "minLength": 1
                    },
                    "id": {
                        "type": "string"
                    }
                },
                "required": ["content", "status", "activeForm"],
                "additionalProperties": False
            },
            "description": "The updated todo list"
        }
    },
    "required": ["todos"],
    "additionalProperties": False
}