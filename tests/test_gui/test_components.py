"""Tests for GUI components."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PySide6.QtWidgets import QApplication, QWidget, QGroupBox, QVBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from finisher.gui.components import StatusBar, ProgressIndicator, ImageDropArea, ConfigurationPanel


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # Don't quit the app as it might be used by other tests


class TestStatusBar:
    """Test StatusBar component."""
    
    def test_init(self, qapp):
        """Test StatusBar initialization."""
        parent = QWidget()
        status_bar = StatusBar(parent)
        
        assert status_bar.status_label.text() == "Ready"
        assert not status_bar.progress_bar.isVisible()
    
    def test_update_status_with_progress(self, qapp):
        """Test updating status with progress."""
        parent = QWidget()
        # Create a layout for the parent so StatusBar can add itself
        layout = QVBoxLayout(parent)
        status_bar = StatusBar(parent)

        # Show the parent widget so visibility works properly
        parent.show()
        qapp.processEvents()

        status_bar.update_status("Processing...", 0.5)
        qapp.processEvents()

        assert status_bar.status_label.text() == "Processing..."
        assert status_bar.progress_bar.isVisible()
        assert status_bar.progress_bar.value() == 50
    
    def test_update_status_without_progress(self, qapp):
        """Test updating status without progress."""
        parent = QWidget()
        # Create a layout for the parent so StatusBar can add itself
        layout = QVBoxLayout(parent)
        status_bar = StatusBar(parent)

        # Show the parent widget so visibility works properly
        parent.show()
        qapp.processEvents()

        # First show progress
        status_bar.update_status("Processing...", 0.5)
        qapp.processEvents()
        assert status_bar.progress_bar.isVisible()

        # Then hide it
        status_bar.update_status("Done")
        qapp.processEvents()
        assert not status_bar.progress_bar.isVisible()


class TestProgressIndicator:
    """Test ProgressIndicator component."""
    
    def test_init(self, qapp):
        """Test ProgressIndicator initialization."""
        parent = QWidget()
        indicator = ProgressIndicator(parent)
        
        assert indicator.progress_bar.value() == 0
        assert indicator.label.text() == ""
    
    def test_update_progress(self, qapp):
        """Test updating progress indicator."""
        parent = QWidget()
        indicator = ProgressIndicator(parent)

        indicator.update_progress(0.75, "Almost done...")

        assert indicator.progress_bar.value() == 75
        assert indicator.label.text() == "Almost done..."


class TestImageDropArea:
    """Test ImageDropArea component."""
    
    def test_init(self, qapp):
        """Test ImageDropArea initialization."""
        parent = QGroupBox()
        drop_area = ImageDropArea(parent)
        
        assert drop_area.acceptDrops()
        assert "Drop image files here" in drop_area.instructions.text()
    
    def test_set_status(self, qapp):
        """Test setting status text."""
        parent = QGroupBox()
        drop_area = ImageDropArea(parent)
        
        drop_area.set_status("Test status", "red")
        
        assert drop_area.instructions.text() == "Test status"
        # Check that stylesheet contains the color
        assert "red" in drop_area.instructions.styleSheet()
    
    def test_is_image_file(self, qapp):
        """Test image file validation."""
        parent = QGroupBox()
        drop_area = ImageDropArea(parent)
        
        assert drop_area._is_image_file("test.png")
        assert drop_area._is_image_file("test.jpg")
        assert drop_area._is_image_file("test.jpeg")
        assert not drop_area._is_image_file("test.txt")
        assert not drop_area._is_image_file("test.pdf")


class TestConfigurationPanel:
    """Test ConfigurationPanel component."""
    
    def test_init(self, qapp):
        """Test ConfigurationPanel initialization."""
        parent = QGroupBox()
        config_panel = ConfigurationPanel(parent)
        
        assert config_panel.scale_spin.value() == 2.5
        assert config_panel.denoising_spin.value() == 0.15
        assert config_panel.tile_spin.value() == 64
    
    def test_get_configuration(self, qapp):
        """Test getting configuration."""
        parent = QGroupBox()
        config_panel = ConfigurationPanel(parent)
        
        # Set some values
        config_panel.upscaler_combo.addItem("Test Upscaler")
        config_panel.upscaler_combo.setCurrentText("Test Upscaler")
        config_panel.scale_spin.setValue(3.0)
        
        config = config_panel.get_configuration()
        
        assert config["upscaler"] == "Test Upscaler"
        assert config["scale_factor"] == 3.0
        assert config["denoising_strength"] == 0.15
        assert config["tile_overlap"] == 64
    
    def test_set_configuration(self, qapp):
        """Test setting configuration."""
        parent = QGroupBox()
        config_panel = ConfigurationPanel(parent)
        
        # Add an upscaler option first
        config_panel.upscaler_combo.addItem("Test Upscaler")
        
        config = {
            "upscaler": "Test Upscaler",
            "scale_factor": 4.0,
            "denoising_strength": 0.25,
            "tile_overlap": 128
        }
        
        config_panel.set_configuration(config)
        
        assert config_panel.upscaler_combo.currentText() == "Test Upscaler"
        assert config_panel.scale_spin.value() == 4.0
        assert config_panel.denoising_spin.value() == 0.25
        assert config_panel.tile_spin.value() == 128
    
    def test_update_options(self, qapp):
        """Test updating available options."""
        parent = QGroupBox()
        config_panel = ConfigurationPanel(parent)
        
        upscalers = ["Upscaler1", "Upscaler2", "Upscaler3"]
        config_panel.update_options(upscalers, [], [], [])
        
        assert config_panel.upscaler_combo.count() == 3
        assert config_panel.upscaler_combo.itemText(0) == "Upscaler1"
        assert config_panel.upscaler_combo.currentText() == "Upscaler1"
