"""
Project Structure Plugin for Codexa - project scaffolding and structure analysis.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from codexa.plugins.plugin_manager import Plugin, PluginInfo
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.prompt import Prompt, Confirm


@dataclass
class ProjectTemplate:
    """Project template definition."""
    name: str
    description: str
    language: str
    version: str
    structure: Dict[str, Any]
    variables: Dict[str, str]


@dataclass
class StructureAnalysis:
    """Project structure analysis result."""
    project_type: str
    confidence: float
    structure_score: float
    missing_files: List[str]
    extra_files: List[str]
    recommendations: List[str]


class ProjectStructurePlugin(Plugin):
    """Project structure management plugin."""
    
    def __init__(self, info: PluginInfo):
        super().__init__(info)
        self.console = Console()
        self.settings = {}
        self.templates_path = Path(__file__).parent / "templates"
        self.templates = {}
        
    async def initialize(self, context: Dict[str, Any]) -> bool:
        """Initialize the plugin."""
        try:
            self.logger.info("Initializing Project Structure Plugin...")
            
            # Load settings
            self.settings = self.info.to_dict().get('settings', {})
            
            # Load built-in templates
            await self._load_templates()
            
            self.logger.info(f"Project Structure Plugin initialized with {len(self.templates)} templates")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Project Structure Plugin: {e}")
            return False
    
    async def shutdown(self) -> bool:
        """Shutdown the plugin."""
        self.logger.info("Project Structure Plugin shutdown")
        return True
    
    async def on_command(self, command: str, args: Dict[str, Any]) -> Optional[str]:
        """Handle plugin commands."""
        try:
            if command == "scaffold":
                return await self._handle_scaffold(args)
            elif command == "template":
                return await self._handle_template(args)
            elif command == "structure-analyze":
                return await self._handle_structure_analyze(args)
            elif command == "project-init":
                return await self._handle_project_init(args)
            elif command == "best-practices":
                return await self._handle_best_practices(args)
            else:
                return f"Unknown command: {command}"
                
        except Exception as e:
            self.logger.error(f"Command {command} failed: {e}")
            return f"Command failed: {e}"
    
    async def _handle_scaffold(self, args: Dict[str, Any]) -> str:
        """Handle project scaffolding."""
        try:
            template_name = args.get('template', 'python_basic')
            project_name = args.get('name')
            target_dir = args.get('directory', '.')
            
            if template_name not in self.templates:
                available = ', '.join(self.templates.keys())
                return f"[red]Template '{template_name}' not found. Available: {available}[/red]"
            
            if not project_name:
                return "[red]Project name required for scaffolding[/red]"
            
            template = self.templates[template_name]
            
            # Create project directory
            project_path = Path(target_dir) / project_name
            if project_path.exists():
                return f"[red]Directory '{project_path}' already exists[/red]"
            
            # Scaffold the project
            await self._scaffold_project(template, project_path, project_name)
            
            return f"[green]✅ Project '{project_name}' scaffolded successfully using '{template_name}' template[/green]"
            
        except Exception as e:
            return f"[red]Scaffolding failed: {e}[/red]"
    
    async def _handle_template(self, args: Dict[str, Any]) -> str:
        """Handle template management."""
        try:
            action = args.get('action', 'list')
            
            if action == 'list':
                return await self._list_templates()
            elif action == 'show':
                template_name = args.get('name')
                if not template_name:
                    return "[red]Template name required[/red]"
                return await self._show_template(template_name)
            elif action == 'create':
                return await self._create_custom_template(args)
            else:
                return f"[red]Unknown template action: {action}[/red]"
                
        except Exception as e:
            return f"[red]Template operation failed: {e}[/red]"
    
    async def _handle_structure_analyze(self, args: Dict[str, Any]) -> str:
        """Handle project structure analysis."""
        try:
            target_path = Path(args.get('path', '.'))
            
            if not target_path.exists():
                return f"[red]Path '{target_path}' does not exist[/red]"
            
            analysis = await self._analyze_project_structure(target_path)
            
            # Create analysis report
            panel_content = []
            panel_content.append(f"[bold cyan]Project Type:[/bold cyan] {analysis.project_type}")
            panel_content.append(f"[bold cyan]Confidence:[/bold cyan] {analysis.confidence:.1%}")
            panel_content.append(f"[bold cyan]Structure Score:[/bold cyan] {analysis.structure_score:.1f}/10.0")
            
            if analysis.missing_files:
                panel_content.append("\n[bold yellow]Missing Files:[/bold yellow]")
                for file in analysis.missing_files[:5]:
                    panel_content.append(f"  • {file}")
                if len(analysis.missing_files) > 5:
                    panel_content.append(f"  ... and {len(analysis.missing_files) - 5} more")
            
            if analysis.recommendations:
                panel_content.append("\n[bold green]Recommendations:[/bold green]")
                for rec in analysis.recommendations[:5]:
                    panel_content.append(f"  • {rec}")
            
            panel = Panel(
                "\n".join(panel_content),
                title="📊 Project Structure Analysis",
                border_style="cyan"
            )
            
            with self.console.capture() as capture:
                self.console.print(panel)
            
            return capture.get()
            
        except Exception as e:
            return f"[red]Structure analysis failed: {e}[/red]"
    
    async def _handle_project_init(self, args: Dict[str, Any]) -> str:
        """Handle project initialization."""
        try:
            project_type = args.get('type')
            interactive = args.get('interactive', True)
            
            if not project_type and interactive:
                # Interactive project type selection
                available_types = list(self.templates.keys())
                self.console.print("[bold cyan]Available project types:[/bold cyan]")
                for i, ptype in enumerate(available_types, 1):
                    template = self.templates[ptype]
                    self.console.print(f"  {i}. [green]{ptype}[/green] - {template.description}")
                
                # In a real implementation, you'd use Prompt.ask for user input
                project_type = available_types[0]  # Default to first available
            
            if not project_type:
                return "[red]Project type required[/red]"
            
            if project_type not in self.templates:
                return f"[red]Unknown project type: {project_type}[/red]"
            
            # Initialize project in current directory
            template = self.templates[project_type]
            current_path = Path('.')
            project_name = current_path.name
            
            await self._initialize_existing_project(template, current_path, project_name)
            
            return f"[green]✅ Project initialized as '{project_type}' in current directory[/green]"
            
        except Exception as e:
            return f"[red]Project initialization failed: {e}[/red]"
    
    async def _handle_best_practices(self, args: Dict[str, Any]) -> str:
        """Handle best practices recommendations."""
        try:
            project_path = Path(args.get('path', '.'))
            project_type = args.get('type')
            
            if not project_type:
                # Auto-detect project type
                analysis = await self._analyze_project_structure(project_path)
                project_type = analysis.project_type
            
            recommendations = await self._get_best_practices(project_path, project_type)
            
            if not recommendations:
                return "[green]✅ Project follows best practices![/green]"
            
            # Display recommendations
            table = Table(title="Best Practices Recommendations")
            table.add_column("Category", style="cyan")
            table.add_column("Recommendation", style="white")
            table.add_column("Priority", style="yellow")
            
            for rec in recommendations:
                table.add_row(rec['category'], rec['message'], rec['priority'])
            
            with self.console.capture() as capture:
                self.console.print(table)
            
            return capture.get()
            
        except Exception as e:
            return f"[red]Best practices analysis failed: {e}[/red]"
    
    # Template management methods
    async def _load_templates(self):
        """Load built-in templates."""
        if not self.templates_path.exists():
            self.logger.warning("Templates directory not found")
            return
        
        for template_file in self.templates_path.glob("*.yaml"):
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    template_data = yaml.safe_load(f)
                
                template = ProjectTemplate(
                    name=template_data['name'],
                    description=template_data['description'],
                    language=template_data['language'],
                    version=template_data['version'],
                    structure=template_data['structure'],
                    variables=template_data.get('variables', {})
                )
                
                self.templates[template_file.stem] = template
                
            except Exception as e:
                self.logger.error(f"Failed to load template {template_file}: {e}")
    
    async def _list_templates(self) -> str:
        """List available templates."""
        if not self.templates:
            return "[yellow]No templates available[/yellow]"
        
        table = Table(title="Available Project Templates")
        table.add_column("Template", style="cyan")
        table.add_column("Language", style="green")
        table.add_column("Description", style="white")
        table.add_column("Version", style="dim")
        
        for name, template in self.templates.items():
            table.add_row(name, template.language, template.description, template.version)
        
        with self.console.capture() as capture:
            self.console.print(table)
        
        return capture.get()
    
    async def _show_template(self, template_name: str) -> str:
        """Show template details."""
        if template_name not in self.templates:
            return f"[red]Template '{template_name}' not found[/red]"
        
        template = self.templates[template_name]
        
        # Create template structure tree
        tree = Tree(f"[bold cyan]{template.name}[/bold cyan]")
        
        # Add directories
        if 'directories' in template.structure:
            dir_branch = tree.add("[bold green]Directories[/bold green]")
            for directory in template.structure['directories']:
                dir_branch.add(f"📁 {directory}")
        
        # Add files
        if 'files' in template.structure:
            file_branch = tree.add("[bold blue]Files[/bold blue]")
            for file_info in template.structure['files']:
                path = file_info['path']
                template_type = file_info.get('template', 'basic')
                file_branch.add(f"📄 {path} ({template_type})")
        
        with self.console.capture() as capture:
            self.console.print(f"[bold cyan]Template: {template.name}[/bold cyan]")
            self.console.print(f"[dim]{template.description}[/dim]")
            self.console.print(f"Language: {template.language} | Version: {template.version}\n")
            self.console.print(tree)
        
        return capture.get()
    
    # Project scaffolding methods
    async def _scaffold_project(self, template: ProjectTemplate, project_path: Path, project_name: str):
        """Scaffold a project from template."""
        # Create project directory
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Create directories
        if 'directories' in template.structure:
            for directory in template.structure['directories']:
                dir_path = project_path / directory
                dir_path.mkdir(parents=True, exist_ok=True)
        
        # Create files
        if 'files' in template.structure:
            for file_info in template.structure['files']:
                file_path = project_path / file_info['path']
                template_name = file_info.get('template', 'basic')
                
                # Generate file content
                content = await self._generate_file_content(template_name, template.variables, project_name)
                
                # Create parent directories if needed
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
    
    async def _initialize_existing_project(self, template: ProjectTemplate, project_path: Path, project_name: str):
        """Initialize existing directory with template."""
        # Only create missing files and directories
        if 'directories' in template.structure:
            for directory in template.structure['directories']:
                dir_path = project_path / directory
                if not dir_path.exists():
                    dir_path.mkdir(parents=True, exist_ok=True)
        
        if 'files' in template.structure:
            for file_info in template.structure['files']:
                file_path = project_path / file_info['path']
                if not file_path.exists():
                    template_name = file_info.get('template', 'basic')
                    content = await self._generate_file_content(template_name, template.variables, project_name)
                    
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
    
    async def _generate_file_content(self, template_name: str, variables: Dict[str, str], project_name: str) -> str:
        """Generate file content from template."""
        # Template content generators
        templates = {
            'python_requirements': "",
            'python_dev_requirements': "pytest\nblack\nisort\nmypy\npylint\n",
            'python_setup': f"""from setuptools import setup, find_packages

setup(
    name="{project_name}",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={{"": "src"}},
    python_requires=">=3.8",
)""",
            'python_pyproject': f"""[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{project_name}"
version = "0.1.0"
description = "A Python project"
requires-python = ">=3.8"

[tool.black]
line-length = 88
target-version = ["py38"]

[tool.isort]
profile = "black"

[tool.mypy]
python_version = "3.8"
strict = true
""",
            'python_readme': f"""# {project_name}

A Python project created with Codexa.

## Installation

```bash
pip install -e .
```

## Development

```bash
pip install -r requirements-dev.txt
```

## Usage

```python
import {project_name}
```
""",
            'python_gitignore': """# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
.hypothesis/
.pytest_cache/

# Virtual environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db
""",
            'python_init': '"""Package initialization."""\n',
            'python_test_basic': f'''"""Basic tests for {project_name}."""

def test_basic():
    """Test basic functionality."""
    assert True
''',
            'python_github_ci': f"""name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, '3.10', '3.11']

    steps:
    - uses: actions/checkout@v3
    - name: Set up Python ${{{{ matrix.python-version }}}}
      uses: actions/setup-python@v4
      with:
        python-version: ${{{{ matrix.python-version }}}}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements-dev.txt
        pip install -e .
    
    - name: Lint with black and isort
      run: |
        black --check src tests
        isort --check src tests
    
    - name: Type check with mypy
      run: |
        mypy src
    
    - name: Test with pytest
      run: |
        pytest
""",
            'basic': "# Generated by Codexa Project Structure Plugin\n"
        }
        
        return templates.get(template_name, templates['basic'])
    
    # Analysis methods
    async def _analyze_project_structure(self, project_path: Path) -> StructureAnalysis:
        """Analyze project structure."""
        # Detect project type
        project_type = await self._detect_project_type(project_path)
        confidence = 0.8  # Placeholder
        
        # Calculate structure score
        structure_score = await self._calculate_structure_score(project_path, project_type)
        
        # Find missing files
        missing_files = await self._find_missing_files(project_path, project_type)
        
        # Generate recommendations
        recommendations = await self._generate_recommendations(project_path, project_type)
        
        return StructureAnalysis(
            project_type=project_type,
            confidence=confidence,
            structure_score=structure_score,
            missing_files=missing_files,
            extra_files=[],  # Placeholder
            recommendations=recommendations
        )
    
    async def _detect_project_type(self, project_path: Path) -> str:
        """Detect project type from files."""
        # Check for Python indicators
        if any(f.exists() for f in [
            project_path / "setup.py",
            project_path / "pyproject.toml",
            project_path / "requirements.txt"
        ]):
            return "Python"
        
        # Check for JavaScript/Node indicators
        if (project_path / "package.json").exists():
            return "JavaScript/Node"
        
        # Check for Rust indicators
        if (project_path / "Cargo.toml").exists():
            return "Rust"
        
        # Check for Go indicators
        if (project_path / "go.mod").exists():
            return "Go"
        
        return "Unknown"
    
    async def _calculate_structure_score(self, project_path: Path, project_type: str) -> float:
        """Calculate project structure score."""
        score = 5.0  # Base score
        
        # Check for common good practices
        if (project_path / "README.md").exists():
            score += 1.0
        if (project_path / ".gitignore").exists():
            score += 1.0
        if (project_path / "tests").exists():
            score += 1.5
        if (project_path / "docs").exists():
            score += 1.0
        if any(f.exists() for f in [project_path / ".github", project_path / ".gitlab-ci.yml"]):
            score += 0.5
        
        return min(score, 10.0)
    
    async def _find_missing_files(self, project_path: Path, project_type: str) -> List[str]:
        """Find missing important files."""
        missing = []
        
        # Common files
        if not (project_path / "README.md").exists():
            missing.append("README.md")
        if not (project_path / ".gitignore").exists():
            missing.append(".gitignore")
        
        # Python-specific
        if project_type == "Python":
            if not (project_path / "requirements.txt").exists() and not (project_path / "pyproject.toml").exists():
                missing.append("requirements.txt or pyproject.toml")
            if not (project_path / "tests").exists():
                missing.append("tests/ directory")
        
        return missing
    
    async def _generate_recommendations(self, project_path: Path, project_type: str) -> List[str]:
        """Generate structure recommendations."""
        recommendations = []
        
        if not (project_path / "tests").exists():
            recommendations.append("Add a tests directory for unit tests")
        
        if not (project_path / "docs").exists():
            recommendations.append("Consider adding documentation")
        
        if project_type == "Python" and not (project_path / "src").exists():
            recommendations.append("Consider using src/ layout for Python projects")
        
        return recommendations
    
    async def _get_best_practices(self, project_path: Path, project_type: str) -> List[Dict[str, str]]:
        """Get best practices recommendations."""
        recommendations = []
        
        # Example recommendations
        if not (project_path / "CHANGELOG.md").exists():
            recommendations.append({
                'category': 'Documentation',
                'message': 'Add CHANGELOG.md to track project changes',
                'priority': 'Medium'
            })
        
        if project_type == "Python" and not (project_path / "pyproject.toml").exists():
            recommendations.append({
                'category': 'Configuration',
                'message': 'Use pyproject.toml for modern Python packaging',
                'priority': 'High'
            })
        
        return recommendations
    
    async def _create_custom_template(self, args: Dict[str, Any]) -> str:
        """Create a custom template (placeholder)."""
        return "[yellow]Custom template creation not yet implemented[/yellow]"