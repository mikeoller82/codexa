# Codexa Default Plugins

This directory contains the default plugins that come pre-configured with Codexa, providing enhanced functionality for common development tasks.

## Available Default Plugins

### 1. Code Quality Plugin (`code_quality`)
**Description**: Comprehensive code quality analysis, linting, and formatting  
**Version**: 1.0.0  

**Commands**:
- `/lint` - Run linting analysis on code
- `/format` - Format code using configured formatters
- `/complexity` - Analyze code complexity
- `/quality-check` - Run comprehensive quality checks
- `/fix-quality` - Automatically fix quality issues

**Capabilities**:
- Code analysis and linting (pylint, mypy, flake8)
- Code formatting (black, isort)
- Complexity analysis (radon)
- Type checking
- Automatic quality fixes

**Usage Examples**:
```bash
/lint target=src/
/format target=. dry_run=true
/complexity threshold=10
/quality-check
/fix-quality target=src/
```

### 2. Git Integration Plugin (`git_integration`)
**Description**: Enhanced Git operations with smart analysis and automation  
**Version**: 1.0.0

**Commands**:
- `/git-status` - Enhanced git status with detailed information
- `/commit-smart` - Smart commit with auto-generated messages
- `/branch-manage` - Branch management operations
- `/git-analyze` - Repository analysis and insights
- `/conflict-assist` - Merge conflict assistance
- `/repo-insights` - Repository statistics and insights

**Capabilities**:
- Smart commit message generation
- Branch management and cleanup
- Conflict resolution assistance
- Repository analysis
- Git workflow optimization

**Usage Examples**:
```bash
/git-status
/commit-smart message="feat: add new feature" auto_stage=true
/branch-manage action=list
/branch-manage action=create branch=feature/new-feature
/git-analyze type=summary
/repo-insights
```

### 3. Project Structure Plugin (`project_structure`)
**Description**: Project scaffolding, templates, and structure analysis  
**Version**: 1.0.0

**Commands**:
- `/scaffold` - Create new project from template
- `/template` - Manage project templates
- `/structure-analyze` - Analyze project structure
- `/project-init` - Initialize existing directory as project
- `/best-practices` - Get best practices recommendations

**Capabilities**:
- Project scaffolding with built-in templates
- Structure analysis and recommendations
- Template management
- Best practices guidance
- Multi-language project support

**Usage Examples**:
```bash
/template action=list
/scaffold template=python_basic name=my_project
/structure-analyze path=.
/project-init type=python_basic
/best-practices
```

## Plugin System Features

### Security Sandboxing
All plugins run in a secure sandbox environment with:
- **Permission-based access control**
- **Resource limits** (CPU, memory, execution time)
- **File system restrictions**
- **Network access controls**

### Auto-Discovery and Loading
Plugins are automatically:
- **Discovered** from the `/plugins/available/` directory
- **Loaded** on Codexa startup
- **Enabled** based on permissions and requirements
- **Validated** for security and compatibility

### Integration with Codexa Core
Plugins seamlessly integrate with:
- **Command system** - Commands registered automatically
- **MCP servers** - Can utilize MCP capabilities
- **Configuration system** - Respect user preferences
- **Error handling** - Consistent error reporting
- **Logging** - Centralized logging system

## Plugin Development

### Directory Structure
```
plugins/available/plugin_name/
├── plugin.json          # Plugin metadata
├── main.py             # Main plugin class
├── commands/           # Plugin-specific commands
├── handlers/           # Event handlers
├── config/            # Default configurations
├── templates/         # Templates and scaffolds
└── tests/             # Plugin tests
```

### Plugin Manifest (plugin.json)
```json
{
    "name": "plugin_name",
    "version": "1.0.0",
    "description": "Plugin description",
    "author": "Author Name",
    "homepage": "https://example.com",
    "license": "MIT",
    "dependencies": ["package1", "package2"],
    "capabilities": ["capability1", "capability2"],
    "permissions": ["file_read", "file_write"],
    "mcp_servers": [],
    "commands": ["command1", "command2"],
    "min_codexa_version": "1.0.0"
}
```

### Available Permissions
- `file_read` - Read files from the filesystem
- `file_write` - Write files to the filesystem
- `process_execute` - Execute system commands
- `network_access` - Access network resources
- `environment_read` - Read environment variables
- `environment_write` - Modify environment variables
- `system_info` - Access system information
- `mcp_server_access` - Access MCP servers

## Configuration

### Plugin Settings
Plugins can be configured through:
1. **Global config** - System-wide plugin settings
2. **Project config** - Project-specific overrides
3. **Runtime parameters** - Command-line arguments

### Disabling Plugins
To disable a plugin:
1. **Temporary**: Use `/config set feature.disable_plugin_name true`
2. **Permanent**: Move plugin out of `/available/` directory
3. **Selective**: Modify plugin permissions

## Troubleshooting

### Common Issues

**Plugin Not Loading**:
- Check plugin.json syntax
- Verify all dependencies are installed
- Check permissions match available Permission enum values
- Ensure main.py has valid Plugin class

**Command Not Working**:
- Verify plugin is enabled: `/status`
- Check plugin logs for errors
- Ensure required tools are installed (for code_quality)
- Verify permissions are sufficient

**Performance Issues**:
- Check sandbox resource limits
- Monitor plugin execution time
- Consider disabling unnecessary plugins
- Review plugin configuration

### Debug Mode
Enable plugin debugging with:
```bash
export CODEXA_PLUGIN_DEBUG=true
```

This provides detailed logging for:
- Plugin discovery and loading
- Command execution
- Error details
- Performance metrics

## Contributing

To contribute new plugins or improve existing ones:

1. **Follow the plugin structure** outlined above
2. **Implement proper error handling** and logging
3. **Add comprehensive tests** for plugin functionality
4. **Document all commands and capabilities**
5. **Ensure security best practices** are followed
6. **Test with different environments** and configurations

## License

All default plugins are licensed under MIT License, same as Codexa core.