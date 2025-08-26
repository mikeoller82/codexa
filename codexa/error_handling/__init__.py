"""
Error handling and user guidance system for Codexa.
"""

from .error_manager import (
    ErrorManager,
    ErrorSeverity,
    ErrorCategory,
    ErrorContext,
    UserGuidance,
    CodexaError
)
from .user_guidance import (
    UserGuidanceSystem,
    GuidanceType,
    GuidanceContext,
    InteractiveGuidance
)
from .recovery_manager import (
    RecoveryManager,
    RecoveryStrategy,
    RecoveryResult
)

__all__ = [
    "ErrorManager",
    "ErrorSeverity",
    "ErrorCategory", 
    "ErrorContext",
    "UserGuidance",
    "CodexaError",
    "UserGuidanceSystem",
    "GuidanceType",
    "GuidanceContext",
    "InteractiveGuidance",
    "RecoveryManager",
    "RecoveryStrategy",
    "RecoveryResult"
]