"""FLUX model handler for optimal performance on Apple Silicon."""

import logging
import os
from pathlib import Path
from typing import Optional

import torch
from diffusers import FluxPipeline
from huggingface_hub import login

logger = logging.getLogger(__name__)


class FluxHandler:
    """Optimized FLUX handler for M1/M2/M3 Macs."""

    def __init__(
        self,
        model_dir: Path = Path("models"),
        output_dir: Path = Path("output/images"),
        use_local_weights: bool = True,
    ):
        self.model_dir = model_dir
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.use_local_weights = use_local_weights
        self.pipeline = None

        # Device configuration for Apple Silicon
        if torch.backends.mps.is_available():
            self.device = "mps"
            self.dtype = torch.float32  # MPS requires float32
            logger.info("Using MPS (Apple Silicon GPU)")
        else:
            self.device = "cpu"
            self.dtype = torch.float32
            logger.info("Using CPU")

    def load_model(self, force_reload: bool = False) -> None:
        """Load FLUX model with optimizations."""
        if self.pipeline and not force_reload:
            return

        # Authenticate if token available
        hf_token = os.getenv("HF_TOKEN")
        if hf_token:
            login(token=hf_token)

        logger.info("Loading FLUX model...")

        try:
            # Load from cache or download
            self.pipeline = FluxPipeline.from_pretrained(
                "black-forest-labs/FLUX.1-dev",
                torch_dtype=self.dtype,
                cache_dir=self.model_dir,
                local_files_only=False,  # Allow downloading if needed
                resume_download=True,
                variant="fp16" if self.device == "cuda" else None,
                use_safetensors=True,
            )

            # Move to device
            self.pipeline = self.pipeline.to(self.device)

            # Apply MPS optimizations
            if self.device == "mps":
                # Enable attention slicing for memory efficiency
                if hasattr(self.pipeline, "enable_attention_slicing"):
                    self.pipeline.enable_attention_slicing()

                # Enable VAE slicing for large images
                if hasattr(self.pipeline, "enable_vae_slicing"):
                    self.pipeline.enable_vae_slicing()

                # Enable sequential CPU offload if available
                if hasattr(self.pipeline, "enable_sequential_cpu_offload"):
                    try:
                        self.pipeline.enable_sequential_cpu_offload()
                        logger.info("Enabled sequential CPU offload")
                    except:
                        pass

            # Optionally load local weights if available
            if self.use_local_weights:
                local_weights = self.model_dir / "flux1-dev.safetensors"
                if local_weights.exists():
                    logger.info(f"Loading local weights from {local_weights}")
                    from safetensors.torch import load_file

                    state_dict = load_file(str(local_weights), device=str(self.device))

                    # Apply weights to the transformer
                    if hasattr(self.pipeline, "transformer"):
                        self.pipeline.transformer.load_state_dict(
                            state_dict, strict=False
                        )
                        logger.info("Local weights loaded to transformer")
                    elif hasattr(self.pipeline, "unet"):
                        self.pipeline.unet.load_state_dict(state_dict, strict=False)
                        logger.info("Local weights loaded to unet")

            logger.info("FLUX model loaded successfully!")

        except Exception as e:
            logger.error(f"Failed to load FLUX: {e}")
            raise

    def generate(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        num_inference_steps: int = 20,
        guidance_scale: float = 3.5,
        seed: Optional[int] = None,
        output_name: Optional[str] = None,
    ) -> Path:
        """Generate an image with FLUX."""
        if not self.pipeline:
            self.load_model()

        # Set seed if provided
        generator = None
        if seed is not None:
            generator = torch.Generator(device=self.device).manual_seed(seed)

        logger.info(f"Generating image: {prompt[:50]}...")

        # Generate with optimized settings
        with torch.no_grad():
            result = self.pipeline(
                prompt=prompt,
                width=width,
                height=height,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                generator=generator,
                max_sequence_length=512,  # Optimize token usage
            )

        # Save image
        image = result.images[0]

        if output_name:
            filename = f"{output_name}.png"
        else:
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"flux_{timestamp}.png"

        output_path = self.output_dir / filename
        image.save(output_path)

        logger.info(f"Image saved to: {output_path}")
        return output_path

    def generate_batch(self, prompts: list[str], **kwargs) -> list[Path]:
        """Generate multiple images."""
        paths = []
        for i, prompt in enumerate(prompts):
            logger.info(f"Generating {i+1}/{len(prompts)}")
            path = self.generate(prompt, **kwargs)
            paths.append(path)
        return paths

    def clear_memory(self) -> None:
        """Clear memory cache."""
        if self.device == "mps":
            # MPS memory management
            if self.pipeline:
                del self.pipeline
                self.pipeline = None
            torch.mps.empty_cache()
            logger.info("MPS memory cleared")


# Quick test function
def test_flux():
    """Test FLUX generation."""
    from dotenv import load_dotenv

    load_dotenv()

    handler = FluxHandler()
    handler.load_model()

    # Test generation
    path = handler.generate(
        prompt="A majestic dragon breathing fire, digital art masterpiece",
        width=1024,
        height=1024,
        num_inference_steps=20,
        guidance_scale=3.5,
        output_name="flux_dragon_test",
    )

    print(f"✅ Generated: {path}")


if __name__ == "__main__":
    test_flux()
