"""
Code search engine for Codexa with regex patterns, syntax-aware search, and content analysis.
"""

import re
import os
from pathlib import Path
from typing import List, Dict, Optional, Union, Pattern, Iterator, Set
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from enum import Enum

class SearchMode(Enum):
    """Search modes for different types of searches."""
    LITERAL = "literal"
    REGEX = "regex" 
    FUZZY = "fuzzy"
    SEMANTIC = "semantic"

class MatchType(Enum):
    """Types of code matches."""
    EXACT = "exact"
    FUNCTION_DEF = "function_def"
    CLASS_DEF = "class_def"
    IMPORT = "import"
    VARIABLE = "variable"
    COMMENT = "comment"
    STRING = "string"
    PATTERN = "pattern"

@dataclass
class CodeMatch:
    """Represents a code search match."""
    file_path: Path
    line_number: int
    line_content: str
    match_text: str
    match_type: MatchType
    context_before: List[str] = field(default_factory=list)
    context_after: List[str] = field(default_factory=list)
    column_start: int = 0
    column_end: int = 0
    confidence: float = 1.0
    metadata: Dict = field(default_factory=dict)

class CodeSearchEngine:
    """Advanced code search engine with syntax awareness and intelligent matching."""
    
    def __init__(self, base_path: Union[str, Path] = None):
        """Initialize the code search engine."""
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.max_workers = min(32, (os.cpu_count() or 1) + 4)
        self._lock = threading.RLock()
        
        # File extensions to search by default
        self.default_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.vue', '.html', '.css',
            '.scss', '.sass', '.json', '.yaml', '.yml', '.md', '.rst', '.txt',
            '.sh', '.bash', '.zsh', '.fish', '.go', '.rs', '.java', '.cpp',
            '.c', '.h', '.hpp', '.php', '.rb', '.pl', '.swift', '.kt',
            '.scala', '.clj', '.xml', '.csv', '.sql', '.toml', '.ini'
        }
        
        # Language-specific patterns for better matching
        self.language_patterns = {
            'python': {
                'function': re.compile(r'^(\s*)def\s+(\w+)\s*\('),
                'class': re.compile(r'^(\s*)class\s+(\w+)'),
                'import': re.compile(r'^(\s*)(from\s+\w+\s+)?import\s+(.+)'),
                'comment': re.compile(r'#.*$'),
                'docstring': re.compile(r'""".*?"""', re.DOTALL),
            },
            'javascript': {
                'function': re.compile(r'(function\s+\w+|const\s+\w+\s*=\s*(?:async\s+)?\(|\w+:\s*(?:async\s+)?function)'),
                'class': re.compile(r'class\s+(\w+)'),
                'import': re.compile(r'import\s+.+\s+from\s+["\'].+["\']|require\(["\'].+["\']\)'),
                'comment': re.compile(r'//.*$|/\*.*?\*/', re.DOTALL),
            },
            'typescript': {
                'function': re.compile(r'(function\s+\w+|const\s+\w+\s*=\s*(?:async\s+)?\(|\w+:\s*(?:async\s+)?function|^\s*\w+\s*\()'),
                'class': re.compile(r'class\s+(\w+)'),
                'interface': re.compile(r'interface\s+(\w+)'),
                'type': re.compile(r'type\s+(\w+)\s*='),
                'import': re.compile(r'import\s+.+\s+from\s+["\'].+["\']'),
                'comment': re.compile(r'//.*$|/\*.*?\*/', re.DOTALL),
            },
            'go': {
                'function': re.compile(r'func\s+(\w+)\s*\('),
                'type': re.compile(r'type\s+(\w+)\s+(struct|interface)'),
                'import': re.compile(r'import\s+(\(.*?\)|".*")'),
                'comment': re.compile(r'//.*$|/\*.*?\*/', re.DOTALL),
            },
            'rust': {
                'function': re.compile(r'fn\s+(\w+)\s*\('),
                'struct': re.compile(r'struct\s+(\w+)'),
                'enum': re.compile(r'enum\s+(\w+)'),
                'trait': re.compile(r'trait\s+(\w+)'),
                'impl': re.compile(r'impl\s+.*\s+for\s+(\w+)'),
                'comment': re.compile(r'//.*$|/\*.*?\*/', re.DOTALL),
            }
        }
        
        # Common code patterns (language agnostic)
        self.common_patterns = {
            'todo': re.compile(r'(TODO|FIXME|HACK|BUG|NOTE):', re.IGNORECASE),
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'url': re.compile(r'https?://[^\s<>"{}|\\^`[\]]+'),
            'uuid': re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', re.IGNORECASE),
            'ip_address': re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
            'hex_color': re.compile(r'#[0-9a-fA-F]{3,6}\b'),
        }

    def search_code(self, 
                   pattern: str,
                   mode: SearchMode = SearchMode.LITERAL,
                   file_patterns: List[str] = None,
                   extensions: Set[str] = None,
                   context_lines: int = 2,
                   case_sensitive: bool = False,
                   whole_words: bool = False,
                   max_matches: int = 1000) -> List[CodeMatch]:
        """
        Search for code patterns across files.
        
        Args:
            pattern: Search pattern (literal text, regex, or semantic query)
            mode: Search mode (literal, regex, fuzzy, semantic)
            file_patterns: Glob patterns for files to search
            extensions: File extensions to include
            context_lines: Number of context lines to include
            case_sensitive: Case-sensitive search
            whole_words: Match whole words only
            max_matches: Maximum number of matches to return
            
        Returns:
            List of CodeMatch objects
        """
        if not pattern.strip():
            return []
        
        # Prepare search parameters
        search_extensions = extensions or self.default_extensions
        regex_pattern = self._prepare_search_pattern(pattern, mode, case_sensitive, whole_words)
        
        # Find files to search
        files_to_search = self._find_searchable_files(file_patterns, search_extensions)
        
        if not files_to_search:
            return []
        
        # Perform search
        matches = []
        
        if len(files_to_search) > 10:  # Use parallel search for many files
            matches = self._parallel_code_search(
                files_to_search, regex_pattern, context_lines, max_matches
            )
        else:
            matches = self._sequential_code_search(
                files_to_search, regex_pattern, context_lines, max_matches
            )
        
        # Sort by relevance and file path
        matches = sorted(matches, key=lambda x: (x.file_path, x.line_number))
        
        return matches[:max_matches]

    def search_functions(self, 
                        name_pattern: str = None,
                        content_pattern: str = None,
                        language: str = None) -> List[CodeMatch]:
        """Search for function definitions."""
        matches = []
        
        # Determine which languages to search
        languages = [language] if language else list(self.language_patterns.keys())
        
        for lang in languages:
            if lang in self.language_patterns and 'function' in self.language_patterns[lang]:
                func_regex = self.language_patterns[lang]['function']
                
                # Search for function patterns
                files_to_search = self._find_files_by_language(lang)
                
                for file_path in files_to_search:
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()
                        
                        for i, line in enumerate(lines):
                            func_match = func_regex.search(line)
                            if func_match:
                                # Check if function name matches pattern
                                if name_pattern:
                                    func_name = self._extract_function_name(line, lang)
                                    if not func_name or not re.search(name_pattern, func_name, re.IGNORECASE):
                                        continue
                                
                                # Check if function content matches pattern
                                if content_pattern:
                                    func_content = self._extract_function_content(lines, i, lang)
                                    if not re.search(content_pattern, func_content, re.IGNORECASE):
                                        continue
                                
                                match = CodeMatch(
                                    file_path=file_path,
                                    line_number=i + 1,
                                    line_content=line.rstrip(),
                                    match_text=func_match.group(),
                                    match_type=MatchType.FUNCTION_DEF,
                                    metadata={'language': lang}
                                )
                                matches.append(match)
                    
                    except (OSError, UnicodeDecodeError):
                        continue
        
        return matches

    def search_classes(self, 
                      name_pattern: str = None,
                      content_pattern: str = None,
                      language: str = None) -> List[CodeMatch]:
        """Search for class definitions."""
        matches = []
        
        languages = [language] if language else list(self.language_patterns.keys())
        
        for lang in languages:
            if lang in self.language_patterns and 'class' in self.language_patterns[lang]:
                class_regex = self.language_patterns[lang]['class']
                
                files_to_search = self._find_files_by_language(lang)
                
                for file_path in files_to_search:
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()
                        
                        for i, line in enumerate(lines):
                            class_match = class_regex.search(line)
                            if class_match:
                                if name_pattern:
                                    class_name = class_match.group(1) if class_match.groups() else ""
                                    if not re.search(name_pattern, class_name, re.IGNORECASE):
                                        continue
                                
                                match = CodeMatch(
                                    file_path=file_path,
                                    line_number=i + 1,
                                    line_content=line.rstrip(),
                                    match_text=class_match.group(),
                                    match_type=MatchType.CLASS_DEF,
                                    metadata={'language': lang}
                                )
                                matches.append(match)
                    
                    except (OSError, UnicodeDecodeError):
                        continue
        
        return matches

    def search_imports(self, pattern: str = None) -> List[CodeMatch]:
        """Search for import statements."""
        matches = []
        
        for lang in self.language_patterns.keys():
            if 'import' in self.language_patterns[lang]:
                import_regex = self.language_patterns[lang]['import']
                
                files_to_search = self._find_files_by_language(lang)
                
                for file_path in files_to_search:
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()
                        
                        for i, line in enumerate(lines):
                            import_match = import_regex.search(line)
                            if import_match:
                                if pattern and not re.search(pattern, line, re.IGNORECASE):
                                    continue
                                
                                match = CodeMatch(
                                    file_path=file_path,
                                    line_number=i + 1,
                                    line_content=line.rstrip(),
                                    match_text=import_match.group(),
                                    match_type=MatchType.IMPORT,
                                    metadata={'language': lang}
                                )
                                matches.append(match)
                    
                    except (OSError, UnicodeDecodeError):
                        continue
        
        return matches

    def search_todos(self) -> List[CodeMatch]:
        """Search for TODO, FIXME, HACK, and similar comments."""
        pattern = self.common_patterns['todo']
        return self._search_with_pattern(pattern, MatchType.COMMENT, "TODO/FIXME search")

    def search_urls(self) -> List[CodeMatch]:
        """Search for URLs in code."""
        pattern = self.common_patterns['url']
        return self._search_with_pattern(pattern, MatchType.STRING, "URL search")

    def search_secrets_risk(self) -> List[CodeMatch]:
        """Search for potential security risks like hardcoded secrets."""
        risky_patterns = [
            re.compile(r'(password|pwd|passwd)\s*[:=]\s*["\'][^"\']+["\']', re.IGNORECASE),
            re.compile(r'(api_key|apikey|secret_key)\s*[:=]\s*["\'][^"\']+["\']', re.IGNORECASE),
            re.compile(r'(token|access_token)\s*[:=]\s*["\'][^"\']+["\']', re.IGNORECASE),
            re.compile(r'(private_key|private-key)\s*[:=]', re.IGNORECASE),
            re.compile(r'-----BEGIN [A-Z ]+ KEY-----'),
        ]
        
        matches = []
        for i, pattern in enumerate(risky_patterns):
            pattern_matches = self._search_with_pattern(
                pattern, MatchType.STRING, f"Security risk pattern {i+1}"
            )
            matches.extend(pattern_matches)
        
        return matches

    def find_duplicates(self, min_lines: int = 5) -> List[Dict]:
        """Find duplicate code blocks."""
        # This is a simplified implementation
        # A full implementation would use more sophisticated algorithms
        file_hashes = {}
        duplicates = []
        
        files_to_search = self._find_searchable_files(None, self.default_extensions)
        
        for file_path in files_to_search:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                
                # Create sliding window of lines
                for i in range(len(lines) - min_lines + 1):
                    block = ''.join(lines[i:i + min_lines]).strip()
                    if len(block) > 50:  # Only consider substantial blocks
                        block_hash = hash(block)
                        
                        if block_hash in file_hashes:
                            duplicates.append({
                                'original': file_hashes[block_hash],
                                'duplicate': {
                                    'file': file_path,
                                    'start_line': i + 1,
                                    'end_line': i + min_lines,
                                    'content': block[:100] + '...' if len(block) > 100 else block
                                }
                            })
                        else:
                            file_hashes[block_hash] = {
                                'file': file_path,
                                'start_line': i + 1,
                                'end_line': i + min_lines,
                                'content': block[:100] + '...' if len(block) > 100 else block
                            }
            
            except (OSError, UnicodeDecodeError):
                continue
        
        return duplicates

    def _prepare_search_pattern(self, pattern: str, mode: SearchMode, 
                               case_sensitive: bool, whole_words: bool) -> Pattern:
        """Prepare the regex pattern based on search mode and options."""
        if mode == SearchMode.REGEX:
            flags = 0 if case_sensitive else re.IGNORECASE
            return re.compile(pattern, flags)
        
        elif mode == SearchMode.LITERAL:
            # Escape special regex characters
            escaped_pattern = re.escape(pattern)
            
            if whole_words:
                escaped_pattern = r'\b' + escaped_pattern + r'\b'
            
            flags = 0 if case_sensitive else re.IGNORECASE
            return re.compile(escaped_pattern, flags)
        
        elif mode == SearchMode.FUZZY:
            # Simple fuzzy search - allow some character differences
            fuzzy_pattern = '.*'.join(re.escape(c) for c in pattern)
            flags = 0 if case_sensitive else re.IGNORECASE
            return re.compile(fuzzy_pattern, flags)
        
        else:  # SEMANTIC mode - would require more sophisticated implementation
            # For now, treat as literal
            escaped_pattern = re.escape(pattern)
            flags = 0 if case_sensitive else re.IGNORECASE
            return re.compile(escaped_pattern, flags)

    def _find_searchable_files(self, file_patterns: List[str] = None, 
                              extensions: Set[str] = None) -> List[Path]:
        """Find files that should be searched."""
        files = []
        search_extensions = extensions or self.default_extensions
        
        if file_patterns:
            # Use file patterns if provided
            import fnmatch
            for pattern in file_patterns:
                for root, dirs, filenames in os.walk(self.base_path):
                    for filename in filenames:
                        if fnmatch.fnmatch(filename, pattern):
                            file_path = Path(root) / filename
                            if self._should_search_file(file_path, search_extensions):
                                files.append(file_path)
        else:
            # Search all files with matching extensions
            for root, dirs, filenames in os.walk(self.base_path):
                # Skip hidden directories and common ignore patterns
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {
                    'node_modules', 'venv', 'env', '__pycache__', '.git', 
                    'target', 'build', 'dist', 'vendor'
                }]
                
                for filename in filenames:
                    file_path = Path(root) / filename
                    if self._should_search_file(file_path, search_extensions):
                        files.append(file_path)
        
        return files

    def _should_search_file(self, file_path: Path, extensions: Set[str]) -> bool:
        """Determine if a file should be searched."""
        # Check extension
        if file_path.suffix.lower() not in extensions:
            return False
        
        # Skip hidden files
        if file_path.name.startswith('.'):
            return False
        
        # Skip large files (>10MB)
        try:
            if file_path.stat().st_size > 10 * 1024 * 1024:
                return False
        except OSError:
            return False
        
        return True

    def _parallel_code_search(self, files: List[Path], pattern: Pattern,
                             context_lines: int, max_matches: int) -> List[CodeMatch]:
        """Perform parallel code search across multiple files."""
        matches = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {
                executor.submit(self._search_file_content, file_path, pattern, context_lines):
                file_path for file_path in files
            }
            
            for future in as_completed(future_to_file):
                try:
                    file_matches = future.result()
                    matches.extend(file_matches)
                    
                    if len(matches) >= max_matches:
                        break
                        
                except Exception as e:
                    # Log error but continue
                    file_path = future_to_file[future]
                    print(f"Error searching {file_path}: {e}")
        
        return matches

    def _sequential_code_search(self, files: List[Path], pattern: Pattern,
                               context_lines: int, max_matches: int) -> List[CodeMatch]:
        """Perform sequential code search across files."""
        matches = []
        
        for file_path in files:
            try:
                file_matches = self._search_file_content(file_path, pattern, context_lines)
                matches.extend(file_matches)
                
                if len(matches) >= max_matches:
                    break
                    
            except Exception as e:
                # Log error but continue
                print(f"Error searching {file_path}: {e}")
        
        return matches

    def _search_file_content(self, file_path: Path, pattern: Pattern, 
                           context_lines: int) -> List[CodeMatch]:
        """Search for pattern in a single file."""
        matches = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            for i, line in enumerate(lines):
                match = pattern.search(line)
                if match:
                    # Get context lines
                    context_before = lines[max(0, i - context_lines):i]
                    context_after = lines[i + 1:i + 1 + context_lines]
                    
                    code_match = CodeMatch(
                        file_path=file_path,
                        line_number=i + 1,
                        line_content=line.rstrip(),
                        match_text=match.group(),
                        match_type=MatchType.PATTERN,
                        context_before=[l.rstrip() for l in context_before],
                        context_after=[l.rstrip() for l in context_after],
                        column_start=match.start(),
                        column_end=match.end()
                    )
                    matches.append(code_match)
        
        except (OSError, UnicodeDecodeError):
            pass  # Skip files we can't read
        
        return matches

    def _search_with_pattern(self, pattern: Pattern, match_type: MatchType, 
                           search_name: str) -> List[CodeMatch]:
        """Helper method to search with a specific pattern."""
        files_to_search = self._find_searchable_files(None, self.default_extensions)
        matches = []
        
        for file_path in files_to_search:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                
                for i, line in enumerate(lines):
                    match = pattern.search(line)
                    if match:
                        code_match = CodeMatch(
                            file_path=file_path,
                            line_number=i + 1,
                            line_content=line.rstrip(),
                            match_text=match.group(),
                            match_type=match_type,
                            column_start=match.start(),
                            column_end=match.end(),
                            metadata={'search_type': search_name}
                        )
                        matches.append(code_match)
            
            except (OSError, UnicodeDecodeError):
                continue
        
        return matches

    def _find_files_by_language(self, language: str) -> List[Path]:
        """Find files for a specific programming language."""
        language_extensions = {
            'python': {'.py'},
            'javascript': {'.js', '.jsx'},
            'typescript': {'.ts', '.tsx'},
            'go': {'.go'},
            'rust': {'.rs'},
            'java': {'.java'},
            'cpp': {'.cpp', '.cc', '.cxx', '.hpp', '.h'},
            'c': {'.c', '.h'},
            'php': {'.php'},
            'ruby': {'.rb'},
            'swift': {'.swift'},
            'kotlin': {'.kt'}
        }
        
        extensions = language_extensions.get(language, self.default_extensions)
        return self._find_searchable_files(None, extensions)

    def _extract_function_name(self, line: str, language: str) -> str:
        """Extract function name from a function definition line."""
        # Simple implementation - could be more sophisticated
        if language == 'python':
            match = re.search(r'def\s+(\w+)', line)
            return match.group(1) if match else ""
        elif language in ['javascript', 'typescript']:
            match = re.search(r'function\s+(\w+)|const\s+(\w+)\s*=|(\w+):\s*function', line)
            return next((g for g in match.groups() if g), "") if match else ""
        else:
            # Generic pattern
            match = re.search(r'\b(\w+)\s*\(', line)
            return match.group(1) if match else ""

    def _extract_function_content(self, lines: List[str], start_index: int, 
                                 language: str) -> str:
        """Extract the content of a function (simplified implementation)."""
        # This is a basic implementation - a full implementation would need
        # proper parsing to handle nested functions, different bracket styles, etc.
        content_lines = []
        bracket_count = 0
        in_function = False
        
        for i in range(start_index, min(len(lines), start_index + 50)):  # Limit search
            line = lines[i]
            content_lines.append(line)
            
            if not in_function and ('(' in line or '{' in line):
                in_function = True
            
            if in_function:
                bracket_count += line.count('{') - line.count('}')
                bracket_count += line.count('(') - line.count(')')
                
                if bracket_count <= 0 and i > start_index:
                    break
        
        return ''.join(content_lines)