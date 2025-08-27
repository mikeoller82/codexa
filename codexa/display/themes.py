"""
Theme management system for Codexa display components.
"""

from typing import Dict, Optional, Any
from enum import Enum
from dataclasses import dataclass


class ColorTheme(Enum):
    """Available color themes."""
    DEFAULT = "default"
    DARK = "dark"
    LIGHT = "light"
    CYBERPUNK = "cyberpunk"
    RETRO = "retro"
    MATRIX = "matrix"


@dataclass
class ThemeColors:
    """Color scheme for a theme."""
    primary: str
    secondary: str
    accent: str
    background: str
    text: str
    success: str
    warning: str
    error: str


class ThemeManager:
    """Manages display themes for Codexa."""
    
    def __init__(self):
        self.themes = self._initialize_themes()
        self.current_theme = ColorTheme.DEFAULT
    
    def _initialize_themes(self) -> Dict[ColorTheme, ThemeColors]:
        """Initialize available themes."""
        return {
            ColorTheme.DEFAULT: ThemeColors(
                primary="cyan",
                secondary="blue",
                accent="bright_cyan",
                background="black",
                text="white",
                success="green",
                warning="yellow",
                error="red"
            ),
            ColorTheme.DARK: ThemeColors(
                primary="bright_blue",
                secondary="dim",
                accent="bright_white",
                background="black",
                text="white",
                success="bright_green",
                warning="bright_yellow",
                error="bright_red"
            ),
            ColorTheme.LIGHT: ThemeColors(
                primary="blue",
                secondary="blue4",
                accent="black",
                background="white",
                text="black",
                success="green",
                warning="yellow",
                error="red"
            ),
            ColorTheme.CYBERPUNK: ThemeColors(
                primary="bright_magenta",
                secondary="magenta",
                accent="bright_cyan",
                background="black",
                text="bright_white",
                success="bright_green",
                warning="bright_yellow",
                error="bright_red"
            ),
            ColorTheme.RETRO: ThemeColors(
                primary="bright_yellow",
                secondary="yellow",
                accent="bright_green",
                background="black",
                text="bright_white",
                success="green",
                warning="yellow",
                error="red"
            ),
            ColorTheme.MATRIX: ThemeColors(
                primary="bright_green",
                secondary="green",
                accent="bright_cyan",
                background="black",
                text="bright_green",
                success="bright_green",
                warning="bright_yellow",
                error="bright_red"
            )
        }
    
    def get_theme(self, theme: Optional[ColorTheme] = None) -> ThemeColors:
        """Get theme colors."""
        theme = theme or self.current_theme
        return self.themes[theme]
    
    def set_theme(self, theme: ColorTheme):
        """Set current theme."""
        self.current_theme = theme
    
    def get_available_themes(self) -> list[str]:
        """Get list of available theme names."""
        return [theme.value for theme in ColorTheme]
    
    def get_secondary_color(self, theme: Optional[ColorTheme] = None) -> str:
        """Get secondary color that's visible for the current theme."""
        theme = theme or self.current_theme
        colors = self.themes[theme]
        
        # Use a more visible alternative for light backgrounds
        if theme == ColorTheme.LIGHT:
            return "blue4"  # Dark blue, visible on light backgrounds
        else:
            return colors.secondary
    
    def style_secondary_text(self, text: str, theme: Optional[ColorTheme] = None) -> str:
        """Style text with appropriate secondary color for visibility."""
        secondary_color = self.get_secondary_color(theme)
        return f"[{secondary_color}]{text}[/{secondary_color}]"