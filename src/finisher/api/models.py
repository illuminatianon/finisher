"""Data models for Auto1111 API responses and configuration."""

from dataclasses import dataclass
from typing import List, Optional, Any, Dict


@dataclass
class UpscalerInfo:
    """Information about an available upscaler."""
    name: str
    model_name: Optional[str] = None
    model_path: Optional[str] = None
    model_url: Optional[str] = None
    scale: int = 4


@dataclass
class ModelInfo:
    """Information about an available SD model."""
    title: str
    model_name: str
    hash: Optional[str] = None
    sha256: Optional[str] = None
    filename: Optional[str] = None
    config: Optional[str] = None


@dataclass
class SamplerInfo:
    """Information about an available sampler."""
    name: str
    aliases: List[str]


@dataclass
class SchedulerInfo:
    """Information about an available scheduler."""
    name: str
    label: str


@dataclass
class ProgressState:
    """State information from progress endpoint."""
    skipped: bool = False
    interrupted: bool = False
    stopping_generation: bool = False
    job: Optional[str] = None
    job_count: int = 0
    job_timestamp: Optional[str] = None
    job_no: int = 0
    sampling_step: int = 0
    sampling_steps: int = 0


@dataclass
class ProgressInfo:
    """Progress information from Auto1111."""
    progress: float = 0.0
    eta_relative: Optional[float] = None
    state: ProgressState = None
    current_image: Optional[str] = None
    textinfo: Optional[str] = None
    
    def __post_init__(self):
        if self.state is None:
            self.state = ProgressState()


@dataclass
class ProcessingConfig:
    """Configuration for image processing."""
    upscaler: str
    scale_factor: float = 2.5
    denoising_strength: float = 0.15
    tile_overlap: int = 64
    steps: int = 25
    sampler_name: str = "Euler a"
    cfg_scale: int = 10
    scheduler: str = "Automatic"
    
    def to_img2img_payload(self, init_images: List[str], prompt: str = "",
                          negative_prompt: str = "") -> Dict[str, Any]:
        """Convert to img2img API payload.

        Args:
            init_images: List of base64 encoded images
            prompt: Generation prompt
            negative_prompt: Negative prompt

        Returns:
            img2img API payload dictionary
        """
        import logging
        logger = logging.getLogger(__name__)

        # Log the configuration values being used
        logger.info(f"Creating img2img payload with config: upscaler={self.upscaler}, "
                   f"scale_factor={self.scale_factor} ({type(self.scale_factor).__name__}), "
                   f"denoising_strength={self.denoising_strength} ({type(self.denoising_strength).__name__}), "
                   f"tile_overlap={self.tile_overlap} ({type(self.tile_overlap).__name__}), "
                   f"steps={self.steps} ({type(self.steps).__name__}), "
                   f"cfg_scale={self.cfg_scale} ({type(self.cfg_scale).__name__})")

        script_args = [
            float(self.scale_factor),
            int(self.tile_overlap),
            self.upscaler,
        ]

        logger.info(f"script_args after conversion: {script_args} (types: {[type(arg).__name__ for arg in script_args]})")

        return {
            "init_images": init_images,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "script_name": "SD upscale",
            "script_args": script_args,
            "denoising_strength": float(self.denoising_strength),
            "steps": int(self.steps),
            "sampler_name": self.sampler_name,
            "cfg_scale": float(self.cfg_scale),
            "batch_size": 1,
            "save_images": False,
            "scheduler": self.scheduler
        }
    
    def to_extra_single_image_payload(self, image: str, 
                                    upscaling_resize: float = 1.5) -> Dict[str, Any]:
        """Convert to extra-single-image API payload.
        
        Args:
            image: Base64 encoded image
            upscaling_resize: Scale factor for final pass
            
        Returns:
            extra-single-image API payload dictionary
        """
        return {
            "image": image,
            "upscaling_resize": upscaling_resize,
            "upscaler_1": self.upscaler,
            "save_images": True
        }
