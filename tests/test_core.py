"""Tests for the core module."""

from magic_tg_card_generator.core import CardGenerator
from magic_tg_card_generator.models import CardType, Color


class TestCardGenerator:
    """Test suite for the CardGenerator class."""

    def test_generator_initialization(self, card_generator: CardGenerator) -> None:
        """Test that the generator initializes correctly."""
        assert card_generator is not None
        assert isinstance(card_generator, CardGenerator)

    def test_generate_creature_card(self, card_generator: CardGenerator) -> None:
        """Test generating a creature card."""
        card = card_generator.generate_card(
            name="Test Creature",
            card_type=CardType.CREATURE,
            mana_cost="2GG",
            color=Color.GREEN,
            power=3,
            toughness=3,
            text="Trample",
        )
        assert card.name == "Test Creature"
        assert card.card_type == CardType.CREATURE
        assert card.power == 3
        assert card.toughness == 3

    def test_generate_spell_card(self, card_generator: CardGenerator) -> None:
        """Test generating a spell card."""
        card = card_generator.generate_card(
            name="Test Spell",
            card_type=CardType.SORCERY,
            mana_cost="1B",
            color=Color.BLACK,
            text="Destroy target creature.",
        )
        assert card.name == "Test Spell"
        assert card.card_type == CardType.SORCERY
        assert card.power is None
        assert card.toughness is None

    def test_generate_colorless_card(self, card_generator: CardGenerator) -> None:
        """Test generating a colorless card."""
        card = card_generator.generate_card(
            name="Artifact",
            card_type=CardType.ARTIFACT,
            mana_cost="3",
        )
        assert card.name == "Artifact"
        assert card.color == Color.COLORLESS
