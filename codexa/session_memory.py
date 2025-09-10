"""
Session Memory System for Codexa - Maintains Agentic Context Across Interactions
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from pathlib import Path


class SessionState(Enum):
    """Session operation states."""
    IDLE = "idle"
    AGENTIC_ACTIVE = "agentic_active"
    AGENTIC_PAUSED = "agentic_paused"
    AWAITING_INPUT = "awaiting_input"
    TASK_COMPLETED = "task_completed"


@dataclass
class AgenticContext:
    """Context for agentic operations."""
    original_task: str
    current_objective: str
    completed_steps: List[str]
    pending_steps: List[str]
    iteration_count: int
    last_result: Optional[str]
    last_evaluation: Optional[str]
    context_keywords: Set[str]
    files_created: List[str]
    files_modified: List[str]
    tools_used: List[str]
    success_indicators: List[str]
    failure_indicators: List[str]
    started_at: datetime
    last_activity: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert sets to lists and datetime to strings for JSON serialization
        data['context_keywords'] = list(data['context_keywords'])
        data['started_at'] = data['started_at'].isoformat()
        data['last_activity'] = data['last_activity'].isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgenticContext':
        """Create from dictionary."""
        # Convert lists back to sets and strings back to datetime
        data['context_keywords'] = set(data['context_keywords'])
        data['started_at'] = datetime.fromisoformat(data['started_at'])
        data['last_activity'] = datetime.fromisoformat(data['last_activity'])
        return cls(**data)
    
    def is_stale(self, max_idle_minutes: int = 30) -> bool:
        """Check if context is stale (no activity for a while)."""
        return datetime.now() - self.last_activity > timedelta(minutes=max_idle_minutes)
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
    
    def add_completed_step(self, step: str):
        """Add a completed step."""
        if step not in self.completed_steps:
            self.completed_steps.append(step)
        if step in self.pending_steps:
            self.pending_steps.remove(step)
        self.update_activity()
    
    def add_pending_step(self, step: str):
        """Add a pending step."""
        if step not in self.pending_steps and step not in self.completed_steps:
            self.pending_steps.append(step)
        self.update_activity()
    
    def is_task_complete(self) -> bool:
        """Check if the task appears to be complete."""
        return (len(self.pending_steps) == 0 and 
                len(self.completed_steps) > 0 and
                self.last_evaluation and 
                "success" in self.last_evaluation.lower())


class SessionMemory:
    """
    Session Memory System for maintaining agentic context across interactions.
    
    This system enables codexa to maintain context between agentic loop iterations
    and regular session interactions, ensuring that tasks continue until completion.
    """
    
    def __init__(self, session_dir: Optional[Path] = None):
        """Initialize session memory."""
        self.logger = logging.getLogger("codexa.session_memory")
        
        # Session state
        self.current_state = SessionState.IDLE
        self.session_id = self._generate_session_id()
        self.agentic_context: Optional[AgenticContext] = None
        self.conversation_history: List[Dict[str, Any]] = []
        self.user_preferences: Dict[str, Any] = {}
        
        # Context tracking
        self.active_tools: Set[str] = set()
        self.session_files: Set[str] = set()
        self.context_keywords: Set[str] = set()
        
        # Persistence
        self.session_dir = session_dir or Path.cwd() / ".codexa" / "sessions"
        self.session_file = self.session_dir / f"session_{self.session_id}.json"
        self.ensure_session_dir()
        
        self.logger.info(f"Session memory initialized with ID: {self.session_id}")
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def ensure_session_dir(self):
        """Ensure session directory exists."""
        try:
            self.session_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.warning(f"Could not create session directory: {e}")
    
    def start_agentic_context(self, task: str, initial_objective: str = None) -> AgenticContext:
        """Start a new agentic context."""
        self.current_state = SessionState.AGENTIC_ACTIVE
        
        # Extract context keywords from task
        context_keywords = self._extract_keywords(task)
        
        self.agentic_context = AgenticContext(
            original_task=task,
            current_objective=initial_objective or task,
            completed_steps=[],
            pending_steps=[],
            iteration_count=0,
            last_result=None,
            last_evaluation=None,
            context_keywords=context_keywords,
            files_created=[],
            files_modified=[],
            tools_used=[],
            success_indicators=[],
            failure_indicators=[],
            started_at=datetime.now(),
            last_activity=datetime.now()
        )
        
        self.context_keywords.update(context_keywords)
        self.save_session()
        
        self.logger.info(f"Started agentic context for task: {task[:50]}...")
        return self.agentic_context
    
    def update_agentic_context(self, 
                             iteration_count: int = None,
                             last_result: str = None,
                             last_evaluation: str = None,
                             completed_steps: List[str] = None,
                             pending_steps: List[str] = None,
                             files_created: List[str] = None,
                             files_modified: List[str] = None,
                             tools_used: List[str] = None):
        """Update the current agentic context."""
        if not self.agentic_context:
            self.logger.warning("Attempted to update non-existent agentic context")
            return
        
        if iteration_count is not None:
            self.agentic_context.iteration_count = iteration_count
        if last_result is not None:
            self.agentic_context.last_result = last_result
        if last_evaluation is not None:
            self.agentic_context.last_evaluation = last_evaluation
        if completed_steps is not None:
            self.agentic_context.completed_steps.extend(completed_steps)
        if pending_steps is not None:
            for step in pending_steps:
                self.agentic_context.add_pending_step(step)
        if files_created is not None:
            self.agentic_context.files_created.extend(files_created)
            self.session_files.update(files_created)
        if files_modified is not None:
            self.agentic_context.files_modified.extend(files_modified)
            self.session_files.update(files_modified)
        if tools_used is not None:
            self.agentic_context.tools_used.extend(tools_used)
            self.active_tools.update(tools_used)
        
        self.agentic_context.update_activity()
        self.save_session()
    
    def is_request_related_to_agentic_task(self, request: str) -> bool:
        """Check if a request is related to the current agentic task."""
        if not self.agentic_context or self.current_state == SessionState.IDLE:
            return False
        
        request_lower = request.lower()
        
        # Check for direct continuation keywords
        continuation_keywords = [
            "continue", "next", "keep going", "proceed", "finish",
            "complete", "done?", "finished?", "status", "progress"
        ]
        
        if any(keyword in request_lower for keyword in continuation_keywords):
            return True
        
        # Check for context keyword overlap
        request_keywords = self._extract_keywords(request)
        context_overlap = request_keywords & self.agentic_context.context_keywords
        
        # If there's significant overlap, it's likely related 
        if len(context_overlap) >= 1:
            # Check if the overlap includes specific/unique words (avoid generic matches)
            # Include both request and context keywords for broader specific word detection
            all_request_keywords = request_keywords
            all_context_keywords = self.agentic_context.context_keywords
            
            specific_words = {
                'calculator', 'add', 'subtract', 'multiply', 'divide', 
                # Add filenames
            } | set(self.agentic_context.files_created)
            
            # Check if either the request or context has specific words that match
            request_has_specific = all_request_keywords & specific_words
            context_has_specific = all_context_keywords & specific_words
            
            # If request mentions specific concepts from our task domain
            if request_has_specific:
                return True
            
            # If context has specific concepts and we have any overlap, it's likely related
            # But avoid false positives from purely generic overlaps
            if context_has_specific and len(context_overlap) >= 1:
                # Make sure the overlap isn't just generic words without context
                if context_overlap - generic_words or len(context_overlap) >= 2:
                    return True
            
            # For generic words, need additional context or multiple overlaps
            generic_words = {'create', 'implement', 'function', 'work', 'next', 'step', 'simple', 'basic'}
            generic_overlap = context_overlap & generic_words
            
            if generic_overlap:
                # Generic words alone are not enough unless there are multiple keywords
                # or the request contains task-continuation language
                if len(context_overlap) >= 2:
                    return True
                
                # Check for task continuation language along with generic overlap
                continuation_phrases = ['the ' + word for word in ['calculator', 'function', 'task', 'project']]
                if any(phrase in request_lower for phrase in continuation_phrases):
                    return True
        
        # Check if request mentions files from the agentic task
        request_files = self._extract_file_references(request)
        agentic_files = set(self.agentic_context.files_created + self.agentic_context.files_modified)
        
        if request_files & agentic_files:
            return True
        
        # Check for tool-specific continuations
        if any(tool in request_lower for tool in self.agentic_context.tools_used):
            return True
        
        return False
    
    def should_continue_agentic_mode(self, request: str) -> bool:
        """Determine if we should continue in agentic mode."""
        if not self.agentic_context:
            return False
        
        # If explicitly asking to continue
        if self.is_request_related_to_agentic_task(request):
            return True
        
        # If task is not complete and recent activity
        if not self.agentic_context.is_task_complete() and not self.agentic_context.is_stale():
            return True
        
        # If there are pending steps
        if len(self.agentic_context.pending_steps) > 0:
            return True
        
        return False
    
    def pause_agentic_context(self):
        """Pause the agentic context."""
        if self.agentic_context:
            self.current_state = SessionState.AGENTIC_PAUSED
            self.save_session()
            self.logger.info("Agentic context paused")
    
    def resume_agentic_context(self):
        """Resume the agentic context."""
        if self.agentic_context and self.current_state == SessionState.AGENTIC_PAUSED:
            self.current_state = SessionState.AGENTIC_ACTIVE
            self.agentic_context.update_activity()
            self.save_session()
            self.logger.info("Agentic context resumed")
    
    def complete_agentic_context(self, final_result: str = None):
        """Mark the agentic context as completed."""
        if self.agentic_context:
            self.current_state = SessionState.TASK_COMPLETED
            if final_result:
                self.agentic_context.last_result = final_result
                self.agentic_context.last_evaluation = "Task completed successfully"
            self.save_session()
            self.logger.info("Agentic context marked as completed")
    
    def end_agentic_context(self):
        """End the current agentic context."""
        if self.agentic_context:
            self.logger.info(f"Ending agentic context after {self.agentic_context.iteration_count} iterations")
            # Archive the context instead of destroying it
            self.archive_agentic_context()
            self.agentic_context = None
            self.current_state = SessionState.IDLE
            self.save_session()
    
    def archive_agentic_context(self):
        """Archive the current agentic context for future reference."""
        if not self.agentic_context:
            return
        
        try:
            archive_dir = self.session_dir / "archived_contexts"
            archive_dir.mkdir(exist_ok=True)
            
            archive_file = archive_dir / f"agentic_context_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(archive_file, 'w', encoding='utf-8') as f:
                json.dump(self.agentic_context.to_dict(), f, indent=2)
            
            self.logger.info(f"Archived agentic context to {archive_file}")
        except Exception as e:
            self.logger.error(f"Failed to archive agentic context: {e}")
    
    def add_conversation_entry(self, user_input: str, assistant_response: str, mode: str = "regular"):
        """Add entry to conversation history."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user": user_input,
            "assistant": assistant_response,
            "mode": mode,
            "session_state": self.current_state.value,
            "agentic_iteration": self.agentic_context.iteration_count if self.agentic_context else 0
        }
        
        self.conversation_history.append(entry)
        
        # Maintain conversation history limit
        max_history = 1000
        if len(self.conversation_history) > max_history:
            self.conversation_history = self.conversation_history[-max_history:]
        
        self.save_session()
    
    def get_agentic_summary(self) -> str:
        """Get a summary of the current agentic context."""
        if not self.agentic_context:
            return "No active agentic context"
        
        summary_parts = [
            f"Task: {self.agentic_context.original_task}",
            f"Current Objective: {self.agentic_context.current_objective}",
            f"Iterations: {self.agentic_context.iteration_count}",
            f"Completed Steps: {len(self.agentic_context.completed_steps)}",
            f"Pending Steps: {len(self.agentic_context.pending_steps)}",
            f"Files Created: {len(self.agentic_context.files_created)}",
            f"Files Modified: {len(self.agentic_context.files_modified)}",
            f"Tools Used: {', '.join(self.agentic_context.tools_used[-3:])}..." if len(self.agentic_context.tools_used) > 3 else f"Tools Used: {', '.join(self.agentic_context.tools_used)}",
            f"Status: {self.current_state.value}",
            f"Duration: {(datetime.now() - self.agentic_context.started_at).total_seconds():.1f}s"
        ]
        
        return "\n".join(summary_parts)
    
    def _extract_keywords(self, text: str) -> Set[str]:
        """Extract meaningful keywords from text."""
        import re
        
        # Common tech keywords and project-related terms
        tech_keywords = {
            'python', 'javascript', 'react', 'vue', 'angular', 'nodejs', 'flask', 'django',
            'api', 'endpoint', 'database', 'sql', 'mongodb', 'redis', 'docker', 'kubernetes',
            'authentication', 'auth', 'login', 'user', 'admin', 'dashboard', 'component',
            'function', 'class', 'module', 'service', 'controller', 'model', 'view',
            'test', 'testing', 'debug', 'deploy', 'build', 'config', 'setup', 'install',
            'calculator', 'add', 'subtract', 'multiply', 'divide', 'create', 'implement',
            'simple', 'basic', 'operation', 'operations'
        }
        
        # Extract words (2+ characters for better coverage)
        words = set(re.findall(r'\b[a-zA-Z]{2,}\b', text.lower()))
        
        # Filter for meaningful keywords
        meaningful_keywords = words & tech_keywords
        
        # Add any capitalized words from original text (likely proper nouns/tech terms)
        capitalized_words = set(re.findall(r'\b[A-Z][a-z]+\b', text))
        meaningful_keywords.update(word.lower() for word in capitalized_words)
        
        # Also add important domain-specific words that appear in the context
        domain_words = words & {
            'calculator', 'function', 'add', 'subtract', 'multiply', 'divide',
            'create', 'implement', 'build', 'make', 'write', 'code', 'project',
            'task', 'work', 'continue', 'next', 'step', 'complete', 'finish'
        }
        meaningful_keywords.update(domain_words)
        
        return meaningful_keywords
    
    def _extract_file_references(self, text: str) -> Set[str]:
        """Extract file references from text."""
        import re
        
        # Pattern to match common file extensions
        file_pattern = r'\b[\w\-_./]+\.(?:py|js|jsx|ts|tsx|html|css|scss|json|yaml|yml|md|txt|sql|sh|bat)\b'
        files = set(re.findall(file_pattern, text, re.IGNORECASE))
        
        return files
    
    def save_session(self):
        """Save current session state to disk."""
        try:
            session_data = {
                "session_id": self.session_id,
                "current_state": self.current_state.value,
                "agentic_context": self.agentic_context.to_dict() if self.agentic_context else None,
                "conversation_history": self.conversation_history[-50:],  # Save recent history
                "user_preferences": self.user_preferences,
                "active_tools": list(self.active_tools),
                "session_files": list(self.session_files),
                "context_keywords": list(self.context_keywords),
                "last_saved": datetime.now().isoformat()
            }
            
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2)
        
        except Exception as e:
            self.logger.error(f"Failed to save session: {e}")
    
    def load_session(self, session_id: str = None) -> bool:
        """Load session from disk."""
        try:
            if session_id:
                self.session_id = session_id
                self.session_file = self.session_dir / f"session_{session_id}.json"
            
            if not self.session_file.exists():
                return False
            
            with open(self.session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            self.session_id = session_data.get("session_id", self.session_id)
            self.current_state = SessionState(session_data.get("current_state", "idle"))
            
            agentic_data = session_data.get("agentic_context")
            if agentic_data:
                self.agentic_context = AgenticContext.from_dict(agentic_data)
            
            self.conversation_history = session_data.get("conversation_history", [])
            self.user_preferences = session_data.get("user_preferences", {})
            self.active_tools = set(session_data.get("active_tools", []))
            self.session_files = set(session_data.get("session_files", []))
            self.context_keywords = set(session_data.get("context_keywords", []))
            
            self.logger.info(f"Loaded session {self.session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load session: {e}")
            return False
    
    def cleanup_old_sessions(self, max_age_days: int = 7):
        """Clean up old session files."""
        try:
            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            
            for session_file in self.session_dir.glob("session_*.json"):
                try:
                    # Extract timestamp from filename
                    timestamp_str = session_file.stem.replace("session_", "")
                    file_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    
                    if file_date < cutoff_date:
                        session_file.unlink()
                        self.logger.debug(f"Cleaned up old session: {session_file}")
                        
                except Exception as e:
                    self.logger.debug(f"Error processing session file {session_file}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Session cleanup failed: {e}")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        return {
            "session_id": self.session_id,
            "current_state": self.current_state.value,
            "has_agentic_context": self.agentic_context is not None,
            "agentic_iterations": self.agentic_context.iteration_count if self.agentic_context else 0,
            "conversation_entries": len(self.conversation_history),
            "active_tools": len(self.active_tools),
            "session_files": len(self.session_files),
            "context_keywords": len(self.context_keywords),
            "session_duration": (datetime.now() - datetime.fromisoformat(self.session_id.replace('_', 'T', 1) + ':00')).total_seconds() if '_' in self.session_id else 0
        }