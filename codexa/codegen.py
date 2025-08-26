"""Code generation and file creation for Codexa."""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.prompt import Confirm

console = Console()


class CodeGenerator:
    """Handles code generation and file creation."""

    def __init__(self, project_root: Path, provider):
        """Initialize the code generator."""
        self.project_root = project_root
        self.provider = provider
        self.created_files: List[str] = []
        
    def detect_project_type(self) -> Dict[str, Any]:
        """Detect the project type and framework."""
        project_info = {
            'type': 'unknown',
            'framework': None,
            'language': None,
            'package_manager': None,
            'existing_files': []
        }
        
        # Check for common project files
        files_to_check = {
            'package.json': {'type': 'javascript', 'package_manager': 'npm'},
            'requirements.txt': {'type': 'python', 'package_manager': 'pip'},
            'pyproject.toml': {'type': 'python', 'package_manager': 'pip'},
            'Cargo.toml': {'type': 'rust', 'package_manager': 'cargo'},
            'go.mod': {'type': 'go', 'package_manager': 'go'},
            'pom.xml': {'type': 'java', 'package_manager': 'maven'},
            'composer.json': {'type': 'php', 'package_manager': 'composer'},
        }
        
        for file, info in files_to_check.items():
            file_path = self.project_root / file
            if file_path.exists():
                project_info.update(info)
                project_info['existing_files'].append(file)
                
                # Try to detect framework from package.json
                if file == 'package.json':
                    project_info['framework'] = self._detect_js_framework(file_path)
                elif file == 'requirements.txt':
                    project_info['framework'] = self._detect_python_framework(file_path)
        
        # Set language based on type
        if project_info['type'] != 'unknown':
            project_info['language'] = project_info['type']
        
        return project_info

    def _detect_js_framework(self, package_json_path: Path) -> Optional[str]:
        """Detect JavaScript framework from package.json."""
        try:
            import json
            with open(package_json_path, 'r') as f:
                data = json.load(f)
            
            dependencies = {**data.get('dependencies', {}), **data.get('devDependencies', {})}
            
            if 'react' in dependencies:
                return 'react'
            elif 'vue' in dependencies:
                return 'vue'
            elif 'angular' in dependencies or '@angular/core' in dependencies:
                return 'angular'
            elif 'next' in dependencies:
                return 'nextjs'
            elif 'svelte' in dependencies:
                return 'svelte'
            elif 'express' in dependencies:
                return 'express'
            
        except Exception:
            pass
        
        return None

    def _detect_python_framework(self, requirements_path: Path) -> Optional[str]:
        """Detect Python framework from requirements.txt."""
        try:
            with open(requirements_path, 'r') as f:
                content = f.read().lower()
            
            if 'flask' in content:
                return 'flask'
            elif 'django' in content:
                return 'django'
            elif 'fastapi' in content:
                return 'fastapi'
            elif 'streamlit' in content:
                return 'streamlit'
            
        except Exception:
            pass
        
        return None

    def generate_file(self, file_path: str, description: str, context: str = "") -> Tuple[bool, str]:
        """Generate a file based on description."""
        # Detect project info
        project_info = self.detect_project_type()
        
        # Build generation prompt
        generation_prompt = f"""Generate a {file_path} file based on this description:
{description}

Project Information:
- Type: {project_info['type']}
- Language: {project_info['language']}
- Framework: {project_info['framework']}
- Package Manager: {project_info['package_manager']}

Requirements:
1. Generate complete, working code
2. Follow best practices for the detected technology stack
3. Include necessary imports and dependencies
4. Add appropriate comments and documentation
5. Make it production-ready

{f'Additional Context: {context}' if context else ''}

Return ONLY the file content, no explanations or markdown formatting."""

        try:
            content = self.provider.ask(generation_prompt)
            
            # Clean up any markdown formatting if present
            content = self._clean_generated_code(content)
            
            return True, content
            
        except Exception as e:
            return False, f"Error generating file: {e}"

    def _clean_generated_code(self, content: str) -> str:
        """Clean up generated code by removing markdown formatting."""
        # Remove markdown code blocks
        content = re.sub(r'^```\w*\n', '', content, flags=re.MULTILINE)
        content = re.sub(r'\n```$', '', content, flags=re.MULTILINE)
        content = content.strip()
        
        return content

    def create_file(self, file_path: str, content: str, backup_existing: bool = True) -> bool:
        """Create a file with the given content."""
        full_path = self.project_root / file_path
        
        # Create directory if it doesn't exist
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Backup existing file if requested
        if full_path.exists() and backup_existing:
            backup_path = full_path.with_suffix(f"{full_path.suffix}.backup")
            full_path.rename(backup_path)
            console.print(f"[dim]Backed up existing {file_path} to {backup_path.name}[/dim]")
        
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.created_files.append(file_path)
            console.print(f"[green]✅ Created {file_path}[/green]")
            return True
            
        except Exception as e:
            console.print(f"[red]Error creating {file_path}: {e}[/red]")
            return False

    def generate_and_create_file(self, file_path: str, description: str, context: str = "", 
                                confirm_creation: bool = True) -> bool:
        """Generate and create a file with confirmation."""
        console.print(f"\n[cyan]🔨 Generating {file_path}...[/cyan]")
        
        success, content = self.generate_file(file_path, description, context)
        
        if not success:
            console.print(f"[red]Failed to generate {file_path}: {content}[/red]")
            return False
        
        # Show the generated content
        console.print(f"\n[bold]Generated content for {file_path}:[/bold]")
        
        # Detect language for syntax highlighting
        language = self._detect_file_language(file_path)
        syntax = Syntax(content, language, theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title=f"Generated: {file_path}", border_style="green"))
        
        # Ask for confirmation
        if confirm_creation:
            try:
                if not Confirm.ask(f"\nCreate {file_path}?", default=True):
                    console.print("[yellow]File creation cancelled.[/yellow]")
                    return False
            except EOFError:
                # Auto-confirm in non-interactive mode
                pass
        
        return self.create_file(file_path, content)

    def _detect_file_language(self, file_path: str) -> str:
        """Detect the programming language from file extension."""
        extension = Path(file_path).suffix.lower()
        
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'jsx',
            '.ts': 'typescript',
            '.tsx': 'tsx',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.sass': 'sass',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.md': 'markdown',
            '.rs': 'rust',
            '.go': 'go',
            '.java': 'java',
            '.php': 'php',
            '.rb': 'ruby',
            '.sh': 'bash',
            '.sql': 'sql'
        }
        
        return language_map.get(extension, 'text')

    def create_project_structure(self, structure_description: str, context: str = "") -> List[str]:
        """Create a complete project structure."""
        project_info = self.detect_project_type()
        
        structure_prompt = f"""Create a project structure based on this description:
{structure_description}

Project Information:
- Type: {project_info['type']}
- Language: {project_info['language']}
- Framework: {project_info['framework']}

Generate a list of files and directories to create, with file contents where appropriate.
Follow best practices for the technology stack.

Format your response as a JSON structure:
{{
    "directories": ["dir1", "dir2/subdir"],
    "files": [
        {{
            "path": "file.ext",
            "description": "What this file does",
            "content": "actual file content (for code files)"
        }}
    ]
}}

{f'Additional Context: {context}' if context else ''}"""

        try:
            response = self.provider.ask(structure_prompt)
            
            # Parse the JSON response
            import json
            
            # Clean up response if it contains markdown
            response = response.strip()
            if response.startswith('```'):
                response = re.sub(r'^```\w*\n', '', response, flags=re.MULTILINE)
                response = re.sub(r'\n```$', '', response, flags=re.MULTILINE)
            
            structure_data = json.loads(response)
            created_files = []
            
            # Create directories
            for directory in structure_data.get('directories', []):
                dir_path = self.project_root / directory
                dir_path.mkdir(parents=True, exist_ok=True)
                console.print(f"[blue]📁 Created directory: {directory}[/blue]")
            
            # Create files
            for file_info in structure_data.get('files', []):
                file_path = file_info['path']
                file_content = file_info.get('content', '')
                
                if file_content:
                    if self.create_file(file_path, file_content, backup_existing=True):
                        created_files.append(file_path)
                else:
                    # Generate content based on description
                    description = file_info.get('description', f'Create {file_path}')
                    if self.generate_and_create_file(file_path, description, context, confirm_creation=False):
                        created_files.append(file_path)
            
            return created_files
            
        except Exception as e:
            console.print(f"[red]Error creating project structure: {e}[/red]")
            return []

    def get_created_files(self) -> List[str]:
        """Get list of files created in this session."""
        return self.created_files.copy()

    def clear_created_files(self) -> None:
        """Clear the list of created files."""
        self.created_files.clear()

    def suggest_next_files(self, current_task: str, context: str = "") -> List[Dict[str, str]]:
        """Suggest next files to create based on current task."""
        project_info = self.detect_project_type()
        
        suggestion_prompt = f"""Based on the current task and project state, suggest 3-5 files that should be created next.

Current Task: {current_task}

Project Information:
- Type: {project_info['type']}
- Framework: {project_info['framework']}
- Existing files: {project_info['existing_files']}
- Recently created: {self.created_files[-5:]}

Return suggestions as JSON:
[
    {{
        "path": "path/to/file.ext",
        "priority": "high|medium|low",
        "description": "What this file does and why it's needed"
    }}
]

{f'Context: {context}' if context else ''}"""

        try:
            response = self.provider.ask(suggestion_prompt)
            
            # Clean and parse JSON response
            response = response.strip()
            if response.startswith('```'):
                response = re.sub(r'^```\w*\n', '', response, flags=re.MULTILINE)
                response = re.sub(r'\n```$', '', response, flags=re.MULTILINE)
            
            import json
            suggestions = json.loads(response)
            
            return suggestions
            
        except Exception as e:
            console.print(f"[red]Error generating file suggestions: {e}[/red]")
            return []

    def show_project_overview(self) -> None:
        """Show an overview of the project structure and status."""
        project_info = self.detect_project_type()
        
        overview = f"""[bold]Project Overview[/bold]

[blue]Type:[/blue] {project_info['type']}
[blue]Language:[/blue] {project_info['language']}
[blue]Framework:[/blue] {project_info['framework'] or 'None detected'}
[blue]Package Manager:[/blue] {project_info['package_manager'] or 'None'}

[blue]Existing Files:[/blue] {len(project_info['existing_files'])}
{chr(10).join(f"  • {f}" for f in project_info['existing_files'])}

[blue]Created This Session:[/blue] {len(self.created_files)}
{chr(10).join(f"  • {f}" for f in self.created_files[-10:])}"""

        console.print(Panel(overview, title="Project Status", border_style="cyan"))