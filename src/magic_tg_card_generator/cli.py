"""Command-line interface for the Magic: The Gathering Card Generator."""

import argparse
import logging
import sys
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler

from magic_tg_card_generator import __version__
from magic_tg_card_generator.core import CardGenerator
from magic_tg_card_generator.models import CardType, Color

console = Console()


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)],
    )


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        description="Generate Magic: The Gathering cards",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Generate command
    generate_parser = subparsers.add_parser("generate", help="Generate a new card")
    generate_parser.add_argument("name", help="Card name")
    generate_parser.add_argument(
        "--type",
        choices=[t.value for t in CardType],
        required=True,
        help="Card type",
    )
    generate_parser.add_argument(
        "--mana-cost",
        required=True,
        help="Mana cost (e.g., 2RR)",
    )
    generate_parser.add_argument(
        "--color",
        choices=[c.value for c in Color],
        help="Card color",
    )
    generate_parser.add_argument(
        "--power",
        type=int,
        help="Power (for creatures)",
    )
    generate_parser.add_argument(
        "--toughness",
        type=int,
        help="Toughness (for creatures)",
    )
    generate_parser.add_argument(
        "--text",
        help="Card rules text",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    setup_logging(args.verbose)

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "generate":
        generator = CardGenerator()
        card = generator.generate_card(
            name=args.name,
            card_type=CardType(args.type),
            mana_cost=args.mana_cost,
            color=Color(args.color) if args.color else None,
            power=args.power,
            toughness=args.toughness,
            text=args.text,
            save=True,  # Speichert die Karte automatisch
        )
        console.print(f"[green]✓[/green] Generated card: {card.name}")
        console.print("[blue]📁 Saved to: output/cards/[/blue]")
        console.print(card.model_dump_json(indent=2))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
