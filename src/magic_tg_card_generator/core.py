"""Core functionality for the Magic: The Gathering Card Generator."""

import json
import logging
import random
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

        # Use to_dict method which properly serializes datetime
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(card.to_dict(), f, indent=2, ensure_ascii=False)

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

        return Card.from_dict(data)

    def generate_batch(self, count: int) -> list[Card]:
        """Generate multiple random cards.

        Args:
            count: Number of cards to generate

        Returns:
            List of generated cards
        """
        cards = []
        for _ in range(count):
            card = self.generate_random()
            cards.append(card)
        return cards

    def generate_random(self) -> Card:
        """Generate a random card.

        Returns:
            A randomly generated Card instance
        """
        # Random card names
        names = [
            "Lightning Bolt",
            "Dark Ritual",
            "Giant Growth",
            "Counterspell",
            "Doom Blade",
            "Swords to Plowshares",
            "Path to Exile",
            "Thoughtseize",
            "Brainstorm",
            "Force of Will",
            "Ancestral Recall",
            "Time Walk",
            "Black Lotus",
            "Mox Pearl",
            "Serra Angel",
            "Shivan Dragon",
        ]

        # Random card type
        card_type = random.choice(list(CardType))

        # Random color
        color = random.choice(list(Color))

        # Random mana cost
        mana_costs = [
            "1",
            "2",
            "3",
            "1R",
            "1U",
            "1B",
            "1W",
            "1G",
            "2R",
            "UU",
            "BB",
            "3RR",
            "2WW",
        ]
        mana_cost = random.choice(mana_costs)

        # Power and toughness for creatures
        power = None
        toughness = None
        if card_type == CardType.CREATURE:
            power = random.randint(1, 8)
            toughness = random.randint(1, 8)

        # Random text
        texts = [
            "Flying",
            "First strike",
            "Trample",
            "Haste",
            "Vigilance",
            "Draw a card",
            "Deal 3 damage to any target",
            "Destroy target creature",
            "Counter target spell",
            "Target creature gets +3/+3 until end of turn",
        ]
        text = random.choice(texts) if random.random() > 0.3 else None

        return self.generate_card(
            name=random.choice(names),
            card_type=card_type,
            mana_cost=mana_cost,
            color=color,
            power=power,
            toughness=toughness,
            text=text,
            save=False,
        )

    def export_card(self, card: Card, format: str = "json") -> Path:
        """Export a card to a specific format.

        Args:
            card: The card to export
            format: The export format (json or text)

        Returns:
            Path to the exported file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(
            c if c.isalnum() or c in (" ", "-", "_") else "_" for c in card.name
        )

        if format == "json":
            filename = f"{safe_name}_{timestamp}.json"
            filepath = self.output_dir / filename
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(card.to_dict(), f, indent=2, ensure_ascii=False)
        elif format == "text":
            filename = f"{safe_name}_{timestamp}.txt"
            filepath = self.output_dir / filename
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"{card.name}\n")
                f.write(f"{card.mana_cost}\n")
                f.write(f"{card.card_type.value}\n")
                if card.power is not None and card.toughness is not None:
                    f.write(f"{card.power}/{card.toughness}\n")
                if card.text:
                    f.write(f"\n{card.text}\n")
        else:
            raise ValueError(f"Unsupported format: {format}")

        logger.info(f"Card exported to: {filepath}")
        return filepath
