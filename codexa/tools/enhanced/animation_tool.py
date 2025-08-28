"""
Animation Tool - Handles startup animations and visual effects for Codexa
"""

import time
import threading
from typing import Dict, Any, Optional, List
import sys

from ..base.tool_interface import Tool, ToolResult, ToolContext, ToolStatus


class AnimationTool(Tool):
    """Tool for handling startup animations and visual effects"""
    
    def __init__(self):
        super().__init__()
        self._animations = {
            'startup': self._startup_animation,
            'loading': self._loading_animation,
            'thinking': self._thinking_animation,
            'processing': self._processing_animation,
            'success': self._success_animation,
            'error': self._error_animation,
            'spinner': self._spinner_animation,
            'dots': self._dots_animation
        }
        self._animation_thread = None
        self._stop_animation = False
    
    @property
    def name(self) -> str:
        return "animation"
    
    @property
    def description(self) -> str:
        return "Handles startup animations and visual effects for enhanced user experience"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def capabilities(self) -> List[str]:
        return [
            "startup_animation",
            "loading_animation", 
            "thinking_animation",
            "processing_animation",
            "success_animation",
            "error_animation",
            "spinner_animation",
            "dots_animation",
            "custom_animation",
            "animation_control"
        ]
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the animation request"""
        request_lower = request.lower()
        
        # High confidence for explicit animation requests
        if any(word in request_lower for word in [
            'animation', 'animate', 'visual effect', 'startup animation',
            'loading animation', 'thinking animation', 'spinner'
        ]):
            return 0.9
            
        # Medium confidence for display-related requests
        if any(word in request_lower for word in [
            'show loading', 'display progress', 'visual feedback',
            'startup sequence', 'boot animation'
        ]):
            return 0.7
            
        # Low confidence for general UI requests
        if any(word in request_lower for word in ['display', 'show', 'visual']):
            return 0.3
            
        return 0.0
    
    def execute(self, request: str, context: ToolContext) -> ToolResult:
        """Execute animation based on request"""
        try:
            animation_type, options = self._parse_animation_request(request)
            
            if animation_type not in self._animations:
                available = ', '.join(self._animations.keys())
                return ToolResult(
                    success=False,
                    data={'error': f'Unknown animation type: {animation_type}. Available: {available}'},
                    message=f"Animation type '{animation_type}' not found",
                    status=ToolStatus.ERROR
                )
            
            # Stop any running animation
            self.stop_animation()
            
            # Start new animation
            result = self._start_animation(animation_type, options)
            
            return ToolResult(
                success=True,
                data=result,
                message=f"Started {animation_type} animation",
                status=ToolStatus.SUCCESS
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                data={'error': str(e)},
                message=f"Animation execution failed: {str(e)}",
                status=ToolStatus.ERROR
            )
    
    def _parse_animation_request(self, request: str) -> tuple[str, Dict[str, Any]]:
        """Parse animation request to extract type and options"""
        request_lower = request.lower()
        options = {}
        
        # Extract animation type
        animation_type = 'startup'  # default
        
        for anim_name in self._animations.keys():
            if anim_name in request_lower:
                animation_type = anim_name
                break
        
        # Extract duration if specified
        if 'duration' in request_lower:
            import re
            duration_match = re.search(r'duration[:\s]+(\d+)', request_lower)
            if duration_match:
                options['duration'] = int(duration_match.group(1))
        
        # Extract speed if specified
        if 'speed' in request_lower:
            if 'fast' in request_lower:
                options['speed'] = 'fast'
            elif 'slow' in request_lower:
                options['speed'] = 'slow'
            else:
                options['speed'] = 'normal'
        
        # Extract message if specified
        if 'message' in request_lower:
            import re
            message_match = re.search(r'message[:\s]+"([^"]+)"', request)
            if message_match:
                options['message'] = message_match.group(1)
        
        return animation_type, options
    
    def _start_animation(self, animation_type: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Start the specified animation"""
        self._stop_animation = False
        
        animation_func = self._animations[animation_type]
        
        # Start animation in separate thread for non-blocking execution
        self._animation_thread = threading.Thread(
            target=animation_func,
            args=(options,),
            daemon=True
        )
        self._animation_thread.start()
        
        return {
            'animation_type': animation_type,
            'options': options,
            'status': 'started',
            'thread_id': self._animation_thread.ident
        }
    
    def stop_animation(self):
        """Stop any running animation"""
        self._stop_animation = True
        if self._animation_thread and self._animation_thread.is_alive():
            self._animation_thread.join(timeout=1.0)
    
    def _startup_animation(self, options: Dict[str, Any]):
        """Codexa startup animation"""
        duration = options.get('duration', 3)
        speed = options.get('speed', 'normal')
        
        speed_multiplier = {'fast': 0.5, 'normal': 1.0, 'slow': 2.0}.get(speed, 1.0)
        
        frames = [
            "🌟 Initializing Codexa...",
            "⚡ Loading enhanced features...",
            "🔧 Connecting tool systems...",
            "🚀 Ready for coding!"
        ]
        
        for frame in frames:
            if self._stop_animation:
                break
            print(f"\r{frame}", end='', flush=True)
            time.sleep(duration / len(frames) * speed_multiplier)
        
        if not self._stop_animation:
            print()  # New line after animation
    
    def _loading_animation(self, options: Dict[str, Any]):
        """Generic loading animation"""
        message = options.get('message', 'Loading')
        duration = options.get('duration', 5)
        speed = options.get('speed', 'normal')
        
        speed_multiplier = {'fast': 0.5, 'normal': 1.0, 'slow': 2.0}.get(speed, 1.0)
        
        chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        start_time = time.time()
        
        while time.time() - start_time < duration and not self._stop_animation:
            for char in chars:
                if self._stop_animation or time.time() - start_time >= duration:
                    break
                print(f"\r{char} {message}...", end='', flush=True)
                time.sleep(0.1 * speed_multiplier)
        
        if not self._stop_animation:
            print(f"\r✅ {message} complete!")
    
    def _thinking_animation(self, options: Dict[str, Any]):
        """Thinking/processing animation"""
        message = options.get('message', 'Thinking')
        duration = options.get('duration', 3)
        speed = options.get('speed', 'normal')
        
        speed_multiplier = {'fast': 0.5, 'normal': 1.0, 'slow': 2.0}.get(speed, 1.0)
        
        dots = ['   ', '.  ', '.. ', '...']
        start_time = time.time()
        
        while time.time() - start_time < duration and not self._stop_animation:
            for dot_pattern in dots:
                if self._stop_animation or time.time() - start_time >= duration:
                    break
                print(f"\r🤔 {message}{dot_pattern}", end='', flush=True)
                time.sleep(0.5 * speed_multiplier)
    
    def _processing_animation(self, options: Dict[str, Any]):
        """Processing animation with progress bar effect"""
        message = options.get('message', 'Processing')
        duration = options.get('duration', 4)
        speed = options.get('speed', 'normal')
        
        speed_multiplier = {'fast': 0.5, 'normal': 1.0, 'slow': 2.0}.get(speed, 1.0)
        
        width = 20
        start_time = time.time()
        
        while time.time() - start_time < duration and not self._stop_animation:
            elapsed = time.time() - start_time
            progress = min(elapsed / duration, 1.0)
            filled = int(width * progress)
            bar = '█' * filled + '░' * (width - filled)
            percent = int(progress * 100)
            
            print(f"\r⚙️  {message}: [{bar}] {percent}%", end='', flush=True)
            time.sleep(0.1 * speed_multiplier)
        
        if not self._stop_animation:
            print(f"\r✅ {message}: [{'█' * width}] 100%")
    
    def _success_animation(self, options: Dict[str, Any]):
        """Success celebration animation"""
        message = options.get('message', 'Success')
        
        frames = ['🎉', '✨', '🌟', '⭐', '✅']
        
        for frame in frames:
            if self._stop_animation:
                break
            print(f"\r{frame} {message}!", end='', flush=True)
            time.sleep(0.3)
        
        if not self._stop_animation:
            print()
    
    def _error_animation(self, options: Dict[str, Any]):
        """Error indication animation"""
        message = options.get('message', 'Error')
        
        for _ in range(3):
            if self._stop_animation:
                break
            print(f"\r❌ {message}", end='', flush=True)
            time.sleep(0.2)
            print(f"\r   {message}", end='', flush=True)
            time.sleep(0.2)
        
        if not self._stop_animation:
            print(f"\r❌ {message}")
    
    def _spinner_animation(self, options: Dict[str, Any]):
        """Simple spinner animation"""
        message = options.get('message', '')
        duration = options.get('duration', 2)
        speed = options.get('speed', 'normal')
        
        speed_multiplier = {'fast': 0.5, 'normal': 1.0, 'slow': 2.0}.get(speed, 1.0)
        
        spinner_chars = '|/-\\'
        start_time = time.time()
        
        while time.time() - start_time < duration and not self._stop_animation:
            for char in spinner_chars:
                if self._stop_animation or time.time() - start_time >= duration:
                    break
                display_text = f"{char} {message}" if message else char
                print(f"\r{display_text}", end='', flush=True)
                time.sleep(0.25 * speed_multiplier)
    
    def _dots_animation(self, options: Dict[str, Any]):
        """Dots loading animation"""
        message = options.get('message', 'Loading')
        duration = options.get('duration', 3)
        speed = options.get('speed', 'normal')
        
        speed_multiplier = {'fast': 0.5, 'normal': 1.0, 'slow': 2.0}.get(speed, 1.0)
        
        start_time = time.time()
        dot_count = 0
        
        while time.time() - start_time < duration and not self._stop_animation:
            dots = '.' * (dot_count % 4)
            spaces = ' ' * (3 - len(dots))
            print(f"\r{message}{dots}{spaces}", end='', flush=True)
            time.sleep(0.5 * speed_multiplier)
            dot_count += 1
    
    def get_status(self) -> Dict[str, Any]:
        """Get current animation status"""
        return {
            'tool_name': self.name,
            'version': self.version,
            'available_animations': list(self._animations.keys()),
            'animation_running': self._animation_thread is not None and self._animation_thread.is_alive(),
            'capabilities': self.capabilities
        }