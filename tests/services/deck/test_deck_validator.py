"""
Tests for DeckValidator functionality
"""

import unittest
from unittest.mock import Mock

from src.domain.models.mtg_card import MTGCard
from src.services.deck.deck_validator import DeckValidator, DeckFormat, ValidationResult
from src.services.deck.card_collection import CardCollection


class TestDeckValidator(unittest.TestCase):
    """Test cases for DeckValidator."""

    def setUp(self):
        """Set up test fixtures."""
        self.commander_validator = DeckValidator(DeckFormat.COMMANDER)
        self.standard_validator = DeckValidator(DeckFormat.STANDARD)
        self.pauper_validator = DeckValidator(DeckFormat.PAUPER)

    def create_test_card(self, name: str, type_line: str = "Creature", cost: str = "{2}{R}", 
                        rarity: str = "common", text: str = "", power: int = 2, toughness: int = 2) -> MTGCard:
        """Helper to create test cards."""
        return MTGCard(
            id=hash(name) % 1000,
            name=name,
            type=type_line,
            cost=cost,
            text=text,
            power=power if "Creature" in type_line else None,
            toughness=toughness if "Creature" in type_line else None,
            rarity=rarity
        )

    def test_commander_deck_validation_success(self):
        """Test successful Commander deck validation."""
        # Create a commander
        commander = self.create_test_card(
            "Sol Ring Commander", 
            "Legendary Creature - Artifact", 
            "{2}{R}{W}",
            "mythic"
        )
        
        # Create a valid 100-card deck
        deck = CardCollection()
        
        # Add some lands (including basics)
        basics = ["Plains", "Mountain", "Island", "Swamp", "Forest"]
        for i, basic in enumerate(basics * 8):  # 40 basic lands
            deck.add_card(self.create_test_card(f"{basic}_{i}", "Basic Land", "", "common", ""))
        
        # Add 59 more cards with commander's color identity
        for i in range(59):
            deck.add_card(self.create_test_card(
                f"Test Card {i}", 
                "Creature", 
                "{1}{R}" if i % 2 == 0 else "{1}{W}",
                "common"
            ))
        
        # Add Sol Ring (1 card, total = 100)
        deck.add_card(self.create_test_card("Sol Ring", "Artifact", "{1}", "uncommon"))
        
        result = self.commander_validator.validate(deck, commander)
        
        self.assertTrue(result.is_valid, f"Validation failed with errors: {result.errors}")
        self.assertEqual(len(result.errors), 0)

    def test_commander_deck_wrong_card_count(self):
        """Test Commander deck with wrong card count."""
        commander = self.create_test_card("Test Commander", "Legendary Creature", "{2}{G}")
        deck = CardCollection()
        
        # Only add 50 cards
        for i in range(50):
            deck.add_card(self.create_test_card(f"Card {i}", "Creature", "{1}{G}"))
        
        result = self.commander_validator.validate(deck, commander)
        
        self.assertFalse(result.is_valid)
        self.assertTrue(any("50 cards but requires at least 100" in error for error in result.errors))

    def test_commander_deck_color_identity_violation(self):
        """Test Commander deck with color identity violation."""
        # Red commander
        commander = self.create_test_card("Fire Commander", "Legendary Creature", "{2}{R}")
        deck = CardCollection()
        
        # Add a blue card (violates color identity)
        deck.add_card(self.create_test_card("Blue Card", "Creature", "{U}"))
        
        # Add 99 more valid red cards to reach 100
        for i in range(99):
            deck.add_card(self.create_test_card(f"Red Card {i}", "Creature", "{1}{R}"))
        
        result = self.commander_validator.validate(deck, commander)
        
        self.assertFalse(result.is_valid)
        self.assertTrue(any("not in commander's color identity" in error for error in result.errors))

    def test_commander_deck_singleton_violation(self):
        """Test Commander deck with singleton violation."""
        commander = self.create_test_card("Test Commander", "Legendary Creature", "{2}{R}")
        deck = CardCollection()
        
        # Add duplicate non-basic cards
        duplicate_card = self.create_test_card("Lightning Bolt", "Instant", "{R}")
        deck.add_card(duplicate_card)
        deck.add_card(duplicate_card)
        
        # Add 98 more cards to reach 100
        for i in range(98):
            deck.add_card(self.create_test_card(f"Card {i}", "Creature", "{1}{R}"))
        
        result = self.commander_validator.validate(deck, commander)
        
        self.assertFalse(result.is_valid)
        self.assertTrue(any("appears 2 times, but singleton" in error for error in result.errors))

    def test_commander_deck_banned_card(self):
        """Test Commander deck with banned card."""
        commander = self.create_test_card("Test Commander", "Legendary Creature", "{2}{R}")
        deck = CardCollection()
        
        # Add banned card
        deck.add_card(self.create_test_card("Black Lotus", "Artifact", "{0}"))
        
        # Add 99 more valid cards
        for i in range(99):
            deck.add_card(self.create_test_card(f"Card {i}", "Creature", "{1}{R}"))
        
        result = self.commander_validator.validate(deck, commander)
        
        self.assertFalse(result.is_valid)
        self.assertTrue(any("Black Lotus" in error and "banned" in error for error in result.errors))

    def test_standard_deck_validation(self):
        """Test Standard deck validation."""
        deck = CardCollection()
        
        # Add 60 cards (minimum for Standard)
        for i in range(15):  # 15 different cards, 4 copies each = 60 cards
            card = self.create_test_card(f"Standard Card {i}", "Creature", "{2}")
            for _ in range(4):  # 4 copies allowed in Standard
                deck.add_card(card)
        
        result = self.standard_validator.validate(deck)
        
        self.assertTrue(result.is_valid, f"Validation failed: {result.errors}")

    def test_standard_deck_too_many_copies(self):
        """Test Standard deck with too many copies of a card."""
        deck = CardCollection()
        
        # Add 5 copies of the same card (violates 4-copy limit)
        card = self.create_test_card("Lightning Bolt", "Instant", "{R}")
        for _ in range(5):
            deck.add_card(card)
        
        # Add more cards to reach minimum
        for i in range(55):
            deck.add_card(self.create_test_card(f"Filler {i}", "Creature", "{2}"))
        
        result = self.standard_validator.validate(deck)
        
        self.assertFalse(result.is_valid)
        self.assertTrue(any("appears 5 times" in error and "maximum 4" in error for error in result.errors))

    def test_pauper_deck_validation(self):
        """Test Pauper deck validation (commons only)."""
        deck = CardCollection()
        
        # Add 60 common cards
        for i in range(60):
            deck.add_card(self.create_test_card(f"Common {i}", "Creature", "{2}", "common"))
        
        result = self.pauper_validator.validate(deck)
        
        self.assertTrue(result.is_valid)

    def test_pauper_deck_non_common_card(self):
        """Test Pauper deck with non-common card."""
        deck = CardCollection()
        
        # Add uncommon card (violates Pauper rules)
        deck.add_card(self.create_test_card("Uncommon Card", "Creature", "{2}", "uncommon"))
        
        # Add 59 common cards
        for i in range(59):
            deck.add_card(self.create_test_card(f"Common {i}", "Creature", "{2}", "common"))
        
        result = self.pauper_validator.validate(deck)
        
        self.assertFalse(result.is_valid)
        self.assertTrue(any("rarity 'uncommon' but Pauper" in error for error in result.errors))

    def test_basic_land_identification(self):
        """Test basic land identification."""
        plains = self.create_test_card("Plains", "Basic Land - Plains")
        mountain = self.create_test_card("Mountain", "Basic Land - Mountain") 
        shock_land = self.create_test_card("Steam Vents", "Land - Island Mountain")
        
        self.assertTrue(self.commander_validator.is_basic_land(plains))
        self.assertTrue(self.commander_validator.is_basic_land(mountain))
        self.assertFalse(self.commander_validator.is_basic_land(shock_land))

    def test_color_identity_extraction(self):
        """Test color identity extraction from cards."""
        # Test mana cost colors
        red_card = self.create_test_card("Fire", "Instant", "{2}{R}")
        multicolor_card = self.create_test_card("Gold", "Creature", "{R}{W}{U}")
        
        red_identity = self.commander_validator.get_color_identity(red_card)
        multi_identity = self.commander_validator.get_color_identity(multicolor_card)
        
        self.assertEqual(red_identity, {'R'})
        self.assertEqual(multi_identity, {'R', 'W', 'U'})

    def test_validation_suggestions(self):
        """Test that validation provides helpful suggestions."""
        commander = self.create_test_card("Expensive Commander", "Legendary Creature", "{6}{R}{R}")
        deck = CardCollection()
        
        # Create deck with high mana curve and few lands
        for i in range(100):
            cost = "{6}" if i < 50 else "{7}"  # High mana cost cards
            deck.add_card(self.create_test_card(f"Expensive {i}", "Creature", cost))
        
        result = self.commander_validator.validate(deck, commander)
        
        # Should have suggestions about mana curve and ramp
        self.assertTrue(len(result.suggestions) > 0)
        suggestion_text = " ".join(result.suggestions)
        self.assertTrue("mana" in suggestion_text.lower() or "ramp" in suggestion_text.lower())

    def test_deck_composition_warnings(self):
        """Test deck composition analysis warnings."""
        commander = self.create_test_card("Commander", "Legendary Creature", "{2}{R}")
        deck = CardCollection()
        
        # Create deck with no creatures (unusual composition)
        for i in range(100):
            deck.add_card(self.create_test_card(f"Spell {i}", "Instant", "{2}"))
        
        result = self.commander_validator.validate(deck, commander)
        
        # Should warn about low creature count
        self.assertTrue(any("creature count" in warning.lower() for warning in result.warnings))

    def test_mana_curve_calculation(self):
        """Test mana curve calculation in CardCollection."""
        deck = CardCollection()
        
        # Add cards with known mana costs
        deck.add_card(self.create_test_card("One Drop", "Creature", "{1}"))
        deck.add_card(self.create_test_card("Two Drop", "Creature", "{2}"))  
        deck.add_card(self.create_test_card("Three Drop", "Creature", "{1}{R}{R}"))
        deck.add_card(self.create_test_card("Land", "Basic Land", ""))
        
        curve = deck.get_mana_curve()
        
        self.assertEqual(curve[1], 1)  # One 1-drop
        self.assertEqual(curve[2], 1)  # One 2-drop  
        self.assertEqual(curve[3], 1)  # One 3-drop
        self.assertNotIn(0, curve)     # Land shouldn't count


if __name__ == '__main__':
    unittest.main()