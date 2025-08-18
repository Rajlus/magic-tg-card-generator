"""Pytest configuration and fixtures."""

import pytest
from magic_tg_card_generator.core import CardGenerator
from magic_tg_card_generator.models import Card, CardType, Color


@pytest.fixture
def card_generator() -> CardGenerator:
    """Provide a CardGenerator instance."""
    return CardGenerator()


@pytest.fixture
def sample_creature() -> Card:
    """Provide a sample creature card."""
    return Card(
        name="Lightning Bolt Dragon",
        card_type=CardType.CREATURE,
        mana_cost="3RR",
        color=Color.RED,
        power=4,
        toughness=4,
        text="Flying, haste",
        rarity="Rare",
    )


@pytest.fixture
def sample_instant() -> Card:
    """Provide a sample instant card."""
    return Card(
        name="Counterspell",
        card_type=CardType.INSTANT,
        mana_cost="UU",
        color=Color.BLUE,
        text="Counter target spell.",
        rarity="Common",
    )
