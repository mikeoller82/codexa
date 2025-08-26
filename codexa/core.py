"""Core Codexa agent implementation."""

import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import yaml

from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown

from .config import Config
from .providers import ProviderFactory
from .planning import PlanningManager
from .execution import TaskExecutionManager
from .codegen import CodeGenerator

console = Console()


class CodexaAgent:
    """Main Codexa agent that handles project initialization and interaction."""

    def __init__(self):
        """Initialize the Codexa agent."""
        self.config = Config()
        self.provider = ProviderFactory.create_provider(self.config)
        self.cwd = Path.cwd()
        self.codexa_dir = self.cwd / ".codexa"
        self.history: List[Dict] = []
        
        if not self.provider:
            raise Exception("No AI provider available. Please configure your API keys.")
        
        # Initialize planning manager
        self.planning_manager = PlanningManager(self.codexa_dir, self.provider)
        
        # Initialize execution manager and code generator
        self.execution_manager = TaskExecutionManager(self.codexa_dir, self.provider)
        self.code_generator = CodeGenerator(self.cwd, self.provider)

    def start_session(self) -> None:
        """Start an interactive Codexa session."""
        # Initialize project if needed
        self.initialize_project()
        
        # Welcome message
        self._show_welcome()
        
        # Main interaction loop
        while True:
            try:
                user_input = Prompt.ask("\n[bold cyan]codexa>[/bold cyan]").strip()
                
                if user_input.lower() in ["exit", "quit", "bye"]:
                    console.print("\n[yellow]Goodbye! Happy coding! 🚀[/yellow]")
                    break
                
                if not user_input:
                    continue
                
                # Handle special commands
                if user_input.startswith("/"):
                    # Try managers in order: planning -> execution -> core
                    if not self.planning_manager.handle_command(user_input):
                        if not self.execution_manager.handle_task_command(user_input):
                            self._handle_command(user_input)
                else:
                    # Handle natural language request
                    self._handle_request(user_input)
                    
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' to quit properly.[/yellow]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

    def initialize_project(self) -> None:
        """Initialize Codexa in the current project."""
        # Create CODEXA.md if it doesn't exist
        codexa_md_path = self.cwd / "CODEXA.md"
        if not codexa_md_path.exists():
            self._create_codexa_md()
        
        # Create .codexa directory
        self.codexa_dir.mkdir(exist_ok=True)
        
        # Create .gitignore entry for .codexa if .git exists
        if (self.cwd / ".git").exists():
            self._update_gitignore()

    def _create_codexa_md(self) -> None:
        """Create the CODEXA.md file with project guidelines."""
        codexa_md_content = f"""# Codexa Guidelines

Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Project: {self.cwd.name}

## Role Definition
Codexa acts as a proactive AI coding assistant for this project, following these principles:

### Coding Philosophy
- Write clean, readable, and maintainable code
- Follow established patterns and conventions
- Prioritize code quality and best practices
- Include comprehensive testing and documentation
- Consider scalability and performance implications

### Development Approach  
- Break down complex tasks into manageable steps
- Create structured plans before implementation
- Generate detailed technical requirements
- Provide clear task breakdowns with priorities
- Maintain project context and consistency

### Communication Style
- Be proactive in suggesting improvements
- Explain reasoning behind architectural decisions
- Provide multiple solution options when appropriate
- Ask clarifying questions to ensure requirements are clear
- Offer guidance on best practices and industry standards

### Project Standards
- Code Style: Clean and consistent formatting
- Testing: Comprehensive unit and integration tests
- Documentation: Clear inline comments and README updates
- Version Control: Meaningful commit messages and PR descriptions
- Security: Follow security best practices for the technology stack

## Project Context
This project is located at: `{self.cwd}`

Codexa will adapt its assistance based on the detected technology stack and project structure.

---
*This file was automatically generated by Codexa. Modify it to customize how Codexa behaves in this project.*"""

        codexa_md_path = self.cwd / "CODEXA.md"
        with open(codexa_md_path, "w", encoding="utf-8") as f:
            f.write(codexa_md_content)
        
        console.print(f"[green]✅ Created CODEXA.md with project guidelines[/green]")

    def _update_gitignore(self) -> None:
        """Add .codexa to .gitignore if it's not already there."""
        gitignore_path = self.cwd / ".gitignore"
        
        # Read existing .gitignore
        existing_content = ""
        if gitignore_path.exists():
            with open(gitignore_path, "r", encoding="utf-8") as f:
                existing_content = f.read()
        
        # Check if .codexa is already ignored
        if ".codexa/" not in existing_content and ".codexa" not in existing_content:
            # Add .codexa to .gitignore
            with open(gitignore_path, "a", encoding="utf-8") as f:
                f.write("\n# Codexa working directory\n.codexa/\n")
            console.print("[dim]Added .codexa/ to .gitignore[/dim]")

    def _show_welcome(self) -> None:
        """Show welcome message and project status."""
        # Check if we're in an active workflow
        workflow_status = ""
        if self.planning_manager.is_in_workflow():
            state = self.planning_manager.get_current_state().value
            workflow_status = f"\n[yellow]Active workflow:[/yellow] {state}"
        
        welcome_text = f"""[bold cyan]Codexa[/bold cyan] - AI Coding Assistant

[blue]Project:[/blue] {self.cwd.name}
[blue]Directory:[/blue] {self.cwd}
[blue]Provider:[/blue] {self.config.get_provider()}{workflow_status}

[bold]Natural Language:[/bold] Describe what you want to build
[bold]Commands:[/bold]
• [cyan]/help[/cyan] - Show available commands
• [cyan]/status[/cyan] - Show workflow status  
• [cyan]/workflow[/cyan] - Learn about structured planning
• [cyan]exit[/cyan] - Quit Codexa

Ready to help you build amazing software! 🚀"""
        
        console.print(Panel(welcome_text, border_style="blue", padding=(1, 2)))

    def _handle_command(self, command: str) -> None:
        """Handle special commands starting with /."""
        parts = command[1:].split()
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        if cmd == "help":
            self._show_help()
        elif cmd == "status":
            self._show_status()
        elif cmd == "reset":
            self._reset_session()
        else:
            console.print(f"[red]Unknown command: /{cmd}[/red]")
            console.print("Type [cyan]/help[/cyan] for available commands.")

    def _handle_request(self, request: str) -> None:
        """Handle a natural language request from the user."""
        console.print(f"\n[dim]Processing request...[/dim]")
        
        # Get project context
        context = self._get_project_context()
        
        # Try planning workflow first
        if self.planning_manager.handle_request(request, context):
            # Planning workflow was initiated, no need for direct response
            return
        
        # Check if this is a code generation request
        if self._is_code_generation_request(request):
            self._handle_code_generation_request(request, context)
        else:
            # Handle as regular natural language request
            response = self.provider.ask(
                prompt=request,
                history=self.history,
                context=context
            )
            
            # Display response
            console.print("\n[bold green]Codexa:[/bold green]")
            console.print(Markdown(response))
            
            # Save to history
            self.history.append({
                "user": request,
                "assistant": response,
                "timestamp": datetime.now().isoformat()
            })


    def _get_project_context(self) -> str:
        """Get context about the current project."""
        context_parts = []
        
        # Add CODEXA.md content
        codexa_md = self.cwd / "CODEXA.md"
        if codexa_md.exists():
            with open(codexa_md, "r", encoding="utf-8") as f:
                context_parts.append(f"Project Guidelines:\n{f.read()}")
        
        # Add basic project info
        context_parts.append(f"Current Directory: {self.cwd}")
        
        # Add file listing (basic)
        files = []
        for item in self.cwd.iterdir():
            if not item.name.startswith('.') and item.is_file():
                files.append(item.name)
        
        if files:
            context_parts.append(f"Files in project: {', '.join(files[:10])}")
        
        return "\n\n".join(context_parts)

    def _show_help(self) -> None:
        """Show help information."""
        help_text = """[bold]Available Commands:[/bold]

[cyan]/help[/cyan]      - Show this help message
[cyan]/status[/cyan]    - Show workflow and project status
[cyan]/workflow[/cyan]  - Learn about structured planning
[cyan]/reset[/cyan]     - Reset conversation history
[cyan]exit[/cyan]       - Exit Codexa

[bold]Planning Commands:[/bold]
[cyan]/approve[/cyan]   - Approve current stage (plan/requirements)
[cyan]/revise[/cyan]    - Request changes with feedback
[cyan]/cancel[/cyan]    - Cancel current workflow

[bold]Task Execution Commands:[/bold]
[cyan]/next-task[/cyan]     - Start the next pending task
[cyan]/tasks[/cyan]         - Show all tasks organized by section  
[cyan]/task-status[/cyan]   - Show task progress overview
[cyan]/complete-task[/cyan] - Mark current task as completed
[cyan]/start-task <id>[/cyan] - Start a specific task by ID

[bold]Natural Language:[/bold]
Just type your request naturally, like:
• "Build a React app with authentication and dashboard"
• "Create a login component in React"
• "Generate a Flask API endpoint for users"  
• "Write a config.json file"
• "Explain this code snippet"
• "Help me debug this error"

Large requests trigger planning, code requests create files."""

        console.print(Panel(help_text, title="Help", border_style="cyan"))

    def _show_status(self) -> None:
        """Show current project status."""
        status_parts = []
        
        # Project info
        status_parts.append(f"[blue]Project:[/blue] {self.cwd.name}")
        status_parts.append(f"[blue]Directory:[/blue] {self.cwd}")
        
        # Planning workflow status
        if self.planning_manager.is_in_workflow():
            state = self.planning_manager.get_current_state().value
            status_parts.append(f"[yellow]Planning State:[/yellow] {state}")
        else:
            status_parts.append("[blue]Planning State:[/blue] idle")
        
        # Task execution status
        if self.execution_manager.has_tasks():
            completion_rate = self.execution_manager.get_completion_rate()
            status_parts.append(f"[green]Task Progress:[/green] {completion_rate:.1f}% completed")
            
            current_task = self.execution_manager.get_current_task()
            if current_task:
                status_parts.append(f"[yellow]Current Task:[/yellow] {current_task['text'][:50]}...")
        else:
            status_parts.append("[blue]Tasks:[/blue] None available")
        
        # Files in .codexa
        codexa_files = []
        if self.codexa_dir.exists():
            for file in self.codexa_dir.iterdir():
                if file.is_file() and file.suffix == '.md':
                    codexa_files.append(file.name)
        
        if codexa_files:
            status_parts.append(f"[blue]Planning Files:[/blue] {', '.join(codexa_files)}")
        
        # Code generation status
        created_files = self.code_generator.get_created_files()
        if created_files:
            status_parts.append(f"[green]Files Created:[/green] {len(created_files)} this session")
        
        # Conversation history
        status_parts.append(f"[blue]Messages in History:[/blue] {len(self.history)}")
        
        console.print(Panel("\n".join(status_parts), title="Project Status", border_style="blue"))


    def _reset_session(self) -> None:
        """Reset the conversation history."""
        try:
            if Confirm.ask("Are you sure you want to reset the conversation history?"):
                self.history.clear()
                console.print("[green]✅ Conversation history reset.[/green]")
        except EOFError:
            # Auto-reset in non-interactive mode
            self.history.clear()
            console.print("[green]✅ Conversation history reset.[/green]")

    def _is_code_generation_request(self, request: str) -> bool:
        """Check if the request is asking for code generation."""
        code_keywords = [
            "create", "generate", "write", "implement", "build",
            "add", "make", "code", "function", "class", "component",
            "file", "script", "module", "api", "endpoint", "route"
        ]
        
        file_extensions = [
            ".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css",
            ".scss", ".json", ".yaml", ".yml", ".md", ".rs", ".go"
        ]
        
        request_lower = request.lower()
        
        # Check for code keywords
        has_code_keywords = any(keyword in request_lower for keyword in code_keywords)
        
        # Check for file extensions
        has_file_extensions = any(ext in request_lower for ext in file_extensions)
        
        # Check for specific code-related phrases
        code_phrases = [
            "write a", "create a", "generate a", "build a",
            "implement a", "add a", "make a", "file for",
            "component for", "function to", "class that"
        ]
        
        has_code_phrases = any(phrase in request_lower for phrase in code_phrases)
        
        return has_code_keywords or has_file_extensions or has_code_phrases

    def _handle_code_generation_request(self, request: str, context: str) -> None:
        """Handle a code generation request."""
        console.print("\n[cyan]🔨 Detected code generation request...[/cyan]")
        
        # Parse the request to extract file path and description
        file_path, description = self._parse_code_generation_request(request)
        
        if file_path:
            # Generate specific file
            if self.code_generator.generate_and_create_file(file_path, description, context):
                console.print(f"[green]✅ Successfully created {file_path}![/green]")
                
                # Show file suggestions for next steps
                suggestions = self.code_generator.suggest_next_files(description, context)
                if suggestions:
                    console.print("\n[yellow]💡 Suggested next files:[/yellow]")
                    for suggestion in suggestions[:3]:
                        priority_color = {"high": "red", "medium": "yellow", "low": "dim"}
                        color = priority_color.get(suggestion['priority'], 'white')
                        console.print(f"[{color}]• {suggestion['path']}[/{color}] - {suggestion['description']}")
            else:
                console.print(f"[red]Failed to create {file_path}[/red]")
        else:
            # General code assistance
            response = self.provider.ask(
                prompt=f"Code generation request: {request}\n\nProvide implementation guidance and code examples.\n\n{context}",
                history=self.history,
                context=context
            )
            
            console.print("\n[bold green]Codexa:[/bold green]")
            console.print(Markdown(response))
        
        # Save to history
        self.history.append({
            "user": request,
            "assistant": f"Handled code generation request for: {file_path or 'general assistance'}",
            "timestamp": datetime.now().isoformat()
        })

    def _parse_code_generation_request(self, request: str) -> Tuple[Optional[str], str]:
        """Parse a code generation request to extract file path and description."""
        # Look for explicit file paths
        file_pattern = r'([a-zA-Z0-9_/-]+\.[a-zA-Z0-9]+)'
        file_matches = re.findall(file_pattern, request)
        
        if file_matches:
            return file_matches[0], request
        
        # Try to infer file path from request
        request_lower = request.lower()
        
        # Common patterns
        if "component" in request_lower and ("react" in request_lower or "jsx" in request_lower):
            # Extract component name
            component_match = re.search(r'(\w+)\s*component', request_lower)
            if component_match:
                component_name = component_match.group(1).capitalize()
                return f"src/components/{component_name}.jsx", request
        
        if "api" in request_lower or "endpoint" in request_lower:
            if "python" in request_lower or "flask" in request_lower:
                return "app.py", request
            elif "javascript" in request_lower or "node" in request_lower:
                return "server.js", request
        
        if "style" in request_lower or "css" in request_lower:
            return "styles.css", request
        
        if "config" in request_lower:
            if "json" in request_lower:
                return "config.json", request
            elif "yaml" in request_lower:
                return "config.yaml", request
        
        # Return None for general requests
        return None, request