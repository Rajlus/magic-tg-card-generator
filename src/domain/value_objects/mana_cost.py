"""Value object for Magic: The Gathering mana costs."""

import re
from typing import Dict, Set, Union, List
from dataclasses import dataclass


@dataclass(frozen=True)
class ManaCost:
    """
    Immutable value object representing a Magic: The Gathering mana cost.
    
    Supports standard MTG mana cost notation including:
    - Generic mana: {1}, {2}, {3}, etc.
    - Colored mana: {W}, {U}, {B}, {R}, {G}
    - Variable costs: {X}
    - Hybrid costs: {2/W}, {R/G}, {W/U}, etc.
    - Phyrexian mana: {W/P}, {U/P}, {B/P}, {R/P}, {G/P}
    - Snow mana: {S}
    - Colorless mana: {C}
    """
    
    mana_string: str
    
    # MTG mana symbols mapping
    COLOR_SYMBOLS = {'W', 'U', 'B', 'R', 'G'}
    SPECIAL_SYMBOLS = {'X', 'Y', 'Z', 'C', 'S'}
    
    def __post_init__(self):
        """Validate mana cost string format after initialization."""
        if not self._is_valid_mana_cost(self.mana_string):
            raise ValueError(f"Invalid mana cost format: {self.mana_string}")
    
    @classmethod
    def from_string(cls, mana_string: str) -> 'ManaCost':
        """Create a ManaCost from a mana string."""
        return cls(mana_string.strip())
    
    @classmethod
    def from_components(cls, generic: int = 0, white: int = 0, blue: int = 0, 
                       black: int = 0, red: int = 0, green: int = 0, 
                       colorless: int = 0, x_count: int = 0) -> 'ManaCost':
        """Create a ManaCost from individual mana components."""
        components = []
        
        # Add X symbols first
        if x_count > 0:
            components.extend(['{X}'] * x_count)
        
        # Add generic mana
        if generic > 0:
            components.append(f'{{{generic}}}')
        
        # Add colored mana
        if white > 0:
            components.extend(['{W}'] * white)
        if blue > 0:
            components.extend(['{U}'] * blue)
        if black > 0:
            components.extend(['{B}'] * black)
        if red > 0:
            components.extend(['{R}'] * red)
        if green > 0:
            components.extend(['{G}'] * green)
        if colorless > 0:
            components.extend(['{C}'] * colorless)
        
        return cls(''.join(components))
    
    def _is_valid_mana_cost(self, mana_string: str) -> bool:
        """Validate that the mana cost string follows MTG notation."""
        if not mana_string:
            return True  # Empty cost is valid (free spells)
        
        # Pattern for valid mana symbols
        pattern = r'^(\{(?:\d+|[WUBRGCSXYZ]|[WUBRG]/[WUBRG]|[WUBRG]/P|\d+/[WUBRG])\})*$'
        return bool(re.match(pattern, mana_string))
    
    def _parse_mana_symbols(self) -> List[str]:
        """Parse mana string into individual mana symbols."""
        if not self.mana_string:
            return []
        
        pattern = r'\{([^}]+)\}'
        return re.findall(pattern, self.mana_string)
    
    @property
    def converted_mana_cost(self) -> int:
        """
        Calculate the converted mana cost (CMC/Mana Value).
        
        Returns the total mana cost where:
        - Numbers add their face value
        - Colored symbols add 1 each
        - X, Y, Z count as 0
        - Hybrid symbols add 1 (the cheaper cost)
        - Phyrexian symbols add 1
        """
        symbols = self._parse_mana_symbols()
        total = 0
        
        for symbol in symbols:
            if symbol.isdigit():
                total += int(symbol)
            elif symbol in self.COLOR_SYMBOLS:
                total += 1
            elif symbol == 'C':  # Colorless mana
                total += 1
            elif symbol == 'S':  # Snow mana
                total += 1
            elif '/' in symbol:  # Hybrid or Phyrexian
                total += 1
            # X, Y, Z count as 0 for CMC
        
        return total
    
    @property
    def color_requirements(self) -> Dict[str, int]:
        """
        Get the color requirements for this mana cost.
        
        Returns a dictionary with color symbols and their counts.
        Does not include generic mana or variable costs.
        """
        symbols = self._parse_mana_symbols()
        colors = {'W': 0, 'U': 0, 'B': 0, 'R': 0, 'G': 0}
        
        for symbol in symbols:
            if symbol in colors:
                colors[symbol] += 1
            elif '/' in symbol and not '/P' in symbol:  # Hybrid mana
                parts = symbol.split('/')
                if len(parts) == 2:
                    # For hybrid, we consider both colors as requirements
                    for part in parts:
                        if part in colors:
                            colors[part] += 1
        
        # Remove colors with 0 count
        return {color: count for color, count in colors.items() if count > 0}
    
    @property
    def generic_mana(self) -> int:
        """Get the amount of generic mana required."""
        symbols = self._parse_mana_symbols()
        total = 0
        
        for symbol in symbols:
            if symbol.isdigit():
                total += int(symbol)
        
        return total
    
    @property
    def colored_mana_count(self) -> int:
        """Get the total count of colored mana symbols."""
        return sum(self.color_requirements.values())
    
    @property
    def is_free(self) -> bool:
        """Check if this is a free spell (no mana cost)."""
        return not self.mana_string or self.mana_string == ''
    
    @property
    def has_x_cost(self) -> bool:
        """Check if this mana cost includes X."""
        return 'X' in self.mana_string
    
    @property
    def has_hybrid_mana(self) -> bool:
        """Check if this mana cost includes hybrid mana."""
        symbols = self._parse_mana_symbols()
        return any('/' in symbol for symbol in symbols)
    
    @property
    def has_phyrexian_mana(self) -> bool:
        """Check if this mana cost includes Phyrexian mana."""
        return '/P' in self.mana_string
    
    def contains_color(self, color: str) -> bool:
        """
        Check if this mana cost contains a specific color.
        
        Args:
            color: Single color symbol ('W', 'U', 'B', 'R', 'G')
        """
        if color not in self.COLOR_SYMBOLS:
            raise ValueError(f"Invalid color symbol: {color}")
        
        return color in self.color_requirements
    
    def can_be_paid_with_colors(self, available_colors: Set[str]) -> bool:
        """
        Check if this mana cost can be paid with the available colors.
        
        Args:
            available_colors: Set of color symbols that can be produced
        """
        required_colors = set(self.color_requirements.keys())
        return required_colors.issubset(available_colors)
    
    def __str__(self) -> str:
        """Return the mana cost string representation."""
        return self.mana_string
    
    def __repr__(self) -> str:
        """Return a detailed representation."""
        return f"ManaCost('{self.mana_string}', CMC={self.converted_mana_cost})"
    
    def __bool__(self) -> bool:
        """Check if this mana cost has any requirements."""
        return bool(self.mana_string)
    
    def __add__(self, other: Union['ManaCost', str]) -> 'ManaCost':
        """Add two mana costs together."""
        if isinstance(other, str):
            other = ManaCost(other)
        elif not isinstance(other, ManaCost):
            raise TypeError("Can only add ManaCost to ManaCost or str")
        
        return ManaCost(self.mana_string + other.mana_string)
    
    def __eq__(self, other) -> bool:
        """Check equality with another ManaCost."""
        if not isinstance(other, ManaCost):
            return False
        return self.mana_string == other.mana_string
    
    def __hash__(self) -> int:
        """Make ManaCost hashable."""
        return hash(self.mana_string)