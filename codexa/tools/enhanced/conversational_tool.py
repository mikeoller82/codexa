"""
Conversational tool for handling basic chat, greetings, and general questions.
"""

import re
from typing import Dict, List, Set, Optional, Any
import logging

from ..base.tool_interface import Tool, ToolResult, ToolContext, ToolPriority


class ConversationalTool(Tool):
    """
    Tool for handling conversational requests, greetings, and general chat.
    
    This tool handles:
    - Greetings (hello, hi, hey)
    - General questions
    - Small talk
    - Basic help requests
    """
    
    @property
    def name(self) -> str:
        return "conversational_tool"
    
    @property
    def description(self) -> str:
        return "Handles conversational requests, greetings, and general chat"
    
    @property
    def category(self) -> str:
        return "enhanced"
    
    @property
    def capabilities(self) -> Set[str]:
        return {
            "greeting", "conversation", "general_chat", 
            "small_talk", "basic_help", "social_interaction"
        }
    
    @property
    def priority(self) -> ToolPriority:
        return ToolPriority.NORMAL
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("codexa.tools.conversational")
        
        # Initialize usage stats
        self._usage_stats = {
            "requests_handled": 0,
            "last_request_type": None,
            "greeting_count": 0,
            "question_count": 0
        }
        
        # Greeting patterns
        self.greeting_patterns = [
            r'\b(hello|hi|hey|greetings|good\s+(morning|afternoon|evening))\b',
            r'\bhowdy\b',
            r'\bsup\b',
            r'\byo\b'
        ]
        
        # Conversational patterns  
        self.conversational_patterns = [
            r'\bhow\s+(are|is)\s+(you|things)\b',
            r'\bwhat\'?s\s+up\b',
            r'\bhow\'?s\s+it\s+going\b',
            r'\bnice\s+to\s+meet\s+you\b',
            r'\bthanks?\b',
            r'\bthank\s+you\b',
            r'\bgoodbye\b',
            r'\bbye\b',
            r'\bsee\s+you\b'
        ]
        
        # Question patterns
        self.question_patterns = [
            r'\bwhat\s+(can|do)\s+you\s+do\b',
            r'\bwho\s+are\s+you\b',
            r'\bwhat\s+are\s+you\b',
            r'\bhelp\s*$',
            r'^\?\s*$',
            r'\bcan\s+you\s+help\b'
        ]
        
        # Response templates
        self.responses = {
            'greeting': [
                "Hello! I'm Codexa, your AI coding assistant. How can I help you with your development work today?",
                "Hi there! Ready to tackle some code? What would you like to work on?",
                "Hey! I'm here to help with your coding projects. What can I assist you with?",
                "Greetings! I'm Codexa, here to make your development workflow smoother. How can I help?"
            ],
            'how_are_you': [
                "I'm doing great and ready to help! What coding challenge can we solve together?",
                "All systems running smoothly! What development task would you like to work on?",
                "I'm functioning optimally and excited to help with your code. What's on your agenda?"
            ],
            'thanks': [
                "You're welcome! Happy to help with your development needs.",
                "My pleasure! Let me know if you need help with anything else.",
                "Glad I could help! Feel free to ask if you have more questions."
            ],
            'goodbye': [
                "Goodbye! Happy coding! 🚀",
                "See you later! Don't hesitate to return when you need coding assistance.",
                "Farewell! Hope your development work goes smoothly."
            ],
            'what_can_you_do': [
                """I'm Codexa, your AI coding assistant! I can help you with:

🔧 **Development Tasks:**
- Write, review, and refactor code
- Debug issues and optimize performance
- Create documentation and tests

📁 **File Operations:**  
- Read, create, modify files and directories
- Search through codebases
- Manage project structure

🤖 **AI Integration:**
- Connect to different AI providers
- Use MCP (Model Context Protocol) servers
- Generate UI components and more

Just tell me what you'd like to work on - I understand natural language requests!""",
                
                """I'm your coding companion! Here's what I can do:

• **Code Development**: Write functions, classes, and full applications
• **Project Management**: Organize files, create documentation  
• **Debugging**: Find and fix issues in your code
• **AI-Powered Features**: Generate UI components, analyze code patterns
• **Tool Integration**: Work with various development tools and APIs

Try asking me something like "create a Python function" or "help me debug this code"!"""
            ],
            'who_are_you': [
                "I'm Codexa, an AI-powered coding assistant designed to help developers with their programming tasks.",
                "I'm Codexa! I'm here to assist you with coding, debugging, file management, and various development tasks.",
                "I'm your AI coding companion, Codexa. I can help with everything from writing code to managing projects."
            ],
            'general': [
                "I'm here to help with your development work! Try asking me to create code, debug issues, or manage your project files.",
                "How can I assist you with coding today? I can write functions, debug problems, create documentation, and much more!",
                "Ready to code! What would you like to work on? I can help with programming tasks, file operations, or project management."
            ]
        }
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """
        Check if this tool can handle the conversational request.
        
        Args:
            request: The user request string
            context: Tool execution context
            
        Returns:
            Confidence score (0.0-1.0)
        """
        if not request or not request.strip():
            return 0.0
            
        request_lower = request.lower().strip()
        
        # Handle greetings - high confidence
        for pattern in self.greeting_patterns:
            if re.search(pattern, request_lower, re.IGNORECASE):
                return 0.9
        
        # Handle conversational patterns - high confidence  
        for pattern in self.conversational_patterns:
            if re.search(pattern, request_lower, re.IGNORECASE):
                return 0.85
                
        # Handle questions about capabilities - high confidence
        for pattern in self.question_patterns:
            if re.search(pattern, request_lower, re.IGNORECASE):
                return 0.8
        
        # Handle very short requests that might be conversational
        if len(request_lower.split()) <= 2:
            common_words = ['hi', 'hello', 'hey', 'help', 'thanks', 'bye', 'yo', 'sup']
            if any(word in request_lower for word in common_words):
                return 0.7
        
        # Handle single word queries
        single_word_patterns = [
            'hello', 'hi', 'hey', 'help', 'thanks', 'bye', 'status', 'info'
        ]
        if request_lower in single_word_patterns:
            return 0.8
        
        # Handle general requests that don't match other tools
        # This provides a safety net for requests that might not match specific tools
        general_indicators = [
            'what', 'how', 'why', 'when', 'where', 'who', 'can you', 'could you',
            'please', 'i need', 'i want', 'i would like', 'show me', 'tell me',
            'explain', 'describe', 'give me', 'find', 'search', 'look for'
        ]
        
        # Check if request contains general indicators
        for indicator in general_indicators:
            if indicator in request_lower:
                return 0.3  # Low confidence but still available
        
        # Handle very short or unclear requests
        if len(request_lower.split()) <= 3:
            return 0.2  # Very low confidence for short requests
            
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """
        Execute the conversational tool.
        
        Args:
            context: Tool execution context
            
        Returns:
            ToolResult with conversational response
        """
        try:
            # Debug: Check what's in the context
            self.logger.debug(f"Context type: {type(context)}")
            self.logger.debug(f"Context attributes: {dir(context)}")
            self.logger.debug(f"Context user_request: {getattr(context, 'user_request', 'NOT_FOUND')}")
            
            # Get request from context user_request
            request = getattr(context, 'user_request', None) or ""
            request = str(request).lower().strip()
            
            self.logger.debug(f"Final request: '{request}'")
            
            if not request:
                return ToolResult.error_result(
                    error=f"No request provided - context.user_request: {getattr(context, 'user_request', 'MISSING')}",
                    tool_name=self.name
                )
            
            # Determine response type and select appropriate response
            response_type = self._classify_request(request)
            response = self._generate_response(response_type, request)
            
            # Track usage
            self._usage_stats["requests_handled"] += 1
            self._usage_stats["last_request_type"] = response_type
            
            return ToolResult.success_result(
                data={
                    "response": response,
                    "response_type": response_type,
                    "conversation": True
                },
                tool_name=self.name,
                output=response
            )
            
        except Exception as e:
            self.logger.error(f"Conversational tool execution failed: {e}")
            return ToolResult.error_result(
                error=f"Conversational error: {str(e)}",
                tool_name=self.name
            )
    
    def _classify_request(self, request: str) -> str:
        """Classify the type of conversational request."""
        
        # Check greeting patterns
        for pattern in self.greeting_patterns:
            if re.search(pattern, request, re.IGNORECASE):
                return 'greeting'
        
        # Check how are you patterns
        if re.search(r'\bhow\s+(are|is)\s+(you|things)', request, re.IGNORECASE):
            return 'how_are_you'
            
        # Check thanks patterns  
        if re.search(r'\b(thanks?|thank\s+you)\b', request, re.IGNORECASE):
            return 'thanks'
            
        # Check goodbye patterns
        if re.search(r'\b(goodbye|bye|see\s+you)\b', request, re.IGNORECASE):
            return 'goodbye'
            
        # Check capability questions
        if re.search(r'\bwhat\s+(can|do)\s+you\s+do\b', request, re.IGNORECASE):
            return 'what_can_you_do'
            
        # Check identity questions  
        if re.search(r'\bwho\s+are\s+you\b', request, re.IGNORECASE):
            return 'who_are_you'
            
        return 'general'
    
    def _generate_response(self, response_type: str, request: str) -> str:
        """Generate appropriate response based on request type."""
        import random
        
        if response_type in self.responses:
            responses = self.responses[response_type]
            return random.choice(responses)
        else:
            # Fallback to general responses
            return random.choice(self.responses['general'])
    
    def get_help(self) -> str:
        """Get help information for this tool."""
        return """**Conversational Tool**

Handles basic conversation, greetings, and general questions.

**Supported patterns:**
• Greetings: hello, hi, hey, good morning
• Questions: what can you do, who are you, help
• Social: how are you, thanks, goodbye
• General chat and small talk

**Examples:**
- "hello" → Friendly greeting response
- "what can you do" → Capabilities overview  
- "thanks" → Acknowledgment response
- "how are you" → Status response

This tool provides a natural conversational interface for basic interactions."""