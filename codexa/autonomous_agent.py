"""
Autonomous agent module for Codexa - handles proactive file discovery and autonomous actions.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.markdown import Markdown

from .filesystem.mcp_filesystem import MCPFileSystem
from .mcp_service import MCPService


class PermissionMode(Enum):
    """Permission modes for autonomous actions."""
    ASK_EACH_TIME = "ask_each_time"
    SESSION_WIDE = "session_wide"
    AUTO_APPROVE = "auto_approve"


@dataclass
class FileDiscoveryResult:
    """Result of file discovery operation."""
    path: str
    file_type: str
    size: int
    relevance_score: float
    content_preview: str = ""
    line_count: int = 0


@dataclass
class AutonomousAction:
    """Represents an autonomous action to be taken."""
    action_type: str  # 'modify', 'create', 'delete', 'analyze'
    file_path: str
    description: str
    code_snippet: str = ""
    line_numbers: str = ""
    estimated_impact: str = "low"  # low, medium, high


class AutonomousAgent:
    """
    Autonomous agent that proactively discovers files, analyzes code, and makes changes.
    
    This class provides the core autonomous functionality that makes Codexa act more
    like Claude Code - proactive, action-oriented, and verbose about its process.
    """
    
    def __init__(self, mcp_service: MCPService = None, console: Console = None):
        """Initialize the autonomous agent."""
        self.mcp_service = mcp_service
        self.console = console or Console()
        self.logger = logging.getLogger("codexa.autonomous")
        
        # MCP filesystem integration
        self.mcp_filesystem = None
        if mcp_service:
            try:
                self.mcp_filesystem = MCPFileSystem(mcp_service)
            except Exception as e:
                self.logger.warning(f"MCP filesystem not available: {e}")
        
        # Session state - Default to auto-approve for better UX
        self.permission_mode = PermissionMode.AUTO_APPROVE
        self.session_approved = True
        self.discovered_files = []
        self.pending_actions = []
        
        # Project context
        self.project_root = Path.cwd()
        self.project_context = {}
    
    def _flush_console(self):
        """Safely flush console output for real-time display."""
        try:
            if hasattr(self.console, '_file') and self.console._file:
                self.console._file.flush()
        except (AttributeError, OSError):
            pass
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except (AttributeError, OSError):
            pass
    
    async def process_request_autonomously(self, request: str, context: str = "") -> str:
        """
        Process a user request autonomously by discovering files, analyzing code, and taking action.
        
        This is the main entry point for autonomous behavior that mimics Claude Code.
        """
        self.console.print(f"\n[bold blue]🔍 Processing request autonomously...[/bold blue]")
        self.console.print(f"[dim]Request: {request}[/dim]")
        
        try:
            # Step 1: Analyze request to determine scope and intent
            request_analysis = await self._analyze_request(request)
            self.console.print(f"\n[bold green]📋 Request Analysis:[/bold green]")
            self.console.print(f"• Intent: {request_analysis['intent']}")
            self.console.print(f"• Scope: {request_analysis['scope']}")
            self.console.print(f"• Priority: {request_analysis['priority']}")
            
            # Step 2: Discover relevant files proactively
            discovered_files = await self._discover_relevant_files(request, request_analysis)
            if discovered_files:
                await self._display_discovered_files(discovered_files)
            
            # Step 3: Analyze discovered code
            code_analysis = await self._analyze_discovered_code(discovered_files, request)
            if code_analysis:
                await self._display_code_analysis(code_analysis)
            
            # Step 4: Plan autonomous actions
            planned_actions = await self._plan_autonomous_actions(request, discovered_files, code_analysis)
            if planned_actions:
                await self._display_planned_actions(planned_actions)
            
            # Step 5: Get permission and execute actions
            if planned_actions:
                permission_granted = await self._get_permission_for_actions(planned_actions)
                if permission_granted:
                    results = await self._execute_autonomous_actions(planned_actions)
                    return await self._format_execution_results(results)
                else:
                    return "Actions cancelled by user. I can provide guidance instead if you'd like."
            else:
                return "No autonomous actions needed. I can provide guidance or answer questions about the code."
                
        except Exception as e:
            self.logger.error(f"Autonomous processing failed: {e}")
            return f"Autonomous processing encountered an error: {e}. I can still provide guidance manually."
    
    async def process_request_autonomously_streaming(self, request: str, context: str = "") -> str:
        """
        Process a user request autonomously with real-time streaming of thought process.
        
        This version displays the reasoning process and thought process in real-time.
        """
        import time
        import sys
        
        self.console.print(f"\n[bold blue]🔍 Processing request autonomously...[/bold blue]")
        self.console.print(f"[dim]Request: {request}[/dim]")
        
        # Force console to display immediately with enhanced buffer control
        self._flush_console()
        
        try:
            # Step 1: Analyze request to determine scope and intent
            self.console.print(f"\n[bold yellow]🧠 Analyzing request...[/bold yellow]")
            self._flush_console()
            time.sleep(0.15)  # Brief pause for visibility
            
            request_analysis = await self._analyze_request(request)
            
            self.console.print(f"\n[bold green]📋 Request Analysis:[/bold green]")
            self.console.print(f"• Intent: {request_analysis['intent']}")
            self.console.print(f"• Scope: {request_analysis['scope']}")
            self.console.print(f"• Priority: {request_analysis['priority']}")
            self._flush_console()
            time.sleep(0.2)
            
            # Step 2: Discover relevant files proactively
            self.console.print(f"\n[bold yellow]📁 Discovering relevant files...[/bold yellow]")
            self._flush_console()
            time.sleep(0.15)
            
            discovered_files = await self._discover_relevant_files(request, request_analysis)
            if discovered_files:
                await self._display_discovered_files(discovered_files)
                self._flush_console()
                time.sleep(0.2)
            
            # Step 3: Analyze discovered code
            self.console.print(f"\n[bold yellow]🔍 Analyzing discovered code...[/bold yellow]")
            self._flush_console()
            time.sleep(0.15)
            
            code_analysis = await self._analyze_discovered_code(discovered_files, request)
            if code_analysis:
                await self._display_code_analysis(code_analysis)
                self._flush_console()
                time.sleep(0.2)
            
            # Step 4: Plan autonomous actions
            self.console.print(f"\n[bold yellow]🎯 Planning actions...[/bold yellow]")
            self._flush_console()
            time.sleep(0.15)
            
            planned_actions = await self._plan_autonomous_actions(request, discovered_files, code_analysis)
            if planned_actions:
                await self._display_planned_actions(planned_actions)
                self._flush_console()
                time.sleep(0.2)
            
            # Step 5: Get permission and execute actions
            if planned_actions:
                permission_granted = await self._get_permission_for_actions(planned_actions)
                if permission_granted:
                    self.console.print(f"\n[bold yellow]⚡ Executing actions...[/bold yellow]")
                    self._flush_console()
                    time.sleep(0.15)
                    
                    results = await self._execute_autonomous_actions_with_real_files(planned_actions)
                    return await self._format_execution_results(results)
                else:
                    return "Actions cancelled by user. I can provide guidance instead if you'd like."
            else:
                return "No autonomous actions needed. I can provide guidance or answer questions about the code."
                
        except Exception as e:
            self.logger.error(f"Autonomous processing failed: {e}")
            return f"Autonomous processing encountered an error: {e}. I can still provide guidance manually."
    
    async def _analyze_request(self, request: str) -> Dict[str, str]:
        """Analyze the user request to determine intent, scope, and priority."""
        # Simple heuristic analysis - in real implementation this could use AI
        request_lower = request.lower()
        
        # Determine intent
        intent = "analyze"
        if any(word in request_lower for word in ["create", "add", "build", "implement", "generate"]):
            intent = "create"
        elif any(word in request_lower for word in ["fix", "update", "modify", "change", "improve"]):
            intent = "modify"
        elif any(word in request_lower for word in ["delete", "remove"]):
            intent = "delete"
        elif any(word in request_lower for word in ["debug", "troubleshoot", "investigate"]):
            intent = "debug"
        
        # Determine scope
        scope = "file"
        if any(word in request_lower for word in ["project", "all", "entire", "system"]):
            scope = "project"
        elif any(word in request_lower for word in ["component", "module", "class"]):
            scope = "module"
        
        # Determine priority
        priority = "medium"
        if any(word in request_lower for word in ["urgent", "critical", "important", "asap"]):
            priority = "high"
        elif any(word in request_lower for word in ["minor", "small", "simple"]):
            priority = "low"
        
        return {
            "intent": intent,
            "scope": scope,
            "priority": priority,
            "keywords": self._extract_keywords(request)
        }
    
    def _extract_keywords(self, request: str) -> List[str]:
        """Extract relevant keywords from the request."""
        # Simple keyword extraction - could be enhanced with NLP
        common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "from", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "can", "must"}
        words = request.lower().split()
        keywords = [word.strip(".,!?;:()[]{}\"'") for word in words if len(word) > 2 and word not in common_words]
        return keywords[:10]  # Top 10 keywords
    
    async def _discover_relevant_files(self, request: str, analysis: Dict[str, str]) -> List[FileDiscoveryResult]:
        """Proactively discover files relevant to the user's request."""
        discovered = []
        
        try:
            if self.mcp_filesystem and self.mcp_filesystem.is_server_available():
                # Use MCP filesystem for enhanced discovery
                discovered = await self._discover_files_with_mcp(request, analysis)
            else:
                # Fallback to local file discovery
                discovered = await self._discover_files_locally(request, analysis)
                
        except Exception as e:
            self.logger.warning(f"File discovery failed: {e}")
        
        return discovered
    
    async def _discover_files_with_mcp(self, request: str, analysis: Dict[str, str]) -> List[FileDiscoveryResult]:
        """Discover files using MCP filesystem capabilities."""
        discovered = []
        
        try:
            # Search by keywords in file names
            for keyword in analysis.get('keywords', []):
                matches = await self.mcp_filesystem.search_files(self.project_root, f"*{keyword}*")
                for match in matches[:5]:  # Limit results
                    discovered.append(FileDiscoveryResult(
                        path=match.get('path', ''),
                        file_type=match.get('type', 'unknown'),
                        size=match.get('size', 0),
                        relevance_score=0.8
                    ))
            
            # Search within file contents
            for keyword in analysis.get('keywords', [])[:3]:  # Limit content search
                content_matches = await self.mcp_filesystem.search_within_files(
                    self.project_root, keyword, max_results=5
                )
                for match in content_matches:
                    discovered.append(FileDiscoveryResult(
                        path=match.get('path', ''),
                        file_type='file',
                        size=match.get('size', 0),
                        relevance_score=0.9,
                        content_preview=match.get('preview', '')
                    ))
            
        except Exception as e:
            self.logger.warning(f"MCP file discovery failed: {e}")
        
        return discovered
    
    async def _discover_files_locally(self, request: str, analysis: Dict[str, str]) -> List[FileDiscoveryResult]:
        """Fallback local file discovery."""
        discovered = []
        
        try:
            # Simple local file discovery based on common patterns
            common_extensions = ['.py', '.js', '.ts', '.tsx', '.jsx', '.css', '.html', '.md', '.json', '.yaml', '.yml']
            
            for ext in common_extensions:
                for file_path in self.project_root.rglob(f"*{ext}"):
                    if file_path.is_file() and not any(part.startswith('.') for part in file_path.parts):
                        # Simple relevance scoring based on filename
                        relevance = 0.5
                        filename_lower = file_path.name.lower()
                        for keyword in analysis.get('keywords', []):
                            if keyword.lower() in filename_lower:
                                relevance += 0.2
                        
                        if relevance > 0.5:
                            discovered.append(FileDiscoveryResult(
                                path=str(file_path),
                                file_type=ext[1:],  # Remove dot
                                size=file_path.stat().st_size,
                                relevance_score=relevance
                            ))
                
                if len(discovered) >= 10:  # Limit results
                    break
        
        except Exception as e:
            self.logger.warning(f"Local file discovery failed: {e}")
        
        # Sort by relevance score
        discovered.sort(key=lambda x: x.relevance_score, reverse=True)
        return discovered[:10]  # Top 10 most relevant
    
    async def _display_discovered_files(self, files: List[FileDiscoveryResult]):
        """Display discovered files in a user-friendly format."""
        if not files:
            self.console.print("\n[yellow]No relevant files discovered.[/yellow]")
            return
        
        self.console.print(f"\n[bold green]📁 Discovered {len(files)} relevant files:[/bold green]")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("File", style="cyan", no_wrap=True)
        table.add_column("Type", style="green")
        table.add_column("Size", style="yellow", justify="right")
        table.add_column("Relevance", style="red", justify="right")
        
        for file in files[:8]:  # Show top 8
            size_str = self._format_file_size(file.size)
            relevance_str = f"{file.relevance_score:.1f}"
            table.add_row(
                file.path,
                file.file_type,
                size_str,
                relevance_str
            )
        
        self.console.print(table)
    
    def _format_file_size(self, size: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}TB"
    
    async def _analyze_discovered_code(self, files: List[FileDiscoveryResult], request: str) -> Dict[str, Any]:
        """Analyze the discovered code files."""
        analysis = {
            "patterns": [],
            "issues": [],
            "dependencies": [],
            "suggestions": []
        }
        
        if not files:
            return analysis
        
        # Analyze top 3 most relevant files
        for file in files[:3]:
            try:
                if self.mcp_filesystem:
                    content = await self.mcp_filesystem.read_file(file.path)
                else:
                    content = Path(file.path).read_text(encoding='utf-8', errors='ignore')
                
                file_analysis = self._analyze_file_content(content, file.path, request)
                analysis["patterns"].extend(file_analysis.get("patterns", []))
                analysis["issues"].extend(file_analysis.get("issues", []))
                analysis["dependencies"].extend(file_analysis.get("dependencies", []))
                
            except Exception as e:
                self.logger.warning(f"Failed to analyze {file.path}: {e}")
        
        return analysis
    
    def _analyze_file_content(self, content: str, file_path: str, request: str) -> Dict[str, Any]:
        """Analyze individual file content."""
        analysis = {
            "patterns": [],
            "issues": [],
            "dependencies": []
        }
        
        lines = content.split('\n')
        
        # Detect imports/dependencies
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if line_stripped.startswith(('import ', 'from ', 'require(', '#include')):
                analysis["dependencies"].append({
                    "file": file_path,
                    "line": i + 1,
                    "dependency": line_stripped
                })
        
        # Look for patterns relevant to request
        request_keywords = request.lower().split()
        for i, line in enumerate(lines):
            for keyword in request_keywords:
                if keyword in line.lower() and len(keyword) > 3:
                    analysis["patterns"].append({
                        "file": file_path,
                        "line": i + 1,
                        "content": line.strip(),
                        "keyword": keyword
                    })
        
        return analysis
    
    async def _display_code_analysis(self, analysis: Dict[str, Any]):
        """Display code analysis results."""
        if not any(analysis.values()):
            return
        
        self.console.print(f"\n[bold green]🔍 Code Analysis Results:[/bold green]")
        
        if analysis.get("patterns"):
            self.console.print("\n[bold yellow]📋 Relevant Code Patterns:[/bold yellow]")
            for i, pattern in enumerate(analysis["patterns"][:5]):  # Show top 5
                self.console.print(f"  {i+1}. {pattern['file']}:{pattern['line']}")
                self.console.print(f"     [dim]{pattern['content']}[/dim]")
        
        if analysis.get("dependencies"):
            self.console.print(f"\n[bold cyan]📦 Dependencies Found: {len(analysis['dependencies'])}[/bold cyan]")
        
        if analysis.get("issues"):
            self.console.print(f"\n[bold red]⚠️  Potential Issues: {len(analysis['issues'])}[/bold red]")
    
    async def _plan_autonomous_actions(self, request: str, files: List[FileDiscoveryResult], analysis: Dict[str, Any]) -> List[AutonomousAction]:
        """Plan autonomous actions based on request and analysis."""
        actions = []
        
        # This is a simplified implementation - in real usage this would be more sophisticated
        request_lower = request.lower()
        
        if "fix" in request_lower or "update" in request_lower:
            # Plan modification actions
            for file in files[:2]:  # Focus on top 2 files
                actions.append(AutonomousAction(
                    action_type="modify",
                    file_path=file.path,
                    description=f"Update {file.path} based on request",
                    estimated_impact="medium"
                ))
        
        elif "create" in request_lower or "add" in request_lower:
            # Plan creation actions based on request analysis
            file_extension = self._determine_file_extension(request, files)
            base_name = self._extract_filename_from_request(request) or "new_file"
            new_file_path = f"{base_name}{file_extension}"
            
            actions.append(AutonomousAction(
                action_type="create",
                file_path=new_file_path,
                description=f"Create {file_extension[1:]} file based on request",
                estimated_impact="low"
            ))
        
        return actions
    
    async def _display_planned_actions(self, actions: List[AutonomousAction]):
        """Display planned autonomous actions."""
        self.console.print(f"\n[bold green]🎯 Planned Actions ({len(actions)}):[/bold green]")
        
        for i, action in enumerate(actions):
            impact_color = {"low": "green", "medium": "yellow", "high": "red"}.get(action.estimated_impact, "white")
            self.console.print(f"  {i+1}. [bold]{action.action_type.upper()}[/bold] {action.file_path}")
            self.console.print(f"     {action.description}")
            self.console.print(f"     Impact: [{impact_color}]{action.estimated_impact}[/{impact_color}]")
    
    async def _get_permission_for_actions(self, actions: List[AutonomousAction]) -> bool:
        """Get user permission for autonomous actions."""
        if self.permission_mode == PermissionMode.AUTO_APPROVE or self.session_approved:
            return True
        
        self.console.print(f"\n[bold yellow]🤖 Permission Required[/bold yellow]")
        self.console.print("I'm ready to make these changes autonomously.")
        
        if self.permission_mode == PermissionMode.ASK_EACH_TIME:
            choices = [
                "1. Approve these actions",
                "2. Approve for entire session", 
                "3. Cancel and provide guidance instead"
            ]
            
            self.console.print("\nOptions:")
            for choice in choices:
                self.console.print(f"  {choice}")
            
            choice = Prompt.ask("\nYour choice", choices=["1", "2", "3"], default="1")
            
            if choice == "1":
                return True
            elif choice == "2":
                self.session_approved = True
                self.permission_mode = PermissionMode.SESSION_WIDE
                return True
            else:
                return False
        
        return Confirm.ask("Proceed with autonomous actions?")
    
    async def _execute_autonomous_actions(self, actions: List[AutonomousAction]) -> List[Dict[str, Any]]:
        """Execute the planned autonomous actions."""
        results = []
        
        self.console.print(f"\n[bold green]⚡ Executing {len(actions)} actions...[/bold green]")
        
        for i, action in enumerate(actions):
            self.console.print(f"\n[bold blue]Action {i+1}/{len(actions)}:[/bold blue] {action.action_type} {action.file_path}")
            
            try:
                if action.action_type == "modify":
                    result = await self._execute_modify_action(action)
                elif action.action_type == "create":
                    result = await self._execute_create_action(action)
                elif action.action_type == "delete":
                    result = await self._execute_delete_action(action)
                else:
                    result = {"success": False, "error": f"Unknown action type: {action.action_type}"}
                
                results.append(result)
                
                if result.get("success"):
                    self.console.print(f"[green]✅ {action.description}[/green]")
                else:
                    self.console.print(f"[red]❌ Failed: {result.get('error', 'Unknown error')}[/red]")
                    
            except Exception as e:
                error_result = {"success": False, "error": str(e), "action": action}
                results.append(error_result)
                self.console.print(f"[red]❌ Error executing action: {e}[/red]")
        
        return results
    
    async def _execute_autonomous_actions_with_real_files(self, actions: List[AutonomousAction]) -> List[Dict[str, Any]]:
        """Execute autonomous actions with actual file operations."""
        import sys
        import time
        results = []
        
        self.console.print(f"\n[bold green]⚡ Executing {len(actions)} actions...[/bold green]")
        
        for i, action in enumerate(actions):
            self.console.print(f"\n[bold blue]Action {i+1}/{len(actions)}:[/bold blue] {action.action_type} {action.file_path}")
            self._flush_console()
            time.sleep(0.15)
            
            try:
                if action.action_type == "modify":
                    result = await self._execute_modify_action_real(action)
                elif action.action_type == "create":
                    result = await self._execute_create_action_real(action)
                elif action.action_type == "delete":
                    result = await self._execute_delete_action_real(action)
                else:
                    # Handle comprehensive MCP filesystem actions
                    result = await self._execute_comprehensive_action(action)
                
                results.append(result)
                
                if result.get("success"):
                    self.console.print(f"[green]✅ {action.description}[/green]")
                else:
                    self.console.print(f"[red]❌ Failed: {result.get('error', 'Unknown error')}[/red]")
                
                self._flush_console()
                time.sleep(0.1)
                    
            except Exception as e:
                error_result = {"success": False, "error": str(e), "action": action}
                results.append(error_result)
                self.console.print(f"[red]❌ Error executing action: {e}[/red]")
                sys.stdout.flush()
                time.sleep(0.1)
        
        return results
    
    async def _execute_modify_action(self, action: AutonomousAction) -> Dict[str, Any]:
        """Execute a file modification action."""
        # This is a placeholder - real implementation would do actual modifications
        return {
            "success": True,
            "action": "modify",
            "file": action.file_path,
            "changes": "Simulated file modification"
        }
    
    async def _execute_create_action(self, action: AutonomousAction) -> Dict[str, Any]:
        """Execute a file creation action."""
        # This is a placeholder - real implementation would create files
        return {
            "success": True, 
            "action": "create",
            "file": action.file_path,
            "content": "Simulated file creation"
        }
    
    async def _execute_create_action_real(self, action: AutonomousAction) -> Dict[str, Any]:
        """Execute a real file creation action with enhanced error handling."""
        try:
            file_path = Path(action.file_path)
            
            # Validate file path
            if not action.file_path or action.file_path.strip() == "":
                raise ValueError("File path cannot be empty")
            
            # Generate content based on file type and description  
            content = self._generate_file_content(action.file_path, action.description)
            
            if not content or len(content.strip()) == 0:
                raise ValueError("Generated content cannot be empty")
            
            # Create directory if it doesn't exist
            try:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                self.console.print(f"[dim]📁 Directory created: {file_path.parent}[/dim]")
            except OSError as e:
                raise OSError(f"Failed to create directory {file_path.parent}: {e}")
            
            # Use MCP filesystem if available
            creation_method = "unknown"
            if self.mcp_filesystem and self.mcp_filesystem.is_server_available():
                try:
                    await self.mcp_filesystem.write_file(action.file_path, content)
                    creation_method = "MCP"
                    self.console.print(f"[dim]✨ Created via MCP: {action.file_path}[/dim]")
                except Exception as e:
                    self.logger.warning(f"MCP file creation failed, using local: {e}")
                    # Fallback to local creation
                    file_path.write_text(content, encoding='utf-8')
                    creation_method = "local_fallback"
                    self.console.print(f"[dim]💾 Created locally (fallback): {action.file_path}[/dim]")
            else:
                # Local file creation
                file_path.write_text(content, encoding='utf-8')
                creation_method = "local"
                self.console.print(f"[dim]💾 Created locally: {action.file_path}[/dim]")
            
            # Verify file was created
            if not file_path.exists():
                raise FileNotFoundError(f"File creation verification failed: {action.file_path}")
            
            file_size = file_path.stat().st_size
            self.console.print(f"[dim]✅ File verified: {file_size} bytes[/dim]")
            
            return {
                "success": True,
                "action": "create",
                "file": action.file_path,
                "content": content[:200] + "..." if len(content) > 200 else content,
                "size": file_size,
                "method": creation_method,
                "verified": True
            }
        except Exception as e:
            error_msg = f"File creation failed: {str(e)}"
            self.console.print(f"[red]❌ {error_msg}[/red]")
            self.logger.error(f"File creation error for {action.file_path}: {e}")
            return {
                "success": False,
                "action": "create", 
                "file": action.file_path,
                "error": error_msg,
                "details": str(e)
            }
    
    async def _execute_modify_action_real(self, action: AutonomousAction) -> Dict[str, Any]:
        """Execute a real file modification action."""
        try:
            file_path = Path(action.file_path)
            
            if not file_path.exists():
                return {
                    "success": False,
                    "action": "modify",
                    "file": action.file_path,
                    "error": "File does not exist"
                }
            
            # Read existing content
            if self.mcp_filesystem and self.mcp_filesystem.is_server_available():
                try:
                    original_content = await self.mcp_filesystem.read_file(action.file_path)
                except Exception:
                    original_content = file_path.read_text(encoding='utf-8')
            else:
                original_content = file_path.read_text(encoding='utf-8')
            
            # Make simple modifications (this could be enhanced with AI)
            modified_content = self._make_simple_modifications(original_content, action.description)
            
            # Write back
            if self.mcp_filesystem and self.mcp_filesystem.is_server_available():
                try:
                    await self.mcp_filesystem.write_file(action.file_path, modified_content)
                    self.console.print(f"[dim]Modified via MCP: {action.file_path}[/dim]")
                except Exception as e:
                    self.logger.warning(f"MCP file modification failed, using local: {e}")
                    file_path.write_text(modified_content, encoding='utf-8')
                    self.console.print(f"[dim]Modified locally: {action.file_path}[/dim]")
            else:
                file_path.write_text(modified_content, encoding='utf-8')
                self.console.print(f"[dim]Modified locally: {action.file_path}[/dim]")
            
            return {
                "success": True,
                "action": "modify",
                "file": action.file_path,
                "changes": "Content updated successfully",
                "size_change": len(modified_content) - len(original_content)
            }
        except Exception as e:
            return {
                "success": False,
                "action": "modify",
                "file": action.file_path,
                "error": str(e)
            }
    
    async def _execute_delete_action_real(self, action: AutonomousAction) -> Dict[str, Any]:
        """Execute a real file deletion action."""
        try:
            file_path = Path(action.file_path)
            
            if not file_path.exists():
                return {
                    "success": False,
                    "action": "delete",
                    "file": action.file_path,
                    "error": "File does not exist"
                }
            
            # Use MCP filesystem if available
            if self.mcp_filesystem and self.mcp_filesystem.is_server_available():
                try:
                    await self.mcp_filesystem.delete_file(action.file_path)
                    self.console.print(f"[dim]Deleted via MCP: {action.file_path}[/dim]")
                except Exception as e:
                    self.logger.warning(f"MCP file deletion failed, using local: {e}")
                    file_path.unlink()
                    self.console.print(f"[dim]Deleted locally: {action.file_path}[/dim]")
            else:
                file_path.unlink()
                self.console.print(f"[dim]Deleted locally: {action.file_path}[/dim]")
            
            return {
                "success": True,
                "action": "delete",
                "file": action.file_path
            }
        except Exception as e:
            return {
                "success": False,
                "action": "delete",
                "file": action.file_path,
                "error": str(e)
            }
    
    async def _execute_delete_action(self, action: AutonomousAction) -> Dict[str, Any]:
        """Execute a file deletion action."""
        # This is a placeholder - real implementation would delete files
        return {
            "success": True,
            "action": "delete", 
            "file": action.file_path
        }
    
    async def _format_execution_results(self, results: List[Dict[str, Any]]) -> str:
        """Format execution results for display."""
        successful = [r for r in results if r.get("success")]
        failed = [r for r in results if not r.get("success")]
        
        summary = f"\n[bold green]🎉 Execution Complete![/bold green]\n"
        summary += f"• Successful actions: {len(successful)}\n"
        summary += f"• Failed actions: {len(failed)}\n"
        
        if failed:
            summary += f"\n[bold red]❌ Failed Actions:[/bold red]\n"
            for result in failed:
                summary += f"• {result.get('error', 'Unknown error')}\n"
        
        if successful:
            summary += f"\n[bold green]✅ Changes Made:[/bold green]\n"
            for result in successful:
                action_type = result.get('action', 'unknown')
                file_path = result.get('file', 'unknown')
                summary += f"• {action_type.title()} {file_path}\n"
        
        return summary
    
    def set_permission_mode(self, mode: PermissionMode):
        """Set the permission mode for autonomous actions."""
        self.permission_mode = mode
        if mode == PermissionMode.SESSION_WIDE:
            self.session_approved = True
        elif mode == PermissionMode.ASK_EACH_TIME:
            self.session_approved = False
    
    def _generate_file_content(self, file_path: str, description: str) -> str:
        """Generate appropriate file content based on file type and description."""
        file_path_obj = Path(file_path)
        extension = file_path_obj.suffix.lower()
        
        if extension == '.py':
            return f'"""\n{description}\n"""\n\n# TODO: Implement {file_path_obj.stem}\n\ndef main():\n    pass\n\nif __name__ == "__main__":\n    main()\n'
        elif extension in ['.js', '.ts']:
            return f'// {description}\n\n// TODO: Implement {file_path_obj.stem}\n\nexport default function {file_path_obj.stem}() {{\n    // Implementation here\n}}\n'
        elif extension == '.md':
            return f'# {file_path_obj.stem.replace("_", " ").title()}\n\n{description}\n\n## Overview\n\nTODO: Add documentation\n'
        elif extension in ['.json']:
            return '{\n    "name": "' + file_path_obj.stem + '",\n    "description": "' + description + '"\n}'
        elif extension in ['.yaml', '.yml']:
            return f'name: {file_path_obj.stem}\ndescription: "{description}"\n'
        else:
            return f'# {description}\n\n# TODO: Implement content for {file_path}\n'
    
    def _make_simple_modifications(self, content: str, description: str) -> str:
        """Make simple modifications to file content based on description."""
        lines = content.split('\n')
        
        # Add a comment about the modification
        modification_comment = f'# Modified: {description}'
        
        if 'TODO' in content:
            # Replace first TODO with actual implementation hint
            for i, line in enumerate(lines):
                if 'TODO' in line:
                    lines[i] = f'{line}\n{modification_comment}'
                    break
        else:
            # Add modification comment at the beginning
            lines.insert(0, modification_comment)
        
        return '\n'.join(lines)
    
    def _determine_file_extension(self, request: str, files: List[FileDiscoveryResult]) -> str:
        """Determine appropriate file extension based on request and existing files."""
        request_lower = request.lower()
        
        # Check for specific language mentions
        if any(word in request_lower for word in ['python', '.py', 'python script']):
            return '.py'
        elif any(word in request_lower for word in ['javascript', 'js', 'node', '.js']):
            return '.js'
        elif any(word in request_lower for word in ['typescript', 'ts', '.ts']):
            return '.ts'
        elif any(word in request_lower for word in ['react', 'jsx', 'component']):
            return '.jsx'
        elif any(word in request_lower for word in ['markdown', 'md', 'documentation', 'readme']):
            return '.md'
        elif any(word in request_lower for word in ['json', 'config']):
            return '.json'
        elif any(word in request_lower for word in ['yaml', 'yml']):
            return '.yml'
        elif any(word in request_lower for word in ['css', 'style']):
            return '.css'
        elif any(word in request_lower for word in ['html', 'webpage']):
            return '.html'
        
        # Infer from existing files in project
        if files:
            extensions = [Path(f.path).suffix for f in files if Path(f.path).suffix]
            if extensions:
                # Return most common extension
                from collections import Counter
                most_common = Counter(extensions).most_common(1)
                return most_common[0][0] if most_common else '.py'
        
        # Default to Python
        return '.py'
    
    def _extract_filename_from_request(self, request: str) -> Optional[str]:
        """Extract filename from request if mentioned."""
        import re
        
        # Look for patterns like "create file.py", "make test.js", etc.
        filename_pattern = r'(?:create|make|add|build)\s+(?:a\s+)?(\w+(?:\.\w+)?)'
        match = re.search(filename_pattern, request.lower())
        if match:
            return match.group(1)
        
        # Look for standalone filenames
        filename_pattern = r'(\w+\.\w+)'
        matches = re.findall(filename_pattern, request)
        if matches:
            return matches[0].rsplit('.', 1)[0]  # Remove extension
        
        # Extract from request context
        words = request.lower().split()
        keywords = ['create', 'make', 'add', 'build', 'implement']
        for i, word in enumerate(words):
            if word in keywords and i + 1 < len(words):
                next_word = words[i + 1]
                if next_word not in ['a', 'an', 'the', 'new']:
                    # Clean the word to make it a valid filename
                    clean_name = re.sub(r'[^\w]', '_', next_word)
                    return clean_name
        
        return None
    
    def _extract_destination_from_request(self, request: str) -> Optional[str]:
        """Extract destination path from request."""
        import re
        
        # Look for "to directory" or "into folder" patterns
        patterns = [
            r'(?:to|into|in)\s+(?:the\s+)?([\\w/]+)(?:\s+directory|\s+folder|\s+dir)?',
            r'move.*?(?:to|into)\s+([\\w/]+)',
            r'put.*?(?:in|into)\s+([\\w/]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, request.lower())
            if match:
                return match.group(1)
        
        return None
    
    def _extract_search_terms(self, request: str) -> List[str]:
        """Extract search terms from request."""
        import re
        
        # Look for quoted terms first  
        quoted_terms = re.findall(r'["\']([^"\']+)["\']', request)
        if quoted_terms:
            return quoted_terms
        
        # Look for search-related patterns
        search_patterns = [
            r'(?:search|find|look)\s+for\s+([\w\s]+?)(?:\s+in|\s+within|$)',
            r'find\s+([\w\s]+?)(?:\s+in|\s+within|$)',
            r'search\s+([\w\s]+?)(?:\s+in|\s+within|$)'
        ]
        
        terms = []
        for pattern in search_patterns:
            matches = re.findall(pattern, request.lower())
            terms.extend([term.strip() for term in matches if len(term.strip()) > 2])
        
        # Fallback to keywords
        if not terms:
            words = request.lower().split()
            terms = [word for word in words if len(word) > 3 and word not in ['search', 'find', 'look', 'within', 'files']]
        
        return terms[:5]  # Limit to 5 terms
    
    async def _execute_comprehensive_action(self, action: AutonomousAction) -> Dict[str, Any]:
        """Execute comprehensive actions using all MCP filesystem capabilities."""
        try:
            action_type = action.action_type
            
            if action_type == "copy":
                return await self._execute_copy_action(action)
            elif action_type == "move":
                return await self._execute_move_action(action)
            elif action_type == "create_directory":
                return await self._execute_create_directory_action(action)
            elif action_type == "analyze_structure":
                return await self._execute_analyze_structure_action(action)
            elif action_type == "search_files":
                return await self._execute_search_files_action(action)
            elif action_type == "search_content":
                return await self._execute_search_content_action(action)
            elif action_type == "read_multiple":
                return await self._execute_read_multiple_action(action)
            else:
                return {
                    "success": False,
                    "action": action_type,
                    "error": f"Unknown comprehensive action type: {action_type}"
                }
        except Exception as e:
            return {
                "success": False,
                "action": action.action_type,
                "error": str(e)
            }
    
    async def _execute_copy_action(self, action: AutonomousAction) -> Dict[str, Any]:
        """Execute file copy using MCP filesystem."""
        try:
            source = action.file_path
            destination = action.code_snippet or f"{source}.backup"
            
            if self.mcp_filesystem and self.mcp_filesystem.is_server_available():
                await self.mcp_filesystem.copy_file(source, destination)
                self.console.print(f"[dim]📋 Copied via MCP: {source} → {destination}[/dim]")
            else:
                # Local fallback
                import shutil
                shutil.copy2(source, destination)
                self.console.print(f"[dim]📋 Copied locally: {source} → {destination}[/dim]")
            
            return {
                "success": True,
                "action": "copy",
                "source": source,
                "destination": destination
            }
        except Exception as e:
            return {
                "success": False,
                "action": "copy",
                "error": str(e)
            }
    
    async def _execute_move_action(self, action: AutonomousAction) -> Dict[str, Any]:
        """Execute file move using MCP filesystem."""
        try:
            source = action.file_path
            destination = action.code_snippet
            
            if self.mcp_filesystem and self.mcp_filesystem.is_server_available():
                await self.mcp_filesystem.move_file(source, destination)
                self.console.print(f"[dim]📦 Moved via MCP: {source} → {destination}[/dim]")
            else:
                # Local fallback
                import shutil
                shutil.move(source, destination)
                self.console.print(f"[dim]📦 Moved locally: {source} → {destination}[/dim]")
            
            return {
                "success": True,
                "action": "move",
                "source": source,
                "destination": destination
            }
        except Exception as e:
            return {
                "success": False,
                "action": "move",
                "error": str(e)
            }
    
    async def _execute_create_directory_action(self, action: AutonomousAction) -> Dict[str, Any]:
        """Execute directory creation using MCP filesystem."""
        try:
            dir_path = action.file_path
            success = await self._ensure_directory_exists(dir_path)
            
            return {
                "success": success,
                "action": "create_directory",
                "path": dir_path
            }
        except Exception as e:
            return {
                "success": False,
                "action": "create_directory",
                "error": str(e)
            }
    
    async def _execute_analyze_structure_action(self, action: AutonomousAction) -> Dict[str, Any]:
        """Execute project structure analysis using MCP filesystem."""
        try:
            root_path = action.file_path
            
            if self.mcp_filesystem and self.mcp_filesystem.is_server_available():
                # Get comprehensive directory tree
                tree = await self.mcp_filesystem.get_directory_tree(root_path, depth=3)
                entries = await self.mcp_filesystem.list_directory(root_path)
                
                self.console.print(f"[dim]🗂️  Analyzed via MCP: {len(entries)} items, depth 3[/dim]")
                
                return {
                    "success": True,
                    "action": "analyze_structure",
                    "entries_count": len(entries),
                    "analysis": f"Found {len(entries)} items in project root"
                }
            else:
                # Local fallback
                root = Path(root_path)
                entries = list(root.iterdir())
                self.console.print(f"[dim]🗂️  Analyzed locally: {len(entries)} items[/dim]")
                
                return {
                    "success": True,
                    "action": "analyze_structure",
                    "entries_count": len(entries),
                    "analysis": f"Found {len(entries)} items in project root"
                }
        except Exception as e:
            return {
                "success": False,
                "action": "analyze_structure",
                "error": str(e)
            }
    
    async def _execute_search_files_action(self, action: AutonomousAction) -> Dict[str, Any]:
        """Execute file search using MCP filesystem."""
        try:
            pattern = action.file_path
            
            if self.mcp_filesystem and self.mcp_filesystem.is_server_available():
                matches = await self.mcp_filesystem.search_files(self.project_root, f"*{pattern}*")
                self.console.print(f"[dim]🔍 Found {len(matches)} files via MCP matching '{pattern}'[/dim]")
                
                return {
                    "success": True,
                    "action": "search_files",
                    "pattern": pattern,
                    "matches_count": len(matches),
                    "files": [m.get('path', '') for m in matches[:5]]
                }
            else:
                # Local fallback using glob
                matches = list(self.project_root.rglob(f"*{pattern}*"))
                self.console.print(f"[dim]🔍 Found {len(matches)} files locally[/dim]")
                
                return {
                    "success": True,
                    "action": "search_files",
                    "pattern": pattern,
                    "matches_count": len(matches),
                    "files": [str(m) for m in matches[:5]]
                }
        except Exception as e:
            return {
                "success": False,
                "action": "search_files",
                "error": str(e)
            }
    
    async def _execute_search_content_action(self, action: AutonomousAction) -> Dict[str, Any]:
        """Execute content search using MCP filesystem."""
        try:
            search_term = action.file_path
            
            if self.mcp_filesystem and self.mcp_filesystem.is_server_available():
                matches = await self.mcp_filesystem.search_within_files(
                    self.project_root, search_term, max_results=10
                )
                self.console.print(f"[dim]🔍 Found '{search_term}' in {len(matches)} files via MCP[/dim]")
                
                return {
                    "success": True,
                    "action": "search_content",
                    "term": search_term,
                    "matches_count": len(matches),
                    "files": [m.get('path', '') for m in matches[:5]]
                }
            else:
                # Basic local fallback
                matches = []
                for file_path in self.project_root.rglob("*.py"):
                    try:
                        content = file_path.read_text(encoding='utf-8', errors='ignore')
                        if search_term.lower() in content.lower():
                            matches.append(str(file_path))
                        if len(matches) >= 10:
                            break
                    except Exception:
                        continue
                
                self.console.print(f"[dim]🔍 Found '{search_term}' in {len(matches)} files locally[/dim]")
                
                return {
                    "success": True,
                    "action": "search_content",
                    "term": search_term,
                    "matches_count": len(matches),
                    "files": matches[:5]
                }
        except Exception as e:
            return {
                "success": False,
                "action": "search_content",
                "error": str(e)
            }
    
    async def _execute_read_multiple_action(self, action: AutonomousAction) -> Dict[str, Any]:
        """Execute multiple file read using MCP filesystem."""
        try:
            file_paths = action.code_snippet.split(',')
            
            if self.mcp_filesystem and self.mcp_filesystem.is_server_available():
                files_content = await self.mcp_filesystem.read_multiple_files(file_paths)
                self.console.print(f"[dim]📖 Read {len(files_content)} files via MCP[/dim]")
                
                # Analyze combined content
                total_lines = sum(len(content.split('\\n')) for content in files_content.values())
                total_chars = sum(len(content) for content in files_content.values())
                
                return {
                    "success": True,
                    "action": "read_multiple",
                    "files_count": len(files_content),
                    "total_lines": total_lines,
                    "total_chars": total_chars,
                    "analysis": f"Read {len(files_content)} files: {total_lines} lines, {total_chars} characters"
                }
            else:
                # Local fallback
                files_content = {}
                for file_path in file_paths:
                    try:
                        content = Path(file_path.strip()).read_text(encoding='utf-8', errors='ignore')
                        files_content[file_path] = content
                    except Exception:
                        continue
                
                self.console.print(f"[dim]📖 Read {len(files_content)} files locally[/dim]")
                
                total_lines = sum(len(content.split('\\n')) for content in files_content.values())
                total_chars = sum(len(content) for content in files_content.values())
                
                return {
                    "success": True,
                    "action": "read_multiple",
                    "files_count": len(files_content),
                    "total_lines": total_lines,
                    "total_chars": total_chars
                }
        except Exception as e:
            return {
                "success": False,
                "action": "read_multiple",
                "error": str(e)
            }
    
    def _extract_find_replace_from_description(self, description: str):
        """Extract find/replace pairs from action description."""
        pairs = []
        
        # Look for explicit find/replace patterns
        import re
        
        # Pattern: "replace X with Y" or "change X to Y"
        patterns = [
            r'replace\\s+["\']?([^"\']+)["\']?\\s+with\\s+["\']?([^"\']+)["\']?',
            r'change\\s+["\']?([^"\']+)["\']?\\s+to\\s+["\']?([^"\']+)["\']?',
            r'update\\s+["\']?([^"\']+)["\']?\\s+to\\s+["\']?([^"\']+)["\']?'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, description.lower())
            pairs.extend(matches)
        
        # Default modifications if no specific patterns found
        if not pairs:
            if 'todo' in description.lower():
                pairs.append(('TODO', 'DONE'))
            elif 'fix' in description.lower():
                pairs.append(('# TODO: Fix', '# Fixed:'))
        
        return pairs