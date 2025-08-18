"""Tests for the CLI module."""

from unittest.mock import patch

import pytest
from magic_tg_card_generator.cli import create_parser, main


class TestCLI:
    """Test suite for the CLI."""

    def test_parser_creation(self) -> None:
        """Test that the parser is created correctly."""
        parser = create_parser()
        assert parser is not None

    def test_help_command(self, capsys) -> None:
        """Test the help command."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Generate Magic: The Gathering cards" in captured.out

    def test_version_command(self, capsys) -> None:
        """Test the version command."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "0.1.0" in captured.out

    @patch("magic_tg_card_generator.cli.CardGenerator")
    def test_generate_command(self, mock_generator, capsys) -> None:
        """Test the generate command."""
        result = main(
            [
                "generate",
                "Test Card",
                "--type",
                "Creature",
                "--mana-cost",
                "2R",
                "--color",
                "Red",
                "--power",
                "2",
                "--toughness",
                "2",
            ]
        )
        assert result == 0
        mock_generator.assert_called_once()

    def test_no_command(self) -> None:
        """Test running without a command."""
        result = main([])
        assert result == 1
