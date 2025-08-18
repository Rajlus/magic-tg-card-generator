# Unified Image Generator Usage Guide

## Overview
The `generate_unified.py` script provides a single interface for generating images using either local models or API services.

## Installation

Make sure you have installed all dependencies:
```bash
poetry install
```

For API mode, set your Replicate API token:
```bash
export REPLICATE_API_TOKEN="your-token-here"
```

## Basic Usage

### Generate with default settings (local mode)
```bash
poetry run python generate_unified.py --prompt "a majestic dragon"
```

### Use API mode
```bash
poetry run python generate_unified.py --mode api --prompt "fantasy warrior"
```

### Apply an art style
```bash
poetry run python generate_unified.py --prompt "wizard casting spell" --style dark_fantasy
```

### List all available art styles
```bash
poetry run python generate_unified.py --list-styles
```

## Command Line Options

- `--mode {local,api}` - Choose generation mode (default from config.yml)
- `--model MODEL` - Specify model (e.g., flux-schnell, sdxl)
- `--prompt PROMPT` - **Required**: Text description of image to generate
- `--style STYLE` - Apply an art style from config.yml
- `--name NAME` - Output filename (without extension)
- `--width WIDTH` - Image width in pixels
- `--height HEIGHT` - Image height in pixels
- `--steps STEPS` - Number of inference steps
- `--guidance GUIDANCE` - Guidance scale value
- `--seed SEED` - Random seed for reproducibility
- `--negative-prompt PROMPT` - What to avoid in the image (local mode only)
- `--config CONFIG` - Path to config file (default: config.yml)
- `--interactive` - Interactive mode with prompts
- `--verbose` - Enable verbose logging

## Available Models

### API Models
- `flux-schnell` - Fast generation (4 steps)
- `flux-dev` - High quality development model
- `flux-pro` - Professional quality model
- `sdxl` - Stable Diffusion XL
- `sdxl-lightning` - Fast SDXL variant (4 steps)

### Local Models
- `SDXL_LOCAL` - Local Stable Diffusion XL

## Available Art Styles

The config.yml includes 26 different art styles:

### Painting Styles
- `fantasy_realism` - Oil painting, Renaissance art
- `digital_art` - Modern illustration, vibrant colors
- `comic_book` - Bold lines, dynamic composition
- `watercolor` - Soft edges, flowing colors
- `dark_fantasy` - Gothic atmosphere, dramatic shadows
- `impressionist` - Visible brushstrokes, Monet-inspired
- `abstract` - Non-representational, bold shapes
- `surrealist` - Dreamlike, Salvador Dali inspired
- `art_nouveau` - Ornamental, Alphonse Mucha inspired
- `baroque` - Dramatic lighting, Caravaggio-inspired

### Digital/Modern Styles
- `cyberpunk` - Neon lights, futuristic dystopia
- `steampunk` - Victorian era, mechanical gears
- `anime` - Japanese animation style
- `pixel_art` - 16-bit aesthetic, retro gaming
- `low_poly` - Geometric 3D, minimalist

### Photography-Inspired
- `photorealistic` - Hyperrealistic detail
- `cinematic` - Movie poster aesthetic
- `noir` - Black and white, high contrast

### Historical Periods
- `medieval` - Illuminated manuscript style
- `ukiyo_e` - Japanese woodblock prints
- `art_deco` - 1920s elegance, geometric patterns
- `pop_art` - Andy Warhol inspired

### Fantasy Specific
- `high_fantasy` - Lord of the Rings aesthetic
- `fairy_tale` - Whimsical storybook quality
- `cosmic_horror` - Lovecraftian aesthetic
- `mythological` - Classical mythology, epic heroes

## Examples

### Generate a cyberpunk scene using API
```bash
poetry run python generate_unified.py \
  --mode api \
  --model flux-schnell \
  --prompt "neon-lit street in Tokyo" \
  --style cyberpunk \
  --name tokyo_night
```

### Create a fantasy painting locally
```bash
poetry run python generate_unified.py \
  --mode local \
  --prompt "ancient wizard in tower" \
  --style fantasy_realism \
  --width 1024 \
  --height 1024 \
  --steps 50
```

### Interactive mode
```bash
poetry run python generate_unified.py --interactive
```

## Configuration

The `config.yml` file controls default settings:
- Default mode (local/api)
- Model paths and settings
- Output directory
- Default generation parameters
- Art styles definitions
- Negative prompts

## Output

Generated images are saved to `output/images/` by default with:
- The generated image file (.png or .jpg)
- A metadata JSON file with generation parameters

## Tips

1. Use `--seed` for reproducible results
2. Higher step counts generally produce better quality (but take longer)
3. Guidance scale affects how closely the image follows the prompt
4. Combine prompts with art styles for best results
5. API mode is faster but requires internet and API token
6. Local mode gives you full control but requires GPU resources
