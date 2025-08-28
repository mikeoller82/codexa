"""
Code Generation Tool - Handles code generation and scaffolding for Codexa
"""

import os
import re
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import json

from ..base.tool_interface import Tool, ToolResult, ToolContext, ToolStatus


class CodeGenerationTool(Tool):
    """Tool for generating code scaffolds, templates, and boilerplate"""
    
    def __init__(self):
        super().__init__()
        self.templates = {
            'python': self._python_templates,
            'javascript': self._javascript_templates,
            'typescript': self._typescript_templates,
            'java': self._java_templates,
            'cpp': self._cpp_templates,
            'rust': self._rust_templates,
            'go': self._go_templates,
            'html': self._html_templates,
            'css': self._css_templates,
            'json': self._json_templates,
            'yaml': self._yaml_templates,
            'markdown': self._markdown_templates
        }
        
        self.generators = {
            'class': self._generate_class,
            'function': self._generate_function,
            'module': self._generate_module,
            'test': self._generate_test,
            'config': self._generate_config,
            'api': self._generate_api,
            'component': self._generate_component,
            'service': self._generate_service,
            'model': self._generate_model,
            'interface': self._generate_interface,
            'enum': self._generate_enum,
            'struct': self._generate_struct
        }
    
    @property
    def name(self) -> str:
        return "code_generation"
    
    @property
    def description(self) -> str:
        return "Generates code scaffolds, templates, and boilerplate for various programming languages and frameworks"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def capabilities(self) -> List[str]:
        return [
            "template_generation",
            "class_generation",
            "function_generation", 
            "module_scaffolding",
            "test_generation",
            "api_scaffolding",
            "component_generation",
            "config_generation",
            "boilerplate_creation",
            "code_templates",
            "multi_language_support",
            "custom_templates"
        ]
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the code generation request"""
        request_lower = request.lower()
        
        # High confidence for explicit generation requests
        if any(word in request_lower for word in [
            'generate', 'create', 'scaffold', 'boilerplate',
            'template', 'code generation', 'generate code'
        ]):
            return 0.9
            
        # Medium confidence for creation requests
        if any(word in request_lower for word in [
            'create class', 'create function', 'new class',
            'new function', 'make class', 'make function'
        ]):
            return 0.7
            
        # Lower confidence for general creation requests
        if any(word in request_lower for word in [
            'new', 'make', 'build', 'setup'
        ]):
            return 0.4
            
        return 0.0
    
    def execute(self, request: str, context: ToolContext) -> ToolResult:
        """Execute code generation based on request"""
        try:
            generation_params = self._parse_generation_request(request)
            
            # Route to appropriate generator
            gen_type = generation_params.get('type', 'class')
            
            if gen_type not in self.generators:
                return ToolResult(
                    success=False,
                    data={'error': f'Unknown generation type: {gen_type}'},
                    message=f"Generation type '{gen_type}' not supported",
                    status=ToolStatus.ERROR
                )
            
            result = self.generators[gen_type](generation_params, context)
            
            return ToolResult(
                success=True,
                data=result,
                message=f"Code generation ({gen_type}) completed",
                status=ToolStatus.SUCCESS
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                data={'error': str(e)},
                message=f"Code generation failed: {str(e)}",
                status=ToolStatus.ERROR
            )
    
    def _parse_generation_request(self, request: str) -> Dict[str, Any]:
        """Parse generation request to extract parameters"""
        request_lower = request.lower()
        params = {
            'type': 'class',  # default
            'language': 'python',  # default
            'name': '',
            'output_file': '',
            'options': {}
        }
        
        # Determine generation type
        type_keywords = {
            'class': ['class', 'classes'],
            'function': ['function', 'func', 'method'],
            'module': ['module', 'package'],
            'test': ['test', 'tests', 'unit test'],
            'config': ['config', 'configuration'],
            'api': ['api', 'endpoint', 'rest'],
            'component': ['component', 'ui component'],
            'service': ['service', 'microservice'],
            'model': ['model', 'data model'],
            'interface': ['interface', 'protocol'],
            'enum': ['enum', 'enumeration'],
            'struct': ['struct', 'structure']
        }
        
        for gen_type, keywords in type_keywords.items():
            if any(keyword in request_lower for keyword in keywords):
                params['type'] = gen_type
                break
        
        # Determine language
        language_keywords = {
            'python': ['python', 'py', '.py'],
            'javascript': ['javascript', 'js', '.js', 'node'],
            'typescript': ['typescript', 'ts', '.ts'],
            'java': ['java', '.java'],
            'cpp': ['cpp', 'c++', '.cpp', '.cc'],
            'rust': ['rust', '.rs'],
            'go': ['go', 'golang', '.go'],
            'html': ['html', '.html'],
            'css': ['css', '.css'],
            'json': ['json', '.json'],
            'yaml': ['yaml', 'yml', '.yaml', '.yml'],
            'markdown': ['markdown', 'md', '.md']
        }
        
        for lang, keywords in language_keywords.items():
            if any(keyword in request_lower for keyword in keywords):
                params['language'] = lang
                break
        
        # Extract name
        name_patterns = [
            r'(?:class|function|module|component|service|model|interface|enum|struct)\s+["\']?([a-zA-Z_][a-zA-Z0-9_]*)["\']?',
            r'(?:create|generate|make)\s+(?:a\s+)?(?:new\s+)?(?:class|function|module)\s+["\']?([a-zA-Z_][a-zA-Z0-9_]*)["\']?',
            r'named?\s+["\']?([a-zA-Z_][a-zA-Z0-9_]*)["\']?'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, request, re.IGNORECASE)
            if match:
                params['name'] = match.group(1)
                break
        
        # Extract output file if specified
        file_match = re.search(r'(?:in|to)\s+["\']?([^"\']+\.[a-zA-Z]+)["\']?', request)
        if file_match:
            params['output_file'] = file_match.group(1)
        
        # Extract additional options
        if 'abstract' in request_lower:
            params['options']['abstract'] = True
        if 'static' in request_lower:
            params['options']['static'] = True
        if 'async' in request_lower:
            params['options']['async'] = True
        if 'public' in request_lower:
            params['options']['visibility'] = 'public'
        elif 'private' in request_lower:
            params['options']['visibility'] = 'private'
        elif 'protected' in request_lower:
            params['options']['visibility'] = 'protected'
        
        return params
    
    def _generate_class(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Generate class code"""
        language = params.get('language', 'python')
        name = params.get('name', 'MyClass')
        options = params.get('options', {})
        
        if language not in self.templates:
            return {'error': f'Language {language} not supported'}
        
        template_func = self.templates[language]
        code = template_func('class', name, options)
        
        result = {
            'generation_type': 'class',
            'language': language,
            'name': name,
            'code': code,
            'options': options
        }
        
        # Write to file if specified
        output_file = params.get('output_file')
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    f.write(code)
                result['output_file'] = output_file
                result['file_created'] = True
            except Exception as e:
                result['file_error'] = str(e)
        
        return result
    
    def _generate_function(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Generate function code"""
        language = params.get('language', 'python')
        name = params.get('name', 'my_function')
        options = params.get('options', {})
        
        if language not in self.templates:
            return {'error': f'Language {language} not supported'}
        
        template_func = self.templates[language]
        code = template_func('function', name, options)
        
        result = {
            'generation_type': 'function',
            'language': language,
            'name': name,
            'code': code,
            'options': options
        }
        
        # Write to file if specified
        output_file = params.get('output_file')
        if output_file:
            try:
                with open(output_file, 'a') as f:  # Append mode for functions
                    f.write('\n\n' + code)
                result['output_file'] = output_file
                result['file_appended'] = True
            except Exception as e:
                result['file_error'] = str(e)
        
        return result
    
    def _generate_module(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Generate module scaffold"""
        language = params.get('language', 'python')
        name = params.get('name', 'my_module')
        options = params.get('options', {})
        
        if language not in self.templates:
            return {'error': f'Language {language} not supported'}
        
        template_func = self.templates[language]
        code = template_func('module', name, options)
        
        result = {
            'generation_type': 'module',
            'language': language,
            'name': name,
            'code': code,
            'options': options
        }
        
        # Create module file
        if language == 'python':
            filename = f'{name}.py'
        elif language == 'javascript':
            filename = f'{name}.js'
        elif language == 'typescript':
            filename = f'{name}.ts'
        else:
            filename = f'{name}.{language}'
        
        output_file = params.get('output_file', filename)
        try:
            with open(output_file, 'w') as f:
                f.write(code)
            result['output_file'] = output_file
            result['file_created'] = True
        except Exception as e:
            result['file_error'] = str(e)
        
        return result
    
    def _generate_test(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Generate test code"""
        language = params.get('language', 'python')
        name = params.get('name', 'test_example')
        options = params.get('options', {})
        
        if language not in self.templates:
            return {'error': f'Language {language} not supported'}
        
        template_func = self.templates[language]
        code = template_func('test', name, options)
        
        result = {
            'generation_type': 'test',
            'language': language,
            'name': name,
            'code': code,
            'options': options
        }
        
        # Create test file
        if language == 'python':
            filename = f'test_{name}.py'
        elif language in ['javascript', 'typescript']:
            filename = f'{name}.test.{language[0:2]}'
        else:
            filename = f'test_{name}.{language}'
        
        output_file = params.get('output_file', filename)
        try:
            with open(output_file, 'w') as f:
                f.write(code)
            result['output_file'] = output_file
            result['file_created'] = True
        except Exception as e:
            result['file_error'] = str(e)
        
        return result
    
    def _generate_config(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Generate configuration file"""
        language = params.get('language', 'json')
        name = params.get('name', 'config')
        options = params.get('options', {})
        
        if language not in self.templates:
            return {'error': f'Config type {language} not supported'}
        
        template_func = self.templates[language]
        code = template_func('config', name, options)
        
        return {
            'generation_type': 'config',
            'format': language,
            'name': name,
            'code': code,
            'options': options
        }
    
    # Generic generators for other types
    def _generate_api(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        return self._generate_generic('api', params, context)
    
    def _generate_component(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        return self._generate_generic('component', params, context)
    
    def _generate_service(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        return self._generate_generic('service', params, context)
    
    def _generate_model(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        return self._generate_generic('model', params, context)
    
    def _generate_interface(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        return self._generate_generic('interface', params, context)
    
    def _generate_enum(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        return self._generate_generic('enum', params, context)
    
    def _generate_struct(self, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        return self._generate_generic('struct', params, context)
    
    def _generate_generic(self, gen_type: str, params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
        """Generic generation handler"""
        language = params.get('language', 'python')
        name = params.get('name', f'my_{gen_type}')
        options = params.get('options', {})
        
        if language not in self.templates:
            return {'error': f'Language {language} not supported'}
        
        template_func = self.templates[language]
        code = template_func(gen_type, name, options)
        
        return {
            'generation_type': gen_type,
            'language': language,
            'name': name,
            'code': code,
            'options': options
        }
    
    # Template functions for different languages
    def _python_templates(self, template_type: str, name: str, options: Dict[str, Any]) -> str:
        """Python code templates"""
        if template_type == 'class':
            abstract = 'from abc import ABC, abstractmethod\n\n' if options.get('abstract') else ''
            inheritance = '(ABC)' if options.get('abstract') else ''
            return f'''{abstract}class {name}{inheritance}:
    """
    {name} class
    """
    
    def __init__(self):
        """Initialize {name}"""
        pass
    
    def __str__(self) -> str:
        """String representation"""
        return f"{name}()"
    
    def __repr__(self) -> str:
        """Developer representation"""
        return self.__str__()
'''
        
        elif template_type == 'function':
            async_def = 'async def' if options.get('async') else 'def'
            return f'''{async_def} {name}():
    """
    {name} function
    
    Returns:
        None
    """
    pass
'''
        
        elif template_type == 'module':
            return f'''"""
{name} module

This module provides functionality for {name}.
"""

__version__ = "1.0.0"
__author__ = "Your Name"

# Module-level imports
from typing import Any, Dict, List, Optional

# Module constants
MODULE_NAME = "{name}"

def main():
    """Main function for {name} module"""
    print(f"Running {{MODULE_NAME}} module")

if __name__ == "__main__":
    main()
'''
        
        elif template_type == 'test':
            return f'''"""
Tests for {name}
"""

import unittest
from unittest.mock import Mock, patch


class Test{name.title()}(unittest.TestCase):
    """Test cases for {name}"""
    
    def setUp(self):
        """Set up test fixtures"""
        pass
    
    def tearDown(self):
        """Clean up test fixtures"""
        pass
    
    def test_{name}_example(self):
        """Test {name} functionality"""
        # Arrange
        expected = True
        
        # Act
        result = True  # Replace with actual call
        
        # Assert
        self.assertEqual(result, expected)

if __name__ == "__main__":
    unittest.main()
'''
        
        return f'# {template_type} template not implemented for Python'
    
    def _javascript_templates(self, template_type: str, name: str, options: Dict[str, Any]) -> str:
        """JavaScript code templates"""
        if template_type == 'class':
            return f'''class {name} {{
    /**
     * Create a {name}
     */
    constructor() {{
        // Initialize {name}
    }}
    
    /**
     * String representation
     * @returns {{string}} String representation
     */
    toString() {{
        return `{name}()`;
    }}
}}

module.exports = {name};
'''
        
        elif template_type == 'function':
            async_keyword = 'async ' if options.get('async') else ''
            return f'''{async_keyword}function {name}() {{
    /**
     * {name} function
     * @returns {{void}}
     */
    // Implementation goes here
}}

module.exports = {name};
'''
        
        return f'// {template_type} template not implemented for JavaScript'
    
    def _typescript_templates(self, template_type: str, name: str, options: Dict[str, Any]) -> str:
        """TypeScript code templates"""
        if template_type == 'class':
            abstract = 'abstract ' if options.get('abstract') else ''
            return f'''{abstract}class {name} {{
    /**
     * Create a {name}
     */
    constructor() {{
        // Initialize {name}
    }}
    
    /**
     * String representation
     */
    toString(): string {{
        return `{name}()`;
    }}
}}

export default {name};
'''
        
        elif template_type == 'interface':
            return f'''interface {name} {{
    // Interface properties and methods
}}

export default {name};
'''
        
        return f'// {template_type} template not implemented for TypeScript'
    
    # Placeholder implementations for other languages
    def _java_templates(self, template_type: str, name: str, options: Dict[str, Any]) -> str:
        return f'// {template_type} template not fully implemented for Java'
    
    def _cpp_templates(self, template_type: str, name: str, options: Dict[str, Any]) -> str:
        return f'// {template_type} template not fully implemented for C++'
    
    def _rust_templates(self, template_type: str, name: str, options: Dict[str, Any]) -> str:
        return f'// {template_type} template not fully implemented for Rust'
    
    def _go_templates(self, template_type: str, name: str, options: Dict[str, Any]) -> str:
        return f'// {template_type} template not fully implemented for Go'
    
    def _html_templates(self, template_type: str, name: str, options: Dict[str, Any]) -> str:
        if template_type == 'component':
            return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name} Component</title>
</head>
<body>
    <div class="{name.lower()}-component">
        <h1>{name}</h1>
        <!-- Component content -->
    </div>
</body>
</html>'''
        return f'<!-- {template_type} template not implemented for HTML -->'
    
    def _css_templates(self, template_type: str, name: str, options: Dict[str, Any]) -> str:
        return f'''/* {name} styles */
.{name.lower()} {{
    /* Add styles here */
}}
'''
    
    def _json_templates(self, template_type: str, name: str, options: Dict[str, Any]) -> str:
        if template_type == 'config':
            return '''{{
    "name": "project-name",
    "version": "1.0.0",
    "description": "Project description",
    "main": "index.js",
    "scripts": {{
        "start": "node index.js",
        "test": "npm test"
    }},
    "dependencies": {{}},
    "devDependencies": {{}}
}}'''
        return f'{{"template": "{template_type}", "name": "{name}"}}'
    
    def _yaml_templates(self, template_type: str, name: str, options: Dict[str, Any]) -> str:
        if template_type == 'config':
            return f'''name: {name}
version: "1.0.0"
description: "Configuration for {name}"

settings:
  debug: false
  port: 3000

database:
  host: localhost
  port: 5432
  name: database_name
'''
        return f'# {template_type} template for {name}'
    
    def _markdown_templates(self, template_type: str, name: str, options: Dict[str, Any]) -> str:
        return f'''# {name}

## Description

Brief description of {name}.

## Usage

```bash
# Usage example
```

## Features

- Feature 1
- Feature 2
- Feature 3

## License

MIT License
'''
    
    def get_status(self) -> Dict[str, Any]:
        """Get code generation tool status"""
        return {
            'tool_name': self.name,
            'version': self.version,
            'supported_languages': list(self.templates.keys()),
            'generation_types': list(self.generators.keys()),
            'capabilities': self.capabilities
        }