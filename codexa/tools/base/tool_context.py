"""
Tool context management for Codexa tool system.
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
import logging

from .tool_interface import ToolContext


class ToolContextManager:
    """
    Manages tool execution contexts and shared state across tool chains.
    """
    
    def __init__(self):
        """Initialize context manager."""
        self.logger = logging.getLogger("codexa.tools.context")
        self._active_contexts: Dict[str, ToolContext] = {}
        self._context_history: List[str] = []
        self._max_history = 100
    
    def create_context(self, 
                      user_request: str,
                      session_id: Optional[str] = None,
                      current_dir: Optional[str] = None,
                      config: Optional[Any] = None,
                      mcp_service: Optional[Any] = None,
                      provider: Optional[Any] = None,
                      **kwargs) -> ToolContext:
        """
        Create new tool execution context.
        
        Args:
            user_request: User's original request
            session_id: Optional session identifier
            current_dir: Current working directory
            config: Configuration object
            mcp_service: MCP service instance
            provider: AI provider instance
            **kwargs: Additional context data
            
        Returns:
            New ToolContext instance
        """
        request_id = str(uuid.uuid4())
        
        # Get project info if in a project
        project_info = {}
        if current_dir:
            project_path = Path(current_dir)
            project_info = {
                "name": project_path.name,
                "path": str(project_path),
                "is_git_repo": (project_path / ".git").exists(),
                "has_codexa": (project_path / "CODEXA.md").exists(),
                "files_count": len(list(project_path.iterdir())) if project_path.exists() else 0
            }
        
        context = ToolContext(
            request_id=request_id,
            user_request=user_request,
            session_id=session_id or str(uuid.uuid4()),
            current_dir=current_dir,
            project_info=project_info,
            config=config,
            mcp_service=mcp_service,
            provider=provider,
            **kwargs
        )
        
        # Store active context
        self._active_contexts[request_id] = context
        self._context_history.append(request_id)
        
        # Maintain history limit
        if len(self._context_history) > self._max_history:
            old_id = self._context_history.pop(0)
            self._active_contexts.pop(old_id, None)
        
        self.logger.debug(f"Created context: {request_id}")
        return context
    
    def get_context(self, request_id: str) -> Optional[ToolContext]:
        """Get context by request ID."""
        return self._active_contexts.get(request_id)
    
    def update_context(self, context: ToolContext) -> None:
        """Update stored context."""
        context.updated_at = datetime.now()
        self._active_contexts[context.request_id] = context
    
    def cleanup_context(self, request_id: str) -> None:
        """Remove context from active contexts."""
        if request_id in self._active_contexts:
            del self._active_contexts[request_id]
            self.logger.debug(f"Cleaned up context: {request_id}")
    
    def get_active_contexts(self) -> Dict[str, ToolContext]:
        """Get all active contexts."""
        return self._active_contexts.copy()
    
    def get_context_stats(self) -> Dict[str, Any]:
        """Get context manager statistics."""
        return {
            "active_contexts": len(self._active_contexts),
            "total_contexts": len(self._context_history),
            "max_history": self._max_history,
            "oldest_context": min(
                (ctx.created_at for ctx in self._active_contexts.values()),
                default=None
            ),
            "newest_context": max(
                (ctx.created_at for ctx in self._active_contexts.values()),
                default=None
            )
        }


@dataclass
class ContextualRequest:
    """
    Enhanced request object with context awareness.
    """
    
    # Original request
    raw_request: str
    processed_request: str
    request_type: str  # command, question, task, etc.
    
    # Context clues
    mentioned_files: List[str] = field(default_factory=list)
    mentioned_tools: List[str] = field(default_factory=list)
    required_capabilities: Set[str] = field(default_factory=set)
    
    # Intent analysis
    intent: str = ""  # create, modify, analyze, etc.
    confidence: float = 0.0
    urgency: str = "normal"  # low, normal, high, critical
    
    # Resource requirements
    estimated_complexity: float = 0.0
    estimated_time: float = 0.0
    requires_user_input: bool = False
    
    def add_context_clue(self, clue_type: str, value: str) -> None:
        """Add contextual clue to request."""
        if clue_type == "file":
            self.mentioned_files.append(value)
        elif clue_type == "tool":
            self.mentioned_tools.append(value)
        elif clue_type == "capability":
            self.required_capabilities.add(value)


class RequestAnalyzer:
    """
    Analyzes user requests to extract context and routing information.
    """
    
    def __init__(self):
        """Initialize request analyzer."""
        self.logger = logging.getLogger("codexa.tools.analyzer")
    
    def analyze_request(self, request: str) -> ContextualRequest:
        """
        Analyze user request to extract context and intent.
        
        Args:
            request: Raw user request string
            
        Returns:
            ContextualRequest with analysis results
        """
        # Create contextual request
        contextual = ContextualRequest(
            raw_request=request,
            processed_request=request.strip(),
            request_type=self._classify_request_type(request)
        )
        
        # Extract mentioned files
        contextual.mentioned_files = self._extract_file_mentions(request)
        
        # Detect intent
        contextual.intent = self._detect_intent(request)
        
        # Estimate complexity
        contextual.estimated_complexity = self._estimate_complexity(request)
        
        # Detect required capabilities
        contextual.required_capabilities = self._extract_capabilities(request)
        
        # Set confidence
        contextual.confidence = self._calculate_confidence(contextual)
        
        return contextual
    
    def _classify_request_type(self, request: str) -> str:
        """Classify the type of request."""
        request_lower = request.lower().strip()
        
        if request_lower.startswith("/"):
            return "command"
        elif any(word in request_lower for word in ["?", "what", "how", "why", "explain"]):
            return "question"
        elif any(word in request_lower for word in ["create", "build", "implement", "generate"]):
            return "creation"
        elif any(word in request_lower for word in ["fix", "debug", "solve", "resolve"]):
            return "problem_solving"
        elif any(word in request_lower for word in ["analyze", "review", "check"]):
            return "analysis"
        else:
            return "task"
    
    def _extract_file_mentions(self, request: str) -> List[str]:
        """Extract file paths/names mentioned in request."""
        import re
        
        # Look for file patterns
        file_patterns = [
            r'([a-zA-Z0-9_/.-]+\.[a-zA-Z0-9]+)',  # files with extensions
            r'([a-zA-Z0-9_/-]+/[a-zA-Z0-9_.-]+)',  # paths
        ]
        
        files = []
        for pattern in file_patterns:
            matches = re.findall(pattern, request)
            files.extend(matches)
        
        return list(set(files))  # Remove duplicates
    
    def _detect_intent(self, request: str) -> str:
        """Detect the main intent of the request."""
        request_lower = request.lower()
        
        intent_keywords = {
            "create": ["create", "build", "generate", "make", "add", "implement"],
            "modify": ["update", "change", "modify", "edit", "fix", "refactor"],
            "analyze": ["analyze", "review", "check", "examine", "inspect"],
            "delete": ["delete", "remove", "clean", "clear"],
            "search": ["find", "search", "locate", "look for"],
            "help": ["help", "explain", "how", "what", "guide"],
            "configure": ["configure", "setup", "install", "enable", "disable"]
        }
        
        for intent, keywords in intent_keywords.items():
            if any(keyword in request_lower for keyword in keywords):
                return intent
        
        return "unknown"
    
    def _estimate_complexity(self, request: str) -> float:
        """Estimate request complexity (0.0-1.0)."""
        complexity = 0.0
        request_lower = request.lower()
        
        # Length factor
        complexity += min(len(request) / 500, 0.3)
        
        # Complexity indicators
        complex_terms = [
            "refactor", "architecture", "system", "integrate", "optimize",
            "comprehensive", "entire", "all", "complete", "full"
        ]
        
        for term in complex_terms:
            if term in request_lower:
                complexity += 0.1
        
        # File count factor
        files_mentioned = len(self._extract_file_mentions(request))
        complexity += min(files_mentioned / 10, 0.2)
        
        return min(complexity, 1.0)
    
    def _extract_capabilities(self, request: str) -> Set[str]:
        """Extract required capabilities from request."""
        capabilities = set()
        request_lower = request.lower()
        
        capability_map = {
            "filesystem": ["file", "directory", "folder", "path", "read", "write"],
            "mcp": ["documentation", "analyze", "ui", "component", "test"],
            "ai": ["generate", "explain", "summarize", "translate"],
            "search": ["find", "search", "locate", "grep"],
            "git": ["commit", "branch", "merge", "repository"],
            "configuration": ["config", "setup", "install", "configure"],
        }
        
        for capability, keywords in capability_map.items():
            if any(keyword in request_lower for keyword in keywords):
                capabilities.add(capability)
        
        return capabilities
    
    def _calculate_confidence(self, contextual: ContextualRequest) -> float:
        """Calculate confidence in analysis."""
        confidence = 0.5  # Base confidence
        
        # Intent detection confidence
        if contextual.intent != "unknown":
            confidence += 0.2
        
        # File mentions boost confidence
        if contextual.mentioned_files:
            confidence += 0.1
        
        # Capability detection
        if contextual.required_capabilities:
            confidence += 0.1
        
        # Clear request type
        if contextual.request_type != "task":
            confidence += 0.1
        
        return min(confidence, 1.0)