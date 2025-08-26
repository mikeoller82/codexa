"""
Animation engine for Codexa startup and interactive elements.
"""

import time
import asyncio
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel

from .ascii_art import ASCIIArtRenderer, LogoTheme, ASCIIAnimation


class AnimationState(Enum):
    """Animation states."""
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class AnimationStep:
    """Individual animation step."""
    name: str
    content: str
    duration: float = 1.0
    callback: Optional[Callable] = None
    colors: Optional[Dict[str, str]] = None


class AnimationEngine:
    """Core animation engine for Codexa."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.ascii_renderer = ASCIIArtRenderer(self.console)
        self.state = AnimationState.IDLE
        self.current_animation: Optional[ASCIIAnimation] = None
        self._stop_requested = False
    
    def set_theme(self, theme: LogoTheme):
        """Set animation theme."""
        self.ascii_renderer.set_theme(theme)
    
    async def play_startup_sequence(self, 
                                  theme: Optional[LogoTheme] = None,
                                  show_system_check: bool = True,
                                  interactive: bool = True) -> bool:
        """Play complete startup animation sequence."""
        self.state = AnimationState.PLAYING
        self._stop_requested = False
        
        try:
            # Phase 1: Loading animation
            await self._play_loading_phase()
            
            if self._stop_requested:
                return False
            
            # Phase 2: Logo reveal
            await self._play_logo_reveal(theme)
            
            if self._stop_requested:
                return False
            
            # Phase 3: System check (optional)
            if show_system_check:
                await self._play_system_check()
            
            if self._stop_requested:
                return False
            
            # Phase 4: Welcome message
            await self._play_welcome_message(interactive)
            
            self.state = AnimationState.COMPLETED
            return True
            
        except Exception as e:
            self.state = AnimationState.ERROR
            self.console.print(f"[red]Animation error: {e}[/red]")
            return False
    
    async def _play_loading_phase(self):
        """Play initial loading animation."""
        loading_steps = [
            "Initializing Codexa",
            "Loading AI providers", 
            "Connecting to services",
            "Preparing workspace"
        ]
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True
        ) as progress:
            
            for step in loading_steps:
                if self._stop_requested:
                    break
                    
                task = progress.add_task(f"{step}...", total=None)
                await asyncio.sleep(0.8)  # Simulate loading time
                progress.remove_task(task)
    
    async def _play_logo_reveal(self, theme: Optional[LogoTheme] = None):
        """Play logo reveal animation."""
        self.console.clear()
        
        # Create logo animation
        animation = self.ascii_renderer.create_startup_animation(theme)
        
        # Play each frame
        animation.reset()
        while True:
            if self._stop_requested:
                break
                
            frame = animation.get_next_frame()
            if frame is None:
                break
            
            self.console.clear()
            self.console.print(frame.content)
            await asyncio.sleep(frame.duration)
    
    async def _play_system_check(self):
        """Play system status check animation."""
        checks = [
            ("Core systems", "✓ Initialized", "green"),
            ("AI providers", "✓ Connected", "green"), 
            ("MCP servers", "⚠ Checking", "yellow"),
            ("Project context", "✓ Loaded", "green"),
            ("Command system", "✓ Ready", "green")
        ]
        
        self.console.print("\n[bold cyan]System Status Check:[/bold cyan]")
        
        for name, status, color in checks:
            if self._stop_requested:
                break
                
            # Show checking state first
            self.console.print(f"[dim]⟳ Checking {name}...[/dim]", end="")
            await asyncio.sleep(0.5)
            
            # Clear line and show result
            self.console.print(f"\r[{color}]{status}[/{color}] {name}")
            await asyncio.sleep(0.3)
    
    async def _play_welcome_message(self, interactive: bool = True):
        """Play welcome message with typing effect."""
        welcome_text = """
[bold cyan]Welcome to Codexa![/bold cyan]

Your AI-powered coding assistant is ready to help you build amazing software.

[yellow]Quick Tips:[/yellow]
• Type naturally to describe what you want to build
• Use [cyan]/help[/cyan] to see available commands
• Start with [cyan]/workflow[/cyan] for structured project planning
• Type [cyan]exit[/cyan] when you're done

[bold green]Ready to code? Let's build something awesome! 🚀[/bold green]
        """
        
        if interactive:
            # Typewriter effect
            await self._typewriter_effect(welcome_text)
        else:
            # Just show the message
            self.console.print(welcome_text)
            await asyncio.sleep(2.0)
    
    async def _typewriter_effect(self, text: str, delay: float = 0.02):
        """Create typewriter effect for text."""
        lines = text.split('\n')
        
        for line in lines:
            if self._stop_requested:
                break
                
            current_line = ""
            for char in line:
                if self._stop_requested:
                    break
                    
                current_line += char
                self.console.print(f"\r{current_line}", end="")
                await asyncio.sleep(delay)
            
            self.console.print()  # New line
            await asyncio.sleep(0.1)  # Brief pause between lines
    
    def stop_animation(self):
        """Stop current animation."""
        self._stop_requested = True
        self.state = AnimationState.IDLE
    
    def create_provider_switch_animation(self, old_provider: str, 
                                       new_provider: str) -> ASCIIAnimation:
        """Create provider switching animation."""
        frames = []
        
        # Frame 1: Show current provider
        frames.append({
            "content": f"[blue]Current Provider:[/blue] {old_provider}",
            "duration": 0.5
        })
        
        # Frame 2: Switching animation
        frames.append({
            "content": f"[yellow]Switching providers...[/yellow]",
            "duration": 0.8
        })
        
        # Frame 3: New provider
        frames.append({
            "content": f"[green]✓ Switched to:[/green] {new_provider}",
            "duration": 1.0
        })
        
        return ASCIIAnimation(frames)
    
    def create_loading_spinner(self, message: str = "Loading...") -> Progress:
        """Create a loading spinner with message."""
        return Progress(
            SpinnerColumn(),
            TextColumn(f"[progress.description]{message}"),
            console=self.console,
            transient=True
        )


class StartupAnimation:
    """Specialized startup animation manager."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.engine = AnimationEngine(console)
        self.config = {}
    
    def configure(self, **kwargs):
        """Configure startup animation options."""
        self.config.update(kwargs)
    
    async def run(self, theme: LogoTheme = LogoTheme.DEFAULT,
                 show_system_check: bool = True,
                 interactive: bool = True) -> bool:
        """Run the complete startup animation."""
        
        # Set theme
        self.engine.set_theme(theme)
        
        # Apply configuration
        show_system_check = self.config.get('show_system_check', show_system_check)
        interactive = self.config.get('interactive', interactive)
        
        return await self.engine.play_startup_sequence(
            theme=theme,
            show_system_check=show_system_check,
            interactive=interactive
        )
    
    def quick_start(self) -> bool:
        """Quick startup without animations."""
        self.console.clear()
        
        # Just show the logo
        logo = self.engine.ascii_renderer.render_logo(LogoTheme.MINIMAL)
        panel = Panel(logo, title="Codexa", border_style="cyan")
        self.console.print(panel)
        
        return True
    
    def get_theme_preview(self, theme: LogoTheme) -> str:
        """Get preview of a theme."""
        return self.engine.ascii_renderer.render_logo(theme, show_info=False)