# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Core Commands
```bash
# Start Codexa interactive session
codexa

# Initialize project (creates .codexa/ and CODEXA.md)
codexa init

# Check configuration and API key status
codexa config

# Setup configuration for first-time use
codexa setup

# Check version
codexa --version
```

### Development Installation
```bash
# Install in development mode (recommended for development)
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"

# Verify installation
python -c "import codexa; print('Installation verified')"
```

### Testing
```bash
# Run tests (if pytest is available)
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_config.py

# Run with verbose output
python -m pytest -v tests/
```

### Code Quality
```bash
# Format code (if black is available)
python -m black codexa/

# Type checking (if mypy is available)
python -m mypy codexa/

# Linting (if flake8 is available)
python -m flake8 codexa/
```

## Architecture Overview

Codexa is built with a dual-mode architecture supporting both basic and enhanced functionality:

### Core Architecture Layers

1. **Entry Points**
   - `cli.py` - Main CLI with fallback to basic mode
   - `enhanced_cli.py` - Enhanced CLI for full-featured mode
   - Both support the same command interface but enhanced mode provides additional capabilities

2. **Agent Systems**
   - `core.py` - Basic Codexa agent with fundamental features
   - `enhanced_core.py` - Advanced agent with tool-based architecture, MCP integration
   - Automatic fallback from enhanced to basic mode if dependencies unavailable

3. **Configuration**
   - `config.py` - Basic configuration handling
   - `enhanced_config.py` - Advanced configuration with provider switching
   - Supports multiple AI providers: OpenAI, Anthropic, OpenRouter

4. **Provider System**
   - `providers.py` - Basic provider factory
   - `enhanced_providers.py` - Advanced provider management with runtime switching
   - Graceful degradation when API keys are missing

### Enhanced Features (Phase 3)

When enhanced features are available, Codexa includes:

- **Tool System** (`tools/` directory)
  - Base tool framework with interfaces and managers
  - Enhanced tools for advanced functionality
  - Filesystem tools for file operations
  - MCP tools for server integration
  - AI provider tools for specialized AI operations

- **Command System** (`commands/` directory)
  - Slash command framework (/help, /status, /provider, etc.)
  - Built-in commands for common workflows
  - Extensible command registry

- **Display System** (`display/` directory)
  - ASCII art rendering with multiple themes
  - Animation support
  - Theme management (default, minimal, cyberpunk, retro, matrix)

- **MCP Integration** (`mcp/` directory)
  - Context7 server for documentation
  - Sequential server for complex reasoning
  - Magic server for UI generation
  - Playwright server for testing automation

### Key Design Patterns

1. **Graceful Degradation**: All enhanced features have fallbacks to basic functionality
2. **Import Guards**: Try/except blocks prevent import errors from breaking the system
3. **Factory Pattern**: Providers and tools use factory patterns for flexible instantiation
4. **Configuration Layering**: Multiple configuration files with inheritance
5. **Async Support**: Enhanced mode uses asyncio for better performance

### File Structure Patterns

- **Modular Organization**: Related functionality grouped in directories
- **Base Classes**: Common interfaces in `base/` subdirectories
- **Plugin Architecture**: Available plugins in `plugins/available/`
- **Testing Structure**: Tests mirror source structure
- **Configuration Files**: Support for both YAML and Python-based config

## Development Workflow

### Setting Up Development Environment

1. **API Configuration**: Set at least one API key environment variable:
   ```bash
   export OPENAI_API_KEY="your-key"
   # or
   export ANTHROPIC_API_KEY="your-key" 
   # or
   export OPENROUTER_API_KEY="your-key"
   ```

2. **Development Installation**:
   ```bash
   pip install -e .
   ```

3. **Test Enhanced Features**:
   ```bash
   python -c "from codexa.cli import ENHANCED_FEATURES; print(f'Enhanced: {ENHANCED_FEATURES}')"
   ```

### Working with the Codebase

- **Enhanced vs Basic Mode**: Check `ENHANCED_FEATURES` flag to determine available functionality
- **Provider Testing**: Use different API keys to test provider switching
- **MCP Development**: MCP servers can be enabled/disabled in configuration
- **Theme Development**: ASCII art themes are in `display/themes.py`

### Important Implementation Details

- **Dual Entry Points**: `cli.py` handles both basic and enhanced modes
- **Import Safety**: All enhanced imports are wrapped in try/except blocks
- **Configuration Hierarchy**: Environment variables > config files > defaults
- **Error Handling**: Rich console output for user-friendly error messages
- **Session Management**: Both sync and async session support

### Testing Considerations

- Test both enhanced and basic modes
- Mock API calls for unit tests
- Test configuration loading and validation
- Verify graceful degradation scenarios
- Test provider switching functionality

## Serena MCP Server Integration

Codexa integrates with Serena MCP server for advanced semantic code analysis and editing capabilities. Serena provides language server integration for intelligent code operations.

### Features
- **Semantic Code Analysis**: Symbol search, reference finding, code structure analysis
- **Intelligent File Operations**: Language-aware editing, pattern search, regex replacement
- **Project Management**: Project activation, onboarding, indexing for better analysis
- **Shell Execution**: Context-aware command execution with project awareness
- **Memory System**: Project-specific knowledge storage and retrieval

### Configuration

Enable Serena in your `~/.codexarc` configuration:

```yaml
mcp_servers:
  serena:
    enabled: true
    command: ["uvx", "--from", "git+https://github.com/oraios/serena", "serena", "start-mcp-server"]
    args: ["--context", "ide-assistant"]
    timeout: 30
    project_path: null  # Set to auto-activate a project
    auto_index: true
    deployment_mode: "uvx"  # Options: uvx, local, docker
```

### Deployment Options

**Option 1: uvx (Recommended)**
```yaml
serena:
  command: ["uvx", "--from", "git+https://github.com/oraios/serena", "serena", "start-mcp-server"]
  args: ["--context", "ide-assistant"]
```

**Option 2: Local Installation**
```bash
git clone https://github.com/oraios/serena
cd serena
```
```yaml
serena:
  command: ["uv", "run", "--directory", "/path/to/serena", "serena", "start-mcp-server"]
  args: ["--context", "ide-assistant"]
```

**Option 3: Docker (Experimental)**
```yaml
serena:
  command: ["docker", "run", "--rm", "-i", "--network", "host", "-v", "/your/projects:/workspaces/projects", "ghcr.io/oraios/serena:latest", "serena", "start-mcp-server"]
  args: ["--transport", "stdio"]
```

### Available Tools

Serena provides the following tool categories:

**Semantic Code Analysis:**
- `serena_code_analysis` - Analyze file symbols and project structure
- `serena_symbol_search` - Search for functions, classes, variables across codebase
- `serena_reference_search` - Find all references to a symbol

**File Operations:**
- `serena_file_operations` - Read, create, modify files with semantic awareness
- `serena_pattern_search` - Search patterns across project files with filtering

**Project Management:**
- `serena_project_management` - Activate projects, perform onboarding
- `serena_memory_management` - Store and retrieve project-specific knowledge

**Development Operations:**
- `serena_shell_execution` - Execute commands with project context

### Usage Examples

**Activate a Project:**
```
Activate project /path/to/my/project
```

**Analyze Code Structure:**
```
Show me the symbols in src/main.py
Analyze the project structure
```

**Search for Code:**
```
Find function "calculateTotal"
Search for class "UserManager" 
Find all references to variable at src/utils.py:45:12
```

**File Operations:**
```
Read file src/config.py
Create file utils/helper.py with content "def helper(): pass"
Replace pattern "oldFunction" with "newFunction" in src/main.py
```

**Shell Commands:**
```
Run npm test
Execute python setup.py build
Run git status
```

**Memory Management:**
```
Write memory "project_info" with "This project uses FastAPI with PostgreSQL"
Read memory "project_info"
List all memories
```

### Context Modes

Serena supports different context modes optimized for various use cases:

- `ide-assistant` (default) - Optimized for IDE integration and coding assistance
- `desktop-app` - For desktop application usage
- `agent` - For autonomous agent scenarios

### Performance Tips

1. **Enable Project Indexing**: Run onboarding when first activating a project
2. **Use Semantic Operations**: Leverage symbol-based operations over text search when possible
3. **Project Memory**: Store important project context in memories for better results
4. **Appropriate Context**: Choose the right context mode for your use case

### Troubleshooting

**Serena Server Not Starting:**
- Ensure uvx or uv is installed and available
- Check network access to GitHub for uvx installation
- Verify project path permissions

**Project Operations Failing:**
- Ensure project is activated first
- Run project onboarding for better semantic analysis
- Check that language servers are available for your file types

**Tool Discovery Issues:**
- Restart Codexa if new Serena tools aren't appearing
- Check MCP service status in debug output
- Verify Serena server is connected and healthy

## OpenRouter Tool Calling

Codexa supports OpenRouter's tool calling functionality for enhanced AI interactions:

### Tool-Capable Models
- `google/gemini-2.0-flash-001` (default for OpenRouter)
- `anthropic/claude-3.5-sonnet`  
- `openai/gpt-4o`
- `openai/gpt-4o-mini`

### Configuration
```bash
# Use a tool-capable model
export CODEXA_OPENROUTER_MODEL="google/gemini-2.0-flash-001"

# Or via config file (~/.codexarc)
models:
  openrouter: "google/gemini-2.0-flash-001"
```

### Tool Calling Implementation
The OpenRouter provider implements the 3-step tool calling process:
1. **Step 1**: Send request with `tools` array
2. **Step 2**: Execute tools locally via Codexa's tool system  
3. **Step 3**: Send results back to continue conversation

### Usage
Tool calling is automatic when using tool-capable models. The provider will:
- Detect when tools should be called
- Coordinate with Codexa's tool system for execution
- Handle multi-turn tool conversations
- Support parallel tool calls when enabled

Find supported models at: https://openrouter.ai/models?supported_parameters=tools

## Extension Points

- **Custom Tools**: Add new tools in `tools/` directory structure
- **New Providers**: Extend provider factory for additional AI services  
- **MCP Servers**: Add new server integrations in `mcp/` directory
- **Commands**: Register new slash commands via command registry
- **Themes**: Add new ASCII art themes in display system