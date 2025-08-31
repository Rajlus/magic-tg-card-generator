"""Domain-specific pytest fixtures for comprehensive testing."""

import pytest
from datetime import datetime
from typing import List, Dict, Tuple

from magic_tg_card_generator.models import Card, CardType, Color


@pytest.fixture
def sample_creature_cards() -> List[Card]:
    """Provide a collection of sample creature cards for testing."""
    return [
        Card(
            name="Lightning Bolt Dragon",
            card_type=CardType.CREATURE,
            mana_cost="3RR",
            color=Color.RED,
            power=4,
            toughness=4,
            text="Flying, haste",
            flavor_text="A dragon's roar splits the sky.",
            rarity="Rare"
        ),
        Card(
            name="Serra Angel",
            card_type=CardType.CREATURE,
            mana_cost="3WW",
            color=Color.WHITE,
            power=4,
            toughness=4,
            text="Flying, vigilance",
            rarity="Rare"
        ),
        Card(
            name="Llanowar Elves",
            card_type=CardType.CREATURE,
            mana_cost="G",
            color=Color.GREEN,
            power=1,
            toughness=1,
            text="T: Add G.",
            rarity="Common"
        ),
        Card(
            name="Vampire Nighthawk",
            card_type=CardType.CREATURE,
            mana_cost="1BB",
            color=Color.BLACK,
            power=2,
            toughness=3,
            text="Flying, deathtouch, lifelink",
            rarity="Uncommon"
        ),
        Card(
            name="Delver of Secrets",
            card_type=CardType.CREATURE,
            mana_cost="U",
            color=Color.BLUE,
            power=1,
            toughness=1,
            text="At the beginning of your upkeep, look at the top card of your library.",
            rarity="Common"
        )
    ]


@pytest.fixture
def sample_spell_cards() -> List[Card]:
    """Provide a collection of sample non-creature spell cards for testing."""
    return [
        Card(
            name="Lightning Bolt",
            card_type=CardType.INSTANT,
            mana_cost="R",
            color=Color.RED,
            text="Deal 3 damage to any target.",
            flavor_text="The spark of the idea was brilliant.",
            rarity="Common"
        ),
        Card(
            name="Counterspell",
            card_type=CardType.INSTANT,
            mana_cost="UU",
            color=Color.BLUE,
            text="Counter target spell.",
            rarity="Common"
        ),
        Card(
            name="Wrath of God",
            card_type=CardType.SORCERY,
            mana_cost="2WW",
            color=Color.WHITE,
            text="Destroy all creatures. They can't be regenerated.",
            rarity="Rare"
        ),
        Card(
            name="Dark Ritual",
            card_type=CardType.INSTANT,
            mana_cost="B",
            color=Color.BLACK,
            text="Add BBB.",
            rarity="Common"
        ),
        Card(
            name="Giant Growth",
            card_type=CardType.INSTANT,
            mana_cost="G",
            color=Color.GREEN,
            text="Target creature gets +3/+3 until end of turn.",
            rarity="Common"
        )
    ]


@pytest.fixture
def sample_multicolor_cards() -> List[Card]:
    """Provide a collection of sample multicolor cards for testing."""
    return [
        Card(
            name="Lightning Helix",
            card_type=CardType.INSTANT,
            mana_cost="RW",
            color=Color.MULTICOLOR,
            text="Deal 3 damage to any target. You gain 3 life.",
            rarity="Uncommon"
        ),
        Card(
            name="Terminate",
            card_type=CardType.INSTANT,
            mana_cost="BR",
            color=Color.MULTICOLOR,
            text="Destroy target creature. It can't be regenerated.",
            rarity="Common"
        ),
        Card(
            name="Mystic Snake",
            card_type=CardType.CREATURE,
            mana_cost="1GU",
            color=Color.MULTICOLOR,
            power=2,
            toughness=2,
            text="Flash. When Mystic Snake enters the battlefield, counter target spell.",
            rarity="Rare"
        ),
        Card(
            name="Lightning Angel",
            card_type=CardType.CREATURE,
            mana_cost="1RWU",
            color=Color.MULTICOLOR,
            power=3,
            toughness=4,
            text="Flying, vigilance, haste",
            rarity="Rare"
        ),
        Card(
            name="Child of Alara",
            card_type=CardType.CREATURE,
            mana_cost="WUBRG",
            color=Color.MULTICOLOR,
            power=6,
            toughness=6,
            text="When Child of Alara dies, destroy all nonland permanents.",
            rarity="Mythic"
        )
    ]


@pytest.fixture
def sample_colorless_cards() -> List[Card]:
    """Provide a collection of sample colorless cards for testing."""
    return [
        Card(
            name="Sol Ring",
            card_type=CardType.ARTIFACT,
            mana_cost="1",
            color=Color.COLORLESS,
            text="T: Add CC.",
            rarity="Uncommon"
        ),
        Card(
            name="Black Lotus",
            card_type=CardType.ARTIFACT,
            mana_cost="0",
            color=Color.COLORLESS,
            text="T, Sacrifice Black Lotus: Add three mana of any one color.",
            rarity="Rare"
        ),
        Card(
            name="Ornithopter",
            card_type=CardType.CREATURE,
            mana_cost="0",
            color=Color.COLORLESS,
            power=0,
            toughness=2,
            text="Flying",
            rarity="Common"
        ),
        Card(
            name="Mana Crypt",
            card_type=CardType.ARTIFACT,
            mana_cost="0",
            color=Color.COLORLESS,
            text="At the beginning of your upkeep, flip a coin.",
            rarity="Mythic"
        ),
        Card(
            name="Eldrazi Temple",
            card_type=CardType.LAND,
            mana_cost="",
            color=Color.COLORLESS,
            text="T: Add C. T: Add CC. Spend this mana only to cast colorless spells.",
            rarity="Rare"
        )
    ]


@pytest.fixture
def sample_x_cost_cards() -> List[Card]:
    """Provide a collection of sample X-cost cards for testing."""
    return [
        Card(
            name="Fireball",
            card_type=CardType.SORCERY,
            mana_cost="XR",
            color=Color.RED,
            text="Deal X damage divided as you choose among any number of targets.",
            rarity="Common"
        ),
        Card(
            name="Braingeyser",
            card_type=CardType.SORCERY,
            mana_cost="XUU",
            color=Color.BLUE,
            text="Target player draws X cards.",
            rarity="Uncommon"
        ),
        Card(
            name="Stroke of Genius",
            card_type=CardType.INSTANT,
            mana_cost="X2U",
            color=Color.BLUE,
            text="Target player draws X cards.",
            rarity="Rare"
        ),
        Card(
            name="Hydra Broodmaster",
            card_type=CardType.CREATURE,
            mana_cost="4GG",
            color=Color.GREEN,
            power=7,
            toughness=7,
            text="XXG: Monstrosity X. When Hydra Broodmaster becomes monstrous, create X X/X green Hydra creature tokens.",
            rarity="Rare"
        ),
        Card(
            name="Villainous Wealth",
            card_type=CardType.SORCERY,
            mana_cost="XBUG",
            color=Color.MULTICOLOR,
            text="Target opponent exiles the top X cards of their library.",
            rarity="Rare"
        )
    ]


@pytest.fixture
def sample_land_cards() -> List[Card]:
    """Provide a collection of sample land cards for testing."""
    return [
        Card(
            name="Forest",
            card_type=CardType.LAND,
            mana_cost="",
            color=Color.GREEN,
            text="T: Add G.",
            rarity="Common"
        ),
        Card(
            name="Mountain",
            card_type=CardType.LAND,
            mana_cost="",
            color=Color.RED,
            text="T: Add R.",
            rarity="Common"
        ),
        Card(
            name="Underground Sea",
            card_type=CardType.LAND,
            mana_cost="",
            color=Color.MULTICOLOR,
            text="T: Add U or B.",
            rarity="Rare"
        ),
        Card(
            name="Command Tower",
            card_type=CardType.LAND,
            mana_cost="",
            color=Color.COLORLESS,
            text="T: Add one mana of any color in your commander's color identity.",
            rarity="Common"
        ),
        Card(
            name="Wasteland",
            card_type=CardType.LAND,
            mana_cost="",
            color=Color.COLORLESS,
            text="T: Add C. T, Sacrifice Wasteland: Destroy target nonbasic land.",
            rarity="Uncommon"
        )
    ]


@pytest.fixture
def sample_planeswalker_cards() -> List[Card]:
    """Provide a collection of sample planeswalker cards for testing."""
    return [
        Card(
            name="Jace, the Mind Sculptor",
            card_type=CardType.PLANESWALKER,
            mana_cost="2UU",
            color=Color.BLUE,
            text="+2: Look at the top card of target player's library.",
            rarity="Mythic"
        ),
        Card(
            name="Elspeth, Knight-Errant",
            card_type=CardType.PLANESWALKER,
            mana_cost="2WW",
            color=Color.WHITE,
            text="+1: Create a 1/1 white Soldier creature token.",
            rarity="Mythic"
        ),
        Card(
            name="Nicol Bolas, Planeswalker",
            card_type=CardType.PLANESWALKER,
            mana_cost="4UBBR",
            color=Color.MULTICOLOR,
            text="+3: Destroy target noncreature permanent.",
            rarity="Mythic"
        ),
        Card(
            name="Karn Liberated",
            card_type=CardType.PLANESWALKER,
            mana_cost="7",
            color=Color.COLORLESS,
            text="+4: Target player exiles a card from their hand.",
            rarity="Mythic"
        ),
        Card(
            name="Chandra, Torch of Defiance",
            card_type=CardType.PLANESWALKER,
            mana_cost="2RR",
            color=Color.RED,
            text="+1: Exile the top card of your library.",
            rarity="Mythic"
        )
    ]


@pytest.fixture
def mana_cost_test_cases() -> List[Tuple[str, int]]:
    """Provide comprehensive mana cost test cases with expected CMC values."""
    return [
        # Empty and zero costs
        ("", 0),
        ("0", 0),
        
        # Simple generic costs
        ("1", 1),
        ("2", 2),
        ("5", 5),
        ("10", 10),
        ("15", 15),
        ("20", 20),
        
        # Single colored mana
        ("W", 1),
        ("U", 1),
        ("B", 1),
        ("R", 1),
        ("G", 1),
        ("C", 1),
        
        # Multiple colored mana
        ("WW", 2),
        ("UU", 2),
        ("BBB", 3),
        ("RRR", 3),
        ("GGGGG", 5),
        ("WUBRG", 5),
        
        # Mixed costs
        ("1W", 2),
        ("2U", 3),
        ("3B", 4),
        ("2WW", 4),
        ("3UU", 5),
        ("1WUBRG", 6),
        ("10WUBRG", 15),
        
        # X costs
        ("X", 0),
        ("XW", 1),
        ("XUU", 2),
        ("X2R", 3),
        ("XX", 0),
        ("XXW", 1),
        ("XX2WW", 4),
        
        # Complex real-world costs
        ("2WW", 4),      # Wrath of God
        ("1UU", 3),      # Counterspell
        ("3UU", 5),      # Force of Will
        ("WUBRG", 5),    # Child of Alara
        ("16", 16),      # Draco
        ("XRR", 2),      # Rolling Thunder
        ("15GGGGGWWWWW", 25),  # Autochthon Wurm
    ]


@pytest.fixture
def color_identity_test_cases() -> List[Tuple[str, Color]]:
    """Provide comprehensive color identity test cases."""
    return [
        # Mono-color cases
        ("W", Color.WHITE),
        ("U", Color.BLUE),
        ("B", Color.BLACK),
        ("R", Color.RED),
        ("G", Color.GREEN),
        ("WW", Color.WHITE),
        ("UU", Color.BLUE),
        ("1W", Color.WHITE),
        ("2U", Color.BLUE),
        ("3BB", Color.BLACK),
        ("5RR", Color.RED),
        ("10G", Color.GREEN),
        
        # Colorless cases
        ("", Color.COLORLESS),
        ("0", Color.COLORLESS),
        ("1", Color.COLORLESS),
        ("5", Color.COLORLESS),
        ("C", Color.COLORLESS),
        ("1C", Color.COLORLESS),
        ("CC", Color.COLORLESS),
        ("16", Color.COLORLESS),
        
        # Two-color cases
        ("WU", Color.MULTICOLOR),
        ("WB", Color.MULTICOLOR),
        ("WR", Color.MULTICOLOR),
        ("WG", Color.MULTICOLOR),
        ("UB", Color.MULTICOLOR),
        ("UR", Color.MULTICOLOR),
        ("UG", Color.MULTICOLOR),
        ("BR", Color.MULTICOLOR),
        ("BG", Color.MULTICOLOR),
        ("RG", Color.MULTICOLOR),
        ("1WU", Color.MULTICOLOR),
        ("2WB", Color.MULTICOLOR),
        
        # Three+ color cases
        ("WUB", Color.MULTICOLOR),
        ("WUR", Color.MULTICOLOR),
        ("WUBRG", Color.MULTICOLOR),
        ("1WUBRG", Color.MULTICOLOR),
        ("2WUBRG", Color.MULTICOLOR),
        
        # X costs with colors
        ("XW", Color.WHITE),
        ("XU", Color.BLUE),
        ("XWU", Color.MULTICOLOR),
        ("XWUBRG", Color.MULTICOLOR),
    ]


@pytest.fixture
def invalid_mana_cost_patterns() -> List[str]:
    """Provide invalid mana cost patterns for validation testing."""
    return [
        "Y",           # Invalid mana symbol
        "Z",           # Invalid mana symbol  
        "1Y",          # Contains invalid symbol
        "2Z3",         # Contains invalid symbol
        "WQ",          # Q is not valid
        "UL",          # L is not valid
        "BH",          # H is not valid
        "RF",          # F is not valid
        "GJ",          # J is not valid
        "1WY",         # Mixed valid and invalid
        "abc",         # Lowercase letters
        "wubrg",       # Lowercase colored mana
        "1w2u",        # Lowercase in mixed cost
        "!@#",         # Special characters
        "W U",         # Spaces not allowed
        "1-R",         # Hyphens not allowed
        "W/U",         # Slashes not allowed
        "(2/W)",       # Parentheses not allowed
        "{W}",         # Curly braces not allowed
    ]


@pytest.fixture
def all_card_types() -> List[CardType]:
    """Provide all available card types for testing."""
    return [
        CardType.CREATURE,
        CardType.INSTANT,
        CardType.SORCERY,
        CardType.ENCHANTMENT,
        CardType.ARTIFACT,
        CardType.PLANESWALKER,
        CardType.LAND
    ]


@pytest.fixture
def all_colors() -> List[Color]:
    """Provide all available colors for testing."""
    return [
        Color.WHITE,
        Color.BLUE,
        Color.BLACK,
        Color.RED,
        Color.GREEN,
        Color.COLORLESS,
        Color.MULTICOLOR
    ]


@pytest.fixture
def all_rarities() -> List[str]:
    """Provide all valid rarity values for testing."""
    return ["Common", "Uncommon", "Rare", "Mythic"]


@pytest.fixture
def boundary_test_cases() -> Dict[str, List]:
    """Provide boundary test cases for various validation rules."""
    return {
        "valid_names": [
            "A",  # Minimum length (1 character)
            "A" * 100,  # Maximum length (100 characters)
            "Test Card",
            "Jace, the Mind Sculptor",
            "Serra's Angel",
            "Lightning Bolt Dragon",
        ],
        "invalid_names": [
            "",  # Too short
            "A" * 101,  # Too long
        ],
        "valid_power_toughness": [
            (0, 0),  # Minimum values
            (99, 99),  # Maximum values
            (1, 1),
            (5, 5),
            (10, 8),
        ],
        "invalid_power_toughness": [
            (-1, 1),  # Negative power
            (1, -1),  # Negative toughness
            (100, 1),  # Power too high
            (1, 100),  # Toughness too high
        ],
        "valid_text_lengths": [
            "",  # Empty (allowed for optional field)
            "A" * 500,  # Maximum length
            "Flying",
            "When this creature enters the battlefield, draw a card.",
        ],
        "invalid_text_lengths": [
            "A" * 501,  # Too long
        ],
        "valid_flavor_text_lengths": [
            "",  # Empty (allowed for optional field)
            "A" * 300,  # Maximum length
            "The spark of the idea was brilliant.",
        ],
        "invalid_flavor_text_lengths": [
            "A" * 301,  # Too long
        ],
    }


@pytest.fixture
def famous_mtg_cards() -> List[Dict[str, any]]:
    """Provide data for famous MTG cards for realistic testing."""
    return [
        {
            "name": "Lightning Bolt",
            "card_type": CardType.INSTANT,
            "mana_cost": "R",
            "color": Color.RED,
            "text": "Deal 3 damage to any target.",
            "rarity": "Common"
        },
        {
            "name": "Black Lotus",
            "card_type": CardType.ARTIFACT,
            "mana_cost": "0",
            "color": Color.COLORLESS,
            "text": "T, Sacrifice Black Lotus: Add three mana of any one color.",
            "rarity": "Rare"
        },
        {
            "name": "Ancestral Recall",
            "card_type": CardType.INSTANT,
            "mana_cost": "U",
            "color": Color.BLUE,
            "text": "Target player draws three cards.",
            "rarity": "Rare"
        },
        {
            "name": "Serra Angel",
            "card_type": CardType.CREATURE,
            "mana_cost": "3WW",
            "color": Color.WHITE,
            "power": 4,
            "toughness": 4,
            "text": "Flying, vigilance",
            "rarity": "Rare"
        },
        {
            "name": "Shivan Dragon",
            "card_type": CardType.CREATURE,
            "mana_cost": "4RR",
            "color": Color.RED,
            "power": 5,
            "toughness": 5,
            "text": "Flying",
            "rarity": "Rare"
        },
        {
            "name": "Force of Nature",
            "card_type": CardType.CREATURE,
            "mana_cost": "2GGGG",
            "color": Color.GREEN,
            "power": 8,
            "toughness": 8,
            "text": "Trample. At the beginning of your upkeep, Force of Nature deals 8 damage to you unless you pay GGGG.",
            "rarity": "Rare"
        },
        {
            "name": "Nightmare",
            "card_type": CardType.CREATURE,
            "mana_cost": "5B",
            "color": Color.BLACK,
            "power": 99,  # Variable, using max for test
            "toughness": 99,  # Variable, using max for test
            "text": "Flying. Nightmare's power and toughness are each equal to the number of Swamps you control.",
            "rarity": "Rare"
        }
    ]


@pytest.fixture
def edge_case_cards() -> List[Dict[str, any]]:
    """Provide edge case card data for comprehensive testing."""
    return [
        {
            "name": "Zero Power Creature",
            "card_type": CardType.CREATURE,
            "mana_cost": "1",
            "color": Color.COLORLESS,
            "power": 0,
            "toughness": 1,
            "text": "Test creature with zero power.",
            "rarity": "Common"
        },
        {
            "name": "Zero Toughness Creature",
            "card_type": CardType.CREATURE,
            "mana_cost": "1",
            "color": Color.COLORLESS,
            "power": 1,
            "toughness": 0,
            "text": "Test creature with zero toughness.",
            "rarity": "Common"
        },
        {
            "name": "Maximum Stats Creature",
            "card_type": CardType.CREATURE,
            "mana_cost": "20",
            "color": Color.COLORLESS,
            "power": 99,
            "toughness": 99,
            "text": "Test creature with maximum stats.",
            "rarity": "Mythic"
        },
        {
            "name": "Empty Text Card",
            "card_type": CardType.INSTANT,
            "mana_cost": "0",
            "color": Color.COLORLESS,
            "rarity": "Common"
        },
        {
            "name": "Maximum Text Length Card",
            "card_type": CardType.ENCHANTMENT,
            "mana_cost": "5",
            "color": Color.COLORLESS,
            "text": "A" * 500,  # Maximum allowed text length
            "flavor_text": "A" * 300,  # Maximum allowed flavor text length
            "rarity": "Rare"
        }
    ]