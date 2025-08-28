"""
AI Code Generation Tool for Codexa.
Handles code generation, completion, and programming tasks using AI providers.
"""

import asyncio
import re
from typing import Dict, List, Set, Optional, Any
import logging

from ..base.tool_interface import Tool, ToolResult, ToolContext, ToolPriority


class AICodeGenerationTool(Tool):
    """
    Tool for AI-powered code generation and completion.
    
    This tool handles:
    - Code generation from natural language
    - Function and class creation
    - Code completion and suggestions
    - Code refactoring assistance
    - Template generation
    """
    
    @property
    def name(self) -> str:
        return "ai_code_generation"
    
    @property
    def description(self) -> str:
        return "AI-powered code generation, completion, and programming assistance"
    
    @property
    def category(self) -> str:
        return "ai"
    
    @property
    def capabilities(self) -> Set[str]:
        return {
            "code_generation", "function_creation", "class_creation", 
            "code_completion", "programming_assistance", "refactoring",
            "template_generation", "ai_code_generation"
        }
    
    @property
    def priority(self) -> ToolPriority:
        return ToolPriority.HIGH
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("codexa.tools.ai.code_generation")
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Determine if this tool can handle the request."""
        request_lower = request.lower()
        confidence = 0.0
        
        # High confidence for explicit code generation requests
        code_generation_keywords = [
            "generate code", "write code", "create function", "build class",
            "implement method", "code for", "function that", "class that"
        ]
        
        for keyword in code_generation_keywords:
            if keyword in request_lower:
                confidence = max(confidence, 0.95)
        
        # High confidence for programming language mentions
        programming_languages = [
            "python", "javascript", "java", "c++", "c#", "go", "rust",
            "typescript", "php", "ruby", "swift", "kotlin", "scala"
        ]
        
        for lang in programming_languages:
            if lang in request_lower and any(word in request_lower for word in ["code", "function", "class", "implement"]):
                confidence = max(confidence, 0.9)
        
        # Medium-high confidence for general programming terms
        programming_keywords = [
            "function", "method", "class", "algorithm", "implement",
            "refactor", "optimize", "debug", "fix code"
        ]
        
        for keyword in programming_keywords:
            if keyword in request_lower:
                confidence = max(confidence, 0.8)
        
        # Medium confidence for development tasks
        dev_keywords = ["create", "build", "develop", "write"]
        code_indicators = ["code", "program", "script", "application"]
        
        if any(dev in request_lower for dev in dev_keywords) and any(code in request_lower for code in code_indicators):
            confidence = max(confidence, 0.7)
        
        return confidence
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute code generation using AI provider."""
        try:
            if not context.user_request:
                return ToolResult.error_result(
                    error="No request provided for code generation",
                    tool_name=self.name
                )
            
            # Check if AI provider is available
            provider = context.provider
            if not provider:
                return ToolResult.error_result(
                    error="No AI provider available for code generation",
                    tool_name=self.name
                )
            
            # Parse the request to determine what kind of code to generate
            request_analysis = self._analyze_code_request(context.user_request)
            
            # Generate prompt for AI provider
            prompt = self._create_code_generation_prompt(
                context.user_request,
                request_analysis,
                context
            )
            
            # Generate code using AI provider
            try:
                generated_code = await self._call_ai_provider(provider, prompt)
                
                if not generated_code:
                    return ToolResult.error_result(
                        error="AI provider returned empty response",
                        tool_name=self.name
                    )
                
                # Clean and validate the generated code
                cleaned_code = self._clean_generated_code(generated_code, request_analysis["language"])
                
                # Format the result
                result_data = {
                    "generated_code": cleaned_code,
                    "language": request_analysis["language"],
                    "code_type": request_analysis["type"],
                    "provider_used": provider.__class__.__name__ if hasattr(provider, '__class__') else "Unknown",
                    "prompt_length": len(prompt)
                }
                
                # Create formatted output
                formatted_output = self._format_code_output(cleaned_code, request_analysis)
                
                return ToolResult.success_result(
                    data=result_data,
                    tool_name=self.name,
                    output=formatted_output
                )
                
            except Exception as provider_error:
                return ToolResult.error_result(
                    error=f"AI provider error: {str(provider_error)}",
                    tool_name=self.name
                )
                
        except Exception as e:
            self.logger.error(f"Code generation failed: {e}")
            return ToolResult.error_result(
                error=f"Code generation error: {str(e)}",
                tool_name=self.name
            )
    
    def _analyze_code_request(self, request: str) -> Dict[str, Any]:
        """Analyze the code generation request to determine language and type."""
        request_lower = request.lower()
        
        analysis = {
            "type": "function",
            "language": "python",  # default
            "complexity": "medium",
            "includes_tests": False,
            "includes_docs": False
        }
        
        # Detect programming language
        language_patterns = {
            "python": ["python", "py", ".py"],
            "javascript": ["javascript", "js", ".js", "node"],
            "typescript": ["typescript", "ts", ".ts"],
            "java": ["java", ".java"],
            "cpp": ["c++", "cpp", ".cpp", "c plus plus"],
            "csharp": ["c#", "csharp", ".cs"],
            "go": ["golang", "go", ".go"],
            "rust": ["rust", ".rs"],
            "php": ["php", ".php"],
            "ruby": ["ruby", ".rb"],
            "swift": ["swift", ".swift"],
            "kotlin": ["kotlin", ".kt"]
        }
        
        for lang, patterns in language_patterns.items():
            if any(pattern in request_lower for pattern in patterns):
                analysis["language"] = lang
                break
        
        # Detect code type
        if any(word in request_lower for word in ["class", "object", "inheritance"]):
            analysis["type"] = "class"
        elif any(word in request_lower for word in ["function", "method", "def"]):
            analysis["type"] = "function"
        elif any(word in request_lower for word in ["algorithm", "solve", "calculate"]):
            analysis["type"] = "algorithm"
        elif any(word in request_lower for word in ["api", "endpoint", "route"]):
            analysis["type"] = "api"
        elif any(word in request_lower for word in ["script", "program", "application"]):
            analysis["type"] = "script"
        
        # Detect complexity
        if any(word in request_lower for word in ["simple", "basic", "easy"]):
            analysis["complexity"] = "simple"
        elif any(word in request_lower for word in ["complex", "advanced", "sophisticated"]):
            analysis["complexity"] = "complex"
        
        # Check for additional requirements
        if any(word in request_lower for word in ["test", "unittest", "pytest"]):
            analysis["includes_tests"] = True
        
        if any(word in request_lower for word in ["documentation", "docstring", "comments"]):
            analysis["includes_docs"] = True
        
        return analysis
    
    def _create_code_generation_prompt(self, request: str, analysis: Dict[str, Any], context: ToolContext) -> str:
        """Create an optimized prompt for AI code generation."""
        
        prompt_parts = []
        
        # Add role and expertise context
        prompt_parts.append(f"You are an expert {analysis['language']} programmer.")
        
        # Add project context if available
        if context.project_info and context.project_info.get("name"):
            prompt_parts.append(f"Working on project: {context.project_info['name']}")
        
        # Add specific instructions based on analysis
        type_instructions = {
            "function": f"Create a well-structured {analysis['language']} function",
            "class": f"Create a well-designed {analysis['language']} class",
            "algorithm": f"Implement an efficient algorithm in {analysis['language']}",
            "api": f"Create API endpoint code in {analysis['language']}",
            "script": f"Write a complete {analysis['language']} script"
        }
        prompt_parts.append(type_instructions.get(analysis["type"], f"Generate {analysis['language']} code"))
        
        # Add quality requirements
        quality_requirements = [
            "Write clean, readable, and well-structured code",
            "Follow best practices and coding conventions",
            "Include appropriate error handling"
        ]
        
        if analysis["includes_docs"]:
            quality_requirements.append("Include comprehensive documentation and comments")
        
        if analysis["includes_tests"]:
            quality_requirements.append("Include unit tests")
        
        prompt_parts.extend(quality_requirements)
        
        # Add the actual request
        prompt_parts.append(f"Request: {request}")
        
        # Add output format instruction
        prompt_parts.append(f"Provide only the {analysis['language']} code with minimal explanation.")
        
        return "\n\n".join(prompt_parts)
    
    def _clean_generated_code(self, code: str, language: str) -> str:
        """Clean and validate generated code."""
        # Remove common AI response artifacts
        code = re.sub(r'^```[\w]*\n', '', code, flags=re.MULTILINE)
        code = re.sub(r'\n```$', '', code, flags=re.MULTILINE)
        code = code.strip()
        
        # Remove explanatory text that might be included
        lines = code.split('\n')
        code_lines = []
        in_code_block = False
        
        for line in lines:
            # Skip explanatory text before code
            if not in_code_block and (
                line.startswith('Here') or 
                line.startswith('This') or 
                line.startswith('The following') or
                line.startswith('Below')
            ):
                continue
            
            # Detect start of actual code
            if self._looks_like_code(line, language):
                in_code_block = True
            
            if in_code_block:
                code_lines.append(line)
        
        return '\n'.join(code_lines)
    
    def _looks_like_code(self, line: str, language: str) -> bool:
        """Check if a line looks like code for the given language."""
        line = line.strip()
        if not line:
            return False
        
        # Language-specific code patterns
        code_patterns = {
            "python": [r'^def\s+', r'^class\s+', r'^import\s+', r'^from\s+', r'^\s*#', r'=', r'if\s+', r'for\s+'],
            "javascript": [r'^function\s+', r'^const\s+', r'^let\s+', r'^var\s+', r'^\s*//', r'=>', r'\.'],
            "java": [r'^public\s+', r'^private\s+', r'^class\s+', r'^import\s+', r'^\s*//', r'\{', r'\}'],
            "cpp": [r'^#include', r'^int\s+', r'^void\s+', r'^class\s+', r'^\s*//', r'\{', r'\}'],
        }
        
        patterns = code_patterns.get(language, [r'[=\{\}\[\];]', r'^\s*[#//]'])
        
        for pattern in patterns:
            if re.search(pattern, line):
                return True
        
        return False
    
    def _format_code_output(self, code: str, analysis: Dict[str, Any]) -> str:
        """Format code output for display."""
        if not code:
            return "No code generated"
        
        # Create formatted output with language identifier
        language = analysis["language"]
        formatted = f"```{language}\n{code}\n```"
        
        # Add metadata
        metadata = [
            f"Language: {language.title()}",
            f"Type: {analysis['type'].title()}",
            f"Complexity: {analysis['complexity'].title()}"
        ]
        
        return f"{formatted}\n\n**Code Details:**\n" + " | ".join(metadata)
    
    async def _call_ai_provider(self, provider: Any, prompt: str) -> str:
        """Call AI provider with error handling and fallbacks."""
        # Try different provider methods
        methods_to_try = [
            'generate_code', 'generate_text', 'generate', 'complete',
            'chat', 'ask', 'query', '__call__'
        ]
        
        for method_name in methods_to_try:
            if hasattr(provider, method_name):
                method = getattr(provider, method_name)
                if callable(method):
                    try:
                        if asyncio.iscoroutinefunction(method):
                            result = await method(prompt)
                        else:
                            result = method(prompt)
                        
                        if result:
                            return str(result)
                    except Exception as e:
                        self.logger.debug(f"Failed to call {method_name}: {e}")
                        continue
        
        raise Exception("Unable to call AI provider - no compatible methods found")