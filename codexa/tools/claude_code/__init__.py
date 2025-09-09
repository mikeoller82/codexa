"""
Claude Code tools integration for Codexa.

This module provides exact Claude Code tool implementations that can be used
by the Codexa tool system to provide Claude Code compatibility.
"""

# Core Claude Code tools
import logging
logger = logging.getLogger(__name__)

# Import core tools (no external dependencies)
try:
    from .task_tool import TaskTool
    from .bash_tool import BashTool
    from .glob_tool import GlobTool
    from .grep_tool import GrepTool
    from .ls_tool import LSTool
    from .read_tool import ReadTool
    from .edit_tool import EditTool
    from .multi_edit_tool import MultiEditTool
    from .write_tool import WriteTool
    from .todo_write_tool import TodoWriteTool
    from .notebook_edit_tool import NotebookEditTool
    from .bash_output_tool import BashOutputTool
    from .kill_bash_tool import KillBashTool
    from .claude_code_registry import claude_code_registry
except ImportError as e:
    logger.error(f"Failed to import core Claude Code tools: {e}")
    TaskTool = BashTool = GlobTool = GrepTool = LSTool = None
    ReadTool = EditTool = MultiEditTool = WriteTool = None
    TodoWriteTool = NotebookEditTool = BashOutputTool = KillBashTool = None
    claude_code_registry = None

# Import web tools (require aiohttp)
try:
    from .web_fetch_tool import WebFetchTool
    from .web_search_tool import WebSearchTool
except ImportError as e:
    logger.warning(f"Web tools unavailable (missing aiohttp): {e}")
    WebFetchTool = WebSearchTool = None

__all__ = [
    'TaskTool',
    'BashTool', 
    'GlobTool',
    'GrepTool',
    'LSTool',
    'ReadTool',
    'EditTool',
    'MultiEditTool',
    'WriteTool',
    'WebFetchTool',
    'WebSearchTool',
    'TodoWriteTool',
    'NotebookEditTool',
    'BashOutputTool',
    'KillBashTool',
    'claude_code_registry'
]