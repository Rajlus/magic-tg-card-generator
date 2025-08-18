#!/usr/bin/env python3
"""Simple image generation using configuration from JSON file."""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import torch
from diffusers import StableDiffusionXLPipeline


def load_config(config_path: str) -> dict:
    """Load configuration from JSON file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path) as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="Generate dragon images with SDXL")
    parser.add_argument(
        "--config", type=str, required=True, help="Path to JSON configuration file"
    )

    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    print("🐉 Dragon Image Generator")
    print("=" * 50)
    print(f"📝 Prompt: {config['prompt'][:60]}...")
    print(f"⚙️  Steps: {config['steps']}")
    print(f"📐 Size: {config['width']}x{config['height']}")
    print(f"📦 Batch: {config.get('batch_size', 1)}")
    print("=" * 50)

    # Load SDXL model
    print("\n⏳ Loading SDXL model...")
    start = time.time()

    model_path = "models/sd_xl_base_1.0.safetensors"
    device = "mps" if torch.backends.mps.is_available() else "cpu"

    pipeline = StableDiffusionXLPipeline.from_single_file(
        model_path,
        torch_dtype=torch.float32,  # float32 for MPS
        use_safetensors=True,
    )
    pipeline = pipeline.to(device)

    # Enable optimizations
    if hasattr(pipeline, "enable_attention_slicing"):
        pipeline.enable_attention_slicing()

    print(f"✅ Model loaded in {time.time() - start:.1f}s")

    # Create output directory
    output_dir = Path(config.get("output_dir", "output/images"))
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate images
    batch_size = config.get("batch_size", 1)

    for i in range(batch_size):
        print(f"\n[{i+1}/{batch_size}] Generating...")
        start = time.time()

        # Setup generator for seed
        generator = None
        if config.get("seed"):
            # Use same seed for all images if you want identical results
            # Or add + i to get variations with predictable seeds
            generator = torch.Generator(device=device).manual_seed(config["seed"])

        # Generate
        with torch.no_grad():
            result = pipeline(
                prompt=config["prompt"],
                negative_prompt=config.get("negative_prompt", ""),
                num_inference_steps=config["steps"],
                guidance_scale=config.get("guidance_scale", 7.5),
                height=config["height"],
                width=config["width"],
                generator=generator,
            )

        # Save image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"dragon_{timestamp}_{i}.png"
        filepath = output_dir / filename

        result.images[0].save(filepath)
        print(f"   ✅ Saved to: {filepath}")
        print(f"   ⏱️  Time: {time.time() - start:.1f}s")

    print("\n" + "=" * 50)
    print("✨ Generation complete!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  Cancelled")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
