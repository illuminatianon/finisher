"""Tests for main module."""

import pytest
from finisher.main import main


def test_main_exits():
    """Test that main function exits."""
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0
