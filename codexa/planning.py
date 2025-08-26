"""Planning and workflow management for Codexa."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Confirm, Prompt

console = Console()


class WorkflowState(Enum):
    """States in the Codexa workflow."""
    IDLE = "idle"
    PLANNING = "planning"
    PLAN_REVIEW = "plan_review"
    REQUIREMENTS = "requirements"
    REQUIREMENTS_REVIEW = "requirements_review"
    TASKS = "tasks"
    EXECUTION = "execution"


class PlanningManager:
    """Manages the structured planning workflow for Codexa."""

    def __init__(self, codexa_dir: Path, provider):
        """Initialize the planning manager."""
        self.codexa_dir = codexa_dir
        self.provider = provider
        self.state = WorkflowState.IDLE
        self.current_request: Optional[str] = None
        self.metadata_file = codexa_dir / "workflow_metadata.json"
        
        # Ensure directory exists
        self.codexa_dir.mkdir(exist_ok=True)
        
        # Load existing state
        self._load_state()

    def _load_state(self) -> None:
        """Load workflow state from metadata file."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    self.state = WorkflowState(metadata.get("state", "idle"))
                    self.current_request = metadata.get("current_request")
            except Exception:
                self.state = WorkflowState.IDLE
                self.current_request = None

    def _save_state(self) -> None:
        """Save current workflow state to metadata file."""
        metadata = {
            "state": self.state.value,
            "current_request": self.current_request,
            "last_updated": datetime.now().isoformat()
        }
        
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

    def handle_request(self, request: str, project_context: str = "") -> bool:
        """
        Handle a user request and determine if it needs structured planning.
        
        Returns True if planning workflow was initiated, False for direct response.
        """
        if self.state != WorkflowState.IDLE:
            console.print(f"[yellow]Currently in {self.state.value} state. Use /status to see options.[/yellow]")
            return False

        # Check if this request needs structured planning
        if self._needs_planning(request):
            console.print("\n[cyan]This looks like a project request that would benefit from structured planning.[/cyan]")
            
            try:
                if Confirm.ask("Would you like me to create a structured plan?", default=True):
                    return self._start_planning_workflow(request, project_context)
                else:
                    # User declined planning, treat as regular request
                    return False
            except EOFError:
                # Non-interactive mode or interrupted input, proceed with planning
                console.print("[yellow]Auto-proceeding with structured planning...[/yellow]")
                return self._start_planning_workflow(request, project_context)
        
        # Not a planning request, handle normally
        return False

    def _needs_planning(self, request: str) -> bool:
        """Determine if a request needs structured planning."""
        # Keywords that suggest project-level work
        project_keywords = [
            "build", "create", "develop", "implement", "make", "design",
            "application", "app", "system", "project", "website", "platform",
            "api", "service", "dashboard", "interface", "architecture",
            "full-stack", "backend", "frontend", "database", "authentication",
            "deployment", "infrastructure", "microservice", "framework"
        ]
        
        # Complexity indicators
        complexity_indicators = [
            "from scratch", "end-to-end", "complete", "comprehensive", 
            "scalable", "production-ready", "enterprise", "multi-user",
            "real-time", "responsive", "secure", "automated"
        ]
        
        request_lower = request.lower()
        
        # Check for project keywords
        has_project_keywords = any(keyword in request_lower for keyword in project_keywords)
        
        # Check for complexity indicators
        has_complexity = any(indicator in request_lower for indicator in complexity_indicators)
        
        # Check for length (longer requests often need planning)
        is_substantial = len(request.split()) > 10
        
        # Return true if it has project keywords and either complexity or length
        return has_project_keywords and (has_complexity or is_substantial)

    def _start_planning_workflow(self, request: str, project_context: str = "") -> bool:
        """Start the structured planning workflow."""
        self.current_request = request
        self.state = WorkflowState.PLANNING
        self._save_state()
        
        console.print("\n[bold green]🎯 Starting structured planning workflow...[/bold green]")
        
        # Generate plan
        plan_content = self._generate_plan(request, project_context)
        
        # Save plan with version
        plan_path = self._save_versioned_file("plan.md", plan_content, request)
        
        console.print(f"\n[green]✅ Plan generated and saved to {plan_path.relative_to(Path.cwd())}[/green]")
        
        # Show the plan
        console.print("\n" + "="*60)
        console.print(Panel(Markdown(plan_content), title="Generated Plan", border_style="green"))
        console.print("="*60)
        
        # Move to review state
        self.state = WorkflowState.PLAN_REVIEW
        self._save_state()
        
        # Ask for approval
        console.print("\n[yellow]Review the plan above. You can:[/yellow]")
        console.print("• [cyan]/approve[/cyan] - Approve and move to requirements")
        console.print("• [cyan]/revise[/cyan] - Request changes to the plan")  
        console.print("• [cyan]/cancel[/cyan] - Cancel planning workflow")
        
        return True

    def _generate_plan(self, request: str, context: str = "") -> str:
        """Generate a comprehensive project plan."""
        plan_prompt = f"""Based on this request: "{request}"

Create a comprehensive project plan with the following structure:

# Project Plan

## Project Overview
Provide a clear, concise description of what we're building. Include the main purpose and target users.

## Goals and Objectives  
List the primary goals and success criteria for this project. What problems are we solving?

## Key Features
Outline the main features and functionalities that need to be implemented. Prioritize them (must-have, nice-to-have).

## Technical Approach
Describe the high-level technical strategy. What technologies, patterns, or architectures will we use?

## Implementation Phases
Break the work down into logical phases (Phase 1, Phase 2, etc.). Each phase should have:
- Clear deliverables
- Dependencies on previous phases
- Estimated effort level (Small/Medium/Large)

## Considerations
- Performance requirements
- Security considerations  
- Scalability needs
- Testing strategy
- Deployment approach

Keep it detailed but concise. Focus on the big picture rather than implementation details.

{f'Project context: {context}' if context else ''}"""

        return self.provider.ask(plan_prompt)

    def _save_versioned_file(self, filename: str, content: str, request: str) -> Path:
        """Save a file with version tracking."""
        timestamp = datetime.now()
        
        # Create the main file
        file_path = self.codexa_dir / filename
        
        # Create version directory if it doesn't exist
        versions_dir = self.codexa_dir / "versions"
        versions_dir.mkdir(exist_ok=True)
        
        # Create versioned filename
        version_timestamp = timestamp.strftime("%Y%m%d_%H%M%S")
        version_filename = f"{filename.replace('.md', '')}_{version_timestamp}.md"
        version_path = versions_dir / version_filename
        
        # Prepare content with metadata
        full_content = f"""# {filename.replace('.md', '').title()}

**Generated:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}
**Request:** {request}
**Version:** {version_timestamp}

---

{content}"""
        
        # Save both current and versioned file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        with open(version_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        return file_path

    def handle_command(self, command: str) -> bool:
        """
        Handle workflow-related commands.
        
        Returns True if command was handled, False otherwise.
        """
        parts = command[1:].split()
        cmd = parts[0].lower()
        
        if cmd == "approve":
            return self._handle_approve()
        elif cmd == "revise":
            return self._handle_revise(parts[1:])
        elif cmd == "cancel":
            return self._handle_cancel()
        elif cmd == "status":
            return self._handle_status()
        elif cmd == "workflow":
            return self._handle_workflow_info()
        
        return False

    def _handle_approve(self) -> bool:
        """Handle approval of current workflow stage."""
        if self.state == WorkflowState.PLAN_REVIEW:
            console.print("[green]✅ Plan approved! Moving to requirements generation...[/green]")
            return self._move_to_requirements()
        elif self.state == WorkflowState.REQUIREMENTS_REVIEW:
            console.print("[green]✅ Requirements approved! Moving to task breakdown...[/green]")
            return self._move_to_tasks()
        else:
            console.print(f"[yellow]Nothing to approve in current state: {self.state.value}[/yellow]")
            return True

    def _handle_revise(self, args: List[str]) -> bool:
        """Handle revision requests."""
        if self.state not in [WorkflowState.PLAN_REVIEW, WorkflowState.REQUIREMENTS_REVIEW]:
            console.print(f"[yellow]Cannot revise in current state: {self.state.value}[/yellow]")
            return True
        
        try:
            revision_request = " ".join(args) if args else Prompt.ask("What changes would you like?")
        except EOFError:
            console.print("[yellow]No revision feedback provided.[/yellow]")
            return True
        
        if self.state == WorkflowState.PLAN_REVIEW:
            console.print("\n[cyan]Revising plan based on your feedback...[/cyan]")
            # Re-generate plan with revision request
            revision_prompt = f"""The user wants to revise this plan with the following feedback: "{revision_request}"

Original request: "{self.current_request}"

Please revise the plan according to the feedback while maintaining the same structure:

# Project Plan

## Project Overview
## Goals and Objectives  
## Key Features
## Technical Approach
## Implementation Phases
## Considerations

Make sure to address the user's feedback while keeping the plan comprehensive."""

            revised_content = self.provider.ask(revision_prompt)
            plan_path = self._save_versioned_file("plan.md", revised_content, self.current_request)
            
            console.print(f"\n[green]✅ Plan revised and saved to {plan_path.relative_to(Path.cwd())}[/green]")
            console.print(Panel(Markdown(revised_content), title="Revised Plan", border_style="yellow"))
            
        elif self.state == WorkflowState.REQUIREMENTS_REVIEW:
            # Handle requirements revision
            console.print("\n[cyan]Revising requirements based on your feedback...[/cyan]")
            # Implementation for requirements revision
            pass
        
        return True

    def _handle_cancel(self) -> bool:
        """Handle workflow cancellation."""
        try:
            if Confirm.ask("Are you sure you want to cancel the current workflow?"):
                self.state = WorkflowState.IDLE
                self.current_request = None
                self._save_state()
                console.print("[yellow]Workflow cancelled. Returning to normal mode.[/yellow]")
        except EOFError:
            # Auto-cancel in non-interactive mode
            self.state = WorkflowState.IDLE
            self.current_request = None
            self._save_state()
            console.print("[yellow]Workflow cancelled. Returning to normal mode.[/yellow]")
        return True

    def _handle_status(self) -> bool:
        """Show current workflow status."""
        status_info = f"""[bold]Workflow Status:[/bold]

[blue]State:[/blue] {self.state.value}
[blue]Current Request:[/blue] {self.current_request or 'None'}

[blue]Available Files:[/blue]"""

        # List files in .codexa directory
        files = []
        if self.codexa_dir.exists():
            for file in self.codexa_dir.iterdir():
                if file.is_file() and file.suffix == '.md':
                    files.append(f"• {file.name}")
        
        if files:
            status_info += "\n" + "\n".join(files)
        else:
            status_info += "\nNone"

        # Add available commands based on state
        if self.state == WorkflowState.PLAN_REVIEW:
            status_info += "\n\n[yellow]Available commands:[/yellow]\n• /approve - Approve plan\n• /revise - Request changes\n• /cancel - Cancel workflow"
        elif self.state == WorkflowState.REQUIREMENTS_REVIEW:
            status_info += "\n\n[yellow]Available commands:[/yellow]\n• /approve - Approve requirements\n• /revise - Request changes\n• /cancel - Cancel workflow"

        console.print(Panel(status_info, title="Planning Status", border_style="blue"))
        return True

    def _handle_workflow_info(self) -> bool:
        """Show information about the Codexa workflow."""
        info = """[bold]Codexa Structured Workflow:[/bold]

[cyan]1. Planning Phase[/cyan]
   • Make a project request
   • Codexa generates a comprehensive plan
   • Review and approve/revise the plan

[cyan]2. Requirements Phase[/cyan]  
   • Codexa generates technical requirements
   • Details frontend, backend, database, etc.
   • Review and approve/revise requirements

[cyan]3. Task Breakdown Phase[/cyan]
   • Codexa creates detailed task list
   • Organized by development areas
   • Tasks can be followed sequentially

[cyan]4. Execution Phase[/cyan]
   • Follow tasks step-by-step
   • Or use natural language requests
   • Both approaches available

[yellow]Commands available during workflow:[/yellow]
• /approve - Approve current stage
• /revise [feedback] - Request changes  
• /cancel - Cancel workflow
• /status - Show current status"""

        console.print(Panel(info, title="Workflow Guide", border_style="green"))
        return True

    def _move_to_requirements(self) -> bool:
        """Move workflow to requirements generation."""
        self.state = WorkflowState.REQUIREMENTS
        self._save_state()
        
        console.print("\n[cyan]Generating technical requirements...[/cyan]")
        
        # Generate requirements
        requirements_content = self._generate_requirements()
        
        # Save requirements
        req_path = self._save_versioned_file("requirements.md", requirements_content, self.current_request)
        
        console.print(f"\n[green]✅ Requirements generated and saved to {req_path.relative_to(Path.cwd())}[/green]")
        
        # Show requirements
        console.print("\n" + "="*60)
        console.print(Panel(Markdown(requirements_content), title="Technical Requirements", border_style="blue"))
        console.print("="*60)
        
        # Move to review state
        self.state = WorkflowState.REQUIREMENTS_REVIEW
        self._save_state()
        
        console.print("\n[yellow]Review the requirements above. You can:[/yellow]")
        console.print("• [cyan]/approve[/cyan] - Approve and move to task breakdown")
        console.print("• [cyan]/revise[/cyan] - Request changes to requirements")
        console.print("• [cyan]/cancel[/cyan] - Cancel workflow")
        
        return True

    def _generate_requirements(self) -> str:
        """Generate technical requirements based on approved plan."""
        # Read the current plan
        plan_path = self.codexa_dir / "plan.md"
        plan_content = ""
        if plan_path.exists():
            with open(plan_path, 'r', encoding='utf-8') as f:
                plan_content = f.read()

        req_prompt = f"""Based on the approved project plan and request: "{self.current_request}"

Plan content:
{plan_content}

Generate comprehensive technical requirements with this structure:

# Technical Requirements

## Architecture Overview
High-level system architecture and design patterns

## Frontend Requirements
- Framework/library choices
- UI/UX considerations  
- Component architecture
- State management
- Styling approach

## Backend Requirements  
- Server technology stack
- API design (REST/GraphQL/etc.)
- Authentication/authorization
- Data validation
- Error handling

## Database Requirements
- Database type and setup
- Schema design
- Data relationships
- Performance considerations

## Infrastructure & DevOps
- Hosting/deployment platform
- CI/CD pipeline
- Environment management
- Monitoring and logging

## Security Requirements
- Authentication mechanisms
- Data protection
- API security
- Compliance considerations

## Performance Requirements
- Load expectations
- Response time targets
- Caching strategy
- Optimization needs

## Testing Strategy
- Unit testing approach
- Integration testing
- End-to-end testing
- Testing tools and frameworks

Be specific about technology choices and justify major decisions."""

        return self.provider.ask(req_prompt)

    def _move_to_tasks(self) -> bool:
        """Move workflow to task breakdown generation."""
        self.state = WorkflowState.TASKS
        self._save_state()
        
        console.print("\n[cyan]Generating detailed task breakdown...[/cyan]")
        
        # Generate tasks
        tasks_content = self._generate_tasks()
        
        # Save tasks
        tasks_path = self._save_versioned_file("tasks.md", tasks_content, self.current_request)
        
        console.print(f"\n[green]✅ Task breakdown generated and saved to {tasks_path.relative_to(Path.cwd())}[/green]")
        
        # Show tasks
        console.print("\n" + "="*60)
        console.print(Panel(Markdown(tasks_content), title="Task Breakdown", border_style="magenta"))
        console.print("="*60)
        
        # Move to execution state
        self.state = WorkflowState.EXECUTION
        self._save_state()
        
        console.print("\n[green]🎉 Planning workflow complete! You can now:[/green]")
        console.print("• Follow tasks step-by-step using [cyan]/next-task[/cyan]")
        console.print("• Use natural language to request specific work")
        console.print("• View all files in [cyan].codexa/[/cyan] directory")
        console.print("• Start a new planning workflow with another request")
        
        return True

    def _generate_tasks(self) -> str:
        """Generate detailed task breakdown."""
        # Read plan and requirements
        plan_path = self.codexa_dir / "plan.md"
        req_path = self.codexa_dir / "requirements.md"
        
        plan_content = ""
        req_content = ""
        
        if plan_path.exists():
            with open(plan_path, 'r', encoding='utf-8') as f:
                plan_content = f.read()
        
        if req_path.exists():
            with open(req_path, 'r', encoding='utf-8') as f:
                req_content = f.read()

        tasks_prompt = f"""Based on the approved plan and requirements for: "{self.current_request}"

Plan:
{plan_content}

Requirements:
{req_content}

Generate a detailed task breakdown organized like a real development team would structure their work:

# Task Breakdown

## Setup & Infrastructure
- [ ] Project setup and repository initialization
- [ ] Development environment configuration
- [ ] CI/CD pipeline setup
- [ ] Deployment environment preparation

## Backend Development
- [ ] Database schema design and setup
- [ ] API endpoint structure planning
- [ ] Authentication system implementation
- [ ] Core business logic development
- [ ] Data validation and error handling
- [ ] API documentation

## Frontend Development  
- [ ] Component architecture setup
- [ ] UI/UX mockups and design system
- [ ] Core component development
- [ ] State management implementation
- [ ] API integration
- [ ] Responsive design implementation

## Integration & Testing
- [ ] Unit test development
- [ ] Integration testing
- [ ] End-to-end testing
- [ ] Performance testing
- [ ] Security testing

## Documentation & Deployment
- [ ] Technical documentation
- [ ] User documentation  
- [ ] Deployment scripts
- [ ] Production deployment
- [ ] Monitoring setup

## Quality Assurance
- [ ] Code review process
- [ ] Performance optimization
- [ ] Security audit
- [ ] User acceptance testing

Each section should have specific, actionable tasks that a developer could pick up and complete. Include estimated effort (Small/Medium/Large) for complex tasks."""

        return self.provider.ask(tasks_prompt)

    def is_in_workflow(self) -> bool:
        """Check if currently in an active workflow."""
        return self.state != WorkflowState.IDLE

    def get_current_state(self) -> WorkflowState:
        """Get the current workflow state."""
        return self.state

    def reset_workflow(self) -> None:
        """Reset workflow to idle state."""
        self.state = WorkflowState.IDLE
        self.current_request = None
        self._save_state()