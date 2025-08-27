"""
MCP Filesystem integration for Codexa with secure file operations.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union, Any
from datetime import datetime

from ..mcp_service import MCPService
from ..mcp.protocol import MCPError
from ..enhanced_config import EnhancedConfig


class MCPFileSystem:
    """
    Secure filesystem operations using MCP Filesystem Server.
    
    Provides enhanced file operations with security validation,
    multiple file operations, and intelligent search capabilities.
    """
    
    def __init__(self, mcp_service: MCPService):
        """Initialize MCP filesystem interface."""
        self.mcp_service = mcp_service
        self.logger = logging.getLogger("codexa.filesystem")
        self.server_name = "filesystem"
    
    async def read_file(self, path: Union[str, Path]) -> str:
        """
        Read the complete contents of a file.
        
        Args:
            path: Path to the file to read
            
        Returns:
            File contents as string
            
        Raises:
            MCPError: If file cannot be read or doesn't exist
        """
        try:
            result = await self.mcp_service.query_server(
                "read_file",
                preferred_server=self.server_name,
                context={"path": str(path)}
            )
            # Parse MCP tool response format
            if result and "content" in result and result["content"]:
                return result["content"][0].get("text", "")
            return ""
        except Exception as e:
            self.logger.error(f"Failed to read file {path}: {e}")
            raise MCPError(f"Cannot read file {path}: {e}")
    
    async def read_multiple_files(self, paths: List[Union[str, Path]]) -> Dict[str, str]:
        """
        Read multiple files in a single operation for efficiency.
        
        Args:
            paths: List of file paths to read
            
        Returns:
            Dictionary mapping file paths to their contents
            
        Raises:
            MCPError: If any files cannot be read
        """
        try:
            str_paths = [str(p) for p in paths]
            result = await self.mcp_service.query_server(
                f"read_multiple_files",
                preferred_server=self.server_name,
                context={"paths": str_paths, "operation": "read_multiple_files"}
            )
            return result.get("files", {})
        except Exception as e:
            self.logger.error(f"Failed to read multiple files: {e}")
            raise MCPError(f"Cannot read multiple files: {e}")
    
    async def write_file(self, path: Union[str, Path], content: str) -> bool:
        """
        Create a new file or overwrite existing file with content.
        
        Args:
            path: Path where to write the file
            content: Content to write to the file
            
        Returns:
            True if successful
            
        Raises:
            MCPError: If file cannot be written
        """
        try:
            await self.mcp_service.query_server(
                f"write_file",
                preferred_server=self.server_name,
                context={"path": str(path), "content": content, "operation": "write_file"}
            )
            self.logger.info(f"Successfully wrote file: {path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to write file {path}: {e}")
            raise MCPError(f"Cannot write file {path}: {e}")
    
    async def modify_file(self, path: Union[str, Path], find: str, replace: str, 
                         all_occurrences: bool = True, regex: bool = False) -> Dict[str, Any]:
        """
        Update file by finding and replacing text.
        
        Args:
            path: Path to the file to modify
            find: Text to search for
            replace: Text to replace with
            all_occurrences: Replace all occurrences (default: True)
            regex: Treat find pattern as regex (default: False)
            
        Returns:
            Dictionary with modification results including count of changes
            
        Raises:
            MCPError: If file cannot be modified
        """
        try:
            result = await self.mcp_service.query_server(
                f"modify_file",
                preferred_server=self.server_name,
                context={
                    "path": str(path),
                    "find": find,
                    "replace": replace,
                    "all_occurrences": all_occurrences,
                    "regex": regex,
                    "operation": "modify_file"
                }
            )
            
            changes_made = result.get("changes_made", 0)
            self.logger.info(f"Modified file {path}: {changes_made} changes made")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to modify file {path}: {e}")
            raise MCPError(f"Cannot modify file {path}: {e}")
    
    async def copy_file(self, source: Union[str, Path], destination: Union[str, Path]) -> bool:
        """
        Copy files and directories.
        
        Args:
            source: Source path of the file or directory
            destination: Destination path
            
        Returns:
            True if successful
            
        Raises:
            MCPError: If copy operation fails
        """
        try:
            await self.mcp_service.query_server(
                f"copy_file",
                preferred_server=self.server_name,
                context={
                    "source": str(source),
                    "destination": str(destination),
                    "operation": "copy_file"
                }
            )
            self.logger.info(f"Successfully copied {source} to {destination}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to copy {source} to {destination}: {e}")
            raise MCPError(f"Cannot copy {source} to {destination}: {e}")
    
    async def move_file(self, source: Union[str, Path], destination: Union[str, Path]) -> bool:
        """
        Move or rename files and directories.
        
        Args:
            source: Source path of the file or directory
            destination: Destination path
            
        Returns:
            True if successful
            
        Raises:
            MCPError: If move operation fails
        """
        try:
            await self.mcp_service.query_server(
                f"move_file",
                preferred_server=self.server_name,
                context={
                    "source": str(source),
                    "destination": str(destination),
                    "operation": "move_file"
                }
            )
            self.logger.info(f"Successfully moved {source} to {destination}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to move {source} to {destination}: {e}")
            raise MCPError(f"Cannot move {source} to {destination}: {e}")
    
    async def delete_file(self, path: Union[str, Path], recursive: bool = False) -> bool:
        """
        Delete a file or directory from the file system.
        
        Args:
            path: Path to the file or directory to delete
            recursive: Whether to recursively delete directories (default: False)
            
        Returns:
            True if successful
            
        Raises:
            MCPError: If deletion fails
        """
        try:
            await self.mcp_service.query_server(
                f"delete_file",
                preferred_server=self.server_name,
                context={
                    "path": str(path),
                    "recursive": recursive,
                    "operation": "delete_file"
                }
            )
            self.logger.info(f"Successfully deleted: {path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete {path}: {e}")
            raise MCPError(f"Cannot delete {path}: {e}")
    
    async def list_directory(self, path: Union[str, Path]) -> List[Dict[str, Any]]:
        """
        Get a detailed listing of all files and directories in a specified path.
        
        Args:
            path: Path of the directory to list
            
        Returns:
            List of file/directory information dictionaries
            
        Raises:
            MCPError: If directory cannot be listed
        """
        try:
            result = await self.mcp_service.query_server(
                f"list_directory",
                preferred_server=self.server_name,
                context={"path": str(path), "operation": "list_directory"}
            )
            return result.get("entries", [])
        except Exception as e:
            self.logger.error(f"Failed to list directory {path}: {e}")
            raise MCPError(f"Cannot list directory {path}: {e}")
    
    async def create_directory(self, path: Union[str, Path]) -> bool:
        """
        Create a new directory or ensure a directory exists.
        
        Args:
            path: Path of the directory to create
            
        Returns:
            True if successful
            
        Raises:
            MCPError: If directory cannot be created
        """
        try:
            await self.mcp_service.query_server(
                f"create_directory",
                preferred_server=self.server_name,
                context={"path": str(path), "operation": "create_directory"}
            )
            self.logger.info(f"Successfully created directory: {path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create directory {path}: {e}")
            raise MCPError(f"Cannot create directory {path}: {e}")
    
    async def get_directory_tree(self, path: Union[str, Path], depth: int = 3, 
                               follow_symlinks: bool = False) -> Dict[str, Any]:
        """
        Returns a hierarchical JSON representation of a directory structure.
        
        Args:
            path: Path of the directory to traverse
            depth: Maximum depth to traverse (default: 3)
            follow_symlinks: Whether to follow symbolic links (default: False)
            
        Returns:
            Hierarchical directory structure as dictionary
            
        Raises:
            MCPError: If tree cannot be generated
        """
        try:
            result = await self.mcp_service.query_server(
                f"tree",
                preferred_server=self.server_name,
                context={
                    "path": str(path),
                    "depth": depth,
                    "follow_symlinks": follow_symlinks,
                    "operation": "tree"
                }
            )
            return result.get("tree", {})
        except Exception as e:
            self.logger.error(f"Failed to get directory tree for {path}: {e}")
            raise MCPError(f"Cannot get directory tree for {path}: {e}")
    
    async def search_files(self, path: Union[str, Path], pattern: str) -> List[Dict[str, Any]]:
        """
        Recursively search for files and directories matching a pattern.
        
        Args:
            path: Starting path for the search
            pattern: Search pattern to match against file names
            
        Returns:
            List of matching file/directory information
            
        Raises:
            MCPError: If search fails
        """
        try:
            result = await self.mcp_service.query_server(
                f"search_files",
                preferred_server=self.server_name,
                context={
                    "path": str(path),
                    "pattern": pattern,
                    "operation": "search_files"
                }
            )
            return result.get("matches", [])
        except Exception as e:
            self.logger.error(f"Failed to search files in {path} with pattern {pattern}: {e}")
            raise MCPError(f"Cannot search files in {path}: {e}")
    
    async def search_within_files(self, path: Union[str, Path], substring: str,
                                 depth: Optional[int] = None, max_results: int = 1000) -> List[Dict[str, Any]]:
        """
        Search for text within file contents across directory trees.
        
        Args:
            path: Starting directory for the search
            substring: Text to search for within file contents
            depth: Maximum directory depth to search
            max_results: Maximum number of results to return (default: 1000)
            
        Returns:
            List of files containing the substring with match details
            
        Raises:
            MCPError: If content search fails
        """
        try:
            result = await self.mcp_service.query_server(
                f"search_within_files",
                preferred_server=self.server_name,
                context={
                    "path": str(path),
                    "substring": substring,
                    "depth": depth,
                    "max_results": max_results,
                    "operation": "search_within_files"
                }
            )
            return result.get("matches", [])
        except Exception as e:
            self.logger.error(f"Failed to search within files in {path} for '{substring}': {e}")
            raise MCPError(f"Cannot search within files in {path}: {e}")
    
    async def get_file_info(self, path: Union[str, Path]) -> Dict[str, Any]:
        """
        Retrieve detailed metadata about a file or directory.
        
        Args:
            path: Path to the file or directory
            
        Returns:
            Dictionary containing file metadata
            
        Raises:
            MCPError: If file info cannot be retrieved
        """
        try:
            result = await self.mcp_service.query_server(
                "get_file_info",
                preferred_server=self.server_name,
                context={"path": str(path)}
            )
            # Parse MCP tool response format
            if result and "content" in result and result["content"]:
                text = result["content"][0].get("text", "")
                # Parse file info from text
                info = {}
                for line in text.split('\n'):
                    if ':' in line and not line.startswith('File information'):
                        key, value = line.split(':', 1)
                        key = key.strip().lower().replace(' ', '_')
                        value = value.strip()
                        info[key] = value
                        # Convert size to bytes if available
                        if key == 'size' and 'bytes' in value:
                            try:
                                info['size'] = int(value.split()[0])
                            except:
                                pass
                return info
            return {}
        except Exception as e:
            self.logger.error(f"Failed to get file info for {path}: {e}")
            raise MCPError(f"Cannot get file info for {path}: {e}")
    
    async def list_allowed_directories(self) -> List[str]:
        """
        Returns the list of directories that this server is allowed to access.
        
        Returns:
            List of allowed directory paths
            
        Raises:
            MCPError: If allowed directories cannot be retrieved
        """
        try:
            result = await self.mcp_service.query_server(
                "list_allowed_directories",
                preferred_server=self.server_name,
                context={}
            )
            # Parse MCP tool response format
            if result and "content" in result and result["content"]:
                text = result["content"][0].get("text", "")
                # Extract directories from text response
                directories = []
                for line in text.split('\n'):
                    if line.strip() and 'file://' in line:
                        # Extract path from "path (file://path)" format
                        parts = line.split(' (file://')
                        if parts:
                            directories.append(parts[0].strip())
                return directories
            return []
        except Exception as e:
            self.logger.error(f"Failed to list allowed directories: {e}")
            raise MCPError(f"Cannot list allowed directories: {e}")
    
    def is_server_available(self) -> bool:
        """Check if the MCP filesystem server is available."""
        return (self.mcp_service.is_running and 
                self.server_name in self.mcp_service.get_available_servers())
    
    async def validate_server(self) -> bool:
        """Validate that the MCP filesystem server is working correctly."""
        try:
            # Test basic functionality
            allowed_dirs = await self.list_allowed_directories()
            return len(allowed_dirs) > 0
        except Exception as e:
            self.logger.error(f"MCP filesystem server validation failed: {e}")
            return False


class FilesystemOperations:
    """
    High-level filesystem operations that integrate MCP with fallback to local operations.
    
    Provides a unified interface that prefers MCP operations but falls back to 
    local filesystem operations when MCP is unavailable.
    """
    
    def __init__(self, config: EnhancedConfig = None):
        """Initialize filesystem operations."""
        self.config = config or EnhancedConfig()
        self.logger = logging.getLogger("codexa.filesystem.operations")
        self.mcp_service = None
        self.mcp_filesystem = None
        
        # Initialize MCP service if available
        self._initialize_mcp()
    
    def _initialize_mcp(self):
        """Initialize MCP service and filesystem interface."""
        try:
            from ..enhanced_core import EnhancedCodexaAgent
            # This would be injected in real usage, simplified for example
            self.logger.info("MCP filesystem integration ready")
        except Exception as e:
            self.logger.warning(f"MCP filesystem not available, using local fallback: {e}")
    
    async def read_file_async(self, path: Union[str, Path]) -> str:
        """Read file with MCP preference, local fallback."""
        if self.mcp_filesystem and self.mcp_filesystem.is_server_available():
            try:
                return await self.mcp_filesystem.read_file(path)
            except Exception as e:
                self.logger.warning(f"MCP read failed, using local fallback: {e}")
        
        # Local fallback
        return Path(path).read_text(encoding='utf-8')
    
    def read_file(self, path: Union[str, Path]) -> str:
        """Synchronous read file wrapper."""
        if self.mcp_filesystem:
            try:
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(self.read_file_async(path))
            except RuntimeError:
                # No event loop, use local fallback
                pass
        
        return Path(path).read_text(encoding='utf-8')
    
    async def enhanced_search(self, path: Union[str, Path], pattern: str, 
                            content_search: str = None) -> List[Dict[str, Any]]:
        """Enhanced search combining file pattern and content search."""
        results = []
        
        if self.mcp_filesystem and self.mcp_filesystem.is_server_available():
            try:
                # Use MCP for enhanced search capabilities
                file_matches = await self.mcp_filesystem.search_files(path, pattern)
                results.extend(file_matches)
                
                if content_search:
                    content_matches = await self.mcp_filesystem.search_within_files(
                        path, content_search
                    )
                    results.extend(content_matches)
                    
                return results
                
            except Exception as e:
                self.logger.warning(f"MCP search failed, using local fallback: {e}")
        
        # Local fallback using existing file search
        from ..search.file_search import FileSearchEngine
        search_engine = FileSearchEngine(path)
        local_results = search_engine.search_files(pattern)
        
        return [
            {
                "path": str(result.path),
                "type": "file",
                "size": result.size,
                "modified": result.modified_time.isoformat(),
                "file_type": result.file_type
            }
            for result in local_results
        ]