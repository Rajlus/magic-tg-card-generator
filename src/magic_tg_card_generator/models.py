"""Data models for Magic: The Gathering cards."""

from datetime import datetime
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
    created_at: datetime = Field(default_factory=datetime.now)

    @validator("power", "toughness")
    def validate_creature_stats(cls, v: Optional[int], values: dict) -> Optional[int]:
        """Validate that power/toughness are only set for creatures."""
        if v is not None and values.get("card_type") != CardType.CREATURE:
            raise ValueError("Power and toughness can only be set for creatures")
        return v

    @validator("power", "toughness", pre=False)
    def validate_creature_requirements(
        cls, v: Optional[int], values: dict
    ) -> Optional[int]:
        """Validate that creatures have power and toughness."""
        if values.get("card_type") == CardType.CREATURE and v is None:
            raise ValueError("Creatures must have power and toughness")
        return v

    @property
    def converted_mana_cost(self) -> int:
        """Calculate the converted mana cost of the card."""
        if not self.mana_cost:
            return 0

        total = 0
        i = 0
        while i < len(self.mana_cost):
            char = self.mana_cost[i]
            if char.isdigit():
                # Handle multi-digit numbers
                num_str = char
                i += 1
                while i < len(self.mana_cost) and self.mana_cost[i].isdigit():
                    num_str += self.mana_cost[i]
                    i += 1
                total += int(num_str)
            elif char in "WUBRGC":
                total += 1
                i += 1
            elif char == "X":
                # X counts as 0 for CMC
                i += 1
            else:
                i += 1

        return total

    def to_dict(self) -> dict:
        """Convert the card to a dictionary."""
        data = self.model_dump()
        # Convert enums to strings
        data["card_type"] = self.card_type.value
        data["color"] = self.color.value
        # Convert datetime to ISO format
        data["created_at"] = self.created_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Card":
        """Create a card from a dictionary."""
        # Convert string values to enums
        if "card_type" in data and isinstance(data["card_type"], str):
            data["card_type"] = CardType(data["card_type"])
        if "color" in data and isinstance(data["color"], str):
            data["color"] = Color(data["color"])
        # Convert ISO string to datetime
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)

    def __str__(self) -> str:
        """Return a string representation of the card."""
        result = f"{self.name} - {self.mana_cost}\n"
        result += f"{self.card_type.value}"
        if self.power is not None and self.toughness is not None:
            result += f" {self.power}/{self.toughness}"
        return result

    def __eq__(self, other) -> bool:
        """Check equality with another card."""
        if not isinstance(other, Card):
            return False
        return (
            self.name == other.name
            and self.card_type == other.card_type
            and self.mana_cost == other.mana_cost
            and self.color == other.color
            and self.power == other.power
            and self.toughness == other.toughness
            and self.text == other.text
        )

    class Config:
        """Pydantic model configuration."""

        json_encoders = {
            CardType: lambda v: v.value,
            Color: lambda v: v.value,
            datetime: lambda v: v.isoformat(),
        }
