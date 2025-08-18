# Configuration Files

This directory contains configuration files for different components of the Magic TG Card Generator.

## Structure

```
configs/
├── README.md                    # This file
├── image_generation/           # Image generation configurations
│   └── default_image.json     # Default settings for image generation
├── game_rules/                 # (Future) Game rules and card mechanics
├── database/                   # (Future) Database configurations
└── api/                        # (Future) API settings
```

## Image Generation Configs

The `image_generation/` subdirectory contains configurations for the AI image generation:

- `default_image.json` - Default configuration with:
  - Model settings (SDXL, device, memory options)
  - Generation parameters (steps, guidance scale, dimensions)
  - Output settings (format, directory, metadata)
  - Default prompts and negative prompts
  - Art style definitions

## Usage

```bash
# Use default image config
python generate_image.py

# Use custom config
python generate_image.py --config configs/image_generation/my_custom_config.json
```

## Creating Custom Configs

You can create custom configurations by copying `default_image.json` and modifying the parameters:

```bash
cp configs/image_generation/default_image.json configs/image_generation/high_quality.json
# Then edit high_quality.json with your preferred settings
```