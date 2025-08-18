"""Image generation for Magic: The Gathering cards using local models."""

import json
import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import torch
from diffusers import DPMSolverMultistepScheduler, StableDiffusionPipeline
from PIL import Image

from magic_tg_card_generator.models import Card, CardType, Color

logger = logging.getLogger(__name__)


class ArtStyle(str, Enum):
    """Available art styles for card generation."""

    OIL_PAINTING = "oil painting, classic art style, brushstrokes, traditional"
    DIGITAL_ART = "digital art, modern, crisp details, vibrant colors"
    FANTASY_REALISM = "fantasy realism, highly detailed, epic, cinematic"
    WATERCOLOR = "watercolor painting, soft edges, flowing colors"
    COMIC_BOOK = "comic book style, bold lines, dynamic composition"
    DARK_GOTHIC = "dark gothic, moody, atmospheric, shadowy"


class ModelConfig(str, Enum):
    """Available Stable Diffusion models."""

    SD_1_4 = "CompVis/stable-diffusion-v1-4"  # ~4GB VRAM, original
    SD_1_5 = "runwayml/stable-diffusion-v1-5"  # ~4GB VRAM, improved
    SD_2_1 = "stabilityai/stable-diffusion-2-1"  # ~5GB VRAM, newer architecture
    SDXL_BASE = "stabilityai/stable-diffusion-xl-base-1.0"  # ~8GB VRAM, highest quality
    SDXL_LOCAL = "models/sd_xl_base_1.0.safetensors"  # Local SDXL model file


class GenerationConfig:
    """Configuration for image generation."""

    def __init__(
        self,
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5,
        height: int = 512,
        width: int = 512,
        seed: Optional[int] = None,
        negative_prompt: Optional[str] = None,
    ):
        self.num_inference_steps = num_inference_steps
        self.guidance_scale = guidance_scale
        self.height = height
        self.width = width
        self.seed = seed
        self.negative_prompt = negative_prompt or (
            "low quality, blurry, pixelated, text, watermark, signature, "
            "extra limbs, deformed, ugly, bad anatomy, bad proportions"
        )


class ImageGenerator:
    """Generate card artwork using local Stable Diffusion models."""

    def __init__(
        self,
        config_file: Optional[Path] = None,
        model: Optional[ModelConfig] = None,
        models_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        device: Optional[str] = None,
        low_memory: bool = False,
    ) -> None:
        """Initialize the image generator.

        Args:
            config_file: Path to JSON configuration file
            model: Model configuration to use (overrides config file)
            models_dir: Directory to cache downloaded models
            output_dir: Directory to save generated images
            device: Device to run on ('cuda', 'mps', 'cpu', or None for auto)
            low_memory: Enable memory optimizations for low VRAM systems
        """
        # Load configuration from file if provided
        self.config = self._load_config(config_file) if config_file else {}

        # Set up directories
        self.output_dir = output_dir or Path(
            self.config.get("output_settings", {}).get("output_dir", "output/images")
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.models_dir = models_dir or Path("models")
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Model configuration
        if model:
            self.model_config = model
        elif "image_generation" in self.config:
            model_name = self.config["image_generation"].get("model", "SD_1_5")
            self.model_config = (
                ModelConfig[model_name]
                if isinstance(model_name, str)
                else ModelConfig.SD_1_5
            )
        else:
            self.model_config = ModelConfig.SD_1_5

        self.device = self._setup_device(
            device or self.config.get("image_generation", {}).get("device")
        )
        self.low_memory = low_memory or self.config.get("image_generation", {}).get(
            "low_memory", False
        )
        self.pipeline: Optional[StableDiffusionPipeline] = None

        logger.info(
            f"ImageGenerator initialized with {self.model_config.value} on {self.device}"
        )

    def _load_config(self, config_file: Path) -> dict[str, Any]:
        """Load configuration from JSON file.

        Args:
            config_file: Path to configuration file

        Returns:
            Configuration dictionary
        """
        if not config_file.exists():
            logger.warning(f"Config file {config_file} not found, using defaults")
            return {}

        with open(config_file) as f:
            config = json.load(f)
            logger.info(f"Loaded configuration from {config_file}")
            return config

    def _setup_device(self, device: Optional[str]) -> str:
        """Determine the best device to use for generation.

        Args:
            device: User-specified device or None for auto-detection

        Returns:
            Device string ('cuda', 'mps', or 'cpu')
        """
        if device and device != "auto":
            return device

        if torch.cuda.is_available():
            logger.info("CUDA available, using GPU")
            return "cuda"
        elif torch.backends.mps.is_available():
            logger.info("MPS available, using Apple Silicon GPU")
            return "mps"
        else:
            logger.warning("No GPU available, using CPU (will be slow)")
            return "cpu"

    def load_model(self, force_reload: bool = False) -> None:
        """Load the Stable Diffusion model.

        Args:
            force_reload: Force reload even if model is already loaded
        """
        if self.pipeline and not force_reload:
            logger.info("Model already loaded")
            return

        logger.info(f"Loading model {self.model_config.value}...")

        try:
            # Check if we're using a local model file
            if self.model_config == ModelConfig.SDXL_LOCAL:
                # Load SDXL pipeline from local file
                from diffusers import StableDiffusionXLPipeline

                local_model_path = Path(self.model_config.value)
                if not local_model_path.exists():
                    raise FileNotFoundError(
                        f"Local model not found: {local_model_path}"
                    )

                logger.info(f"Loading local SDXL model from {local_model_path}")
                # Use float32 for MPS to avoid black images issue
                dtype = (
                    torch.float32 if self.device in ["mps", "cpu"] else torch.float16
                )
                self.pipeline = StableDiffusionXLPipeline.from_single_file(
                    str(local_model_path),
                    torch_dtype=dtype,
                    use_safetensors=True,
                    safety_checker=None,
                    requires_safety_checker=False,
                )
                logger.info(f"Using dtype: {dtype} for device: {self.device}")
            else:
                # Load pipeline from Hugging Face
                # Use float32 for MPS and CPU to avoid black images
                dtype = (
                    torch.float32 if self.device in ["mps", "cpu"] else torch.float16
                )
                logger.info(f"Using dtype: {dtype} for device: {self.device}")

                self.pipeline = StableDiffusionPipeline.from_pretrained(
                    self.model_config.value,
                    torch_dtype=dtype,
                    cache_dir=self.models_dir,
                    safety_checker=None,  # Disable for performance
                    requires_safety_checker=False,
                    local_files_only=False,  # Allow downloading if not cached
                    resume_download=True,  # Resume interrupted downloads
                )

            # Move to device
            self.pipeline = self.pipeline.to(self.device)

            # Use faster scheduler
            self.pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
                self.pipeline.scheduler.config
            )

            # Enable memory optimizations
            if self.low_memory:
                if hasattr(self.pipeline, "enable_attention_slicing"):
                    self.pipeline.enable_attention_slicing()
                # CPU offloading requires accelerate package
                if hasattr(self.pipeline, "enable_model_cpu_offload"):
                    try:
                        self.pipeline.enable_model_cpu_offload()
                    except RuntimeError as e:
                        logger.warning(f"Could not enable CPU offloading: {e}")
                        # Continue without this optimization
            elif hasattr(self.pipeline, "enable_attention_slicing"):
                self.pipeline.enable_attention_slicing()

            logger.info("Model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def generate_card_art(
        self,
        card: Card,
        style: Optional[ArtStyle] = None,
        config: Optional[GenerationConfig] = None,
        custom_prompt: Optional[str] = None,
    ) -> Path:
        """Generate artwork for a Magic card.

        Args:
            card: The card to generate art for
            style: Art style to use (defaults to OIL_PAINTING)
            config: Generation configuration
            custom_prompt: Custom prompt to use instead of auto-generated one

        Returns:
            Path to the generated image
        """
        if style is None:
            style = ArtStyle.OIL_PAINTING
        if config is None:
            # Load generation params from config if available
            if "generation_params" in self.config:
                params = self.config["generation_params"]
                config = GenerationConfig(
                    num_inference_steps=params.get("steps", 30),
                    guidance_scale=params.get("guidance_scale", 7.5),
                    height=params.get("height", 512),
                    width=params.get("width", 512),
                    seed=params.get("seed"),
                    negative_prompt=self.config.get("default_prompts", {}).get(
                        "negative_prompt"
                    ),
                )
            else:
                config = GenerationConfig()

        if not self.pipeline:
            self.load_model()

        # Use custom prompt or build from card
        if custom_prompt:
            prompt = custom_prompt
            # Add style suffix from config if available
            if (
                "default_prompts" in self.config
                and "style_suffix" in self.config["default_prompts"]
            ):
                prompt = f"{prompt}, {self.config['default_prompts']['style_suffix']}"
        else:
            prompt = self._build_prompt(card, style)

        logger.info(f"Generating image for {card.name} with prompt: {prompt[:100]}...")

        # Set seed if provided
        generator = None
        if config.seed is not None:
            generator = torch.Generator(device=self.device).manual_seed(config.seed)

        try:
            # Generate image
            with torch.no_grad():
                result = self.pipeline(
                    prompt=prompt,
                    negative_prompt=config.negative_prompt,
                    width=config.width,
                    height=config.height,
                    num_inference_steps=config.num_inference_steps,
                    guidance_scale=config.guidance_scale,
                    generator=generator,
                )

            # Get the generated image
            if hasattr(result, "images") and result.images:
                image = result.images[0]
                # The pipeline should already return a PIL Image
                if not isinstance(image, Image.Image):
                    logger.error(f"Unexpected image type: {type(image)}")
                    raise ValueError(
                        f"Pipeline returned unexpected image type: {type(image)}"
                    )
                # Log image info for debugging
                logger.info(f"Generated image: {image.size}, mode: {image.mode}")
            else:
                raise ValueError("Pipeline returned no images")

            # Add card frame and text
            final_image = self._add_card_frame(image, card)

            # Save image
            filepath = self._save_image(final_image, card)
            logger.info(f"Image saved to {filepath}")

            return filepath

        except Exception as e:
            logger.error(f"Failed to generate image: {e}")
            raise

    def _build_prompt(self, card: Card, style: ArtStyle) -> str:
        """Build a detailed prompt for image generation.

        Args:
            card: The card to generate art for
            style: The art style to use

        Returns:
            A detailed prompt string
        """
        # Base prompt with card name and type
        prompt_parts = [f"A {card.name}"]

        # Add creature description
        if card.card_type == CardType.CREATURE:
            if card.power and card.toughness:
                if card.power >= 5:
                    prompt_parts.append("powerful and imposing")
                elif card.power <= 2:
                    prompt_parts.append("small but cunning")

        # Add color-specific elements
        color_descriptions = {
            Color.WHITE: "holy, radiant, divine light",
            Color.BLUE: "mystical, arcane, surrounded by water or energy",
            Color.BLACK: "dark, sinister, shadowy atmosphere",
            Color.RED: "fiery, aggressive, volcanic or explosive",
            Color.GREEN: "natural, forest setting, living harmony",
            Color.COLORLESS: "metallic, artificial, otherworldly",
        }

        if card.color in color_descriptions:
            prompt_parts.append(color_descriptions[card.color])

        # Add card text elements if present
        if card.text:
            text_lower = card.text.lower()
            if "flying" in text_lower:
                prompt_parts.append("with wings, airborne")
            if "haste" in text_lower:
                prompt_parts.append("in motion, dynamic pose")
            if "trample" in text_lower:
                prompt_parts.append("massive, crushing")
            if "deathtouch" in text_lower:
                prompt_parts.append("venomous, deadly")

        # Add style
        prompt_parts.append(style.value)

        # Add quality modifiers
        prompt_parts.append("masterpiece, best quality, highly detailed")

        return ", ".join(prompt_parts)

    def _add_card_frame(self, image: Image.Image, card: Card) -> Image.Image:
        """Add a basic card frame with name and stats.

        Args:
            image: The generated artwork
            card: The card data

        Returns:
            Image with card frame added
        """
        # For now, just return the image as-is
        # TODO: Implement actual card frame overlay
        return image

    def _save_image(self, image: Image.Image, card: Card) -> Path:
        """Save the generated image to disk.

        Args:
            image: The image to save
            card: The card data (for filename)

        Returns:
            Path to the saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(
            c if c.isalnum() or c in (" ", "-", "_") else "_" for c in card.name
        )
        filename = f"{safe_name}_{timestamp}.png"
        filepath = self.output_dir / filename

        image.save(filepath, "PNG", optimize=True)

        # Also save metadata
        metadata = {
            "card_name": card.name,
            "card_type": card.card_type.value,
            "timestamp": timestamp,
            "model": self.model_config.value,
        }

        metadata_path = filepath.with_suffix(".json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        return filepath

    def generate_batch(
        self,
        cards: list[Card],
        style: Optional[ArtStyle] = None,
        config: Optional[GenerationConfig] = None,
    ) -> list[Path]:
        """Generate images for multiple cards.

        Args:
            cards: List of cards to generate art for
            style: Art style to use for all cards (defaults to OIL_PAINTING)
            config: Generation configuration

        Returns:
            List of paths to generated images
        """
        if style is None:
            style = ArtStyle.OIL_PAINTING
        if config is None:
            config = GenerationConfig()

        if not self.pipeline:
            self.load_model()

        paths = []
        total = len(cards)

        for i, card in enumerate(cards, 1):
            logger.info(f"Generating {i}/{total}: {card.name}")
            try:
                path = self.generate_card_art(card, style, config)
                paths.append(path)
            except Exception as e:
                logger.error(f"Failed to generate {card.name}: {e}")
                continue

        return paths

    def clear_memory(self) -> None:
        """Clear GPU/CPU memory cache."""
        if self.device == "cuda" and torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
            logger.info("GPU memory cleared")
        elif self.device == "mps":
            # MPS doesn't have explicit cache clearing yet
            pass

    def unload_model(self) -> None:
        """Unload model from memory."""
        if self.pipeline:
            del self.pipeline
            self.pipeline = None
            self.clear_memory()
            logger.info("Model unloaded")

    def __del__(self):
        """Cleanup on deletion."""
        self.unload_model()
