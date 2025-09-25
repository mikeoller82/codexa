#!/usr/bin/env python3
"""
GUI launcher for Codexa.
This script provides an easy way to launch the Codexa GUI interface.
"""

import sys
import os
from pathlib import Path

def main():
    """Launch the Codexa GUI."""
    # Add the current directory to Python path
    current_dir = Path(__file__).parent
    sys.path.insert(0, str(current_dir))

    try:
        # Import and launch the GUI
        from codexa_gui import main as gui_main
        gui_main()
    except ImportError as e:
        print(f"Error importing GUI: {e}")
        print("Make sure you're running this from the codexa directory.")
        sys.exit(1)
    except Exception as e:
        print(f"Error launching GUI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()