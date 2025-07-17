"""Tests for main module."""

import pytest
from unittest.mock import patch, MagicMock
from finisher.main import main, setup_logging


def test_setup_logging():
    """Test logging setup."""
    with patch('logging.basicConfig') as mock_config:
        setup_logging("DEBUG")
        mock_config.assert_called_once()


def test_main_keyboard_interrupt():
    """Test main function with keyboard interrupt."""
    with patch('finisher.main.ApplicationController') as mock_controller:
        mock_app = MagicMock()
        mock_controller.return_value = mock_app
        mock_app.run.side_effect = KeyboardInterrupt()

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0


def test_main_exception():
    """Test main function with exception."""
    with patch('finisher.main.ApplicationController') as mock_controller:
        mock_app = MagicMock()
        mock_controller.return_value = mock_app
        mock_app.run.side_effect = Exception("Test error")

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
