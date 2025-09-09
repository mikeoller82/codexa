"""
Centralized system prompt management for Codexa Agent.
"""

import os
from pathlib import Path
from typing import Optional
from datetime import datetime

# Get the system prompt from the docs directory
DOCS_DIR = Path(__file__).parent.parent / "docs"
SYSTEM_PROMPT_FILE = DOCS_DIR / "codexa-agent-prompt.txt"


def get_codexa_system_prompt(context: Optional[str] = None) -> str:
    """
    Get the main Codexa Agent system prompt.
    
    Args:
        context: Optional project context to append
        
    Returns:
        The complete system prompt for Codexa Agent
    """
    try:
        # Read the system prompt from the file
        if SYSTEM_PROMPT_FILE.exists():
            with open(SYSTEM_PROMPT_FILE, 'r', encoding='utf-8') as f:
                base_prompt = f.read()
        else:
            # Fallback system prompt if file not found
            base_prompt = get_fallback_system_prompt()
        
        # Replace placeholder date with current date
        current_date = datetime.now().strftime("%Y-%m-%d")
        base_prompt = base_prompt.replace("1848-15-03", current_date)
        
        # Add project context if provided
        if context:
            # Find the insertion point for project context
            # Look for "Additional user rules:" section
            if "Additional user rules:" in base_prompt:
                context_section = f"""
# Project Context
{context}

"""
                base_prompt = base_prompt.replace("Additional user rules:", f"{context_section}Additional user rules:")
            else:
                # Fallback: add at the end before final instructions
                context_section = f"""

# Project Context
{context}
"""
                base_prompt += context_section
        
        return base_prompt.strip()
        
    except Exception as e:
        # Fallback in case of any errors
        print(f"Warning: Could not load system prompt from file: {e}")
        return get_fallback_system_prompt(context)


def get_fallback_system_prompt(context: Optional[str] = None) -> str:
    """
    Fallback system prompt if the main file cannot be loaded.
    
    Args:
        context: Optional project context
        
    Returns:
        Basic Codexa system prompt
    """
    base_prompt = """# Role
You are Codexa Agent developed by Codexa Code, an agentic coding AI assistant with access to the developer's codebase through Codexa's world-leading context engine and integrations.
You can read from and write to the codebase using the provided tools.

# Identity  
You are Codexa Agent developed by Codexa Code, an agentic coding AI assistant based on various CLI coding agents, with access to the developer's codebase through Codexa's context engine and integrations.

# Core Principles
- Focus on doing what the user asks you to do
- Do NOT do more than the user asked - if you think there is a clear follow-up task, ASK the user
- Be conservative with potentially damaging actions
- Always use package managers for dependency management
- Test your code implementations and iterate until tests pass
- When showing code, wrap it in <Codexa_code_snippet> XML tags with path and mode attributes

# Making Edits
When making edits:
- Always gather detailed information about the code before making changes
- Be very conservative and respect the existing codebase
- Use appropriate tools for file operations
- Consider the impact of changes on the broader system

# Testing
You are very good at writing unit tests and making them work. If you write code, suggest to the user to test the code by writing tests and running them.
You often mess up initial implementations, but you work diligently on iterating on tests until they pass, usually resulting in a much better outcome.

Answer the user's request using at most one relevant tool, if available. Check that all required parameters for each tool call are provided or can reasonably be inferred from context."""

    if context:
        base_prompt += f"""

# Project Context
{context}"""

    return base_prompt


def validate_system_prompt() -> bool:
    """
    Validate that the system prompt file exists and is readable.
    
    Returns:
        True if the system prompt file is valid, False otherwise
    """
    try:
        if not SYSTEM_PROMPT_FILE.exists():
            return False
            
        with open(SYSTEM_PROMPT_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Basic validation - check for key sections
        required_sections = ["# Role", "# Identity", "# Making edits", "# Testing"]
        return all(section in content for section in required_sections)
        
    except Exception:
        return False


# For debugging and testing
if __name__ == "__main__":
    print("=== Codexa System Prompt ===")
    print(get_codexa_system_prompt())
    print("\n=== Validation ===")
    print(f"System prompt file exists: {SYSTEM_PROMPT_FILE.exists()}")
    print(f"System prompt is valid: {validate_system_prompt()}")