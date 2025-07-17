"""Application settings management."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from .defaults import DEFAULT_CONFIG, DEFAULT_API_CONFIG

logger = logging.getLogger(__name__)


class ApplicationSettings:
    """Manages application settings and configuration."""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize settings manager.
        
        Args:
            config_file: Path to configuration file (optional)
        """
        if config_file:
            self.config_file = Path(config_file)
        else:
            # Use default config location
            config_dir = Path.home() / ".finisher"
            config_dir.mkdir(exist_ok=True)
            self.config_file = config_dir / "config.json"
        
        self.settings = self._load_settings()
    
    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from file or create defaults.
        
        Returns:
            Settings dictionary
        """
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    settings = json.load(f)
                
                # Merge with defaults to ensure all keys exist
                merged_settings = DEFAULT_CONFIG.copy()
                merged_settings.update(settings)
                
                logger.info(f"Loaded settings from {self.config_file}")
                return merged_settings
                
            except Exception as e:
                logger.error(f"Failed to load settings: {e}")
                logger.info("Using default settings")
        
        return DEFAULT_CONFIG.copy()
    
    def save_settings(self) -> None:
        """Save current settings to file."""
        try:
            # Ensure directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            
            logger.info(f"Settings saved to {self.config_file}")
            
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value.
        
        Args:
            key: Setting key (supports dot notation like 'api.base_url')
            default: Default value if key not found
            
        Returns:
            Setting value or default
        """
        keys = key.split('.')
        value = self.settings
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """Set a setting value.
        
        Args:
            key: Setting key (supports dot notation like 'api.base_url')
            value: Value to set
        """
        keys = key.split('.')
        target = self.settings
        
        # Navigate to parent of target key
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        
        # Set the value
        target[keys[-1]] = value
        
        logger.debug(f"Setting {key} = {value}")
    
    def get_api_config(self) -> Dict[str, Any]:
        """Get API configuration.
        
        Returns:
            API configuration dictionary
        """
        return self.get('api', DEFAULT_API_CONFIG.copy())
    
    def set_api_config(self, config: Dict[str, Any]) -> None:
        """Set API configuration.
        
        Args:
            config: API configuration dictionary
        """
        current_api = self.get('api', {})
        current_api.update(config)
        self.set('api', current_api)
    
    def get_processing_config(self) -> Dict[str, Any]:
        """Get processing configuration.
        
        Returns:
            Processing configuration dictionary
        """
        return self.get('processing', {
            'upscaler': 'Lanczos',
            'scale_factor': 2.5,
            'denoising_strength': 0.15,
            'tile_overlap': 64,
            'steps': 25,
            'sampler_name': 'Euler a',
            'cfg_scale': 10,
            'scheduler': 'Automatic'
        })
    
    def set_processing_config(self, config: Dict[str, Any]) -> None:
        """Set processing configuration.
        
        Args:
            config: Processing configuration dictionary
        """
        current_processing = self.get('processing', {})
        current_processing.update(config)
        self.set('processing', current_processing)
    
    def get_ui_config(self) -> Dict[str, Any]:
        """Get UI configuration.
        
        Returns:
            UI configuration dictionary
        """
        return self.get('ui', {
            'window_width': 800,
            'window_height': 600,
            'window_x': None,
            'window_y': None,
            'theme': 'default'
        })
    
    def set_ui_config(self, config: Dict[str, Any]) -> None:
        """Set UI configuration.
        
        Args:
            config: UI configuration dictionary
        """
        current_ui = self.get('ui', {})
        current_ui.update(config)
        self.set('ui', current_ui)
    
    def reset_to_defaults(self) -> None:
        """Reset all settings to defaults."""
        self.settings = DEFAULT_CONFIG.copy()
        logger.info("Settings reset to defaults")
    
    def export_settings(self, file_path: str) -> None:
        """Export settings to a file.
        
        Args:
            file_path: Path to export file
        """
        try:
            with open(file_path, 'w') as f:
                json.dump(self.settings, f, indent=2)
            
            logger.info(f"Settings exported to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to export settings: {e}")
            raise
    
    def import_settings(self, file_path: str) -> None:
        """Import settings from a file.
        
        Args:
            file_path: Path to import file
        """
        try:
            with open(file_path, 'r') as f:
                imported_settings = json.load(f)
            
            # Validate and merge with current settings
            self.settings.update(imported_settings)
            
            logger.info(f"Settings imported from {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to import settings: {e}")
            raise
    
    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access."""
        return self.get(key)
    
    def __setitem__(self, key: str, value: Any) -> None:
        """Allow dictionary-style assignment."""
        self.set(key, value)
