"""
Theme Tool - Handles theme management and customization for Codexa
"""

import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path

from ..base.tool_interface import Tool, ToolResult, ToolContext, ToolStatus


class ThemeTool(Tool):
    """Tool for managing themes and customization"""
    
    def __init__(self):
        super().__init__()
        self.themes_dir = Path.home() / '.codexa' / 'themes'
        self.current_theme_file = Path.home() / '.codexa' / 'current_theme.json'
        self._ensure_theme_directory()
        self._load_default_themes()
    
    @property
    def name(self) -> str:
        return "theme"
    
    @property
    def description(self) -> str:
        return "Manages themes and customization for Codexa interface and experience"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def capabilities(self) -> List[str]:
        return [
            "list_themes",
            "set_theme", 
            "create_theme",
            "edit_theme",
            "delete_theme",
            "export_theme",
            "import_theme",
            "get_current_theme",
            "reset_theme",
            "preview_theme",
            "theme_validation"
        ]
    
    def can_handle_request(self, request: str, context: ToolContext) -> float:
        """Check if this tool can handle the theme request"""
        request_lower = request.lower()
        
        # High confidence for explicit theme requests
        if any(word in request_lower for word in [
            'theme', 'themes', 'color scheme', 'customize', 'appearance',
            'set theme', 'change theme', 'theme list'
        ]):
            return 0.9
            
        # Medium confidence for style-related requests
        if any(word in request_lower for word in [
            'style', 'colors', 'visual', 'interface', 'ui',
            'dark mode', 'light mode', 'customization'
        ]):
            return 0.6
            
        # Low confidence for general display requests
        if any(word in request_lower for word in ['display', 'show', 'look']):
            return 0.2
            
        return 0.0
    
    def execute(self, request: str, context: ToolContext) -> ToolResult:
        """Execute theme operation based on request"""
        try:
            action, params = self._parse_theme_request(request)
            
            # Route to appropriate handler
            handlers = {
                'list': self._list_themes,
                'set': self._set_theme,
                'create': self._create_theme,
                'edit': self._edit_theme,
                'delete': self._delete_theme,
                'export': self._export_theme,
                'import': self._import_theme,
                'current': self._get_current_theme,
                'reset': self._reset_theme,
                'preview': self._preview_theme
            }
            
            if action not in handlers:
                return ToolResult(
                    success=False,
                    data={'error': f'Unknown theme action: {action}'},
                    message=f"Theme action '{action}' not supported",
                    status=ToolStatus.ERROR
                )
            
            result = handlers[action](params)
            
            return ToolResult(
                success=True,
                data=result,
                message=f"Theme {action} completed successfully",
                status=ToolStatus.SUCCESS
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                data={'error': str(e)},
                message=f"Theme operation failed: {str(e)}",
                status=ToolStatus.ERROR
            )
    
    def _parse_theme_request(self, request: str) -> tuple[str, Dict[str, Any]]:
        """Parse theme request to extract action and parameters"""
        request_lower = request.lower()
        params = {}
        
        # Determine action
        if any(word in request_lower for word in ['list', 'show themes', 'available themes']):
            action = 'list'
        elif any(word in request_lower for word in ['set theme', 'use theme', 'apply theme']):
            action = 'set'
            # Extract theme name
            import re
            theme_match = re.search(r'(?:set|use|apply)\s+theme\s+["\']?([^"\']+)["\']?', request_lower)
            if theme_match:
                params['theme_name'] = theme_match.group(1).strip()
        elif any(word in request_lower for word in ['create theme', 'new theme']):
            action = 'create'
            # Extract theme name
            import re
            theme_match = re.search(r'(?:create|new)\s+theme\s+["\']?([^"\']+)["\']?', request_lower)
            if theme_match:
                params['theme_name'] = theme_match.group(1).strip()
        elif 'edit theme' in request_lower:
            action = 'edit'
            # Extract theme name
            import re
            theme_match = re.search(r'edit\s+theme\s+["\']?([^"\']+)["\']?', request_lower)
            if theme_match:
                params['theme_name'] = theme_match.group(1).strip()
        elif 'delete theme' in request_lower:
            action = 'delete'
            # Extract theme name
            import re
            theme_match = re.search(r'delete\s+theme\s+["\']?([^"\']+)["\']?', request_lower)
            if theme_match:
                params['theme_name'] = theme_match.group(1).strip()
        elif any(word in request_lower for word in ['current theme', 'active theme']):
            action = 'current'
        elif 'reset theme' in request_lower:
            action = 'reset'
        elif 'preview theme' in request_lower:
            action = 'preview'
            # Extract theme name
            import re
            theme_match = re.search(r'preview\s+theme\s+["\']?([^"\']+)["\']?', request_lower)
            if theme_match:
                params['theme_name'] = theme_match.group(1).strip()
        else:
            action = 'list'  # Default action
        
        return action, params
    
    def _ensure_theme_directory(self):
        """Ensure theme directory exists"""
        self.themes_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_default_themes(self):
        """Load default themes if they don't exist"""
        default_themes = {
            'default': {
                'name': 'Default',
                'description': 'Default Codexa theme',
                'colors': {
                    'primary': '#007ACC',
                    'secondary': '#4CAF50',
                    'background': '#1E1E1E',
                    'foreground': '#FFFFFF',
                    'accent': '#FF6B35',
                    'error': '#F44336',
                    'warning': '#FF9800',
                    'success': '#4CAF50',
                    'info': '#2196F3'
                },
                'fonts': {
                    'main': 'Consolas, monospace',
                    'ui': 'Segoe UI, sans-serif'
                },
                'styles': {
                    'border_radius': '4px',
                    'shadow': '0 2px 4px rgba(0,0,0,0.1)',
                    'animation_speed': '0.3s'
                }
            },
            'dark': {
                'name': 'Dark',
                'description': 'Dark theme for Codexa',
                'colors': {
                    'primary': '#BB86FC',
                    'secondary': '#03DAC6',
                    'background': '#121212',
                    'foreground': '#FFFFFF',
                    'accent': '#CF6679',
                    'error': '#CF6679',
                    'warning': '#FFC107',
                    'success': '#4CAF50',
                    'info': '#03DAC6'
                },
                'fonts': {
                    'main': 'Fira Code, monospace',
                    'ui': 'Roboto, sans-serif'
                },
                'styles': {
                    'border_radius': '8px',
                    'shadow': '0 4px 8px rgba(0,0,0,0.3)',
                    'animation_speed': '0.2s'
                }
            },
            'light': {
                'name': 'Light',
                'description': 'Light theme for Codexa',
                'colors': {
                    'primary': '#1976D2',
                    'secondary': '#388E3C',
                    'background': '#FFFFFF',
                    'foreground': '#212121',
                    'accent': '#D32F2F',
                    'error': '#D32F2F',
                    'warning': '#F57C00',
                    'success': '#388E3C',
                    'info': '#1976D2'
                },
                'fonts': {
                    'main': 'Source Code Pro, monospace',
                    'ui': 'Open Sans, sans-serif'
                },
                'styles': {
                    'border_radius': '6px',
                    'shadow': '0 2px 6px rgba(0,0,0,0.15)',
                    'animation_speed': '0.25s'
                }
            },
            'cyberpunk': {
                'name': 'Cyberpunk',
                'description': 'Futuristic cyberpunk theme',
                'colors': {
                    'primary': '#00FFFF',
                    'secondary': '#FF00FF',
                    'background': '#0A0A0A',
                    'foreground': '#00FF41',
                    'accent': '#FFFF00',
                    'error': '#FF073A',
                    'warning': '#FFA500',
                    'success': '#39FF14',
                    'info': '#00BFFF'
                },
                'fonts': {
                    'main': 'JetBrains Mono, monospace',
                    'ui': 'Orbitron, sans-serif'
                },
                'styles': {
                    'border_radius': '2px',
                    'shadow': '0 0 10px rgba(0,255,255,0.3)',
                    'animation_speed': '0.1s'
                }
            }
        }
        
        # Save default themes if they don't exist
        for theme_id, theme_data in default_themes.items():
            theme_file = self.themes_dir / f'{theme_id}.json'
            if not theme_file.exists():
                with open(theme_file, 'w') as f:
                    json.dump(theme_data, f, indent=2)
    
    def _list_themes(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available themes"""
        themes = {}
        
        for theme_file in self.themes_dir.glob('*.json'):
            try:
                with open(theme_file, 'r') as f:
                    theme_data = json.load(f)
                themes[theme_file.stem] = {
                    'name': theme_data.get('name', theme_file.stem),
                    'description': theme_data.get('description', 'No description'),
                    'file': str(theme_file)
                }
            except Exception as e:
                themes[theme_file.stem] = {
                    'name': theme_file.stem,
                    'description': f'Error loading theme: {e}',
                    'file': str(theme_file),
                    'error': True
                }
        
        current_theme = self._get_current_theme_name()
        
        return {
            'themes': themes,
            'current_theme': current_theme,
            'total_count': len(themes)
        }
    
    def _set_theme(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set active theme"""
        theme_name = params.get('theme_name')
        if not theme_name:
            raise ValueError("Theme name is required")
        
        theme_file = self.themes_dir / f'{theme_name}.json'
        if not theme_file.exists():
            raise ValueError(f"Theme '{theme_name}' not found")
        
        # Load theme data to validate
        with open(theme_file, 'r') as f:
            theme_data = json.load(f)
        
        # Save as current theme
        current_theme_data = {
            'theme_id': theme_name,
            'theme_name': theme_data.get('name', theme_name),
            'theme_file': str(theme_file),
            'applied_at': self._get_timestamp()
        }
        
        with open(self.current_theme_file, 'w') as f:
            json.dump(current_theme_data, f, indent=2)
        
        return {
            'theme_set': theme_name,
            'theme_data': theme_data,
            'applied_at': current_theme_data['applied_at']
        }
    
    def _create_theme(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create new theme"""
        theme_name = params.get('theme_name')
        if not theme_name:
            raise ValueError("Theme name is required")
        
        theme_file = self.themes_dir / f'{theme_name}.json'
        if theme_file.exists():
            raise ValueError(f"Theme '{theme_name}' already exists")
        
        # Create basic theme structure
        new_theme = {
            'name': theme_name.title(),
            'description': f'Custom theme: {theme_name}',
            'created_at': self._get_timestamp(),
            'colors': {
                'primary': '#007ACC',
                'secondary': '#4CAF50',
                'background': '#1E1E1E',
                'foreground': '#FFFFFF',
                'accent': '#FF6B35',
                'error': '#F44336',
                'warning': '#FF9800',
                'success': '#4CAF50',
                'info': '#2196F3'
            },
            'fonts': {
                'main': 'Consolas, monospace',
                'ui': 'Segoe UI, sans-serif'
            },
            'styles': {
                'border_radius': '4px',
                'shadow': '0 2px 4px rgba(0,0,0,0.1)',
                'animation_speed': '0.3s'
            }
        }
        
        with open(theme_file, 'w') as f:
            json.dump(new_theme, f, indent=2)
        
        return {
            'theme_created': theme_name,
            'theme_file': str(theme_file),
            'theme_data': new_theme
        }
    
    def _edit_theme(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Edit existing theme"""
        theme_name = params.get('theme_name')
        if not theme_name:
            raise ValueError("Theme name is required")
        
        theme_file = self.themes_dir / f'{theme_name}.json'
        if not theme_file.exists():
            raise ValueError(f"Theme '{theme_name}' not found")
        
        return {
            'theme_file': str(theme_file),
            'edit_instructions': "Edit the JSON file directly or use theme creation tools",
            'backup_created': False  # Could implement backup functionality
        }
    
    def _delete_theme(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete theme"""
        theme_name = params.get('theme_name')
        if not theme_name:
            raise ValueError("Theme name is required")
        
        # Prevent deletion of default themes
        if theme_name in ['default', 'dark', 'light']:
            raise ValueError(f"Cannot delete built-in theme '{theme_name}'")
        
        theme_file = self.themes_dir / f'{theme_name}.json'
        if not theme_file.exists():
            raise ValueError(f"Theme '{theme_name}' not found")
        
        # Check if it's the current theme
        current_theme = self._get_current_theme_name()
        if current_theme == theme_name:
            # Reset to default theme
            self._set_theme({'theme_name': 'default'})
        
        theme_file.unlink()
        
        return {
            'theme_deleted': theme_name,
            'reset_to_default': current_theme == theme_name
        }
    
    def _get_current_theme(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get current active theme"""
        if not self.current_theme_file.exists():
            return {
                'current_theme': 'default',
                'theme_data': None,
                'message': 'No theme set, using default'
            }
        
        with open(self.current_theme_file, 'r') as f:
            current_theme_info = json.load(f)
        
        theme_id = current_theme_info.get('theme_id', 'default')
        theme_file = self.themes_dir / f'{theme_id}.json'
        
        if theme_file.exists():
            with open(theme_file, 'r') as f:
                theme_data = json.load(f)
        else:
            theme_data = None
        
        return {
            'current_theme': theme_id,
            'theme_info': current_theme_info,
            'theme_data': theme_data
        }
    
    def _reset_theme(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Reset to default theme"""
        return self._set_theme({'theme_name': 'default'})
    
    def _preview_theme(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Preview theme without applying"""
        theme_name = params.get('theme_name')
        if not theme_name:
            raise ValueError("Theme name is required")
        
        theme_file = self.themes_dir / f'{theme_name}.json'
        if not theme_file.exists():
            raise ValueError(f"Theme '{theme_name}' not found")
        
        with open(theme_file, 'r') as f:
            theme_data = json.load(f)
        
        return {
            'preview_theme': theme_name,
            'theme_data': theme_data,
            'preview_only': True
        }
    
    def _get_current_theme_name(self) -> str:
        """Get current theme name"""
        if not self.current_theme_file.exists():
            return 'default'
        
        try:
            with open(self.current_theme_file, 'r') as f:
                current_theme_info = json.load(f)
            return current_theme_info.get('theme_id', 'default')
        except Exception:
            return 'default'
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _export_theme(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Export theme to file"""
        theme_name = params.get('theme_name')
        if not theme_name:
            raise ValueError("Theme name is required")
        
        theme_file = self.themes_dir / f'{theme_name}.json'
        if not theme_file.exists():
            raise ValueError(f"Theme '{theme_name}' not found")
        
        return {
            'export_file': str(theme_file),
            'theme_name': theme_name,
            'export_format': 'json'
        }
    
    def _import_theme(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Import theme from file"""
        # This would need file path parameter
        return {
            'import_status': 'not_implemented',
            'message': 'Theme import functionality needs file path parameter'
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get theme tool status"""
        themes_count = len(list(self.themes_dir.glob('*.json')))
        current_theme = self._get_current_theme_name()
        
        return {
            'tool_name': self.name,
            'version': self.version,
            'themes_directory': str(self.themes_dir),
            'themes_count': themes_count,
            'current_theme': current_theme,
            'capabilities': self.capabilities
        }