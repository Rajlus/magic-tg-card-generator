"""Comprehensive functional tests to achieve 70% coverage."""

import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

# Test imports to increase coverage
from magic_tg_card_generator.cli import main
from magic_tg_card_generator.config import Settings
from magic_tg_card_generator.core import CardGenerator
from magic_tg_card_generator.models import Card, CardType, Color


class TestFullCoverage:
    """Comprehensive tests to reach 70% coverage."""

    def test_cli_generate_card_function(self):
        """Test CLI card generation through main function."""
        test_args = [
            "generate",
            "Test",
            "--type",
            "Creature",
            "--mana-cost",
            "3",
            "--color",
            "Red",
            "--power",
            "3",
            "--toughness",
            "3",
        ]

        with patch("magic_tg_card_generator.cli.CardGenerator") as mock_gen:
            mock_card = Card(
                name="Test",
                card_type=CardType.CREATURE,
                mana_cost="3",
                color=Color.RED,
                power=3,
                toughness=3,
            )
            mock_gen.return_value.generate_card.return_value = mock_card

            result = main(test_args)

            assert result == 0
            mock_gen.return_value.generate_card.assert_called_once()

    def test_cli_help_command(self):
        """Test CLI help command."""
        test_args = ["--help"]

        with patch("sys.stdout", new=StringIO()) as fake_stdout:
            with pytest.raises(SystemExit) as exc_info:
                main(test_args)

            assert exc_info.value.code == 0
            output = fake_stdout.getvalue()
            assert "Magic: The Gathering" in output or "generate" in output

    def test_cli_main_with_generate(self):
        """Test CLI main function with generate command."""
        test_args = [
            "generate",
            "Test",
            "--type",
            "Instant",
            "--mana-cost",
            "1U",
            "--color",
            "Blue",
        ]

        with patch("magic_tg_card_generator.cli.CardGenerator") as mock_gen:
            mock_card = Card(
                name="Test",
                card_type=CardType.INSTANT,
                mana_cost="1U",
                color=Color.BLUE,
            )
            mock_gen.return_value.generate_card.return_value = mock_card

            result = main(test_args)
            assert result == 0

    def test_cli_main_without_command(self):
        """Test CLI main function without command."""
        test_args = []

        with patch("sys.stdout", new=StringIO()):
            result = main(test_args)
            assert result == 1

    def test_config_initialization(self, tmp_path, monkeypatch):
        """Test Settings initialization."""
        # Use tmp_path to avoid creating real directories
        monkeypatch.chdir(tmp_path)

        settings = Settings()

        assert settings.app_name == "Magic TG Card Generator"
        assert settings.app_version == "0.1.0"
        assert settings.debug is False
        assert settings.log_level == "INFO"
        assert settings.data_dir == Path("data")
        assert settings.output_dir == Path("output")

    def test_config_with_env_vars(self, tmp_path, monkeypatch):
        """Test Settings with environment variables."""
        monkeypatch.chdir(tmp_path)

        with patch.dict("os.environ", {"DEBUG": "true", "LOG_LEVEL": "DEBUG"}):
            settings = Settings()
            assert settings.debug is True
            assert settings.log_level == "DEBUG"

    def test_core_card_generator_init(self):
        """Test CardGenerator initialization."""
        gen = CardGenerator()
        assert gen.output_dir == Path("output/cards")

    def test_core_generate_card(self):
        """Test card generation."""
        gen = CardGenerator()

        card = gen.generate_card(
            name="Dragon",
            card_type=CardType.CREATURE,
            mana_cost="5R",
            color=Color.RED,
            power=5,
            toughness=5,
        )

        assert card.name == "Dragon"
        assert card.card_type == CardType.CREATURE
        assert card.power == 5
        assert card.toughness == 5

    def test_core_save_card(self, tmp_path):
        """Test saving a card."""
        gen = CardGenerator(output_dir=tmp_path)

        card = Card(
            name="Test Card",
            card_type=CardType.INSTANT,
            mana_cost="1U",
            color=Color.BLUE,
        )

        filepath = gen.save_card(card)

        assert filepath.exists()
        assert filepath.suffix == ".json"

        with open(filepath) as f:
            data = json.load(f)
            assert data["name"] == "Test Card"

    def test_core_generate_batch(self):
        """Test batch generation."""
        gen = CardGenerator()

        cards = gen.generate_batch(3)

        assert len(cards) == 3
        # All cards should have unique names
        names = [card.name for card in cards]
        assert len(names) == len(set(names))

    def test_core_generate_random(self):
        """Test random card generation."""
        gen = CardGenerator()

        card = gen.generate_random()

        assert card is not None
        assert card.name is not None
        assert card.card_type in CardType
        assert card.color in Color
        assert card.mana_cost is not None

    def test_models_card_validation(self):
        """Test Card model validation."""
        # Valid creature
        creature = Card(
            name="Beast",
            card_type=CardType.CREATURE,
            mana_cost="2G",
            color=Color.GREEN,
            power=3,
            toughness=3,
        )
        assert creature.power == 3

        # Valid instant (no power/toughness)
        instant = Card(
            name="Bolt", card_type=CardType.INSTANT, mana_cost="R", color=Color.RED
        )
        assert instant.power is None

    def test_models_to_dict(self):
        """Test Card serialization."""
        card = Card(
            name="Test",
            card_type=CardType.ARTIFACT,
            mana_cost="2",
            color=Color.COLORLESS,
        )

        card_dict = card.to_dict()

        assert card_dict["name"] == "Test"
        assert card_dict["card_type"] == "Artifact"
        assert card_dict["mana_cost"] == "2"

    def test_models_from_dict(self):
        """Test Card deserialization."""
        data = {
            "name": "Test",
            "card_type": "Sorcery",
            "mana_cost": "1B",
            "color": "Black",
        }

        card = Card.from_dict(data)

        assert card.name == "Test"
        assert card.card_type == CardType.SORCERY
        assert card.color == Color.BLACK

    def test_models_string_representation(self):
        """Test Card string representation."""
        card = Card(
            name="Lightning", card_type=CardType.INSTANT, mana_cost="R", color=Color.RED
        )

        str_repr = str(card)
        assert "Lightning" in str_repr

    def test_main_entry_point(self):
        """Test __main__ module."""
        with patch("magic_tg_card_generator.__main__.main"):
            # Just test that it imports without error
            from magic_tg_card_generator import __main__

            assert __main__ is not None

    def test_init_module(self):
        """Test __init__ module."""
        from magic_tg_card_generator import Card, CardGenerator, CardType, Color

        assert CardGenerator is not None
        assert Card is not None
        assert CardType is not None
        assert Color is not None

    def test_cli_with_all_args(self):
        """Test CLI with all arguments."""
        test_args = [
            "generate",
            "Full Card",
            "--type",
            "Creature",
            "--mana-cost",
            "3WW",
            "--color",
            "White",
            "--power",
            "4",
            "--toughness",
            "5",
            "--text",
            "Vigilance",
        ]

        with patch("magic_tg_card_generator.cli.CardGenerator") as mock_gen:
            mock_card = Card(
                name="Full Card",
                card_type=CardType.CREATURE,
                mana_cost="3WW",
                color=Color.WHITE,
                power=4,
                toughness=5,
                text="Vigilance",
            )
            mock_gen.return_value.generate_card.return_value = mock_card

            result = main(test_args)
            assert result == 0

            # Verify the generator was called with correct args
            call_args = mock_gen.return_value.generate_card.call_args[1]
            assert call_args["name"] == "Full Card"
            assert call_args["power"] == 4
            assert call_args["toughness"] == 5
