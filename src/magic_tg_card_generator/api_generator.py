"""API-based image generation using Replicate."""

import logging
import os
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional

import replicate
import requests
from dotenv import load_dotenv
from PIL import Image

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class ReplicateGenerator:
    """Generate images using Replicate API."""

    # Available models on Replicate
    MODELS = {
        "flux-schnell": "black-forest-labs/flux-schnell",
        "flux-dev": "black-forest-labs/flux-dev",
        "flux-pro": "black-forest-labs/flux-pro",
        "sdxl": "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
        "sdxl-lightning": "bytedance/sdxl-lightning-4step:727e49a643e999d602a896c774a0658ffefea21465756a6ce24b7ea4165eba6a",
    }

    def __init__(
        self,
        api_token: Optional[str] = None,
        output_dir: Path = Path("output/images"),
        model: str = "flux-schnell",
    ):
        """Initialize Replicate API client.

        Args:
            api_token: Replicate API token (or use REPLICATE_API_TOKEN env var)
            output_dir: Directory to save generated images
            model: Model to use (flux-schnell, flux-dev, flux-pro, sdxl, sdxl-lightning)
        """
        self.api_token = api_token or os.getenv("REPLICATE_API_TOKEN")
        if not self.api_token:
            raise ValueError(
                "Replicate API token required. Set REPLICATE_API_TOKEN env var or pass api_token"
            )

        # Set API token for replicate client
        os.environ["REPLICATE_API_TOKEN"] = self.api_token

        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.model = self.MODELS.get(model, model)
        logger.info(f"Using Replicate model: {self.model}")

    def generate(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        num_inference_steps: Optional[int] = None,
        guidance_scale: Optional[float] = None,
        seed: Optional[int] = None,
        output_name: Optional[str] = None,
        **kwargs,
    ) -> Path:
        """Generate an image using Replicate API.

        Args:
            prompt: Text prompt for generation
            width: Image width
            height: Image height
            num_inference_steps: Number of inference steps (model-specific)
            guidance_scale: Guidance scale (model-specific)
            seed: Random seed
            output_name: Optional name for output file
            **kwargs: Additional model-specific parameters

        Returns:
            Path to saved image
        """
        logger.info(f"Generating image via API: {prompt[:50]}...")

        # Build input parameters based on model
        input_params = {
            "prompt": prompt,
            "width": width,
            "height": height,
        }

        # Add optional parameters if provided
        if seed is not None:
            input_params["seed"] = seed

        # Model-specific defaults
        if "flux-schnell" in self.model:
            # FLUX schnell defaults
            input_params["num_inference_steps"] = num_inference_steps or 4
            # FLUX schnell doesn't use guidance_scale
        elif "flux-dev" in self.model or "flux-pro" in self.model:
            # FLUX dev/pro defaults
            input_params["num_inference_steps"] = num_inference_steps or 25
            input_params["guidance_scale"] = guidance_scale or 3.5
        elif "sdxl-lightning" in self.model:
            # SDXL Lightning defaults (4-step)
            input_params["num_inference_steps"] = num_inference_steps or 4
            input_params["guidance_scale"] = guidance_scale or 0
        else:
            # Standard SDXL defaults
            input_params["num_inference_steps"] = num_inference_steps or 30
            input_params["guidance_scale"] = guidance_scale or 7.5

        # Add any additional kwargs
        input_params.update(kwargs)

        try:
            # Run the model
            logger.info(f"Calling Replicate API with model {self.model}")
            start_time = time.time()

            output = replicate.run(self.model, input=input_params)

            # Output is usually a list of URLs
            if isinstance(output, list):
                image_url = output[0]
            else:
                image_url = output

            elapsed = time.time() - start_time
            logger.info(f"Image generated in {elapsed:.1f}s")

            # Download the image
            response = requests.get(image_url)
            response.raise_for_status()

            # Open and save image
            image = Image.open(BytesIO(response.content))

            # Generate filename
            if output_name:
                filename = f"{output_name}.png"
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"api_{timestamp}.png"

            output_path = self.output_dir / filename
            image.save(output_path)

            logger.info(f"Image saved to: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"API generation failed: {e}")
            raise

    def generate_batch(self, prompts: list[str], **kwargs) -> list[Path]:
        """Generate multiple images.

        Args:
            prompts: List of prompts
            **kwargs: Generation parameters

        Returns:
            List of paths to generated images
        """
        paths = []
        for i, prompt in enumerate(prompts):
            logger.info(f"Generating {i+1}/{len(prompts)}")
            try:
                path = self.generate(prompt, **kwargs)
                paths.append(path)
            except Exception as e:
                logger.error(f"Failed to generate image {i+1}: {e}")
                continue
        return paths

    def list_models(self) -> dict[str, str]:
        """List available models."""
        return self.MODELS


# Unified interface for both local and API generation
class HybridGenerator:
    """Unified interface for local and API-based generation."""

    def __init__(
        self,
        use_api: bool = False,
        api_model: str = "flux-schnell",
        local_model: str = "SDXL_LOCAL",
        output_dir: Path = Path("output/images"),
    ):
        """Initialize hybrid generator.

        Args:
            use_api: Whether to use API (True) or local (False)
            api_model: Model to use for API generation
            local_model: Model to use for local generation
            output_dir: Directory for output images
        """
        self.use_api = use_api
        self.output_dir = output_dir

        if use_api:
            self.generator = ReplicateGenerator(output_dir=output_dir, model=api_model)
            logger.info(f"Using API generation with {api_model}")
        else:
            from magic_tg_card_generator.image_generator import (
                ImageGenerator,
                ModelConfig,
            )

            self.generator = ImageGenerator(
                model=ModelConfig[local_model]
                if isinstance(local_model, str)
                else local_model,
                output_dir=output_dir,
            )
            self.generator.load_model()
            logger.info(f"Using local generation with {local_model}")

    def generate(self, prompt: str, **kwargs) -> Path:
        """Generate an image using configured backend."""
        if self.use_api:
            return self.generator.generate(prompt, **kwargs)
        else:
            # Local generation uses different parameter names
            from magic_tg_card_generator.image_generator import GenerationConfig

            config = GenerationConfig(
                num_inference_steps=kwargs.get("num_inference_steps", 30),
                guidance_scale=kwargs.get("guidance_scale", 7.5),
                width=kwargs.get("width", 1024),
                height=kwargs.get("height", 1024),
                seed=kwargs.get("seed"),
            )

            # Create a dummy card for local generation
            from magic_tg_card_generator.models import Card, CardType, Color

            card = Card(
                name=kwargs.get("output_name", "generated"),
                card_type=CardType.CREATURE,
                color=Color.COLORLESS,
                mana_cost="0",
                text="",
            )

            return self.generator.generate_card_art(
                card, config=config, custom_prompt=prompt
            )


# Quick test function
def test_replicate():
    """Test Replicate API generation."""
    generator = ReplicateGenerator(model="flux-schnell")

    # Test Harry Potter image
    path = generator.generate(
        prompt="Harry Potter flying on a broomstick over the Quidditch field, wearing Hogwarts robes, holding his wand, iconic lightning scar on his forehead, detailed fantasy realism, magical atmosphere",
        width=1024,
        height=1024,
        output_name="harry_potter_api",
    )

    print(f"✅ Generated Harry Potter image: {path}")
    return path


if __name__ == "__main__":
    test_replicate()
