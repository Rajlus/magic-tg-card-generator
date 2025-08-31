"""Enumeration for Magic: The Gathering card rarities."""

from enum import Enum


class Rarity(str, Enum):
    """Enumeration of Magic card rarities.
    
    The rarities are defined in increasing order of rarity and value.
    """
    
    COMMON = "common"
    UNCOMMON = "uncommon" 
    RARE = "rare"
    MYTHIC = "mythic"
    
    def __str__(self) -> str:
        """Return the string representation of the rarity."""
        return self.value
    
    @property
    def display_name(self) -> str:
        """Return the capitalized display name for UI purposes."""
        return self.value.capitalize()
    
    @classmethod
    def from_string(cls, value: str) -> 'Rarity':
        """Create a Rarity from a string value, case-insensitive."""
        if not isinstance(value, str):
            raise ValueError(f"Expected string, got {type(value)}")
        
        normalized = value.lower().strip()
        for rarity in cls:
            if rarity.value == normalized:
                return rarity
        
        raise ValueError(f"Invalid rarity: {value}. Valid rarities are: {[r.value for r in cls]}")