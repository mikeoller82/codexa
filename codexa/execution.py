"""Task execution and tracking for Codexa."""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn
from rich.prompt import Confirm

console = Console()


class TaskStatus(Enum):
    """Status of individual tasks."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class TaskExecutionManager:
    """Manages task execution and progress tracking."""

    def __init__(self, codexa_dir: Path, provider):
        """Initialize the task execution manager."""
        self.codexa_dir = codexa_dir
        self.provider = provider
        self.tasks_file = codexa_dir / "tasks.md"
        self.progress_file = codexa_dir / "task_progress.json"
        self.execution_log_file = codexa_dir / "execution_log.md"
        
        # Task tracking
        self.tasks: List[Dict] = []
        self.task_progress: Dict = {}
        self.current_task_index: int = 0
        
        # Load existing state
        self._load_tasks()
        self._load_progress()

    def _load_tasks(self) -> None:
        """Load tasks from tasks.md file."""
        if not self.tasks_file.exists():
            return
            
        try:
            with open(self.tasks_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse markdown task list
            self.tasks = self._parse_markdown_tasks(content)
            
        except Exception as e:
            console.print(f"[red]Error loading tasks: {e}[/red]")

    def _parse_markdown_tasks(self, content: str) -> List[Dict]:
        """Parse markdown content to extract tasks."""
        tasks = []
        current_section = "General"
        
        lines = content.split('\n')
        task_id = 0
        
        for line in lines:
            # Check for section headers
            if line.startswith('## ') and not line.startswith('## '):
                current_section = line[3:].strip()
            elif line.startswith('### '):
                current_section = line[4:].strip()
            
            # Check for task items (markdown checkboxes)
            task_match = re.match(r'^- \[([ x])\] (.+)$', line.strip())
            if task_match:
                is_completed = task_match.group(1) == 'x'
                task_text = task_match.group(2).strip()
                
                # Extract effort level if present
                effort_match = re.search(r'\((Small|Medium|Large)\)$', task_text)
                effort = effort_match.group(1) if effort_match else "Medium"
                if effort_match:
                    task_text = task_text[:effort_match.start()].strip()
                
                tasks.append({
                    'id': task_id,
                    'section': current_section,
                    'text': task_text,
                    'effort': effort,
                    'status': TaskStatus.COMPLETED if is_completed else TaskStatus.PENDING,
                    'created_at': datetime.now().isoformat()
                })
                task_id += 1
        
        return tasks

    def _load_progress(self) -> None:
        """Load task progress from JSON file."""
        if not self.progress_file.exists():
            self._initialize_progress()
            return
            
        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.task_progress = data.get('tasks', {})
                self.current_task_index = data.get('current_task_index', 0)
                
            # Sync progress with loaded tasks
            self._sync_progress()
            
        except Exception as e:
            console.print(f"[red]Error loading progress: {e}[/red]")
            self._initialize_progress()

    def _initialize_progress(self) -> None:
        """Initialize progress tracking for all tasks."""
        self.task_progress = {}
        for task in self.tasks:
            self.task_progress[str(task['id'])] = {
                'status': task['status'].value,
                'started_at': None,
                'completed_at': None,
                'notes': '',
                'files_created': [],
                'commands_run': []
            }
        self.current_task_index = 0
        self._save_progress()

    def _sync_progress(self) -> None:
        """Sync progress data with current tasks."""
        # Update task statuses from progress
        for task in self.tasks:
            task_id = str(task['id'])
            if task_id in self.task_progress:
                status_str = self.task_progress[task_id]['status']
                task['status'] = TaskStatus(status_str)

    def _save_progress(self) -> None:
        """Save current progress to JSON file."""
        data = {
            'current_task_index': self.current_task_index,
            'last_updated': datetime.now().isoformat(),
            'tasks': self.task_progress
        }
        
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def get_next_task(self) -> Optional[Dict]:
        """Get the next pending task."""
        for i in range(self.current_task_index, len(self.tasks)):
            task = self.tasks[i]
            if task['status'] == TaskStatus.PENDING:
                return task
        
        # Check from beginning if we reached the end
        for i in range(0, self.current_task_index):
            task = self.tasks[i]
            if task['status'] == TaskStatus.PENDING:
                return task
        
        return None

    def get_current_task(self) -> Optional[Dict]:
        """Get the current task in progress."""
        for task in self.tasks:
            if task['status'] == TaskStatus.IN_PROGRESS:
                return task
        return None

    def start_task(self, task_id: int) -> bool:
        """Start working on a specific task."""
        if task_id >= len(self.tasks):
            return False
            
        task = self.tasks[task_id]
        
        # Mark previous in-progress tasks as pending
        for other_task in self.tasks:
            if other_task['status'] == TaskStatus.IN_PROGRESS:
                other_task['status'] = TaskStatus.PENDING
                self.task_progress[str(other_task['id'])]['status'] = TaskStatus.PENDING.value
        
        # Start the new task
        task['status'] = TaskStatus.IN_PROGRESS
        self.current_task_index = task_id
        
        # Update progress tracking
        task_progress = self.task_progress[str(task_id)]
        task_progress['status'] = TaskStatus.IN_PROGRESS.value
        task_progress['started_at'] = datetime.now().isoformat()
        
        self._save_progress()
        return True

    def complete_task(self, task_id: int, notes: str = "", files_created: List[str] = None) -> bool:
        """Mark a task as completed."""
        if task_id >= len(self.tasks):
            return False
            
        task = self.tasks[task_id]
        task['status'] = TaskStatus.COMPLETED
        
        # Update progress tracking
        task_progress = self.task_progress[str(task_id)]
        task_progress['status'] = TaskStatus.COMPLETED.value
        task_progress['completed_at'] = datetime.now().isoformat()
        task_progress['notes'] = notes
        task_progress['files_created'] = files_created or []
        
        self._save_progress()
        self._log_task_completion(task, notes, files_created)
        return True

    def _log_task_completion(self, task: Dict, notes: str, files_created: List[str]) -> None:
        """Log task completion to execution log."""
        log_entry = f"""
## Task Completed: {task['text']}
**Section:** {task['section']}  
**Effort:** {task['effort']}  
**Completed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  

"""
        if notes:
            log_entry += f"**Notes:** {notes}\n\n"
        
        if files_created:
            log_entry += "**Files Created:**\n"
            for file in files_created:
                log_entry += f"- {file}\n"
            log_entry += "\n"
        
        log_entry += "---\n"
        
        # Append to log file
        with open(self.execution_log_file, 'a', encoding='utf-8') as f:
            if not self.execution_log_file.exists() or self.execution_log_file.stat().st_size == 0:
                f.write("# Codexa Execution Log\n\n")
            f.write(log_entry)

    def show_task_status(self) -> None:
        """Display current task status and progress."""
        if not self.tasks:
            console.print("[yellow]No tasks found. Generate a project plan first.[/yellow]")
            return
        
        # Create progress summary
        total_tasks = len(self.tasks)
        completed_tasks = len([t for t in self.tasks if t['status'] == TaskStatus.COMPLETED])
        in_progress_tasks = len([t for t in self.tasks if t['status'] == TaskStatus.IN_PROGRESS])
        pending_tasks = len([t for t in self.tasks if t['status'] == TaskStatus.PENDING])
        
        # Progress bar
        progress_percent = (completed_tasks / total_tasks) * 100
        
        status_info = f"""[bold]Task Progress Overview[/bold]

[blue]Total Tasks:[/blue] {total_tasks}
[green]Completed:[/green] {completed_tasks} ({progress_percent:.1f}%)
[yellow]In Progress:[/yellow] {in_progress_tasks}
[dim]Pending:[/dim] {pending_tasks}

[bold]Progress:[/bold] {"█" * int(progress_percent/5)}{"░" * (20 - int(progress_percent/5))} {progress_percent:.1f}%"""

        # Current task info
        current_task = self.get_current_task()
        if current_task:
            status_info += f"\n\n[bold yellow]Current Task:[/bold yellow]\n{current_task['section']}: {current_task['text']}"
        
        next_task = self.get_next_task()
        if next_task:
            status_info += f"\n\n[bold cyan]Next Task:[/bold cyan]\n{next_task['section']}: {next_task['text']}"

        console.print(Panel(status_info, title="Task Status", border_style="blue"))

    def show_tasks_by_section(self) -> None:
        """Display all tasks organized by section."""
        if not self.tasks:
            console.print("[yellow]No tasks found. Generate a project plan first.[/yellow]")
            return
        
        # Group tasks by section
        sections = {}
        for task in self.tasks:
            section = task['section']
            if section not in sections:
                sections[section] = []
            sections[section].append(task)
        
        # Display each section
        for section_name, section_tasks in sections.items():
            table = Table(title=section_name, show_header=True, header_style="bold magenta")
            table.add_column("ID", style="dim", width=6)
            table.add_column("Status", width=12)
            table.add_column("Task", flex=1)
            table.add_column("Effort", width=8)
            
            for task in section_tasks:
                status_color = {
                    TaskStatus.COMPLETED: "[green]✓ Done[/green]",
                    TaskStatus.IN_PROGRESS: "[yellow]⚡ Active[/yellow]",
                    TaskStatus.PENDING: "[dim]○ Pending[/dim]",
                    TaskStatus.BLOCKED: "[red]⚠ Blocked[/red]",
                    TaskStatus.SKIPPED: "[dim]⊘ Skipped[/dim]"
                }
                
                table.add_row(
                    str(task['id']),
                    status_color[task['status']],
                    task['text'],
                    task['effort']
                )
            
            console.print(table)
            console.print()

    def execute_task(self, task: Dict, project_context: str = "") -> Tuple[str, List[str]]:
        """Execute a task using AI assistance."""
        console.print(f"\n[bold green]🚀 Executing Task:[/bold green] {task['text']}")
        console.print(f"[dim]Section: {task['section']} | Effort: {task['effort']}[/dim]\n")
        
        # Build execution prompt
        execution_prompt = f"""I need help executing this development task:

**Task:** {task['text']}
**Section:** {task['section']}
**Effort Level:** {task['effort']}

Please provide:
1. Step-by-step implementation guidance
2. Code examples if applicable
3. File structure recommendations
4. Commands to run
5. Testing suggestions

Be specific and actionable. Focus on practical implementation.

{f'Project context: {project_context}' if project_context else ''}"""

        try:
            response = self.provider.ask(execution_prompt)
            
            # Display the response
            console.print("[bold green]Implementation Guidance:[/bold green]")
            console.print(Markdown(response))
            
            # Ask if user wants to mark as complete
            files_created = []
            notes = ""
            
            try:
                if Confirm.ask("\nDid this help complete the task?", default=True):
                    try:
                        notes = input("Add any notes (optional): ").strip()
                        files_input = input("List any files created (comma-separated, optional): ").strip()
                        if files_input:
                            files_created = [f.strip() for f in files_input.split(",")]
                    except EOFError:
                        pass
                    
                    return response, files_created
                else:
                    return response, []
                    
            except EOFError:
                # Auto-complete in non-interactive mode
                return response, []
                
        except Exception as e:
            error_msg = f"Error executing task: {e}"
            console.print(f"[red]{error_msg}[/red]")
            return error_msg, []

    def handle_task_command(self, command: str) -> bool:
        """Handle task-related commands."""
        parts = command[1:].split()
        cmd = parts[0].lower()
        
        if cmd == "next-task" or cmd == "next":
            return self._handle_next_task()
        elif cmd == "complete-task" or cmd == "complete":
            task_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
            return self._handle_complete_task(task_id)
        elif cmd == "tasks":
            self.show_tasks_by_section()
            return True
        elif cmd == "task-status":
            self.show_task_status()
            return True
        elif cmd == "start-task":
            task_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
            return self._handle_start_task(task_id)
        
        return False

    def _handle_next_task(self) -> bool:
        """Handle /next-task command."""
        next_task = self.get_next_task()
        
        if not next_task:
            console.print("[yellow]🎉 All tasks completed! Great work![/yellow]")
            return True
        
        # Start the next task
        if self.start_task(next_task['id']):
            console.print(f"[green]📋 Started Task {next_task['id']}:[/green] {next_task['text']}")
            
            # Execute the task
            project_context = self._get_project_context()
            response, files_created = self.execute_task(next_task, project_context)
            
            # If files were created, mark as complete
            if files_created:
                self.complete_task(next_task['id'], "Task completed via /next-task", files_created)
                console.print(f"[green]✅ Task {next_task['id']} marked as completed![/green]")
                
                # Show progress
                self.show_task_status()
        else:
            console.print("[red]Error starting task.[/red]")
        
        return True

    def _handle_complete_task(self, task_id: Optional[int]) -> bool:
        """Handle /complete-task command."""
        # If no task ID provided, complete current task
        if task_id is None:
            current_task = self.get_current_task()
            if not current_task:
                console.print("[yellow]No current task to complete. Use /next-task to start one.[/yellow]")
                return True
            task_id = current_task['id']
        
        if task_id >= len(self.tasks):
            console.print(f"[red]Task {task_id} not found.[/red]")
            return True
        
        task = self.tasks[task_id]
        
        try:
            notes = input(f"Add notes for task '{task['text']}' (optional): ").strip()
            files_input = input("List files created (comma-separated, optional): ").strip()
            files_created = [f.strip() for f in files_input.split(",")] if files_input else []
        except EOFError:
            notes = ""
            files_created = []
        
        if self.complete_task(task_id, notes, files_created):
            console.print(f"[green]✅ Task {task_id} marked as completed![/green]")
            self.show_task_status()
        else:
            console.print("[red]Error completing task.[/red]")
        
        return True

    def _handle_start_task(self, task_id: Optional[int]) -> bool:
        """Handle /start-task command."""
        if task_id is None:
            console.print("[yellow]Please specify a task ID: /start-task <id>[/yellow]")
            return True
        
        if task_id >= len(self.tasks):
            console.print(f"[red]Task {task_id} not found.[/red]")
            return True
        
        task = self.tasks[task_id]
        
        if task['status'] == TaskStatus.COMPLETED:
            console.print(f"[yellow]Task {task_id} is already completed.[/yellow]")
            return True
        
        if self.start_task(task_id):
            console.print(f"[green]📋 Started Task {task_id}:[/green] {task['text']}")
            
            # Execute the task
            project_context = self._get_project_context()
            response, files_created = self.execute_task(task, project_context)
        else:
            console.print("[red]Error starting task.[/red]")
        
        return True

    def _get_project_context(self) -> str:
        """Get project context for task execution."""
        context_parts = []
        
        # Add project guidelines
        codexa_md = self.codexa_dir.parent / "CODEXA.md"
        if codexa_md.exists():
            with open(codexa_md, 'r', encoding='utf-8') as f:
                context_parts.append(f"Project Guidelines:\n{f.read()[:1000]}...")
        
        # Add current plan
        plan_file = self.codexa_dir / "plan.md"
        if plan_file.exists():
            with open(plan_file, 'r', encoding='utf-8') as f:
                context_parts.append(f"Project Plan:\n{f.read()[:1000]}...")
        
        # Add requirements
        req_file = self.codexa_dir / "requirements.md"
        if req_file.exists():
            with open(req_file, 'r', encoding='utf-8') as f:
                context_parts.append(f"Requirements:\n{f.read()[:1000]}...")
        
        return "\n\n".join(context_parts)

    def has_tasks(self) -> bool:
        """Check if there are any tasks available."""
        return len(self.tasks) > 0

    def get_completion_rate(self) -> float:
        """Get the completion rate as a percentage."""
        if not self.tasks:
            return 0.0
        
        completed = len([t for t in self.tasks if t['status'] == TaskStatus.COMPLETED])
        return (completed / len(self.tasks)) * 100