"""Configuration manager for Auto1111 API settings."""

import logging
from typing import List, Optional
from .client import Auto1111Client
from .models import (
    UpscalerInfo,
    ModelInfo,
    SamplerInfo,
    SchedulerInfo,
    ProcessingConfig,
)

logger = logging.getLogger(__name__)


class ConfigurationManager:
    """Manages Auto1111 API configuration and caching."""

    def __init__(self, client: Auto1111Client):
        """Initialize configuration manager.

        Args:
            client: Auto1111 API client instance
        """
        self.client = client
        self.upscalers: List[UpscalerInfo] = []
        self.models: List[ModelInfo] = []
        self.samplers: List[SamplerInfo] = []
        self.schedulers: List[SchedulerInfo] = []
        self.loading = False
        self.error: Optional[str] = None

    def load_upscalers(self) -> List[UpscalerInfo]:
        """Load available upscalers from Auto1111.

        Returns:
            List of upscaler information

        Raises:
            Exception: If loading fails
        """
        try:
            self.loading = True
            self.error = None

            raw_upscalers = self.client.get_upscalers()
            self.upscalers = [
                UpscalerInfo(
                    name=upscaler["name"],
                    model_name=upscaler.get("model_name"),
                    model_path=upscaler.get("model_path"),
                    model_url=upscaler.get("model_url"),
                    scale=upscaler.get("scale", 4),
                )
                for upscaler in raw_upscalers
            ]

            logger.info(f"Loaded {len(self.upscalers)} upscalers")
            return self.upscalers

        except Exception as error:
            self.error = str(error)
            logger.error(f"Failed to load upscalers: {error}")
            raise
        finally:
            self.loading = False

    def load_models(self) -> List[ModelInfo]:
        """Load available models from Auto1111.

        Returns:
            List of model information

        Raises:
            Exception: If loading fails
        """
        try:
            self.loading = True
            self.error = None

            raw_models = self.client.get_models()
            self.models = [
                ModelInfo(
                    title=model["title"],
                    model_name=model["model_name"],
                    hash=model.get("hash"),
                    sha256=model.get("sha256"),
                    filename=model.get("filename"),
                    config=model.get("config"),
                )
                for model in raw_models
            ]

            logger.info(f"Loaded {len(self.models)} models")
            return self.models

        except Exception as error:
            self.error = str(error)
            logger.error(f"Failed to load models: {error}")
            raise
        finally:
            self.loading = False

    def load_samplers(self) -> List[SamplerInfo]:
        """Load available samplers from Auto1111.

        Returns:
            List of sampler information

        Raises:
            Exception: If loading fails
        """
        try:
            self.loading = True
            self.error = None

            raw_samplers = self.client.get_samplers()
            self.samplers = [
                SamplerInfo(name=sampler["name"], aliases=sampler.get("aliases", []))
                for sampler in raw_samplers
            ]

            logger.info(f"Loaded {len(self.samplers)} samplers")
            return self.samplers

        except Exception as error:
            self.error = str(error)
            logger.error(f"Failed to load samplers: {error}")
            raise
        finally:
            self.loading = False

    def load_schedulers(self) -> List[SchedulerInfo]:
        """Load available schedulers from Auto1111.

        Returns:
            List of scheduler information

        Raises:
            Exception: If loading fails
        """
        try:
            self.loading = True
            self.error = None

            raw_schedulers = self.client.get_schedulers()
            self.schedulers = [
                SchedulerInfo(
                    name=scheduler["name"],
                    label=scheduler.get("label", scheduler["name"]),
                )
                for scheduler in raw_schedulers
            ]

            logger.info(f"Loaded {len(self.schedulers)} schedulers")
            return self.schedulers

        except Exception as error:
            self.error = str(error)
            logger.error(f"Failed to load schedulers: {error}")
            raise
        finally:
            self.loading = False

    def load_all_options(self) -> None:
        """Load all configuration options from Auto1111.

        Raises:
            Exception: If any loading operation fails
        """
        logger.info("Loading all Auto1111 configuration options")

        self.load_upscalers()
        self.load_models()
        self.load_samplers()
        self.load_schedulers()

        logger.info("Successfully loaded all configuration options")

    def get_default_config(self) -> ProcessingConfig:
        """Get default processing configuration.

        Returns:
            Default processing configuration
        """
        # Use first available upscaler or fallback
        default_upscaler = self.upscalers[0].name if self.upscalers else "Lanczos"

        return ProcessingConfig(
            upscaler=default_upscaler,
            scale_factor=2.5,
            denoising_strength=0.15,
            tile_overlap=64,
            steps=25,
            sampler_name="Euler a",
            cfg_scale=10,
            scheduler="Automatic",
        )

    def validate_api_connection(self) -> bool:
        """Validate API connection to Auto1111.

        Returns:
            True if connection is valid, False otherwise
        """
        return self.client.health_check()
