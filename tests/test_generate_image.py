"""Tests for the generate_image module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from magic_tg_card_generator.generate_image import main
from magic_tg_card_generator.image_generator import ImageGenerator
from magic_tg_card_generator.models import Card, CardType, Color


class TestGenerateImage:
    """Test the generate_image CLI."""

    @patch("magic_tg_card_generator.generate_image.ImageGenerator")
    def test_generate_with_custom_prompt(self, mock_generator):
        """Test generation with custom prompt."""
        mock_instance = MagicMock()
        mock_generator.return_value = mock_instance
        mock_instance.generate_card_art.return_value = Path("test.png")
        mock_instance.pipeline = None

        test_args = [
            "prog",
            "--prompt",
            "A majestic dragon in the clouds",
            "--name",
            "Cloud Dragon",
        ]

        with patch("sys.argv", test_args):
            result = main()

        assert result == 0
        mock_instance.generate_card_art.assert_called_once()
        call_args = mock_instance.generate_card_art.call_args
        assert call_args.kwargs["custom_prompt"] == "A majestic dragon in the clouds"

    @patch("magic_tg_card_generator.generate_image.ImageGenerator")
    @patch("magic_tg_card_generator.generate_image.Prompt.ask")
    def test_interactive_mode(self, mock_prompt, mock_generator):
        """Test interactive prompt mode."""
        mock_prompt.return_value = "An epic battle scene"
        mock_instance = MagicMock()
        mock_generator.return_value = mock_instance
        mock_instance.generate_card_art.return_value = Path("test.png")
        mock_instance.pipeline = None

        test_args = ["prog", "--interactive"]

        with patch("sys.argv", test_args):
            result = main()

        assert result == 0
        mock_prompt.assert_called_once_with(
            "[green]Was für ein Bild soll generiert werden?[/green]",
            default=None,
        )
        call_args = mock_instance.generate_card_art.call_args
        assert call_args.kwargs["custom_prompt"] == "An epic battle scene"

    @patch("magic_tg_card_generator.generate_image.ImageGenerator")
    def test_generate_with_config_file(self, mock_generator, tmp_path):
        """Test generation with config file."""
        # Create nested directory structure
        config_dir = tmp_path / "configs" / "image_generation"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "test_config.json"
        config_data = {
            "image_generation": {"model": "SDXL_LOCAL"},
            "generation_params": {"steps": 50, "guidance_scale": 8.0},
        }
        config_file.write_text(json.dumps(config_data))

        mock_instance = MagicMock()
        mock_generator.return_value = mock_instance
        mock_instance.generate_card_art.return_value = Path("test.png")
        mock_instance.pipeline = None

        test_args = ["prog", "--config", str(config_file)]

        with patch("sys.argv", test_args):
            result = main()

        assert result == 0
        mock_generator.assert_called_once_with(config_file=config_file)

    @patch("magic_tg_card_generator.generate_image.ImageGenerator")
    def test_generate_creature_with_power_toughness(self, mock_generator):
        """Test generating a creature with power/toughness."""
        mock_instance = MagicMock()
        mock_generator.return_value = mock_instance
        mock_instance.generate_card_art.return_value = Path("test.png")
        mock_instance.pipeline = None

        test_args = [
            "prog",
            "--name",
            "Fire Drake",
            "--type",
            "Creature",
            "--color",
            "Red",
            "--power",
            "4",
            "--toughness",
            "3",
        ]

        with patch("sys.argv", test_args):
            result = main()

        assert result == 0
        call_args = mock_instance.generate_card_art.call_args
        card = call_args.kwargs["card"]
        assert card.name == "Fire Drake"
        assert card.card_type == CardType.CREATURE
        assert card.color == Color.RED
        assert card.power == 4
        assert card.toughness == 3

    @patch("magic_tg_card_generator.generate_image.ImageGenerator")
    def test_error_handling(self, mock_generator):
        """Test error handling during generation."""
        mock_instance = MagicMock()
        mock_generator.return_value = mock_instance
        mock_instance.generate_card_art.side_effect = Exception("Generation failed")
        mock_instance.pipeline = None

        test_args = ["prog", "--name", "Test Card"]

        with patch("sys.argv", test_args):
            result = main()

        assert result == 1  # Should return error code

    @patch("magic_tg_card_generator.generate_image.ImageGenerator")
    def test_model_cleanup(self, mock_generator):
        """Test that model is properly unloaded."""
        mock_instance = MagicMock()
        mock_generator.return_value = mock_instance
        mock_instance.generate_card_art.return_value = Path("test.png")
        mock_instance.pipeline = MagicMock()  # Pipeline is loaded

        test_args = ["prog", "--name", "Test Card"]

        with patch("sys.argv", test_args):
            result = main()

        assert result == 0
        mock_instance.unload_model.assert_called_once()