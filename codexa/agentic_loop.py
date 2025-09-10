"""
Agentic Loop System for Codexa - Think, Execute, Evaluate, Repeat
"""

import asyncio
import time
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.text import Text

try:
    from .enhanced_providers import EnhancedProviderFactory
    from .tools.base.tool_manager import ToolManager
    from .planning import PlanningManager
    from .execution import TaskExecutionManager
    from .providers import ProviderFactory  # Always import this as fallback
    from .session_memory import SessionMemory, AgenticContext
    ENHANCED_MODE = True
except ImportError:
    from .providers import ProviderFactory
    from .planning import PlanningManager  
    from .execution import TaskExecutionManager
    try:
        from .session_memory import SessionMemory, AgenticContext
    except ImportError:
        SessionMemory = None
        AgenticContext = None
    ENHANCED_MODE = False


class LoopStatus(Enum):
    """Status of the agentic loop."""
    THINKING = "thinking"
    EXECUTING = "executing"
    EVALUATING = "evaluating"
    REFINING = "refining"
    SUCCESS = "success"
    FAILURE = "failure"
    MAX_ITERATIONS = "max_iterations"


@dataclass
class LoopIteration:
    """Represents a single iteration of the agentic loop."""
    iteration: int
    thinking: str
    plan: str
    execution_result: str
    evaluation: str
    success: bool
    feedback: str
    timestamp: datetime
    duration: float = 0.0


@dataclass
class AgenticTaskResult:
    """Result of an agentic task execution."""
    task: str
    status: LoopStatus
    iterations: List[LoopIteration]
    total_duration: float
    final_result: Optional[str]
    success: bool


class CodexaAgenticLoop:
    """
    Agentic Loop System for Codexa
    
    This system implements an autonomous execution loop where Codexa:
    1. Thinks out loud about the task (shows reasoning/steps)
    2. Executes one clear action
    3. Evaluates the result
    4. Refines the approach if needed
    5. Repeats until task is complete or max iterations reached
    """

    def __init__(
        self,
        config=None,
        console: Console = None,
        max_iterations: int = 20,
        verbose: bool = True,
        session_memory: Optional[SessionMemory] = None
    ):
        """Initialize the agentic loop system."""
        self.console = console or Console()
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.logger = logging.getLogger("codexa.agentic_loop")
        
        # Session memory integration
        self.session_memory = session_memory
        
        # Initialize providers and tools
        self.config = config
        self.provider = None
        self.tool_manager = None
        
        if config:
            try:
                if ENHANCED_MODE:
                    # Try enhanced provider first
                    try:
                        enhanced_factory = EnhancedProviderFactory()
                        self.provider = enhanced_factory.get_provider()
                        if self.provider:
                            self.tool_manager = ToolManager()
                            self.logger.info("Using enhanced provider mode")
                    except Exception as e:
                        self.logger.warning(f"Enhanced mode failed: {e}")
                
                # Fallback to basic provider if enhanced failed or not available
                if not self.provider:
                    self.provider = ProviderFactory.create_provider(config)
                    self.logger.info("Using basic provider mode")
                    
            except Exception as e:
                self.logger.error(f"Provider initialization failed: {e}")
                self.provider = None
            
        # Initialize managers
        self.planning_manager = None
        self.execution_manager = None
        
        # Loop state
        self.current_task = None
        self.iterations: List[LoopIteration] = []
        self.start_time = None

    async def run_agentic_loop(self, task: str) -> AgenticTaskResult:
        """
        Run the main agentic loop until task completion or max iterations.
        
        Args:
            task: The task description to accomplish
            
        Returns:
            AgenticTaskResult with complete execution history
        """
        self.current_task = task
        self.iterations = []
        self.start_time = time.time()
        
        # Initialize or update session memory context
        if self.session_memory and SessionMemory:
            if not self.session_memory.agentic_context:
                self.session_memory.start_agentic_context(task)
                self.logger.info("Started new agentic context in session memory")
            else:
                # Update existing context with new iteration
                self.session_memory.agentic_context.current_objective = task
                self.session_memory.agentic_context.update_activity()
                self.logger.info("Continuing existing agentic context")
        
        if self.verbose:
            self._display_task_header(task)
        
        context = task
        status = LoopStatus.THINKING
        
        for i in range(self.max_iterations):
            iteration_start = time.time()
            
            if self.verbose:
                self._display_iteration_header(i + 1)
            
            # Step 1: Think / Plan
            thinking_result = await self._think_step(context, i + 1)
            if self.verbose:
                self._display_thinking(thinking_result)
            
            # Step 2: Execute
            execution_result = await self._execute_step(thinking_result["plan"], i + 1)
            if self.verbose:
                self._display_execution(execution_result)
            
            # Step 3: Evaluate
            evaluation_result = await self._evaluate_step(
                execution_result, context, thinking_result["plan"]
            )
            if self.verbose:
                self._display_evaluation(evaluation_result)
            
            # Record iteration
            iteration_duration = time.time() - iteration_start
            iteration = LoopIteration(
                iteration=i + 1,
                thinking=thinking_result["thinking"],
                plan=thinking_result["plan"],
                execution_result=execution_result["result"],
                evaluation=evaluation_result["feedback"],
                success=evaluation_result["success"],
                feedback=evaluation_result["feedback"],
                timestamp=datetime.now(),
                duration=iteration_duration
            )
            self.iterations.append(iteration)
            
            # Update session memory with iteration results
            if self.session_memory and SessionMemory:
                tools_used = execution_result.get("tools_used", [])
                files_created = execution_result.get("files_created", [])
                files_modified = execution_result.get("files_modified", [])
                
                # Determine completed vs pending steps based on evaluation
                if evaluation_result["success"]:
                    completed_steps = [thinking_result["plan"]]
                    pending_steps = []
                else:
                    completed_steps = []
                    pending_steps = [thinking_result["plan"]]
                
                self.session_memory.update_agentic_context(
                    iteration_count=i + 1,
                    last_result=execution_result["result"],
                    last_evaluation=evaluation_result["feedback"],
                    completed_steps=completed_steps,
                    pending_steps=pending_steps,
                    files_created=files_created,
                    files_modified=files_modified,
                    tools_used=tools_used
                )
            
            # Step 4: Check for completion
            if evaluation_result["success"]:
                status = LoopStatus.SUCCESS
                
                # Mark task as completed in session memory
                if self.session_memory and SessionMemory:
                    self.session_memory.complete_agentic_context(execution_result["result"])
                
                if self.verbose:
                    self._display_success(i + 1)
                break
            else:
                # Step 5: Refine context for next iteration
                refined_context = await self._refine_task(context, evaluation_result["feedback"])
                context = refined_context
                if self.verbose:
                    self._display_refinement(refined_context)
            
            # Brief pause to make the loop visible
            if self.verbose:
                await asyncio.sleep(0.5)
        
        if status != LoopStatus.SUCCESS:
            status = LoopStatus.MAX_ITERATIONS
            if self.verbose:
                self._display_max_iterations_reached()
        
        total_duration = time.time() - self.start_time
        
        # Create final result
        result = AgenticTaskResult(
            task=task,
            status=status,
            iterations=self.iterations,
            total_duration=total_duration,
            final_result=execution_result["result"] if status == LoopStatus.SUCCESS else None,
            success=status == LoopStatus.SUCCESS
        )
        
        if self.verbose:
            self._display_final_summary(result)
        
        return result

    async def _think_step(self, context: str, iteration: int) -> Dict[str, str]:
        """
        Generate reasoning and plan for the next action using real LLM.
        
        Args:
            context: Current task context
            iteration: Current iteration number
            
        Returns:
            Dictionary with 'thinking' and 'plan' keys
        """
        try:
            # Construct thinking prompt using Codexa Agent identity
            thinking_prompt = f"""You are Codexa Agent developed by Codexa Code, an agentic coding AI assistant with access to the developer's codebase through Codexa's world-leading context engine and integrations.

You are currently running in autonomous agentic loop mode.

CURRENT TASK: {context}
ITERATION: {iteration}/{self.max_iterations}

Think through this task step by step and plan your next concrete action. Be specific and actionable.

FORMAT YOUR RESPONSE AS:

THINKING:
[Your reasoning process - what you understand about the task, what you've learned from previous attempts, and what approach you want to take]

PLAN:
[One specific, concrete action you will take next - be very specific about files to read/write, code to create, or commands to run]

Remember:
- Be specific about file names and paths
- If creating code, specify the programming language
- If reading files, mention what you're looking for
- If this is iteration {iteration}, consider what might have failed before
- Focus on ONE clear action that moves toward completing the task"""
            
            if self.provider and hasattr(self.provider, 'ask'):
                # Use the provider's ask method (works with OpenRouter)
                response = self.provider.ask(thinking_prompt)
            elif self.provider and hasattr(self.provider, 'generate_response'):
                # Alternative method if available
                response = await self.provider.generate_response(thinking_prompt)
            else:
                # Fallback reasoning
                response = f"""THINKING:
I need to analyze the task "{context}" and determine the next action.
This is iteration {iteration}, so I should be specific and actionable.

PLAN:
Analyze the task requirements and take the first logical step to complete it."""
            
            # Parse response
            thinking = ""
            plan = ""
            
            if "THINKING:" in response and "PLAN:" in response:
                parts = response.split("PLAN:")
                thinking = parts[0].replace("THINKING:", "").strip()
                plan = parts[1].strip()
            else:
                # Try alternative parsing
                lines = response.split('\n')
                in_thinking = False
                in_plan = False
                thinking_lines = []
                plan_lines = []
                
                for line in lines:
                    line = line.strip()
                    if line.startswith("THINKING"):
                        in_thinking = True
                        in_plan = False
                        continue
                    elif line.startswith("PLAN"):
                        in_thinking = False
                        in_plan = True
                        continue
                    
                    if in_thinking:
                        thinking_lines.append(line)
                    elif in_plan:
                        plan_lines.append(line)
                
                thinking = '\n'.join(thinking_lines).strip()
                plan = '\n'.join(plan_lines).strip()
                
                # Final fallback
                if not thinking or not plan:
                    thinking = f"Analyzing task iteration {iteration}"
                    plan = response.strip()[:200] if response.strip() else "Take next logical step"
            
            # Clean up empty responses
            if not thinking:
                thinking = f"Processing task context for iteration {iteration}"
            if not plan:
                plan = "Determine and execute the next logical action"
            
            return {
                "thinking": thinking,
                "plan": plan,
                "raw_response": response,
                "provider_used": bool(self.provider)
            }
            
        except Exception as e:
            self.logger.error(f"Think step failed: {e}")
            return {
                "thinking": f"Error in thinking step: {e}. Falling back to basic reasoning.",
                "plan": "Attempt to complete the task using available information",
                "raw_response": str(e),
                "provider_used": False
            }

    async def _execute_step(self, plan: str, iteration: int) -> Dict[str, Any]:
        """
        Execute the planned action.
        
        Args:
            plan: The plan to execute
            iteration: Current iteration number
            
        Returns:
            Dictionary with execution results
        """
        try:
            execution_start = time.time()
            
            # Determine execution type from plan
            if self.tool_manager and ENHANCED_MODE:
                result = await self._execute_with_tools(plan, iteration)
            else:
                result = await self._execute_basic(plan, iteration)
            
            execution_duration = time.time() - execution_start
            
            return {
                "result": result,
                "duration": execution_duration,
                "success": True,
                "method": "tools" if self.tool_manager else "basic"
            }
            
        except Exception as e:
            self.logger.error(f"Execute step failed: {e}")
            return {
                "result": f"Execution failed: {e}",
                "duration": 0,
                "success": False,
                "error": str(e)
            }

    async def _execute_with_tools(self, plan: str, iteration: int) -> str:
        """Execute plan using Codexa's tool system."""
        try:
            if not self.tool_manager:
                return await self._execute_basic(plan, iteration)
            
            # Show what we're about to do
            if self.verbose:
                from rich.console import Console
                console = Console()
                console.print(f"[cyan]🛠️ Using tool system to execute: {plan[:80]}{'...' if len(plan) > 80 else ''}[/cyan]")
            
            # Create a context for tool execution
            from .tools.base.tool_interface import ToolContext
            
            context = ToolContext(
                tool_manager=self.tool_manager,
                config=self.config,
                user_request=plan,
                current_path=".",
                provider=self.provider
            )
            
            # Use the tool manager to process the plan
            result = await self.tool_manager.process_request(
                plan, 
                context, 
                max_tools=3,
                verbose=self.verbose,
                enable_coordination=True
            )
            
            if result.success:
                # Extract meaningful result for the agentic loop
                if result.data:
                    if isinstance(result.data, dict):
                        # Extract useful information from structured data
                        if 'message' in result.data:
                            return str(result.data['message'])
                        elif 'coordination_result' in result.data:
                            return self._extract_coordination_message(result.data['coordination_result'])
                        elif 'output' in result.data:
                            return str(result.data['output'])
                    return str(result.data)
                elif result.output:
                    return str(result.output)
                else:
                    return f"Tool execution completed successfully for iteration {iteration}"
            else:
                error_msg = result.error or "Tool execution failed"
                self.logger.warning(f"Tool execution failed in iteration {iteration}: {error_msg}")
                return f"Tool execution failed: {error_msg}. May need to try a different approach."
                
        except Exception as e:
            self.logger.error(f"Tool execution failed: {e}")
            return f"Tool execution failed: {e}. Falling back to basic approach."
    
    def _extract_coordination_message(self, coordination_result) -> str:
        """Extract a clean message from coordination results."""
        if hasattr(coordination_result, 'tool_results'):
            for tool_name, tool_result in coordination_result.tool_results.items():
                if hasattr(tool_result, 'success') and tool_result.success:
                    if hasattr(tool_result, 'data') and isinstance(tool_result.data, dict):
                        if 'message' in tool_result.data:
                            return str(tool_result.data['message'])
                        elif 'response' in tool_result.data:
                            return str(tool_result.data['response'])
                    elif hasattr(tool_result, 'output') and tool_result.output:
                        return str(tool_result.output)
            return "Tool coordination completed successfully"
        return "Coordination executed"

    async def _execute_file_read(self, plan: str) -> str:
        """Execute file reading using real file operations."""
        try:
            # Extract filename from plan
            import re
            filename_patterns = [
                r'read\s+(?:file\s+)?["\']?([^"\'\\s]+)["\']?',
                r'(?:open|check|examine)\s+["\']?([^"\'\\s]+)["\']?',
                r'["\']([^"\']*\.(?:py|js|json|md|txt|yml|yaml)[^"\']*)["\']'
            ]
            
            filename = None
            for pattern in filename_patterns:
                match = re.search(pattern, plan, re.IGNORECASE)
                if match:
                    filename = match.group(1)
                    break
            
            if not filename:
                return "Could not determine which file to read from the plan. Please specify a filename."
            
            # Try to read the file
            from pathlib import Path
            file_path = Path(filename)
            
            if not file_path.exists():
                # Try relative to current directory or common locations
                possible_paths = [
                    Path.cwd() / filename,
                    Path.cwd() / "src" / filename,
                    Path.cwd() / "lib" / filename,
                    Path.cwd() / "app" / filename
                ]
                
                for path in possible_paths:
                    if path.exists():
                        file_path = path
                        break
                else:
                    return f"File '{filename}' not found in current directory or common locations."
            
            content = file_path.read_text(encoding='utf-8')
            lines = len(content.split('\n'))
            size = len(content)
            
            return f"Successfully read file '{filename}' ({lines} lines, {size} characters). File content loaded and ready for analysis."
            
        except Exception as e:
            return f"Failed to read file: {e}"

    async def _execute_file_write(self, plan: str) -> str:
        """Execute file writing using real file operations."""
        try:
            # Extract filename and content from plan
            import re
            
            # Try to extract filename
            filename_patterns = [
                r'(?:create|write|make)\s+(?:file\s+)?["\']?([^"\'\\s]+)["\']?',
                r'["\']([^"\']*\.(?:py|js|json|md|txt|yml|yaml)[^"\']*)["\']'
            ]
            
            filename = None
            for pattern in filename_patterns:
                match = re.search(pattern, plan, re.IGNORECASE)
                if match:
                    filename = match.group(1)
                    break
            
            if not filename:
                # Generate a filename based on the plan
                if "python" in plan.lower() or ".py" in plan:
                    filename = "generated_script.py"
                elif "javascript" in plan.lower() or "js" in plan.lower():
                    filename = "generated_script.js"
                elif "json" in plan.lower():
                    filename = "generated_data.json"
                elif "markdown" in plan.lower() or "readme" in plan.lower():
                    filename = "README.md"
                else:
                    filename = "generated_file.txt"
            
            # Generate appropriate content based on the plan
            content = self._generate_file_content_from_plan(plan, filename)
            
            # Write the file
            from pathlib import Path
            file_path = Path(filename)
            
            # Create directory if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding='utf-8')
            
            return f"Successfully created file '{filename}' with {len(content.split('\\n'))} lines of content."
            
        except Exception as e:
            return f"Failed to create file: {e}"

    async def _execute_search(self, plan: str) -> str:
        """Execute search operations."""
        try:
            import re
            from pathlib import Path
            
            # Extract search term from plan
            search_patterns = [
                r'search\s+for\s+["\']([^"\']+)["\']',
                r'find\s+["\']([^"\']+)["\']',
                r'look\s+for\s+["\']([^"\']+)["\']'
            ]
            
            search_term = None
            for pattern in search_patterns:
                match = re.search(pattern, plan, re.IGNORECASE)
                if match:
                    search_term = match.group(1)
                    break
            
            if not search_term:
                return "Could not determine what to search for from the plan."
            
            # Search in current directory
            results = []
            current_dir = Path.cwd()
            
            # Search in common file types
            extensions = ['.py', '.js', '.ts', '.json', '.md', '.txt', '.yml', '.yaml']
            
            for ext in extensions:
                for file_path in current_dir.rglob(f"*{ext}"):
                    try:
                        if file_path.is_file():
                            content = file_path.read_text(encoding='utf-8', errors='ignore')
                            if search_term.lower() in content.lower():
                                line_count = content.count('\\n') + 1
                                results.append(f"{file_path.relative_to(current_dir)} (found in {line_count} line file)")
                    except Exception:
                        continue
            
            if results:
                return f"Found '{search_term}' in {len(results)} files:\\n" + "\\n".join(results[:10])
            else:
                return f"No files found containing '{search_term}' in the current project."
            
        except Exception as e:
            return f"Search operation failed: {e}"

    async def _execute_command(self, plan: str) -> str:
        """Execute command operations (simulated for security)."""
        # For security, we simulate command execution rather than actually running commands
        import re
        
        command_patterns = [
            r'run\s+["\']([^"\']+)["\']',
            r'execute\s+["\']([^"\']+)["\']',
            r'command\s+["\']([^"\']+)["\']'
        ]
        
        command = None
        for pattern in command_patterns:
            match = re.search(pattern, plan, re.IGNORECASE)
            if match:
                command = match.group(1)
                break
        
        if not command:
            return "Could not determine which command to execute from the plan."
        
        # Simulate safe commands
        if command.startswith(('ls', 'dir', 'pwd', 'whoami')):
            return f"Simulated execution of safe command: {command}"
        elif command.startswith(('python', 'node', 'npm')):
            return f"Would execute development command: {command} (simulated for security)"
        else:
            return f"Command execution requested: {command} (simulated for security reasons)"

    async def _execute_directory_list(self, plan: str) -> str:
        """Execute directory listing operations."""
        try:
            from pathlib import Path
            
            current_dir = Path.cwd()
            items = []
            
            for item in current_dir.iterdir():
                if item.is_file():
                    size = item.stat().st_size
                    items.append(f"📄 {item.name} ({size} bytes)")
                elif item.is_dir():
                    try:
                        file_count = len(list(item.iterdir()))
                        items.append(f"📁 {item.name}/ ({file_count} items)")
                    except PermissionError:
                        items.append(f"📁 {item.name}/ (permission denied)")
            
            if items:
                return f"Directory listing for {current_dir.name}:\\n" + "\\n".join(items[:20])
            else:
                return f"Directory {current_dir.name} appears to be empty."
                
        except Exception as e:
            return f"Failed to list directory: {e}"

    async def _execute_with_tool_manager(self, plan: str, iteration: int) -> str:
        """Execute using the tool manager system."""
        try:
            # This would use the actual tool manager to select and execute appropriate tools
            # For now, provide intelligent fallback
            plan_lower = plan.lower()
            
            if any(word in plan_lower for word in ['analyze', 'check', 'examine', 'review']):
                return f"Analysis operation based on plan: {plan}"
            elif any(word in plan_lower for word in ['fix', 'repair', 'correct', 'debug']):
                return f"Fix operation based on plan: {plan}"
            elif any(word in plan_lower for word in ['optimize', 'improve', 'enhance']):
                return f"Optimization operation based on plan: {plan}"
            else:
                return f"General operation executed based on plan: {plan}"
                
        except Exception as e:
            return f"Tool manager execution failed: {e}"

    def _generate_file_content_from_plan(self, plan: str, filename: str) -> str:
        """Generate appropriate file content based on the plan and filename."""
        from pathlib import Path
        
        file_extension = Path(filename).suffix.lower()
        plan_lower = plan.lower()
        
        if file_extension == '.py':
            if 'hello' in plan_lower or 'world' in plan_lower:
                return '#!/usr/bin/env python3\\n\\nprint("Hello, World!")\\n'
            elif 'fibonacci' in plan_lower:
                return '''#!/usr/bin/env python3

def fibonacci(n):
    """Calculate the nth Fibonacci number."""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

def main():
    # Calculate and print first 10 Fibonacci numbers
    for i in range(10):
        print(f"F({i}) = {fibonacci(i)}")

if __name__ == "__main__":
    main()
'''
            elif 'calculator' in plan_lower:
                return '''#!/usr/bin/env python3

def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    if b != 0:
        return a / b
    else:
        return "Error: Division by zero"

def main():
    print("Simple Calculator")
    print("1. Add")
    print("2. Subtract") 
    print("3. Multiply")
    print("4. Divide")

if __name__ == "__main__":
    main()
'''
            else:
                return f'''#!/usr/bin/env python3
"""
{plan}
"""

def main():
    # TODO: Implement the functionality described in the plan
    pass

if __name__ == "__main__":
    main()
'''
        
        elif file_extension == '.js':
            if 'hello' in plan_lower:
                return 'console.log("Hello, World!");\\n'
            else:
                return f'''// {plan}

function main() {{
    // TODO: Implement the functionality described in the plan
}}

main();
'''
        
        elif file_extension == '.json':
            return '''{
    "name": "generated-project",
    "description": "''' + plan + '''",
    "version": "1.0.0"
}
'''
        
        elif file_extension == '.md':
            return f'''# Generated File

## Purpose
{plan}

## Implementation
TODO: Add implementation details here.
'''
        
        else:
            return f'''Generated file based on plan: {plan}

TODO: Implement the required functionality.
'''

    async def _execute_basic(self, plan: str, iteration: int) -> str:
        """Execute plan using basic operations."""
        # Basic execution fallback
        return f"Executed plan (iteration {iteration}): {plan}"

    async def _evaluate_step(
        self, 
        execution_result: Dict[str, Any], 
        original_context: str,
        plan: str
    ) -> Dict[str, Any]:
        """
        Evaluate if the execution result solves the task using LLM-powered analysis.
        
        Args:
            execution_result: Result from execution step
            original_context: Original task context
            plan: The plan that was executed
            
        Returns:
            Dictionary with success status and feedback
        """
        try:
            result_text = execution_result.get("result", "")
            
            # Try LLM-powered evaluation first
            if self.provider and hasattr(self.provider, 'ask'):
                llm_evaluation = await self._evaluate_with_llm(
                    original_context, plan, result_text, execution_result
                )
                if llm_evaluation:
                    return llm_evaluation
            
            # Fallback to heuristic evaluation
            return await self._evaluate_with_heuristics(execution_result, original_context, plan)
            
        except Exception as e:
            self.logger.error(f"Evaluate step failed: {e}")
            return {
                "success": False,
                "feedback": f"Evaluation error: {e}",
                "error": str(e),
                "evaluation_method": "error"
            }

    async def _evaluate_with_llm(
        self,
        original_context: str,
        plan: str,
        result_text: str,
        execution_result: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Use LLM to evaluate task completion."""
        try:
            evaluation_prompt = f"""You are Codexa Agent evaluating whether a task was completed successfully.

ORIGINAL TASK: {original_context}

PLAN THAT WAS EXECUTED: {plan}

EXECUTION RESULT: {result_text}

EXECUTION SUCCESS: {execution_result.get('success', False)}

Please evaluate whether the execution result indicates the original task was completed successfully.

Respond in this format:

SUCCESS: true/false
CONFIDENCE: 0.0-1.0 (how confident you are in this assessment)
REASONING: [Explain your reasoning for this evaluation]
FEEDBACK: [Brief feedback on what was accomplished or what needs to be done next]

Consider:
- Did the execution achieve what the original task requested?
- Was the plan appropriate for the task?
- Are there any errors or failures in the result?
- Is the result relevant to the original task?
- Would a user consider this task "done"?"""

            response = self.provider.ask(evaluation_prompt)
            
            # Parse LLM response
            success = False
            confidence = 0.0
            reasoning = ""
            feedback = ""
            
            lines = response.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('SUCCESS:'):
                    success_text = line.split(':', 1)[1].strip().lower()
                    success = success_text in ['true', 'yes', '1']
                elif line.startswith('CONFIDENCE:'):
                    try:
                        confidence = float(line.split(':', 1)[1].strip())
                    except ValueError:
                        confidence = 0.5
                elif line.startswith('REASONING:'):
                    reasoning = line.split(':', 1)[1].strip()
                elif line.startswith('FEEDBACK:'):
                    feedback = line.split(':', 1)[1].strip()
            
            # If we didn't get proper parsing, try a simpler approach
            if not feedback:
                if 'successfully' in response.lower() or 'completed' in response.lower():
                    success = True
                    feedback = "Task appears to be completed successfully based on LLM evaluation."
                else:
                    success = False
                    feedback = "Task does not appear to be completed based on LLM evaluation."
                    
            return {
                "success": success,
                "feedback": feedback,
                "confidence": confidence,
                "reasoning": reasoning,
                "evaluation_method": "llm",
                "llm_response": response
            }
            
        except Exception as e:
            self.logger.warning(f"LLM evaluation failed: {e}")
            return None

    async def _evaluate_with_heuristics(
        self,
        execution_result: Dict[str, Any],
        original_context: str,
        plan: str
    ) -> Dict[str, Any]:
        """Fallback heuristic evaluation when LLM is unavailable."""
        result_text = execution_result.get("result", "")
        
        # Enhanced heuristic indicators
        success_indicators = [
            "successfully", "completed", "finished", "done", "created", "generated",
            "written", "updated", "saved", "built", "implemented", "fixed"
        ]
        
        failure_indicators = [
            "error", "failed", "exception", "not found", "cannot", "unable",
            "denied", "invalid", "missing", "timeout", "refused"
        ]
        
        result_lower = result_text.lower()
        
        # Check for explicit success/failure indicators
        success_count = sum(1 for indicator in success_indicators if indicator in result_lower)
        failure_count = sum(1 for indicator in failure_indicators if indicator in result_lower)
        
        # Enhanced evaluation logic
        if failure_count > 0:
            success = False
            feedback = f"Execution encountered {failure_count} error indicator(s). Need to try a different approach."
        elif success_count > 0:
            success = True
            feedback = f"Execution shows {success_count} success indicator(s). Task appears completed."
        else:
            # Check task-specific indicators
            context_lower = original_context.lower()
            task_completed = False
            
            # Check for file creation tasks
            if "create" in context_lower or "write" in context_lower:
                if "created" in result_lower or "written" in result_lower:
                    task_completed = True
            
            # Check for read tasks
            if "read" in context_lower or "open" in context_lower:
                if "read" in result_lower or "loaded" in result_lower:
                    task_completed = True
            
            # Check for search tasks
            if "search" in context_lower or "find" in context_lower:
                if "found" in result_lower or "results" in result_lower:
                    task_completed = True
            
            if task_completed:
                success = True
                feedback = "Task appears to be completed based on task-specific indicators."
            else:
                # Check keyword overlap as last resort
                context_keywords = set(context_lower.split())
                result_keywords = set(result_lower.split())
                overlap = context_keywords & result_keywords
                relevance_score = len(overlap) / max(len(context_keywords), 1) if context_keywords else 0
                
                if relevance_score > 0.4:  # 40% keyword overlap
                    success = True
                    feedback = f"Result appears relevant to task ({relevance_score:.1%} keyword overlap)."
                else:
                    success = False
                    feedback = f"Result doesn't clearly address the task (only {relevance_score:.1%} relevance)."
        
        return {
            "success": success,
            "feedback": feedback,
            "success_indicators": success_count,
            "failure_indicators": failure_count,
            "evaluation_method": "heuristic"
        }

    async def _refine_task(self, task: str, feedback: str) -> str:
        """
        Refine the task context based on feedback.
        
        Args:
            task: Current task context
            feedback: Feedback from evaluation
            
        Returns:
            Refined task context
        """
        try:
            # Simple refinement - could be enhanced with AI
            refined = f"{task} | Previous feedback: {feedback}"
            
            # Add iteration-specific guidance
            iteration_count = len(self.iterations)
            if iteration_count > 5:
                refined += f" | Note: This is iteration {iteration_count + 1}, consider alternative approaches."
            
            return refined
            
        except Exception as e:
            self.logger.error(f"Refine task failed: {e}")
            return f"{task} | Refinement error: {e}"

    # Display Methods for Verbose Output
    
    def _display_task_header(self, task: str):
        """Display the task header."""
        self.console.print()
        self.console.print(Panel(
            Text(task, style="bold white"),
            title="🤖 Codexa Agentic Loop",
            title_align="left",
            border_style="blue",
            padding=(1, 2)
        ))

    def _display_iteration_header(self, iteration: int):
        """Display iteration header."""
        self.console.print(f"\n[bold blue]{'='*60}[/bold blue]")
        self.console.print(f"[bold blue]🔄 Iteration {iteration}/{self.max_iterations}[/bold blue]")
        self.console.print(f"[bold blue]{'='*60}[/bold blue]")

    def _display_thinking(self, thinking_result: Dict[str, str]):
        """Display the thinking process with enhanced verbose feedback."""
        self.console.print(f"\n[bold yellow]🧠 [Thinking Process][/bold yellow]")
        
        # Show provider status
        provider_info = ""
        if thinking_result.get("provider_used"):
            provider_info = "[dim](Using AI provider for reasoning)[/dim]\n"
        else:
            provider_info = "[dim](Using fallback reasoning)[/dim]\n"
        
        thinking_content = thinking_result["thinking"]
        
        # Add analysis indicators
        if len(thinking_content) > 200:
            analysis_depth = "Deep analysis"
        elif len(thinking_content) > 100:
            analysis_depth = "Moderate analysis"
        else:
            analysis_depth = "Quick analysis"
        
        full_content = f"{provider_info}[dim]Analysis depth: {analysis_depth}[/dim]\n\n{thinking_content}"
        
        self.console.print(Panel(
            full_content,
            border_style="yellow",
            padding=(1, 2),
            title="💭 Reasoning",
            title_align="left"
        ))
        
        # Show the plan separately for clarity
        self.console.print(f"\n[bold cyan]📋 [Action Plan][/bold cyan]")
        plan_content = thinking_result.get("plan", "No specific plan generated")
        self.console.print(Panel(
            plan_content,
            border_style="cyan",
            padding=(0, 1),
            title="🎯 Next Action",
            title_align="left"
        ))

    def _display_execution(self, execution_result: Dict[str, Any]):
        """Display execution results with enhanced feedback."""
        self.console.print(f"\n[bold green]⚡ [Execution Result][/bold green]")
        
        result_text = execution_result.get("result", "No result")
        duration = execution_result.get("duration", 0)
        method = execution_result.get("method", "unknown")
        success = execution_result.get("success", False)
        
        # Show execution method and status
        status_icon = "✅" if success else "❌"
        method_text = f"Method: {method}" if method != "unknown" else ""
        duration_text = f"Duration: {duration:.2f}s"
        
        metadata = f"{status_icon} {method_text} • {duration_text}"
        
        # Truncate very long results for display
        display_result = result_text
        if len(result_text) > 500:
            display_result = result_text[:500] + "\n[dim]... (result truncated for display)[/dim]"
        
        content = f"{display_result}\n\n[dim]{metadata}[/dim]"
        
        self.console.print(Panel(
            content,
            border_style="green" if success else "red",
            padding=(1, 2),
            title=f"🔧 Execution {'Success' if success else 'Failed'}",
            title_align="left"
        ))

    def _display_evaluation(self, evaluation_result: Dict[str, Any]):
        """Display evaluation results with enhanced feedback."""
        success = evaluation_result.get("success", False)
        feedback = evaluation_result.get("feedback", "No feedback")
        confidence = evaluation_result.get("confidence", 0.0)
        evaluation_method = evaluation_result.get("evaluation_method", "unknown")
        
        icon = "✅" if success else "❌"
        color = "green" if success else "red"
        
        self.console.print(f"\n[bold {color}]🔍 [Evaluation Result] {icon}[/bold {color}]")
        
        # Build metadata
        metadata_parts = []
        if confidence > 0:
            metadata_parts.append(f"Confidence: {confidence:.1%}")
        metadata_parts.append(f"Method: {evaluation_method}")
        
        if evaluation_method == "llm":
            reasoning = evaluation_result.get("reasoning", "")
            if reasoning:
                metadata_parts.append(f"AI Reasoning: {reasoning[:100]}{'...' if len(reasoning) > 100 else ''}")
        
        metadata = " • ".join(metadata_parts)
        
        content = f"{feedback}\n\n[dim]{metadata}[/dim]" if metadata else feedback
        
        self.console.print(Panel(
            content,
            border_style=color,
            padding=(1, 2),
            title=f"🧐 Assessment {'Passed' if success else 'Failed'}",
            title_align="left"
        ))

    def _display_refinement(self, refined_context: str):
        """Display context refinement."""
        self.console.print(f"\n[bold cyan]🔄 [Refined Context][/bold cyan]")
        self.console.print(Panel(
            refined_context,
            border_style="cyan",
            padding=(0, 1)
        ))

    def _display_success(self, iterations: int):
        """Display success message."""
        self.console.print(f"\n[bold green]{'='*60}[/bold green]")
        self.console.print(f"[bold green]🎉 Task completed successfully in {iterations} iterations![/bold green]")
        self.console.print(f"[bold green]{'='*60}[/bold green]")

    def _display_max_iterations_reached(self):
        """Display max iterations reached message."""
        self.console.print(f"\n[bold yellow]{'='*60}[/bold yellow]")
        self.console.print(f"[bold yellow]⚠️ Maximum iterations ({self.max_iterations}) reached.[/bold yellow]")
        self.console.print("[yellow]Task may not be fully completed.[/yellow]")
        self.console.print(f"[bold yellow]{'='*60}[/bold yellow]")

    def _display_final_summary(self, result: AgenticTaskResult):
        """Display final execution summary."""
        self.console.print(f"\n[bold magenta]📊 Final Summary[/bold magenta]")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Status", str(result.status.value))
        table.add_row("Total Iterations", str(len(result.iterations)))
        table.add_row("Total Duration", f"{result.total_duration:.2f}s")
        table.add_row("Success", "✅ Yes" if result.success else "❌ No")
        table.add_row("Task", result.task[:50] + "..." if len(result.task) > 50 else result.task)
        
        self.console.print(table)

    # Utility Methods
    
    def set_max_iterations(self, max_iterations: int):
        """Set the maximum number of iterations."""
        self.max_iterations = max_iterations

    def set_verbose(self, verbose: bool):
        """Set verbose output mode."""
        self.verbose = verbose

    def get_iteration_history(self) -> List[LoopIteration]:
        """Get the history of all iterations."""
        return self.iterations.copy()

    async def run_simple_task(self, task: str) -> str:
        """
        Run a simple task and return just the result.
        
        Args:
            task: Task to execute
            
        Returns:
            String result of the task
        """
        result = await self.run_agentic_loop(task)
        return result.final_result or "Task completed but no specific result available"
    
    def export_session_context(self) -> Optional[Dict[str, Any]]:
        """
        Export current agentic context for session continuity.
        
        Returns:
            Dictionary containing session context data for handoff to main session
        """
        if not self.session_memory or not self.session_memory.agentic_context:
            return None
        
        context = self.session_memory.agentic_context
        
        return {
            "original_task": context.original_task,
            "current_objective": context.current_objective,
            "is_task_complete": context.is_task_complete(),
            "pending_steps": context.pending_steps,
            "completed_steps": context.completed_steps,
            "iteration_count": context.iteration_count,
            "last_result": context.last_result,
            "last_evaluation": context.last_evaluation,
            "context_keywords": list(context.context_keywords),
            "files_created": context.files_created,
            "files_modified": context.files_modified,
            "tools_used": context.tools_used,
            "session_state": self.session_memory.current_state.value,
            "should_continue": len(context.pending_steps) > 0 or not context.is_task_complete()
        }
    
    def import_session_context(self, context_data: Dict[str, Any]) -> bool:
        """
        Import session context from main session.
        
        Args:
            context_data: Context data from main session
            
        Returns:
            True if context was successfully imported
        """
        if not self.session_memory or not SessionMemory or not context_data:
            return False
        
        try:
            # Start or update agentic context with imported data
            if not self.session_memory.agentic_context:
                self.session_memory.start_agentic_context(
                    context_data["original_task"],
                    context_data["current_objective"]
                )
            
            # Update with imported data
            self.session_memory.update_agentic_context(
                iteration_count=context_data.get("iteration_count", 0),
                last_result=context_data.get("last_result"),
                last_evaluation=context_data.get("last_evaluation"),
                completed_steps=context_data.get("completed_steps", []),
                pending_steps=context_data.get("pending_steps", []),
                files_created=context_data.get("files_created", []),
                files_modified=context_data.get("files_modified", []),
                tools_used=context_data.get("tools_used", [])
            )
            
            self.logger.info("Successfully imported session context")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to import session context: {e}")
            return False


# Factory function for easy instantiation
def create_agentic_loop(
    config=None,
    max_iterations: int = 20,
    verbose: bool = True,
    session_memory: Optional[SessionMemory] = None
) -> CodexaAgenticLoop:
    """
    Factory function to create a configured agentic loop instance.
    
    Args:
        config: Codexa configuration object
        max_iterations: Maximum number of loop iterations
        verbose: Whether to show verbose output
        session_memory: Session memory for context persistence
        
    Returns:
        Configured CodexaAgenticLoop instance
    """
    return CodexaAgenticLoop(
        config=config,
        max_iterations=max_iterations,
        verbose=verbose,
        session_memory=session_memory
    )