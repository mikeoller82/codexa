"""
Theme utilities for Codexa display system.
Provides global theme-aware styling functions.
"""

from .themes import ThemeManager, ColorTheme
import re
from typing import Optional

# Global theme manager instance
_theme_manager = ThemeManager()

def get_theme_manager() -> ThemeManager:
    """Get the global theme manager instance."""
    return _theme_manager

def set_global_theme(theme: ColorTheme):
    """Set the global theme."""
    _theme_manager.set_theme(theme)

def theme_aware_style(text: str, theme: Optional[ColorTheme] = None) -> str:
    """
    Convert dim styling to theme-appropriate colors.
    Replaces [dim]...[/dim] with theme-appropriate colors.
    """
    theme_mgr = get_theme_manager()
    dim_style = theme_mgr.get_dim_style(theme)
    
    # Replace [dim] and [/dim] tags with appropriate theme colors
    themed_text = re.sub(r'\[dim\]', f'[{dim_style}]', text)
    themed_text = re.sub(r'\[/dim\]', f'[/{dim_style}]', themed_text)
    
    return themed_text

def ensure_visible_colors(text: str, theme: Optional[ColorTheme] = None) -> str:
    """
    Ensure all colors in the text are visible on the current theme background.
    This is the main function to call for theme-aware text rendering.
    """
    return theme_aware_style(text, theme)

# Quick access functions
def dim_text(text: str, theme: Optional[ColorTheme] = None) -> str:
    """Style text as dim/secondary in a theme-appropriate way."""
    return _theme_manager.style_dim_text(text, theme)

def secondary_text(text: str, theme: Optional[ColorTheme] = None) -> str:
    """Style text as secondary in a theme-appropriate way."""
    return _theme_manager.style_secondary_text(text, theme)