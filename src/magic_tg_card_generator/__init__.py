"""Magic: The Gathering Card Generator Package."""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "you@example.com"

from magic_tg_card_generator.core import CardGenerator
from magic_tg_card_generator.models import Card, CardType, Color

__all__ = ["CardGenerator", "Card", "CardType", "Color"]
