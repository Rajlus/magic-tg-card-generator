"""Tests for the image generator module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from magic_tg_card_generator.image_generator import (
    ArtStyle,
    GenerationConfig,
    ImageGenerator,
    ModelConfig,
)
from magic_tg_card_generator.models import Card, CardType, Color
from PIL import Image


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


@pytest.fixture
def tmp_output_dir(tmp_path):
    """Create temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


class TestArtStyle:
    """Test ArtStyle enum."""

    def test_all_styles_have_values(self):
        """Test that all art styles have string values."""
        for style in ArtStyle:
            assert isinstance(style.value, str)
            assert len(style.value) > 0

    def test_specific_styles_exist(self):
        """Test that expected styles exist."""
        assert ArtStyle.OIL_PAINTING
        assert ArtStyle.DIGITAL_ART
        assert ArtStyle.FANTASY_REALISM
        assert ArtStyle.WATERCOLOR
        assert ArtStyle.COMIC_BOOK
        assert ArtStyle.DARK_GOTHIC


class TestModelConfig:
    """Test ModelConfig enum."""

    def test_all_models_have_values(self):
        """Test that all models have string values."""
        for model in ModelConfig:
            assert isinstance(model.value, str)
            assert len(model.value) > 0

    def test_specific_models_exist(self):
        """Test that expected models exist."""
        assert ModelConfig.SD_1_4
        assert ModelConfig.SD_1_5
        assert ModelConfig.SD_2_1
        assert ModelConfig.SDXL_BASE
        assert ModelConfig.SDXL_LOCAL

    def test_local_model_path(self):
        """Test that local model has correct path."""
        assert "models/sd_xl_base_1.0.safetensors" in ModelConfig.SDXL_LOCAL.value


class TestGenerationConfig:
    """Test GenerationConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = GenerationConfig()
        assert config.num_inference_steps == 30
        assert config.guidance_scale == 7.5
        assert config.height == 512
        assert config.width == 512
        assert config.seed is None
        assert "low quality" in config.negative_prompt

    def test_custom_values(self):
        """Test custom configuration values."""
        config = GenerationConfig(
            num_inference_steps=50,
            guidance_scale=10.0,
            height=1024,
            width=1024,
            seed=42,
            negative_prompt="custom negative",
        )
        assert config.num_inference_steps == 50
        assert config.guidance_scale == 10.0
        assert config.height == 1024
        assert config.width == 1024
        assert config.seed == 42
        assert config.negative_prompt == "custom negative"


class TestImageGenerator:
    """Test suite for ImageGenerator class."""

    def test_init_with_config_file(self, tmp_path):
        """Test ImageGenerator initialization with config file."""
        config_file = tmp_path / "config.json"
        config_data = {
            "image_generation": {"model": "SDXL_BASE", "low_memory": True},
            "output_settings": {"output_dir": "custom/output"},
        }
        config_file.write_text(json.dumps(config_data))

        generator = ImageGenerator(config_file=config_file)

        assert generator.model_config == ModelConfig.SDXL_BASE
        assert generator.low_memory is True
        assert generator.config == config_data

    def test_init_creates_directories(self, tmp_path):
        """Test that initialization creates necessary directories."""
        output_dir = tmp_path / "output"
        models_dir = tmp_path / "models"

        generator = ImageGenerator(
            output_dir=output_dir,
            models_dir=models_dir,
        )

        assert output_dir.exists()
        assert models_dir.exists()
        assert generator.output_dir == output_dir
        assert generator.models_dir == models_dir

    def test_init_default_directories(self):
        """Test default directory creation."""
        generator = ImageGenerator()
        assert generator.output_dir == Path("output/images")
        assert generator.models_dir == Path("models")

    @patch("torch.cuda.is_available")
    @patch("torch.backends.mps.is_available")
    def test_device_selection_cpu(self, mock_mps, mock_cuda):
        """Test device selection defaults to CPU when no GPU available."""
        mock_cuda.return_value = False
        mock_mps.return_value = False

        generator = ImageGenerator()
        assert generator.device == "cpu"

    @patch("torch.cuda.is_available")
    def test_device_selection_cuda(self, mock_cuda):
        """Test device selection prefers CUDA when available."""
        mock_cuda.return_value = True

        generator = ImageGenerator()
        assert generator.device == "cuda"

    @patch("torch.cuda.is_available")
    @patch("torch.backends.mps.is_available")
    def test_device_selection_mps(self, mock_mps, mock_cuda):
        """Test device selection uses MPS on Apple Silicon."""
        mock_cuda.return_value = False
        mock_mps.return_value = True

        generator = ImageGenerator()
        assert generator.device == "mps"

    def test_device_selection_manual(self):
        """Test manual device selection."""
        generator = ImageGenerator(device="cpu")
        assert generator.device == "cpu"

    def test_low_memory_flag(self):
        """Test low memory optimization flag."""
        generator = ImageGenerator(low_memory=True)
        assert generator.low_memory is True

        generator = ImageGenerator(low_memory=False)
        assert generator.low_memory is False

    def test_model_config(self):
        """Test different model configurations."""
        generator = ImageGenerator(model=ModelConfig.SD_1_5)
        assert generator.model_config == ModelConfig.SD_1_5

        generator = ImageGenerator(model=ModelConfig.SDXL_LOCAL)
        assert generator.model_config == ModelConfig.SDXL_LOCAL

    def test_build_prompt_creature(self, sample_card):
        """Test prompt building for creature cards."""
        generator = ImageGenerator()
        prompt = generator._build_prompt(sample_card, ArtStyle.FANTASY_REALISM)

        assert "Test Dragon" in prompt
        assert "powerful and imposing" in prompt  # power >= 5
        assert "fiery" in prompt  # RED color
        assert "with wings" in prompt  # has flying
        assert "in motion" in prompt  # has haste
        assert "fantasy realism" in prompt.lower()

    def test_build_prompt_noncreature(self):
        """Test prompt building for non-creature cards."""
        generator = ImageGenerator()
        card = Card(
            name="Lightning Bolt",
            card_type=CardType.INSTANT,
            mana_cost="R",
            color=Color.RED,
            text="Deal 3 damage to any target.",
        )

        prompt = generator._build_prompt(card, ArtStyle.DIGITAL_ART)

        assert "Lightning Bolt" in prompt
        assert "fiery" in prompt
        assert "digital art" in prompt.lower()

    def test_generate_with_custom_prompt(self, sample_card):
        """Test generation with custom prompt."""
        generator = ImageGenerator()
        generator.pipeline = MagicMock()

        custom_prompt = "A majestic dragon soaring through storm clouds"
        
        with patch.object(generator, "_save_image") as mock_save:
            mock_save.return_value = Path("test.png")
            with patch.object(generator, "_add_card_frame") as mock_frame:
                mock_frame.return_value = MagicMock()
                
                generator.generate_card_art(
                    sample_card, 
                    custom_prompt=custom_prompt
                )
                
        # Verify custom prompt was used
        generator.pipeline.assert_called_once()
        call_args = generator.pipeline.call_args
        assert custom_prompt in call_args[1]["prompt"]

    def test_build_prompt_colorless(self):
        """Test prompt building for colorless cards."""
        generator = ImageGenerator()
        card = Card(
            name="Sol Ring",
            card_type=CardType.ARTIFACT,
            mana_cost="1",
            color=Color.COLORLESS,
            text="Add two colorless mana.",
        )

        prompt = generator._build_prompt(card, ArtStyle.OIL_PAINTING)

        assert "Sol Ring" in prompt
        assert "metallic" in prompt
        assert "oil painting" in prompt.lower()

    def test_build_prompt_with_abilities(self):
        """Test prompt includes card abilities."""
        generator = ImageGenerator()
        card = Card(
            name="Death Angel",
            card_type=CardType.CREATURE,
            mana_cost="2BB",
            color=Color.BLACK,
            power=3,
            toughness=3,
            text="Flying, deathtouch, trample",
        )

        prompt = generator._build_prompt(card, ArtStyle.DARK_GOTHIC)

        assert "Death Angel" in prompt
        assert "with wings" in prompt  # flying
        assert "venomous" in prompt  # deathtouch
        assert "massive" in prompt  # trample
        assert "dark" in prompt.lower()  # color and style

    def test_save_image(self, tmp_output_dir, sample_card):
        """Test image saving functionality."""
        generator = ImageGenerator(output_dir=tmp_output_dir)

        # Create a dummy image
        test_image = Image.new("RGB", (512, 512), color="red")

        filepath = generator._save_image(test_image, sample_card)

        assert filepath.exists()
        assert filepath.suffix == ".png"
        assert "Test" in filepath.name and "Dragon" in filepath.name

        # Check metadata file
        metadata_path = filepath.with_suffix(".json")
        assert metadata_path.exists()

        # Load and verify metadata
        import json

        with open(metadata_path) as f:
            metadata = json.load(f)

        assert metadata["card_name"] == "Test Dragon"
        assert metadata["card_type"] == "Creature"
        assert "timestamp" in metadata
        assert "model" in metadata

    def test_add_card_frame(self, sample_card):
        """Test card frame addition (currently pass-through)."""
        generator = ImageGenerator()
        test_image = Image.new("RGB", (512, 512), color="blue")

        result = generator._add_card_frame(test_image, sample_card)

        assert result == test_image  # Currently just returns the image

    @patch("torch.cuda.is_available")
    @patch("torch.cuda.empty_cache")
    @patch("torch.cuda.ipc_collect")
    def test_clear_memory_cuda(self, mock_ipc, mock_empty, mock_available):
        """Test memory clearing on CUDA."""
        mock_available.return_value = True
        generator = ImageGenerator(device="cuda")
        generator.clear_memory()

        mock_empty.assert_called_once()
        mock_ipc.assert_called_once()

    def test_clear_memory_mps(self):
        """Test memory clearing on MPS (no-op)."""
        generator = ImageGenerator(device="mps")
        generator.clear_memory()  # Should not raise

    def test_unload_model(self):
        """Test model unloading."""
        generator = ImageGenerator()
        generator.pipeline = MagicMock()

        generator.unload_model()

        assert generator.pipeline is None

    def test_unload_model_no_pipeline(self):
        """Test unloading when no model loaded."""
        generator = ImageGenerator()
        generator.unload_model()  # Should not raise

    @patch("pathlib.Path.exists")
    def test_load_model_local_not_found(self, mock_exists):
        """Test error when local model not found."""
        mock_exists.return_value = False

        generator = ImageGenerator(model=ModelConfig.SDXL_LOCAL)

        with pytest.raises(FileNotFoundError):
            generator.load_model()

    def test_load_model_already_loaded(self):
        """Test that model is not reloaded if already loaded."""
        generator = ImageGenerator()
        generator.pipeline = MagicMock()

        with patch(
            "magic_tg_card_generator.image_generator.StableDiffusionPipeline"
        ) as mock_sd:
            generator.load_model()
            mock_sd.from_pretrained.assert_not_called()

    def test_generate_batch(self, sample_card):
        """Test batch generation."""
        generator = ImageGenerator()
        generator.pipeline = MagicMock()

        cards = [sample_card, sample_card]

        with patch.object(generator, "generate_card_art") as mock_generate:
            mock_generate.return_value = Path("test.png")
            paths = generator.generate_batch(cards)

        assert len(paths) == 2
        assert mock_generate.call_count == 2

    def test_generate_batch_with_error(self, sample_card):
        """Test batch generation continues on error."""
        generator = ImageGenerator()
        generator.pipeline = MagicMock()

        cards = [sample_card, sample_card]

        with patch.object(generator, "generate_card_art") as mock_generate:
            mock_generate.side_effect = [Exception("Error"), Path("test.png")]
            paths = generator.generate_batch(cards)

        assert len(paths) == 1
        assert mock_generate.call_count == 2
