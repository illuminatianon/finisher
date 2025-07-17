"""Tests for application settings."""

import pytest
from unittest.mock import Mock, patch, mock_open
import json
from pathlib import Path
from finisher.config.settings import ApplicationSettings
from finisher.config.defaults import DEFAULT_CONFIG


class TestApplicationSettings:
    """Test ApplicationSettings class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('pathlib.Path.exists', return_value=False):
            self.settings = ApplicationSettings()
    
    def test_init_with_default_config_file(self):
        """Test initialization with default config file location."""
        with patch('pathlib.Path.exists', return_value=False):
            settings = ApplicationSettings()
            
            assert settings.config_file.name == "config.json"
            assert ".finisher" in str(settings.config_file)
    
    def test_init_with_custom_config_file(self):
        """Test initialization with custom config file."""
        custom_path = "/custom/path/config.json"
        with patch('pathlib.Path.exists', return_value=False):
            settings = ApplicationSettings(custom_path)
            
            assert str(settings.config_file) == custom_path
    
    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_load_settings_from_file(self, mock_file, mock_exists):
        """Test loading settings from existing file."""
        mock_exists.return_value = True
        test_settings = {"api": {"base_url": "http://custom.local"}}
        mock_file.return_value.read.return_value = json.dumps(test_settings)
        
        with patch('json.load', return_value=test_settings):
            settings = ApplicationSettings()
            
            assert settings.settings["api"]["base_url"] == "http://custom.local"
    
    @patch('pathlib.Path.exists')
    def test_load_settings_file_not_exists(self, mock_exists):
        """Test loading settings when file doesn't exist."""
        mock_exists.return_value = False
        
        settings = ApplicationSettings()
        
        assert settings.settings == DEFAULT_CONFIG
    
    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    def test_load_settings_json_error(self, mock_json_load, mock_file, mock_exists):
        """Test loading settings with JSON error."""
        mock_exists.return_value = True
        mock_json_load.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        
        settings = ApplicationSettings()
        
        assert settings.settings == DEFAULT_CONFIG
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_save_settings_success(self, mock_json_dump, mock_file):
        """Test successful settings save."""
        self.settings.save_settings()
        
        mock_file.assert_called_once()
        mock_json_dump.assert_called_once()
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_save_settings_error(self, mock_json_dump, mock_file):
        """Test settings save with error."""
        mock_json_dump.side_effect = Exception("Write error")
        
        # Should not raise exception
        self.settings.save_settings()
    
    def test_get_simple_key(self):
        """Test getting simple key value."""
        self.settings.settings = {"test_key": "test_value"}
        
        result = self.settings.get("test_key")
        
        assert result == "test_value"
    
    def test_get_nested_key(self):
        """Test getting nested key value."""
        self.settings.settings = {"level1": {"level2": "nested_value"}}
        
        result = self.settings.get("level1.level2")
        
        assert result == "nested_value"
    
    def test_get_nonexistent_key(self):
        """Test getting nonexistent key with default."""
        result = self.settings.get("nonexistent.key", "default_value")
        
        assert result == "default_value"
    
    def test_set_simple_key(self):
        """Test setting simple key value."""
        self.settings.set("test_key", "new_value")
        
        assert self.settings.settings["test_key"] == "new_value"
    
    def test_set_nested_key(self):
        """Test setting nested key value."""
        self.settings.set("level1.level2", "nested_value")
        
        assert self.settings.settings["level1"]["level2"] == "nested_value"
    
    def test_set_nested_key_creates_structure(self):
        """Test setting nested key creates intermediate structure."""
        self.settings.settings = {}
        self.settings.set("new.nested.key", "value")
        
        assert self.settings.settings["new"]["nested"]["key"] == "value"
    
    def test_get_api_config(self):
        """Test getting API configuration."""
        result = self.settings.get_api_config()
        
        assert "base_url" in result
        assert "timeout" in result
    
    def test_set_api_config(self):
        """Test setting API configuration."""
        new_config = {"base_url": "http://new.local", "timeout": 60}
        
        self.settings.set_api_config(new_config)
        
        api_config = self.settings.get_api_config()
        assert api_config["base_url"] == "http://new.local"
        assert api_config["timeout"] == 60
    
    def test_get_processing_config(self):
        """Test getting processing configuration."""
        result = self.settings.get_processing_config()
        
        assert "upscaler" in result
        assert "scale_factor" in result
        assert "denoising_strength" in result
    
    def test_set_processing_config(self):
        """Test setting processing configuration."""
        new_config = {"upscaler": "ESRGAN", "scale_factor": 4.0}
        
        self.settings.set_processing_config(new_config)
        
        processing_config = self.settings.get_processing_config()
        assert processing_config["upscaler"] == "ESRGAN"
        assert processing_config["scale_factor"] == 4.0
    
    def test_get_ui_config(self):
        """Test getting UI configuration."""
        result = self.settings.get_ui_config()
        
        assert "window_width" in result
        assert "window_height" in result
    
    def test_set_ui_config(self):
        """Test setting UI configuration."""
        new_config = {"window_width": 1024, "window_height": 768}
        
        self.settings.set_ui_config(new_config)
        
        ui_config = self.settings.get_ui_config()
        assert ui_config["window_width"] == 1024
        assert ui_config["window_height"] == 768
    
    def test_reset_to_defaults(self):
        """Test resetting settings to defaults."""
        self.settings.settings = {"custom": "value"}
        
        self.settings.reset_to_defaults()
        
        assert self.settings.settings == DEFAULT_CONFIG
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_export_settings(self, mock_json_dump, mock_file):
        """Test exporting settings to file."""
        export_path = "/export/path/settings.json"
        
        self.settings.export_settings(export_path)
        
        mock_file.assert_called_once_with(export_path, 'w')
        mock_json_dump.assert_called_once()
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    def test_import_settings(self, mock_json_load, mock_file):
        """Test importing settings from file."""
        import_path = "/import/path/settings.json"
        imported_data = {"imported": "value"}
        mock_json_load.return_value = imported_data
        
        self.settings.import_settings(import_path)
        
        mock_file.assert_called_once_with(import_path, 'r')
        assert self.settings.settings["imported"] == "value"
    
    def test_dict_style_access_get(self):
        """Test dictionary-style access for getting values."""
        self.settings.settings = {"test": "value"}
        
        result = self.settings["test"]
        
        assert result == "value"
    
    def test_dict_style_access_set(self):
        """Test dictionary-style access for setting values."""
        self.settings["test"] = "new_value"
        
        assert self.settings.settings["test"] == "new_value"
