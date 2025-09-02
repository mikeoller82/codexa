"""
Enhanced startup interface for Codexa with modern UI and better user experience.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.text import Text
from rich.align import Align
from rich.columns import Columns
from rich.status import Status
from rich import box
from rich.rule import Rule

from .enhanced_ui import EnhancedUI, get_theme
from .ascii_art import ASCIIArtRenderer, LogoTheme


class EnhancedStartup:
    """Enhanced startup interface for Codexa."""
    
    def __init__(self, console: Optional[Console] = None, theme: str = "default"):
        self.console = console or Console()
        self.ui = EnhancedUI(console, get_theme(theme))
        self.ascii_renderer = ASCIIArtRenderer(console)
        self.startup_tasks = []
        self.current_task = 0
    
    async def show_startup_sequence(self, 
                                  title: str = "Codexa",
                                  subtitle: str = "AI-Powered Development Assistant",
                                  tasks: Optional[List[Dict[str, Any]]] = None) -> bool:
        """Show the enhanced startup sequence with progress tracking."""
        
        # Default startup tasks
        if tasks is None:
            tasks = [
                {"name": "Initializing Core", "description": "Starting core systems...", "duration": 1.0},
                {"name": "Loading Configuration", "description": "Loading user configuration...", "duration": 0.8},
                {"name": "Connecting to AI Providers", "description": "Establishing AI provider connections...", "duration": 1.5},
                {"name": "Initializing MCP Servers", "description": "Starting MCP server connections...", "duration": 2.0},
                {"name": "Loading Tools", "description": "Loading available tools...", "duration": 1.2},
                {"name": "Setting up UI", "description": "Preparing user interface...", "duration": 0.5},
                {"name": "Ready", "description": "All systems ready!", "duration": 0.3}
            ]
        
        self.startup_tasks = tasks
        
        # Create startup layout
        layout = Layout()
        layout.split_column(
            Layout(name="logo", size=8),
            Layout(name="progress", size=6),
            Layout(name="status", size=3)
        )
        
        # Show logo
        logo_panel = self._create_logo_panel(title, subtitle)
        layout["logo"].update(logo_panel)
        
        # Show initial status
        status_panel = self._create_status_panel("Initializing...", "Starting up Codexa")
        layout["status"].update(status_panel)
        
        # Create progress display
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        )
        
        # Add tasks to progress
        task_ids = []
        for task in tasks:
            task_id = progress.add_task(
                task["description"],
                total=100,
                completed=0
            )
            task_ids.append(task_id)
        
        progress_panel = Panel(
            progress,
            title="[bold]Startup Progress[/bold]",
            box=box.ROUNDED,
            style="cyan on black",
            padding=(1, 1)
        )
        layout["progress"].update(progress_panel)
        
        # Display with live updates
        with Live(layout, console=self.console, refresh_per_second=10) as live:
            # Run startup tasks
            for i, task in enumerate(tasks):
                # Update status
                status_panel = self._create_status_panel(
                    f"Step {i+1}/{len(tasks)}: {task['name']}",
                    task["description"]
                )
                layout["status"].update(status_panel)
                
                # Simulate task progress
                await self._simulate_task_progress(progress, task_ids[i], task["duration"])
                
                # Small delay between tasks
                await asyncio.sleep(0.2)
            
            # Final success message
            status_panel = self._create_status_panel(
                "✅ Ready!",
                "Codexa is ready to assist you with your development tasks"
            )
            layout["status"].update(status_panel)
            
            # Hold the display for a moment
            await asyncio.sleep(1.0)
        
        return True
    
    def _create_logo_panel(self, title: str, subtitle: str) -> Panel:
        """Create the logo panel with ASCII art."""
        # Get ASCII logo
        logo = self.ascii_renderer.render_logo(LogoTheme.DEFAULT)
        
        # Create title text
        title_text = Text()
        title_text.append(title, style="bold cyan")
        title_text.append("\n", style="white")
        title_text.append(subtitle, style="blue")
        
        # Combine logo and title
        content = f"{logo}\n\n{title_text}"
        
        return Panel(
            Align.center(content),
            box=box.DOUBLE,
            style="cyan on black",
            padding=(1, 2)
        )
    
    def _create_status_panel(self, status: str, message: str) -> Panel:
        """Create a status panel."""
        content = Text()
        content.append(status, style="bold cyan")
        content.append("\n", style="white")
        content.append(message, style="white")
        
        return Panel(
            Align.center(content),
            box=box.SIMPLE,
            style="blue on black",
            padding=(0, 1)
        )
    
    async def _simulate_task_progress(self, progress: Progress, task_id: int, duration: float):
        """Simulate task progress with realistic timing."""
        steps = 20
        step_duration = duration / steps
        
        for step in range(steps + 1):
            progress.update(task_id, completed=step * 5)  # 5% per step
            await asyncio.sleep(step_duration)
    
    def show_welcome_screen(self, 
                          title: str = "Welcome to Codexa",
                          features: Optional[List[str]] = None) -> None:
        """Show a welcome screen with features and options."""
        
        if features is None:
            features = [
                "🤖 AI-Powered Code Generation",
                "🔧 Advanced Development Tools",
                "📚 Intelligent Documentation",
                "🔍 Smart Code Analysis",
                "🎨 UI Component Generation",
                "⚡ Real-time Assistance"
            ]
        
        # Create welcome layout
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=4),
            Layout(name="features", size=8),
            Layout(name="footer", size=3)
        )
        
        # Header
        header_text = Text()
        header_text.append(title, style="bold cyan")
        header_text.append("\n", style="white")
        header_text.append("Your AI-powered development assistant", style="blue")
        
        header_panel = Panel(
            Align.center(header_text),
            box=box.DOUBLE,
            style="cyan on black",
            padding=(1, 2)
        )
        layout["header"].update(header_panel)
        
        # Features
        features_text = Text()
        for feature in features:
            features_text.append(f"  {feature}\n", style="white")
        
        features_panel = Panel(
            features_text,
            title="[bold]Key Features[/bold]",
            box=box.ROUNDED,
            style="cyan on black",
            padding=(1, 2)
        )
        layout["features"].update(features_panel)
        
        # Footer
        footer_text = Text()
        footer_text.append("Press any key to continue...", style="dim white")
        
        footer_panel = Panel(
            Align.center(footer_text),
            box=box.SIMPLE,
            style="blue on black",
            padding=(0, 1)
        )
        layout["footer"].update(footer_panel)
        
        # Display
        with Live(layout, console=self.console, refresh_per_second=4) as live:
            # Wait for user input
            try:
                input()
            except KeyboardInterrupt:
                pass
    
    async def show_system_status(self, status_data: Dict[str, Any]) -> None:
        """Show system status with enhanced UI."""
        self.ui.clear_screen()
        
        # Create status layout
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="content"),
            Layout(name="footer", size=2)
        )
        
        # Header
        header = self.ui.create_header("System Status", "Codexa Health Dashboard")
        layout["header"].update(header)
        
        # Content - status table
        status_table = self.ui.create_status_table(status_data)
        layout["content"].update(status_table)
        
        # Footer
        footer = self.ui.create_footer("System monitoring active", "1.0.1")
        layout["footer"].update(footer)
        
        # Display
        with Live(layout, console=self.console, refresh_per_second=2) as live:
            try:
                # Keep updating for a while
                for _ in range(50):  # 25 seconds at 2fps
                    await asyncio.sleep(0.5)
            except KeyboardInterrupt:
                pass
    
    def show_quick_start_guide(self) -> None:
        """Show a quick start guide for new users."""
        guide_content = """
# 🚀 Quick Start Guide

## Getting Started
1. **Ask Questions**: Simply type your question or request
2. **Generate Code**: Ask for code generation in any language
3. **Get Help**: Use `/help` for available commands
4. **Check Status**: Use `/status` to see system information

## Common Commands
- `/help` - Show all available commands
- `/status` - Display system status
- `/provider` - Switch AI providers
- `/clear` - Clear the conversation

## Examples
- "Generate a React component for a login form"
- "Explain this Python code"
- "Create a REST API endpoint"
- "Help me debug this error"

## Tips
- Be specific in your requests
- Include context when asking questions
- Use the enhanced UI features for better experience
        """
        
        self.ui.clear_screen()
        
        # Create guide layout
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="content"),
            Layout(name="footer", size=2)
        )
        
        # Header
        header = self.ui.create_header("Quick Start Guide", "Get up and running with Codexa")
        layout["header"].update(header)
        
        # Content - markdown guide
        from rich.markdown import Markdown
        guide_panel = Panel(
            Markdown(guide_content),
            title="[bold]Guide[/bold]",
            box=box.ROUNDED,
            style="cyan on black",
            padding=(1, 2)
        )
        layout["content"].update(guide_panel)
        
        # Footer
        footer = self.ui.create_footer("Ready to start", "1.0.1")
        layout["footer"].update(footer)
        
        # Display
        with Live(layout, console=self.console, refresh_per_second=4) as live:
            try:
                input("\nPress Enter to continue...")
            except KeyboardInterrupt:
                pass


def create_enhanced_startup(theme: str = "default", console: Optional[Console] = None) -> EnhancedStartup:
    """Create an enhanced startup instance."""
    return EnhancedStartup(console, theme)