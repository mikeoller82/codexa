# 🤖 Codexa

<div align="center">

**AI-Powered CLI Coding Assistant & Development Partner**

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/codexa.svg)](https://pypi.org/project/codexa/)
[![Downloads](https://img.shields.io/pypi/dm/codexa.svg)](https://pypi.org/project/codexa/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

*Transform your development workflow with an intelligent AI assistant that understands your code, suggests improvements, and helps you build better software faster.*

[🚀 Quick Start](#-quick-start) • [✨ Features](#-features) • [📖 Documentation](#-documentation) • [🤝 Contributing](#-contributing)

</div>

---

## 🎯 What is Codexa?

Codexa is a next-generation CLI coding assistant that serves as your proactive development partner. Unlike traditional tools, Codexa understands context, learns from your codebase, and provides intelligent suggestions to accelerate your development workflow.

### 🌟 Key Highlights

- **🧠 Context-Aware AI**: Understands your entire codebase and development patterns
- **⚡ Lightning Fast**: Optimized performance with <1s startup time
- **🎨 Beautiful Interface**: Animated ASCII art with 5 stunning themes
- **🔌 Extensible**: MCP server integration for specialized capabilities
- **🛡️ Secure**: Local-first processing with optional cloud AI providers
- **📱 Cross-Platform**: Works seamlessly on Linux, macOS, and Windows

---

## ✨ Features

### 🤖 **Intelligent Code Assistance**
- **Smart Code Analysis**: Deep understanding of your codebase architecture
- **Contextual Suggestions**: Recommendations based on your coding patterns
- **Multi-Language Support**: Python, JavaScript, TypeScript, Go, and more
- **Real-time Error Detection**: Catch issues before they become problems

### 🎛️ **Advanced Provider System**
- **Runtime Provider Switching**: Switch between OpenAI, Anthropic, and OpenRouter instantly
- **Model Selection**: Choose the best model for each task
- **Intelligent Routing**: Automatic provider selection based on task complexity
- **Fallback Support**: Graceful degradation when providers are unavailable

### 🔧 **MCP Server Integration**
- **Context7**: Access up-to-date documentation and code examples
- **Sequential**: Complex reasoning and multi-step analysis
- **Magic**: Modern UI component generation
- **Playwright**: Cross-browser testing and automation

### 🎨 **Enhanced User Experience**
- **Animated ASCII Art**: 5 beautiful themes (default, minimal, cyberpunk, retro, matrix)
- **Interactive Startup**: Guided onboarding for new users
- **Smart Command System**: Powerful slash commands for common workflows
- **Contextual Help**: Get assistance exactly when you need it

### 🚀 **Slash Commands**
```bash
/help          # Get comprehensive help and guidance
/status        # View system status and health metrics
/provider      # Switch AI providers and models
/model         # Select specific models for tasks
/mcp           # Manage MCP server connections
/commands      # List available slash commands
/config        # View and modify configuration
```

---

## 🚀 Quick Start

### Installation

#### Option 1: pipx (Recommended)
```bash
pipx install codexa
```

#### Option 2: pip
```bash
pip install codexa
```

#### Option 3: Development Install
```bash
git clone https://github.com/mikeoller82/codexa.git
cd codexa
pip install -e .
```

### Initial Setup

1. **Configure API Keys** (choose one or more):
```bash
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
export OPENROUTER_API_KEY="your-openrouter-key"
```

2. **Initialize Codexa**:
```bash
codexa setup
```

3. **Start Your First Session**:
```bash
codexa
```

That's it! 🎉 Codexa will guide you through an interactive setup and help you get started.

---

## 📖 Usage Examples

### Basic Code Analysis
```bash
# Analyze your current project
codexa analyze

# Get help with a specific file
codexa explain app.py

# Generate documentation
codexa document --format markdown
```

### Interactive Development
```bash
# Start interactive session
codexa

# Switch providers on-the-fly
/provider anthropic

# Change themes
/config theme cyberpunk

# Get project status
/status
```

### Advanced Workflows
```bash
# Complex code refactoring
codexa refactor --target ./src --style clean

# Security audit
codexa audit --security --comprehensive

# Performance optimization
codexa optimize --focus performance
```

---

## ⚙️ Configuration

### User Configuration (`~/.codexarc`)
```yaml
# AI Provider Settings
default_provider: "openai"
default_model: "gpt-4"

# UI Preferences
theme: "default"
animations: true
startup_tips: true

# MCP Servers
mcp_servers:
  context7: true
  sequential: true
  magic: false
  playwright: false

# Performance
cache_enabled: true
parallel_processing: true
```

### Project Configuration (`CODEXA.md`)
Auto-generated project-specific guidelines that Codexa creates to understand your project better.

---

## 🏗️ Architecture

Codexa is built with a modular, extensible architecture:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CLI Interface │    │  Enhanced UX    │    │  Command System │
│                 │    │                 │    │                 │
│ • Typer-based   │    │ • ASCII Art     │    │ • Slash Commands│
│ • Auto-complete │    │ • Animations    │    │ • Extensible    │
│ • Error Handling│    │ • Themes        │    │ • Built-in Help │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                ┌─────────────────▼─────────────────┐
                │          Agent System             │
                │                                   │
                │ • Enhanced Agent (Phase 3)        │
                │ • Basic Agent (Fallback)          │
                │ • Dual-mode Operation            │
                └─────────────────┬─────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌─────────▼─────────┐    ┌───────▼───────┐    ┌─────────▼─────────┐
│  Provider System  │    │ MCP Integration│    │  Display System   │
│                   │    │                │    │                   │
│ • OpenAI          │    │ • Context7     │    │ • ASCII Renderer  │
│ • Anthropic       │    │ • Sequential   │    │ • Theme Manager   │
│ • OpenRouter      │    │ • Magic        │    │ • Animation Engine│
│ • Runtime Switch  │    │ • Playwright   │    │ • Progress Bars   │
└───────────────────┘    └────────────────┘    └───────────────────┘
```

---

## 🤝 Contributing

We welcome contributions from the community! Here's how you can help:

### 🐛 Bug Reports
Found a bug? [Open an issue](https://github.com/yourusername/codexa/issues) with:
- Detailed description
- Steps to reproduce
- Expected vs actual behavior
- Environment details

### 💡 Feature Requests
Have an idea? [Create a feature request](https://github.com/yourusername/codexa/issues) with:
- Use case description
- Proposed solution
- Alternative approaches
- Examples

### 🔧 Development Setup
```bash
# Clone the repository
git clone https://github.com/yourusername/codexa.git
cd codexa

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Format code
black codexa/
```

### 📝 Pull Request Guidelines
1. **Fork the repository** and create a feature branch
2. **Write tests** for new functionality
3. **Update documentation** as needed
4. **Follow code style** (Black formatting, type hints)
5. **Submit PR** with clear description

---

## 📊 Project Stats

<div align="center">

![GitHub stars](https://img.shields.io/github/stars/yourusername/codexa?style=social)
![GitHub forks](https://img.shields.io/github/forks/yourusername/codexa?style=social)
![GitHub issues](https://img.shields.io/github/issues/yourusername/codexa)
![GitHub pull requests](https://img.shields.io/github/issues-pr/yourusername/codexa)

</div>

---

## 🛠️ Tech Stack

- **Core**: Python 3.8+, asyncio
- **CLI**: Typer, Rich
- **AI Integration**: OpenAI, Anthropic, OpenRouter APIs
- **Testing**: pytest, pytest-asyncio
- **Code Quality**: Black, mypy, flake8
- **Documentation**: MkDocs (coming soon)

---

## 🚧 Roadmap

### Phase 3 ✅ (Current)
- [x] Enhanced UX with animations and themes
- [x] MCP server integration
- [x] Advanced command system
- [x] Error handling and user guidance

### Phase 4 🚀 (Next)
- [ ] Plugin ecosystem
- [ ] Team collaboration features
- [ ] Advanced code generation
- [ ] Integration with popular IDEs

### Phase 5 🌟 (Future)
- [ ] Cloud synchronization
- [ ] Advanced analytics
- [ ] Custom model training
- [ ] Enterprise features

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Claude Code Team** for inspiration and guidance
- **MCP Community** for the Model Context Protocol
- **Open Source Community** for amazing tools and libraries
- **Contributors** who make this project better every day

---

## 📞 Support

- 📖 **Documentation**: [Full documentation](https://mikeoller82.github.io/codexa) (coming soon)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/mikeoller82/codexa/discussions)
- 🐛 **Issues**: [Report bugs](https://github.com/mikeoller82/codexa/issues)
- 📧 **Email**: support@codexa.dev (coming soon)

---

<div align="center">

**Made with ❤️ by the Codexa Team**

*Star ⭐ this repo if you find it useful!*

</div>
