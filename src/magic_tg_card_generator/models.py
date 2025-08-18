"""Data models for Magic: The Gathering cards."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, validator


class CardType(str, Enum):
    """Enumeration of Magic card types."""

    CREATURE = "Creature"
    INSTANT = "Instant"
    SORCERY = "Sorcery"
    ENCHANTMENT = "Enchantment"
    ARTIFACT = "Artifact"
    PLANESWALKER = "Planeswalker"
    LAND = "Land"


class Color(str, Enum):
    """Enumeration of Magic colors."""

    WHITE = "White"
    BLUE = "Blue"
    BLACK = "Black"
    RED = "Red"
    GREEN = "Green"
    COLORLESS = "Colorless"
    MULTICOLOR = "Multicolor"


class Card(BaseModel):
    """Model representing a Magic: The Gathering card."""

    name: str = Field(..., min_length=1, max_length=100)
    card_type: CardType
    mana_cost: str = Field(..., pattern=r"^[0-9WUBRGXC]*$")
    color: Color
    power: Optional[int] = Field(None, ge=0, le=99)
    toughness: Optional[int] = Field(None, ge=0, le=99)
    text: Optional[str] = Field(None, max_length=500)
    flavor_text: Optional[str] = Field(None, max_length=300)
    rarity: str = Field(default="Common", pattern=r"^(Common|Uncommon|Rare|Mythic)$")

    @validator("power", "toughness")
    def validate_creature_stats(cls, v: Optional[int], values: dict) -> Optional[int]:
        """Validate that power/toughness are only set for creatures."""
        if v is not None and values.get("card_type") != CardType.CREATURE:
            raise ValueError("Power and toughness can only be set for creatures")
        return v

    class Config:
        """Pydantic model configuration."""

        json_encoders = {
            CardType: lambda v: v.value,
            Color: lambda v: v.value,
        }
