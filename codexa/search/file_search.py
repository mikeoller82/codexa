"""
File system search engine for Codexa with glob patterns and intelligent filtering.
"""

import os
import fnmatch
import re
from pathlib import Path
from typing import List, Dict, Optional, Union, Pattern, Iterator
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

@dataclass
class SearchResult:
    """Represents a file search result."""
    path: Path
    relative_path: str
    size: int
    modified_time: datetime
    file_type: str
    match_score: float = 0.0
    match_context: Dict = field(default_factory=dict)

class FileSearchEngine:
    """High-performance file search engine with glob patterns and intelligent filtering."""
    
    def __init__(self, base_path: Union[str, Path] = None):
        """Initialize the file search engine."""
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.max_workers = min(32, (os.cpu_count() or 1) + 4)
        self._lock = threading.RLock()
        
        # Default ignore patterns (similar to gitignore)
        self.default_ignore_patterns = {
            # Version control
            '.git/**', '.svn/**', '.hg/**', '.bzr/**',
            # Dependencies
            'node_modules/**', 'venv/**', 'env/**', '.env/**',
            'vendor/**', 'target/**', 'build/**', 'dist/**',
            '__pycache__/**', '.pytest_cache/**', '.tox/**',
            # IDE/Editor
            '.vscode/**', '.idea/**', '*.swp', '*.swo', '*~',
            '.DS_Store', 'Thumbs.db',
            # Temporary files
            '*.tmp', '*.temp', '*.log', '*.pid', '*.lock',
            # Compiled files
            '*.pyc', '*.pyo', '*.class', '*.o', '*.so',
            '*.dylib', '*.dll', '*.exe',
        }
        
        # File type mappings
        self.file_types = {
            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
            '.jsx': 'react', '.tsx': 'typescript-react', '.vue': 'vue',
            '.html': 'html', '.css': 'css', '.scss': 'scss', '.sass': 'sass',
            '.json': 'json', '.yaml': 'yaml', '.yml': 'yaml', '.toml': 'toml',
            '.md': 'markdown', '.rst': 'restructuredtext', '.txt': 'text',
            '.sh': 'shell', '.bash': 'bash', '.zsh': 'zsh', '.fish': 'fish',
            '.go': 'go', '.rs': 'rust', '.java': 'java', '.cpp': 'cpp',
            '.c': 'c', '.h': 'header', '.hpp': 'cpp-header',
            '.php': 'php', '.rb': 'ruby', '.pl': 'perl', '.swift': 'swift',
            '.kt': 'kotlin', '.scala': 'scala', '.clj': 'clojure',
            '.xml': 'xml', '.csv': 'csv', '.sql': 'sql'
        }

    def search_files(self, 
                    pattern: str = "*",
                    path: Union[str, Path] = None,
                    ignore_patterns: List[str] = None,
                    file_types: List[str] = None,
                    max_depth: int = None,
                    include_hidden: bool = False,
                    sort_by: str = "name") -> List[SearchResult]:
        """
        Search for files using glob patterns with advanced filtering.
        
        Args:
            pattern: Glob pattern to match files (e.g., "*.py", "**/*.js")
            path: Directory to search in (defaults to base_path)
            ignore_patterns: Additional patterns to ignore
            file_types: Filter by file types (e.g., ["python", "javascript"])
            max_depth: Maximum directory depth to search
            include_hidden: Include hidden files/directories
            sort_by: Sort results by "name", "size", "modified", "type"
            
        Returns:
            List of SearchResult objects sorted by modification time (newest first)
        """
        search_path = Path(path) if path else self.base_path
        
        if not search_path.exists():
            raise FileNotFoundError(f"Search path does not exist: {search_path}")
        
        # Combine ignore patterns
        all_ignore_patterns = set(self.default_ignore_patterns)
        if ignore_patterns:
            all_ignore_patterns.update(ignore_patterns)
        
        results = []
        
        try:
            # Use parallel processing for large directory structures
            if self._should_use_parallel_search(search_path):
                results = self._parallel_search(
                    pattern, search_path, all_ignore_patterns,
                    file_types, max_depth, include_hidden
                )
            else:
                results = self._sequential_search(
                    pattern, search_path, all_ignore_patterns,
                    file_types, max_depth, include_hidden
                )
            
            # Sort results
            results = self._sort_results(results, sort_by)
            
        except Exception as e:
            raise RuntimeError(f"Search failed: {e}")
        
        return results

    def find_by_name(self, 
                    name: str, 
                    exact_match: bool = False,
                    case_sensitive: bool = False) -> List[SearchResult]:
        """Find files by exact or partial name match."""
        if exact_match:
            if case_sensitive:
                pattern = name
            else:
                pattern = f"**/{name}"
        else:
            if case_sensitive:
                pattern = f"**/*{name}*"
            else:
                pattern = f"**/*{name.lower()}*"
        
        results = self.search_files(pattern)
        
        if not case_sensitive and not exact_match:
            # Filter results for case-insensitive partial matching
            filtered_results = []
            name_lower = name.lower()
            for result in results:
                if name_lower in result.path.name.lower():
                    result.match_score = self._calculate_name_match_score(
                        result.path.name, name
                    )
                    filtered_results.append(result)
            results = sorted(filtered_results, key=lambda x: x.match_score, reverse=True)
        
        return results

    def find_by_extension(self, 
                         extensions: Union[str, List[str]],
                         path: Union[str, Path] = None) -> List[SearchResult]:
        """Find files by file extension(s)."""
        if isinstance(extensions, str):
            extensions = [extensions]
        
        # Normalize extensions
        normalized_exts = []
        for ext in extensions:
            if not ext.startswith('.'):
                ext = '.' + ext
            normalized_exts.append(ext.lower())
        
        # Create glob pattern
        if len(normalized_exts) == 1:
            pattern = f"**/*{normalized_exts[0]}"
        else:
            # Multiple extensions - we'll filter after glob search
            pattern = "**/*.*"
        
        results = self.search_files(pattern, path)
        
        if len(normalized_exts) > 1:
            # Filter for multiple extensions
            filtered_results = []
            for result in results:
                if result.path.suffix.lower() in normalized_exts:
                    filtered_results.append(result)
            results = filtered_results
        
        return results

    def find_by_size(self, 
                    min_size: int = None,
                    max_size: int = None,
                    path: Union[str, Path] = None) -> List[SearchResult]:
        """Find files by size range (in bytes)."""
        results = self.search_files("**/*", path)
        
        filtered_results = []
        for result in results:
            if min_size is not None and result.size < min_size:
                continue
            if max_size is not None and result.size > max_size:
                continue
            filtered_results.append(result)
        
        return sorted(filtered_results, key=lambda x: x.size, reverse=True)

    def find_recent_files(self, 
                         hours: int = 24,
                         path: Union[str, Path] = None) -> List[SearchResult]:
        """Find files modified within the last N hours."""
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        results = self.search_files("**/*", path)
        
        recent_files = [
            result for result in results 
            if result.modified_time >= cutoff_time
        ]
        
        return sorted(recent_files, key=lambda x: x.modified_time, reverse=True)

    def get_project_structure(self, 
                            max_depth: int = 3,
                            show_hidden: bool = False) -> Dict:
        """Get a tree structure of the project."""
        structure = {}
        
        def build_tree(path: Path, current_depth: int = 0):
            if max_depth and current_depth >= max_depth:
                return
            
            try:
                items = list(path.iterdir())
                # Sort: directories first, then files
                items.sort(key=lambda x: (x.is_file(), x.name.lower()))
                
                for item in items:
                    if not show_hidden and item.name.startswith('.'):
                        continue
                    
                    if self._should_ignore_path(item):
                        continue
                    
                    item_info = {
                        'type': 'file' if item.is_file() else 'directory',
                        'size': item.stat().st_size if item.is_file() else 0,
                        'modified': datetime.fromtimestamp(item.stat().st_mtime)
                    }
                    
                    if item.is_file():
                        item_info['file_type'] = self._get_file_type(item)
                    
                    relative_path = str(item.relative_to(self.base_path))
                    structure[relative_path] = item_info
                    
                    if item.is_dir():
                        build_tree(item, current_depth + 1)
                        
            except PermissionError:
                pass  # Skip directories we can't read
            except Exception:
                pass  # Skip other errors
        
        build_tree(self.base_path)
        return structure

    def _should_use_parallel_search(self, path: Path) -> bool:
        """Determine if parallel search should be used based on directory size."""
        try:
            # Count immediate subdirectories
            subdirs = sum(1 for item in path.iterdir() if item.is_dir())
            return subdirs > 5  # Use parallel for more than 5 subdirectories
        except:
            return False

    def _parallel_search(self, pattern, search_path, ignore_patterns, 
                        file_types, max_depth, include_hidden) -> List[SearchResult]:
        """Perform parallel file search using ThreadPoolExecutor."""
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit search tasks for each subdirectory
            future_to_path = {}
            
            try:
                for item in search_path.iterdir():
                    if item.is_dir() and not self._should_ignore_path(item, ignore_patterns):
                        future = executor.submit(
                            self._sequential_search,
                            pattern, item, ignore_patterns,
                            file_types, max_depth, include_hidden
                        )
                        future_to_path[future] = item
                
                # Also search files in the root directory
                root_future = executor.submit(
                    self._search_files_in_directory,
                    pattern, search_path, ignore_patterns,
                    file_types, include_hidden, current_depth=0
                )
                future_to_path[root_future] = search_path
                
                # Collect results
                for future in as_completed(future_to_path):
                    try:
                        results.extend(future.result())
                    except Exception as e:
                        # Log error but continue with other results
                        print(f"Search error in {future_to_path[future]}: {e}")
                        
            except Exception as e:
                # Fallback to sequential search on error
                return self._sequential_search(
                    pattern, search_path, ignore_patterns,
                    file_types, max_depth, include_hidden
                )
        
        return results

    def _sequential_search(self, pattern, search_path, ignore_patterns,
                          file_types, max_depth, include_hidden) -> List[SearchResult]:
        """Perform sequential file search."""
        results = []
        
        for root, dirs, files in os.walk(search_path):
            root_path = Path(root)
            current_depth = len(root_path.relative_to(search_path).parts)
            
            # Check max depth
            if max_depth and current_depth >= max_depth:
                dirs.clear()  # Don't recurse deeper
                continue
            
            # Filter directories to skip
            dirs[:] = [
                d for d in dirs
                if (include_hidden or not d.startswith('.')) and
                not self._should_ignore_path(root_path / d, ignore_patterns)
            ]
            
            # Process files in current directory
            for file_name in files:
                if not include_hidden and file_name.startswith('.'):
                    continue
                
                file_path = root_path / file_name
                
                if self._should_ignore_path(file_path, ignore_patterns):
                    continue
                
                if self._matches_pattern(file_name, pattern):
                    result = self._create_search_result(file_path)
                    
                    # Filter by file type if specified
                    if file_types and result.file_type not in file_types:
                        continue
                    
                    results.append(result)
        
        return results

    def _search_files_in_directory(self, pattern, directory, ignore_patterns,
                                  file_types, include_hidden, current_depth=0):
        """Search for files in a single directory (non-recursive)."""
        results = []
        
        try:
            for item in directory.iterdir():
                if item.is_file():
                    if not include_hidden and item.name.startswith('.'):
                        continue
                    
                    if self._should_ignore_path(item, ignore_patterns):
                        continue
                    
                    if self._matches_pattern(item.name, pattern):
                        result = self._create_search_result(item)
                        
                        if file_types and result.file_type not in file_types:
                            continue
                        
                        results.append(result)
        except (PermissionError, OSError):
            pass  # Skip directories we can't read
        
        return results

    def _should_ignore_path(self, path: Path, ignore_patterns: set = None) -> bool:
        """Check if a path should be ignored based on patterns."""
        if ignore_patterns is None:
            ignore_patterns = self.default_ignore_patterns
        
        # Convert to relative path for pattern matching
        try:
            relative_path = str(path.relative_to(self.base_path))
        except ValueError:
            # Path is not relative to base_path
            relative_path = str(path)
        
        for pattern in ignore_patterns:
            if fnmatch.fnmatch(relative_path, pattern) or fnmatch.fnmatch(path.name, pattern):
                return True
        
        return False

    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """Check if a filename matches the given pattern."""
        if pattern == "*" or pattern == "**/*":
            return True
        
        # Handle different pattern types
        if "**/" in pattern:
            # Recursive pattern - just check the filename part
            filename_pattern = pattern.split("**/")[-1]
            return fnmatch.fnmatch(filename, filename_pattern)
        else:
            return fnmatch.fnmatch(filename, pattern)

    def _create_search_result(self, file_path: Path) -> SearchResult:
        """Create a SearchResult object from a file path."""
        try:
            stat_result = file_path.stat()
            relative_path = str(file_path.relative_to(self.base_path))
        except (OSError, ValueError):
            # Fallback if we can't get stats or relative path
            stat_result = None
            relative_path = str(file_path)
        
        return SearchResult(
            path=file_path,
            relative_path=relative_path,
            size=stat_result.st_size if stat_result else 0,
            modified_time=datetime.fromtimestamp(stat_result.st_mtime) if stat_result else datetime.now(),
            file_type=self._get_file_type(file_path)
        )

    def _get_file_type(self, file_path: Path) -> str:
        """Get the file type based on extension."""
        extension = file_path.suffix.lower()
        return self.file_types.get(extension, 'unknown')

    def _calculate_name_match_score(self, filename: str, search_name: str) -> float:
        """Calculate a relevance score for name matching."""
        filename_lower = filename.lower()
        search_lower = search_name.lower()
        
        # Exact match gets highest score
        if filename_lower == search_lower:
            return 1.0
        
        # Starts with search term gets high score
        if filename_lower.startswith(search_lower):
            return 0.9
        
        # Contains search term gets medium score
        if search_lower in filename_lower:
            return 0.7
        
        # Fuzzy matching (simple implementation)
        common_chars = sum(1 for c in search_lower if c in filename_lower)
        return common_chars / len(search_lower) * 0.5

    def _sort_results(self, results: List[SearchResult], sort_by: str) -> List[SearchResult]:
        """Sort search results by specified criteria."""
        if sort_by == "name":
            return sorted(results, key=lambda x: x.path.name.lower())
        elif sort_by == "size":
            return sorted(results, key=lambda x: x.size, reverse=True)
        elif sort_by == "type":
            return sorted(results, key=lambda x: (x.file_type, x.path.name.lower()))
        elif sort_by == "modified":
            return sorted(results, key=lambda x: x.modified_time, reverse=True)
        else:
            # Default: sort by modification time (newest first)
            return sorted(results, key=lambda x: x.modified_time, reverse=True)