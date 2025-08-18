"""Tests for the models module."""

import pytest
from magic_tg_card_generator.models import Card, CardType, Color
from pydantic import ValidationError


class TestCard:
    """Test suite for the Card model."""

    def test_create_creature_card(self) -> None:
        """Test creating a creature card."""
        card = Card(
            name="Goblin Warrior",
            card_type=CardType.CREATURE,
            mana_cost="1R",
            color=Color.RED,
            power=2,
            toughness=1,
            text="Haste",
        )
        assert card.name == "Goblin Warrior"
        assert card.card_type == CardType.CREATURE
        assert card.power == 2
        assert card.toughness == 1

    def test_create_instant_card(self) -> None:
        """Test creating an instant card."""
        card = Card(
            name="Lightning Bolt",
            card_type=CardType.INSTANT,
            mana_cost="R",
            color=Color.RED,
            text="Deal 3 damage to any target.",
        )
        assert card.name == "Lightning Bolt"
        assert card.card_type == CardType.INSTANT
        assert card.power is None
        assert card.toughness is None

    def test_invalid_mana_cost(self) -> None:
        """Test that invalid mana cost raises validation error."""
        with pytest.raises(ValidationError):
            Card(
                name="Invalid Card",
                card_type=CardType.INSTANT,
                mana_cost="Invalid",
                color=Color.RED,
            )

    def test_power_toughness_only_for_creatures(self) -> None:
        """Test that power/toughness can only be set for creatures."""
        with pytest.raises(ValidationError):
            Card(
                name="Invalid Instant",
                card_type=CardType.INSTANT,
                mana_cost="1U",
                color=Color.BLUE,
                power=2,
                toughness=2,
            )

    def test_card_json_serialization(self, sample_creature: Card) -> None:
        """Test that cards can be serialized to JSON."""
        json_data = sample_creature.model_dump_json()
        assert "Lightning Bolt Dragon" in json_data
        assert "Creature" in json_data
