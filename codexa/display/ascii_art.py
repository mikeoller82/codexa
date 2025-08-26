"""
ASCII art system for Codexa with multiple themes and animations.
"""

import time
import sys
from typing import List, Dict, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from rich.console import Console
from rich.panel import Panel
from rich.align import Align


class LogoTheme(Enum):
    """Available logo themes."""
    DEFAULT = "default"
    MINIMAL = "minimal"
    CYBERPUNK = "cyberpunk"
    RETRO = "retro"
    MATRIX = "matrix"


@dataclass
class ASCIIFrame:
    """Single frame of ASCII art."""
    content: str
    duration: float = 0.1  # Duration in seconds
    colors: Optional[Dict[str, str]] = None


class ASCIIAnimation:
    """ASCII art animation container."""
    
    def __init__(self, frames: List[ASCIIFrame], loop: bool = False):
        self.frames = frames
        self.loop = loop
        self.current_frame = 0
    
    def get_next_frame(self) -> Optional[ASCIIFrame]:
        """Get the next frame in the animation."""
        if self.current_frame >= len(self.frames):
            if self.loop:
                self.current_frame = 0
            else:
                return None
        
        frame = self.frames[self.current_frame]
        self.current_frame += 1
        return frame
    
    def reset(self):
        """Reset animation to first frame."""
        self.current_frame = 0


class ASCIIArtRenderer:
    """ASCII art renderer with animation support."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.themes = self._initialize_themes()
        self.current_theme = LogoTheme.DEFAULT
    
    def _initialize_themes(self) -> Dict[LogoTheme, Dict[str, str]]:
        """Initialize ASCII art themes."""
        return {
            LogoTheme.DEFAULT: {
                "logo": self._get_default_logo(),
                "colors": {
                    "primary": "cyan",
                    "secondary": "blue", 
                    "accent": "bright_cyan"
                }
            },
            LogoTheme.MINIMAL: {
                "logo": self._get_minimal_logo(),
                "colors": {
                    "primary": "white",
                    "secondary": "dim",
                    "accent": "bright_white"
                }
            },
            LogoTheme.CYBERPUNK: {
                "logo": self._get_cyberpunk_logo(),
                "colors": {
                    "primary": "bright_magenta",
                    "secondary": "magenta",
                    "accent": "bright_cyan"
                }
            },
            LogoTheme.RETRO: {
                "logo": self._get_retro_logo(),
                "colors": {
                    "primary": "bright_yellow",
                    "secondary": "yellow",
                    "accent": "bright_green"
                }
            },
            LogoTheme.MATRIX: {
                "logo": self._get_matrix_logo(),
                "colors": {
                    "primary": "bright_green",
                    "secondary": "green",
                    "accent": "bright_cyan"
                }
            }
        }
    
    def _get_default_logo(self) -> str:
        """Get default Codexa logo."""
        return '''
 ██████╗ ██████╗ ██████╗ ███████╗██╗  ██╗ █████╗ 
██╔════╝██╔═══██╗██╔══██╗██╔════╝╚██╗██╔╝██╔══██╗
██║     ██║   ██║██║  ██║█████╗   ╚███╔╝ ███████║
██║     ██║   ██║██║  ██║██╔══╝   ██╔██╗ ██╔══██║
╚██████╗╚██████╔╝██████╔╝███████╗██╔╝ ██╗██║  ██║
 ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝
        '''
    
    def _get_minimal_logo(self) -> str:
        """Get minimal Codexa logo."""
        return '''
╭─────────────────────────────────────╮
│    C O D E X A                      │
│    AI-Powered Coding Assistant      │
╰─────────────────────────────────────╯
        '''
    
    def _get_cyberpunk_logo(self) -> str:
        """Get cyberpunk-themed logo."""
        return '''
╔══════════════════════════════════════╗
║ ██████╗ ██████╗ ██████╗ ███████╗██╗  ║
║██╔════╝██╔═══██╗██╔══██╗██╔════╝╚██╗ ║
║██║     ██║   ██║██║  ██║█████╗   ╚██║ ║
║██║     ██║   ██║██║  ██║██╔══╝   ██╔╝ ║
║╚██████╗╚██████╔╝██████╔╝███████╗██╔╝  ║
║ ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝   ║
║  ██╗  ██╗ █████╗     [NEURAL LINK]   ║
║  ╚██╗██╔╝██╔══██╗    [ACTIVE]        ║
║   ╚███╔╝ ███████║                    ║
║   ██╔██╗ ██╔══██║    > jack_in()     ║
║  ██╔╝ ██╗██║  ██║                    ║
║  ╚═╝  ╚═╝╚═╝  ╚═╝                    ║
╚══════════════════════════════════════╝
        '''
    
    def _get_retro_logo(self) -> str:
        """Get retro-themed logo."""
        return '''
████████████████████████████████████████
█  ▄▄▄▄  ▄▄▄▄   ▄▄▄▄  ▄▄▄▄▄ █▄   ▄  ▄▄▄█
█ █     █    █ █      █     ██ █▄█ █ █  █
█ █     █    █ █      █▄▄▄▄ ██  █  █ ████
█ █     █    █ █      █     ██ █▄█ █ █  █
█  ▀▀▀▀   ▀▀▀▀   ▀▀▀▀  ▀▀▀▀▀ █▀   ▀  ▀▀▀█
████████████████████████████████████████
        '''
    
    def _get_matrix_logo(self) -> str:
        """Get Matrix-themed logo."""
        return '''
╔═══════════════════════════════════════╗
║  ╓─╖ ╓─╖ ╓─╖ ╓─╖ ╓─╖ ╓─╖             ║
║  ║C║ ║O║ ║D║ ║E║ ║X║ ║A║     ██████  ║
║  ╙─╜ ╙─╜ ╙─╜ ╙─╜ ╙─╜ ╙─╜     ██  ██  ║
║                               ██████  ║
║  [MATRIX PROTOCOL ACTIVE]     ██      ║
║  [NEURAL INTERFACE] >>> OK    ██      ║
║  [CIPHER MODE]      >>> ON            ║
║  [REALITY.EXE]      >>> LOADING...    ║
║                                       ║
║  FOLLOW THE WHITE RABBIT...           ║
╚═══════════════════════════════════════╝
        '''
    
    def set_theme(self, theme: LogoTheme):
        """Set the current theme."""
        self.current_theme = theme
    
    def render_logo(self, theme: Optional[LogoTheme] = None, 
                   show_info: bool = True) -> str:
        """Render the logo with optional theme."""
        theme = theme or self.current_theme
        theme_data = self.themes[theme]
        
        logo = theme_data["logo"]
        colors = theme_data["colors"]
        
        # Apply colors to logo
        colored_logo = f"[{colors['primary']}]{logo}[/{colors['primary']}]"
        
        # Add info section if requested
        if show_info:
            info = f"""
[{colors['secondary']}]AI-Powered Coding Assistant[/{colors['secondary']}]
[{colors['accent']}]Ready to build amazing software! 🚀[/{colors['accent']}]
            """
            colored_logo += info
        
        return colored_logo
    
    def create_startup_animation(self, theme: Optional[LogoTheme] = None) -> ASCIIAnimation:
        """Create startup animation sequence."""
        theme = theme or self.current_theme
        theme_data = self.themes[theme]
        colors = theme_data["colors"]
        
        frames = []
        
        # Frame 1: Loading dots
        frames.append(ASCIIFrame(
            content=f"[{colors['primary']}]Starting Codexa.[/{colors['primary']}]",
            duration=0.5
        ))
        
        frames.append(ASCIIFrame(
            content=f"[{colors['primary']}]Starting Codexa..[/{colors['primary']}]",
            duration=0.5
        ))
        
        frames.append(ASCIIFrame(
            content=f"[{colors['primary']}]Starting Codexa...[/{colors['primary']}]",
            duration=0.5
        ))
        
        # Frame 2: Logo reveal
        frames.append(ASCIIFrame(
            content=self.render_logo(theme, show_info=False),
            duration=1.0
        ))
        
        # Frame 3: Full logo with info
        frames.append(ASCIIFrame(
            content=self.render_logo(theme, show_info=True),
            duration=2.0
        ))
        
        # Frame 4: System status
        status_text = f"""
{self.render_logo(theme, show_info=False)}

[{colors['secondary']}]System Status:[/{colors['secondary']}]
[{colors['accent']}]✓[/{colors['accent']}] Core systems initialized
[{colors['accent']}]✓[/{colors['accent']}] AI providers configured  
[{colors['accent']}]✓[/{colors['accent']}] MCP servers ready
[{colors['accent']}]✓[/{colors['accent']}] Ready for commands

[{colors['primary']}]Welcome to the future of coding![/{colors['primary']}]
        """
        
        frames.append(ASCIIFrame(
            content=status_text,
            duration=1.5
        ))
        
        return ASCIIAnimation(frames)
    
    def create_typewriter_effect(self, text: str, 
                                char_delay: float = 0.05) -> ASCIIAnimation:
        """Create typewriter effect animation."""
        frames = []
        
        for i in range(len(text) + 1):
            frame_text = text[:i]
            if i < len(text):
                frame_text += "█"  # Cursor
            
            frames.append(ASCIIFrame(
                content=frame_text,
                duration=char_delay
            ))
        
        return ASCIIAnimation(frames)
    
    def create_matrix_rain(self, width: int = 80, height: int = 20) -> ASCIIAnimation:
        """Create Matrix-style digital rain effect."""
        import random
        import string
        
        frames = []
        
        # Initialize rain columns
        columns = []
        for _ in range(width):
            columns.append({
                "chars": [],
                "speed": random.uniform(0.5, 2.0),
                "y": random.randint(-height, 0)
            })
        
        # Generate frames
        for frame_num in range(60):  # 60 frames (~3 seconds at 20fps)
            frame_lines = []
            
            for row in range(height):
                line = ""
                for col in range(width):
                    column = columns[col]
                    
                    if row >= column["y"] and row < column["y"] + 10:
                        # Show character
                        char = random.choice(string.ascii_letters + string.digits)
                        if row == column["y"]:
                            line += f"[bright_green]{char}[/bright_green]"
                        elif row < column["y"] + 3:
                            line += f"[green]{char}[/green]"
                        else:
                            line += f"[dim]{char}[/dim]"
                    else:
                        line += " "
                
                frame_lines.append(line)
            
            # Update column positions
            for column in columns:
                column["y"] += column["speed"]
                if column["y"] > height:
                    column["y"] = random.randint(-height, -5)
            
            frames.append(ASCIIFrame(
                content="\n".join(frame_lines),
                duration=0.05
            ))
        
        return ASCIIAnimation(frames, loop=True)
    
    def play_animation(self, animation: ASCIIAnimation, 
                      clear_screen: bool = True):
        """Play an ASCII animation."""
        animation.reset()
        
        try:
            while True:
                frame = animation.get_next_frame()
                if frame is None:
                    break
                
                if clear_screen:
                    self.console.clear()
                
                self.console.print(frame.content)
                time.sleep(frame.duration)
                
        except KeyboardInterrupt:
            pass
    
    def render_panel(self, content: str, title: str = "", 
                    border_style: str = "blue") -> Panel:
        """Render content in a styled panel."""
        return Panel(
            Align.center(content),
            title=title,
            border_style=border_style,
            padding=(1, 2)
        )
    
    def get_available_themes(self) -> List[str]:
        """Get list of available theme names."""
        return [theme.value for theme in LogoTheme]