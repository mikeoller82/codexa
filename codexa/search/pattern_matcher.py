"""
Pattern matching utilities for advanced search operations.
"""

import re
import difflib
from typing import List, Dict, Optional, Union, Pattern, Tuple
from dataclasses import dataclass
from enum import Enum

class PatternType(Enum):
    """Types of patterns for matching."""
    GLOB = "glob"
    REGEX = "regex"
    FUZZY = "fuzzy"
    EXACT = "exact"
    SEMANTIC = "semantic"

@dataclass
class MatchResult:
    """Result of a pattern match operation."""
    matched: bool
    confidence: float
    match_text: str
    start_pos: int = 0
    end_pos: int = 0
    metadata: Dict = None

class PatternMatcher:
    """Advanced pattern matching with multiple algorithms."""
    
    def __init__(self):
        """Initialize the pattern matcher."""
        self.compiled_patterns = {}
        
    def match(self, 
             text: str, 
             pattern: str,
             pattern_type: PatternType = PatternType.EXACT,
             case_sensitive: bool = True,
             whole_words: bool = False) -> MatchResult:
        """
        Match text against a pattern using specified matching algorithm.
        
        Args:
            text: Text to search in
            pattern: Pattern to match
            pattern_type: Type of pattern matching
            case_sensitive: Case-sensitive matching
            whole_words: Match whole words only
            
        Returns:
            MatchResult with match details
        """
        if not text or not pattern:
            return MatchResult(matched=False, confidence=0.0, match_text="")
        
        # Prepare text and pattern based on options
        search_text = text if case_sensitive else text.lower()
        search_pattern = pattern if case_sensitive else pattern.lower()
        
        if pattern_type == PatternType.EXACT:
            return self._exact_match(search_text, search_pattern, whole_words)
        elif pattern_type == PatternType.REGEX:
            return self._regex_match(search_text, search_pattern, case_sensitive, whole_words)
        elif pattern_type == PatternType.GLOB:
            return self._glob_match(search_text, search_pattern)
        elif pattern_type == PatternType.FUZZY:
            return self._fuzzy_match(search_text, search_pattern)
        elif pattern_type == PatternType.SEMANTIC:
            return self._semantic_match(search_text, search_pattern)
        else:
            return MatchResult(matched=False, confidence=0.0, match_text="")

    def find_all_matches(self,
                        text: str,
                        pattern: str,
                        pattern_type: PatternType = PatternType.EXACT,
                        case_sensitive: bool = True,
                        max_matches: int = 100) -> List[MatchResult]:
        """Find all matches of pattern in text."""
        matches = []
        
        if pattern_type == PatternType.REGEX:
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                compiled_pattern = re.compile(pattern, flags)
                
                for match in compiled_pattern.finditer(text):
                    result = MatchResult(
                        matched=True,
                        confidence=1.0,
                        match_text=match.group(),
                        start_pos=match.start(),
                        end_pos=match.end()
                    )
                    matches.append(result)
                    
                    if len(matches) >= max_matches:
                        break
                        
            except re.error:
                return []
        
        elif pattern_type == PatternType.EXACT:
            search_text = text if case_sensitive else text.lower()
            search_pattern = pattern if case_sensitive else pattern.lower()
            
            start = 0
            while True:
                pos = search_text.find(search_pattern, start)
                if pos == -1:
                    break
                
                result = MatchResult(
                    matched=True,
                    confidence=1.0,
                    match_text=text[pos:pos + len(pattern)],
                    start_pos=pos,
                    end_pos=pos + len(pattern)
                )
                matches.append(result)
                
                start = pos + 1
                if len(matches) >= max_matches:
                    break
        
        elif pattern_type == PatternType.FUZZY:
            # For fuzzy matching, we'll use a sliding window approach
            pattern_len = len(pattern)
            search_text = text if case_sensitive else text.lower()
            search_pattern = pattern if case_sensitive else pattern.lower()
            
            for i in range(len(text) - pattern_len + 1):
                substring = search_text[i:i + pattern_len]
                similarity = difflib.SequenceMatcher(None, search_pattern, substring).ratio()
                
                if similarity > 0.6:  # Threshold for fuzzy match
                    result = MatchResult(
                        matched=True,
                        confidence=similarity,
                        match_text=text[i:i + pattern_len],
                        start_pos=i,
                        end_pos=i + pattern_len
                    )
                    matches.append(result)
                    
                    if len(matches) >= max_matches:
                        break
        
        return matches

    def compile_pattern(self, 
                       pattern: str, 
                       pattern_type: PatternType,
                       case_sensitive: bool = True) -> Optional[Pattern]:
        """Compile pattern for repeated use."""
        cache_key = (pattern, pattern_type, case_sensitive)
        
        if cache_key in self.compiled_patterns:
            return self.compiled_patterns[cache_key]
        
        compiled = None
        
        if pattern_type == PatternType.REGEX:
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                compiled = re.compile(pattern, flags)
            except re.error:
                pass
        
        elif pattern_type == PatternType.GLOB:
            # Convert glob pattern to regex
            import fnmatch
            regex_pattern = fnmatch.translate(pattern)
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                compiled = re.compile(regex_pattern, flags)
            except re.error:
                pass
        
        self.compiled_patterns[cache_key] = compiled
        return compiled

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings."""
        if not text1 or not text2:
            return 0.0
        
        return difflib.SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    def find_best_matches(self,
                         text: str,
                         candidates: List[str],
                         max_results: int = 5,
                         min_similarity: float = 0.3) -> List[Tuple[str, float]]:
        """Find best matching candidates for given text."""
        matches = []
        
        for candidate in candidates:
            similarity = self.calculate_similarity(text, candidate)
            if similarity >= min_similarity:
                matches.append((candidate, similarity))
        
        # Sort by similarity descending
        matches.sort(key=lambda x: x[1], reverse=True)
        
        return matches[:max_results]

    def extract_words(self, text: str, min_length: int = 2) -> List[str]:
        """Extract words from text."""
        # Simple word extraction using regex
        words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', text)
        return [word for word in words if len(word) >= min_length]

    def extract_identifiers(self, code: str, language: str = "python") -> List[str]:
        """Extract identifiers (variable names, function names, etc.) from code."""
        identifiers = set()
        
        if language == "python":
            # Extract function definitions
            func_matches = re.findall(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)', code)
            identifiers.update(func_matches)
            
            # Extract class definitions
            class_matches = re.findall(r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)', code)
            identifiers.update(class_matches)
            
            # Extract variable assignments
            var_matches = re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*=', code)
            identifiers.update(var_matches)
        
        elif language in ["javascript", "typescript"]:
            # Extract function definitions
            func_matches = re.findall(r'function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)', code)
            identifiers.update(func_matches)
            
            # Extract const/let/var declarations
            var_matches = re.findall(r'(?:const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)', code)
            identifiers.update(var_matches)
            
            # Extract class definitions
            class_matches = re.findall(r'class\s+([a-zA-Z_$][a-zA-Z0-9_$]*)', code)
            identifiers.update(class_matches)
        
        return list(identifiers)

    def _exact_match(self, text: str, pattern: str, whole_words: bool) -> MatchResult:
        """Perform exact string matching."""
        if whole_words:
            # Use word boundaries
            word_pattern = r'\b' + re.escape(pattern) + r'\b'
            match = re.search(word_pattern, text)
            if match:
                return MatchResult(
                    matched=True,
                    confidence=1.0,
                    match_text=match.group(),
                    start_pos=match.start(),
                    end_pos=match.end()
                )
        else:
            pos = text.find(pattern)
            if pos != -1:
                return MatchResult(
                    matched=True,
                    confidence=1.0,
                    match_text=pattern,
                    start_pos=pos,
                    end_pos=pos + len(pattern)
                )
        
        return MatchResult(matched=False, confidence=0.0, match_text="")

    def _regex_match(self, text: str, pattern: str, case_sensitive: bool, 
                    whole_words: bool) -> MatchResult:
        """Perform regex matching."""
        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            
            if whole_words:
                pattern = r'\b(?:' + pattern + r')\b'
            
            match = re.search(pattern, text, flags)
            if match:
                return MatchResult(
                    matched=True,
                    confidence=1.0,
                    match_text=match.group(),
                    start_pos=match.start(),
                    end_pos=match.end()
                )
        except re.error:
            pass
        
        return MatchResult(matched=False, confidence=0.0, match_text="")

    def _glob_match(self, text: str, pattern: str) -> MatchResult:
        """Perform glob pattern matching."""
        import fnmatch
        
        if fnmatch.fnmatch(text, pattern):
            return MatchResult(
                matched=True,
                confidence=1.0,
                match_text=text,
                start_pos=0,
                end_pos=len(text)
            )
        
        return MatchResult(matched=False, confidence=0.0, match_text="")

    def _fuzzy_match(self, text: str, pattern: str) -> MatchResult:
        """Perform fuzzy string matching."""
        similarity = difflib.SequenceMatcher(None, pattern, text).ratio()
        
        if similarity > 0.6:  # Threshold for considering it a match
            return MatchResult(
                matched=True,
                confidence=similarity,
                match_text=text,
                start_pos=0,
                end_pos=len(text),
                metadata={"similarity": similarity}
            )
        
        # Try finding the best matching substring
        best_similarity = 0
        best_match = ""
        best_start = 0
        best_end = 0
        
        for i in range(len(text) - len(pattern) + 1):
            substring = text[i:i + len(pattern)]
            sim = difflib.SequenceMatcher(None, pattern, substring).ratio()
            
            if sim > best_similarity:
                best_similarity = sim
                best_match = substring
                best_start = i
                best_end = i + len(pattern)
        
        if best_similarity > 0.6:
            return MatchResult(
                matched=True,
                confidence=best_similarity,
                match_text=best_match,
                start_pos=best_start,
                end_pos=best_end,
                metadata={"similarity": best_similarity}
            )
        
        return MatchResult(matched=False, confidence=0.0, match_text="")

    def _semantic_match(self, text: str, pattern: str) -> MatchResult:
        """Perform semantic matching (simplified implementation)."""
        # This is a placeholder for more sophisticated semantic matching
        # In a full implementation, this might use NLP models, word embeddings, etc.
        
        # For now, we'll use a combination of techniques:
        # 1. Exact match gets highest score
        # 2. Fuzzy match for similar strings
        # 3. Word overlap for semantic similarity
        
        # Exact match
        if pattern in text:
            pos = text.find(pattern)
            return MatchResult(
                matched=True,
                confidence=1.0,
                match_text=pattern,
                start_pos=pos,
                end_pos=pos + len(pattern),
                metadata={"method": "exact"}
            )
        
        # Word overlap
        pattern_words = set(self.extract_words(pattern.lower()))
        text_words = set(self.extract_words(text.lower()))
        
        if pattern_words and text_words:
            overlap = pattern_words.intersection(text_words)
            overlap_ratio = len(overlap) / len(pattern_words)
            
            if overlap_ratio > 0.5:
                return MatchResult(
                    matched=True,
                    confidence=overlap_ratio * 0.8,  # Scale down for word-based matching
                    match_text=text,
                    start_pos=0,
                    end_pos=len(text),
                    metadata={"method": "word_overlap", "overlap_ratio": overlap_ratio}
                )
        
        # Fallback to fuzzy matching
        fuzzy_result = self._fuzzy_match(text, pattern)
        if fuzzy_result.matched:
            fuzzy_result.confidence *= 0.7  # Scale down for fuzzy
            fuzzy_result.metadata = {"method": "fuzzy", **fuzzy_result.metadata}
            return fuzzy_result
        
        return MatchResult(matched=False, confidence=0.0, match_text="")