"""
ASCII Logo Tool for Codexa.
"""

from typing import Set
import asyncio

from ..base.tool_interface import Tool, ToolResult, ToolContext


class ASCIILogoTool(Tool):
    """Tool for displaying ASCII art logos and branding."""
    
    @property
    def name(self) -> str:
        return "ascii_logo"
    
    @property
    def description(self) -> str:
        return "Display ASCII art logos and branding with theme support"
    
    @property
    def category(self) -> str:
        return "enhanced"
    
    @property
    def capabilities(self) -> Set[str]:
        return {"ascii_art", "branding", "theming", "display"}
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the request."""
        request_lower = request.lower()
        
        # High confidence for explicit logo requests
        if any(phrase in request_lower for phrase in [
            "show logo", "display logo", "ascii logo", "ascii art",
            "branding", "startup logo", "codexa logo"
        ]):
            return 0.9
        
        # Medium confidence for visual/display requests
        if any(word in request_lower for word in ["logo", "ascii", "art", "banner"]):
            return 0.6
        
        return 0.0
    
    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute ASCII logo display."""
        try:
            # Get parameters from context
            theme_name = context.get_state("theme", "default")
            interactive = context.get_state("interactive", True)
            
            # Check if feature is enabled
            if context.config and not context.config.is_feature_enabled("ascii_logo"):
                return ToolResult.success_result(
                    data={"message": "ASCII logo feature is disabled"},
                    tool_name=self.name,
                    output="ASCII logo feature is disabled in configuration"
                )
            
            # Display logo
            logo_output = await self._display_logo(theme_name, interactive, context)
            
            return ToolResult.success_result(
                data={
                    "theme": theme_name,
                    "interactive": interactive,
                    "logo_displayed": True
                },
                tool_name=self.name,
                output=logo_output
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Failed to display ASCII logo: {str(e)}",
                tool_name=self.name
            )
    
    async def _display_logo(self, theme_name: str, interactive: bool, context: ToolContext) -> str:
        """Display the ASCII logo."""
        try:
            # Try to use existing display system
            if hasattr(context, 'config') and context.config:
                from ...display.ascii_art import ASCIIArtRenderer, LogoTheme
                from ...display.animations import StartupAnimation
                
                # Create renderer
                renderer = ASCIIArtRenderer()
                
                # Get theme
                try:
                    theme = LogoTheme(theme_name.lower())
                except ValueError:
                    theme = LogoTheme.DEFAULT
                
                # Configure animation
                animation = StartupAnimation(console=None)  # Console would be injected in real usage
                animation.configure(interactive=interactive)
                
                # Run startup sequence
                if interactive:
                    await animation.run(theme=theme)
                    return f"Displayed interactive ASCII logo with {theme.value} theme"
                else:
                    logo_text = renderer.render_logo(theme)
                    return f"ASCII Logo ({theme.value} theme):\n{logo_text}"
            
            else:
                # Fallback simple logo
                return self._get_simple_logo()
                
        except ImportError:
            # Fallback if display modules not available
            return self._get_simple_logo()
    
    def _get_simple_logo(self) -> str:
        """Get a simple fallback logo."""
        return """
╔═══════════════════════════════════════╗
║                                       ║
║   ╔═══╗╔═══╗╔═══╗╔═══╗╔═══╗╔═══╗    ║
║   ║   ║║   ║║   ║║   ║║   ║║   ║    ║
║   ║   ║║   ║║   ║║   ║║   ║║   ║    ║
║   ╚═══╝╚═══╝╚═══╝╚═══╝╚═══╝╚═══╝    ║
║                                       ║
║        CODEXA - AI Coding Assistant   ║
║                                       ║
╚═══════════════════════════════════════╝

  🤖 Tool-based AI Agent System Ready!
"""