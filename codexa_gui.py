#!/usr/bin/env python3
"""
GUI interface for Codexa AI Coding Assistant.
Provides a graphical user interface for the Codexa CLI application.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import queue
import sys
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

# Add the codexa module to path
sys.path.insert(0, str(Path(__file__).parent))

from codexa.cli import app
from codexa.config import Config
from codexa.core import CodexaAgent
try:
    from codexa.enhanced_core import EnhancedCodexaAgent
    ENHANCED_AVAILABLE = True
except ImportError:
    ENHANCED_AVAILABLE = False

class CodexaGUI:
    """Main GUI application for Codexa."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Codexa - AI Coding Assistant")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)

        # Initialize components
        self.config = None
        self.agent = None
        self.session_active = False
        self.output_queue = queue.Queue()
        self.current_directory = os.getcwd()

        # Setup GUI components
        self.setup_ui()
        self.setup_styles()

        # Check configuration on startup
        self.check_configuration()

        # Start output processing
        self.process_output_queue()

    def setup_ui(self):
        """Setup the main UI components."""
        # Create main menu
        self.create_menu()

        # Create main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # Header section
        self.create_header(main_frame)

        # Status bar
        self.create_status_bar(main_frame)

        # Main content area (notebook with tabs)
        self.create_main_content(main_frame)

    def create_menu(self):
        """Create the application menu."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Project", command=self.new_project)
        file_menu.add_command(label="Open Project", command=self.open_project)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Session menu
        session_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Session", menu=session_menu)
        session_menu.add_command(label="Start Session", command=self.start_session)
        session_menu.add_command(label="End Session", command=self.end_session)
        session_menu.add_separator()
        session_menu.add_command(label="Clear Output", command=self.clear_output)

        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Configuration", command=self.show_config)
        settings_menu.add_command(label="Setup API Keys", command=self.setup_api_keys)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Commands", command=self.show_help)
        help_menu.add_command(label="About", command=self.show_about)

    def create_header(self, parent):
        """Create the header section."""
        header_frame = ttk.Frame(parent)
        header_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # Title
        title_label = ttk.Label(
            header_frame,
            text="🤖 Codexa - AI Coding Assistant",
            font=('Arial', 16, 'bold')
        )
        title_label.pack(side=tk.LEFT)

        # Current directory
        self.dir_label = ttk.Label(
            header_frame,
            text=f"📁 {self.current_directory}",
            font=('Arial', 10)
        )
        self.dir_label.pack(side=tk.RIGHT)

    def create_status_bar(self, parent):
        """Create the status bar."""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # Status indicators
        self.status_label = ttk.Label(status_frame, text="🔴 Not Configured", relief=tk.SUNKEN)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Provider info
        self.provider_label = ttk.Label(status_frame, text="Provider: None", relief=tk.SUNKEN)
        self.provider_label.pack(side=tk.RIGHT, padx=(5, 0))

    def create_main_content(self, parent):
        """Create the main content area with tabs."""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(parent)
        self.notebook.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Chat tab
        self.create_chat_tab()

        # Tasks tab
        self.create_tasks_tab()

        # Files tab
        self.create_files_tab()

        # Settings tab
        self.create_settings_tab()

    def create_chat_tab(self):
        """Create the chat interface tab."""
        chat_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(chat_frame, text="💬 Chat")

        # Configure grid weights
        chat_frame.columnconfigure(0, weight=1)
        chat_frame.rowconfigure(1, weight=1)

        # Output area
        output_label = ttk.Label(chat_frame, text="Output:", font=('Arial', 10, 'bold'))
        output_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))

        self.output_text = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            height=15,
            font=('Consolas', 10)
        )
        self.output_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        # Input area
        input_label = ttk.Label(chat_frame, text="Input:", font=('Arial', 10, 'bold'))
        input_label.grid(row=2, column=0, sticky=tk.W, pady=(0, 5))

        input_frame = ttk.Frame(chat_frame)
        input_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))
        input_frame.columnconfigure(0, weight=1)

        self.input_entry = ttk.Entry(input_frame, font=('Arial', 11))
        self.input_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))

        self.send_button = ttk.Button(input_frame, text="Send", command=self.send_input)
        self.send_button.grid(row=0, column=1)

        # Quick commands
        commands_frame = ttk.LabelFrame(chat_frame, text="Quick Commands", padding="5")
        commands_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

        quick_commands = [
            ("/help", "Show help"),
            ("/status", "Show status"),
            ("/workflow", "Start workflow"),
            ("/tasks", "Show tasks"),
            ("/reset", "Reset session")
        ]

        for i, (cmd, desc) in enumerate(quick_commands):
            btn = ttk.Button(
                commands_frame,
                text=cmd,
                command=lambda c=cmd: self.quick_command(c),
                width=15
            )
            btn.grid(row=i//3, column=i%3, padx=2, pady=2, sticky=tk.W)

        # Bind Enter key to send
        self.input_entry.bind('<Return>', lambda e: self.send_input())

    def create_tasks_tab(self):
        """Create the tasks management tab."""
        tasks_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tasks_frame, text="📋 Tasks")

        # Task list
        tasks_label = ttk.Label(tasks_frame, text="Current Tasks:", font=('Arial', 12, 'bold'))
        tasks_label.pack(anchor=tk.W, pady=(0, 10))

        self.tasks_text = scrolledtext.ScrolledText(
            tasks_frame,
            wrap=tk.WORD,
            height=20,
            font=('Consolas', 10)
        )
        self.tasks_text.pack(fill=tk.BOTH, expand=True)

        # Task controls
        task_controls = ttk.Frame(tasks_frame)
        task_controls.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(task_controls, text="Refresh Tasks", command=self.refresh_tasks).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(task_controls, text="Next Task", command=self.next_task).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(task_controls, text="Complete Task", command=self.complete_task).pack(side=tk.LEFT)

    def create_files_tab(self):
        """Create the files management tab."""
        files_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(files_frame, text="📁 Files")

        # File browser
        browser_label = ttk.Label(files_frame, text="Project Files:", font=('Arial', 12, 'bold'))
        browser_label.pack(anchor=tk.W, pady=(0, 10))

        # File list
        self.file_tree = ttk.Treeview(files_frame, columns=('Type', 'Size'), height=15)
        self.file_tree.heading('#0', text='Name')
        self.file_tree.heading('Type', text='Type')
        self.file_tree.heading('Size', text='Size')
        self.file_tree.column('#0', width=200)
        self.file_tree.column('Type', width=100)
        self.file_tree.column('Size', width=100)

        file_scrollbar = ttk.Scrollbar(files_frame, orient=tk.VERTICAL, command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=file_scrollbar.set)

        self.file_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        file_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # File controls
        file_controls = ttk.Frame(files_frame)
        file_controls.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(file_controls, text="Refresh", command=self.refresh_files).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(file_controls, text="Open File", command=self.open_file).pack(side=tk.LEFT)

    def create_settings_tab(self):
        """Create the settings tab."""
        settings_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(settings_frame, text="⚙️ Settings")

        # Configuration display
        config_label = ttk.Label(settings_frame, text="Configuration:", font=('Arial', 12, 'bold'))
        config_label.pack(anchor=tk.W, pady=(0, 10))

        self.config_text = scrolledtext.ScrolledText(
            settings_frame,
            wrap=tk.WORD,
            height=15,
            font=('Consolas', 10)
        )
        self.config_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Settings controls
        settings_controls = ttk.Frame(settings_frame)
        settings_controls.pack(fill=tk.X)

        ttk.Button(settings_controls, text="Setup API Keys", command=self.setup_api_keys).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(settings_controls, text="Refresh Config", command=self.refresh_config).pack(side=tk.LEFT)

    def setup_styles(self):
        """Setup custom styles for the GUI."""
        style = ttk.Style()

        # Configure styles
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'))
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'))

    def check_configuration(self):
        """Check if Codexa is properly configured."""
        try:
            self.config = Config()

            if self.config.has_valid_config():
                self.status_label.config(text="🟢 Configured")
                provider = self.config.get_provider()
                self.provider_label.config(text=f"Provider: {provider}")

                # Initialize agent
                if ENHANCED_AVAILABLE:
                    self.agent = EnhancedCodexaAgent()
                else:
                    self.agent = CodexaAgent()

                self.update_config_display()
                self.refresh_files()

            else:
                self.status_label.config(text="🔴 Not Configured")
                messagebox.showwarning(
                    "Configuration Required",
                    "Codexa needs to be configured before use.\n\nPlease set up your API keys in the Settings tab."
                )

        except Exception as e:
            self.status_label.config(text="🔴 Error")
            self.add_output(f"Error checking configuration: {e}")

    def start_session(self):
        """Start a new Codexa session."""
        if not self.config or not self.config.has_valid_config():
            messagebox.showwarning("Configuration Required", "Please configure API keys first.")
            return

        if self.session_active:
            messagebox.showinfo("Session Active", "A session is already active.")
            return

        try:
            self.session_active = True
            self.add_output("🚀 Starting Codexa session...\n")
            self.add_output(f"📁 Project: {self.current_directory}")
            self.add_output(f"🤖 Provider: {self.config.get_provider()}")
            self.add_output("\n💬 You can now interact with Codexa using the chat interface.\n")
            self.add_output("Type 'help' for available commands or 'exit' to end the session.\n")
            self.status_label.config(text="🟢 Session Active")

        except Exception as e:
            self.session_active = False
            self.add_output(f"❌ Error starting session: {e}")
            messagebox.showerror("Session Error", f"Failed to start session: {e}")

    def end_session(self):
        """End the current session."""
        if not self.session_active:
            messagebox.showinfo("No Session", "No active session to end.")
            return

        self.session_active = False
        self.add_output("\n👋 Session ended. Thanks for using Codexa!\n")
        self.status_label.config(text="🟡 Configured")

    def send_input(self):
        """Send user input to Codexa."""
        if not self.session_active:
            messagebox.showwarning("No Session", "Please start a session first.")
            return

        user_input = self.input_entry.get().strip()
        if not user_input:
            return

        # Clear input field
        self.input_entry.delete(0, tk.END)

        # Add user input to output
        self.add_output(f"\n👤 You: {user_input}\n")

        # Process input in separate thread
        threading.Thread(target=self.process_input, args=(user_input,), daemon=True).start()

    def process_input(self, user_input: str):
        """Process user input using Codexa agent."""
        try:
            if user_input.lower() in ["exit", "quit", "bye"]:
                self.root.after(0, self.end_session)
                return

            # Handle special commands
            if user_input.startswith("/"):
                response = self.handle_command(user_input)
            else:
                # Handle natural language request
                response = self.agent.provider.ask(
                    prompt=user_input,
                    history=[],
                    context=self.get_project_context()
                )

            self.add_output(f"\n🤖 Codexa: {response}\n")

        except Exception as e:
            error_msg = f"❌ Error processing input: {e}"
            self.add_output(f"\n{error_msg}\n")

    def handle_command(self, command: str) -> str:
        """Handle special commands."""
        cmd = command[1:].lower()

        if cmd == "help":
            return """Available Commands:
/help - Show this help message
/status - Show session status
/tasks - Show current tasks
/workflow - Start planning workflow
/reset - Reset conversation
/exit - End session"""

        elif cmd == "status":
            return f"""Session Status:
- Status: {'Active' if self.session_active else 'Inactive'}
- Directory: {self.current_directory}
- Provider: {self.config.get_provider() if self.config else 'None'}"""

        elif cmd == "tasks":
            if hasattr(self.agent, 'execution_manager') and self.agent.execution_manager.has_tasks():
                return "Tasks are available. Check the Tasks tab for details."
            else:
                return "No tasks available."

        elif cmd == "workflow":
            return "Workflow functionality is available. Use natural language to describe what you want to build."

        elif cmd == "reset":
            return "Conversation reset functionality available in CLI mode."

        else:
            return f"Unknown command: {command}. Type /help for available commands."

    def quick_command(self, command: str):
        """Execute a quick command."""
        self.input_entry.delete(0, tk.END)
        self.input_entry.insert(0, command)
        self.send_input()

    def add_output(self, text: str):
        """Add text to the output area."""
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)

    def clear_output(self):
        """Clear the output area."""
        self.output_text.delete(1.0, tk.END)

    def get_project_context(self) -> str:
        """Get project context for Codexa."""
        context = f"Current Directory: {self.current_directory}\n"

        # Add CODEXA.md content if available
        codexa_md = Path(self.current_directory) / "CODEXA.md"
        if codexa_md.exists():
            with open(codexa_md, 'r', encoding='utf-8') as f:
                context += f"\nProject Guidelines:\n{f.read()}"

        return context

    def new_project(self):
        """Create a new project."""
        directory = filedialog.askdirectory(title="Select Project Directory")
        if directory:
            self.current_directory = directory
            self.dir_label.config(text=f"📁 {directory}")
            os.chdir(directory)
            self.refresh_files()
            self.add_output(f"📁 Changed to directory: {directory}\n")

    def open_project(self):
        """Open an existing project."""
        directory = filedialog.askdirectory(title="Select Project Directory")
        if directory:
            self.current_directory = directory
            self.dir_label.config(text=f"📁 {directory}")
            os.chdir(directory)
            self.refresh_files()
            self.add_output(f"📁 Opened project: {directory}\n")

    def show_config(self):
        """Show configuration dialog."""
        self.notebook.select(3)  # Switch to settings tab

    def setup_api_keys(self):
        """Show API key setup dialog."""
        dialog = APIKeyDialog(self.root)
        self.root.wait_window(dialog.dialog)
        self.check_configuration()  # Refresh configuration

    def show_help(self):
        """Show help dialog."""
        help_text = """Codexa GUI - AI Coding Assistant

🚀 Getting Started:
1. Set up your API keys in the Settings tab
2. Click 'Start Session' to begin
3. Type your requests naturally or use commands

💬 Chat Interface:
- Natural language: "Build a React app with auth"
- Commands: /help, /status, /tasks, /workflow
- Type 'exit' to end the session

📋 Tasks Tab:
- View and manage project tasks
- Track progress and completion

📁 Files Tab:
- Browse project files
- Quick file access

⚙️ Settings Tab:
- Configure API keys
- View current configuration

🔧 Requirements:
- Python 3.7+
- API key from OpenAI, Anthropic, or OpenRouter
- Internet connection for AI services"""

        messagebox.showinfo("Codexa GUI Help", help_text)

    def show_about(self):
        """Show about dialog."""
        about_text = """Codexa GUI v1.0

A graphical user interface for Codexa AI Coding Assistant.

Codexa helps you build software faster with AI-powered:
• Code generation and editing
• Project planning and workflows
• Task management and execution
• Multi-provider AI support

Created with ❤️ using Python and Tkinter"""

        messagebox.showinfo("About Codexa GUI", about_text)

    def refresh_tasks(self):
        """Refresh the tasks display."""
        if hasattr(self.agent, 'execution_manager'):
            tasks = self.agent.execution_manager.get_all_tasks()
            self.tasks_text.delete(1.0, tk.END)

            if tasks:
                for task in tasks:
                    status = "✅" if task.get('completed', False) else "⏳"
                    self.tasks_text.insert(tk.END, f"{status} {task.get('text', 'No description')}\n")
            else:
                self.tasks_text.insert(tk.END, "No tasks available.")

    def next_task(self):
        """Start the next task."""
        if hasattr(self.agent, 'execution_manager'):
            # This would integrate with the task execution system
            self.add_output("📋 Next task functionality would integrate with Codexa's task system.\n")

    def complete_task(self):
        """Complete the current task."""
        if hasattr(self.agent, 'execution_manager'):
            # This would integrate with the task completion system
            self.add_output("✅ Task completion functionality would integrate with Codexa's task system.\n")

    def refresh_files(self):
        """Refresh the file browser."""
        self.file_tree.delete(*self.file_tree.get_children())

        try:
            for item in Path(self.current_directory).iterdir():
                if not item.name.startswith('.'):
                    file_type = "Directory" if item.is_dir() else "File"
                    size = f"{item.stat().st_size} bytes" if item.is_file() else "-"

                    self.file_tree.insert('', 'end', text=item.name,
                                        values=(file_type, size))
        except Exception as e:
            self.add_output(f"❌ Error refreshing files: {e}\n")

    def open_file(self):
        """Open selected file."""
        selection = self.file_tree.selection()
        if selection:
            file_name = self.file_tree.item(selection[0])['text']
            file_path = Path(self.current_directory) / file_name

            if file_path.is_file():
                # Simple file viewer (could be enhanced)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Create a simple file viewer window
                    viewer = tk.Toplevel(self.root)
                    viewer.title(f"File: {file_name}")
                    viewer.geometry("600x400")

                    text_widget = scrolledtext.ScrolledText(viewer, wrap=tk.WORD)
                    text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                    text_widget.insert(1.0, content)
                    text_widget.config(state=tk.DISABLED)

                except Exception as e:
                    messagebox.showerror("Error", f"Could not open file: {e}")

    def update_config_display(self):
        """Update the configuration display."""
        if self.config:
            config_info = f"""Current Configuration:
Provider: {self.config.get_provider()}
Model: {self.config.get_model()}

API Key Status:
OpenAI: {'✅ Configured' if self.config.openai_api_key else '❌ Not Set'}
Anthropic: {'✅ Configured' if self.config.anthropic_api_key else '❌ Not Set'}
OpenRouter: {'✅ Configured' if self.config.openrouter_api_key else '❌ Not Set'}

Config File: {Path.home() / '.codexarc'}
"""
            self.config_text.delete(1.0, tk.END)
            self.config_text.insert(1.0, config_info)

    def refresh_config(self):
        """Refresh configuration display."""
        self.check_configuration()

    def process_output_queue(self):
        """Process messages from the output queue."""
        try:
            while True:
                message = self.output_queue.get_nowait()
                self.add_output(message)
        except queue.Empty:
            pass

        # Schedule next check
        self.root.after(100, self.process_output_queue)


class APIKeyDialog:
    """Dialog for setting up API keys."""

    def __init__(self, parent):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Setup API Keys")
        self.dialog.geometry("500x400")
        self.dialog.resizable(False, False)

        # Make dialog modal
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (400 // 2)
        self.dialog.geometry(f"500x400+{x}+{y}")

        self.setup_ui()

    def setup_ui(self):
        """Setup the API key dialog UI."""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(
            main_frame,
            text="🔑 API Key Setup",
            font=('Arial', 16, 'bold')
        )
        title_label.pack(pady=(0, 20))

        # Instructions
        instructions = """Codexa needs an AI provider API key to function.
Please enter your API key for one of the supported providers:

📝 Get API Keys:
• OpenAI: https://platform.openai.com/api-keys
• Anthropic: https://console.anthropic.com/
• OpenRouter: https://openrouter.ai/keys"""

        inst_label = ttk.Label(main_frame, text=instructions, justify=tk.LEFT)
        inst_label.pack(pady=(0, 20), anchor=tk.W)

        # API key entries
        self.openai_var = tk.StringVar()
        self.anthropic_var = tk.StringVar()
        self.openrouter_var = tk.StringVar()

        # OpenAI
        openai_frame = ttk.Frame(main_frame)
        openai_frame.pack(fill=tk.X, pady=5)
        ttk.Label(openai_frame, text="OpenAI API Key:", width=20).pack(side=tk.LEFT)
        ttk.Entry(openai_frame, textvariable=self.openai_var, show="*", width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Anthropic
        anthropic_frame = ttk.Frame(main_frame)
        anthropic_frame.pack(fill=tk.X, pady=5)
        ttk.Label(anthropic_frame, text="Anthropic API Key:", width=20).pack(side=tk.LEFT)
        ttk.Entry(anthropic_frame, textvariable=self.anthropic_var, show="*", width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # OpenRouter
        openrouter_frame = ttk.Frame(main_frame)
        openrouter_frame.pack(fill=tk.X, pady=5)
        ttk.Label(openrouter_frame, text="OpenRouter API Key:", width=20).pack(side=tk.LEFT)
        ttk.Entry(openrouter_frame, textvariable=self.openrouter_var, show="*", width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Environment variables info
        env_info = """💡 Tip: You can also set API keys using environment variables:
export OPENAI_API_KEY='your-key'
export ANTHROPIC_API_KEY='your-key'
export OPENROUTER_API_KEY='your-key'"""

        env_label = ttk.Label(main_frame, text=env_info, justify=tk.LEFT, font=('Arial', 9))
        env_label.pack(pady=(20, 0), anchor=tk.W)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))

        ttk.Button(button_frame, text="Save Keys", command=self.save_keys).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.RIGHT)

    def save_keys(self):
        """Save the API keys."""
        try:
            # Create or update .env file
            env_path = Path.cwd() / ".env"
            env_content = []

            if env_path.exists():
                with open(env_path, 'r') as f:
                    for line in f:
                        if not line.startswith(('OPENAI_API_KEY=', 'ANTHROPIC_API_KEY=', 'OPENROUTER_API_KEY=')):
                            env_content.append(line)

            # Add new keys
            if self.openai_var.get():
                env_content.append(f"OPENAI_API_KEY={self.openai_var.get()}")
            if self.anthropic_var.get():
                env_content.append(f"ANTHROPIC_API_KEY={self.anthropic_var.get()}")
            if self.openrouter_var.get():
                env_content.append(f"OPENROUTER_API_KEY={self.openrouter_var.get()}")

            # Write .env file
            with open(env_path, 'w') as f:
                f.write('\n'.join(env_content))

            messagebox.showinfo("Success", "API keys saved to .env file\n\nPlease restart the application for changes to take effect.")
            self.dialog.destroy()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save API keys: {e}")


def main():
    """Main entry point for the GUI application."""
    root = tk.Tk()
    app = CodexaGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()