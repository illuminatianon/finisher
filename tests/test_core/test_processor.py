"""Tests for image processor."""

import pytest
from unittest.mock import Mock, patch, mock_open
from PIL import Image
import io
import base64
from finisher.core.processor import ImageProcessor


class TestImageProcessor:
    """Test ImageProcessor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = ImageProcessor()
    
    def test_init(self):
        """Test processor initialization."""
        assert self.processor.metadata_extractor is not None
    
    @patch('finisher.core.processor.validate_image_format')
    @patch('PIL.Image.open')
    @patch('finisher.core.processor.encode_image_to_base64')
    def test_prepare_image_for_processing_success(self, mock_encode, mock_open, mock_validate):
        """Test successful image preparation."""
        # Setup mocks
        mock_validate.return_value = True
        mock_image = Mock(spec=Image.Image)
        mock_image.mode = 'RGB'
        mock_image.size = (512, 512)
        mock_open.return_value.__enter__.return_value = mock_image
        mock_encode.return_value = "base64_encoded_image"
        
        # Mock metadata extraction
        self.processor.metadata_extractor.extract_prompts = Mock(
            return_value=("test prompt", "test negative")
        )
        
        # Test
        result = self.processor.prepare_image_for_processing("test.png")
        
        # Assertions
        assert result == ("base64_encoded_image", "test prompt", "test negative")
        mock_validate.assert_called_once_with("test.png")
        mock_open.assert_called_once_with("test.png")
    
    @patch('finisher.core.processor.validate_image_format')
    def test_prepare_image_for_processing_invalid_format(self, mock_validate):
        """Test image preparation with invalid format."""
        mock_validate.return_value = False
        
        with pytest.raises(ValueError, match="Unsupported image format"):
            self.processor.prepare_image_for_processing("test.txt")
    
    @patch('finisher.core.processor.validate_image_format')
    @patch('PIL.Image.open')
    def test_prepare_image_for_processing_io_error(self, mock_open, mock_validate):
        """Test image preparation with IO error."""
        mock_validate.return_value = True
        mock_open.side_effect = IOError("Cannot open file")
        
        with pytest.raises(IOError, match="Cannot load image"):
            self.processor.prepare_image_for_processing("test.png")
    
    @patch('PIL.Image.open')
    @patch('finisher.core.processor.encode_image_to_base64')
    def test_prepare_image_data_for_processing_success(self, mock_encode, mock_open):
        """Test successful image data preparation."""
        # Setup mocks
        mock_image = Mock(spec=Image.Image)
        mock_image.mode = 'RGB'
        mock_image.size = (512, 512)
        mock_open.return_value = mock_image
        mock_encode.return_value = "base64_encoded_image"
        
        # Mock metadata extraction
        self.processor.metadata_extractor.extract_prompts = Mock(
            return_value=("test prompt", "test negative")
        )
        
        # Test
        image_data = b"fake_image_data"
        result = self.processor.prepare_image_data_for_processing(image_data)
        
        # Assertions
        assert result == ("base64_encoded_image", "test prompt", "test negative")
        mock_open.assert_called_once()
    
    @patch('PIL.Image.open')
    def test_prepare_image_data_for_processing_error(self, mock_open):
        """Test image data preparation with error."""
        mock_open.side_effect = Exception("Invalid image data")
        
        with pytest.raises(IOError, match="Cannot process image data"):
            self.processor.prepare_image_data_for_processing(b"invalid_data")
    
    @patch('finisher.core.processor.decode_base64_to_image')
    def test_process_base64_result_success(self, mock_decode):
        """Test successful base64 result processing."""
        mock_image = Mock(spec=Image.Image)
        mock_image.size = (1024, 1024)
        mock_decode.return_value = mock_image
        
        result = self.processor.process_base64_result("base64_data")
        
        assert result == mock_image
        mock_decode.assert_called_once_with("base64_data")
    
    @patch('finisher.core.processor.decode_base64_to_image')
    def test_process_base64_result_error(self, mock_decode):
        """Test base64 result processing with error."""
        mock_decode.side_effect = Exception("Invalid base64 data")
        
        with pytest.raises(ValueError, match="Invalid base64 image data"):
            self.processor.process_base64_result("invalid_base64")
    
    def test_validate_image_dimensions_valid(self):
        """Test image dimension validation with valid dimensions."""
        mock_image = Mock(spec=Image.Image)
        mock_image.size = (512, 512)
        
        result = self.processor.validate_image_dimensions(mock_image)
        
        assert result is True
    
    def test_validate_image_dimensions_too_large(self):
        """Test image dimension validation with too large dimensions."""
        mock_image = Mock(spec=Image.Image)
        mock_image.size = (5000, 5000)
        
        result = self.processor.validate_image_dimensions(mock_image)
        
        assert result is False
    
    def test_validate_image_dimensions_too_small(self):
        """Test image dimension validation with too small dimensions."""
        mock_image = Mock(spec=Image.Image)
        mock_image.size = (32, 32)
        
        result = self.processor.validate_image_dimensions(mock_image)
        
        assert result is False
    
    def test_resize_image_if_needed_no_resize(self):
        """Test image resizing when no resize is needed."""
        mock_image = Mock(spec=Image.Image)
        mock_image.size = (512, 512)
        
        result = self.processor.resize_image_if_needed(mock_image, max_dimension=1024)
        
        assert result == mock_image
    
    def test_resize_image_if_needed_width_larger(self):
        """Test image resizing when width is larger."""
        mock_image = Mock(spec=Image.Image)
        mock_image.size = (2048, 1024)
        mock_resized = Mock(spec=Image.Image)
        mock_image.resize.return_value = mock_resized
        
        result = self.processor.resize_image_if_needed(mock_image, max_dimension=1024)
        
        assert result == mock_resized
        mock_image.resize.assert_called_once_with((1024, 512), Image.Resampling.LANCZOS)
    
    def test_resize_image_if_needed_height_larger(self):
        """Test image resizing when height is larger."""
        mock_image = Mock(spec=Image.Image)
        mock_image.size = (1024, 2048)
        mock_resized = Mock(spec=Image.Image)
        mock_image.resize.return_value = mock_resized
        
        result = self.processor.resize_image_if_needed(mock_image, max_dimension=1024)
        
        assert result == mock_resized
        mock_image.resize.assert_called_once_with((512, 1024), Image.Resampling.LANCZOS)
