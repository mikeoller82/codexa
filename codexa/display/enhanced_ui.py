"""
Enhanced UI components for Codexa with modern design and better user experience.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.text import Text
from rich.align import Align
from rich.columns import Columns
from rich.status import Status
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.tree import Tree
from rich import box
from rich.rule import Rule


@dataclass
class UITheme:
    """Enhanced UI theme configuration."""
    name: str
    primary_color: str = "cyan"
    secondary_color: str = "blue"
    accent_color: str = "bright_cyan"
    success_color: str = "green"
    warning_color: str = "yellow"
    error_color: str = "red"
    info_color: str = "blue"
    background_color: str = "black"
    text_color: str = "white"
    border_style: str = "round"
    box_style: str = "round"


class EnhancedUI:
    """Enhanced UI system for Codexa with modern components."""
    
    def __init__(self, console: Optional[Console] = None, theme: Optional[UITheme] = None):
        self.console = console or Console()
        self.theme = theme or UITheme("default")
        self.layout = Layout()
        self._setup_layout()
    
    def _setup_layout(self):
        """Setup the main layout structure."""
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        self.layout["main"].split_row(
            Layout(name="sidebar", size=30),
            Layout(name="content")
        )
    
    def create_header(self, title: str = "Codexa", subtitle: str = "AI-Powered Development Assistant") -> Panel:
        """Create an enhanced header panel."""
        header_text = Text()
        header_text.append(title, style=f"bold {self.theme.primary_color}")
        header_text.append(" - ", style=self.theme.text_color)
        header_text.append(subtitle, style=self.theme.secondary_color)
        
        return Panel(
            Align.center(header_text),
            box=box.DOUBLE,
            style=f"{self.theme.primary_color} on {self.theme.background_color}",
            padding=(0, 1)
        )
    
    def create_footer(self, status: str = "Ready", version: str = "1.0.1") -> Panel:
        """Create an enhanced footer panel."""
        footer_text = Text()
        footer_text.append("Status: ", style="bold")
        footer_text.append(status, style=self.theme.success_color)
        footer_text.append(" | ", style=self.theme.text_color)
        footer_text.append("Version: ", style="bold")
        footer_text.append(version, style=self.theme.info_color)
        
        return Panel(
            Align.center(footer_text),
            box=box.SIMPLE,
            style=f"{self.theme.secondary_color} on {self.theme.background_color}",
            padding=(0, 1)
        )
    
    def create_sidebar(self, items: List[Dict[str, Any]]) -> Panel:
        """Create an enhanced sidebar with navigation items."""
        tree = Tree("📁 Codexa", style=self.theme.primary_color)
        
        for item in items:
            icon = item.get("icon", "📄")
            name = item.get("name", "Item")
            status = item.get("status", "active")
            
            if status == "active":
                style = f"bold {self.theme.accent_color}"
            elif status == "disabled":
                style = "dim"
            else:
                style = self.theme.text_color
            
            node = tree.add(f"{icon} {name}", style=style)
            
            # Add sub-items if available
            sub_items = item.get("sub_items", [])
            for sub_item in sub_items:
                sub_icon = sub_item.get("icon", "•")
                sub_name = sub_item.get("name", "Sub-item")
                sub_node = node.add(f"{sub_icon} {sub_name}", style=self.theme.text_color)
        
        return Panel(
            tree,
            title="[bold]Navigation[/bold]",
            box=getattr(box, self.theme.box_style.upper(), box.ROUNDED),
            style=f"{self.theme.primary_color} on {self.theme.background_color}",
            padding=(1, 1)
        )
    
    def create_status_table(self, data: Dict[str, Any]) -> Table:
        """Create a status table with system information."""
        table = Table(
            title="[bold]System Status[/bold]",
            box=getattr(box, self.theme.box_style.upper(), box.ROUNDED),
            show_header=True,
            header_style=f"bold {self.theme.primary_color}"
        )
        
        table.add_column("Component", style=self.theme.text_color)
        table.add_column("Status", style=self.theme.text_color)
        table.add_column("Details", style=self.theme.text_color)
        
        for component, info in data.items():
            status = info.get("status", "unknown")
            details = info.get("details", "")
            
            if status == "active":
                status_style = f"bold {self.theme.success_color}"
                status_text = "✅ Active"
            elif status == "error":
                status_style = f"bold {self.theme.error_color}"
                status_text = "❌ Error"
            elif status == "warning":
                status_style = f"bold {self.theme.warning_color}"
                status_text = "⚠️ Warning"
            else:
                status_style = self.theme.text_color
                status_text = f"❓ {status.title()}"
            
            table.add_row(
                component,
                Text(status_text, style=status_style),
                details
            )
        
        return table
    
    def create_progress_dashboard(self, tasks: List[Dict[str, Any]]) -> Panel:
        """Create a progress dashboard with multiple tasks."""
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        )
        
        task_ids = []
        for task in tasks:
            task_id = progress.add_task(
                task.get("description", "Processing..."),
                total=task.get("total", 100),
                completed=task.get("completed", 0)
            )
            task_ids.append(task_id)
        
        return Panel(
            progress,
            title="[bold]Progress Dashboard[/bold]",
            box=getattr(box, self.theme.box_style.upper(), box.ROUNDED),
            style=f"{self.theme.primary_color} on {self.theme.background_color}",
            padding=(1, 1)
        )
    
    def create_code_display(self, code: str, language: str = "python", title: str = "Code") -> Panel:
        """Create a syntax-highlighted code display."""
        syntax = Syntax(code, language, theme="monokai", line_numbers=True)
        
        return Panel(
            syntax,
            title=f"[bold]{title}[/bold]",
            box=getattr(box, self.theme.box_style.upper(), box.ROUNDED),
            style=f"{self.theme.primary_color} on {self.theme.background_color}",
            padding=(1, 1)
        )
    
    def create_info_cards(self, cards: List[Dict[str, Any]]) -> Columns:
        """Create information cards in columns."""
        panels = []
        
        for card in cards:
            title = card.get("title", "Info")
            content = card.get("content", "")
            color = card.get("color", self.theme.primary_color)
            
            panel = Panel(
                content,
                title=f"[bold]{title}[/bold]",
                box=getattr(box, self.theme.box_style.upper(), box.ROUNDED),
                style=f"{color} on {self.theme.background_color}",
                padding=(1, 1)
            )
            panels.append(panel)
        
        return Columns(panels, equal=True, expand=True)
    
    def create_interactive_menu(self, options: List[Dict[str, Any]], title: str = "Menu") -> str:
        """Create an interactive menu with rich formatting."""
        self.console.print(f"\n[bold {self.theme.primary_color}]{title}[/bold {self.theme.primary_color}]")
        self.console.print(Rule(style=self.theme.secondary_color))
        
        for i, option in enumerate(options, 1):
            icon = option.get("icon", "•")
            name = option.get("name", f"Option {i}")
            description = option.get("description", "")
            
            self.console.print(f"[{self.theme.accent_color}]{i}.[/{self.theme.accent_color}] {icon} [bold]{name}[/bold]")
            if description:
                self.console.print(f"   [dim]{description}[/dim]")
        
        self.console.print(Rule(style=self.theme.secondary_color))
        
        while True:
            try:
                choice = Prompt.ask(
                    f"[{self.theme.primary_color}]Select an option[/{self.theme.primary_color}]",
                    choices=[str(i) for i in range(1, len(options) + 1)],
                    default="1"
                )
                return options[int(choice) - 1].get("value", choice)
            except KeyboardInterrupt:
                return ""
    
    def create_confirmation_dialog(self, message: str, default: bool = True) -> bool:
        """Create a confirmation dialog with rich formatting."""
        self.console.print(f"\n[{self.theme.warning_color}]⚠️ {message}[/{self.theme.warning_color}]")
        return Confirm.ask(
            f"[{self.theme.primary_color}]Continue?[/{self.theme.primary_color}]",
            default=default
        )
    
    def create_loading_screen(self, message: str = "Loading...") -> Status:
        """Create a loading screen with spinner."""
        return Status(message, spinner="dots", console=self.console)
    
    def create_success_message(self, message: str, details: Optional[str] = None) -> Panel:
        """Create a success message panel."""
        content = Text()
        content.append("✅ ", style=f"bold {self.theme.success_color}")
        content.append(message, style=f"bold {self.theme.success_color}")
        
        if details:
            content.append(f"\n\n{details}", style=self.theme.text_color)
        
        return Panel(
            content,
            box=getattr(box, self.theme.box_style.upper(), box.ROUNDED),
            style=f"{self.theme.success_color} on {self.theme.background_color}",
            padding=(1, 1)
        )
    
    def create_error_message(self, message: str, details: Optional[str] = None) -> Panel:
        """Create an error message panel."""
        content = Text()
        content.append("❌ ", style=f"bold {self.theme.error_color}")
        content.append(message, style=f"bold {self.theme.error_color}")
        
        if details:
            content.append(f"\n\n{details}", style=self.theme.text_color)
        
        return Panel(
            content,
            box=getattr(box, self.theme.box_style.upper(), box.ROUNDED),
            style=f"{self.theme.error_color} on {self.theme.background_color}",
            padding=(1, 1)
        )
    
    def create_warning_message(self, message: str, details: Optional[str] = None) -> Panel:
        """Create a warning message panel."""
        content = Text()
        content.append("⚠️ ", style=f"bold {self.theme.warning_color}")
        content.append(message, style=f"bold {self.theme.warning_color}")
        
        if details:
            content.append(f"\n\n{details}", style=self.theme.text_color)
        
        return Panel(
            content,
            box=getattr(box, self.theme.box_style.upper(), box.ROUNDED),
            style=f"{self.theme.warning_color} on {self.theme.background_color}",
            padding=(1, 1)
        )
    
    def create_info_message(self, message: str, details: Optional[str] = None) -> Panel:
        """Create an info message panel."""
        content = Text()
        content.append("ℹ️ ", style=f"bold {self.theme.info_color}")
        content.append(message, style=f"bold {self.theme.info_color}")
        
        if details:
            content.append(f"\n\n{details}", style=self.theme.text_color)
        
        return Panel(
            content,
            box=getattr(box, self.theme.box_style.upper(), box.ROUNDED),
            style=f"{self.theme.info_color} on {self.theme.background_color}",
            padding=(1, 1)
        )
    
    def display_full_interface(self, 
                              title: str = "Codexa",
                              subtitle: str = "AI-Powered Development Assistant",
                              sidebar_items: Optional[List[Dict[str, Any]]] = None,
                              status_data: Optional[Dict[str, Any]] = None,
                              content: Optional[str] = None):
        """Display the full enhanced interface."""
        # Setup layout content
        self.layout["header"].update(self.create_header(title, subtitle))
        self.layout["footer"].update(self.create_footer())
        
        if sidebar_items:
            self.layout["sidebar"].update(self.create_sidebar(sidebar_items))
        
        if status_data:
            status_table = self.create_status_table(status_data)
            self.layout["content"].update(status_table)
        elif content:
            self.layout["content"].update(Panel(content, box=getattr(box, self.theme.box_style.upper(), box.ROUNDED)))
        
        # Display the layout
        with Live(self.layout, console=self.console, refresh_per_second=4) as live:
            return live
    
    def clear_screen(self):
        """Clear the console screen."""
        self.console.clear()
    
    def print_separator(self, char: str = "─", style: Optional[str] = None):
        """Print a separator line."""
        style = style or self.theme.secondary_color
        self.console.print(char * self.console.size.width, style=style)


# Predefined themes
THEMES = {
    "default": UITheme("default"),
    "cyberpunk": UITheme(
        "cyberpunk",
        primary_color="bright_magenta",
        secondary_color="bright_blue",
        accent_color="bright_cyan",
        success_color="bright_green",
        warning_color="bright_yellow",
        error_color="bright_red",
        info_color="bright_blue"
    ),
    "retro": UITheme(
        "retro",
        primary_color="yellow",
        secondary_color="bright_yellow",
        accent_color="bright_white",
        success_color="green",
        warning_color="yellow",
        error_color="red",
        info_color="blue"
    ),
    "matrix": UITheme(
        "matrix",
        primary_color="green",
        secondary_color="bright_green",
        accent_color="white",
        success_color="bright_green",
        warning_color="yellow",
        error_color="red",
        info_color="cyan"
    )
}


def get_theme(theme_name: str) -> UITheme:
    """Get a theme by name."""
    return THEMES.get(theme_name, THEMES["default"])


def create_enhanced_ui(theme_name: str = "default", console: Optional[Console] = None) -> EnhancedUI:
    """Create an enhanced UI instance with the specified theme."""
    theme = get_theme(theme_name)
    return EnhancedUI(console, theme)