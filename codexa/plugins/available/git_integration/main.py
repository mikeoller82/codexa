"""
Git Integration Plugin for Codexa - enhanced Git operations and analysis.
"""

import asyncio
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from codexa.plugins.plugin_manager import Plugin, PluginInfo
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.text import Text


@dataclass
class GitStatus:
    """Git repository status information."""
    branch: str
    modified: List[str]
    staged: List[str]
    untracked: List[str]
    conflicts: List[str]
    ahead: int
    behind: int
    clean: bool


@dataclass
class CommitInfo:
    """Git commit information."""
    hash: str
    message: str
    author: str
    date: datetime
    files_changed: int
    insertions: int
    deletions: int


class GitIntegrationPlugin(Plugin):
    """Git integration plugin with smart operations."""
    
    def __init__(self, info: PluginInfo):
        super().__init__(info)
        self.console = Console()
        self.settings = {}
        self.repo_path = None
        
    async def initialize(self, context: Dict[str, Any]) -> bool:
        """Initialize the plugin."""
        try:
            self.logger.info("Initializing Git Integration Plugin...")
            
            # Load settings
            self.settings = self.info.to_dict().get('settings', {})
            
            # Find git repository
            self.repo_path = await self._find_git_repo()
            if not self.repo_path:
                self.logger.warning("Not in a Git repository")
                return True  # Still initialize, but with limited functionality
            
            self.logger.info(f"Git repository found: {self.repo_path}")
            
            # Check git availability
            if not await self._check_git_available():
                self.logger.error("Git command not available")
                return False
            
            self.logger.info("Git Integration Plugin initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Git Integration Plugin: {e}")
            return False
    
    async def shutdown(self) -> bool:
        """Shutdown the plugin."""
        self.logger.info("Git Integration Plugin shutdown")
        return True
    
    async def on_command(self, command: str, args: Dict[str, Any]) -> Optional[str]:
        """Handle plugin commands."""
        try:
            if not self.repo_path:
                return "[yellow]Not in a Git repository[/yellow]"
            
            if command == "git-status":
                return await self._handle_git_status(args)
            elif command == "commit-smart":
                return await self._handle_commit_smart(args)
            elif command == "branch-manage":
                return await self._handle_branch_manage(args)
            elif command == "git-analyze":
                return await self._handle_git_analyze(args)
            elif command == "conflict-assist":
                return await self._handle_conflict_assist(args)
            elif command == "repo-insights":
                return await self._handle_repo_insights(args)
            else:
                return f"Unknown command: {command}"
                
        except Exception as e:
            self.logger.error(f"Command {command} failed: {e}")
            return f"Command failed: {e}"
    
    async def _handle_git_status(self, args: Dict[str, Any]) -> str:
        """Handle enhanced git status."""
        try:
            status = await self._get_git_status()
            
            # Create enhanced status display
            panel_content = []
            
            # Branch info
            branch_text = f"[bold cyan]Branch:[/bold cyan] {status.branch}"
            if status.ahead > 0 or status.behind > 0:
                sync_info = []
                if status.ahead > 0:
                    sync_info.append(f"↑{status.ahead}")
                if status.behind > 0:
                    sync_info.append(f"↓{status.behind}")
                branch_text += f" [{', '.join(sync_info)}]"
            panel_content.append(branch_text)
            
            # Status indicator
            if status.clean:
                panel_content.append("[green]✅ Working directory clean[/green]")
            else:
                panel_content.append("[yellow]📝 Working directory has changes[/yellow]")
            
            # Changes summary
            changes = []
            if status.staged:
                changes.append(f"[green]{len(status.staged)} staged[/green]")
            if status.modified:
                changes.append(f"[yellow]{len(status.modified)} modified[/yellow]")
            if status.untracked:
                changes.append(f"[blue]{len(status.untracked)} untracked[/blue]")
            if status.conflicts:
                changes.append(f"[red]{len(status.conflicts)} conflicts[/red]")
            
            if changes:
                panel_content.append(f"Changes: {', '.join(changes)}")
            
            # File details
            if not status.clean:
                panel_content.append("")
                
                if status.staged:
                    panel_content.append("[bold green]Staged files:[/bold green]")
                    for file in status.staged:
                        panel_content.append(f"  [green]✓[/green] {file}")
                
                if status.modified:
                    panel_content.append("[bold yellow]Modified files:[/bold yellow]")
                    for file in status.modified:
                        panel_content.append(f"  [yellow]M[/yellow] {file}")
                
                if status.untracked:
                    panel_content.append("[bold blue]Untracked files:[/bold blue]")
                    for file in status.untracked[:5]:  # Limit display
                        panel_content.append(f"  [blue]?[/blue] {file}")
                    if len(status.untracked) > 5:
                        panel_content.append(f"  ... and {len(status.untracked) - 5} more")
                
                if status.conflicts:
                    panel_content.append("[bold red]Conflicts:[/bold red]")
                    for file in status.conflicts:
                        panel_content.append(f"  [red]⚠[/red] {file}")
            
            panel = Panel(
                "\n".join(panel_content),
                title="🔧 Git Status",
                border_style="cyan"
            )
            
            with self.console.capture() as capture:
                self.console.print(panel)
            
            return capture.get()
            
        except Exception as e:
            return f"[red]Failed to get git status: {e}[/red]"
    
    async def _handle_commit_smart(self, args: Dict[str, Any]) -> str:
        """Handle smart commit with auto-generated messages."""
        try:
            message = args.get('message')
            auto_stage = args.get('auto_stage', True)
            
            # Get current status
            status = await self._get_git_status()
            
            if status.clean:
                return "[yellow]No changes to commit[/yellow]"
            
            # Auto-stage modified files if requested
            if auto_stage and status.modified:
                for file in status.modified:
                    await self._run_git_command(['add', file])
                self.console.print(f"[green]Auto-staged {len(status.modified)} modified files[/green]")
            
            # Generate commit message if not provided
            if not message and self.settings.get('auto_generate_commit_messages', True):
                message = await self._generate_commit_message()
                
                # Show generated message and ask for confirmation
                self.console.print(f"\n[bold cyan]Generated commit message:[/bold cyan]")
                self.console.print(f"[dim]{message}[/dim]")
                
                # In a real implementation, you'd prompt for user confirmation
                # For now, we'll use the generated message
            
            if not message:
                return "[red]Commit message required[/red]"
            
            # Create the commit
            result = await self._run_git_command(['commit', '-m', message])
            
            if result.returncode == 0:
                return f"[green]✅ Commit created successfully[/green]\n[dim]{message}[/dim]"
            else:
                return f"[red]Commit failed: {result.stderr}[/red]"
                
        except Exception as e:
            return f"[red]Smart commit failed: {e}[/red]"
    
    async def _handle_branch_manage(self, args: Dict[str, Any]) -> str:
        """Handle branch management operations."""
        try:
            action = args.get('action', 'list')
            branch_name = args.get('branch')
            
            if action == 'list':
                return await self._list_branches()
            elif action == 'create':
                if not branch_name:
                    return "[red]Branch name required for create action[/red]"
                return await self._create_branch(branch_name)
            elif action == 'switch':
                if not branch_name:
                    return "[red]Branch name required for switch action[/red]"
                return await self._switch_branch(branch_name)
            elif action == 'delete':
                if not branch_name:
                    return "[red]Branch name required for delete action[/red]"
                return await self._delete_branch(branch_name)
            elif action == 'cleanup':
                return await self._cleanup_branches()
            else:
                return f"[red]Unknown branch action: {action}[/red]"
                
        except Exception as e:
            return f"[red]Branch management failed: {e}[/red]"
    
    async def _handle_git_analyze(self, args: Dict[str, Any]) -> str:
        """Handle git repository analysis."""
        try:
            analysis_type = args.get('type', 'summary')
            
            if analysis_type == 'summary':
                return await self._analyze_repo_summary()
            elif analysis_type == 'activity':
                return await self._analyze_commit_activity()
            elif analysis_type == 'files':
                return await self._analyze_file_changes()
            else:
                return f"[red]Unknown analysis type: {analysis_type}[/red]"
                
        except Exception as e:
            return f"[red]Git analysis failed: {e}[/red]"
    
    async def _handle_conflict_assist(self, args: Dict[str, Any]) -> str:
        """Handle merge conflict assistance."""
        try:
            status = await self._get_git_status()
            
            if not status.conflicts:
                return "[green]No merge conflicts detected[/green]"
            
            # Analyze conflicts
            conflict_analysis = []
            for file_path in status.conflicts:
                analysis = await self._analyze_conflict(file_path)
                conflict_analysis.append(analysis)
            
            # Display conflict summary
            table = Table(title="Merge Conflicts")
            table.add_column("File", style="cyan")
            table.add_column("Conflicts", style="red")
            table.add_column("Suggestions", style="green")
            
            for analysis in conflict_analysis:
                table.add_row(
                    analysis['file'],
                    str(analysis['conflict_count']),
                    analysis['suggestion']
                )
            
            with self.console.capture() as capture:
                self.console.print(table)
                self.console.print("\n[yellow]💡 Use your editor to resolve conflicts, then run:[/yellow]")
                self.console.print("[dim]git add <resolved-files>[/dim]")
                self.console.print("[dim]git commit[/dim]")
            
            return capture.get()
            
        except Exception as e:
            return f"[red]Conflict assistance failed: {e}[/red]"
    
    async def _handle_repo_insights(self, args: Dict[str, Any]) -> str:
        """Handle repository insights and statistics."""
        try:
            # Gather repository statistics
            insights = await self._gather_repo_insights()
            
            # Create insights display
            table = Table(title="Repository Insights")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            table.add_column("Details", style="dim")
            
            table.add_row("Total Commits", str(insights['total_commits']), "All time")
            table.add_row("Contributors", str(insights['contributors']), "Unique authors")
            table.add_row("Branches", str(insights['branches']), "Local branches")
            table.add_row("Repository Age", insights['repo_age'], "Since first commit")
            table.add_row("Latest Activity", insights['latest_activity'], "Last commit")
            
            # File type analysis
            if insights['file_types']:
                table.add_row("", "", "")
                table.add_row("File Types", "", "")
                for ext, count in list(insights['file_types'].items())[:5]:
                    table.add_row(f"  {ext or 'no extension'}", str(count), "files")
            
            with self.console.capture() as capture:
                self.console.print(table)
            
            return capture.get()
            
        except Exception as e:
            return f"[red]Repository insights failed: {e}[/red]"
    
    # Helper methods
    async def _find_git_repo(self) -> Optional[Path]:
        """Find the git repository root."""
        current = Path.cwd()
        while current != current.parent:
            if (current / '.git').exists():
                return current
            current = current.parent
        return None
    
    async def _check_git_available(self) -> bool:
        """Check if git is available."""
        try:
            result = await self._run_command(['git', '--version'])
            return result.returncode == 0
        except Exception:
            return False
    
    async def _get_git_status(self) -> GitStatus:
        """Get detailed git status."""
        # Get basic status
        result = await self._run_git_command(['status', '--porcelain=v1'])
        
        modified = []
        staged = []
        untracked = []
        conflicts = []
        
        for line in result.stdout.split('\n'):
            if not line.strip():
                continue
            
            status_code = line[:2]
            file_path = line[3:]
            
            if status_code.startswith('?'):
                untracked.append(file_path)
            elif status_code.startswith('U') or 'U' in status_code:
                conflicts.append(file_path)
            elif status_code[0] in 'MADRC':
                staged.append(file_path)
            elif status_code[1] in 'M':
                modified.append(file_path)
        
        # Get branch info
        branch_result = await self._run_git_command(['branch', '--show-current'])
        branch = branch_result.stdout.strip()
        
        # Get ahead/behind info
        ahead = behind = 0
        try:
            ahead_behind_result = await self._run_git_command([
                'rev-list', '--count', '--left-right', f'{branch}...origin/{branch}'
            ])
            if ahead_behind_result.returncode == 0:
                parts = ahead_behind_result.stdout.strip().split()
                if len(parts) == 2:
                    ahead, behind = int(parts[0]), int(parts[1])
        except Exception:
            pass
        
        return GitStatus(
            branch=branch,
            modified=modified,
            staged=staged,
            untracked=untracked,
            conflicts=conflicts,
            ahead=ahead,
            behind=behind,
            clean=not (modified or staged or untracked or conflicts)
        )
    
    async def _generate_commit_message(self) -> str:
        """Generate a smart commit message based on changes."""
        try:
            # Get diff for staged changes
            result = await self._run_git_command(['diff', '--cached', '--name-status'])
            
            if not result.stdout.strip():
                return "Update files"
            
            changes = {}
            for line in result.stdout.strip().split('\n'):
                if '\t' in line:
                    status, file_path = line.split('\t', 1)
                    changes[status] = changes.get(status, []) + [file_path]
            
            # Generate conventional commit message
            commit_type = "feat"
            if 'M' in changes:
                commit_type = "fix" if any(
                    'test' in f or 'bug' in f or 'error' in f 
                    for f in changes['M']
                ) else "feat"
            elif 'A' in changes:
                commit_type = "feat"
            elif 'D' in changes:
                commit_type = "remove"
            
            # Create scope based on files
            files = []
            for file_list in changes.values():
                files.extend(file_list)
            
            scope = self._determine_scope(files)
            
            # Generate description
            description = self._generate_description(changes)
            
            if scope:
                return f"{commit_type}({scope}): {description}"
            else:
                return f"{commit_type}: {description}"
                
        except Exception as e:
            self.logger.warning(f"Failed to generate commit message: {e}")
            return "Update files"
    
    def _determine_scope(self, files: List[str]) -> str:
        """Determine commit scope from file paths."""
        if not files:
            return ""
        
        # Common patterns
        if any('test' in f.lower() for f in files):
            return "tests"
        elif any('doc' in f.lower() or f.endswith('.md') for f in files):
            return "docs"
        elif any(f.endswith('.json') or f.endswith('.yaml') or f.endswith('.yml') for f in files):
            return "config"
        elif any('api' in f.lower() for f in files):
            return "api"
        elif any('ui' in f.lower() or 'frontend' in f.lower() for f in files):
            return "ui"
        
        # Use directory name if consistent
        dirs = set()
        for f in files:
            parts = f.split('/')
            if len(parts) > 1:
                dirs.add(parts[0])
        
        if len(dirs) == 1:
            return dirs.pop()
        
        return ""
    
    def _generate_description(self, changes: Dict[str, List[str]]) -> str:
        """Generate commit description from changes."""
        descriptions = []
        
        if 'A' in changes:
            count = len(changes['A'])
            descriptions.append(f"add {count} file{'s' if count > 1 else ''}")
        
        if 'M' in changes:
            count = len(changes['M'])
            descriptions.append(f"update {count} file{'s' if count > 1 else ''}")
        
        if 'D' in changes:
            count = len(changes['D'])
            descriptions.append(f"remove {count} file{'s' if count > 1 else ''}")
        
        return " and ".join(descriptions) or "modify files"
    
    async def _list_branches(self) -> str:
        """List git branches."""
        result = await self._run_git_command(['branch', '-v'])
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            
            table = Table(title="Git Branches")
            table.add_column("Branch", style="cyan")
            table.add_column("Latest Commit", style="dim")
            table.add_column("Status", style="green")
            
            for line in lines:
                if line.strip():
                    current = line.startswith('*')
                    parts = line.replace('*', '').strip().split(None, 2)
                    if len(parts) >= 2:
                        branch_name = parts[0]
                        commit_hash = parts[1]
                        commit_message = parts[2] if len(parts) > 2 else ""
                        
                        status = "→ current" if current else ""
                        table.add_row(branch_name, f"{commit_hash[:8]} {commit_message[:50]}", status)
            
            with self.console.capture() as capture:
                self.console.print(table)
            
            return capture.get()
        else:
            return f"[red]Failed to list branches: {result.stderr}[/red]"
    
    async def _run_command(self, cmd: List[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
        """Run a system command."""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd or self.repo_path
        )
        stdout, stderr = await process.communicate()
        
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=process.returncode,
            stdout=stdout.decode('utf-8'),
            stderr=stderr.decode('utf-8')
        )
    
    async def _run_git_command(self, args: List[str]) -> subprocess.CompletedProcess:
        """Run a git command."""
        return await self._run_command(['git'] + args)
    
    async def _create_branch(self, branch_name: str) -> str:
        """Create a new branch."""
        result = await self._run_git_command(['checkout', '-b', branch_name])
        if result.returncode == 0:
            return f"[green]✅ Created and switched to branch: {branch_name}[/green]"
        else:
            return f"[red]Failed to create branch: {result.stderr}[/red]"
    
    async def _switch_branch(self, branch_name: str) -> str:
        """Switch to an existing branch."""
        result = await self._run_git_command(['checkout', branch_name])
        if result.returncode == 0:
            return f"[green]✅ Switched to branch: {branch_name}[/green]"
        else:
            return f"[red]Failed to switch branch: {result.stderr}[/red]"
    
    async def _delete_branch(self, branch_name: str) -> str:
        """Delete a branch."""
        result = await self._run_git_command(['branch', '-d', branch_name])
        if result.returncode == 0:
            return f"[green]✅ Deleted branch: {branch_name}[/green]"
        else:
            return f"[red]Failed to delete branch: {result.stderr}[/red]"
    
    async def _cleanup_branches(self) -> str:
        """Clean up merged branches."""
        # This would implement branch cleanup logic
        return "[yellow]Branch cleanup not implemented yet[/yellow]"
    
    async def _analyze_repo_summary(self) -> str:
        """Analyze repository summary."""
        # This would implement repository analysis
        return "[yellow]Repository analysis not implemented yet[/yellow]"
    
    async def _analyze_commit_activity(self) -> str:
        """Analyze commit activity."""
        # This would implement commit activity analysis
        return "[yellow]Commit activity analysis not implemented yet[/yellow]"
    
    async def _analyze_file_changes(self) -> str:
        """Analyze file changes."""
        # This would implement file change analysis
        return "[yellow]File change analysis not implemented yet[/yellow]"
    
    async def _analyze_conflict(self, file_path: str) -> Dict[str, Any]:
        """Analyze a conflict file."""
        # This would implement conflict analysis
        return {
            'file': file_path,
            'conflict_count': 1,
            'suggestion': 'Review manually'
        }
    
    async def _gather_repo_insights(self) -> Dict[str, Any]:
        """Gather repository insights."""
        # This would implement repository insights gathering
        return {
            'total_commits': 0,
            'contributors': 0,
            'branches': 0,
            'repo_age': 'Unknown',
            'latest_activity': 'Unknown',
            'file_types': {}
        }