"""Functional tests for Models - testing actual model behavior and validation."""

import json
from datetime import datetime

import pytest
from magic_tg_card_generator.models import Card, CardType, Color


class TestModelsFunctionality:
    """Test that models actually work as documented."""

    def test_card_validates_creature_requirements(self):
        """Test that creatures must have power and toughness."""
        # Valid creature
        creature = Card(
            name="Dragon",
            card_type=CardType.CREATURE,
            mana_cost="5",
            color=Color.RED,
            power=5,
            toughness=5,
        )
        assert creature.power == 5
        assert creature.toughness == 5

        # Creature without power/toughness should fail validation
        with pytest.raises(ValueError):
            Card(
                name="Invalid Creature",
                card_type=CardType.CREATURE,
                mana_cost="3",
                color=Color.RED,
                power=None,  # Missing power
                toughness=3,
            )

    def test_card_non_creatures_cannot_have_power_toughness(self):
        """Test that non-creatures cannot have power/toughness."""
        # This should work - instant without power/toughness
        instant = Card(
            name="Lightning Bolt",
            card_type=CardType.INSTANT,
            mana_cost="R",
            color=Color.RED,
            text="Deal 3 damage",
        )
        assert instant.power is None
        assert instant.toughness is None

        # Non-creature with power/toughness should be rejected
        with pytest.raises(ValueError):
            Card(
                name="Invalid Instant",
                card_type=CardType.INSTANT,
                mana_cost="R",
                color=Color.RED,
                power=3,  # Instants can't have power!
                toughness=3,
            )

    def test_card_calculates_converted_mana_cost(self):
        """Test that CMC is calculated correctly."""
        test_cases = [
            ("3", 3),
            ("2R", 3),
            ("1UU", 3),
            ("WUBRG", 5),
            ("3RR", 5),
            ("X", 0),
            ("XXR", 1),
            ("", 0),
        ]

        for mana_cost, expected_cmc in test_cases:
            card = Card(
                name=f"Test {mana_cost}",
                card_type=CardType.INSTANT,
                mana_cost=mana_cost,
                color=Color.COLORLESS,
            )
            assert card.converted_mana_cost == expected_cmc

    def test_card_serialization_preserves_all_data(self):
        """Test that cards can be serialized and deserialized without data loss."""
        original = Card(
            name="Complex Card",
            card_type=CardType.CREATURE,
            mana_cost="3WW",
            color=Color.WHITE,
            power=4,
            toughness=5,
            text="Flying, vigilance",
            flavor_text="A majestic being",
            rarity="Rare",
        )

        # Serialize to dict
        card_dict = original.to_dict()

        # Verify all fields are present
        assert card_dict["name"] == "Complex Card"
        assert card_dict["card_type"] == "Creature"
        assert card_dict["mana_cost"] == "3WW"
        assert card_dict["color"] == "White"
        assert card_dict["power"] == 4
        assert card_dict["toughness"] == 5
        assert card_dict["text"] == "Flying, vigilance"
        assert card_dict["flavor_text"] == "A majestic being"
        assert card_dict["rarity"] == "Rare"

        # Deserialize back
        restored = Card.from_dict(card_dict)

        # Verify it matches original
        assert restored.name == original.name
        assert restored.card_type == original.card_type
        assert restored.mana_cost == original.mana_cost
        assert restored.power == original.power
        assert restored.toughness == original.toughness
        assert restored.text == original.text

    def test_card_json_serialization_works(self):
        """Test that cards can be JSON serialized."""
        card = Card(
            name="JSON Test",
            card_type=CardType.ARTIFACT,
            mana_cost="2",
            color=Color.COLORLESS,
            text="Artifact ability",
        )

        # Should be JSON serializable
        json_str = json.dumps(card.to_dict())
        loaded = json.loads(json_str)

        assert loaded["name"] == "JSON Test"
        assert loaded["card_type"] == "Artifact"

    def test_card_equality_comparison(self):
        """Test that cards can be compared for equality."""
        card1 = Card(
            name="Test Card",
            card_type=CardType.INSTANT,
            mana_cost="1U",
            color=Color.BLUE,
        )

        card2 = Card(
            name="Test Card",
            card_type=CardType.INSTANT,
            mana_cost="1U",
            color=Color.BLUE,
        )

        card3 = Card(
            name="Different Card",
            card_type=CardType.INSTANT,
            mana_cost="1U",
            color=Color.BLUE,
        )

        assert card1 == card2  # Same attributes
        assert card1 != card3  # Different name

    def test_card_string_representation(self):
        """Test that cards have readable string representation."""
        card = Card(
            name="Display Test",
            card_type=CardType.CREATURE,
            mana_cost="2G",
            color=Color.GREEN,
            power=3,
            toughness=3,
        )

        str_repr = str(card)

        # Should contain key information
        assert "Display Test" in str_repr
        assert "Creature" in str_repr
        assert "2G" in str_repr
        assert "3/3" in str_repr

    def test_color_enum_values_are_valid(self):
        """Test that Color enum has valid MTG colors."""
        expected_colors = {
            "White",
            "Blue",
            "Black",
            "Red",
            "Green",
            "Colorless",
            "Multicolor",
        }
        actual_colors = {color.value for color in Color}

        assert actual_colors == expected_colors

    def test_card_type_enum_values_are_valid(self):
        """Test that CardType enum has valid MTG card types."""
        expected_types = {
            "Creature",
            "Instant",
            "Sorcery",
            "Enchantment",
            "Artifact",
            "Planeswalker",
            "Land",
        }
        actual_types = {card_type.value for card_type in CardType}

        assert expected_types.issubset(actual_types)

    def test_card_validates_mana_cost_format(self):
        """Test that mana cost follows MTG format."""
        valid_costs = ["3", "2R", "1UU", "WUBRG", "X", "XXG", ""]

        for cost in valid_costs:
            card = Card(
                name="Test",
                card_type=CardType.INSTANT,
                mana_cost=cost,
                color=Color.COLORLESS,
            )
            assert card.mana_cost == cost

    def test_card_rarity_values(self):
        """Test that rarity has valid values."""
        valid_rarities = ["Common", "Uncommon", "Rare", "Mythic"]

        for rarity in valid_rarities:
            card = Card(
                name="Test",
                card_type=CardType.INSTANT,
                mana_cost="1",
                color=Color.COLORLESS,
                rarity=rarity,
            )
            assert card.rarity == rarity

    def test_card_timestamp_is_set(self):
        """Test that cards get a creation timestamp."""
        card = Card(
            name="Timestamp Test",
            card_type=CardType.INSTANT,
            mana_cost="1",
            color=Color.COLORLESS,
        )

        # Should have a created_at timestamp
        assert hasattr(card, "created_at")
        assert isinstance(card.created_at, datetime)

        # Timestamp should be recent
        time_diff = datetime.now() - card.created_at
        assert time_diff.total_seconds() < 1  # Created within last second

    def test_card_with_special_characters_in_name(self):
        """Test that cards handle special characters correctly."""
        card = Card(
            name="Jace's Phantasm",
            card_type=CardType.CREATURE,
            mana_cost="U",
            color=Color.BLUE,
            power=1,
            toughness=1,
            text="Flying\nJace's Phantasm gets +4/+4 as long as...",
        )

        assert card.name == "Jace's Phantasm"
        assert "Flying" in card.text

        # Should serialize correctly
        card_dict = card.to_dict()
        assert card_dict["name"] == "Jace's Phantasm"
