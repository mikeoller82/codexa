"""
AI Analysis Tool for Codexa.
Handles code analysis, review, and explanation tasks using AI providers.
"""

import asyncio
import re
from typing import Dict, List, Set, Optional, Any
import logging

from ..base.tool_interface import Tool, ToolResult, ToolContext, ToolPriority


class AIAnalysisTool(Tool):
    """
    Tool for AI-powered code analysis and review.
    
    This tool handles:
    - Code analysis and review
    - Code explanation and documentation
    - Bug detection and suggestions
    - Performance analysis
    - Security review
    - Best practices validation
    """
    
    @property
    def name(self) -> str:
        return "ai_analysis"
    
    @property
    def description(self) -> str:
        return "AI-powered code analysis, review, and explanation"
    
    @property
    def category(self) -> str:
        return "ai"
    
    @property
    def capabilities(self) -> Set[str]:
        return {
            "code_analysis", "code_review", "bug_detection", "performance_analysis",
            "security_review", "code_explanation", "best_practices", "ai_analysis"
        }
    
    @property
    def priority(self) -> ToolPriority:
        return ToolPriority.HIGH
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("codexa.tools.ai.analysis")
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Determine if this tool can handle the request."""
        request_lower = request.lower()
        confidence = 0.0
        
        # High confidence for explicit analysis requests
        analysis_keywords = [
            "analyze code", "review code", "code analysis", "code review",
            "check code", "inspect code", "evaluate code", "assess code"
        ]
        
        for keyword in analysis_keywords:
            if keyword in request_lower:
                confidence = max(confidence, 0.95)
        
        # High confidence for specific analysis types
        specific_analysis = [
            "find bugs", "detect issues", "security review", "performance analysis",
            "best practices", "code quality", "vulnerability", "optimize"
        ]
        
        for keyword in specific_analysis:
            if keyword in request_lower:
                confidence = max(confidence, 0.9)
        
        # Medium-high confidence for explanation requests
        explanation_keywords = ["explain", "describe", "what does", "how does"]
        if any(keyword in request_lower for keyword in explanation_keywords) and "code" in request_lower:
            confidence = max(confidence, 0.8)
        
        # Medium confidence for general analysis terms
        general_analysis = ["analyze", "review", "check", "examine", "inspect"]
        for keyword in general_analysis:
            if keyword in request_lower:
                confidence = max(confidence, 0.6)
        
        return confidence
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute code analysis using AI provider."""
        try:
            if not context.user_request:
                return ToolResult.error_result(
                    error="No request provided for code analysis",
                    tool_name=self.name
                )
            
            # Check if AI provider is available
            provider = context.provider
            if not provider:
                return ToolResult.error_result(
                    error="No AI provider available for code analysis",
                    tool_name=self.name
                )
            
            # Parse the request to determine analysis type
            analysis_type = self._determine_analysis_type(context.user_request)
            
            # Get code to analyze (from context or request)
            code_to_analyze = await self._extract_code_for_analysis(context)
            
            if not code_to_analyze:
                return ToolResult.error_result(
                    error="No code found to analyze",
                    tool_name=self.name
                )
            
            # Generate analysis prompt
            prompt = self._create_analysis_prompt(
                context.user_request,
                code_to_analyze,
                analysis_type,
                context
            )
            
            # Perform analysis using AI provider
            try:
                analysis_result = await self._call_ai_provider(provider, prompt)
                
                if not analysis_result:
                    return ToolResult.error_result(
                        error="AI provider returned empty analysis",
                        tool_name=self.name
                    )
                
                # Structure the analysis result
                structured_analysis = self._structure_analysis_result(
                    analysis_result, 
                    analysis_type,
                    code_to_analyze
                )
                
                # Format the result
                result_data = {
                    "analysis": structured_analysis,
                    "analysis_type": analysis_type,
                    "code_analyzed": len(code_to_analyze),
                    "provider_used": provider.__class__.__name__ if hasattr(provider, '__class__') else "Unknown"
                }
                
                # Create formatted output
                formatted_output = self._format_analysis_output(structured_analysis, analysis_type)
                
                return ToolResult.success_result(
                    data=result_data,
                    tool_name=self.name,
                    output=formatted_output
                )
                
            except Exception as provider_error:
                return ToolResult.error_result(
                    error=f"AI provider error during analysis: {str(provider_error)}",
                    tool_name=self.name
                )
                
        except Exception as e:
            self.logger.error(f"Code analysis failed: {e}")
            return ToolResult.error_result(
                error=f"Code analysis error: {str(e)}",
                tool_name=self.name
            )
    
    def _determine_analysis_type(self, request: str) -> str:
        """Determine what type of analysis to perform."""
        request_lower = request.lower()
        
        analysis_types = {
            "security": ["security", "vulnerability", "exploit", "secure", "threat"],
            "performance": ["performance", "optimize", "speed", "efficiency", "bottleneck"],
            "bugs": ["bug", "error", "issue", "problem", "fix", "debug"],
            "best_practices": ["best practices", "coding standards", "conventions", "quality"],
            "explanation": ["explain", "describe", "what does", "how does", "understand"],
            "review": ["review", "assess", "evaluate", "critique", "feedback"],
            "general": ["analyze", "check", "examine", "inspect"]
        }
        
        for analysis_type, keywords in analysis_types.items():
            if any(keyword in request_lower for keyword in keywords):
                return analysis_type
        
        return "general"
    
    async def _extract_code_for_analysis(self, context: ToolContext) -> str:
        """Extract code to analyze from context or mentioned files."""
        code = ""
        
        # First, check if code is directly in the request
        request = context.user_request or ""
        code_blocks = self._extract_code_blocks_from_text(request)
        if code_blocks:
            return "\n\n".join(code_blocks)
        
        # Check if files are mentioned in the request
        if hasattr(context, 'current_dir') and context.current_dir:
            # Look for file mentions in the request
            mentioned_files = self._extract_file_mentions(request)
            
            if mentioned_files:
                # Try to read the mentioned files
                for file_path in mentioned_files[:3]:  # Limit to 3 files
                    try:
                        # Use absolute path if not already
                        if not file_path.startswith('/'):
                            file_path = f"{context.current_dir}/{file_path}"
                        
                        with open(file_path, 'r', encoding='utf-8') as f:
                            file_content = f.read()
                            code += f"\n# File: {file_path}\n{file_content}\n"
                    except Exception as e:
                        self.logger.debug(f"Could not read file {file_path}: {e}")
                        continue
        
        # If still no code, provide a helpful message
        if not code.strip():
            code = "# No specific code provided for analysis\n# Please provide code directly or specify file paths"
        
        return code.strip()
    
    def _extract_code_blocks_from_text(self, text: str) -> List[str]:
        """Extract code blocks from text."""
        # Look for code blocks in markdown format
        code_block_pattern = r'```[\w]*\n(.*?)\n```'
        code_blocks = re.findall(code_block_pattern, text, re.DOTALL)
        
        # Also look for inline code
        if not code_blocks:
            inline_code_pattern = r'`([^`]+)`'
            inline_codes = re.findall(inline_code_pattern, text)
            if inline_codes:
                code_blocks = inline_codes
        
        return code_blocks
    
    def _extract_file_mentions(self, text: str) -> List[str]:
        """Extract file path mentions from text."""
        # Look for file patterns
        file_patterns = [
            r'([a-zA-Z0-9_/.-]+\.[a-zA-Z0-9]+)',  # files with extensions
            r'([a-zA-Z0-9_/-]+/[a-zA-Z0-9_.-]+)',  # paths
        ]
        
        files = []
        for pattern in file_patterns:
            matches = re.findall(pattern, text)
            files.extend(matches)
        
        # Filter out common false positives
        filtered_files = []
        for file_path in files:
            if not any(exclude in file_path for exclude in [
                'http://', 'https://', '@', '.com', '.org', '.net'
            ]):
                filtered_files.append(file_path)
        
        return list(set(filtered_files))  # Remove duplicates
    
    def _create_analysis_prompt(self, request: str, code: str, analysis_type: str, context: ToolContext) -> str:
        """Create an optimized prompt for AI code analysis."""
        
        prompt_parts = []
        
        # Add role and expertise context
        prompt_parts.append("You are an expert software engineer and code reviewer.")
        
        # Add project context if available
        if context.project_info and context.project_info.get("name"):
            prompt_parts.append(f"Analyzing code from project: {context.project_info['name']}")
        
        # Add specific analysis instructions based on type
        analysis_instructions = {
            "security": [
                "Perform a thorough security analysis of the code.",
                "Look for potential vulnerabilities, security flaws, and attack vectors.",
                "Check for input validation, authentication, authorization issues.",
                "Identify any sensitive information exposure or insecure practices."
            ],
            "performance": [
                "Analyze the code for performance issues and optimization opportunities.",
                "Look for algorithmic inefficiencies, resource usage, and bottlenecks.",
                "Suggest improvements for speed, memory usage, and scalability.",
                "Consider time and space complexity."
            ],
            "bugs": [
                "Carefully examine the code for bugs, errors, and potential issues.",
                "Look for logical errors, edge cases, and exception handling problems.",
                "Check for null pointer exceptions, array bounds, and type mismatches.",
                "Identify any code that might cause runtime errors."
            ],
            "best_practices": [
                "Review the code against software engineering best practices.",
                "Check coding standards, naming conventions, and code organization.",
                "Evaluate maintainability, readability, and documentation quality.",
                "Suggest improvements for code structure and design patterns."
            ],
            "explanation": [
                "Provide a clear, detailed explanation of what this code does.",
                "Break down the logic, data flow, and key components.",
                "Explain any complex algorithms or design patterns used.",
                "Make the explanation accessible and educational."
            ],
            "review": [
                "Provide a comprehensive code review with constructive feedback.",
                "Cover functionality, quality, maintainability, and potential improvements.",
                "Highlight both strengths and areas for improvement.",
                "Suggest specific actionable recommendations."
            ],
            "general": [
                "Provide a general analysis of the code quality and functionality.",
                "Look for potential issues, improvements, and best practices.",
                "Give an overall assessment and recommendations."
            ]
        }
        
        instructions = analysis_instructions.get(analysis_type, analysis_instructions["general"])
        prompt_parts.extend(instructions)
        
        # Add formatting requirements
        prompt_parts.extend([
            "",
            "Please structure your analysis with clear sections:",
            "1. Summary/Overview",
            "2. Key Findings",
            "3. Specific Issues (if any)",
            "4. Recommendations",
            "5. Conclusion",
            "",
            "Provide specific examples and line references where applicable.",
        ])
        
        # Add the actual request and code
        prompt_parts.extend([
            f"User Request: {request}",
            "",
            "Code to analyze:",
            "```",
            code,
            "```"
        ])
        
        return "\n".join(prompt_parts)
    
    def _structure_analysis_result(self, analysis_result: str, analysis_type: str, code: str) -> Dict[str, Any]:
        """Structure the raw analysis result into organized sections."""
        
        structured = {
            "type": analysis_type,
            "summary": "",
            "findings": [],
            "recommendations": [],
            "severity": "info",
            "code_length": len(code.split('\n'))
        }
        
        # Try to extract structured information from the analysis
        lines = analysis_result.split('\n')
        current_section = "summary"
        current_content = []
        
        for line in lines:
            line = line.strip()
            
            # Detect section headers
            if any(header in line.lower() for header in ["summary", "overview"]):
                if current_content:
                    structured[current_section] = "\n".join(current_content)
                current_section = "summary"
                current_content = []
            elif any(header in line.lower() for header in ["findings", "issues", "problems"]):
                if current_content:
                    structured[current_section] = "\n".join(current_content)
                current_section = "findings"
                current_content = []
            elif any(header in line.lower() for header in ["recommendations", "suggestions"]):
                if current_content:
                    if current_section == "findings":
                        structured["findings"] = current_content
                    else:
                        structured[current_section] = "\n".join(current_content)
                current_section = "recommendations"
                current_content = []
            else:
                if line:  # Skip empty lines
                    current_content.append(line)
        
        # Handle remaining content
        if current_content:
            if current_section == "findings":
                structured["findings"] = current_content
            elif current_section == "recommendations":
                structured["recommendations"] = current_content
            else:
                structured[current_section] = "\n".join(current_content)
        
        # Determine severity based on findings
        if isinstance(structured["findings"], list):
            findings_text = " ".join(structured["findings"]).lower()
        else:
            findings_text = str(structured["findings"]).lower()
        
        if any(term in findings_text for term in ["critical", "severe", "security", "vulnerability"]):
            structured["severity"] = "high"
        elif any(term in findings_text for term in ["warning", "issue", "problem", "bug"]):
            structured["severity"] = "medium"
        
        return structured
    
    def _format_analysis_output(self, analysis: Dict[str, Any], analysis_type: str) -> str:
        """Format analysis output for display."""
        
        output_parts = []
        
        # Add header with analysis type
        severity_emoji = {"high": "🚨", "medium": "⚠️", "info": "ℹ️"}
        emoji = severity_emoji.get(analysis["severity"], "📊")
        
        output_parts.append(f"{emoji} **Code Analysis Results** ({analysis_type.title()})")
        output_parts.append("=" * 50)
        
        # Add summary
        if analysis.get("summary"):
            output_parts.extend([
                "",
                "**Summary:**",
                analysis["summary"]
            ])
        
        # Add findings
        findings = analysis.get("findings", [])
        if findings:
            output_parts.extend(["", "**Key Findings:**"])
            if isinstance(findings, list):
                for i, finding in enumerate(findings, 1):
                    output_parts.append(f"{i}. {finding}")
            else:
                output_parts.append(str(findings))
        
        # Add recommendations
        recommendations = analysis.get("recommendations", [])
        if recommendations:
            output_parts.extend(["", "**Recommendations:**"])
            if isinstance(recommendations, list):
                for i, rec in enumerate(recommendations, 1):
                    output_parts.append(f"{i}. {rec}")
            else:
                output_parts.append(str(recommendations))
        
        # Add metadata
        output_parts.extend([
            "",
            f"**Analysis Details:**",
            f"• Code Lines: {analysis['code_length']}",
            f"• Severity: {analysis['severity'].title()}",
            f"• Type: {analysis_type.title()}"
        ])
        
        return "\n".join(output_parts)
    
    async def _call_ai_provider(self, provider: Any, prompt: str) -> str:
        """Call AI provider with error handling and fallbacks."""
        # Try different provider methods
        methods_to_try = [
            'analyze_code', 'analyze', 'review_code', 'generate_text', 
            'generate', 'complete', 'chat', 'ask', 'query', '__call__'
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