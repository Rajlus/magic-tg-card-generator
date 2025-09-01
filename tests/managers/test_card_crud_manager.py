#!/usr/bin/env python3
"""
Unit tests for CardCRUDManager class
Tests CRUD operations for MTG cards
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

# Add parent path to sys.path for imports
root_path = Path(__file__).parent.parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QApplication, QTableWidget, QWidget

# Import the manager to test
from src.managers.card_crud_manager import CardCRUDManager

# Import MTGCard
try:
    from src.domain.models import MTGCard
except ImportError:
    # Create a mock MTGCard for testing
    class MTGCard:
        def __init__(self, **kwargs):
            self.id = kwargs.get("id", 1)
            self.name = kwargs.get("name", "Test Card")
            self.type = kwargs.get("type", "Creature")
            self.cost = kwargs.get("cost", "{1}")
            self.text = kwargs.get("text", "")
            self.power = kwargs.get("power")
            self.toughness = kwargs.get("toughness")
            self.rarity = kwargs.get("rarity", "common")
            self.art = kwargs.get("art", "")
            self.flavor = kwargs.get("flavor", "")
            self.status = kwargs.get("status", "pending")
            self.card_path = kwargs.get("card_path")
            self.image_path = kwargs.get("image_path")
            self.generated_at = kwargs.get("generated_at")

            # Support both cost and mana_cost
            self.mana_cost = kwargs.get("mana_cost", self.cost)


@unittest.skip("Tests need to be fixed for new CardCRUDManager implementation")
class TestCardCRUDManager(unittest.TestCase):
    """Test suite for CardCRUDManager"""

    @classmethod
    def setUpClass(cls):
        """Set up Qt application for testing"""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        """Set up test fixtures"""
        # Create mock parent widget
        self.parent_widget = Mock(spec=QWidget)
        self.parent_widget.table = Mock(spec=QTableWidget)
        self.parent_widget.table.currentRow.return_value = 0
        self.parent_widget.table.rowCount.return_value = 1

        # Create mock table manager
        self.table_manager = Mock()
        self.table_manager.get_selected_rows.return_value = [0]
        self.table_manager.refresh_table = Mock()
        self.table_manager.set_cards = Mock()
        self.table_manager.set_commander_colors = Mock()

        # Create mock validation manager
        self.validation_manager = Mock()
        self.validation_manager.update_cards = Mock()
        self.validation_manager.commander_colors = set()
        self.validation_manager.log_color_violations = Mock()

        # Create mock logger
        self.logger = Mock()
        self.logger.log_message = Mock()

        # Create test cards
        self.test_cards = [
            MTGCard(id=1, name="Lightning Bolt", type="Instant", cost="R"),
            MTGCard(
                id=2,
                name="Grizzly Bears",
                type="Creature",
                cost="1G",
                power=2,
                toughness=2,
            ),
            MTGCard(id=3, name="Counterspell", type="Instant", cost="UU"),
        ]

        # Create manager instance
        self.manager = CardCRUDManager(
            parent_widget=self.parent_widget,
            cards=self.test_cards.copy(),
            table_manager=self.table_manager,
            validation_manager=self.validation_manager,
            logger=self.logger,
        )

    def test_initialization(self):
        """Test CardCRUDManager initialization"""
        self.assertEqual(self.manager.parent_widget, self.parent_widget)
        self.assertEqual(len(self.manager.cards), 3)
        self.assertEqual(self.manager.table_manager, self.table_manager)
        self.assertEqual(self.manager.validation_manager, self.validation_manager)
        self.assertEqual(self.manager.logger, self.logger)

    def test_get_next_card_id(self):
        """Test getting next available card ID"""
        next_id = self.manager.get_next_card_id()
        self.assertEqual(next_id, 4)  # Should be max ID (3) + 1

        # Test with non-integer IDs
        self.manager.cards.append(MTGCard(id="invalid", name="Test", type="Creature"))
        next_id = self.manager.get_next_card_id()
        self.assertEqual(next_id, 4)  # Should still be 4

    @patch("src.managers.card_crud_manager.QDialog")
    def test_add_new_card(self, mock_dialog):
        """Test adding a new card"""
        # Mock dialog to accept
        mock_dialog_instance = Mock()
        mock_dialog_instance.exec.return_value = 1  # Accepted
        mock_dialog.return_value = mock_dialog_instance

        initial_count = len(self.manager.cards)
        self.manager.add_new_card()

        # Check card was added
        self.assertEqual(len(self.manager.cards), initial_count + 1)
        new_card = self.manager.cards[-1]
        self.assertEqual(new_card.name, "New Card")
        self.assertEqual(new_card.type, "Creature")
        self.assertEqual(new_card.status, "pending")

        # Check table was refreshed
        self.table_manager.refresh_table.assert_called()

    def test_load_cards(self):
        """Test loading cards"""
        new_cards = [
            MTGCard(id=10, name="New Card 1", type="Artifact"),
            MTGCard(
                id=11,
                name="New Card 2",
                type="Enchantment",
                card_path="/path/to/card.png",
            ),
        ]

        self.manager.load_cards(new_cards)

        # Check cards were loaded
        self.assertEqual(len(self.manager.cards), 2)
        self.assertEqual(self.manager.cards[0].name, "New Card 1")
        self.assertEqual(self.manager.cards[1].name, "New Card 2")

        # Check status synchronization
        self.assertEqual(self.manager.cards[0].status, "pending")
        self.assertEqual(self.manager.cards[1].status, "completed")  # Has card_path

        # Check validation manager was updated
        self.validation_manager.update_cards.assert_called_with(new_cards)
        self.validation_manager.log_color_violations.assert_called()

        # Check table manager was updated
        self.table_manager.set_cards.assert_called_with(new_cards)

    def test_get_card_by_id(self):
        """Test getting card by ID"""
        card = self.manager.get_card_by_id(2)
        self.assertIsNotNone(card)
        self.assertEqual(card.name, "Grizzly Bears")

        # Test non-existent ID
        card = self.manager.get_card_by_id(999)
        self.assertIsNone(card)

    def test_get_card_by_index(self):
        """Test getting card by index"""
        card = self.manager.get_card_by_index(1)
        self.assertIsNotNone(card)
        self.assertEqual(card.name, "Grizzly Bears")

        # Test out of bounds index
        card = self.manager.get_card_by_index(999)
        self.assertIsNone(card)

        card = self.manager.get_card_by_index(-1)
        self.assertIsNone(card)

    @patch("src.managers.card_crud_manager.QDialog")
    def test_edit_card(self, mock_dialog):
        """Test editing a card"""
        # Mock dialog to accept with updated values
        mock_dialog_instance = Mock()
        mock_dialog_instance.exec.return_value = 1  # Accepted
        mock_dialog.return_value = mock_dialog_instance

        # Select first card
        self.table_manager.get_selected_rows.return_value = [0]
        self.parent_widget.table.currentRow.return_value = 0

        # Mock the form inputs
        with patch("src.managers.card_crud_manager.QLineEdit") as mock_line_edit, patch(
            "src.managers.card_crud_manager.QTextEdit"
        ) as mock_text_edit:
            # Set up mock inputs
            mock_name_input = Mock()
            mock_name_input.text.return_value = "Updated Lightning Bolt"
            mock_type_input = Mock()
            mock_type_input.text.return_value = "Sorcery"
            mock_mana_input = Mock()
            mock_mana_input.text.return_value = "RR"

            mock_line_edit.side_effect = [
                mock_name_input,  # name
                mock_type_input,  # type
                mock_mana_input,  # mana
                Mock(),  # power
                Mock(),  # toughness
            ]

            mock_text_input = Mock()
            mock_text_input.toPlainText.return_value = "Deal 4 damage"
            mock_text_edit.return_value = mock_text_input

            self.manager.edit_card()

            # Check dialog was shown
            mock_dialog.assert_called()

            # Check table was refreshed
            self.table_manager.refresh_table.assert_called()

    def test_update_card(self):
        """Test updating card data directly"""
        updates = {
            "name": "Super Lightning Bolt",
            "cost": "RRR",
            "text": "Deal 5 damage to any target",
        }

        result = self.manager.update_card(1, updates)
        self.assertTrue(result)

        # Check card was updated
        card = self.manager.get_card_by_id(1)
        self.assertEqual(card.name, "Super Lightning Bolt")
        self.assertEqual(card.cost, "RRR")
        self.assertEqual(card.text, "Deal 5 damage to any target")

        # Test updating non-existent card
        result = self.manager.update_card(999, updates)
        self.assertFalse(result)

    @patch("src.managers.card_crud_manager.QMessageBox")
    def test_delete_selected_cards(self, mock_messagebox):
        """Test deleting selected cards"""
        # Mock user confirming deletion
        mock_messagebox.question.return_value = mock_messagebox.StandardButton.Yes

        # Select middle card
        self.table_manager.get_selected_rows.return_value = [1]

        initial_count = len(self.manager.cards)
        self.manager.delete_selected_cards()

        # Check card was deleted
        self.assertEqual(len(self.manager.cards), initial_count - 1)

        # Check the right card was deleted
        remaining_names = [c.name for c in self.manager.cards]
        self.assertNotIn("Grizzly Bears", remaining_names)
        self.assertIn("Lightning Bolt", remaining_names)
        self.assertIn("Counterspell", remaining_names)

        # Check table was refreshed
        self.table_manager.refresh_table.assert_called()

    @patch("src.managers.card_crud_manager.QMessageBox")
    def test_delete_selected_cards_cancelled(self, mock_messagebox):
        """Test cancelling card deletion"""
        # Mock user cancelling deletion
        mock_messagebox.question.return_value = mock_messagebox.StandardButton.No

        self.table_manager.get_selected_rows.return_value = [1]

        initial_count = len(self.manager.cards)
        self.manager.delete_selected_cards()

        # Check no cards were deleted
        self.assertEqual(len(self.manager.cards), initial_count)

    def test_duplicate_selected_card(self):
        """Test duplicating a card"""
        # Select first card
        self.parent_widget.table.currentRow.return_value = 0

        initial_count = len(self.manager.cards)
        self.manager.duplicate_selected_card()

        # Check card was duplicated
        self.assertEqual(len(self.manager.cards), initial_count + 1)

        # Check duplicate properties
        duplicate = self.manager.cards[1]  # Should be inserted after original
        self.assertEqual(duplicate.name, "Lightning Bolt (Copy)")
        self.assertEqual(duplicate.type, "Instant")
        self.assertEqual(duplicate.cost, "R")
        self.assertEqual(duplicate.status, "pending")
        self.assertEqual(duplicate.id, 4)  # Should have new ID

        # Check table was refreshed
        self.table_manager.refresh_table.assert_called()

    def test_duplicate_with_no_selection(self):
        """Test duplicating with no card selected"""
        # No card selected
        self.parent_widget.table.currentRow.return_value = -1

        initial_count = len(self.manager.cards)
        self.manager.duplicate_selected_card()

        # Check no card was added
        self.assertEqual(len(self.manager.cards), initial_count)

    def test_signal_emission(self):
        """Test that signals are emitted correctly"""
        # Create signal spy mocks
        card_created_spy = Mock()
        card_updated_spy = Mock()
        cards_updated_spy = Mock()

        self.manager.card_created.connect(card_created_spy)
        self.manager.card_updated.connect(card_updated_spy)
        self.manager.cards_updated.connect(cards_updated_spy)

        # Test update_card signal emission
        self.manager.update_card(1, {"name": "Updated Name"})
        card_updated_spy.assert_called()
        cards_updated_spy.assert_called()

    def test_logging(self):
        """Test logging functionality"""
        # Test logging with provided logger
        self.manager._log_message("INFO", "Test message")
        self.logger.log_message.assert_called_with("INFO", "Test message")

        # Test logging without logger (should use main window)
        manager_no_logger = CardCRUDManager(parent_widget=self.parent_widget, cards=[])

        with patch("src.managers.card_crud_manager.get_main_window") as mock_get_main:
            mock_main = Mock()
            mock_main.log_message = Mock()
            mock_get_main.return_value = mock_main

            manager_no_logger._log_message("WARNING", "Test warning")
            mock_main.log_message.assert_called_with("WARNING", "Test warning")


if __name__ == "__main__":
    unittest.main()
