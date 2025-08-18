# Image Generation Configurations

This directory contains configuration files for the AI image generation component.

## Available Configurations

### config.json
- **Purpose**: Default balanced settings for general use
- **Model**: SDXL_LOCAL
- **Quality**: Medium-High (25 steps, 1152x896)
- **Speed**: Moderate
- **Use Case**: Standard card art generation

### fast_preview.json
- **Purpose**: Quick preview generation
- **Model**: SD_1_5 (smaller, faster)
- **Quality**: Lower (15 steps, 512x512)
- **Speed**: Fast
- **Use Case**: Testing prompts, quick iterations

### high_quality.json
- **Purpose**: Maximum quality output
- **Model**: SDXL_BASE
- **Quality**: Highest (50 steps, 1024x1024, PNG format)
- **Speed**: Slow
- **Use Case**: Final card art, print quality

## Usage Examples

```bash
# Use default configuration
python generate_image.py --interactive

# Use fast preview for testing
python generate_image.py --config configs/image_generation/fast_preview.json --prompt "Quick test dragon"

# Use high quality for final art
python generate_image.py --config configs/image_generation/high_quality.json --prompt "Epic legendary dragon"

# Interactive mode with custom config
python generate_image.py --config configs/image_generation/high_quality.json --interactive
```

## Configuration Structure

Each configuration file contains:

- **image_generation**: Model and device settings
- **generation_params**: Steps, guidance scale, dimensions
- **output_settings**: Output directory, format, metadata
- **default_prompts**: Negative prompts and style suffixes
- **art_styles**: Pre-defined artistic styles

## Creating Custom Configurations

1. Copy an existing configuration:
```bash
cp config.json my_custom_config.json
```

2. Modify parameters as needed:
- Increase `steps` for better quality (slower)
- Adjust `width` and `height` for different aspect ratios
- Change `guidance_scale` to control prompt adherence (7-12 typical)
- Modify `negative_prompt` to avoid specific issues

3. Use your custom config:
```bash
python generate_image.py --config configs/image_generation/my_custom_config.json
```
