#!/usr/bin/env python3
"""Unified image generation script - supports both local and API generation."""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class UnifiedImageGenerator:
    """Unified image generator supporting both local and API modes."""

    def __init__(self, config_path: str = "configs/image_generation/config.yml"):
        """Initialize generator with configuration."""
        self.config = self._load_config(config_path)
        self.mode = None
        self.generator = None

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        config_file = Path(config_path)
        if not config_file.exists():
            logger.warning(f"Config file {config_path} not found, using defaults")
            return self._get_default_config()

        with open(config_file) as f:
            return yaml.safe_load(f)

    def _get_default_config(self) -> dict:
        """Get default configuration if config file not found."""
        return {
            "image_generation": {
                "default_mode": "api",
                "local": {
                    "model": "SDXL_LOCAL",
                    "model_path": "models/stable-diffusion-xl-base-1.0",
                },
                "api": {"default_model": "flux-schnell"},
            },
            "generation_params": {
                "steps": 30,
                "guidance_scale": 7.5,
                "width": 1024,
                "height": 1024,
            },
            "output_settings": {
                "output_dir": "output/images",
                "save_metadata": True,
                "image_format": "png",
            },
        }

    def setup_generator(self, mode: str, model: Optional[str] = None):
        """Setup the generator based on mode (local or api)."""
        self.mode = mode

        if mode == "api":
            self._setup_api_generator(model)
        else:
            self._setup_local_generator(model)

    def _setup_api_generator(self, model: Optional[str] = None):
        """Setup API-based generator."""
        try:
            from io import BytesIO

            import replicate
            import requests
            from PIL import Image

            # Check for API token
            api_token = os.getenv("REPLICATE_API_TOKEN")
            if not api_token:
                raise ValueError("REPLICATE_API_TOKEN environment variable not set")

            self.api_model = (
                model or self.config["image_generation"]["api"]["default_model"]
            )

            # Model mappings for Replicate
            self.api_models = {
                "flux-schnell": "black-forest-labs/flux-schnell",
                "flux-dev": "black-forest-labs/flux-dev",
                "flux-pro": "black-forest-labs/flux-pro",
                "sdxl": "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
                "sdxl-lightning": "bytedance/sdxl-lightning-4step:727e49a643e999d602a896c774a0658ffefea21465756a6ce24b7ea4165eba6a",
            }

            logger.info(f"API mode initialized with model: {self.api_model}")

        except ImportError as e:
            logger.error(f"Failed to import required API modules: {e}")
            logger.error("Please install: pip install replicate pillow requests")
            sys.exit(1)

    def _setup_local_generator(self, model: Optional[str] = None):
        """Setup local generation using diffusers."""
        try:
            # Add src to path for imports
            sys.path.insert(0, str(Path(__file__).parent / "src"))

            from magic_tg_card_generator.image_generator import (
                ImageGenerator,
                ModelConfig,
            )

            model_name = model or self.config["image_generation"]["local"]["model"]

            # Use existing ImageGenerator infrastructure
            self.generator = ImageGenerator(
                model=ModelConfig[model_name]
                if isinstance(model_name, str)
                else model_name,
                output_dir=Path(self.config["output_settings"]["output_dir"]),
            )
            self.generator.load_model()

            logger.info(f"Local mode initialized with model: {model_name}")

        except ImportError as e:
            logger.error(f"Failed to import local generation modules: {e}")
            logger.error("Please ensure the project is properly installed")
            sys.exit(1)

    def generate(
        self,
        prompt: str,
        style: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        steps: Optional[int] = None,
        guidance: Optional[float] = None,
        seed: Optional[int] = None,
        output_name: Optional[str] = None,
        negative_prompt: Optional[str] = None,
    ) -> Path:
        """Generate an image with the configured generator."""

        # Apply art style if specified
        if style and style in self.config.get("art_styles", {}):
            style_suffix = self.config["art_styles"][style]
            prompt = f"{prompt}, {style_suffix}"
            logger.info(f"Applied art style: {style}")

        # Add default style suffix if configured
        if (
            "default_prompts" in self.config
            and "style_suffix" in self.config["default_prompts"]
        ):
            prompt = f"{prompt}, {self.config['default_prompts']['style_suffix']}"

        # Get default parameters
        gen_params = self.config.get("generation_params", {})
        width = width or gen_params.get("width", 1024)
        height = height or gen_params.get("height", 1024)
        steps = steps or gen_params.get("steps", 30)
        guidance = guidance or gen_params.get("guidance_scale", 7.5)

        logger.debug(
            f"Using dimensions: {width}x{height} (from config: {gen_params.get('width')}x{gen_params.get('height')})"
        )

        # Get negative prompt
        if negative_prompt is None and "default_prompts" in self.config:
            negative_prompt = self.config["default_prompts"].get("negative_prompt")

        # Output settings
        output_dir = Path(self.config["output_settings"]["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        if self.mode == "api":
            return self._generate_api(
                prompt,
                width,
                height,
                steps,
                guidance,
                seed,
                output_name,
                output_dir,
                gen_params,
            )
        else:
            return self._generate_local(
                prompt,
                width,
                height,
                steps,
                guidance,
                seed,
                output_name,
                negative_prompt,
            )

    def _generate_api(
        self,
        prompt: str,
        width: int,
        height: int,
        steps: int,
        guidance: float,
        seed: Optional[int],
        output_name: Optional[str],
        output_dir: Path,
        gen_params: Optional[dict] = None,
    ) -> Path:
        """Generate image using API."""
        from io import BytesIO

        import replicate
        import requests
        from PIL import Image

        # Build input parameters
        input_params = {
            "prompt": prompt,
        }

        # Flux models use aspect_ratio instead of width/height
        if "flux" in self.api_model.lower():
            # Check if aspect_ratio is defined in config or calculate from dimensions
            config_aspect = gen_params.get("aspect_ratio") if gen_params else None
            valid_aspects = [
                "1:1",
                "16:9",
                "21:9",
                "3:2",
                "2:3",
                "4:5",
                "5:4",
                "3:4",
                "4:3",
                "9:16",
                "9:21",
            ]

            if config_aspect and config_aspect in valid_aspects:
                # Use aspect ratio from config
                input_params["aspect_ratio"] = config_aspect
                logger.debug(f"Using aspect ratio from config: {config_aspect}")
            else:
                # Calculate from width/height
                aspect_ratios = {
                    (1024, 1024): "1:1",
                    (1152, 896): "4:3",  # Close to 9:7, use 4:3
                    (896, 1152): "3:4",  # Close to 7:9, use 3:4
                    (1024, 768): "4:3",
                    (768, 1024): "3:4",
                    (1344, 768): "16:9",
                    (768, 1344): "9:16",
                    (1536, 1024): "3:2",
                    (1024, 1536): "2:3",
                }
                ratio = aspect_ratios.get((width, height))

                if ratio and ratio in valid_aspects:
                    input_params["aspect_ratio"] = ratio
                else:
                    # Find closest valid aspect ratio
                    if width > height:
                        input_params["aspect_ratio"] = "4:3"  # Landscape
                    elif height > width:
                        input_params["aspect_ratio"] = "3:4"  # Portrait
                    else:
                        input_params["aspect_ratio"] = "1:1"  # Square
                    logger.info(
                        f"Auto-detected aspect ratio {input_params['aspect_ratio']} for {width}x{height}"
                    )
        else:
            # Other models use width/height
            input_params["width"] = width
            input_params["height"] = height

        if seed is not None:
            input_params["seed"] = seed

        # Model-specific parameters
        model_key = self.api_model
        if model_key in self.config.get("model_configs", {}):
            model_config = self.config["model_configs"][model_key]
            steps = model_config.get("steps", steps)
            guidance = model_config.get("guidance_scale", guidance)

        # Apply model-specific defaults
        if "flux-schnell" in self.api_model:
            input_params["num_inference_steps"] = 4
        elif "flux-dev" in self.api_model or "flux-pro" in self.api_model:
            input_params["num_inference_steps"] = steps
            input_params["guidance_scale"] = guidance
        elif "sdxl-lightning" in self.api_model:
            input_params["num_inference_steps"] = 4
            input_params["guidance_scale"] = 0
        else:
            input_params["num_inference_steps"] = steps
            input_params["guidance_scale"] = guidance

        logger.info(f"Generating via API with {self.api_model}...")
        logger.debug(f"API input parameters: {input_params}")
        start_time = time.time()

        # Run the model
        model_id = self.api_models.get(self.api_model, self.api_model)
        output = replicate.run(model_id, input=input_params)

        # Get image URL
        if isinstance(output, list):
            image_url = output[0]
        else:
            image_url = output

        elapsed = time.time() - start_time
        logger.info(f"Generated in {elapsed:.1f}s")

        # Download and save image
        response = requests.get(image_url)
        response.raise_for_status()

        image = Image.open(BytesIO(response.content))

        # Generate filename
        if output_name:
            filename = f"{output_name}.{self.config['output_settings']['image_format']}"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"generated_{timestamp}.{self.config['output_settings']['image_format']}"

        output_path = output_dir / filename
        image.save(output_path)

        # Save metadata if configured
        if self.config["output_settings"].get("save_metadata", True):
            metadata = {
                "prompt": prompt,
                "model": self.api_model,
                "width": width,
                "height": height,
                "steps": input_params.get("num_inference_steps"),
                "guidance_scale": input_params.get("guidance_scale"),
                "seed": seed,
                "timestamp": datetime.now().isoformat(),
                "mode": "api",
            }
            metadata_path = output_path.with_suffix(".json")
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

        logger.info(f"Image saved to: {output_path}")
        return output_path

    def _generate_local(
        self,
        prompt: str,
        width: int,
        height: int,
        steps: int,
        guidance: float,
        seed: Optional[int],
        output_name: Optional[str],
        negative_prompt: Optional[str],
    ) -> Path:
        """Generate image using local model."""
        from magic_tg_card_generator.image_generator import GenerationConfig
        from magic_tg_card_generator.models import Card, CardType, Color

        # Create generation config
        config = GenerationConfig(
            num_inference_steps=steps,
            guidance_scale=guidance,
            width=width,
            height=height,
            seed=seed,
            negative_prompt=negative_prompt,
        )

        # Create a dummy card for the existing infrastructure
        card = Card(
            name=output_name or "Generated",
            card_type=CardType.CREATURE,
            color=Color.COLORLESS,
            mana_cost="0",
            text="",
        )

        logger.info(f"Generating locally with prompt: {prompt[:100]}...")

        # Generate image
        output_path = self.generator.generate_card_art(
            card=card, config=config, custom_prompt=prompt
        )

        # Save metadata if configured
        if self.config["output_settings"].get("save_metadata", True):
            metadata = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "model": self.config["image_generation"]["local"]["model"],
                "width": width,
                "height": height,
                "steps": steps,
                "guidance_scale": guidance,
                "seed": seed,
                "timestamp": datetime.now().isoformat(),
                "mode": "local",
            }
            metadata_path = output_path.with_suffix(".json")
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

        logger.info(f"Image saved to: {output_path}")
        return output_path

    def list_styles(self) -> dict[str, str]:
        """List available art styles."""
        return self.config.get("art_styles", {})

    def cleanup(self):
        """Clean up resources."""
        if self.mode == "local" and self.generator:
            self.generator.unload_model()
            logger.info("Local model unloaded")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Generate images using local models or API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate with default settings
  python generate_unified.py --prompt "a majestic dragon"

  # Use API mode with specific model
  python generate_unified.py --mode api --model flux-schnell --prompt "fantasy warrior"

  # Use local mode with art style
  python generate_unified.py --mode local --prompt "wizard casting spell" --style dark_fantasy

  # List available art styles
  python generate_unified.py --list-styles
        """,
    )

    # Mode selection
    parser.add_argument(
        "--mode",
        choices=["local", "api"],
        help="Generation mode: local or api (default from config.yml)",
    )

    # Model selection
    parser.add_argument(
        "--model",
        help="Model to use (api: flux-schnell, flux-dev, sdxl, etc.; local: SDXL_LOCAL, etc.)",
    )

    # Prompt and style
    parser.add_argument("--prompt", help="Text prompt for image generation")

    parser.add_argument(
        "--style",
        help="Art style from config.yml (e.g., fantasy_realism, digital_art, cyberpunk, etc.)",
    )

    # Generation parameters
    parser.add_argument("--name", help="Output filename (without extension)")

    parser.add_argument(
        "--width", type=int, help="Image width (default from config.yml)"
    )

    parser.add_argument(
        "--height", type=int, help="Image height (default from config.yml)"
    )

    parser.add_argument("--steps", type=int, help="Number of inference steps")

    parser.add_argument("--guidance", type=float, help="Guidance scale")

    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")

    parser.add_argument(
        "--negative-prompt", help="Negative prompt for local generation"
    )

    # Other options
    parser.add_argument(
        "--config",
        default="configs/image_generation/config.yml",
        help="Path to configuration file (default: configs/image_generation/config.yml)",
    )

    parser.add_argument(
        "--list-styles", action="store_true", help="List available art styles and exit"
    )

    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive mode - prompt for inputs",
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize generator
    generator = UnifiedImageGenerator(config_path=args.config)

    # Handle --list-styles
    if args.list_styles:
        print("\n🎨 Available Art Styles:")
        print("-" * 50)
        styles = generator.list_styles()
        for style_name, style_desc in styles.items():
            # Truncate long descriptions
            desc = style_desc[:70] + "..." if len(style_desc) > 70 else style_desc
            print(f"  {style_name:20} - {desc}")
        print("\nUse --style <name> to apply a style to your prompt")
        return 0

    # Interactive mode
    if args.interactive:
        print("\n🎮 Interactive Mode")
        print("-" * 50)

        if not args.prompt:
            args.prompt = input("Enter your image prompt: ").strip()
            if not args.prompt:
                print("❌ Prompt is required")
                return 1

        if not args.mode:
            mode_choice = input("Select mode [1=local, 2=api] (default=1): ").strip()
            args.mode = "api" if mode_choice == "2" else "local"

        if not args.style:
            print("\nAvailable styles: " + ", ".join(generator.list_styles().keys()))
            style = input("Enter style name (or press Enter to skip): ").strip()
            if style and style in generator.list_styles():
                args.style = style

    # Validate prompt
    if not args.prompt:
        print("❌ Error: --prompt is required")
        print("Use --help for usage information")
        return 1

    # Get mode from config if not specified
    if not args.mode:
        args.mode = generator.config["image_generation"]["default_mode"]

    # Setup generator
    print(f"\n🚀 Initializing {args.mode.upper()} mode...")
    try:
        generator.setup_generator(args.mode, args.model)
    except Exception as e:
        print(f"❌ Failed to initialize generator: {e}")
        return 1

    # Generate image
    print("🎨 Generating image...")
    if args.style:
        print(f"   Style: {args.style}")
    print(f"   Prompt: {args.prompt[:80]}...")

    try:
        output_path = generator.generate(
            prompt=args.prompt,
            style=args.style,
            width=args.width,
            height=args.height,
            steps=args.steps,
            guidance=args.guidance,
            seed=args.seed,
            output_name=args.name,
            negative_prompt=args.negative_prompt,
        )

        print(f"\n✅ Success! Image saved to: {output_path}")

        # Check for metadata
        metadata_path = output_path.with_suffix(".json")
        if metadata_path.exists():
            print(f"📄 Metadata saved to: {metadata_path}")

    except Exception as e:
        print(f"\n❌ Generation failed: {e}")
        import traceback

        if args.verbose:
            traceback.print_exc()
        return 1

    finally:
        # Cleanup
        generator.cleanup()

    return 0


if __name__ == "__main__":
    exit(main())
