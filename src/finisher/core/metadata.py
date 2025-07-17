"""Image metadata extraction for generation parameters."""

import logging
from typing import Tuple, Dict, Any, Optional
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import re

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """Extracts generation parameters from image metadata."""
    
    def extract_prompts(self, image: Image.Image) -> Tuple[str, str]:
        """Extract prompt and negative prompt from image metadata.
        
        Args:
            image: PIL Image object
            
        Returns:
            Tuple of (prompt, negative_prompt)
        """
        prompt = ""
        negative_prompt = ""
        
        try:
            # Check for PNG text chunks (most common format)
            if hasattr(image, 'text') and image.text:
                prompt, negative_prompt = self._extract_from_png_text(image.text)
            
            # Check for EXIF data (alternative format)
            elif hasattr(image, '_getexif') and image._getexif():
                prompt, negative_prompt = self._extract_from_exif(image._getexif())
            
            logger.debug(f"Extracted metadata - Prompt: {prompt[:50]}..., "
                        f"Negative: {negative_prompt[:50]}...")
            
        except Exception as e:
            logger.warning(f"Failed to extract metadata: {e}")
        
        return prompt, negative_prompt
    
    def _extract_from_png_text(self, text_data: Dict[str, str]) -> Tuple[str, str]:
        """Extract prompts from PNG text chunks.
        
        Args:
            text_data: PNG text chunk data
            
        Returns:
            Tuple of (prompt, negative_prompt)
        """
        prompt = ""
        negative_prompt = ""
        
        # Check common PNG text keys
        if "parameters" in text_data:
            prompt, negative_prompt = self._parse_parameters_string(text_data["parameters"])
        elif "prompt" in text_data:
            prompt = text_data["prompt"]
            negative_prompt = text_data.get("negative_prompt", "")
        elif "Description" in text_data:
            # Some tools use Description field
            prompt, negative_prompt = self._parse_parameters_string(text_data["Description"])
        
        return prompt, negative_prompt
    
    def _extract_from_exif(self, exif_data: Dict[int, Any]) -> Tuple[str, str]:
        """Extract prompts from EXIF data.
        
        Args:
            exif_data: EXIF data dictionary
            
        Returns:
            Tuple of (prompt, negative_prompt)
        """
        prompt = ""
        negative_prompt = ""
        
        # EXIF tag 270 is ImageDescription
        if 270 in exif_data:
            description = exif_data[270]
            if isinstance(description, str):
                prompt, negative_prompt = self._parse_parameters_string(description)
        
        # EXIF tag 37510 is UserComment
        if 37510 in exif_data and not prompt:
            user_comment = exif_data[37510]
            if isinstance(user_comment, (str, bytes)):
                if isinstance(user_comment, bytes):
                    try:
                        user_comment = user_comment.decode('utf-8')
                    except UnicodeDecodeError:
                        user_comment = user_comment.decode('utf-8', errors='ignore')
                prompt, negative_prompt = self._parse_parameters_string(user_comment)
        
        return prompt, negative_prompt
    
    def _parse_parameters_string(self, parameters: str) -> Tuple[str, str]:
        """Parse parameters string to extract prompt and negative prompt.
        
        Args:
            parameters: Parameters string from metadata
            
        Returns:
            Tuple of (prompt, negative_prompt)
        """
        prompt = ""
        negative_prompt = ""
        
        try:
            # Common format: "prompt\nNegative prompt: negative_prompt\nSteps: ..."
            lines = parameters.split('\n')
            
            current_section = "prompt"
            prompt_lines = []
            negative_lines = []
            
            for line in lines:
                line = line.strip()
                
                if line.startswith("Negative prompt:"):
                    current_section = "negative"
                    # Extract negative prompt from this line
                    negative_part = line[len("Negative prompt:"):].strip()
                    if negative_part:
                        negative_lines.append(negative_part)
                elif line.startswith(("Steps:", "Sampler:", "CFG scale:", "Seed:", 
                                    "Size:", "Model:", "Denoising strength:")):
                    # End of prompts, start of generation parameters
                    break
                elif current_section == "prompt" and line:
                    prompt_lines.append(line)
                elif current_section == "negative" and line:
                    negative_lines.append(line)
            
            prompt = " ".join(prompt_lines).strip()
            negative_prompt = " ".join(negative_lines).strip()
            
            # Alternative parsing for different formats
            if not prompt and not negative_prompt:
                prompt, negative_prompt = self._parse_alternative_format(parameters)
            
        except Exception as e:
            logger.warning(f"Failed to parse parameters string: {e}")
        
        return prompt, negative_prompt
    
    def _parse_alternative_format(self, parameters: str) -> Tuple[str, str]:
        """Parse alternative parameter formats.
        
        Args:
            parameters: Parameters string
            
        Returns:
            Tuple of (prompt, negative_prompt)
        """
        prompt = ""
        negative_prompt = ""
        
        # Try regex patterns for different formats
        patterns = [
            # Format: prompt<negative:negative_prompt>
            r'^(.+?)<negative:(.+?)>',
            # Format: [prompt] [negative:negative_prompt]
            r'^\[(.+?)\]\s*\[negative:(.+?)\]',
            # Format: prompt | negative: negative_prompt
            r'^(.+?)\s*\|\s*negative:\s*(.+?)$',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, parameters, re.DOTALL | re.IGNORECASE)
            if match:
                prompt = match.group(1).strip()
                negative_prompt = match.group(2).strip()
                break
        
        # If no pattern matches, treat entire string as prompt
        if not prompt and parameters.strip():
            prompt = parameters.strip()
        
        return prompt, negative_prompt
    
    def extract_generation_info(self, image: Image.Image) -> Dict[str, Any]:
        """Extract all available generation information from image.
        
        Args:
            image: PIL Image object
            
        Returns:
            Dictionary containing all extracted generation parameters
        """
        info = {
            "prompt": "",
            "negative_prompt": "",
            "steps": None,
            "sampler": None,
            "cfg_scale": None,
            "seed": None,
            "size": None,
            "model": None,
            "denoising_strength": None,
        }
        
        try:
            # Extract prompts first
            info["prompt"], info["negative_prompt"] = self.extract_prompts(image)
            
            # Extract other parameters if available
            if hasattr(image, 'text') and image.text:
                parameters = image.text.get("parameters", "")
                if parameters:
                    info.update(self._parse_generation_parameters(parameters))
            
        except Exception as e:
            logger.warning(f"Failed to extract generation info: {e}")
        
        return info
    
    def _parse_generation_parameters(self, parameters: str) -> Dict[str, Any]:
        """Parse generation parameters from parameters string.
        
        Args:
            parameters: Parameters string
            
        Returns:
            Dictionary of parsed parameters
        """
        params = {}
        
        # Common parameter patterns
        patterns = {
            "steps": r"Steps:\s*(\d+)",
            "sampler": r"Sampler:\s*([^,\n]+)",
            "cfg_scale": r"CFG scale:\s*([\d.]+)",
            "seed": r"Seed:\s*(\d+)",
            "size": r"Size:\s*(\d+x\d+)",
            "model": r"Model:\s*([^,\n]+)",
            "denoising_strength": r"Denoising strength:\s*([\d.]+)",
        }
        
        for param_name, pattern in patterns.items():
            match = re.search(pattern, parameters, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                
                # Convert to appropriate type
                if param_name in ["steps", "seed"]:
                    try:
                        params[param_name] = int(value)
                    except ValueError:
                        pass
                elif param_name in ["cfg_scale", "denoising_strength"]:
                    try:
                        params[param_name] = float(value)
                    except ValueError:
                        pass
                else:
                    params[param_name] = value
        
        return params
