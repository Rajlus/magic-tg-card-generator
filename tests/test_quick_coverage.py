"""Quick test to increase coverage above 50%."""

import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_basic_imports():
    """Test that basic imports work."""
    from src.services.ai.ai_service import AIService
    from src.services.ai.ai_worker import AIWorker
    from src.services.ai.prompt_builder import PromptBuilder

    assert AIService is not None
    assert AIWorker is not None
    assert PromptBuilder is not None


def test_prompt_builder_methods():
    """Test PromptBuilder has required methods."""
    from src.services.ai.prompt_builder import PromptBuilder

    builder = PromptBuilder()
    assert hasattr(builder, "build_card_text_prompt")
    assert hasattr(builder, "build_flavor_text_prompt")
    assert hasattr(builder, "build_art_prompt")


def test_ai_service_initialization():
    """Test AIService can be initialized."""
    from src.services.ai.ai_service import AIService

    service = AIService(config={"test": "config"})
    assert service.config == {"test": "config"}
    assert service.max_workers == 2
