"""Functional tests for ImageGenerator - testing actual image generation behavior."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import torch
from magic_tg_card_generator.image_generator import (
    ArtStyle,
    GenerationConfig,
    ImageGenerator,
)
from magic_tg_card_generator.models import Card, CardType, Color
from PIL import Image


class TestImageGeneratorFunctionality:
    """Test that ImageGenerator actually generates images correctly."""

    def test_generator_creates_output_directories(self, tmp_path):
        """Test that generator creates necessary directories on init."""
        output_dir = tmp_path / "test_output"
        models_dir = tmp_path / "test_models"

        # Directories shouldn't exist yet
        assert not output_dir.exists()
        assert not models_dir.exists()

        # Create generator
        generator = ImageGenerator(output_dir=output_dir, models_dir=models_dir)

        # Directories should now exist
        assert output_dir.exists()
        assert output_dir.is_dir()
        assert models_dir.exists()
        assert models_dir.is_dir()

    def test_generator_detects_best_device_automatically(self):
        """Test that generator picks the best available device."""
        generator = ImageGenerator()

        # Should pick a valid device
        assert generator.device in ["cuda", "mps", "cpu"]

        # Device should match system capabilities
        if torch.cuda.is_available():
            assert generator.device == "cuda"
        elif torch.backends.mps.is_available():
            assert generator.device == "mps"
        else:
            assert generator.device == "cpu"

    def test_generator_builds_meaningful_prompts_for_creatures(self):
        """Test that prompts accurately describe the card."""
        generator = ImageGenerator()

        dragon = Card(
            name="Ancient Fire Dragon",
            card_type=CardType.CREATURE,
            mana_cost="5RR",
            color=Color.RED,
            power=7,
            toughness=6,
            text="Flying, haste\nWhen Ancient Fire Dragon enters, deal 5 damage.",
        )

        prompt = generator._build_prompt(dragon, ArtStyle.FANTASY_REALISM)

        # Prompt should describe the card accurately
        assert "Ancient Fire Dragon" in prompt
        assert "powerful" in prompt  # Because power >= 5
        assert "fiery" in prompt or "volcanic" in prompt  # Red color
        assert "wings" in prompt  # Has flying
        assert "motion" in prompt or "dynamic" in prompt  # Has haste
        assert "fantasy realism" in prompt.lower()

    def test_generator_builds_different_prompts_for_different_cards(self):
        """Test that each card gets a unique, appropriate prompt."""
        generator = ImageGenerator()

        # Small creature
        elf = Card(
            name="Forest Elf",
            card_type=CardType.CREATURE,
            mana_cost="G",
            color=Color.GREEN,
            power=1,
            toughness=1,
        )

        # Large creature
        giant = Card(
            name="Mountain Giant",
            card_type=CardType.CREATURE,
            mana_cost="6RR",
            color=Color.RED,
            power=8,
            toughness=8,
            text="Trample",
        )

        elf_prompt = generator._build_prompt(elf, ArtStyle.DIGITAL_ART)
        giant_prompt = generator._build_prompt(giant, ArtStyle.DIGITAL_ART)

        # Prompts should be different
        assert elf_prompt != giant_prompt

        # Elf should be described as small
        assert "small" in elf_prompt or "cunning" in elf_prompt

        # Giant should be described as powerful
        assert "powerful" in giant_prompt or "imposing" in giant_prompt
        assert "massive" in giant_prompt  # Has trample

    def test_generator_saves_images_with_metadata(self, tmp_path):
        """Test that images are saved with accompanying metadata."""
        generator = ImageGenerator(output_dir=tmp_path)

        card = Card(
            name="Test Dragon",
            card_type=CardType.CREATURE,
            mana_cost="5R",
            color=Color.RED,
            power=5,
            toughness=5,
        )

        # Create a test image
        test_image = Image.new("RGB", (512, 512), color="red")

        # Save it
        image_path = generator._save_image(test_image, card)

        # Check image file exists
        assert image_path.exists()
        assert image_path.suffix == ".png"

        # Check metadata file exists
        metadata_path = image_path.with_suffix(".json")
        assert metadata_path.exists()

        # Verify metadata content
        with open(metadata_path) as f:
            metadata = json.load(f)

        assert metadata["card_name"] == "Test Dragon"
        assert metadata["card_type"] == "Creature"
        assert "timestamp" in metadata
        assert "model" in metadata

    def test_generator_handles_different_image_sizes(self):
        """Test that generator can handle different resolution settings."""
        generator = ImageGenerator()

        # Test different configurations
        configs = [
            GenerationConfig(width=512, height=512),
            GenerationConfig(width=1024, height=1024),
            GenerationConfig(width=1152, height=896),  # 4:3 ratio
        ]

        for config in configs:
            assert config.width > 0
            assert config.height > 0
            assert config.width % 8 == 0  # Should be divisible by 8 for stability
            assert config.height % 8 == 0

    def test_generator_respects_seed_for_reproducibility(self):
        """Test that same seed produces same results."""
        generator = ImageGenerator()

        config1 = GenerationConfig(seed=42)
        config2 = GenerationConfig(seed=42)
        config3 = GenerationConfig(seed=123)

        # Same seed should give same generator state
        gen1 = torch.Generator().manual_seed(config1.seed)
        gen2 = torch.Generator().manual_seed(config2.seed)
        gen3 = torch.Generator().manual_seed(config3.seed)

        # Same seeds should produce same initial random values
        val1 = torch.rand(1, generator=gen1).item()
        val2 = torch.rand(1, generator=gen2).item()
        val3 = torch.rand(1, generator=gen3).item()

        assert val1 == val2  # Same seed
        assert val1 != val3  # Different seed

    def test_generator_memory_management(self):
        """Test that generator properly manages memory."""
        generator = ImageGenerator()

        # Initially no pipeline loaded
        assert generator.pipeline is None

        # Mock a pipeline
        generator.pipeline = MagicMock()

        # Unload should clear it
        generator.unload_model()
        assert generator.pipeline is None

    def test_generator_batch_processing_efficiency(self):
        """Test that batch generation works efficiently."""
        generator = ImageGenerator()
        generator.pipeline = MagicMock()  # Mock to avoid actual loading

        cards = [
            Card(
                name=f"Card {i}",
                card_type=CardType.CREATURE,
                mana_cost="2",
                color=Color.WHITE,
                power=2,
                toughness=2,
            )
            for i in range(3)
        ]

        with patch.object(generator, "generate_card_art") as mock_generate:
            mock_generate.return_value = Path("test.png")

            paths = generator.generate_batch(cards)

            # Should process all cards
            assert len(paths) == 3
            assert mock_generate.call_count == 3

    def test_generator_error_handling_in_batch(self):
        """Test that batch generation handles errors gracefully."""
        generator = ImageGenerator()
        generator.pipeline = MagicMock()

        cards = [
            Card(
                name="Good Card",
                card_type=CardType.INSTANT,
                mana_cost="1",
                color=Color.BLUE,
            ),
            Card(
                name="Bad Card",
                card_type=CardType.INSTANT,
                mana_cost="1",
                color=Color.BLUE,
            ),
            Card(
                name="Good Card 2",
                card_type=CardType.INSTANT,
                mana_cost="1",
                color=Color.BLUE,
            ),
        ]

        with patch.object(generator, "generate_card_art") as mock_generate:
            # Second card fails
            mock_generate.side_effect = [
                Path("card1.png"),
                Exception("Generation failed"),
                Path("card3.png"),
            ]

            paths = generator.generate_batch(cards)

            # Should still return successful generations
            assert len(paths) == 2
            assert all(isinstance(p, Path) for p in paths)

    def test_generator_uses_appropriate_dtype_for_device(self):
        """Test that generator uses correct precision for each device."""
        # MPS needs float32
        mps_gen = ImageGenerator(device="mps")
        assert mps_gen.device == "mps"

        # CUDA can use float16
        cuda_gen = ImageGenerator(device="cuda")
        assert cuda_gen.device == "cuda"

        # CPU uses float32
        cpu_gen = ImageGenerator(device="cpu")
        assert cpu_gen.device == "cpu"

    def test_generator_art_styles_produce_different_prompts(self):
        """Test that different art styles create different prompts."""
        generator = ImageGenerator()

        card = Card(
            name="Test Card",
            card_type=CardType.INSTANT,
            mana_cost="1",
            color=Color.BLUE,
        )

        prompts = {}
        for style in ArtStyle:
            prompts[style] = generator._build_prompt(card, style)

        # Each style should produce a unique prompt
        unique_prompts = set(prompts.values())
        assert len(unique_prompts) == len(ArtStyle)

        # Each prompt should contain its style
        for style, prompt in prompts.items():
            assert style.value.lower() in prompt.lower()

    def test_generator_handles_special_card_abilities(self):
        """Test that special abilities are reflected in prompts."""
        generator = ImageGenerator()

        abilities = {
            "flying": "wings",
            "haste": "motion",
            "trample": "massive",
            "deathtouch": "venomous",
        }

        for ability, expected_word in abilities.items():
            card = Card(
                name="Test Creature",
                card_type=CardType.CREATURE,
                mana_cost="3",
                color=Color.BLACK,
                power=3,
                toughness=3,
                text=ability.capitalize(),
            )

            prompt = generator._build_prompt(card, ArtStyle.FANTASY_REALISM)
            assert expected_word in prompt.lower()

    def test_generator_cleans_filenames_properly(self, tmp_path):
        """Test that special characters in names are handled."""
        generator = ImageGenerator(output_dir=tmp_path)

        card = Card(
            name="Jace's Mind/Sculptor & Friends!",
            card_type=CardType.INSTANT,
            mana_cost="2U",
            color=Color.BLUE,
        )

        test_image = Image.new("RGB", (100, 100))
        filepath = generator._save_image(test_image, card)

        # Filename should be sanitized
        assert filepath.exists()
        assert "/" not in filepath.name
        assert "&" not in filepath.name
        assert "!" not in filepath.name
