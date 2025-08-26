"""
Simple onboarding system for Codexa.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from rich.console import Console


@dataclass 
class OnboardingStep:
    """Single onboarding step."""
    id: str
    title: str
    description: str
    completed: bool = False


class OnboardingManager:
    """Simple onboarding manager."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.steps = []
    
    def add_step(self, step: OnboardingStep):
        """Add onboarding step."""
        self.steps.append(step)
    
    def show_progress(self):
        """Show onboarding progress."""
        completed = len([s for s in self.steps if s.completed])
        total = len(self.steps)
        self.console.print(f"Progress: {completed}/{total} steps completed")