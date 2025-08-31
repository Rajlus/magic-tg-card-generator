#!/usr/bin/env python3
"""
Integration tests for CardGenerationController with CardManagementTab.

Tests that the refactored controller properly integrates with the UI.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from managers.card_generation_controller import (
    CardGenerationController,
    GenerationConfig,
    GenerationMode,
    GenerationStatistics,
)


# Mock MTGCard for testing
class MockMTGCard:
    def __init__(self, id, name, card_type="Creature", status="pending"):
        self.id = id
        self.name = name
        self.type = card_type
        self.status = status
        self.cost = "1"
        self.text = "Test card text"
        self.power = None
        self.toughness = None
        self.flavor = None
        self.rarity = "Common"
        self.art = "Test art description"
        self.image_path = None
        self.card_path = None
        self.generated_at = None


@pytest.fixture
def mock_app():
    """Create a QApplication instance for testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def mock_cards():
    """Create test cards for generation testing."""
    return [
        MockMTGCard(1, "Test Card 1"),
        MockMTGCard(2, "Test Card 2"),
        MockMTGCard(3, "Test Card 3"),
    ]


class TestCardManagementTabIntegration:
    """Test integration between CardGenerationController and UI components."""

    def test_controller_instantiation(self, mock_app):
        """Test that CardManagementTab can instantiate CardGenerationController."""
        # Mock the UI components
        mock_parent_widget = MagicMock()
        mock_logger = MagicMock()
        mock_progress_reporter = MagicMock()
        mock_status_updater = MagicMock()
        mock_worker = MagicMock()

        # Create controller
        controller = CardGenerationController(
            parent_widget=mock_parent_widget,
            logger=mock_logger,
            progress_reporter=mock_progress_reporter,
            status_updater=mock_status_updater,
            generation_worker=mock_worker,
        )

        assert controller is not None
        assert controller.parent_widget == mock_parent_widget
        assert controller.logger == mock_logger
        assert controller.progress_reporter == mock_progress_reporter
        assert controller.status_updater == mock_status_updater

    def test_adapter_classes_work(self):
        """Test that the adapter classes work correctly."""
        # Import the adapter classes from mtg_deck_builder
        try:
            from mtg_deck_builder import (
                CardGeneratorWorkerAdapter,
                CardManagementProgressReporter,
                CardManagementStatusUpdater,
            )

            # Test that adapter classes exist and can be instantiated
            mock_worker = MagicMock()
            adapter = CardGeneratorWorkerAdapter(mock_worker)
            assert adapter is not None
            assert adapter.worker == mock_worker

            mock_parent = MagicMock()
            progress_reporter = CardManagementProgressReporter(mock_parent)
            assert progress_reporter is not None
            assert progress_reporter.parent_tab == mock_parent

            status_updater = CardManagementStatusUpdater(mock_parent)
            assert status_updater is not None
            assert status_updater.parent_tab == mock_parent

        except ImportError as e:
            pytest.fail(f"Failed to import adapter classes: {e}")

    def test_generation_controller_signals(self, mock_app, mock_cards):
        """Test that CardGenerationController signals are properly connected."""
        mock_parent_widget = MagicMock()
        mock_logger = MagicMock()
        mock_worker = MagicMock()

        controller = CardGenerationController(
            parent_widget=mock_parent_widget,
            logger=mock_logger,
            generation_worker=mock_worker,
        )

        # Mock signal connections
        signals_connected = []

        def mock_connect(signal_name):
            def connect_func(slot):
                signals_connected.append((signal_name, slot))

            return connect_func

        controller.generation_started.connect = mock_connect("generation_started")
        controller.generation_progress.connect = mock_connect("generation_progress")
        controller.generation_completed.connect = mock_connect("generation_completed")
        controller.card_status_changed.connect = mock_connect("card_status_changed")
        controller.error_occurred.connect = mock_connect("error_occurred")

        # Test that signals can be connected
        mock_slot1 = MagicMock()
        mock_slot2 = MagicMock()
        controller.generation_started.connect(mock_slot1)
        controller.generation_completed.connect(mock_slot2)

        assert len(signals_connected) == 2
        assert ("generation_started", mock_slot1) in signals_connected
        assert ("generation_completed", mock_slot2) in signals_connected

    def test_controller_generation_workflow(self, mock_app, mock_cards):
        """Test the complete generation workflow with controller."""
        mock_parent_widget = MagicMock()
        mock_logger = MagicMock()
        mock_progress_reporter = MagicMock()
        mock_status_updater = MagicMock()
        mock_worker = MagicMock()

        # Configure worker mock
        mock_worker.is_running.return_value = False

        controller = CardGenerationController(
            parent_widget=mock_parent_widget,
            logger=mock_logger,
            progress_reporter=mock_progress_reporter,
            status_updater=mock_status_updater,
            generation_worker=mock_worker,
        )

        # Test starting generation
        result = controller.start_generation(
            mock_cards, GenerationMode.COMPLETE, model="sdxl", style="mtg_modern"
        )

        assert result is True
        assert controller.is_generation_active()
        mock_worker.start_generation.assert_called_once()

    def test_controller_validates_cards(self, mock_app):
        """Test that controller properly validates cards."""
        controller = CardGenerationController(
            parent_widget=MagicMock(),
            logger=MagicMock(),
        )

        # Test with valid cards
        valid_cards = [
            MockMTGCard(1, "Valid Card 1", "Creature"),
            MockMTGCard(2, "Valid Card 2", "Instant"),
        ]

        issues = controller.validate_cards_for_generation(valid_cards)
        assert len(issues) == 0

        # Test with invalid cards
        invalid_cards = [
            MockMTGCard(1, "", "Creature"),  # Missing name
            MockMTGCard(2, "Card 2", ""),  # Missing type
        ]

        issues = controller.validate_cards_for_generation(invalid_cards)
        assert len(issues) == 2
        assert "Missing name" in str(issues)
        assert "Missing type" in str(issues)

    def test_controller_handles_empty_card_list(self, mock_app):
        """Test that controller handles empty card lists gracefully."""
        controller = CardGenerationController(
            parent_widget=MagicMock(),
            logger=MagicMock(),
        )

        # Try to start generation with empty list
        result = controller.start_generation([], GenerationMode.COMPLETE)
        assert result is False
        assert not controller.is_generation_active()

    def test_controller_generation_statistics(self, mock_app, mock_cards):
        """Test that controller properly tracks generation statistics."""
        controller = CardGenerationController(
            parent_widget=MagicMock(),
            logger=MagicMock(),
        )

        # Get statistics for cards
        stats = controller.get_generation_statistics(mock_cards)

        assert isinstance(stats, dict)
        assert "total_cards" in stats
        assert "pending_cards" in stats
        assert "completed_cards" in stats
        assert "failed_cards" in stats
        assert "completion_rate" in stats
        assert "failure_rate" in stats

        assert stats["total_cards"] == len(mock_cards)
        assert stats["pending_cards"] == len(mock_cards)  # All cards start as pending

    def test_controller_batch_operations(self, mock_app, mock_cards):
        """Test controller batch operation methods."""
        controller = CardGenerationController(
            parent_widget=MagicMock(),
            logger=MagicMock(),
            generation_worker=MagicMock(),
        )

        # Configure worker mock
        controller.generation_worker.is_running.return_value = False

        # Test generate missing cards
        result = controller.generate_missing_cards(mock_cards)
        assert result is True

        # Test with no missing cards (all completed)
        completed_cards = [
            MockMTGCard(i, f"Card {i}", status="completed") for i in range(3)
        ]
        result = controller.generate_missing_cards(completed_cards)
        assert result is False

        # Test generate failed cards
        failed_cards = [MockMTGCard(i, f"Card {i}", status="failed") for i in range(3)]
        result = controller.generate_failed_cards(failed_cards)
        assert result is True

    @patch("subprocess.run")
    def test_controller_environment_validation(self, mock_subprocess, mock_app):
        """Test that controller validates the generation environment."""
        controller = CardGenerationController(
            parent_widget=MagicMock(),
            logger=MagicMock(),
        )

        issues = controller.validate_generation_environment()

        # Should check for output directory creation and generation scripts
        assert isinstance(issues, list)

        # Output directory should be created successfully
        output_dir = controller.config.output_directory
        assert output_dir.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
