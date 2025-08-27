"""
Unified search manager that coordinates file search, code search, and pattern matching.
"""

from pathlib import Path
from typing import List, Dict, Optional, Union, Set, Any
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import threading
from datetime import datetime

from .file_search import FileSearchEngine, SearchResult
from .code_search import CodeSearchEngine, CodeMatch, SearchMode
from .pattern_matcher import PatternMatcher, PatternType

class SearchType(Enum):
    """Types of searches available."""
    FILES = "files"
    CODE = "code"
    FUNCTIONS = "functions"
    CLASSES = "classes"
    IMPORTS = "imports"
    TODOS = "todos"
    URLS = "urls"
    SECURITY_RISKS = "security_risks"
    DUPLICATES = "duplicates"
    MIXED = "mixed"

@dataclass
class UnifiedSearchResult:
    """Unified result that can contain different types of search matches."""
    search_type: SearchType
    query: str
    total_matches: int
    execution_time: float
    file_matches: List[SearchResult] = field(default_factory=list)
    code_matches: List[CodeMatch] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class SearchManager:
    """Unified search manager providing high-level search operations."""
    
    def __init__(self, base_path: Union[str, Path] = None):
        """Initialize the search manager."""
        self.base_path = Path(base_path) if base_path else Path.cwd()
        
        # Initialize search engines
        self.file_engine = FileSearchEngine(self.base_path)
        self.code_engine = CodeSearchEngine(self.base_path)
        self.pattern_matcher = PatternMatcher()
        
        self._lock = threading.RLock()
        self.search_history: List[UnifiedSearchResult] = []
        
    def search(self, 
               query: str,
               search_type: SearchType = SearchType.MIXED,
               **kwargs) -> UnifiedSearchResult:
        """
        Perform a unified search operation.
        
        Args:
            query: Search query
            search_type: Type of search to perform
            **kwargs: Additional search parameters
            
        Returns:
            UnifiedSearchResult with all matching results
        """
        start_time = datetime.now()
        
        result = UnifiedSearchResult(
            search_type=search_type,
            query=query,
            total_matches=0,
            execution_time=0.0
        )
        
        try:
            if search_type == SearchType.FILES or search_type == SearchType.MIXED:
                file_results = self._search_files(query, kwargs)
                result.file_matches = file_results
                result.total_matches += len(file_results)
            
            if search_type == SearchType.CODE or search_type == SearchType.MIXED:
                code_results = self._search_code(query, kwargs)
                result.code_matches = code_results
                result.total_matches += len(code_results)
            
            if search_type == SearchType.FUNCTIONS:
                function_results = self._search_functions(query, kwargs)
                result.code_matches = function_results
                result.total_matches += len(function_results)
            
            if search_type == SearchType.CLASSES:
                class_results = self._search_classes(query, kwargs)
                result.code_matches = class_results
                result.total_matches += len(class_results)
            
            if search_type == SearchType.IMPORTS:
                import_results = self._search_imports(query, kwargs)
                result.code_matches = import_results
                result.total_matches += len(import_results)
            
            if search_type == SearchType.TODOS:
                todo_results = self._search_todos()
                result.code_matches = todo_results
                result.total_matches += len(todo_results)
            
            if search_type == SearchType.URLS:
                url_results = self._search_urls()
                result.code_matches = url_results
                result.total_matches += len(url_results)
            
            if search_type == SearchType.SECURITY_RISKS:
                security_results = self._search_security_risks()
                result.code_matches = security_results
                result.total_matches += len(security_results)
            
            if search_type == SearchType.DUPLICATES:
                duplicate_results = self._search_duplicates(kwargs)
                result.metadata['duplicates'] = duplicate_results
                result.total_matches += len(duplicate_results)
        
        except Exception as e:
            result.metadata['error'] = str(e)
        
        finally:
            end_time = datetime.now()
            result.execution_time = (end_time - start_time).total_seconds()
            
            # Add to search history
            with self._lock:
                self.search_history.append(result)
                # Keep only last 100 searches
                if len(self.search_history) > 100:
                    self.search_history.pop(0)
        
        return result

    def quick_search(self, query: str, max_results: int = 50) -> UnifiedSearchResult:
        """
        Perform a quick search across files and code with limited results.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            UnifiedSearchResult with quick search results
        """
        return self.search(
            query,
            SearchType.MIXED,
            max_matches=max_results // 2,  # Split between file and code results
            context_lines=1,  # Minimal context for speed
            case_sensitive=False
        )

    def deep_search(self, query: str) -> UnifiedSearchResult:
        """
        Perform a comprehensive deep search with full context and analysis.
        
        Args:
            query: Search query
            
        Returns:
            UnifiedSearchResult with comprehensive results
        """
        return self.search(
            query,
            SearchType.MIXED,
            max_matches=1000,
            context_lines=3,
            include_hidden=True,
            case_sensitive=False
        )

    def find_file(self, name: str, exact_match: bool = False) -> List[SearchResult]:
        """Find files by name."""
        return self.file_engine.find_by_name(name, exact_match=exact_match)

    def find_by_extension(self, extensions: Union[str, List[str]]) -> List[SearchResult]:
        """Find files by extension."""
        return self.file_engine.find_by_extension(extensions)

    def find_recent_files(self, hours: int = 24) -> List[SearchResult]:
        """Find recently modified files."""
        return self.file_engine.find_recent_files(hours)

    def find_large_files(self, min_size_mb: int = 1) -> List[SearchResult]:
        """Find large files."""
        min_size_bytes = min_size_mb * 1024 * 1024
        return self.file_engine.find_by_size(min_size=min_size_bytes)

    def find_functions(self, name_pattern: str = None, language: str = None) -> List[CodeMatch]:
        """Find function definitions."""
        return self.code_engine.search_functions(name_pattern, language=language)

    def find_classes(self, name_pattern: str = None, language: str = None) -> List[CodeMatch]:
        """Find class definitions."""
        return self.code_engine.search_classes(name_pattern, language=language)

    def find_imports(self, pattern: str = None) -> List[CodeMatch]:
        """Find import statements."""
        return self.code_engine.search_imports(pattern)

    def find_todos(self) -> List[CodeMatch]:
        """Find TODO, FIXME, and similar comments."""
        return self.code_engine.search_todos()

    def find_security_risks(self) -> List[CodeMatch]:
        """Find potential security risks."""
        return self.code_engine.search_secrets_risk()

    def find_duplicates(self, min_lines: int = 5) -> List[Dict]:
        """Find duplicate code blocks."""
        return self.code_engine.find_duplicates(min_lines)

    def get_project_overview(self) -> Dict[str, Any]:
        """Get a comprehensive overview of the project."""
        overview = {}
        
        try:
            # File statistics
            all_files = self.file_engine.search_files("**/*")
            overview['total_files'] = len(all_files)
            
            # Group by file type
            file_types = {}
            total_size = 0
            for file_result in all_files:
                file_type = file_result.file_type
                if file_type not in file_types:
                    file_types[file_type] = {'count': 0, 'size': 0}
                file_types[file_type]['count'] += 1
                file_types[file_type]['size'] += file_result.size
                total_size += file_result.size
            
            overview['file_types'] = file_types
            overview['total_size'] = total_size
            
            # Code statistics
            functions = self.code_engine.search_functions()
            classes = self.code_engine.search_classes()
            imports = self.code_engine.search_imports()
            todos = self.code_engine.search_todos()
            
            overview['code_stats'] = {
                'functions': len(functions),
                'classes': len(classes),
                'imports': len(imports),
                'todos': len(todos)
            }
            
            # Recent activity
            recent_files = self.file_engine.find_recent_files(hours=24)
            overview['recent_files'] = len(recent_files)
            
            # Project structure
            structure = self.file_engine.get_project_structure(max_depth=2)
            overview['structure_overview'] = {
                'directories': len([k for k, v in structure.items() if v['type'] == 'directory']),
                'max_depth_files': len([k for k, v in structure.items() if v['type'] == 'file'])
            }
            
        except Exception as e:
            overview['error'] = str(e)
        
        return overview

    def get_search_suggestions(self, partial_query: str) -> List[str]:
        """Get search suggestions based on partial query."""
        suggestions = []
        
        # Common search patterns
        common_patterns = [
            "TODO", "FIXME", "HACK", "BUG", "NOTE",
            "def ", "class ", "import ", "from ",
            "function ", "const ", "var ", "let ",
            "http://", "https://", "api_key", "password"
        ]
        
        # File extensions
        common_extensions = [
            "*.py", "*.js", "*.ts", "*.jsx", "*.tsx",
            "*.html", "*.css", "*.json", "*.md", "*.yml"
        ]
        
        # Add matching suggestions
        query_lower = partial_query.lower()
        
        for pattern in common_patterns:
            if pattern.lower().startswith(query_lower):
                suggestions.append(pattern)
        
        for ext in common_extensions:
            if ext.lower().startswith(query_lower):
                suggestions.append(ext)
        
        # Add suggestions from search history
        with self._lock:
            for result in reversed(self.search_history[-10:]):  # Last 10 searches
                if result.query.lower().startswith(query_lower) and result.query not in suggestions:
                    suggestions.append(result.query)
        
        return suggestions[:10]  # Limit to 10 suggestions

    def get_search_history(self) -> List[UnifiedSearchResult]:
        """Get search history."""
        with self._lock:
            return self.search_history.copy()

    def clear_search_history(self):
        """Clear search history."""
        with self._lock:
            self.search_history.clear()

    def export_results(self, result: UnifiedSearchResult, format: str = "json") -> str:
        """Export search results in specified format."""
        if format == "json":
            import json
            export_data = {
                'search_type': result.search_type.value,
                'query': result.query,
                'total_matches': result.total_matches,
                'execution_time': result.execution_time,
                'timestamp': datetime.now().isoformat(),
                'file_matches': [
                    {
                        'path': str(match.relative_path),
                        'size': match.size,
                        'type': match.file_type,
                        'modified': match.modified_time.isoformat()
                    }
                    for match in result.file_matches
                ],
                'code_matches': [
                    {
                        'file': str(match.file_path.relative_to(self.base_path)),
                        'line': match.line_number,
                        'content': match.line_content,
                        'match': match.match_text,
                        'type': match.match_type.value
                    }
                    for match in result.code_matches
                ]
            }
            return json.dumps(export_data, indent=2)
        
        elif format == "csv":
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(['Type', 'File', 'Line', 'Content', 'Match'])
            
            # Write file matches
            for match in result.file_matches:
                writer.writerow(['file', str(match.relative_path), '', '', match.file_type])
            
            # Write code matches
            for match in result.code_matches:
                writer.writerow([
                    'code', 
                    str(match.file_path.relative_to(self.base_path)),
                    match.line_number,
                    match.line_content[:100],  # Truncate long lines
                    match.match_text
                ])
            
            return output.getvalue()
        
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _search_files(self, query: str, kwargs: Dict) -> List[SearchResult]:
        """Internal method to search files."""
        return self.file_engine.search_files(
            pattern=kwargs.get('pattern', query),
            ignore_patterns=kwargs.get('ignore_patterns'),
            file_types=kwargs.get('file_types'),
            max_depth=kwargs.get('max_depth'),
            include_hidden=kwargs.get('include_hidden', False),
            sort_by=kwargs.get('sort_by', 'modified')
        )

    def _search_code(self, query: str, kwargs: Dict) -> List[CodeMatch]:
        """Internal method to search code."""
        mode = SearchMode.LITERAL
        if kwargs.get('use_regex'):
            mode = SearchMode.REGEX
        elif kwargs.get('fuzzy'):
            mode = SearchMode.FUZZY
        
        return self.code_engine.search_code(
            pattern=query,
            mode=mode,
            context_lines=kwargs.get('context_lines', 2),
            case_sensitive=kwargs.get('case_sensitive', True),
            whole_words=kwargs.get('whole_words', False),
            max_matches=kwargs.get('max_matches', 100)
        )

    def _search_functions(self, query: str, kwargs: Dict) -> List[CodeMatch]:
        """Internal method to search functions."""
        return self.code_engine.search_functions(
            name_pattern=query,
            language=kwargs.get('language')
        )

    def _search_classes(self, query: str, kwargs: Dict) -> List[CodeMatch]:
        """Internal method to search classes."""
        return self.code_engine.search_classes(
            name_pattern=query,
            language=kwargs.get('language')
        )

    def _search_imports(self, query: str, kwargs: Dict) -> List[CodeMatch]:
        """Internal method to search imports."""
        return self.code_engine.search_imports(pattern=query)

    def _search_todos(self) -> List[CodeMatch]:
        """Internal method to search TODOs."""
        return self.code_engine.search_todos()

    def _search_urls(self) -> List[CodeMatch]:
        """Internal method to search URLs."""
        return self.code_engine.search_urls()

    def _search_security_risks(self) -> List[CodeMatch]:
        """Internal method to search security risks."""
        return self.code_engine.search_secrets_risk()

    def _search_duplicates(self, kwargs: Dict) -> List[Dict]:
        """Internal method to search duplicates."""
        return self.code_engine.find_duplicates(
            min_lines=kwargs.get('min_lines', 5)
        )