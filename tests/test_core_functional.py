"""Functional tests for Core - testing actual card generation behavior."""

import json

from magic_tg_card_generator.core import CardGenerator
from magic_tg_card_generator.models import CardType, Color


class TestCardGeneratorFunctionality:
    """Test that CardGenerator actually generates cards correctly."""

    def test_generator_creates_valid_creature_card(self):
        """Test that generator creates a creature with all required attributes."""
        generator = CardGenerator()

        card = generator.generate_card(
            name="Dragon Lord",
            card_type=CardType.CREATURE,
            mana_cost="5RR",
            color=Color.RED,
            power=7,
            toughness=7,
            text="Flying, trample",
        )

        # Verify the card is actually valid
        assert card.name == "Dragon Lord"
        assert card.card_type == CardType.CREATURE
        assert card.mana_cost == "5RR"
        assert card.color == Color.RED
        assert card.power == 7
        assert card.toughness == 7
        assert card.text == "Flying, trample"
        assert card.converted_mana_cost == 7  # 5 + R + R

    def test_generator_creates_instant_without_power_toughness(self):
        """Test that non-creatures don't have power/toughness."""
        generator = CardGenerator()

        card = generator.generate_card(
            name="Cancel",
            card_type=CardType.INSTANT,
            mana_cost="1UU",
            color=Color.BLUE,
            text="Counter target spell.",
        )

        # Verify instant spell attributes
        assert card.name == "Cancel"
        assert card.card_type == CardType.INSTANT
        assert card.power is None
        assert card.toughness is None
        assert card.converted_mana_cost == 3

    def test_generator_saves_card_to_file(self, tmp_path):
        """Test that cards are actually saved to disk."""
        output_dir = tmp_path / "cards"
        generator = CardGenerator(output_dir=output_dir)

        card = generator.generate_card(
            name="Test Card",
            card_type=CardType.ARTIFACT,
            mana_cost="3",
            color=Color.COLORLESS,
        )

        # Save the card
        filepath = generator.save_card(card)

        # Verify file was created
        assert filepath.exists()
        assert filepath.suffix == ".json"
        assert output_dir.exists()

        # Verify content is correct
        with open(filepath) as f:
            saved_data = json.load(f)

        assert saved_data["name"] == "Test Card"
        assert saved_data["card_type"] == "Artifact"
        assert saved_data["mana_cost"] == "3"

    def test_generator_batch_creates_multiple_unique_cards(self):
        """Test that batch generation creates unique cards."""
        generator = CardGenerator()

        cards = generator.generate_batch(count=5)

        # Verify we got the right number
        assert len(cards) == 5

        # Verify all cards are unique
        names = [card.name for card in cards]
        assert len(names) == len(set(names))

        # Verify all cards are valid
        for card in cards:
            assert card.name
            assert card.card_type in CardType
            assert card.mana_cost
            assert card.color in Color

    def test_generator_random_creates_varied_cards(self):
        """Test that random generation creates varied card types."""
        generator = CardGenerator()

        # Generate multiple random cards
        card_types = set()
        colors = set()

        for _ in range(20):
            card = generator.generate_random()
            card_types.add(card.card_type)
            colors.add(card.color)

        # Verify variety (should have multiple types and colors after 20 cards)
        assert len(card_types) > 1
        assert len(colors) > 1

    def test_generator_respects_color_identity(self):
        """Test that mana cost matches color identity."""
        generator = CardGenerator()

        # Red card should have red mana
        red_card = generator.generate_card(
            name="Red Spell",
            card_type=CardType.INSTANT,
            mana_cost="2R",
            color=Color.RED,
        )
        assert "R" in red_card.mana_cost

        # Blue card should have blue mana
        blue_card = generator.generate_card(
            name="Blue Spell",
            card_type=CardType.INSTANT,
            mana_cost="UU",
            color=Color.BLUE,
        )
        assert "U" in blue_card.mana_cost

    def test_generator_calculates_mana_cost_correctly(self):
        """Test that converted mana cost is calculated correctly."""
        generator = CardGenerator()

        test_cases = [
            ("3", 3),
            ("1R", 2),
            ("2UU", 4),
            ("WUBRG", 5),
            ("3WW", 5),
            ("X", 0),
            ("XX", 0),
            ("XR", 1),
        ]

        for mana_cost, expected_cmc in test_cases:
            card = generator.generate_card(
                name=f"Test {mana_cost}",
                card_type=CardType.INSTANT,
                mana_cost=mana_cost,
                color=Color.COLORLESS,
            )
            assert card.converted_mana_cost == expected_cmc

    def test_generator_validates_creature_power_toughness(self):
        """Test that creatures must have valid power/toughness."""
        generator = CardGenerator()

        # Valid creature
        valid_card = generator.generate_card(
            name="Valid Creature",
            card_type=CardType.CREATURE,
            mana_cost="2",
            color=Color.WHITE,
            power=2,
            toughness=3,
        )
        assert valid_card.power == 2
        assert valid_card.toughness == 3

        # Creature without power/toughness should get defaults
        default_card = generator.generate_card(
            name="Default Creature",
            card_type=CardType.CREATURE,
            mana_cost="2",
            color=Color.WHITE,
        )
        assert default_card.power is not None
        assert default_card.toughness is not None

    def test_generator_handles_multicolor_cards(self):
        """Test that multicolor cards work correctly."""
        generator = CardGenerator()

        # Multicolor card
        card = generator.generate_card(
            name="Multicolor Spell",
            card_type=CardType.INSTANT,
            mana_cost="1WU",
            color=Color.WHITE,  # Primary color
        )

        assert card.mana_cost == "1WU"
        assert card.converted_mana_cost == 3

    def test_generator_load_from_file(self, tmp_path):
        """Test loading cards from saved files."""
        generator = CardGenerator(output_dir=tmp_path)

        # Create and save a card
        original_card = generator.generate_card(
            name="Saved Card",
            card_type=CardType.ENCHANTMENT,
            mana_cost="2G",
            color=Color.GREEN,
            text="Test enchantment",
        )
        filepath = generator.save_card(original_card)

        # Load the card back
        loaded_card = generator.load_card(filepath)

        # Verify it matches
        assert loaded_card.name == original_card.name
        assert loaded_card.card_type == original_card.card_type
        assert loaded_card.mana_cost == original_card.mana_cost
        assert loaded_card.text == original_card.text

    def test_generator_export_to_different_formats(self, tmp_path):
        """Test exporting cards to different formats."""
        generator = CardGenerator(output_dir=tmp_path)

        card = generator.generate_card(
            name="Export Test",
            card_type=CardType.CREATURE,
            mana_cost="3",
            color=Color.COLORLESS,
            power=3,
            toughness=3,
        )

        # Export as JSON
        json_path = generator.export_card(card, format="json")
        assert json_path.exists()
        assert json_path.suffix == ".json"

        # Export as text (for printing)
        text_path = generator.export_card(card, format="text")
        assert text_path.exists()
        assert text_path.suffix == ".txt"

        with open(text_path) as f:
            content = f.read()
            assert "Export Test" in content
            assert "3" in content  # Mana cost
            assert "3/3" in content  # Power/Toughness
