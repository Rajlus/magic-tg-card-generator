"""Value object for Magic: The Gathering card colors."""

from typing import Set, FrozenSet, Union, List
from dataclasses import dataclass
from enum import Enum

from .mana_cost import ManaCost


class MTGColor(Enum):
    """Enumeration of Magic: The Gathering colors."""
    WHITE = 'W'
    BLUE = 'U'
    BLACK = 'B'
    RED = 'R'
    GREEN = 'G'


@dataclass(frozen=True)
class CardColors:
    """
    Immutable value object representing a Magic: The Gathering card's color identity.
    
    Handles WUBRG (White, Blue, Black, Red, Green) color system and provides
    methods for color identity analysis and validation.
    """
    
    colors: FrozenSet[str]
    
    # Color constants
    ALL_COLORS = frozenset({'W', 'U', 'B', 'R', 'G'})
    COLOR_NAMES = {
        'W': 'White',
        'U': 'Blue', 
        'B': 'Black',
        'R': 'Red',
        'G': 'Green'
    }
    
    def __post_init__(self):
        """Validate colors after initialization."""
        if not isinstance(self.colors, frozenset):
            object.__setattr__(self, 'colors', frozenset(self.colors))
        
        # Validate all colors are valid MTG colors
        invalid_colors = self.colors - self.ALL_COLORS
        if invalid_colors:
            raise ValueError(f"Invalid color symbols: {invalid_colors}")
    
    @classmethod
    def from_colors(cls, *colors: str) -> 'CardColors':
        """Create CardColors from individual color symbols."""
        return cls(frozenset(colors))
    
    @classmethod
    def from_mana_cost(cls, mana_cost: Union[ManaCost, str]) -> 'CardColors':
        """
        Derive color identity from a mana cost.
        
        Args:
            mana_cost: ManaCost object or mana cost string
        """
        if isinstance(mana_cost, str):
            mana_cost = ManaCost(mana_cost)
        
        colors = set()
        symbols = mana_cost._parse_mana_symbols()
        
        for symbol in symbols:
            if symbol in cls.ALL_COLORS:
                # Direct colored mana
                colors.add(symbol)
            elif '/' in symbol:
                # Hybrid or Phyrexian mana
                parts = symbol.split('/')
                for part in parts:
                    if part in cls.ALL_COLORS:
                        colors.add(part)
                    # For Phyrexian mana like "W/P", we still want the "W"
        
        return cls(frozenset(colors))
    
    @classmethod
    def white(cls) -> 'CardColors':
        """Create mono-white colors."""
        return cls(frozenset(['W']))
    
    @classmethod
    def blue(cls) -> 'CardColors':
        """Create mono-blue colors."""
        return cls(frozenset(['U']))
    
    @classmethod
    def black(cls) -> 'CardColors':
        """Create mono-black colors."""
        return cls(frozenset(['B']))
    
    @classmethod
    def red(cls) -> 'CardColors':
        """Create mono-red colors."""
        return cls(frozenset(['R']))
    
    @classmethod
    def green(cls) -> 'CardColors':
        """Create mono-green colors."""
        return cls(frozenset(['G']))
    
    @classmethod
    def colorless(cls) -> 'CardColors':
        """Create colorless (no colors)."""
        return cls(frozenset())
    
    @classmethod
    def all_colors(cls) -> 'CardColors':
        """Create WUBRG (all five colors)."""
        return cls(cls.ALL_COLORS)
    
    @property
    def is_colorless(self) -> bool:
        """Check if this card has no colors."""
        return len(self.colors) == 0
    
    @property
    def is_monocolored(self) -> bool:
        """Check if this card has exactly one color."""
        return len(self.colors) == 1
    
    @property
    def is_multicolored(self) -> bool:
        """Check if this card has two or more colors."""
        return len(self.colors) >= 2
    
    @property
    def is_white(self) -> bool:
        """Check if this card is mono-white."""
        return self.colors == frozenset(['W'])
    
    @property
    def is_blue(self) -> bool:
        """Check if this card is mono-blue."""
        return self.colors == frozenset(['U'])
    
    @property
    def is_black(self) -> bool:
        """Check if this card is mono-black."""
        return self.colors == frozenset(['B'])
    
    @property
    def is_red(self) -> bool:
        """Check if this card is mono-red."""
        return self.colors == frozenset(['R'])
    
    @property
    def is_green(self) -> bool:
        """Check if this card is mono-green."""
        return self.colors == frozenset(['G'])
    
    @property
    def is_guild(self) -> bool:
        """Check if this is a two-color combination (guild)."""
        return len(self.colors) == 2
    
    @property
    def is_shard(self) -> bool:
        """Check if this is a three-color allied combination (shard)."""
        if len(self.colors) != 3:
            return False
        
        # Allied three-color combinations (shards)
        shards = [
            frozenset(['W', 'U', 'G']),  # Bant
            frozenset(['U', 'B', 'R']),  # Grixis  
            frozenset(['B', 'R', 'G']),  # Jund
            frozenset(['R', 'G', 'W']),  # Naya
            frozenset(['G', 'W', 'U'])   # Bant (alternative representation)
        ]
        
        return self.colors in shards
    
    @property
    def is_wedge(self) -> bool:
        """Check if this is a three-color enemy combination (wedge)."""
        if len(self.colors) != 3:
            return False
        
        # Enemy three-color combinations (wedges)
        wedges = [
            frozenset(['W', 'B', 'G']),  # Abzan
            frozenset(['U', 'R', 'W']),  # Jeskai
            frozenset(['B', 'G', 'U']),  # Sultai
            frozenset(['R', 'W', 'B']),  # Mardu
            frozenset(['G', 'U', 'R'])   # Temur
        ]
        
        return self.colors in wedges
    
    @property
    def is_four_color(self) -> bool:
        """Check if this is a four-color combination."""
        return len(self.colors) == 4
    
    @property
    def is_five_color(self) -> bool:
        """Check if this is a five-color combination (WUBRG)."""
        return len(self.colors) == 5
    
    @property
    def color_count(self) -> int:
        """Get the number of colors in this color identity."""
        return len(self.colors)
    
    @property
    def color_names(self) -> List[str]:
        """Get the full names of the colors in WUBRG order."""
        ordered_colors = [color for color in ['W', 'U', 'B', 'R', 'G'] if color in self.colors]
        return [self.COLOR_NAMES[color] for color in ordered_colors]
    
    @property
    def guild_name(self) -> str:
        """
        Get the name of the two-color guild combination.
        Returns empty string if not a guild.
        """
        if not self.is_guild:
            return ""
        
        guild_names = {
            frozenset(['W', 'U']): 'Azorius',
            frozenset(['U', 'B']): 'Dimir', 
            frozenset(['B', 'R']): 'Rakdos',
            frozenset(['R', 'G']): 'Gruul',
            frozenset(['G', 'W']): 'Selesnya',
            frozenset(['W', 'B']): 'Orzhov',
            frozenset(['U', 'R']): 'Izzet',
            frozenset(['B', 'G']): 'Golgari',
            frozenset(['R', 'W']): 'Boros',
            frozenset(['G', 'U']): 'Simic'
        }
        
        return guild_names.get(self.colors, "")
    
    @property
    def shard_name(self) -> str:
        """
        Get the name of the three-color shard combination.
        Returns empty string if not a shard.
        """
        if not self.is_shard:
            return ""
        
        shard_names = {
            frozenset(['W', 'U', 'G']): 'Bant',
            frozenset(['U', 'B', 'R']): 'Grixis',
            frozenset(['B', 'R', 'G']): 'Jund', 
            frozenset(['R', 'G', 'W']): 'Naya',
            frozenset(['G', 'W', 'U']): 'Bant'
        }
        
        return shard_names.get(self.colors, "")
    
    @property
    def wedge_name(self) -> str:
        """
        Get the name of the three-color wedge combination.
        Returns empty string if not a wedge.
        """
        if not self.is_wedge:
            return ""
        
        wedge_names = {
            frozenset(['W', 'B', 'G']): 'Abzan',
            frozenset(['U', 'R', 'W']): 'Jeskai',
            frozenset(['B', 'G', 'U']): 'Sultai',
            frozenset(['R', 'W', 'B']): 'Mardu',
            frozenset(['G', 'U', 'R']): 'Temur'
        }
        
        return wedge_names.get(self.colors, "")
    
    def contains_color(self, color: str) -> bool:
        """
        Check if this color identity contains a specific color.
        
        Args:
            color: Single color symbol ('W', 'U', 'B', 'R', 'G')
        """
        if color not in self.ALL_COLORS:
            raise ValueError(f"Invalid color symbol: {color}")
        
        return color in self.colors
    
    def shares_colors_with(self, other: 'CardColors') -> bool:
        """Check if this color identity shares any colors with another."""
        return bool(self.colors & other.colors)
    
    def is_subset_of(self, other: 'CardColors') -> bool:
        """Check if this color identity is a subset of another."""
        return self.colors.issubset(other.colors)
    
    def is_superset_of(self, other: 'CardColors') -> bool:
        """Check if this color identity is a superset of another."""
        return self.colors.issuperset(other.colors)
    
    def union_with(self, other: 'CardColors') -> 'CardColors':
        """Create a new CardColors with the union of both color identities."""
        return CardColors(self.colors | other.colors)
    
    def intersection_with(self, other: 'CardColors') -> 'CardColors':
        """Create a new CardColors with the intersection of both color identities."""
        return CardColors(self.colors & other.colors)
    
    def without_colors(self, *colors: str) -> 'CardColors':
        """Create a new CardColors without the specified colors."""
        return CardColors(self.colors - frozenset(colors))
    
    def add_colors(self, *colors: str) -> 'CardColors':
        """Create a new CardColors with additional colors."""
        return CardColors(self.colors | frozenset(colors))
    
    def __str__(self) -> str:
        """Return string representation of colors in WUBRG order."""
        if self.is_colorless:
            return "Colorless"
        
        ordered_colors = [color for color in ['W', 'U', 'B', 'R', 'G'] if color in self.colors]
        return ''.join(ordered_colors)
    
    def __repr__(self) -> str:
        """Return detailed representation."""
        if self.is_colorless:
            return "CardColors(colorless)"
        
        color_names = ', '.join(self.color_names)
        return f"CardColors({color_names})"
    
    def __bool__(self) -> bool:
        """Check if this has any colors (not colorless)."""
        return bool(self.colors)
    
    def __len__(self) -> int:
        """Return the number of colors."""
        return len(self.colors)
    
    def __iter__(self):
        """Iterate over colors in WUBRG order."""
        ordered = [color for color in ['W', 'U', 'B', 'R', 'G'] if color in self.colors]
        return iter(ordered)
    
    def __contains__(self, color: str) -> bool:
        """Check if a color is contained in this color identity."""
        return color in self.colors
    
    def __eq__(self, other) -> bool:
        """Check equality with another CardColors."""
        if not isinstance(other, CardColors):
            return False
        return self.colors == other.colors
    
    def __hash__(self) -> int:
        """Make CardColors hashable."""
        return hash(self.colors)
    
    def __or__(self, other: 'CardColors') -> 'CardColors':
        """Union operator (|)."""
        return self.union_with(other)
    
    def __and__(self, other: 'CardColors') -> 'CardColors':
        """Intersection operator (&)."""
        return self.intersection_with(other)
    
    def __sub__(self, other: 'CardColors') -> 'CardColors':
        """Difference operator (-)."""
        return CardColors(self.colors - other.colors)