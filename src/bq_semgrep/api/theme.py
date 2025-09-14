"""
Theme management for the web UI.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

import yaml

class ThemeManager:
    """Manage UI themes and customization."""

    DEFAULT_THEMES = {
        "default": {
            "name": "Default",
            "colors": {
                "primary": "#1976d2",
                "secondary": "#dc004e",
                "accent": "#9c27b0",
                "background": "#ffffff",
                "surface": "#f5f5f5",
                "text": "#333333"
            }
        },
        "google": {
            "name": "Google",
            "colors": {
                "primary": "#4285f4",
                "secondary": "#34a853",
                "accent": "#fbbc04",
                "background": "#ffffff",
                "surface": "#f8f9fa",
                "text": "#202124"
            }
        },
        "github": {
            "name": "GitHub",
            "colors": {
                "primary": "#24292e",
                "secondary": "#0366d6",
                "accent": "#28a745",
                "background": "#ffffff",
                "surface": "#f6f8fa",
                "text": "#24292e"
            }
        },
        "enterprise": {
            "name": "Enterprise",
            "colors": {
                "primary": "#003366",
                "secondary": "#0066cc",
                "accent": "#66b2ff",
                "background": "#ffffff",
                "surface": "#f0f4f8",
                "text": "#1a1a1a"
            }
        },
        "dark": {
            "name": "Dark",
            "colors": {
                "primary": "#90caf9",
                "secondary": "#f48fb1",
                "accent": "#ce93d8",
                "background": "#121212",
                "surface": "#1e1e1e",
                "text": "#ffffff"
            }
        }
    }

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize theme manager."""
        self.config_path = config_path or Path.home() / ".grepctl" / "theme.yaml"
        self.current_theme = self.load_theme()

    def load_theme(self) -> Dict[str, Any]:
        """Load theme configuration from file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    if self.config_path.suffix == '.json':
                        return json.load(f)
                    else:
                        return yaml.safe_load(f)
            except Exception:
                pass
        return self.get_default_theme()

    def save_theme(self, theme: Dict[str, Any]) -> bool:
        """Save theme configuration to file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                if self.config_path.suffix == '.json':
                    json.dump(theme, f, indent=2)
                else:
                    yaml.dump(theme, f, default_flow_style=False)
            self.current_theme = theme
            return True
        except Exception:
            return False

    def get_default_theme(self) -> Dict[str, Any]:
        """Get the default theme configuration."""
        return {
            "branding": {
                "companyName": "grepctl",
                "logo": "/static/logo.svg",
                "favicon": "/favicon.ico",
                "tagline": "Multimodal Semantic Search Platform"
            },
            "colors": self.DEFAULT_THEMES["default"]["colors"],
            "darkMode": {
                "enabled": True,
                "colors": self.DEFAULT_THEMES["dark"]["colors"]
            },
            "layout": {
                "maxWidth": "1200px",
                "borderRadius": "8px",
                "fontFamily": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
                "headerHeight": "64px"
            },
            "features": {
                "darkMode": True,
                "exportEnabled": True,
                "advancedFilters": True,
                "keyboardShortcuts": True
            }
        }

    def apply_preset(self, preset_name: str) -> Dict[str, Any]:
        """Apply a preset theme."""
        if preset_name in self.DEFAULT_THEMES:
            theme = self.get_default_theme()
            theme["colors"] = self.DEFAULT_THEMES[preset_name]["colors"]
            theme["preset"] = preset_name
            self.save_theme(theme)
            return theme
        return self.current_theme

    def update_branding(self, company_name: str = None, logo_path: str = None,
                        tagline: str = None) -> Dict[str, Any]:
        """Update branding information."""
        if company_name:
            self.current_theme["branding"]["companyName"] = company_name
        if logo_path:
            self.current_theme["branding"]["logo"] = logo_path
        if tagline:
            self.current_theme["branding"]["tagline"] = tagline
        self.save_theme(self.current_theme)
        return self.current_theme

    def update_colors(self, colors: Dict[str, str]) -> Dict[str, Any]:
        """Update theme colors."""
        self.current_theme["colors"].update(colors)
        self.save_theme(self.current_theme)
        return self.current_theme

    def export_theme(self, output_path: Path) -> bool:
        """Export current theme to a file."""
        try:
            with open(output_path, 'w') as f:
                if output_path.suffix == '.json':
                    json.dump(self.current_theme, f, indent=2)
                else:
                    yaml.dump(self.current_theme, f, default_flow_style=False)
            return True
        except Exception:
            return False

    def import_theme(self, input_path: Path) -> Dict[str, Any]:
        """Import theme from a file."""
        try:
            with open(input_path, 'r') as f:
                if input_path.suffix == '.json':
                    theme = json.load(f)
                else:
                    theme = yaml.safe_load(f)
            self.save_theme(theme)
            return theme
        except Exception:
            return self.current_theme