"""Tests for main window."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from finisher.gui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # Don't quit the app as it might be used by other tests


class TestMainWindow:
    """Test MainWindow class."""
    
    def test_init(self, qapp):
        """Test MainWindow initialization."""
        window = MainWindow()
        
        assert window.windowTitle() == "Finisher - AI Image Upscaling Tool"
        assert window.size().width() == 800
        assert window.size().height() == 600
        assert window.minimumSize().width() == 600
        assert window.minimumSize().height() == 400
    
    def test_init_custom_title(self, qapp):
        """Test MainWindow initialization with custom title."""
        custom_title = "Custom Finisher Title"
        window = MainWindow(custom_title)
        
        assert window.windowTitle() == custom_title
    
    def test_callbacks_initialization(self, qapp):
        """Test that callbacks are initialized to None."""
        window = MainWindow()
        
        assert window.on_image_dropped is None
        assert window.on_file_selected is None
        assert window.on_cancel_job is None
        assert window.on_emergency_stop is None
        assert window.on_config_changed is None
    
    def test_set_cancel_button_enabled(self, qapp):
        """Test enabling/disabling cancel button."""
        window = MainWindow()
        
        # Initially disabled
        assert not window.cancel_button.isEnabled()
        
        # Enable
        window.set_cancel_button_enabled(True)
        assert window.cancel_button.isEnabled()
        
        # Disable
        window.set_cancel_button_enabled(False)
        assert not window.cancel_button.isEnabled()
    
    def test_update_status(self, qapp):
        """Test updating status."""
        window = MainWindow()
        
        window.update_status("Test status")
        assert window.status_bar.status_label.text() == "Test status"
    
    def test_update_status_with_progress(self, qapp):
        """Test updating status with progress."""
        window = MainWindow()

        # Show the window so visibility works properly
        window.show()
        qapp.processEvents()

        window.update_status("Processing...", 0.75)
        qapp.processEvents()

        assert window.status_bar.status_label.text() == "Processing..."
        assert window.status_bar.progress_bar.value() == 75
        assert window.status_bar.progress_bar.isVisible()
    
    @patch('finisher.gui.main_window.QMessageBox.information')
    def test_show_success_message(self, mock_msgbox, qapp):
        """Test showing success message."""
        window = MainWindow()
        
        window.show_success_message("Success!")
        
        mock_msgbox.assert_called_once_with(window, "Success", "Success!")
    
    @patch('finisher.gui.main_window.QMessageBox.critical')
    def test_show_error_message(self, mock_msgbox, qapp):
        """Test showing error message."""
        window = MainWindow()
        
        window.show_error_message("Error!")
        
        mock_msgbox.assert_called_once_with(window, "Error", "Error!")
    
    def test_show_processing_feedback(self, qapp):
        """Test showing processing feedback."""
        window = MainWindow()
        
        window.show_processing_feedback("Processing image...")
        
        # Check that drop area status was updated
        assert "⏳ Processing image..." in window.drop_area.instructions.text()
    
    def test_reset_ui_state(self, qapp):
        """Test resetting UI state."""
        window = MainWindow()
        
        # First enable cancel button and set some status
        window.set_cancel_button_enabled(True)
        window.update_status("Processing...")
        
        # Reset
        window.reset_ui_state()
        
        assert not window.cancel_button.isEnabled()
        assert window.status_bar.status_label.text() == "Ready"
    
    @patch('finisher.gui.main_window.QFileDialog.getOpenFileName')
    def test_browse_files(self, mock_dialog, qapp):
        """Test file browsing."""
        window = MainWindow()
        mock_dialog.return_value = ("/path/to/image.png", "")
        
        # Set up callback
        callback_called = False
        selected_file = None
        
        def mock_callback(file_path):
            nonlocal callback_called, selected_file
            callback_called = True
            selected_file = file_path
        
        window.on_file_selected = mock_callback
        
        # Trigger browse
        window._browse_files()
        
        assert callback_called
        assert selected_file == "/path/to/image.png"
    
    @patch('finisher.gui.main_window.QFileDialog.getOpenFileName')
    def test_browse_files_cancelled(self, mock_dialog, qapp):
        """Test file browsing when cancelled."""
        window = MainWindow()
        mock_dialog.return_value = ("", "")  # Empty string means cancelled
        
        # Set up callback
        callback_called = False
        
        def mock_callback(file_path):
            nonlocal callback_called
            callback_called = True
        
        window.on_file_selected = mock_callback
        
        # Trigger browse
        window._browse_files()
        
        assert not callback_called
    
    def test_emergency_stop_callback(self, qapp):
        """Test emergency stop callback."""
        window = MainWindow()
        
        callback_called = False
        
        def mock_callback():
            nonlocal callback_called
            callback_called = True
        
        window.on_emergency_stop = mock_callback
        
        # Mock the message box to return Yes
        with patch('finisher.gui.main_window.QMessageBox.question') as mock_question:
            from PySide6.QtWidgets import QMessageBox
            mock_question.return_value = QMessageBox.StandardButton.Yes
            
            window._emergency_stop()
            
            assert callback_called
    
    def test_cancel_job_callback(self, qapp):
        """Test cancel job callback."""
        window = MainWindow()
        
        callback_called = False
        
        def mock_callback():
            nonlocal callback_called
            callback_called = True
        
        window.on_cancel_job = mock_callback
        
        window._cancel_job()
        
        assert callback_called
