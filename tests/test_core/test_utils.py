"""Tests for core utilities."""

import pytest
from unittest.mock import Mock, patch
from PIL import Image
import base64
import tempfile  # noqa: F401 - used in patch decorators
import os  # noqa: F401 - used in patch decorators
from finisher.core.utils import (
    encode_image_to_base64,
    decode_base64_to_image,
    validate_image_format,
    create_temp_file,
    cleanup_temp_files,
    get_image_info,
    convert_image_format,
    is_image_file,
    get_supported_formats,
)


class TestCoreUtils:
    """Test core utility functions."""

    def test_encode_image_to_base64_success(self):
        """Test successful image encoding to base64."""
        # Create a simple test image
        image = Image.new("RGB", (100, 100), color="red")

        result = encode_image_to_base64(image)

        assert isinstance(result, str)
        assert len(result) > 0
        # Verify it's valid base64
        base64.b64decode(result)

    def test_encode_image_to_base64_jpeg(self):
        """Test image encoding to base64 with JPEG format."""
        image = Image.new("RGB", (100, 100), color="blue")

        result = encode_image_to_base64(image, format="JPEG")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_decode_base64_to_image_success(self):
        """Test successful base64 decoding to image."""
        # Create test image and encode it
        original_image = Image.new("RGB", (100, 100), color="green")
        base64_string = encode_image_to_base64(original_image)

        result = decode_base64_to_image(base64_string)

        assert isinstance(result, Image.Image)
        assert result.size == (100, 100)

    def test_decode_base64_to_image_with_data_url(self):
        """Test base64 decoding with data URL prefix."""
        original_image = Image.new("RGB", (50, 50), color="yellow")
        base64_string = encode_image_to_base64(original_image)
        data_url = f"data:image/png;base64,{base64_string}"

        result = decode_base64_to_image(data_url)

        assert isinstance(result, Image.Image)
        assert result.size == (50, 50)

    def test_decode_base64_to_image_invalid(self):
        """Test base64 decoding with invalid data."""
        with pytest.raises(ValueError, match="Cannot decode base64 image"):
            decode_base64_to_image("invalid_base64_data")

    @patch("pathlib.Path.suffix")
    @patch("PIL.Image.open")
    def test_validate_image_format_valid(self, mock_open, mock_suffix):
        """Test image format validation with valid format."""
        mock_suffix.return_value = ".png"
        mock_image = Mock()
        mock_open.return_value.__enter__.return_value = mock_image

        result = validate_image_format("test.png")

        assert result is True

    @patch("pathlib.Path.suffix")
    def test_validate_image_format_invalid_extension(self, mock_suffix):
        """Test image format validation with invalid extension."""
        mock_suffix.return_value = ".txt"

        result = validate_image_format("test.txt")

        assert result is False

    @patch("pathlib.Path.suffix")
    @patch("PIL.Image.open")
    def test_validate_image_format_corrupt_file(self, mock_open, mock_suffix):
        """Test image format validation with corrupt file."""
        mock_suffix.return_value = ".png"
        mock_open.side_effect = Exception("Corrupt file")

        result = validate_image_format("corrupt.png")

        assert result is False

    @patch("tempfile.mkstemp")
    @patch("os.close")
    @patch("finisher.core.utils.get_docs_temp_dir")
    def test_create_temp_file_success(
        self, mock_get_docs_temp_dir, mock_close, mock_mkstemp
    ):
        """Test successful temporary file creation."""
        mock_get_docs_temp_dir.return_value = "/project/docs/temp"
        mock_mkstemp.return_value = (123, "/project/docs/temp/test_file.png")
        image = Mock(spec=Image.Image)

        result = create_temp_file(image)

        assert result == "/project/docs/temp/test_file.png"
        mock_close.assert_called_once_with(123)
        image.save.assert_called_once_with("/project/docs/temp/test_file.png")
        mock_mkstemp.assert_called_once_with(
            suffix=".png", prefix="finisher_", dir="/project/docs/temp"
        )

    @patch("tempfile.mkstemp")
    def test_create_temp_file_error(self, mock_mkstemp):
        """Test temporary file creation with error."""
        mock_mkstemp.side_effect = Exception("Cannot create temp file")
        image = Mock(spec=Image.Image)

        with pytest.raises(IOError, match="Cannot create temporary file"):
            create_temp_file(image)

    @patch("os.path.exists")
    @patch("os.unlink")
    @patch("finisher.core.utils._temp_files", ["file1.tmp", "file2.tmp"])
    def test_cleanup_temp_files(self, mock_unlink, mock_exists):
        """Test temporary files cleanup."""
        mock_exists.return_value = True

        cleanup_temp_files()

        assert mock_unlink.call_count == 2
        mock_unlink.assert_any_call("file1.tmp")
        mock_unlink.assert_any_call("file2.tmp")

    @patch("PIL.Image.open")
    @patch("os.path.getsize")
    def test_get_image_info_success(self, mock_getsize, mock_open):
        """Test successful image info retrieval."""
        mock_image = Mock()
        mock_image.format = "PNG"
        mock_image.mode = "RGB"
        mock_image.size = (800, 600)
        mock_image.width = 800
        mock_image.height = 600
        mock_image.info = {}
        mock_open.return_value.__enter__.return_value = mock_image
        mock_getsize.return_value = 1024000

        result = get_image_info("test.png")

        expected = {
            "format": "PNG",
            "mode": "RGB",
            "size": (800, 600),
            "width": 800,
            "height": 600,
            "has_transparency": False,
            "file_size": 1024000,
        }
        assert result == expected

    def test_convert_image_format_no_conversion_needed(self):
        """Test image format conversion when no conversion is needed."""
        image = Mock(spec=Image.Image)
        image.mode = "RGB"

        result = convert_image_format(image, "RGB")

        assert result == image

    def test_convert_image_format_conversion_needed(self):
        """Test image format conversion when conversion is needed."""
        image = Mock(spec=Image.Image)
        image.mode = "RGBA"
        converted_image = Mock(spec=Image.Image)
        image.convert.return_value = converted_image

        result = convert_image_format(image, "RGB")

        assert result == converted_image
        image.convert.assert_called_once_with("RGB")

    @patch("os.path.isfile")
    @patch("finisher.core.utils.validate_image_format")
    def test_is_image_file_true(self, mock_validate, mock_isfile):
        """Test is_image_file with valid image file."""
        mock_isfile.return_value = True
        mock_validate.return_value = True

        result = is_image_file("test.png")

        assert result is True

    @patch("os.path.isfile")
    def test_is_image_file_not_file(self, mock_isfile):
        """Test is_image_file with non-existent file."""
        mock_isfile.return_value = False

        result = is_image_file("nonexistent.png")

        assert result is False

    def test_get_supported_formats(self):
        """Test getting supported formats list."""
        result = get_supported_formats()

        assert isinstance(result, list)
        assert ".png" in result
        assert ".jpg" in result
        assert ".jpeg" in result
