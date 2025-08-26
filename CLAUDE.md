# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Codexa is an AI-powered CLI coding assistant that serves as a proactive development partner. It features enhanced capabilities including animated ASCII art, runtime provider switching, MCP server integration, and comprehensive slash commands.

## Development Commands

### Environment Setup
```bash
# Install in development mode
pip install -e .

# Install with pipx (recommended for users)
pipx install .

# Install dependencies
pip install -r requirements.txt
```

### Testing Commands
```bash
# Run tests (when implemented)
pytest

# Run with coverage
pytest --cov=codexa

# Test specific module
pytest tests/test_config.py

# Test enhanced features functionality
PYTHONPATH=/home/mike/codexa python -c "from codexa.enhanced_core import EnhancedCodexaAgent; agent = EnhancedCodexaAgent(); print('✅ Enhanced agent created')"
```

### Code Quality
```bash
# Format code
black codexa/

# Lint code
flake8 codexa/

# Type checking
mypy codexa/
```

### Running Codexa
```bash
# Start interactive session
codexa

# Show version
codexa --version

# Show configuration
codexa config

# Initialize setup
codexa setup
```

## Architecture Overview

### Core Architecture Layers

**Layer 1: CLI Interface**
- `cli.py`: Main entry point with typer-based CLI
- `enhanced_cli.py`: Enhanced CLI with additional features
- Auto-detects enhanced features availability with graceful fallback

**Layer 2: Agent System**
- `core.py`: Basic CodexaAgent implementation
- `enhanced_core.py`: Enhanced agent with Phase 3 capabilities including error handling, user guidance, and advanced UX
- Dual-mode operation: Enhanced features when available, basic mode as fallback

**Layer 3: Provider System**
- `providers.py`: Basic AI provider implementations
- `enhanced_providers.py`: Enhanced provider factory with runtime switching
- `config.py` / `enhanced_config.py`: Configuration management
- Support for OpenAI, Anthropic, and OpenRouter with intelligent fallback

**Layer 4: MCP Integration**
- `mcp_service.py`: Model Context Protocol service integration
- `mcp/`: MCP server management, health monitoring, and connection handling
- Support for Context7, Sequential, Magic, and Playwright servers

**Layer 5: Command System**
- `commands/`: Slash command registry, parser, and executor
- Built-in commands: `/help`, `/status`, `/provider`, `/model`, `/mcp`, `/commands`, `/config`
- Extensible command registration system

**Layer 6: Enhanced UX**
- `display/`: ASCII art renderer with 5 themes, animations, and startup sequences
- `ui/`: Interactive startup flow, contextual help, and onboarding
- `ux/`: Suggestion engine and user experience optimization
- `error_handling/`: Comprehensive error management and user guidance

### Key Architectural Patterns

**Enhanced Feature Detection**: Uses try/import pattern to gracefully handle enhanced features:
```python
try:
    from .enhanced_core import EnhancedCodexaAgent as CodexaAgent
    ENHANCED_FEATURES = True
except ImportError:
    from .core import CodexaAgent
    ENHANCED_FEATURES = False
```

**Dual-Mode Operation**: Basic and enhanced modes with automatic fallback ensures compatibility

**MCP Server Integration**: Pluggable MCP servers for specialized capabilities:
- Context7: Documentation and code examples
- Sequential: Complex reasoning and analysis
- Magic: UI component generation
- Playwright: Cross-browser testing

**Provider Factory Pattern**: Runtime switching between AI providers with intelligent routing

**Command Registry Pattern**: Extensible slash command system with built-in commands

## Configuration System

### Configuration Files
- `~/.codexarc`: User configuration file (YAML format)
- `CODEXA.md`: Project-specific guidelines (auto-generated)
- `.env`: Environment variables for API keys

### Environment Variables
- `OPENAI_API_KEY`: OpenAI API key
- `ANTHROPIC_API_KEY`: Anthropic API key  
- `OPENROUTER_API_KEY`: OpenRouter API key

### Theme System
5 ASCII art themes available:
- `default`: Clean cyan styling
- `minimal`: Simple and elegant
- `cyberpunk`: Bright magenta futuristic
- `retro`: Yellow/green terminal aesthetics
- `matrix`: Green-on-black matrix-inspired

## Development Patterns

### Error Handling
- Comprehensive error management with `ErrorManager` class
- Context-aware error reporting and user guidance
- Automatic recovery strategies where possible
- Graceful degradation when enhanced features unavailable

### Async/Await Pattern
Enhanced core uses async/await for:
- MCP server communication
- Provider interactions
- Interactive startup flows
- Command execution

### Modular Design
- Clear separation of concerns across modules
- Plugin architecture for extensibility
- MCP server integration as pluggable modules
- Command system designed for easy extension

### Configuration Management
- Layered configuration: defaults → user config → project config → runtime
- Enhanced config system with feature flags
- Validation and migration support

## Key Files and Locations

### Core Files
- `codexa/cli.py`: Main CLI entry point (lines 29-175)
- `codexa/enhanced_core.py`: Enhanced agent implementation (lines 77-940)
- `codexa/config.py` / `enhanced_config.py`: Configuration systems
- `pyproject.toml`: Package configuration and dependencies

### Module Structure
- `codexa/commands/`: Command system implementation
- `codexa/display/`: ASCII art and visual system
- `codexa/mcp/`: MCP server integration
- `codexa/ui/`: User interface components
- `codexa/error_handling/`: Error management system

### Testing
- `tests/`: Test suite (basic structure present)
- `test_e2e_workflows.py`: End-to-end testing

## Development Guidelines

### Code Style
- Follow PEP8 with 88-character line length (Black formatting)
- Type hints required (`mypy` configuration in pyproject.toml)
- Comprehensive docstrings for all public methods

### Error Handling Philosophy
- Never fail silently - always provide meaningful error messages
- Graceful degradation when enhanced features unavailable
- Context-aware error reporting with user guidance
- Automatic recovery where possible

### Testing Requirements
- Use pytest for all tests
- Maintain >90% code coverage where practical
- Test both basic and enhanced feature modes
- Mock external dependencies (AI providers, MCP servers)

### Documentation Standards
- Keep README.md up to date with feature changes
- Update CODEXA.md when changing behavior
- Inline comments for complex logic
- Type hints for all public interfaces

## MCP Server Development

### Adding New MCP Servers
1. Add server configuration to `enhanced_config.py`
2. Update `mcp_service.py` with server-specific methods
3. Add health monitoring in `mcp/advanced_health_monitor.py`
4. Update command system if server needs specific commands

### Server Integration Pattern
```python
# In mcp_service.py
async def query_new_server(self, request: str) -> Dict:
    if "new_server" not in self.enabled_servers:
        raise ValueError("New server not enabled")
    
    # Server-specific implementation
    return await self._call_server("new_server", request)
```

## Performance Considerations

- Startup time optimized: <1s typical, <3s with full features
- Memory usage: <100MB typical usage
- ASCII rendering: 30fps real-time animations
- Provider switching: <5s including model loading
- Lazy loading of enhanced features to improve startup time

## Security Notes

- API keys stored in environment variables only
- No data collection or personal information storage
- Secure API communications only
- Plugin system uses security sandboxing
- Local-first processing approach