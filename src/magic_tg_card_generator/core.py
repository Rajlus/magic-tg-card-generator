"""Core functionality for the Magic: The Gathering Card Generator."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from magic_tg_card_generator.models import Card, CardType, Color

logger = logging.getLogger(__name__)


class CardGenerator:
    """Main class for generating Magic: The Gathering cards."""

    def __init__(self, output_dir: Optional[Path] = None) -> None:
        """Initialize the card generator.

        Args:
            output_dir: Directory to save generated cards (default: ./output/cards)
        """
        logger.info("Initializing CardGenerator")
        self.output_dir = output_dir or Path("output/cards")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_card(
        self,
        name: str,
        card_type: CardType,
        mana_cost: str,
        color: Optional[Color] = None,
        power: Optional[int] = None,
        toughness: Optional[int] = None,
        text: Optional[str] = None,
        save: bool = True,
    ) -> Card:
        """Generate a new Magic card.

        Args:
            name: The name of the card
            card_type: The type of the card
            mana_cost: The mana cost string (e.g., "2RR")
            color: The color(s) of the card
            power: Power value for creatures
            toughness: Toughness value for creatures
            text: The card's rules text
            save: Whether to save the card to a file

        Returns:
            A new Card instance
        """
        card = Card(
            name=name,
            card_type=card_type,
            mana_cost=mana_cost,
            color=color or Color.COLORLESS,
            power=power,
            toughness=toughness,
            text=text,
        )
        logger.info(f"Generated card: {card.name}")

        if save:
            self.save_card(card)

        return card

    def save_card(self, card: Card) -> Path:
        """Save a card to a JSON file.

        Args:
            card: The card to save

        Returns:
            Path to the saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(
            c if c.isalnum() or c in (" ", "-", "_") else "_" for c in card.name
        )
        filename = f"{safe_name}_{timestamp}.json"
        filepath = self.output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(card.model_dump(), f, indent=2, ensure_ascii=False)

        logger.info(f"Card saved to: {filepath}")
        return filepath

    def load_card(self, filepath: Path) -> Card:
        """Load a card from a JSON file.

        Args:
            filepath: Path to the card file

        Returns:
            The loaded Card instance
        """
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        return Card(**data)
