#!/usr/bin/env python3
"""Standalone script to generate images with Magic card generator."""

import argparse
import logging
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt

from magic_tg_card_generator.image_generator import (
    ImageGenerator,
)
from magic_tg_card_generator.models import Card, CardType, Color

console = Console()


def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def main():
    """Main function for image generation."""
    parser = argparse.ArgumentParser(description="Generate Magic card artwork")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/image_generation/config.yml"),
        help="Path to configuration file",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        help="Custom prompt for image generation (optional)",
    )
    parser.add_argument(
        "--style",
        type=str,
        help="Art style from config (e.g., fantasy_realism, digital_art, comic_book, watercolor, dark_fantasy)",
    )
    parser.add_argument(
        "--list-styles",
        action="store_true",
        help="List available art styles from config and exit",
    )
    parser.add_argument(
        "--name",
        type=str,
        default="Custom Card",
        help="Card name",
    )
    parser.add_argument(
        "--type",
        type=str,
        choices=[t.value for t in CardType],
        default="Creature",
        help="Card type",
    )
    parser.add_argument(
        "--color",
        type=str,
        choices=[c.value for c in Color],
        default="Red",
        help="Card color",
    )
    parser.add_argument(
        "--power",
        type=int,
        help="Creature power",
    )
    parser.add_argument(
        "--toughness",
        type=int,
        help="Creature toughness",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive mode - prompt for image description",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    # Handle --list-styles
    if args.list_styles:
        import json

        import yaml

        config_path = args.config
        if config_path.exists():
            with open(config_path) as f:
                if config_path.suffix in [".yml", ".yaml"]:
                    config = yaml.safe_load(f)
                else:
                    config = json.load(f)

            console.print(f"\n[blue]Available art styles in {config_path}:[/blue]")
            if "art_styles" in config:
                for style_name, style_desc in config["art_styles"].items():
                    console.print(
                        f"  [green]{style_name:20}[/green] - {style_desc[:60]}..."
                    )
            else:
                console.print("[yellow]No art styles defined in config[/yellow]")
        else:
            console.print(f"[red]Config file not found: {config_path}[/red]")
        return 0

    # Create card
    card_type = CardType(args.type)

    # Set default power/toughness for creatures if not provided
    if card_type == CardType.CREATURE:
        power = args.power if args.power is not None else 3
        toughness = args.toughness if args.toughness is not None else 3
    else:
        power = None
        toughness = None

    card = Card(
        name=args.name,
        card_type=card_type,
        mana_cost="3",
        color=Color(args.color),
        power=power,
        toughness=toughness,
    )

    # Initialize image generator with config
    console.print(f"[blue]Loading configuration from {args.config}...[/blue]")
    generator = ImageGenerator(config_file=args.config)

    # Get prompt
    custom_prompt = args.prompt
    if args.interactive and not custom_prompt:
        console.print("\n[yellow]Interactive Mode[/yellow]")
        custom_prompt = Prompt.ask(
            "[green]Was für ein Bild soll generiert werden?[/green]",
            default=None,
        )

    # Apply art style from config if specified
    if args.style and custom_prompt:
        # Load art styles from config
        if (
            "art_styles" in generator.config
            and args.style in generator.config["art_styles"]
        ):
            style_suffix = generator.config["art_styles"][args.style]
            custom_prompt = f"{custom_prompt}, {style_suffix}"
            console.print(f"[dim]Applying art style: {args.style}[/dim]")
        else:
            available_styles = list(generator.config.get("art_styles", {}).keys())
            console.print(
                f"[yellow]Warning: Style '{args.style}' not found in config[/yellow]"
            )
            if available_styles:
                console.print(
                    f"[dim]Available styles: {', '.join(available_styles)}[/dim]"
                )

    # Generate image
    console.print(f"\n[blue]Generating image for {card.name}...[/blue]")

    try:
        if custom_prompt:
            console.print(f"[dim]Using custom prompt: {custom_prompt[:100]}...[/dim]")
        else:
            console.print(
                "[dim]Using auto-generated prompt based on card attributes[/dim]"
            )

        image_path = generator.generate_card_art(
            card=card,
            custom_prompt=custom_prompt,
        )

        console.print(f"[green]✓[/green] Image saved to: {image_path}")

        # Show metadata
        metadata_path = image_path.with_suffix(".json")
        if metadata_path.exists():
            console.print(f"[green]✓[/green] Metadata saved to: {metadata_path}")

    except Exception as e:
        console.print(f"[red]✗ Error generating image: {e}[/red]")
        return 1
    finally:
        # Clean up
        if generator.pipeline:
            generator.unload_model()
            console.print("[dim]Model unloaded[/dim]")

    return 0


if __name__ == "__main__":
    exit(main())
