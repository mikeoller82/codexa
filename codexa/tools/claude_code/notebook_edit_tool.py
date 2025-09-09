"""
NotebookEdit tool - Edits Jupyter notebook cells.
"""

import json
import os
from pathlib import Path
from typing import Set, Dict, Any, Optional
from ..base.tool_interface import Tool, ToolContext, ToolResult


class NotebookEditTool(Tool):
    """Edits Jupyter notebook cells."""
    
    @property
    def name(self) -> str:
        return "NotebookEdit"
    
    @property
    def description(self) -> str:
        return "Completely replaces the contents of a specific cell in a Jupyter notebook"
    
    @property
    def category(self) -> str:
        return "claude_code"
    
    @property
    def required_context(self) -> Set[str]:
        return {"notebook_path", "new_source"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Determine if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for notebook operations
        if any(phrase in request_lower for phrase in [
            "edit notebook", "modify notebook", "jupyter notebook", "ipynb"
        ]):
            return 0.9
        
        # Medium confidence for cell operations
        if any(phrase in request_lower for phrase in [
            "notebook cell", "edit cell", "modify cell"
        ]):
            return 0.8
        
        # Lower confidence for notebook files
        if ".ipynb" in request_lower:
            return 0.6
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute the NotebookEdit tool."""
        try:
            # Extract parameters
            notebook_path = context.get_state("notebook_path")
            new_source = context.get_state("new_source")
            cell_id = context.get_state("cell_id")
            cell_type = context.get_state("cell_type")
            edit_mode = context.get_state("edit_mode", "replace")
            
            if not notebook_path:
                return ToolResult.error_result(
                    error="Missing required parameter: notebook_path",
                    tool_name=self.name
                )
            
            if new_source is None:
                return ToolResult.error_result(
                    error="Missing required parameter: new_source",
                    tool_name=self.name
                )
            
            # Convert to Path object
            target_path = Path(notebook_path)
            
            if not target_path.exists():
                return ToolResult.error_result(
                    error=f"Notebook file does not exist: {notebook_path}",
                    tool_name=self.name
                )
            
            if not target_path.suffix.lower() == '.ipynb':
                return ToolResult.error_result(
                    error=f"File is not a Jupyter notebook (.ipynb): {notebook_path}",
                    tool_name=self.name
                )
            
            # Load notebook
            try:
                with open(target_path, 'r', encoding='utf-8') as f:
                    notebook = json.load(f)
            except json.JSONDecodeError as e:
                return ToolResult.error_result(
                    error=f"Invalid JSON in notebook file: {str(e)}",
                    tool_name=self.name
                )
            except Exception as e:
                return ToolResult.error_result(
                    error=f"Failed to read notebook file: {str(e)}",
                    tool_name=self.name
                )
            
            # Validate notebook structure
            if not isinstance(notebook, dict) or 'cells' not in notebook:
                return ToolResult.error_result(
                    error="Invalid notebook structure: missing 'cells' field",
                    tool_name=self.name
                )
            
            cells = notebook['cells']
            if not isinstance(cells, list):
                return ToolResult.error_result(
                    error="Invalid notebook structure: 'cells' must be a list",
                    tool_name=self.name
                )
            
            # Perform the edit operation
            result = self._perform_edit(cells, cell_id, new_source, cell_type, edit_mode)
            
            if not result["success"]:
                return ToolResult.error_result(
                    error=result["error"],
                    tool_name=self.name
                )
            
            # Save modified notebook
            try:
                with open(target_path, 'w', encoding='utf-8') as f:
                    json.dump(notebook, f, indent=2, ensure_ascii=False)
                
                return ToolResult.success_result(
                    data={
                        "notebook_path": str(target_path.resolve()),
                        "edit_mode": edit_mode,
                        "cell_id": cell_id,
                        "cell_type": result.get("cell_type"),
                        "cell_index": result.get("cell_index"),
                        "total_cells": len(cells),
                        "operation": result.get("operation")
                    },
                    tool_name=self.name,
                    output=f"Notebook edited successfully: {target_path.name} ({result.get('operation', edit_mode)} operation)",
                    files_modified=[str(target_path)]
                )
                
            except Exception as e:
                return ToolResult.error_result(
                    error=f"Failed to save notebook file: {str(e)}",
                    tool_name=self.name
                )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"NotebookEdit tool execution failed: {str(e)}",
                tool_name=self.name
            )
    
    def _perform_edit(self, cells: list, cell_id: Optional[str], new_source: str, 
                     cell_type: Optional[str], edit_mode: str) -> Dict[str, Any]:
        """Perform the actual edit operation on the cells."""
        
        if edit_mode == "insert":
            return self._insert_cell(cells, cell_id, new_source, cell_type)
        elif edit_mode == "delete":
            return self._delete_cell(cells, cell_id)
        else:  # replace mode
            return self._replace_cell(cells, cell_id, new_source, cell_type)
    
    def _find_cell_index(self, cells: list, cell_id: str) -> int:
        """Find cell index by cell ID."""
        for i, cell in enumerate(cells):
            if isinstance(cell, dict) and cell.get('id') == cell_id:
                return i
        return -1
    
    def _insert_cell(self, cells: list, cell_id: Optional[str], new_source: str, 
                    cell_type: Optional[str]) -> Dict[str, Any]:
        """Insert a new cell."""
        if not cell_type:
            return {"success": False, "error": "cell_type is required for insert mode"}
        
        if cell_type not in ["code", "markdown"]:
            return {"success": False, "error": "cell_type must be 'code' or 'markdown'"}
        
        # Create new cell
        import uuid
        new_cell = {
            "id": str(uuid.uuid4()),
            "cell_type": cell_type,
            "source": new_source.splitlines(keepends=True) if new_source else [],
            "metadata": {}
        }
        
        if cell_type == "code":
            new_cell["execution_count"] = None
            new_cell["outputs"] = []
        
        # Find insertion point
        if cell_id:
            insert_index = self._find_cell_index(cells, cell_id)
            if insert_index == -1:
                return {"success": False, "error": f"Cell with ID '{cell_id}' not found"}
            insert_index += 1  # Insert after the specified cell
        else:
            insert_index = 0  # Insert at beginning
        
        # Insert the cell
        cells.insert(insert_index, new_cell)
        
        return {
            "success": True,
            "operation": "insert",
            "cell_index": insert_index,
            "cell_type": cell_type,
            "cell_id": new_cell["id"]
        }
    
    def _delete_cell(self, cells: list, cell_id: Optional[str]) -> Dict[str, Any]:
        """Delete a cell."""
        if not cell_id:
            return {"success": False, "error": "cell_id is required for delete mode"}
        
        cell_index = self._find_cell_index(cells, cell_id)
        if cell_index == -1:
            return {"success": False, "error": f"Cell with ID '{cell_id}' not found"}
        
        # Remove the cell
        deleted_cell = cells.pop(cell_index)
        
        return {
            "success": True,
            "operation": "delete",
            "cell_index": cell_index,
            "cell_type": deleted_cell.get("cell_type"),
            "cell_id": cell_id
        }
    
    def _replace_cell(self, cells: list, cell_id: Optional[str], new_source: str, 
                     cell_type: Optional[str]) -> Dict[str, Any]:
        """Replace cell content."""
        if cell_id:
            # Find cell by ID
            cell_index = self._find_cell_index(cells, cell_id)
            if cell_index == -1:
                return {"success": False, "error": f"Cell with ID '{cell_id}' not found"}
        else:
            # Use first cell if no ID specified
            if not cells:
                return {"success": False, "error": "No cells in notebook"}
            cell_index = 0
        
        cell = cells[cell_index]
        
        # Update cell type if specified
        if cell_type:
            if cell_type not in ["code", "markdown"]:
                return {"success": False, "error": "cell_type must be 'code' or 'markdown'"}
            
            cell["cell_type"] = cell_type
            
            # Update cell structure based on type
            if cell_type == "code":
                if "execution_count" not in cell:
                    cell["execution_count"] = None
                if "outputs" not in cell:
                    cell["outputs"] = []
            else:  # markdown
                # Remove code-specific fields
                cell.pop("execution_count", None)
                cell.pop("outputs", None)
        
        # Update source
        cell["source"] = new_source.splitlines(keepends=True) if new_source else []
        
        return {
            "success": True,
            "operation": "replace",
            "cell_index": cell_index,
            "cell_type": cell.get("cell_type"),
            "cell_id": cell.get("id")
        }


# Claude Code schema compatibility
CLAUDE_CODE_SCHEMA = {
    "type": "object",
    "properties": {
        "notebook_path": {
            "type": "string",
            "description": "The absolute path to the Jupyter notebook file to edit"
        },
        "cell_id": {
            "type": "string",
            "description": "The ID of the cell to edit"
        },
        "new_source": {
            "type": "string",
            "description": "The new source for the cell"
        },
        "cell_type": {
            "type": "string",
            "enum": ["code", "markdown"],
            "description": "The type of the cell (code or markdown)"
        },
        "edit_mode": {
            "type": "string",
            "enum": ["replace", "insert", "delete"],
            "description": "The type of edit to make (replace, insert, delete)"
        }
    },
    "required": ["notebook_path", "new_source"],
    "additionalProperties": False
}