"""Auto1111 API client implementation."""

import requests
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class Auto1111Client:
    """HTTP client for Automatic1111 API communication."""
    
    def __init__(self, base_url: str = "http://127.0.0.1:7860", timeout: int = 300):
        """Initialize the API client.
        
        Args:
            base_url: Base URL for Auto1111 API
            timeout: Request timeout in seconds (default 5 minutes)
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        
    def get_upscalers(self) -> List[Dict[str, Any]]:
        """Get available upscalers from Auto1111.
        
        Returns:
            List of upscaler information dictionaries
            
        Raises:
            requests.RequestException: If API call fails
        """
        response = self.session.get(
            f"{self.base_url}/sdapi/v1/upscalers",
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    def get_models(self) -> List[Dict[str, Any]]:
        """Get available SD models from Auto1111.
        
        Returns:
            List of model information dictionaries
            
        Raises:
            requests.RequestException: If API call fails
        """
        response = self.session.get(
            f"{self.base_url}/sdapi/v1/sd-models", 
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    def get_samplers(self) -> List[Dict[str, Any]]:
        """Get available samplers from Auto1111.
        
        Returns:
            List of sampler information dictionaries
            
        Raises:
            requests.RequestException: If API call fails
        """
        response = self.session.get(
            f"{self.base_url}/sdapi/v1/samplers",
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    def get_schedulers(self) -> List[Dict[str, Any]]:
        """Get available schedulers from Auto1111.
        
        Returns:
            List of scheduler information dictionaries
            
        Raises:
            requests.RequestException: If API call fails
        """
        response = self.session.get(
            f"{self.base_url}/sdapi/v1/schedulers",
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current processing progress from Auto1111.
        
        Returns:
            Progress information dictionary
            
        Raises:
            requests.RequestException: If API call fails
        """
        response = self.session.get(
            f"{self.base_url}/sdapi/v1/progress",
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    
    def interrupt(self) -> None:
        """Interrupt current Auto1111 processing job.
        
        Raises:
            requests.RequestException: If API call fails
        """
        response = self.session.post(
            f"{self.base_url}/sdapi/v1/interrupt",
            timeout=10
        )
        response.raise_for_status()
    
    def img2img(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Perform img2img processing with Auto1111.
        
        Args:
            payload: img2img request payload
            
        Returns:
            Processing result dictionary
            
        Raises:
            requests.RequestException: If API call fails
        """
        response = self.session.post(
            f"{self.base_url}/sdapi/v1/img2img",
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def extra_single_image(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Perform extra single image processing with Auto1111.
        
        Args:
            payload: extra-single-image request payload
            
        Returns:
            Processing result dictionary
            
        Raises:
            requests.RequestException: If API call fails
        """
        response = self.session.post(
            f"{self.base_url}/sdapi/v1/extra-single-image",
            json=payload,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def health_check(self) -> bool:
        """Check if Auto1111 API is available.
        
        Returns:
            True if API is available, False otherwise
        """
        try:
            response = self.session.get(
                f"{self.base_url}/sdapi/v1/memory",
                timeout=10
            )
            return response.status_code == 200
        except requests.RequestException:
            return False
