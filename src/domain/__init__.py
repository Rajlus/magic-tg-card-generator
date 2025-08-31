"""Domain layer for Magic: The Gathering card generator.

This package contains the core domain models and business logic,
free from dependencies on UI or external systems.
"""

from .models.mtg_card import MTGCard
from .enums.rarity import Rarity

__all__ = ["MTGCard", "Rarity"]