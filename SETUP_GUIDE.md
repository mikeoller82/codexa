# Codexa Setup & Usage Guide

Complete guide to setting up and using Codexa enhanced AI coding assistant.

## 📦 Installation

### Method 1: Development Installation (Recommended)

```bash
# Clone or navigate to the Codexa directory
cd /path/to/codexa

# Install in development mode
pip install -e .

# Verify installation
codexa --version
```

### Method 2: Global Installation

```bash
# Install globally with pipx (requires pipx)
pipx install /path/to/codexa

# Or with pip (not recommended for development)
pip install /path/to/codexa
```

## 🔑 API Key Configuration

### Step 1: Choose Your AI Provider

Codexa supports multiple AI providers. Choose one or configure multiple:

#### OpenAI (Recommended)
```bash
export OPENAI_API_KEY="sk-your-key-here"
```

#### Anthropic (Claude)
```bash
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
```

#### OpenRouter (Multiple Models)
```bash
export OPENROUTER_API_KEY="sk-or-your-key-here"
```

### Step 2: Make Keys Persistent

Add to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.):
```bash
# Add this line to your ~/.bashrc or ~/.zshrc
export OPENAI_API_KEY="your-key-here"

# Reload your shell
source ~/.bashrc
```

### Step 3: Verify Configuration

```bash
# Check if your key is set
echo $OPENAI_API_KEY

# Test Codexa startup
codexa --version
```

## 🚀 First Run

### Initial Startup

```bash
# Navigate to any project directory
cd /path/to/your/project

# Start Codexa
codexa
```

### What Happens on First Run

1. **Animated Logo**: Beautiful ASCII art with your chosen theme
2. **System Check**: Verification of AI providers and MCP servers
3. **Interactive Setup**: Choose your preferences
4. **Project Initialization**: Create `CODEXA.md` and `.codexa/` directory
5. **Ready State**: Enter the interactive terminal

### First Run Options

When you see the interactive setup:

1. **Theme Selection**: Choose from 5 visual themes
   - `default` - Clean cyan for professional use
   - `minimal` - Simple and elegant
   - `cyberpunk` - Bright magenta futuristic
   - `retro` - Nostalgic yellow/green
   - `matrix` - Green-on-black matrix style

2. **Provider Selection**: Choose your primary AI provider
   - OpenAI (GPT models)
   - Anthropic (Claude models)  
   - OpenRouter (Various models)

3. **MCP Server Setup**: Enable enhanced capabilities
   - Context7 (Documentation)
   - Sequential (Complex reasoning)
   - Magic (UI generation)

## 💻 Using Codexa

### Basic Interaction

Once Codexa is running, you'll see the prompt:
```
codexa>
```

You can interact in two ways:

#### 1. Natural Language
```
codexa> Create a React component for user authentication
codexa> Explain this function and suggest improvements
codexa> Set up a FastAPI project with PostgreSQL
```

#### 2. Slash Commands
```
codexa> /help
codexa> /status
codexa> /provider switch anthropic
```

### Essential Slash Commands

#### Getting Help
```bash
/help                    # Show contextual help
/help provider          # Help for specific command
/commands               # List all commands
```

#### System Status
```bash
/status                 # Overall system status
/status --detailed      # Detailed system information
```

#### Provider Management
```bash
/provider list          # Show available providers
/provider switch openai # Switch to OpenAI
/provider status        # Current provider info
```

#### Model Management
```bash
/model list            # Show available models
/model switch gpt-4o   # Switch to specific model
/model info claude-3-5-sonnet  # Model information
```

#### MCP Servers
```bash
/mcp status            # MCP service status
/mcp list              # Available servers
/mcp enable context7   # Enable documentation server
/mcp query sequential "analyze this code"  # Direct query
```

#### Configuration
```bash
/config show           # Current configuration
/config set theme cyberpunk  # Change theme
/config reset          # Reset to defaults
```

## 🎨 Customization

### Theme Configuration

Change themes during your session:
```bash
codexa> /config set theme cyberpunk
codexa> /config set enable_animations true
```

Or edit the config file directly:
```bash
# Edit ~/.codexarc
nano ~/.codexarc
```

Example configuration:
```yaml
ai_provider: "openai"
default_model: "gpt-4o"
theme: "cyberpunk"
enable_animations: true
mcp_servers:
  context7:
    enabled: true
    priority: 1
  sequential:
    enabled: true
    priority: 2
  magic:
    enabled: false
    priority: 3
```

### Project-Specific Settings

Each project gets a `CODEXA.md` file for project-specific guidelines:

```markdown
# Codexa Guidelines for MyProject

## Coding Standards
- Use TypeScript for all new code
- Follow Prettier formatting
- Write comprehensive tests

## Architecture
- Follow clean architecture principles
- Use dependency injection
- Implement proper error handling

## AI Provider Preferences
- Use Claude for code reviews
- Use GPT-4 for complex problem solving
- Use OpenRouter for cost optimization
```

## 🔧 Advanced Configuration

### Multiple API Keys

You can configure multiple providers and switch between them:

```bash
# In your shell profile
export OPENAI_API_KEY="sk-openai-key"
export ANTHROPIC_API_KEY="sk-ant-key"
export OPENROUTER_API_KEY="sk-or-key"
```

Then switch providers during your session:
```bash
codexa> /provider switch openai      # Use GPT models
codexa> /provider switch anthropic   # Use Claude models
codexa> /provider switch openrouter  # Use various models
```

### MCP Server Setup

Enable enhanced capabilities with MCP servers:

#### Context7 (Documentation Server)
```bash
codexa> /mcp enable context7
codexa> /mcp query context7 "show React hooks documentation"
```

#### Sequential (Reasoning Server)
```bash
codexa> /mcp enable sequential
codexa> /mcp query sequential "analyze this complex algorithm"
```

#### Magic (UI Generation Server)
```bash
codexa> /mcp enable magic
codexa> /mcp query magic "create a responsive navbar component"
```

### Performance Optimization

For optimal performance:

```bash
# Disable animations if needed
codexa> /config set enable_animations false

# Use faster models for simple tasks
codexa> /model switch gpt-3.5-turbo

# Enable only necessary MCP servers
codexa> /mcp disable magic  # If you don't need UI generation
```

## 🎯 Common Workflows

### Web Development Workflow

1. **Project Setup**
```bash
cd /path/to/project
codexa
```

2. **Configure for Web Development**
```bash
codexa> /mcp enable magic         # For UI components
codexa> /mcp enable context7      # For documentation
codexa> /provider switch openai   # GPT-4 for complex tasks
```

3. **Development Tasks**
```bash
codexa> Create a React component with TypeScript for user profile
codexa> Add error handling and validation to my API endpoints
codexa> Generate unit tests for the authentication service
```

### Backend Development Workflow

1. **Setup for Backend Work**
```bash
codexa> /mcp enable sequential    # For complex logic
codexa> /provider switch anthropic # Claude for code analysis
```

2. **Common Tasks**
```bash
codexa> Design a REST API for user management with FastAPI
codexa> Create database migrations for the new schema
codexa> Add logging and monitoring to the payment service
```

### Code Review Workflow

1. **Setup for Code Review**
```bash
codexa> /provider switch anthropic  # Claude excels at code review
codexa> /mcp enable sequential      # For thorough analysis
```

2. **Review Process**
```bash
codexa> Review this function for security vulnerabilities
codexa> Suggest improvements for performance and readability
codexa> Check if this code follows best practices
```

## 🐛 Troubleshooting

### Common Issues and Solutions

#### 1. Codexa Won't Start

**Problem**: `command not found: codexa`

**Solutions**:
```bash
# Check if installed correctly
pip show codexa

# Reinstall if needed
pip uninstall codexa
pip install -e /path/to/codexa

# Check Python path
which python
python -c "import codexa; print('OK')"
```

#### 2. API Key Issues

**Problem**: "No API key found" or authentication errors

**Solutions**:
```bash
# Verify key is set
echo $OPENAI_API_KEY

# Set key temporarily
export OPENAI_API_KEY="your-key"

# Try different provider
codexa> /provider switch anthropic
```

#### 3. Slow Performance

**Problem**: Codexa is slow to respond

**Solutions**:
```bash
# Check system status
codexa> /status

# Disable animations
codexa> /config set enable_animations false

# Use faster model
codexa> /model switch gpt-3.5-turbo

# Disable unused MCP servers
codexa> /mcp disable magic
```

#### 4. MCP Server Issues

**Problem**: MCP servers not working

**Solutions**:
```bash
# Check MCP status
codexa> /mcp status

# Restart specific server
codexa> /mcp disable context7
codexa> /mcp enable context7

# Check logs (if available)
ls ~/.codexa/logs/
```

#### 5. Theme/Display Issues

**Problem**: ASCII art not displaying correctly

**Solutions**:
```bash
# Switch to minimal theme
codexa> /config set theme minimal

# Disable animations
codexa> /config set enable_animations false

# Check terminal compatibility
echo $TERM
```

### Getting Additional Help

1. **In-App Help**
```bash
codexa> /help
codexa> /help provider
codexa> /status
```

2. **Configuration Check**
```bash
codexa> /config show
```

3. **Log Files** (if available)
```bash
ls ~/.codexa/logs/
tail ~/.codexa/logs/codexa.log
```

## 💡 Tips & Best Practices

### Productivity Tips

1. **Use Slash Commands for Quick Tasks**
   - `/status` to check system health
   - `/provider switch` to optimize for different tasks
   - `/help` when you forget command syntax

2. **Leverage Multiple Providers**
   - OpenAI GPT-4 for complex reasoning
   - Anthropic Claude for code analysis
   - OpenRouter for cost optimization

3. **Enable Relevant MCP Servers**
   - Context7 for documentation-heavy work
   - Sequential for complex problem solving
   - Magic for UI/frontend development

4. **Project-Specific Configuration**
   - Customize `CODEXA.md` for each project
   - Set project-specific provider preferences
   - Document coding standards and practices

### Security Best Practices

1. **API Key Security**
   - Never commit API keys to version control
   - Use environment variables
   - Rotate keys regularly

2. **Project Isolation**
   - Use separate keys for different projects
   - Review generated code before committing
   - Be cautious with sensitive code/data

### Performance Best Practices

1. **Model Selection**
   - Use appropriate models for tasks
   - Faster models for simple tasks
   - More capable models for complex problems

2. **MCP Server Management**
   - Enable only needed servers
   - Monitor resource usage
   - Disable servers when not needed

3. **Configuration Optimization**
   - Disable animations on slower systems
   - Use minimal themes for better performance
   - Regular configuration cleanup

---

## 🎉 You're Ready!

With this setup guide, you should be able to:

- ✅ Install and configure Codexa
- ✅ Set up API keys for your preferred providers
- ✅ Navigate the enhanced terminal interface
- ✅ Use slash commands effectively
- ✅ Customize themes and settings
- ✅ Troubleshoot common issues
- ✅ Follow best practices for productivity

**Happy coding with your AI-enhanced development environment!** 🚀