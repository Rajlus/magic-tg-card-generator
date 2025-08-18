"""Tests for the image generator module."""

from unittest.mock import MagicMock, patch

import pytest
from magic_tg_card_generator.image_generator import (
    ImageGenerator,
    ImageStyle,
    ModelSize,
)
from magic_tg_card_generator.models import Card, CardType, Color
from PIL import Image


@pytest.fixture
def mock_pipeline():
    """Mock the Stable Diffusion pipeline."""
    with patch(
        "magic_tg_card_generator.image_generator.StableDiffusionPipeline"
    ) as mock:
        pipeline = MagicMock()
        pipeline.to.return_value = pipeline
        mock.from_pretrained.return_value = pipeline
        yield mock


@pytest.fixture
def sample_card():
    """Create a sample card for testing."""
    return Card(
        name="Test Dragon",
        card_type=CardType.CREATURE,
        mana_cost="3RR",
        color=Color.RED,
        power=5,
        toughness=5,
        text="Flying, haste",
    )


class TestImageGenerator:
    """Test suite for ImageGenerator class."""

    def test_init_creates_directories(self, tmp_path):
        """Test that initialization creates necessary directories."""
        output_dir = tmp_path / "output"
        cache_dir = tmp_path / "cache"

        generator = ImageGenerator(
            output_dir=output_dir,
            cache_dir=cache_dir,
        )

        assert output_dir.exists()
        assert cache_dir.exists()

    def test_device_selection_cpu(self):
        """Test device selection defaults to CPU when no GPU available."""
        with patch("torch.cuda.is_available", return_value=False):
            with patch("torch.backends.mps.is_available", return_value=False):
                generator = ImageGenerator()
                assert generator.device == "cpu"

    def test_device_selection_cuda(self):
        """Test device selection prefers CUDA when available."""
        with patch("torch.cuda.is_available", return_value=True):
            generator = ImageGenerator()
            assert generator.device == "cuda"

    def test_device_selection_mps(self):
        """Test device selection uses MPS on Apple Silicon."""
        with patch("torch.cuda.is_available", return_value=False):
            with patch("torch.backends.mps.is_available", return_value=True):
                generator = ImageGenerator()
                assert generator.device == "mps"

    def test_device_selection_manual(self):
        """Test manual device selection."""
        generator = ImageGenerator(device="cpu")
        assert generator.device == "cpu"

    def test_build_prompt(self, sample_card):
        """Test prompt building for different cards."""
        generator = ImageGenerator()

        prompt = generator._build_prompt(sample_card, ImageStyle.FANTASY)

        assert "Test Dragon" in prompt
        assert "powerful" in prompt  # Because power >= 5
        assert "fiery" in prompt  # Because it's red
        assert "wings" in prompt  # Because it has flying
        assert "fantasy art style" in prompt

    def test_build_prompt_colorless(self):
        """Test prompt building for colorless cards."""
        generator = ImageGenerator()

        card = Card(
            name="Artifact Golem",
            card_type=CardType.ARTIFACT,
            mana_cost="5",
            color=Color.COLORLESS,
        )

        prompt = generator._build_prompt(card, ImageStyle.REALISTIC)

        assert "metallic" in prompt
        assert "realistic" in prompt

    def test_negative_prompt(self):
        """Test negative prompt generation."""
        generator = ImageGenerator()

        negative = generator._build_negative_prompt()

        assert "low quality" in negative
        assert "watermark" in negative
        assert "deformed" in negative

    @patch("magic_tg_card_generator.image_generator.StableDiffusionPipeline")
    def test_load_model(self, mock_sd):
        """Test model loading."""
        generator = ImageGenerator(model_size=ModelSize.SMALL)

        mock_pipeline = MagicMock()
        mock_pipeline.to.return_value = mock_pipeline
        mock_sd.from_pretrained.return_value = mock_pipeline

        generator.load_model()

        mock_sd.from_pretrained.assert_called_once()
        assert generator.pipeline is not None

    @patch("magic_tg_card_generator.image_generator.StableDiffusionPipeline")
    def test_load_model_force_reload(self, mock_sd):
        """Test force reloading of model."""
        generator = ImageGenerator()

        mock_pipeline = MagicMock()
        mock_pipeline.to.return_value = mock_pipeline
        mock_sd.from_pretrained.return_value = mock_pipeline

        generator.load_model()
        generator.load_model(force_reload=True)

        assert mock_sd.from_pretrained.call_count == 2

    def test_save_image(self, tmp_path, sample_card):
        """Test image saving functionality."""
        generator = ImageGenerator(output_dir=tmp_path)

        # Create a dummy image
        image = Image.new("RGB", (512, 512), color="red")

        filepath = generator._save_image(image, sample_card)

        assert filepath.exists()
        assert filepath.suffix == ".png"
        assert "Test_Dragon" in filepath.name

        # Check metadata file
        metadata_path = filepath.with_suffix(".json")
        assert metadata_path.exists()

    @patch("magic_tg_card_generator.image_generator.torch.cuda.empty_cache")
    def test_cleanup_with_cuda(self, mock_empty_cache):
        """Test cleanup with CUDA available."""
        with patch("torch.cuda.is_available", return_value=True):
            generator = ImageGenerator()
            generator.pipeline = MagicMock()

            generator.cleanup()

            assert generator.pipeline is None
            mock_empty_cache.assert_called_once()

    def test_cleanup_without_model(self):
        """Test cleanup when no model is loaded."""
        generator = ImageGenerator()
        generator.cleanup()  # Should not raise

    def test_model_sizes(self):
        """Test different model size configurations."""
        for size in ModelSize:
            generator = ImageGenerator(model_size=size)
            assert generator.model_size == size

    def test_image_styles(self):
        """Test all image style enums are valid."""
        styles = list(ImageStyle)
        assert len(styles) > 0

        for style in styles:
            assert isinstance(style.value, str)
            assert len(style.value) > 0
