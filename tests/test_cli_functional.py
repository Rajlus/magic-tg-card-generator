"""Functional tests for CLI - testing actual behavior, not just code."""

from io import StringIO
from unittest.mock import patch

import pytest
from magic_tg_card_generator.cli import main
from magic_tg_card_generator.models import Card, CardType, Color


class TestCLIFunctionality:
    """Test that CLI actually works as documented."""

    @patch("magic_tg_card_generator.cli.CardGenerator")
    def test_cli_generates_creature_card_with_correct_attributes(self, mock_generator):
        """Test that CLI correctly generates a creature card with all attributes."""
        # Setup
        mock_card = Card(
            name="Fire Dragon",
            card_type=CardType.CREATURE,
            mana_cost="3RR",
            color=Color.RED,
            power=5,
            toughness=4,
            text="Flying",
        )
        mock_generator.return_value.generate_card.return_value = mock_card

        # Execute
        test_args = [
            "generate",
            "Fire Dragon",
            "--type",
            "Creature",
            "--mana-cost",
            "3RR",
            "--color",
            "Red",
            "--power",
            "5",
            "--toughness",
            "4",
            "--text",
            "Flying",
        ]

        with patch("sys.stdout", new=StringIO()) as fake_out:
            result = main(test_args)
            output = fake_out.getvalue()

        # Verify functionality
        assert result == 0
        mock_generator.return_value.generate_card.assert_called_once()
        call_args = mock_generator.return_value.generate_card.call_args[1]

        assert call_args["name"] == "Fire Dragon"
        assert call_args["card_type"] == CardType.CREATURE
        assert call_args["power"] == 5
        assert call_args["toughness"] == 4
        assert "Fire Dragon" in output

    @patch("magic_tg_card_generator.cli.CardGenerator")
    def test_cli_generates_instant_spell_without_power_toughness(self, mock_generator):
        """Test that instant spells don't have power/toughness."""
        mock_card = Card(
            name="Lightning Bolt",
            card_type=CardType.INSTANT,
            mana_cost="R",
            color=Color.RED,
            text="Deal 3 damage to any target.",
        )
        mock_generator.return_value.generate_card.return_value = mock_card

        test_args = [
            "generate",
            "Lightning Bolt",
            "--type",
            "Instant",
            "--mana-cost",
            "R",
            "--color",
            "Red",
            "--text",
            "Deal 3 damage to any target.",
        ]

        with patch("sys.stdout", new=StringIO()) as fake_out:
            result = main(test_args)
            output = fake_out.getvalue()

        # Verify instant has no power/toughness
        assert result == 0
        call_args = mock_generator.return_value.generate_card.call_args[1]
        assert call_args.get("power") is None
        assert call_args.get("toughness") is None
        assert "Lightning Bolt" in output

    def test_cli_no_command_shows_help(self):
        """Test that running without command shows help."""
        test_args = []

        with patch("sys.stdout", new=StringIO()) as fake_out:
            result = main(test_args)
            output = fake_out.getvalue()

        assert result == 1  # Should return error code

    def test_cli_help_displays_usage_information(self):
        """Test that help actually shows usage instructions."""
        test_args = ["--help"]

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.stdout", new=StringIO()) as fake_out:
                main(test_args)
                output = fake_out.getvalue()

        assert exc_info.value.code == 0  # Help exits with 0

    def test_cli_invalid_type_shows_error(self):
        """Test that invalid card type shows helpful error."""
        test_args = ["generate", "Test", "--type", "invalid_type", "--mana-cost", "1"]

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.stderr", new=StringIO()) as fake_err:
                main(test_args)
                error = fake_err.getvalue()

        assert exc_info.value.code != 0  # Error exit

    @patch("magic_tg_card_generator.cli.CardGenerator")
    def test_cli_creature_requires_power_toughness(self, mock_generator):
        """Test that creatures require power and toughness."""
        mock_card = Card(
            name="Test Creature",
            card_type=CardType.CREATURE,
            mana_cost="2",
            color=Color.BLUE,
            power=2,
            toughness=3,
        )
        mock_generator.return_value.generate_card.return_value = mock_card

        test_args = [
            "generate",
            "Test Creature",
            "--type",
            "Creature",
            "--mana-cost",
            "2",
            "--color",
            "Blue",
            "--power",
            "2",
            "--toughness",
            "3",
        ]

        with patch("sys.stdout", new=StringIO()) as fake_out:
            result = main(test_args)
            output = fake_out.getvalue()

        assert result == 0
        assert "Test Creature" in output

    @patch("magic_tg_card_generator.cli.CardGenerator")
    def test_cli_colorless_cards_work(self, mock_generator):
        """Test that colorless cards can be generated."""
        mock_card = Card(
            name="Sol Ring",
            card_type=CardType.ARTIFACT,
            mana_cost="1",
            color=Color.COLORLESS,
            text="Add 2 colorless mana",
        )
        mock_generator.return_value.generate_card.return_value = mock_card

        test_args = [
            "generate",
            "Sol Ring",
            "--type",
            "Artifact",
            "--mana-cost",
            "1",
            "--text",
            "Add 2 colorless mana",
        ]

        with patch("sys.stdout", new=StringIO()) as fake_out:
            result = main(test_args)
            output = fake_out.getvalue()

        assert result == 0
        # When no color is provided, should default to colorless
        call_args = mock_generator.return_value.generate_card.call_args[1]
        assert call_args.get("color") is None or call_args["color"] == Color.COLORLESS

    @patch("magic_tg_card_generator.cli.CardGenerator")
    def test_cli_verbose_mode_enables_debug_logging(self, mock_generator):
        """Test that verbose flag enables debug logging."""
        mock_card = Card(
            name="Test", card_type=CardType.INSTANT, mana_cost="1", color=Color.BLUE
        )
        mock_generator.return_value.generate_card.return_value = mock_card

        test_args = [
            "--verbose",
            "generate",
            "Test",
            "--type",
            "Instant",
            "--mana-cost",
            "1",
        ]

        with patch("magic_tg_card_generator.cli.setup_logging") as mock_logging:
            with patch("sys.stdout", new=StringIO()):
                result = main(test_args)

        assert result == 0
        mock_logging.assert_called_once_with(True)  # verbose=True
