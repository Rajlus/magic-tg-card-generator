#!/usr/bin/env python3
"""Hybrid image generation - choose between local or API."""

import argparse
import logging
from pathlib import Path

from dotenv import load_dotenv

from magic_tg_card_generator.api_generator import HybridGenerator

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Generate images locally or via API")

    # Mode selection
    parser.add_argument(
        "--mode",
        choices=["local", "api"],
        default="api",
        help="Generation mode: local or api (default: api)",
    )

    # Model selection
    parser.add_argument(
        "--model",
        default=None,
        help="Model to use (api: flux-schnell, flux-dev, sdxl, sdxl-lightning; local: SDXL_LOCAL, etc.)",
    )

    # Generation parameters
    parser.add_argument(
        "--prompt", required=True, help="Text prompt for image generation"
    )

    parser.add_argument("--name", help="Output filename (without extension)")

    parser.add_argument(
        "--width", type=int, default=1024, help="Image width (default: 1024)"
    )

    parser.add_argument(
        "--height", type=int, default=1024, help="Image height (default: 1024)"
    )

    parser.add_argument("--steps", type=int, help="Number of inference steps")

    parser.add_argument("--guidance", type=float, help="Guidance scale")

    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/images"),
        help="Output directory",
    )

    args = parser.parse_args()

    # Set default models based on mode
    if args.model is None:
        args.model = "flux-schnell" if args.mode == "api" else "SDXL_LOCAL"

    # Create generator
    print(f"\n🎨 Image Generation ({args.mode.upper()} mode)")
    print(f"Model: {args.model}")
    print(f"Prompt: {args.prompt[:100]}...")

    try:
        generator = HybridGenerator(
            use_api=(args.mode == "api"),
            api_model=args.model if args.mode == "api" else None,
            local_model=args.model if args.mode == "local" else None,
            output_dir=args.output_dir,
        )

        # Prepare generation parameters
        gen_params = {
            "width": args.width,
            "height": args.height,
            "output_name": args.name,
        }

        if args.steps:
            gen_params["num_inference_steps"] = args.steps
        if args.guidance is not None:
            gen_params["guidance_scale"] = args.guidance
        if args.seed:
            gen_params["seed"] = args.seed

        # Generate image
        print("\n⏳ Generating image...")
        output_path = generator.generate(args.prompt, **gen_params)

        print(f"\n✅ Success! Image saved to: {output_path}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
