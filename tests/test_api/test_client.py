"""Tests for API client."""

import pytest
from unittest.mock import Mock, patch
import requests
from finisher.api.client import Auto1111Client


class TestAuto1111Client:
    """Test Auto1111Client class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = Auto1111Client("http://test.local:7860", timeout=30)
    
    def test_init(self):
        """Test client initialization."""
        assert self.client.base_url == "http://test.local:7860"
        assert self.client.timeout == 30
        assert self.client.session is not None
    
    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is stripped from base URL."""
        client = Auto1111Client("http://test.local:7860/")
        assert client.base_url == "http://test.local:7860"
    
    @patch('requests.Session.get')
    def test_get_upscalers_success(self, mock_get):
        """Test successful upscalers retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {"name": "Lanczos", "scale": 4},
            {"name": "ESRGAN", "scale": 4}
        ]
        mock_get.return_value = mock_response
        
        result = self.client.get_upscalers()
        
        assert len(result) == 2
        assert result[0]["name"] == "Lanczos"
        mock_get.assert_called_once_with(
            "http://test.local:7860/sdapi/v1/upscalers",
            timeout=30
        )
    
    @patch('requests.Session.get')
    def test_get_upscalers_http_error(self, mock_get):
        """Test upscalers retrieval with HTTP error."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response
        
        with pytest.raises(requests.HTTPError):
            self.client.get_upscalers()
    
    @patch('requests.Session.get')
    def test_get_models_success(self, mock_get):
        """Test successful models retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {"title": "model1.safetensors", "model_name": "model1"}
        ]
        mock_get.return_value = mock_response
        
        result = self.client.get_models()
        
        assert len(result) == 1
        assert result[0]["model_name"] == "model1"
        mock_get.assert_called_once_with(
            "http://test.local:7860/sdapi/v1/sd-models",
            timeout=30
        )
    
    @patch('requests.Session.get')
    def test_get_samplers_success(self, mock_get):
        """Test successful samplers retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {"name": "Euler", "aliases": ["euler"]},
            {"name": "Euler a", "aliases": ["euler_a"]}
        ]
        mock_get.return_value = mock_response
        
        result = self.client.get_samplers()
        
        assert len(result) == 2
        assert result[0]["name"] == "Euler"
        mock_get.assert_called_once_with(
            "http://test.local:7860/sdapi/v1/samplers",
            timeout=30
        )
    
    @patch('requests.Session.get')
    def test_get_schedulers_success(self, mock_get):
        """Test successful schedulers retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {"name": "Automatic", "label": "Automatic"}
        ]
        mock_get.return_value = mock_response
        
        result = self.client.get_schedulers()
        
        assert len(result) == 1
        assert result[0]["name"] == "Automatic"
        mock_get.assert_called_once_with(
            "http://test.local:7860/sdapi/v1/schedulers",
            timeout=30
        )
    
    @patch('requests.Session.get')
    def test_get_progress_success(self, mock_get):
        """Test successful progress retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "progress": 0.5,
            "eta_relative": 30.0,
            "state": {
                "job": "Processing",
                "job_timestamp": "20231201120000"
            }
        }
        mock_get.return_value = mock_response
        
        result = self.client.get_progress()
        
        assert result["progress"] == 0.5
        assert result["eta_relative"] == 30.0
        mock_get.assert_called_once_with(
            "http://test.local:7860/sdapi/v1/progress",
            timeout=10
        )
    
    @patch('requests.Session.post')
    def test_interrupt_success(self, mock_post):
        """Test successful interrupt."""
        mock_response = Mock()
        mock_post.return_value = mock_response
        
        self.client.interrupt()
        
        mock_post.assert_called_once_with(
            "http://test.local:7860/sdapi/v1/interrupt",
            timeout=10
        )
    
    @patch('requests.Session.post')
    def test_img2img_success(self, mock_post):
        """Test successful img2img request."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "images": ["base64_image_data"]
        }
        mock_post.return_value = mock_response
        
        payload = {
            "init_images": ["base64_input"],
            "prompt": "test prompt"
        }
        
        result = self.client.img2img(payload)
        
        assert "images" in result
        assert len(result["images"]) == 1
        mock_post.assert_called_once_with(
            "http://test.local:7860/sdapi/v1/img2img",
            json=payload,
            timeout=30
        )
    
    @patch('requests.Session.post')
    def test_extra_single_image_success(self, mock_post):
        """Test successful extra-single-image request."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "image": "base64_result"
        }
        mock_post.return_value = mock_response
        
        payload = {
            "image": "base64_input",
            "upscaling_resize": 2.0
        }
        
        result = self.client.extra_single_image(payload)
        
        assert "image" in result
        mock_post.assert_called_once_with(
            "http://test.local:7860/sdapi/v1/extra-single-image",
            json=payload,
            timeout=30
        )
    
    @patch('requests.Session.get')
    def test_health_check_success(self, mock_get):
        """Test successful health check."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = self.client.health_check()
        
        assert result is True
        mock_get.assert_called_once_with(
            "http://test.local:7860/sdapi/v1/memory",
            timeout=10
        )
    
    @patch('requests.Session.get')
    def test_health_check_failure(self, mock_get):
        """Test health check with connection error."""
        mock_get.side_effect = requests.ConnectionError("Connection failed")
        
        result = self.client.health_check()
        
        assert result is False
    
    @patch('requests.Session.get')
    def test_health_check_http_error(self, mock_get):
        """Test health check with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        result = self.client.health_check()
        
        assert result is False
