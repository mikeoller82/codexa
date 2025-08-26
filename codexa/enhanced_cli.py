"""
Enhanced CLI entry point for Codexa with Phase 2 features.
"""

import asyncio
import sys
import logging
from pathlib import Path

from .enhanced_core import EnhancedCodexaAgent


def main():
    """Main entry point for enhanced Codexa CLI."""
    try:
        # Create and run enhanced agent
        agent = EnhancedCodexaAgent()
        
        # Run the async session
        asyncio.run(agent.start_session())
        
    except KeyboardInterrupt:
        print("\n👋 Session interrupted. Goodbye!")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()