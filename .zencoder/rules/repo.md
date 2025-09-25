---
description: Repository Information Overview
alwaysApply: true
---

# Codexa Information

## Summary
Codexa is an AI-powered CLI coding assistant that provides interactive coding sessions with autonomous capabilities. It features a dual-mode architecture supporting both basic and enhanced functionality, with graceful degradation when dependencies are unavailable.

## Structure
- **codexa/**: Main package containing core functionality
  - **analytics/**: Usage analytics and dashboard
  - **commands/**: Slash command system (/help, /status, etc.)
  - **display/**: ASCII art rendering with multiple themes
  - **mcp/**: MCP server integration for advanced features
  - **tools/**: Tool-based architecture for enhanced functionality
  - **ui/**: User interface components
- **tests/**: Test suite for the application
- **docs/**: Documentation files

## Language & Runtime
**Language**: Python
**Version**: >=3.8 (supports 3.8, 3.9, 3.10, 3.11, 3.12)
**Build System**: setuptools
**Package Manager**: pip

## Dependencies
**Main Dependencies**:
- typer[all]>=0.12.0 - CLI framework
- rich>=13.7.0 - Terminal formatting
- openai>=1.50.0 - OpenAI API integration
- anthropic>=0.34.0 - Anthropic API integration
- pyyaml>=6.0 - Configuration file handling
- python-dotenv>=1.0.0 - Environment variable loading

**Development Dependencies**:
- pytest>=7.0 - Testing framework
- black>=23.0 - Code formatting
- flake8>=6.0 - Linting
- mypy>=1.0 - Type checking

## Build & Installation
```bash
# Install in development mode
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"

# Verify installation
python -c "import codexa; print('Installation verified')"
```

## Entry Points
**Main CLI**: `codexa.cli:main`

The application has a dual-mode architecture:
- **Basic Mode**: `core.py` - Fundamental features with minimal dependencies
- **Enhanced Mode**: `enhanced_core.py` - Advanced features with tool-based architecture

## Testing
**Framework**: pytest
**Test Location**: tests/
**Naming Convention**: test_*.py
**Run Command**:
```bash
python -m pytest tests/
```

## Key Features
- **Autonomous Mode**: Proactive file discovery and code modification
- **MCP Integration**: Context7, Sequential, Magic, and Playwright servers
- **Tool System**: Dynamic tool-based architecture
- **Command System**: Slash commands for common operations
- **Provider System**: Support for multiple AI providers (OpenAI, Anthropic, OpenRouter)
- **Display System**: ASCII art rendering with multiple themes