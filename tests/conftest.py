"""Pytest configuration and fixtures."""

import pytest
from unittest.mock import Mock
from PIL import Image
import tempfile
import os


@pytest.fixture
def mock_image():
    """Create a mock PIL Image for testing."""
    image = Mock(spec=Image.Image)
    image.size = (512, 512)
    image.mode = 'RGB'
    image.format = 'PNG'
    return image


@pytest.fixture
def test_image():
    """Create a real test image for testing."""
    return Image.new('RGB', (100, 100), color='red')


@pytest.fixture
def temp_image_file(test_image):
    """Create a temporary image file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        test_image.save(tmp.name, 'PNG')
        yield tmp.name
    
    # Cleanup
    try:
        os.unlink(tmp.name)
    except OSError:
        pass


@pytest.fixture
def mock_auto1111_client():
    """Create a mock Auto1111Client for testing."""
    client = Mock()
    client.base_url = "http://test.local:7860"
    client.timeout = 30
    
    # Mock API responses
    client.get_upscalers.return_value = [
        {"name": "Lanczos", "scale": 4},
        {"name": "ESRGAN", "scale": 4}
    ]
    
    client.get_models.return_value = [
        {"title": "test_model.safetensors", "model_name": "test_model"}
    ]
    
    client.get_samplers.return_value = [
        {"name": "Euler", "aliases": ["euler"]},
        {"name": "Euler a", "aliases": ["euler_a"]}
    ]
    
    client.get_schedulers.return_value = [
        {"name": "Automatic", "label": "Automatic"}
    ]
    
    client.get_progress.return_value = {
        "progress": 0.0,
        "eta_relative": None,
        "state": {
            "job": None,
            "job_timestamp": None
        }
    }
    
    client.health_check.return_value = True
    
    return client


@pytest.fixture
def sample_processing_config():
    """Create a sample processing configuration."""
    return {
        "upscaler": "Lanczos",
        "scale_factor": 2.5,
        "denoising_strength": 0.15,
        "tile_overlap": 64,
        "steps": 25,
        "sampler_name": "Euler a",
        "cfg_scale": 10,
        "scheduler": "Automatic"
    }


@pytest.fixture
def sample_api_response():
    """Create a sample API response."""
    return {
        "images": ["base64_encoded_image_data"],
        "parameters": {
            "prompt": "test prompt",
            "negative_prompt": "test negative prompt"
        }
    }


@pytest.fixture
def sample_progress_response():
    """Create a sample progress response."""
    return {
        "progress": 0.5,
        "eta_relative": 30.0,
        "state": {
            "skipped": False,
            "interrupted": False,
            "stopping_generation": False,
            "job": "Processing",
            "job_count": 1,
            "job_timestamp": "20231201120000",
            "job_no": 1,
            "sampling_step": 10,
            "sampling_steps": 20
        },
        "current_image": None,
        "textinfo": None
    }
