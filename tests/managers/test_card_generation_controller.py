#!/usr/bin/env python3
"""
Comprehensive test suite for CardGenerationController.

This test suite verifies all functionality of the CardGenerationController class including:
- Generation queue management
- Progress tracking and reporting
- Error handling and recovery
- Signal emissions
- Worker thread coordination
- Batch processing
- Configuration management
- Statistics collection
- Validation logic

The tests use extensive mocking to isolate the controller from dependencies and ensure
that the refactoring maintains all expected functionality.
"""

import os
import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, PropertyMock, call, patch

import pytest
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtTest import QSignalSpy, QTest

# Qt imports for testing
from PyQt6.QtWidgets import QApplication, QMessageBox, QProgressBar, QWidget

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from managers.card_generation_controller import (
    CardGenerationController,
    GenerationConfig,
    GenerationMode,
    GenerationStatistics,
    GenerationWorker,
    Logger,
    ProgressReporter,
    StatusUpdater,
)

# Import MTGCard for testing
try:
    from mtg_deck_builder import MTGCard
except ImportError:
    # Create a mock MTGCard class for testing
    class MTGCard:
        def __init__(
            self,
            id=1,
            name="Test Card",
            type="Creature",
            cost="1R",
            text="Test text",
            power=2,
            toughness=2,
            rarity="common",
            art="Test art",
            status="pending",
            image_path=None,
            card_path=None,
            generated_at=None,
            flavor=None,
        ):
            self.id = id
            self.name = name
            self.type = type
            self.cost = cost
            self.text = text
            self.power = power
            self.toughness = toughness
            self.rarity = rarity
            self.art = art
            self.status = status
            self.image_path = image_path
            self.card_path = card_path
            self.generated_at = generated_at
            self.flavor = flavor


class MockLogger:
    """Mock logger for testing."""

    def __init__(self):
        self.messages = []

    def log_message(self, level: str, message: str) -> None:
        self.messages.append((level, message))


class MockProgressReporter:
    """Mock progress reporter for testing."""

    def __init__(self):
        self.progress_updates = []
        self.indeterminate_state = False

    def update_progress(self, current: int, total: int, message: str = "") -> None:
        self.progress_updates.append((current, total, message))

    def set_indeterminate(self, active: bool) -> None:
        self.indeterminate_state = active


class MockStatusUpdater:
    """Mock status updater for testing."""

    def __init__(self):
        self.status_updates = []
        self.display_refreshes = []

    def update_card_status(self, card: MTGCard, status: str) -> None:
        self.status_updates.append((card, status))

    def refresh_card_display(self, card: MTGCard) -> None:
        self.display_refreshes.append(card)


class MockGenerationWorker:
    """Mock generation worker for testing."""

    def __init__(self):
        self.is_running_value = False
        self.start_calls = []
        self.stop_calls = []

        # Mock Qt signals
        self.progress = Mock()
        self.completed = Mock()
        self.error = Mock()

    def start_generation(
        self, cards: list[MTGCard], generation_mode: str, **kwargs
    ) -> None:
        self.start_calls.append((cards, generation_mode, kwargs))
        self.is_running_value = True

    def stop_generation(self) -> None:
        self.stop_calls.append(True)
        self.is_running_value = False

    def is_running(self) -> bool:
        return self.is_running_value


class TestCardGenerationController(unittest.TestCase):
    """Test suite for CardGenerationController."""

    @classmethod
    def setUpClass(cls):
        """Set up QApplication for testing."""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        """Set up test fixtures."""
        # Create mock dependencies
        self.parent_widget = Mock(spec=QWidget)
        self.logger = MockLogger()
        self.progress_reporter = MockProgressReporter()
        self.status_updater = MockStatusUpdater()
        self.generation_worker = MockGenerationWorker()
        self.config = GenerationConfig()

        # Create test cards
        self.test_cards = [
            MTGCard(
                1, "Lightning Bolt", "Instant", "R", "Deal 3 damage", status="pending"
            ),
            MTGCard(
                2, "Grizzly Bears", "Creature", "1G", "A 2/2 bear", status="pending"
            ),
            MTGCard(
                3, "Black Lotus", "Artifact", "0", "Add 3 mana", status="completed"
            ),
            MTGCard(
                4, "Failed Card", "Sorcery", "2B", "This will fail", status="failed"
            ),
        ]

        # Create controller instance
        self.controller = CardGenerationController(
            parent_widget=self.parent_widget,
            logger=self.logger,
            progress_reporter=self.progress_reporter,
            status_updater=self.status_updater,
            generation_worker=self.generation_worker,
            config=self.config,
        )

    def tearDown(self):
        """Clean up after tests."""
        # Stop any active generation
        if self.controller.is_generation_active():
            self.controller.stop_generation()

    # Tests for Initialization

    def test_controller_initialization(self):
        """Test controller initializes correctly."""
        self.assertIsInstance(self.controller, CardGenerationController)
        self.assertEqual(self.controller.parent_widget, self.parent_widget)
        self.assertEqual(self.controller.logger, self.logger)
        self.assertEqual(self.controller.progress_reporter, self.progress_reporter)
        self.assertEqual(self.controller.status_updater, self.status_updater)
        self.assertEqual(self.controller.generation_worker, self.generation_worker)
        self.assertEqual(self.controller.config, self.config)

        # Check initial state
        self.assertFalse(self.controller.is_generation_active())
        self.assertEqual(self.controller.get_generation_queue_size(), 0)
        self.assertIsNone(self.controller.get_generation_mode())

    def test_initialization_with_defaults(self):
        """Test controller initialization with default parameters."""
        controller = CardGenerationController(self.parent_widget)

        self.assertIsNotNone(controller.config)
        self.assertIsInstance(controller.config, GenerationConfig)
        self.assertIsNotNone(controller.generation_worker)

    def test_default_worker_creation(self):
        """Test that default worker is created when none provided."""
        controller = CardGenerationController(
            parent_widget=self.parent_widget, generation_worker=None
        )

        self.assertIsNotNone(controller.generation_worker)
        # Test default worker methods
        controller.generation_worker.start_generation([], "test")
        controller.generation_worker.stop_generation()
        self.assertFalse(controller.generation_worker.is_running())

    # Tests for Generation Control

    def test_start_generation_success(self):
        """Test successful generation start."""
        cards = self.test_cards[:2]  # Use pending cards

        result = self.controller.start_generation(cards, GenerationMode.COMPLETE)

        self.assertTrue(result)
        self.assertTrue(self.controller.is_generation_active())
        self.assertEqual(self.controller.get_generation_mode(), GenerationMode.COMPLETE)
        self.assertEqual(self.controller.get_generation_queue_size(), 2)

        # Check worker was called
        self.assertEqual(len(self.generation_worker.start_calls), 1)
        called_cards, called_mode, called_kwargs = self.generation_worker.start_calls[0]
        self.assertEqual(len(called_cards), 2)
        self.assertEqual(called_mode, GenerationMode.COMPLETE.value)

        # Check progress reporter was set to indeterminate
        self.assertTrue(self.progress_reporter.indeterminate_state)

        # Check log messages
        log_messages = [msg[1] for msg in self.logger.messages]
        self.assertTrue(
            any("Started complete generation" in msg for msg in log_messages)
        )

    def test_start_generation_already_active(self):
        """Test starting generation when already active."""
        # Start first generation
        self.controller.start_generation(self.test_cards[:1], GenerationMode.COMPLETE)

        # Try to start another
        result = self.controller.start_generation(
            self.test_cards[1:2], GenerationMode.CARDS_ONLY
        )

        self.assertFalse(result)
        # Should still be in original generation mode
        self.assertEqual(self.controller.get_generation_mode(), GenerationMode.COMPLETE)

    def test_start_generation_no_cards(self):
        """Test starting generation with empty card list."""
        result = self.controller.start_generation([], GenerationMode.COMPLETE)

        self.assertFalse(result)
        self.assertFalse(self.controller.is_generation_active())

    def test_start_generation_validation_failure(self):
        """Test generation start with card validation failure."""
        # Create invalid cards
        invalid_cards = [
            MTGCard(1, "", "Invalid", "X", "No name", status="pending"),  # Missing name
        ]

        result = self.controller.start_generation(
            invalid_cards, GenerationMode.COMPLETE
        )

        self.assertFalse(result)
        self.assertFalse(self.controller.is_generation_active())

    @patch("managers.card_generation_controller.QMessageBox.critical")
    def test_start_generation_exception(self, mock_message_box):
        """Test generation start with exception."""
        # Make worker throw exception
        self.generation_worker.start_generation = Mock(
            side_effect=Exception("Test error")
        )

        result = self.controller.start_generation(
            self.test_cards[:1], GenerationMode.COMPLETE
        )

        self.assertFalse(result)
        self.assertFalse(self.controller.is_generation_active())

        # Check error was logged
        error_messages = [
            msg for level, msg in self.logger.messages if level == "ERROR"
        ]
        self.assertTrue(
            any("Generation startup failed" in msg for msg in error_messages)
        )

    def test_stop_generation_success(self):
        """Test successful generation stop."""
        # Start generation
        self.controller.start_generation(self.test_cards[:2], GenerationMode.COMPLETE)

        result = self.controller.stop_generation()

        self.assertTrue(result)
        self.assertFalse(self.controller.is_generation_active())
        self.assertIsNone(self.controller.get_generation_mode())
        self.assertEqual(self.controller.get_generation_queue_size(), 0)

        # Check worker was stopped
        self.assertEqual(len(self.generation_worker.stop_calls), 1)

        # Check progress reporter was reset
        self.assertFalse(self.progress_reporter.indeterminate_state)

    def test_stop_generation_not_active(self):
        """Test stopping generation when not active."""
        result = self.controller.stop_generation()

        self.assertFalse(result)

        # Check warning was logged
        warning_messages = [
            msg for level, msg in self.logger.messages if level == "WARNING"
        ]
        self.assertTrue(
            any("No active generation to stop" in msg for msg in warning_messages)
        )

    def test_pause_resume_generation(self):
        """Test pausing and resuming generation."""
        # Start generation
        self.controller.start_generation(self.test_cards[:2], GenerationMode.COMPLETE)

        # Pause
        pause_result = self.controller.pause_generation()
        self.assertTrue(pause_result)

        # Resume
        resume_result = self.controller.resume_generation()
        self.assertTrue(resume_result)

        # Try to pause when not active
        self.controller.stop_generation()
        pause_result = self.controller.pause_generation()
        self.assertFalse(pause_result)

    # Tests for Signal Emissions

    def test_generation_signals_emitted(self):
        """Test that appropriate signals are emitted during generation."""
        # Create signal spies
        generation_started_spy = QSignalSpy(self.controller.generation_started)
        generation_progress_spy = QSignalSpy(self.controller.generation_progress)
        card_status_changed_spy = QSignalSpy(self.controller.card_status_changed)

        cards = self.test_cards[:2]

        # Start generation
        self.controller.start_generation(cards, GenerationMode.COMPLETE)

        # Check generation started signal
        self.assertEqual(len(generation_started_spy), 1)
        signal_args = generation_started_spy[0]
        self.assertEqual(signal_args[0], 2)  # card count
        self.assertEqual(signal_args[1], GenerationMode.COMPLETE.value)  # mode

        # Simulate worker progress
        self.controller._on_worker_progress(1, 2, "Processing card")

        # Check progress signal
        self.assertEqual(len(generation_progress_spy), 1)
        progress_args = generation_progress_spy[0]
        self.assertEqual(progress_args[0], 1)  # current
        self.assertEqual(progress_args[1], 2)  # total
        self.assertEqual(progress_args[2], "Processing card")  # message

    def test_error_signal_emission(self):
        """Test error signal emission."""
        error_occurred_spy = QSignalSpy(self.controller.error_occurred)

        # Trigger an error through the controller's error method
        self.controller._show_error("Test Error", "This is a test error")

        # Check error signal was emitted
        self.assertEqual(len(error_occurred_spy), 1)
        error_args = error_occurred_spy[0]
        self.assertEqual(error_args[0], "Test Error")
        self.assertEqual(error_args[1], "This is a test error")

    # Tests for Worker Event Handling

    def test_worker_progress_handling(self):
        """Test handling of worker progress events."""
        self.controller._on_worker_progress(5, 10, "Generating card")

        # Check progress was updated
        self.assertEqual(len(self.progress_reporter.progress_updates), 1)
        current, total, message = self.progress_reporter.progress_updates[0]
        self.assertEqual(current, 5)
        self.assertEqual(total, 10)
        self.assertEqual(message, "Generating card")

    def test_worker_completion_handling(self):
        """Test handling of worker completion events."""
        # Start generation
        cards = self.test_cards[:2]
        self.controller.start_generation(cards, GenerationMode.COMPLETE)

        # Clear previous status updates from start
        self.status_updater.status_updates.clear()

        # Simulate worker completion
        results = [
            (cards[0], True, "Success"),  # Successful generation
            (cards[1], False, "Failed"),  # Failed generation
        ]

        generation_completed_spy = QSignalSpy(self.controller.generation_completed)

        self.controller._on_worker_completed(results)

        # Check generation is no longer active
        self.assertFalse(self.controller.is_generation_active())

        # Check completion signal was emitted
        self.assertEqual(len(generation_completed_spy), 1)

        # Check status updates (should be 2: one for each card result)
        self.assertEqual(len(self.status_updater.status_updates), 2)

        # Check final card statuses directly
        self.assertEqual(cards[0].status, "completed")
        self.assertEqual(cards[1].status, "failed")

    def test_worker_error_handling(self):
        """Test handling of worker error events."""
        error_message = "Worker encountered an error"

        # Need to start generation first to have active statistics
        self.controller.start_generation(self.test_cards[:1], GenerationMode.COMPLETE)

        self.controller._on_worker_error(error_message)

        # Check error was logged
        error_messages = [
            msg for level, msg in self.logger.messages if level == "ERROR"
        ]
        self.assertTrue(any(error_message in msg for msg in error_messages))

        # Check error was added to current statistics
        self.assertIn(error_message, self.controller._current_statistics.errors)

    # Tests for Statistics and Status Management

    def test_generation_statistics(self):
        """Test generation statistics calculation."""
        # Test with no active generation - controller counts cards by their status
        stats = self.controller.get_generation_statistics(self.test_cards)

        # Count expected cards by status
        pending_count = sum(1 for card in self.test_cards if card.status == "pending")
        completed_count = sum(
            1 for card in self.test_cards if card.status == "completed"
        )
        failed_count = sum(1 for card in self.test_cards if card.status == "failed")

        self.assertEqual(stats["total_cards"], len(self.test_cards))
        self.assertEqual(stats["pending_cards"], pending_count)
        self.assertEqual(stats["completed_cards"], completed_count)
        self.assertEqual(stats["failed_cards"], failed_count)

        # Test during active generation
        self.controller.start_generation(self.test_cards[:2], GenerationMode.COMPLETE)
        active_stats = self.controller.get_generation_statistics()
        self.assertEqual(active_stats["total_cards"], 2)

    def test_statistics_calculations(self):
        """Test statistics calculation methods."""
        stats = GenerationStatistics()
        stats.total_cards = 10
        stats.completed_cards = 7
        stats.failed_cards = 2
        stats.start_time = datetime(2023, 1, 1, 10, 0, 0)
        stats.end_time = datetime(2023, 1, 1, 10, 5, 0)

        self.assertEqual(stats.completion_rate, 70.0)
        self.assertEqual(stats.failure_rate, 20.0)
        self.assertEqual(stats.duration_seconds, 300.0)

        # Test to_dict conversion
        stats_dict = stats.to_dict()
        self.assertEqual(stats_dict["completion_rate"], 70.0)
        self.assertIn("start_time", stats_dict)

    def test_card_status_filtering(self):
        """Test filtering cards by status."""
        pending_cards = self.controller.get_pending_cards(self.test_cards)
        self.assertEqual(len(pending_cards), 2)
        self.assertTrue(all(card.status == "pending" for card in pending_cards))

        completed_cards = self.controller.get_completed_cards(self.test_cards)
        self.assertEqual(len(completed_cards), 1)
        self.assertEqual(completed_cards[0].name, "Black Lotus")

        failed_cards = self.controller.get_failed_cards(self.test_cards)
        self.assertEqual(len(failed_cards), 1)
        self.assertEqual(failed_cards[0].name, "Failed Card")

        generating_cards = self.controller.get_generating_cards(self.test_cards)
        self.assertEqual(len(generating_cards), 0)

    def test_card_status_updates(self):
        """Test card status update functionality."""
        card = self.test_cards[0]
        original_status = card.status

        # Update status
        self.controller._update_card_status(card, "generating")

        self.assertEqual(card.status, "generating")
        self.assertIn((card, "generating"), self.status_updater.status_updates)
        self.assertIn(card, self.status_updater.display_refreshes)

        # Update to completed
        self.controller._update_card_status(card, "completed")
        self.assertEqual(card.status, "completed")
        self.assertIsNotNone(card.generated_at)

    # Tests for Validation

    def test_card_validation(self):
        """Test card validation for generation."""
        # Valid cards
        valid_cards = self.test_cards[:2]
        issues = self.controller.validate_cards_for_generation(valid_cards)
        self.assertEqual(len(issues), 0)

        # Invalid cards
        invalid_cards = [
            MTGCard(1, "", "Creature", "1G", "No name"),  # Missing name
            MTGCard(2, "Valid Name", "", "1R", "No type"),  # Missing type
            MTGCard(3, "Long Text", "Creature", "1B", "x" * 1001),  # Text too long
        ]

        issues = self.controller.validate_cards_for_generation(invalid_cards)
        self.assertGreater(len(issues), 0)
        self.assertTrue(any("Missing name" in issue for issue in issues))
        self.assertTrue(any("Missing type" in issue for issue in issues))
        self.assertTrue(any("Text too long" in issue for issue in issues))

        # Test AI art descriptions validation
        self.controller.config.ai_art_descriptions = True
        cards_no_art = [MTGCard(1, "Test", "Creature", "1G", "Test", art="")]
        issues = self.controller.validate_cards_for_generation(cards_no_art)
        self.assertTrue(any("Missing art description" in issue for issue in issues))

    def test_environment_validation(self):
        """Test generation environment validation."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False

            with patch("pathlib.Path.mkdir") as mock_mkdir:
                issues = self.controller.validate_generation_environment()

                # Should try to create directory
                mock_mkdir.assert_called_once()

                # Check for missing scripts
                self.assertTrue(
                    any("Generation script not found" in issue for issue in issues)
                )

    # Tests for Batch Operations

    def test_generate_missing_cards(self):
        """Test generating only missing/pending cards."""
        result = self.controller.generate_missing_cards(self.test_cards)

        self.assertTrue(result)
        self.assertTrue(self.controller.is_generation_active())
        self.assertEqual(
            self.controller.get_generation_mode(), GenerationMode.MISSING_ONLY
        )

        # Should only include pending cards
        self.assertEqual(self.controller.get_generation_queue_size(), 2)

    def test_generate_missing_cards_none_missing(self):
        """Test generating missing cards when none are missing."""
        # All cards completed
        completed_cards = [card for card in self.test_cards]
        for card in completed_cards:
            card.status = "completed"

        result = self.controller.generate_missing_cards(completed_cards)
        self.assertFalse(result)

    def test_generate_failed_cards(self):
        """Test retrying failed cards."""
        result = self.controller.generate_failed_cards(self.test_cards)

        self.assertTrue(result)
        self.assertEqual(
            self.controller.get_generation_mode(), GenerationMode.REGENERATE
        )

        # Should have reset failed card to pending
        failed_card = next(
            card for card in self.test_cards if card.name == "Failed Card"
        )
        self.assertEqual(failed_card.status, "pending")

    def test_generate_failed_cards_none_failed(self):
        """Test generating failed cards when none have failed."""
        # No failed cards
        no_failed_cards = [card for card in self.test_cards if card.status != "failed"]

        result = self.controller.generate_failed_cards(no_failed_cards)
        self.assertFalse(result)

    def test_regenerate_selected_cards(self):
        """Test regenerating specific cards."""
        selected_cards = self.test_cards[:2]

        result = self.controller.regenerate_selected_cards(selected_cards)

        self.assertTrue(result)
        self.assertEqual(
            self.controller.get_generation_mode(), GenerationMode.REGENERATE
        )

        # Should have reset cards to pending
        for card in selected_cards:
            self.assertEqual(card.status, "pending")

    def test_regenerate_selected_cards_empty(self):
        """Test regenerating with empty selection."""
        result = self.controller.regenerate_selected_cards([])
        self.assertFalse(result)

    def test_generate_art_descriptions(self):
        """Test generating AI art descriptions."""
        # Create cards needing art
        cards_need_art = [
            MTGCard(1, "Card 1", "Creature", "1G", "Test", art=""),
            MTGCard(2, "Card 2", "Instant", "1R", "Test", art="Existing art"),
        ]

        result = self.controller.generate_art_descriptions(cards_need_art)

        self.assertTrue(result)
        self.assertEqual(
            self.controller.get_generation_mode(), GenerationMode.ART_DESCRIPTIONS
        )
        self.assertEqual(
            self.controller.get_generation_queue_size(), 1
        )  # Only card without art

    def test_generate_art_descriptions_none_needed(self):
        """Test generating art descriptions when none needed."""
        # All cards have art
        cards_with_art = [MTGCard(1, "Test", "Creature", "1G", "Test", art="Has art")]

        result = self.controller.generate_art_descriptions(cards_with_art)
        self.assertFalse(result)

    # Tests for Configuration

    def test_config_update(self):
        """Test updating generation configuration."""
        new_config = GenerationConfig(batch_size=20, concurrent_workers=4)

        self.controller.update_config(new_config)

        self.assertEqual(self.controller.get_config(), new_config)
        self.assertEqual(self.controller.config.batch_size, 20)
        self.assertEqual(self.controller.config.concurrent_workers, 4)

        # Check log message
        log_messages = [msg[1] for msg in self.logger.messages]
        self.assertTrue(any("configuration updated" in msg for msg in log_messages))

    # Tests for Batch Processing

    @patch("managers.card_generation_controller.QTimer")
    def test_batch_processing_setup(self, mock_timer_class):
        """Test batch processing timer setup."""
        mock_timer = Mock()
        mock_timer_class.return_value = mock_timer

        controller = CardGenerationController(self.parent_widget)

        # Timer should be created and configured
        mock_timer_class.assert_called_once()
        mock_timer.timeout.connect.assert_called_once()
        mock_timer.setSingleShot.assert_called_once_with(False)

    def test_single_card_generation_methods(self):
        """Test individual card generation methods."""
        card = self.test_cards[0]

        # Test card image generation
        with patch.object(
            self.controller, "_generate_card_image", return_value=True
        ) as mock_card:
            with patch.object(
                self.controller, "_generate_artwork_image", return_value=True
            ) as mock_artwork:
                # Test different generation modes
                self.controller._current_generation = GenerationMode.CARDS_ONLY
                result = self.controller._generate_single_card(card)
                self.assertTrue(result)
                mock_card.assert_called_once_with(card)
                mock_artwork.assert_not_called()

                mock_card.reset_mock()
                mock_artwork.reset_mock()

                self.controller._current_generation = GenerationMode.ARTWORK_ONLY
                result = self.controller._generate_single_card(card)
                self.assertTrue(result)
                mock_card.assert_not_called()
                mock_artwork.assert_called_once_with(card)

                mock_card.reset_mock()
                mock_artwork.reset_mock()

                self.controller._current_generation = GenerationMode.COMPLETE
                result = self.controller._generate_single_card(card)
                self.assertTrue(result)
                mock_card.assert_called_once_with(card)
                mock_artwork.assert_called_once_with(card)

    # Tests for Context Manager

    def test_context_manager(self):
        """Test context manager functionality."""
        with self.controller as controller:
            self.assertEqual(controller, self.controller)

            # Start generation inside context
            controller.start_generation(self.test_cards[:1], GenerationMode.COMPLETE)
            self.assertTrue(controller.is_generation_active())

        # Should have stopped generation on exit
        self.assertFalse(self.controller.is_generation_active())
        self.assertEqual(self.controller.get_generation_queue_size(), 0)

    def test_context_manager_exception_handling(self):
        """Test context manager handles exceptions properly."""
        try:
            with self.controller as controller:
                controller.start_generation(
                    self.test_cards[:1], GenerationMode.COMPLETE
                )
                raise Exception("Test exception")
        except Exception:
            pass

        # Should still have cleaned up
        self.assertFalse(self.controller.is_generation_active())

    # Tests for Error Handling

    def test_error_handling_with_mock_parent(self):
        """Test error handling when parent widget is mock/None."""
        self.controller._show_error("Test Error", "Test Message")

        # Should have emitted signal
        # Should have logged error
        error_messages = [
            msg for level, msg in self.logger.messages if level == "ERROR"
        ]
        self.assertTrue(
            any("Test Error: Test Message" in msg for msg in error_messages)
        )

    def test_warning_handling_with_mock_parent(self):
        """Test warning handling when parent widget is mock/None."""
        self.controller._show_warning("Test Warning", "Test Message")

        # Should have logged warning
        warning_messages = [
            msg for level, msg in self.logger.messages if level == "WARNING"
        ]
        self.assertTrue(
            any("Test Warning: Test Message" in msg for msg in warning_messages)
        )

    # Tests for Internal State Management

    def test_statistics_status_change_updates(self):
        """Test that statistics are updated correctly when card status changes."""
        # Start with fresh statistics
        self.controller._current_statistics = GenerationStatistics()
        self.controller._current_statistics.total_cards = 1
        self.controller._current_statistics.pending_cards = 1

        # Simulate status change from pending to generating
        self.controller._update_statistics_for_status_change("pending", "generating")

        self.assertEqual(self.controller._current_statistics.pending_cards, 0)
        self.assertEqual(self.controller._current_statistics.generating_cards, 1)

        # Change from generating to completed
        self.controller._update_statistics_for_status_change("generating", "completed")

        self.assertEqual(self.controller._current_statistics.generating_cards, 0)
        self.assertEqual(self.controller._current_statistics.completed_cards, 1)

        # Change from completed to failed (edge case)
        self.controller._update_statistics_for_status_change("completed", "failed")

        self.assertEqual(self.controller._current_statistics.completed_cards, 0)
        self.assertEqual(self.controller._current_statistics.failed_cards, 1)

    def test_logging_functionality(self):
        """Test internal logging functionality."""
        self.controller._log("INFO", "Test info message")
        self.controller._log("ERROR", "Test error message")
        self.controller._log("DEBUG", "Test debug message")

        # Check messages were logged
        messages = [msg[1] for msg in self.logger.messages]
        self.assertIn("Test info message", messages)
        self.assertIn("Test error message", messages)
        self.assertIn("Test debug message", messages)

        # Check log levels
        levels = [level for level, msg in self.logger.messages]
        self.assertIn("INFO", levels)
        self.assertIn("ERROR", levels)
        self.assertIn("DEBUG", levels)


class TestGenerationMode(unittest.TestCase):
    """Test GenerationMode enum."""

    def test_generation_mode_values(self):
        """Test that all generation modes have correct values."""
        self.assertEqual(GenerationMode.CARDS_ONLY.value, "cards_only")
        self.assertEqual(GenerationMode.ARTWORK_ONLY.value, "artwork_only")
        self.assertEqual(GenerationMode.COMPLETE.value, "complete")
        self.assertEqual(GenerationMode.ART_DESCRIPTIONS.value, "art_descriptions")
        self.assertEqual(GenerationMode.MISSING_ONLY.value, "missing_only")
        self.assertEqual(GenerationMode.REGENERATE.value, "regenerate")


class TestGenerationConfig(unittest.TestCase):
    """Test GenerationConfig class."""

    def test_config_defaults(self):
        """Test configuration default values."""
        config = GenerationConfig()

        self.assertEqual(config.output_directory, Path("saved_decks"))
        self.assertEqual(config.concurrent_workers, 1)
        self.assertEqual(config.retry_attempts, 3)
        self.assertEqual(config.timeout_seconds, 300)
        self.assertTrue(config.generate_images)
        self.assertTrue(config.generate_artwork)
        self.assertTrue(config.use_existing_artwork)
        self.assertFalse(config.ai_art_descriptions)
        self.assertEqual(config.batch_size, 10)

    def test_config_custom_values(self):
        """Test configuration with custom values."""
        custom_dir = Path("/custom/output")
        config = GenerationConfig(
            output_directory=custom_dir,
            concurrent_workers=4,
            retry_attempts=5,
            timeout_seconds=600,
            generate_images=False,
            generate_artwork=False,
            use_existing_artwork=False,
            ai_art_descriptions=True,
            batch_size=20,
        )

        self.assertEqual(config.output_directory, custom_dir)
        self.assertEqual(config.concurrent_workers, 4)
        self.assertEqual(config.retry_attempts, 5)
        self.assertEqual(config.timeout_seconds, 600)
        self.assertFalse(config.generate_images)
        self.assertFalse(config.generate_artwork)
        self.assertFalse(config.use_existing_artwork)
        self.assertTrue(config.ai_art_descriptions)
        self.assertEqual(config.batch_size, 20)


class TestGenerationStatistics(unittest.TestCase):
    """Test GenerationStatistics class."""

    def test_statistics_initialization(self):
        """Test statistics initialization."""
        stats = GenerationStatistics()

        self.assertEqual(stats.total_cards, 0)
        self.assertEqual(stats.pending_cards, 0)
        self.assertEqual(stats.generating_cards, 0)
        self.assertEqual(stats.completed_cards, 0)
        self.assertEqual(stats.failed_cards, 0)
        self.assertIsNone(stats.start_time)
        self.assertIsNone(stats.end_time)
        self.assertEqual(stats.errors, [])

    def test_statistics_rate_calculations(self):
        """Test completion and failure rate calculations."""
        stats = GenerationStatistics()

        # Test with zero total
        self.assertEqual(stats.completion_rate, 0.0)
        self.assertEqual(stats.failure_rate, 0.0)

        # Test with actual values
        stats.total_cards = 100
        stats.completed_cards = 85
        stats.failed_cards = 10

        self.assertEqual(stats.completion_rate, 85.0)
        self.assertEqual(stats.failure_rate, 10.0)

    def test_statistics_duration_calculation(self):
        """Test duration calculation."""
        stats = GenerationStatistics()

        # Test with no start time
        self.assertEqual(stats.duration_seconds, 0.0)

        # Test with start time only
        stats.start_time = datetime.now()
        duration = stats.duration_seconds
        self.assertGreaterEqual(duration, 0.0)

        # Test with both start and end time
        stats.start_time = datetime(2023, 1, 1, 10, 0, 0)
        stats.end_time = datetime(2023, 1, 1, 10, 5, 30)
        self.assertEqual(stats.duration_seconds, 330.0)  # 5 minutes 30 seconds

    def test_statistics_to_dict(self):
        """Test statistics dictionary conversion."""
        stats = GenerationStatistics()
        stats.total_cards = 10
        stats.completed_cards = 8
        stats.failed_cards = 1
        stats.start_time = datetime(2023, 1, 1, 10, 0, 0)
        stats.end_time = datetime(2023, 1, 1, 10, 5, 0)
        stats.errors = ["Error 1", "Error 2"]

        stats_dict = stats.to_dict()

        # Check all fields are present
        expected_fields = [
            "total_cards",
            "pending_cards",
            "generating_cards",
            "completed_cards",
            "failed_cards",
            "completion_rate",
            "failure_rate",
            "duration_seconds",
            "start_time",
            "end_time",
            "errors",
        ]

        for field in expected_fields:
            self.assertIn(field, stats_dict)

        # Check calculated values
        self.assertEqual(stats_dict["completion_rate"], 80.0)
        self.assertEqual(stats_dict["failure_rate"], 10.0)
        self.assertEqual(stats_dict["duration_seconds"], 300.0)

        # Check datetime serialization
        self.assertEqual(stats_dict["start_time"], "2023-01-01T10:00:00")
        self.assertEqual(stats_dict["end_time"], "2023-01-01T10:05:00")

        # Check errors
        self.assertEqual(stats_dict["errors"], ["Error 1", "Error 2"])


if __name__ == "__main__":
    # Set up test discovery and execution
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestCardGenerationController))
    suite.addTests(loader.loadTestsFromTestCase(TestGenerationMode))
    suite.addTests(loader.loadTestsFromTestCase(TestGenerationConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestGenerationStatistics))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
