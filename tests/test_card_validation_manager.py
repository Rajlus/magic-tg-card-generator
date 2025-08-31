#!/usr/bin/env python3
"""
Comprehensive test suite for CardValidationManager.

This test suite verifies all functionality of the CardValidationManager class including:
- validate_card_data() - comprehensive card data validation
- check_card_format() - format-specific card legality checks
- validate_mana_cost() - mana cost format and content validation
- validate_card_type() - card type line validation
- validate_power_toughness() - power/toughness validation for creatures
- check_card_rules() - fundamental Magic rules compliance
- validate_card_text() - card text content and formatting
- enforce_format_constraints() - format-specific deck constraints

The tests use extensive mocking to isolate the manager from dependencies and ensure
comprehensive coverage of all validation scenarios including edge cases and error conditions.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, Mock, patch

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from managers.card_validation_manager import CardValidationManager


class MockCard:
    """Mock MTG card for testing validation functionality."""

    def __init__(
        self,
        id=1,
        name="Test Card",
        type="Creature — Human",
        cost="2G",
        power=2,
        toughness=2,
        text="Test card text",
        rarity="common",
        art="Test art description",
        status="pending",
    ):
        self.id = id
        self.name = name
        self.type = type
        self.cost = cost
        self.power = power
        self.toughness = toughness
        self.text = text
        self.rarity = rarity
        self.art = art
        self.status = status
        self.image_path = None


class MockLogger:
    """Mock logger for testing."""

    def __init__(self):
        self.messages = []

    def log_message(self, level: str, message: str) -> None:
        self.messages.append((level, message))

    def get_messages_by_level(self, level: str) -> list[str]:
        return [msg for lvl, msg in self.messages if lvl == level]


class TestCardValidationManager(unittest.TestCase):
    """Test suite for CardValidationManager."""

    def setUp(self):
        """Set up test fixtures."""
        self.logger = MockLogger()
        self.test_cards = [
            MockCard(
                1,
                "Lightning Commander",
                "Legendary Creature — Dragon",
                "2RR",
                4,
                4,
                "Flying, haste",
            ),
            MockCard(
                2,
                "Lightning Bolt",
                "Instant",
                "R",
                None,
                None,
                "Deal 3 damage to any target",
            ),
            MockCard(3, "Grizzly Bears", "Creature — Bear", "1G", 2, 2, ""),
            MockCard(
                4,
                "Black Lotus",
                "Artifact",
                "0",
                None,
                None,
                "Add three mana of any one color",
            ),
            MockCard(
                5, "Mountain", "Basic Land — Mountain", "", None, None, "Tap: Add R"
            ),
        ]

        self.manager = CardValidationManager(self.test_cards, self.logger)

    # Tests for Initialization and Setup

    def test_manager_initialization(self):
        """Test that CardValidationManager initializes correctly."""
        self.assertIsInstance(self.manager, CardValidationManager)
        self.assertEqual(self.manager.cards, self.test_cards)
        self.assertEqual(self.manager.logger, self.logger)
        self.assertIsInstance(self.manager.commander_colors, set)

    def test_initialization_without_cards(self):
        """Test manager initialization without cards."""
        manager = CardValidationManager(logger=self.logger)
        self.assertEqual(manager.cards, [])
        self.assertEqual(manager.logger, self.logger)
        self.assertEqual(manager.commander_colors, set())

    def test_initialization_without_logger(self):
        """Test manager initialization without logger."""
        manager = CardValidationManager(self.test_cards)
        self.assertEqual(manager.cards, self.test_cards)
        self.assertIsNone(manager.logger)

    def test_update_cards(self):
        """Test updating cards list."""
        new_cards = [MockCard(6, "Test Update", "Instant", "U")]
        self.manager.update_cards(new_cards)
        self.assertEqual(self.manager.cards, new_cards)

    # Tests for validate_card_data()

    def test_validate_card_data_valid_creature(self):
        """Test validate_card_data with a valid creature card."""
        valid_creature = MockCard(
            1, "Valid Creature", "Creature — Human Wizard", "2U", 2, 3, "Flying."
        )
        is_valid, errors = self.manager.validate_card_data(valid_creature)

        # Print errors for debugging if test fails
        if not is_valid:
            print(f"Validation errors: {errors}")

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_card_data_valid_instant(self):
        """Test validate_card_data with a valid instant card."""
        valid_instant = MockCard(
            2,
            "Valid Instant",
            "Instant",
            "1R",
            None,
            None,
            "Deal 2 damage to any target.",
        )
        is_valid, errors = self.manager.validate_card_data(valid_instant)

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_card_data_missing_name(self):
        """Test validate_card_data with missing card name."""
        invalid_card = MockCard(1, "", "Creature — Human", "1G", 1, 1, "Test")
        is_valid, errors = self.manager.validate_card_data(invalid_card)

        self.assertFalse(is_valid)
        self.assertIn("Card name is required and cannot be empty", errors)

    def test_validate_card_data_name_too_long(self):
        """Test validate_card_data with overly long card name."""
        long_name = "A" * 201  # Exceeds 200 character limit
        invalid_card = MockCard(1, long_name, "Creature — Human", "1G", 1, 1, "Test")
        is_valid, errors = self.manager.validate_card_data(invalid_card)

        self.assertFalse(is_valid)
        self.assertIn("Card name cannot exceed 200 characters", errors)

    def test_validate_card_data_missing_type(self):
        """Test validate_card_data with missing card type."""
        invalid_card = MockCard(1, "Test Card", "", "1G", 1, 1, "Test")
        is_valid, errors = self.manager.validate_card_data(invalid_card)

        self.assertFalse(is_valid)
        self.assertIn("Card type is required and cannot be empty", errors)

    def test_validate_card_data_creature_missing_power_toughness(self):
        """Test validate_card_data with creature missing power/toughness."""
        invalid_creature = MockCard(
            1, "Invalid Creature", "Creature — Beast", "2G", None, None, "Test"
        )
        is_valid, errors = self.manager.validate_card_data(invalid_creature)

        self.assertFalse(is_valid)
        self.assertIn("Creature cards must have power defined", errors)
        self.assertIn("Creature cards must have toughness defined", errors)

    def test_validate_card_data_invalid_mana_cost(self):
        """Test validate_card_data with invalid mana cost."""
        invalid_card = MockCard(
            1, "Test Card", "Instant", "INVALID", None, None, "Test"
        )
        is_valid, errors = self.manager.validate_card_data(invalid_card)

        self.assertFalse(is_valid)
        self.assertTrue(
            any("Mana cost contains invalid characters" in error for error in errors)
        )

    def test_validate_card_data_no_card_object(self):
        """Test validate_card_data with None card object."""
        # Should handle None gracefully and return validation errors
        is_valid, errors = self.manager.validate_card_data(None)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

    # Tests for check_card_format()

    def test_check_card_format_legal_commander(self):
        """Test check_card_format with legal commander card."""
        legal_card = MockCard(1, "Lightning Bolt", "Instant", "R")
        # Set commander colors to include red so card is legal
        self.manager.set_commander_colors({"R"})
        is_legal, issues = self.manager.check_card_format(legal_card, "commander")

        self.assertTrue(is_legal)
        self.assertEqual(len(issues), 0)

    def test_check_card_format_banned_commander(self):
        """Test check_card_format with banned commander card."""
        banned_card = MockCard(1, "Black Lotus", "Artifact", "0")
        is_legal, issues = self.manager.check_card_format(banned_card, "commander")

        self.assertFalse(is_legal)
        self.assertIn("Card 'Black Lotus' is banned in commander format", issues)

    def test_check_card_format_legal_standard(self):
        """Test check_card_format with legal standard card."""
        legal_card = MockCard(1, "Grizzly Bears", "Creature — Bear", "1G", 2, 2)
        is_legal, issues = self.manager.check_card_format(legal_card, "standard")

        self.assertTrue(is_legal)
        self.assertEqual(len(issues), 0)

    def test_check_card_format_banned_standard(self):
        """Test check_card_format with banned standard card."""
        banned_card = MockCard(1, "Lightning Bolt", "Instant", "R")
        is_legal, issues = self.manager.check_card_format(banned_card, "standard")

        self.assertFalse(is_legal)
        self.assertIn("Card 'Lightning Bolt' is banned in standard format", issues)

    def test_check_card_format_legal_modern(self):
        """Test check_card_format with legal modern card."""
        legal_card = MockCard(1, "Lightning Bolt", "Instant", "R")
        is_legal, issues = self.manager.check_card_format(legal_card, "modern")

        self.assertTrue(is_legal)
        self.assertEqual(len(issues), 0)

    def test_check_card_format_banned_modern(self):
        """Test check_card_format with banned modern card."""
        banned_card = MockCard(1, "Mental Misstep", "Instant", "UP")  # Phyrexian mana
        is_legal, issues = self.manager.check_card_format(banned_card, "modern")

        self.assertFalse(is_legal)
        self.assertIn("Card 'Mental Misstep' is banned in modern format", issues)

    def test_check_card_format_no_name(self):
        """Test check_card_format with card lacking name."""
        nameless_card = MockCard(1, "", "Instant", "R")
        is_legal, issues = self.manager.check_card_format(nameless_card, "commander")

        self.assertFalse(is_legal)
        self.assertIn("Cannot check format legality - card has no name", issues)

    def test_check_card_format_color_identity_violation(self):
        """Test check_card_format with commander color identity violation."""
        self.manager.set_commander_colors({"R"})  # Red commander
        blue_card = MockCard(1, "Counterspell", "Instant", "UU")
        is_legal, issues = self.manager.check_card_format(blue_card, "commander")

        self.assertFalse(is_legal)
        self.assertIn("Card 'Counterspell' violates commander color identity", issues)

    # Tests for validate_mana_cost()

    def test_validate_mana_cost_empty_cost(self):
        """Test validate_mana_cost with empty cost."""
        is_valid, errors = self.manager.validate_mana_cost("")
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_mana_cost_none_cost(self):
        """Test validate_mana_cost with None cost."""
        is_valid, errors = self.manager.validate_mana_cost(None)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_mana_cost_simple_numeric(self):
        """Test validate_mana_cost with simple numeric cost."""
        is_valid, errors = self.manager.validate_mana_cost("3")
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_mana_cost_single_color(self):
        """Test validate_mana_cost with single colored mana."""
        is_valid, errors = self.manager.validate_mana_cost("R")
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_mana_cost_mixed_cost(self):
        """Test validate_mana_cost with mixed numeric and colored mana."""
        is_valid, errors = self.manager.validate_mana_cost("2RR")
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_mana_cost_bracketed_format(self):
        """Test validate_mana_cost with bracketed mana symbols."""
        is_valid, errors = self.manager.validate_mana_cost("{2}{R}{R}")
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_mana_cost_hybrid_mana(self):
        """Test validate_mana_cost with hybrid mana symbols."""
        is_valid, errors = self.manager.validate_mana_cost("{R/G}")
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_mana_cost_variable_x(self):
        """Test validate_mana_cost with X variable cost."""
        is_valid, errors = self.manager.validate_mana_cost("XRR")
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_mana_cost_colorless_c(self):
        """Test validate_mana_cost with colorless C mana."""
        is_valid, errors = self.manager.validate_mana_cost("{C}{C}")
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_mana_cost_invalid_characters(self):
        """Test validate_mana_cost with invalid characters."""
        is_valid, errors = self.manager.validate_mana_cost("2RP!")  # ! is invalid
        self.assertFalse(is_valid)
        self.assertTrue(
            any("Mana cost contains invalid characters" in error for error in errors)
        )

    def test_validate_mana_cost_unbalanced_braces(self):
        """Test validate_mana_cost with unbalanced braces."""
        is_valid, errors = self.manager.validate_mana_cost("{2{R}")
        self.assertFalse(is_valid)
        self.assertIn("Mana cost has unbalanced braces", errors)

    def test_validate_mana_cost_high_numeric(self):
        """Test validate_mana_cost with high numeric values."""
        is_valid, errors = self.manager.validate_mana_cost("15")
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    # Tests for validate_card_type()

    def test_validate_card_type_valid_creature(self):
        """Test validate_card_type with valid creature type."""
        creature_card = MockCard(1, "Test", "Creature — Human Wizard", "1U")
        is_valid, errors = self.manager.validate_card_type(creature_card)

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_card_type_valid_instant(self):
        """Test validate_card_type with valid instant type."""
        instant_card = MockCard(1, "Test", "Instant", "1R")
        is_valid, errors = self.manager.validate_card_type(instant_card)

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_card_type_valid_legendary(self):
        """Test validate_card_type with valid legendary supertype."""
        legendary_card = MockCard(1, "Test", "Legendary Creature — Dragon", "3RR")
        is_valid, errors = self.manager.validate_card_type(legendary_card)

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_card_type_valid_planeswalker(self):
        """Test validate_card_type with valid planeswalker type."""
        walker_card = MockCard(1, "Test", "Planeswalker — Jace", "2UU")
        is_valid, errors = self.manager.validate_card_type(walker_card)

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_card_type_missing_type(self):
        """Test validate_card_type with missing type."""
        no_type_card = MockCard(1, "Test", "", "1G")
        is_valid, errors = self.manager.validate_card_type(no_type_card)

        self.assertFalse(is_valid)
        self.assertIn("Card type is required", errors)

    def test_validate_card_type_invalid_type(self):
        """Test validate_card_type with invalid card type."""
        invalid_card = MockCard(1, "Test", "InvalidType", "1G")
        is_valid, errors = self.manager.validate_card_type(invalid_card)

        self.assertFalse(is_valid)
        self.assertTrue(
            any(
                "Card type must include at least one valid type" in error
                for error in errors
            )
        )

    def test_validate_card_type_creature_no_subtypes(self):
        """Test validate_card_type with creature lacking subtypes."""
        creature_card = MockCard(1, "Test", "Creature", "1G")
        is_valid, errors = self.manager.validate_card_type(creature_card)

        self.assertFalse(is_valid)
        self.assertIn(
            "Creature cards should have subtypes (e.g., 'Creature — Human Wizard')",
            errors,
        )

    def test_validate_card_type_planeswalker_no_subtypes(self):
        """Test validate_card_type with planeswalker lacking subtypes."""
        walker_card = MockCard(1, "Test", "Planeswalker", "3UU")
        is_valid, errors = self.manager.validate_card_type(walker_card)

        self.assertFalse(is_valid)
        self.assertIn(
            "Planeswalker cards should have subtypes (e.g., 'Planeswalker — Jace')",
            errors,
        )

    def test_validate_card_type_artifact_creature(self):
        """Test validate_card_type with artifact creature type."""
        artifact_creature = MockCard(1, "Test", "Artifact Creature — Construct", "3")
        is_valid, errors = self.manager.validate_card_type(artifact_creature)

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    # Tests for validate_power_toughness()

    def test_validate_power_toughness_valid_creature(self):
        """Test validate_power_toughness with valid creature stats."""
        creature = MockCard(1, "Test", "Creature — Human", "1G", 2, 2)
        is_valid, errors = self.manager.validate_power_toughness(creature)

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_power_toughness_non_creature(self):
        """Test validate_power_toughness with non-creature card."""
        instant = MockCard(1, "Test", "Instant", "1R", None, None)
        is_valid, errors = self.manager.validate_power_toughness(instant)

        self.assertTrue(is_valid)  # Should pass as it's not a creature
        self.assertEqual(len(errors), 0)

    def test_validate_power_toughness_missing_power(self):
        """Test validate_power_toughness with missing power."""
        creature = MockCard(1, "Test", "Creature — Human", "1G", None, 2)
        is_valid, errors = self.manager.validate_power_toughness(creature)

        self.assertFalse(is_valid)
        self.assertIn("Creature cards must have power defined", errors)

    def test_validate_power_toughness_missing_toughness(self):
        """Test validate_power_toughness with missing toughness."""
        creature = MockCard(1, "Test", "Creature — Human", "1G", 2, None)
        is_valid, errors = self.manager.validate_power_toughness(creature)

        self.assertFalse(is_valid)
        self.assertIn("Creature cards must have toughness defined", errors)

    def test_validate_power_toughness_zero_stats(self):
        """Test validate_power_toughness with zero power/toughness."""
        creature = MockCard(1, "Test", "Creature — Plant Wall", "1G", 0, 3)
        is_valid, errors = self.manager.validate_power_toughness(creature)

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_power_toughness_high_stats(self):
        """Test validate_power_toughness with high power/toughness values."""
        creature = MockCard(1, "Test", "Creature — Dragon", "8RR", 15, 15)
        is_valid, errors = self.manager.validate_power_toughness(creature)

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_power_toughness_star_power(self):
        """Test validate_power_toughness with * power/toughness."""
        creature = MockCard(1, "Test", "Creature — Avatar", "3G", "*", "*")
        is_valid, errors = self.manager.validate_power_toughness(creature)

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_power_toughness_x_power(self):
        """Test validate_power_toughness with X power/toughness."""
        creature = MockCard(1, "Test", "Creature — Hydra", "XG", "X", "X")
        is_valid, errors = self.manager.validate_power_toughness(creature)

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_power_toughness_negative_power(self):
        """Test validate_power_toughness with negative power."""
        creature = MockCard(1, "Test", "Creature — Spirit", "1B", -1, 1)
        is_valid, errors = self.manager.validate_power_toughness(creature)

        self.assertFalse(is_valid)
        self.assertTrue(any("Power cannot be negative" in error for error in errors))

    def test_validate_power_toughness_invalid_characters(self):
        """Test validate_power_toughness with invalid P/T characters."""
        creature = MockCard(1, "Test", "Creature — Weird", "2U", "2@", "2")
        is_valid, errors = self.manager.validate_power_toughness(creature)

        self.assertFalse(is_valid)
        self.assertTrue(any("Invalid power value" in error for error in errors))

    # Tests for check_card_rules()

    def test_check_card_rules_valid_creature(self):
        """Test check_card_rules with valid creature."""
        creature = MockCard(1, "Test", "Creature — Human", "1G", 2, 2, "Trample")
        follows_rules, violations = self.manager.check_card_rules(creature)

        self.assertTrue(follows_rules)
        self.assertEqual(len(violations), 0)

    def test_check_card_rules_valid_instant(self):
        """Test check_card_rules with valid instant."""
        instant = MockCard(1, "Test", "Instant", "1R", None, None, "Deal 3 damage")
        follows_rules, violations = self.manager.check_card_rules(instant)

        self.assertTrue(follows_rules)
        self.assertEqual(len(violations), 0)

    def test_check_card_rules_basic_land_with_cost(self):
        """Test check_card_rules with basic land having mana cost."""
        land = MockCard(1, "Test", "Basic Land — Plains", "1", None, None, "Tap: Add W")
        follows_rules, violations = self.manager.check_card_rules(land)

        self.assertFalse(follows_rules)
        self.assertIn("Basic lands should not have mana costs", violations)

    def test_check_card_rules_instant_with_power(self):
        """Test check_card_rules with instant having power/toughness."""
        instant = MockCard(1, "Test", "Instant", "1R", 2, 2, "Deal 3 damage")
        follows_rules, violations = self.manager.check_card_rules(instant)

        self.assertFalse(follows_rules)
        self.assertIn(
            "Instant and Sorcery cards cannot have power/toughness", violations
        )

    def test_check_card_rules_sorcery_with_toughness(self):
        """Test check_card_rules with sorcery having toughness."""
        sorcery = MockCard(
            1, "Test", "Sorcery", "2B", None, 1, "Destroy target creature"
        )
        follows_rules, violations = self.manager.check_card_rules(sorcery)

        self.assertFalse(follows_rules)
        self.assertIn(
            "Instant and Sorcery cards cannot have power/toughness", violations
        )

    def test_check_card_rules_planeswalker_without_abilities(self):
        """Test check_card_rules with planeswalker lacking loyalty abilities."""
        walker = MockCard(
            1, "Test", "Planeswalker — Jace", "3UU", None, None, "Draw cards"
        )
        follows_rules, violations = self.manager.check_card_rules(walker)

        self.assertFalse(follows_rules)
        self.assertIn(
            "Planeswalker cards should have loyalty abilities (+ or - abilities)",
            violations,
        )

    def test_check_card_rules_planeswalker_with_abilities(self):
        """Test check_card_rules with planeswalker having loyalty abilities."""
        walker = MockCard(
            1,
            "Test",
            "Planeswalker — Jace",
            "3UU",
            None,
            None,
            "+1: Draw a card.\n-2: Bounce target creature.",
        )
        follows_rules, violations = self.manager.check_card_rules(walker)

        self.assertTrue(follows_rules)
        self.assertEqual(len(violations), 0)

    def test_check_card_rules_nonbasic_land_with_cost(self):
        """Test check_card_rules with non-basic land having mana cost (should be okay)."""
        land = MockCard(
            1, "Test", "Land", "2", None, None, "Enters tapped. Tap: Add any color"
        )
        follows_rules, violations = self.manager.check_card_rules(land)

        self.assertTrue(follows_rules)
        self.assertEqual(len(violations), 0)

    # Tests for validate_card_text()

    def test_validate_card_text_empty_text(self):
        """Test validate_card_text with empty text."""
        is_valid, errors = self.manager.validate_card_text("")

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_card_text_none_text(self):
        """Test validate_card_text with None text."""
        is_valid, errors = self.manager.validate_card_text(None)

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_card_text_simple_text(self):
        """Test validate_card_text with simple ability text."""
        is_valid, errors = self.manager.validate_card_text("Flying, trample.")

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_card_text_multiple_abilities(self):
        """Test validate_card_text with multiple abilities."""
        text = "Flying.\nWhen this creature enters, draw a card."
        is_valid, errors = self.manager.validate_card_text(text)

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_card_text_activated_ability(self):
        """Test validate_card_text with activated ability."""
        text = "{T}: Add one mana of any color."
        is_valid, errors = self.manager.validate_card_text(text)

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_card_text_too_long(self):
        """Test validate_card_text with overly long text."""
        long_text = "A" * 2001  # Exceeds 2000 character limit
        is_valid, errors = self.manager.validate_card_text(long_text)

        self.assertFalse(is_valid)
        self.assertIn("Card text is too long (maximum 2000 characters)", errors)

    def test_validate_card_text_unbalanced_parentheses(self):
        """Test validate_card_text with unbalanced parentheses."""
        is_valid, errors = self.manager.validate_card_text(
            "Flying (this creature can't be blocked."
        )

        self.assertFalse(is_valid)
        self.assertIn("Card text has unbalanced parentheses", errors)

    def test_validate_card_text_unbalanced_brackets(self):
        """Test validate_card_text with unbalanced brackets."""
        is_valid, errors = self.manager.validate_card_text(
            "Reminder text [this is incomplete"
        )

        self.assertFalse(is_valid)
        self.assertIn("Card text has unbalanced brackets", errors)

    def test_validate_card_text_missing_period(self):
        """Test validate_card_text with ability missing proper punctuation."""
        is_valid, errors = self.manager.validate_card_text("Flying, trample")

        self.assertFalse(is_valid)
        self.assertTrue(
            any(
                "Ability text should end with proper punctuation" in error
                for error in errors
            )
        )

    def test_validate_card_text_flavor_text(self):
        """Test validate_card_text with flavor text in quotes."""
        text = 'Flying.\n"The sky is my domain." —Jace'
        is_valid, errors = self.manager.validate_card_text(text)

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_card_text_reminder_text(self):
        """Test validate_card_text with reminder text in parentheses."""
        text = "Flying (This creature can't be blocked except by creatures with flying or reach.)"
        is_valid, errors = self.manager.validate_card_text(text)

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    # Tests for enforce_format_constraints()

    def test_enforce_format_constraints_commander_valid(self):
        """Test enforce_format_constraints with valid Commander deck."""
        # Create 100 cards including a commander
        commander_cards = [
            MockCard(1, "Commander", "Legendary Creature — Dragon", "3RR", 5, 5)
        ]
        commander_cards.extend(
            [MockCard(i + 2, f"Card {i}", "Instant", "R") for i in range(99)]
        )

        is_legal, violations, stats = self.manager.enforce_format_constraints(
            commander_cards, "commander"
        )

        self.assertTrue(is_legal)
        self.assertEqual(len(violations), 0)
        self.assertEqual(stats["total_cards"], 100)
        self.assertEqual(stats["format"], "commander")

    def test_enforce_format_constraints_commander_wrong_count(self):
        """Test enforce_format_constraints with wrong card count for Commander."""
        # Only 50 cards
        few_cards = [MockCard(i, f"Card {i}", "Instant", "R") for i in range(50)]

        is_legal, violations, stats = self.manager.enforce_format_constraints(
            few_cards, "commander"
        )

        self.assertFalse(is_legal)
        self.assertIn(
            "Commander decks must have exactly 100 cards (found 50)", violations
        )

    def test_enforce_format_constraints_commander_no_commander(self):
        """Test enforce_format_constraints with no commander in deck."""
        # 100 cards but no legendary creature
        no_commander_cards = [
            MockCard(i, f"Card {i}", "Instant", "R") for i in range(100)
        ]

        is_legal, violations, stats = self.manager.enforce_format_constraints(
            no_commander_cards, "commander"
        )

        self.assertFalse(is_legal)
        self.assertIn(
            "Commander deck must have a legendary creature or planeswalker as commander",
            violations,
        )

    def test_enforce_format_constraints_commander_multiple_commanders(self):
        """Test enforce_format_constraints with multiple commanders."""
        # 2 legendary creatures + 98 other cards
        multi_commander_cards = [
            MockCard(1, "Commander 1", "Legendary Creature — Dragon", "3RR", 5, 5),
            MockCard(2, "Commander 2", "Legendary Creature — Angel", "3WW", 4, 4),
        ]
        multi_commander_cards.extend(
            [MockCard(i + 3, f"Card {i}", "Instant", "R") for i in range(98)]
        )

        is_legal, violations, stats = self.manager.enforce_format_constraints(
            multi_commander_cards, "commander"
        )

        self.assertFalse(is_legal)
        self.assertIn("Commander deck can only have one commander", violations)

    def test_enforce_format_constraints_commander_duplicate_cards(self):
        """Test enforce_format_constraints with duplicate non-basic cards."""
        commander_cards = [
            MockCard(1, "Commander", "Legendary Creature — Dragon", "3RR", 5, 5)
        ]
        # Add duplicates of non-basic cards
        commander_cards.extend(
            [MockCard(i + 2, "Lightning Bolt", "Instant", "R") for i in range(2)]
        )  # 2 Lightning Bolts
        commander_cards.extend(
            [MockCard(i + 4, f"Card {i}", "Instant", "R") for i in range(97)]
        )

        is_legal, violations, stats = self.manager.enforce_format_constraints(
            commander_cards, "commander"
        )

        self.assertFalse(is_legal)
        self.assertIn(
            "Commander allows only one copy of 'Lightning Bolt' (found 2)", violations
        )

    def test_enforce_format_constraints_standard_valid(self):
        """Test enforce_format_constraints with valid Standard deck."""
        # 60 cards with 4-of rule
        standard_cards = []
        for i in range(15):  # 15 different cards with 4 copies each
            standard_cards.extend(
                [MockCard(j, f"Card {i}", "Instant", "R") for j in range(4)]
            )

        is_legal, violations, stats = self.manager.enforce_format_constraints(
            standard_cards, "standard"
        )

        self.assertTrue(is_legal)
        self.assertEqual(len(violations), 0)
        self.assertEqual(stats["total_cards"], 60)

    def test_enforce_format_constraints_standard_too_few_cards(self):
        """Test enforce_format_constraints with too few cards for Standard."""
        few_cards = [MockCard(i, f"Card {i}", "Instant", "R") for i in range(30)]

        is_legal, violations, stats = self.manager.enforce_format_constraints(
            few_cards, "standard"
        )

        self.assertFalse(is_legal)
        self.assertIn(
            "Standard decks must have at least 60 cards (found 30)", violations
        )

    def test_enforce_format_constraints_standard_too_many_copies(self):
        """Test enforce_format_constraints with too many copies in Standard."""
        # 5 copies of the same card
        standard_cards = [
            MockCard(i, "Lightning Bolt", "Instant", "R") for i in range(5)
        ]
        standard_cards.extend(
            [MockCard(i + 5, f"Card {i}", "Instant", "R") for i in range(55)]
        )

        is_legal, violations, stats = self.manager.enforce_format_constraints(
            standard_cards, "standard"
        )

        self.assertFalse(is_legal)
        self.assertIn(
            "Standard allows maximum 4 copies of 'Lightning Bolt' (found 5)", violations
        )

    def test_enforce_format_constraints_modern_valid(self):
        """Test enforce_format_constraints with valid Modern deck."""
        # 60 cards following Modern rules (same as Standard for deck construction)
        modern_cards = []
        for i in range(15):
            modern_cards.extend(
                [MockCard(j, f"Card {i}", "Instant", "R") for j in range(4)]
            )

        is_legal, violations, stats = self.manager.enforce_format_constraints(
            modern_cards, "modern"
        )

        self.assertTrue(is_legal)
        self.assertEqual(len(violations), 0)
        self.assertEqual(stats["total_cards"], 60)

    def test_enforce_format_constraints_basic_lands_allowed(self):
        """Test enforce_format_constraints allows multiple basic lands."""
        commander_cards = [
            MockCard(1, "Commander", "Legendary Creature — Dragon", "3RR", 5, 5)
        ]
        # Add 20 mountains (should be allowed)
        commander_cards.extend(
            [
                MockCard(i + 2, "Mountain", "Basic Land — Mountain", "")
                for i in range(20)
            ]
        )
        commander_cards.extend(
            [MockCard(i + 22, f"Card {i}", "Instant", "R") for i in range(79)]
        )

        is_legal, violations, stats = self.manager.enforce_format_constraints(
            commander_cards, "commander"
        )

        self.assertTrue(is_legal)
        self.assertEqual(len(violations), 0)

    def test_enforce_format_constraints_unknown_format(self):
        """Test enforce_format_constraints with unknown format."""
        cards = [MockCard(1, "Test", "Instant", "R")]
        is_legal, violations, stats = self.manager.enforce_format_constraints(
            cards, "unknown_format"
        )

        self.assertFalse(is_legal)
        self.assertIn("Unknown format: unknown_format", violations)

    # Tests for Color Identity and Commander Colors

    def test_get_commander_colors_legendary_creature(self):
        """Test get_commander_colors with legendary creature."""
        commander_cards = [
            MockCard(1, "Test Commander", "Legendary Creature — Dragon", "2RG", 4, 4)
        ]
        manager = CardValidationManager(commander_cards, self.logger)
        colors = manager.get_commander_colors()

        self.assertEqual(colors, {"R", "G"})

    def test_get_commander_colors_first_card(self):
        """Test get_commander_colors treats first card as commander."""
        cards = [MockCard(1, "Commander", "Creature — Human", "WU", 1, 1)]
        manager = CardValidationManager(cards, self.logger)
        colors = manager.get_commander_colors()

        self.assertEqual(colors, {"W", "U"})

    def test_get_commander_colors_colorless(self):
        """Test get_commander_colors with colorless commander."""
        cards = [
            MockCard(1, "Commander", "Legendary Artifact Creature — Golem", "5", 5, 5)
        ]
        manager = CardValidationManager(cards, self.logger)
        colors = manager.get_commander_colors()

        self.assertEqual(colors, set())

    def test_set_commander_colors_manual(self):
        """Test manually setting commander colors."""
        self.manager.set_commander_colors({"U", "B"})
        self.assertEqual(self.manager.commander_colors, {"U", "B"})

    def test_get_card_colors_simple(self):
        """Test get_card_colors with simple mana cost."""
        colors = self.manager.get_card_colors("2RG")
        self.assertEqual(colors, {"R", "G"})

    def test_get_card_colors_bracketed(self):
        """Test get_card_colors with bracketed mana cost."""
        colors = self.manager.get_card_colors("{2}{W}{U}")
        self.assertEqual(colors, {"W", "U"})

    def test_get_card_colors_colorless(self):
        """Test get_card_colors with colorless cost."""
        colors = self.manager.get_card_colors("5")
        self.assertEqual(colors, set())

    def test_get_card_colors_empty(self):
        """Test get_card_colors with empty cost."""
        colors = self.manager.get_card_colors("")
        self.assertEqual(colors, set())

    def test_check_color_violation_no_violation(self):
        """Test check_color_violation with legal card."""
        self.manager.set_commander_colors({"R", "G"})
        violation = self.manager.check_color_violation("2R")

        self.assertFalse(violation)

    def test_check_color_violation_with_violation(self):
        """Test check_color_violation with illegal card."""
        self.manager.set_commander_colors({"R"})
        violation = self.manager.check_color_violation("1U")

        self.assertTrue(violation)

    def test_check_color_violation_colorless_allowed(self):
        """Test check_color_violation allows colorless cards."""
        self.manager.set_commander_colors({"R"})
        violation = self.manager.check_color_violation("3")

        self.assertFalse(violation)

    # Tests for Deck Validation

    def test_validate_deck_comprehensive(self):
        """Test comprehensive deck validation."""
        self.manager.set_commander_colors({"R"})
        result = self.manager.validate_deck()

        self.assertIn("commander_colors", result)
        self.assertIn("total_cards", result)
        self.assertIn("violations", result)
        self.assertIn("valid_cards", result)
        self.assertIn("has_violations", result)
        self.assertEqual(result["total_cards"], len(self.test_cards))

    def test_validate_deck_with_violations(self):
        """Test validate_deck with color violations."""
        self.manager.set_commander_colors({"R"})  # Only red allowed
        result = self.manager.validate_deck()

        self.assertTrue(result["has_violations"])
        self.assertGreater(len(result["violations"]), 0)

        # Check that Grizzly Bears (1G) is flagged as violation
        violation_names = [v["name"] for v in result["violations"]]
        self.assertIn("Grizzly Bears", violation_names)

    def test_log_color_violations(self):
        """Test logging of color violations."""
        self.manager.set_commander_colors({"R"})
        self.manager.log_color_violations()

        warning_messages = self.logger.get_messages_by_level("WARNING")
        self.assertTrue(any("color violations" in msg for msg in warning_messages))

    # Edge Cases and Error Handling Tests

    def test_edge_case_card_without_attributes(self):
        """Test handling card objects missing expected attributes."""

        class IncompleteCard:
            name = "Test"
            # Missing other attributes

        incomplete_card = IncompleteCard()

        # Should not crash, but will report validation errors
        is_valid, errors = self.manager.validate_card_data(incomplete_card)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

    def test_edge_case_none_values(self):
        """Test handling of None values in card attributes."""
        none_card = MockCard(1, None, None, None, None, None, None)

        is_valid, errors = self.manager.validate_card_data(none_card)
        self.assertFalse(is_valid)
        self.assertIn("Card name is required and cannot be empty", errors)
        self.assertIn("Card type is required and cannot be empty", errors)

    def test_edge_case_numeric_cost_conversion(self):
        """Test handling of numeric mana costs."""
        numeric_cost_card = MockCard(
            1, "Test", "Instant", 3
        )  # Integer instead of string
        is_valid, errors = self.manager.validate_card_data(numeric_cost_card)

        # Should handle conversion internally - check that cost validation doesn't fail
        # The validation might fail on type validation but not on cost conversion
        self.assertTrue(
            len(errors) == 0
            or not any(
                "Mana cost contains invalid characters" in error for error in errors
            )
        )

    def test_edge_case_whitespace_handling(self):
        """Test handling of whitespace in card attributes."""
        whitespace_card = MockCard(1, "  Test  ", "  Instant  ", "  1R  ")
        is_valid, errors = self.manager.validate_card_data(whitespace_card)

        # Should handle whitespace trimming - at minimum, should not crash
        # May have validation errors but should handle the whitespace gracefully
        self.assertTrue(
            len(errors) == 0
            or not any("Card name is required" in error for error in errors)
        )

    def test_manager_without_logger_no_crash(self):
        """Test that manager methods work without logger."""
        no_logger_manager = CardValidationManager(self.test_cards)

        # Should not crash when trying to log
        no_logger_manager.log_color_violations()
        colors = no_logger_manager.get_commander_colors()

        # Should work normally
        self.assertIsInstance(colors, set)


if __name__ == "__main__":
    # Set up test discovery and execution
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test class
    suite.addTests(loader.loadTestsFromTestCase(TestCardValidationManager))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
