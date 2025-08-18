"""Wrapper for FLUX model integration."""

import logging
import sys
from pathlib import Path

import torch
from PIL import Image

logger = logging.getLogger(__name__)

# Add FLUX to path
FLUX_PATH = Path(__file__).parent.parent.parent / "flux-official" / "src"
if FLUX_PATH.exists():
    sys.path.insert(0, str(FLUX_PATH))


def load_flux_model(model_path: str, device: str = "mps"):
    """Load FLUX model from local safetensors file.

    Args:
        model_path: Path to the model file
        device: Device to use (cuda, mps, cpu)

    Returns:
        Loaded model ready for inference
    """
    try:
        from flux.api import ImageRequest
        from flux.cli import SamplingOptions
        from flux.util import load_ae, load_clip, load_flow_model, load_t5

        # Load model components
        logger.info("Loading FLUX components...")

        # Model configuration for FLUX.1-dev
        name = "flux-dev"

        # Load the flow model from safetensors
        model = load_flow_model(name, device=device, hf_download=False)

        # Load other components
        ae = load_ae(name, device=device)
        t5 = load_t5(device=device)
        clip = load_clip(device=device)

        logger.info("FLUX model loaded successfully")

        return {"model": model, "ae": ae, "t5": t5, "clip": clip, "device": device}

    except ImportError as e:
        logger.error(f"Could not import FLUX: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to load FLUX model: {e}")
        raise


def generate_with_flux(
    components: dict,
    prompt: str,
    width: int = 1024,
    height: int = 1024,
    steps: int = 20,
    guidance: float = 3.5,
    seed: int = None,
) -> Image.Image:
    """Generate an image using FLUX.

    Args:
        components: Model components from load_flux_model
        prompt: Text prompt for generation
        width: Image width
        height: Image height
        steps: Number of inference steps
        guidance: Guidance scale
        seed: Random seed

    Returns:
        Generated PIL Image
    """
    try:
        from flux.sampling import (
            denoise,
            get_noise,
            get_schedule,
            unpack,
        )
        from flux.util import SamplingOptions

        # Set up sampling options
        opts = SamplingOptions(
            width=width,
            height=height,
            num_steps=steps,
            guidance=guidance,
            seed=seed,
        )

        # Prepare inputs
        logger.info(f"Generating image with prompt: {prompt[:100]}...")

        # Get text embeddings
        t5_emb = components["t5"](prompt)
        clip_emb = components["clip"](prompt)

        # Prepare latents
        x = get_noise(
            1,  # batch size
            height // 8,
            width // 8,
            device=components["device"],
            dtype=torch.float32,
            seed=opts.seed,
        )

        # Get timestep schedule
        timesteps = get_schedule(
            opts.num_steps,
            x.shape[1] * x.shape[2] // 4,
            shift=True,
        )

        # Sampling loop
        x = denoise(
            components["model"],
            x,
            timesteps,
            guidance=opts.guidance,
            t5_emb=t5_emb,
            clip_emb=clip_emb,
        )

        # Decode latents to image
        x = unpack(x, height // 8, width // 8)
        image = components["ae"].decode(x)

        # Convert to PIL Image
        image = Image.fromarray((image * 255).astype("uint8"))

        logger.info("Image generated successfully")
        return image

    except Exception as e:
        logger.error(f"Failed to generate image: {e}")
        raise


class FLUXImageGenerator:
    """FLUX-based image generator for Magic cards."""

    def __init__(self, model_path: str, device: str = "auto"):
        """Initialize FLUX generator.

        Args:
            model_path: Path to FLUX model file
            device: Device to use (auto, cuda, mps, cpu)
        """
        if device == "auto":
            if torch.cuda.is_available():
                device = "cuda"
            elif torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"

        self.device = device
        self.model_path = model_path
        self.components = None

    def load_model(self):
        """Load the FLUX model."""
        if self.components is None:
            self.components = load_flux_model(self.model_path, self.device)

    def generate(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        steps: int = 20,
        guidance: float = 3.5,
        seed: int = None,
    ) -> Image.Image:
        """Generate an image.

        Args:
            prompt: Text prompt
            width: Image width
            height: Image height
            steps: Inference steps
            guidance: Guidance scale
            seed: Random seed

        Returns:
            Generated PIL Image
        """
        if self.components is None:
            self.load_model()

        return generate_with_flux(
            self.components,
            prompt,
            width,
            height,
            steps,
            guidance,
            seed,
        )
