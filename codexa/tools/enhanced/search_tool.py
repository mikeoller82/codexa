"""
Search Tool - Handles various search operations for Codexa
"""

import os
import re
import fnmatch
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import sqlite3
import tempfile

from ..base.tool_interface import Tool, ToolResult, ToolContext, ToolStatus


class SearchTool(Tool):
    """Tool for handling search operations across files, content, and metadata"""
    
    def __init__(self):
        super().__init__()
        self.search_history = []
        self.max_history = 100
        self._setup_search_index()
    
    @property
    def name(self) -> str:
        return "search"
    
    @property
    def description(self) -> str:
        return "Handles various search operations including file search, content search, and pattern matching"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def capabilities(self) -> List[str]:
        return [
            "file_search",
            "content_search",
            "pattern_search",
            "regex_search",
            "fuzzy_search",
            "indexed_search",
            "search_history",
            "search_suggestions",
            "multi_type_search",
            "search_filtering",
            "search_ranking"
        ]
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the search request"""
        request_lower = request.lower()
        
        # High confidence for explicit search requests
        if any(word in request_lower for word in [
            'search', 'find', 'locate', 'look for', 'grep',
            'search for', 'find files', 'search content'
        ]):
            return 0.9
            
        # Medium confidence for pattern-like requests
        if any(word in request_lower for word in [
            'pattern', 'match', 'contains', 'filter',
            'regex', 'wildcard', 'glob'
        ]):
            return 0.6
            
        # Lower confidence for general queries
        if any(word in request_lower for word in [
            'where', 'which', 'show', 'list'
        ]):
            return 0.3
            
        return 0.0
    
    def execute(self, request: str, context: ToolContext) -> ToolResult:
        """Execute search operation based on request"""
        try:
            search_params = self._parse_search_request(request)
            
            # Route to appropriate search handler
            search_type = search_params.get('type', 'content')
            
            handlers = {
                'file': self._file_search,
                'content': self._content_search,
                'pattern': self._pattern_search,
                'regex': self._regex_search,
                'fuzzy': self._fuzzy_search,
                'indexed': self._indexed_search,
                'history': self._search_history_handler
            }
            
            if search_type not in handlers:
                return ToolResult(
                    success=False,
                    data={'error': f'Unknown search type: {search_type}'},
                    message=f"Search type '{search_type}' not supported",
                    status=ToolStatus.ERROR
                )
            
            result = handlers[search_type](search_params, context)
            
            # Add to search history
            self._add_to_history(search_params)
            
            return ToolResult(
                success=True,
                data=result,
                message=f"{search_type.title()} search completed",
                status=ToolStatus.SUCCESS
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                data={'error': str(e)},
                message=f"Search operation failed: {str(e)}",
                status=ToolStatus.ERROR
            )
    
    def _parse_search_request(self, request: str) -> Dict[str, Any]:
        """Parse search request to extract parameters"""
        request_lower = request.lower()
        params = {
            'type': 'content',  # default
            'query': '',
            'path': '.',
            'extensions': [],
            'exclude_patterns': [],
            'case_sensitive': False,
            'whole_word': False,
            'regex': False,
            'max_results': 100,
            'recursive': True
        }
        
        # Determine search type
        if any(word in request_lower for word in ['file search', 'find files', 'search files']):
            params['type'] = 'file'
        elif any(word in request_lower for word in ['content search', 'search content', 'grep']):
            params['type'] = 'content'
        elif 'pattern' in request_lower:
            params['type'] = 'pattern'
        elif 'regex' in request_lower:
            params['type'] = 'regex'
            params['regex'] = True
        elif 'fuzzy' in request_lower:
            params['type'] = 'fuzzy'
        elif 'history' in request_lower:
            params['type'] = 'history'
        
        # Extract search query
        query_patterns = [
            r'search for ["\']([^"\']+)["\']',
            r'find ["\']([^"\']+)["\']',
            r'look for ["\']([^"\']+)["\']',
            r'search ["\']([^"\']+)["\']',
            r'grep ["\']([^"\']+)["\']',
        ]
        
        for pattern in query_patterns:
            match = re.search(pattern, request, re.IGNORECASE)
            if match:
                params['query'] = match.group(1)
                break
        
        # If no quoted query found, try to extract from context
        if not params['query']:
            # Simple heuristic: take words after search terms
            for search_word in ['search', 'find', 'grep', 'look for']:
                if search_word in request_lower:
                    parts = request.split(search_word, 1)
                    if len(parts) > 1:
                        remaining = parts[1].strip()
                        # Take first meaningful part (not flags)
                        words = remaining.split()
                        if words and not words[0].startswith('-'):
                            params['query'] = words[0]
                        break
        
        # Extract path if specified
        path_match = re.search(r'in ["\']([^"\']+)["\']', request, re.IGNORECASE)
        if path_match:
            params['path'] = path_match.group(1)
        
        # Extract file extensions
        ext_match = re.search(r'\.(\w+) files?', request, re.IGNORECASE)
        if ext_match:
            params['extensions'] = [ext_match.group(1)]
        
        # Extract flags
        if 'case sensitive' in request_lower:
            params['case_sensitive'] = True
        if 'whole word' in request_lower:
            params['whole_word'] = True
        if 'not recursive' in request_lower or 'non-recursive' in request_lower:
            params['recursive'] = False
        
        # Extract max results
        max_match = re.search(r'(?:limit|max|first) (\d+)', request_lower)
        if max_match:
            params['max_results'] = int(max_match.group(1))
        
        return params
    
    def _file_search(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Search for files by name"""
        query = params.get('query', '')
        path = params.get('path', '.')
        extensions = params.get('extensions', [])
        recursive = params.get('recursive', True)
        max_results = params.get('max_results', 100)
        case_sensitive = params.get('case_sensitive', False)
        
        if not query:
            return {'error': 'Search query is required'}
        
        results = []
        search_pattern = query if case_sensitive else query.lower()
        
        try:
            search_path = Path(path).expanduser().resolve()
            
            if recursive:
                pattern = '**/*'
            else:
                pattern = '*'
            
            for file_path in search_path.glob(pattern):
                if len(results) >= max_results:
                    break
                
                if not file_path.is_file():
                    continue
                
                # Check extension filter
                if extensions and file_path.suffix[1:] not in extensions:
                    continue
                
                # Check name match
                file_name = file_path.name if case_sensitive else file_path.name.lower()
                
                if search_pattern in file_name:
                    results.append({
                        'file': str(file_path),
                        'name': file_path.name,
                        'size': file_path.stat().st_size,
                        'modified': file_path.stat().st_mtime,
                        'match_type': 'name'
                    })
        
        except Exception as e:
            return {'error': f'File search failed: {str(e)}'}
        
        return {
            'search_type': 'file',
            'query': query,
            'path': path,
            'results': results,
            'result_count': len(results),
            'truncated': len(results) >= max_results
        }
    
    def _content_search(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Search for content within files"""
        query = params.get('query', '')
        path = params.get('path', '.')
        extensions = params.get('extensions', [])
        recursive = params.get('recursive', True)
        max_results = params.get('max_results', 100)
        case_sensitive = params.get('case_sensitive', False)
        whole_word = params.get('whole_word', False)
        
        if not query:
            return {'error': 'Search query is required'}
        
        results = []
        
        try:
            search_path = Path(path).expanduser().resolve()
            
            if recursive:
                pattern = '**/*'
            else:
                pattern = '*'
            
            # Compile search pattern
            flags = 0 if case_sensitive else re.IGNORECASE
            if whole_word:
                search_regex = re.compile(r'\b' + re.escape(query) + r'\b', flags)
            else:
                search_regex = re.compile(re.escape(query), flags)
            
            for file_path in search_path.glob(pattern):
                if len(results) >= max_results:
                    break
                
                if not file_path.is_file():
                    continue
                
                # Check extension filter
                if extensions and file_path.suffix[1:] not in extensions:
                    continue
                
                # Skip binary files
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except (UnicodeDecodeError, PermissionError):
                    continue
                
                # Search content
                matches = []
                for line_num, line in enumerate(content.splitlines(), 1):
                    if search_regex.search(line):
                        matches.append({
                            'line_number': line_num,
                            'line_content': line.strip(),
                            'match_positions': [m.span() for m in search_regex.finditer(line)]
                        })
                
                if matches:
                    results.append({
                        'file': str(file_path),
                        'name': file_path.name,
                        'matches': matches,
                        'match_count': len(matches)
                    })
        
        except Exception as e:
            return {'error': f'Content search failed: {str(e)}'}
        
        return {
            'search_type': 'content',
            'query': query,
            'path': path,
            'results': results,
            'result_count': len(results),
            'total_matches': sum(r['match_count'] for r in results),
            'truncated': len(results) >= max_results
        }
    
    def _pattern_search(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Search using glob patterns"""
        query = params.get('query', '')
        path = params.get('path', '.')
        recursive = params.get('recursive', True)
        max_results = params.get('max_results', 100)
        
        if not query:
            return {'error': 'Search pattern is required'}
        
        results = []
        
        try:
            search_path = Path(path).expanduser().resolve()
            
            if recursive and '**' not in query:
                search_pattern = f'**/{query}'
            else:
                search_pattern = query
            
            for file_path in search_path.glob(search_pattern):
                if len(results) >= max_results:
                    break
                
                results.append({
                    'file': str(file_path),
                    'name': file_path.name,
                    'type': 'directory' if file_path.is_dir() else 'file',
                    'size': file_path.stat().st_size if file_path.is_file() else None,
                    'modified': file_path.stat().st_mtime
                })
        
        except Exception as e:
            return {'error': f'Pattern search failed: {str(e)}'}
        
        return {
            'search_type': 'pattern',
            'pattern': query,
            'path': path,
            'results': results,
            'result_count': len(results),
            'truncated': len(results) >= max_results
        }
    
    def _regex_search(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Search using regular expressions"""
        query = params.get('query', '')
        path = params.get('path', '.')
        extensions = params.get('extensions', [])
        recursive = params.get('recursive', True)
        max_results = params.get('max_results', 100)
        case_sensitive = params.get('case_sensitive', False)
        
        if not query:
            return {'error': 'Regex pattern is required'}
        
        results = []
        
        try:
            search_path = Path(path).expanduser().resolve()
            
            # Compile regex
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                search_regex = re.compile(query, flags)
            except re.error as e:
                return {'error': f'Invalid regex pattern: {str(e)}'}
            
            if recursive:
                pattern = '**/*'
            else:
                pattern = '*'
            
            for file_path in search_path.glob(pattern):
                if len(results) >= max_results:
                    break
                
                if not file_path.is_file():
                    continue
                
                # Check extension filter
                if extensions and file_path.suffix[1:] not in extensions:
                    continue
                
                # Skip binary files
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except (UnicodeDecodeError, PermissionError):
                    continue
                
                # Search content
                matches = []
                for line_num, line in enumerate(content.splitlines(), 1):
                    regex_matches = list(search_regex.finditer(line))
                    if regex_matches:
                        matches.append({
                            'line_number': line_num,
                            'line_content': line.strip(),
                            'matches': [{
                                'match': m.group(),
                                'start': m.start(),
                                'end': m.end(),
                                'groups': m.groups()
                            } for m in regex_matches]
                        })
                
                if matches:
                    results.append({
                        'file': str(file_path),
                        'name': file_path.name,
                        'matches': matches,
                        'match_count': sum(len(m['matches']) for m in matches)
                    })
        
        except Exception as e:
            return {'error': f'Regex search failed: {str(e)}'}
        
        return {
            'search_type': 'regex',
            'pattern': query,
            'path': path,
            'results': results,
            'result_count': len(results),
            'total_matches': sum(r['match_count'] for r in results),
            'truncated': len(results) >= max_results
        }
    
    def _fuzzy_search(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Fuzzy search implementation"""
        query = params.get('query', '')
        path = params.get('path', '.')
        max_results = params.get('max_results', 100)
        
        if not query:
            return {'error': 'Fuzzy search query is required'}
        
        # Simple fuzzy search using Levenshtein-like scoring
        def fuzzy_score(text, query):
            """Simple fuzzy matching score"""
            text_lower = text.lower()
            query_lower = query.lower()
            
            if query_lower in text_lower:
                return 1.0  # Exact substring match
            
            # Character-by-character matching
            score = 0
            text_idx = 0
            
            for char in query_lower:
                while text_idx < len(text_lower) and text_lower[text_idx] != char:
                    text_idx += 1
                if text_idx < len(text_lower):
                    score += 1
                    text_idx += 1
            
            return score / len(query)
        
        results = []
        
        try:
            search_path = Path(path).expanduser().resolve()
            
            candidates = []
            for file_path in search_path.rglob('*'):
                if file_path.is_file():
                    score = fuzzy_score(file_path.name, query)
                    if score > 0.3:  # Minimum threshold
                        candidates.append({
                            'file': str(file_path),
                            'name': file_path.name,
                            'score': score,
                            'size': file_path.stat().st_size,
                            'modified': file_path.stat().st_mtime
                        })
            
            # Sort by score and take top results
            candidates.sort(key=lambda x: x['score'], reverse=True)
            results = candidates[:max_results]
        
        except Exception as e:
            return {'error': f'Fuzzy search failed: {str(e)}'}
        
        return {
            'search_type': 'fuzzy',
            'query': query,
            'path': path,
            'results': results,
            'result_count': len(results)
        }
    
    def _indexed_search(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Search using index (placeholder for future implementation)"""
        return {
            'search_type': 'indexed',
            'status': 'not_implemented',
            'message': 'Indexed search requires building and maintaining search indices'
        }
    
    def _search_history_handler(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Handle search history requests"""
        return {
            'search_history': self.search_history[-10:],  # Last 10 searches
            'total_searches': len(self.search_history)
        }
    
    def _setup_search_index(self):
        """Setup search indexing (placeholder)"""
        # Future: implement search indexing for faster searches
        pass
    
    def _add_to_history(self, search_params: Dict[str, Any]):
        """Add search to history"""
        import time
        
        history_entry = {
            'timestamp': time.time(),
            'search_type': search_params.get('type'),
            'query': search_params.get('query'),
            'path': search_params.get('path')
        }
        
        self.search_history.append(history_entry)
        
        # Keep history size manageable
        if len(self.search_history) > self.max_history:
            self.search_history = self.search_history[-self.max_history:]
    
    def get_status(self) -> Dict[str, Any]:
        """Get search tool status"""
        return {
            'tool_name': self.name,
            'version': self.version,
            'capabilities': self.capabilities,
            'search_history_count': len(self.search_history),
            'max_history': self.max_history
        }