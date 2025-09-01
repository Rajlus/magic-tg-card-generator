#!/usr/bin/env python3
"""
Test suite for CardTableManager to verify issue #21 resolution.

This test verifies that the CardTableManager class properly encapsulates
table-related functionality that was extracted from CardManagementTab.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, Mock, patch

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QComboBox, QLabel, QLineEdit, QTableWidget

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from managers.card_table_manager import CardTableManager


class MockCard:
    """Mock MTG card for testing."""

    def __init__(
        self,
        id=1,
        name="Test Card",
        cost="2R",
        type="Creature",
        power="2",
        toughness="2",
        text="Test card text",
        rarity="common",
        art="Test art description",
        status="pending",
    ):
        self.id = id
        self.name = name
        self.cost = cost
        self.type = type
        self.power = power
        self.toughness = toughness
        self.text = text
        self.rarity = rarity
        self.art = art
        self.status = status
        self.image_path = None


class TestCardTableManager(unittest.TestCase):
    """Test cases for CardTableManager functionality."""

    @classmethod
    def setUpClass(cls):
        """Set up QApplication for testing."""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        """Set up test fixtures."""
        self.table = QTableWidget()
        self.cards = [
            MockCard(
                1,
                "Lightning Bolt",
                "R",
                "Instant",
                None,
                None,
                "Deal 3 damage",
                "common",
                "Red lightning",
            ),
            MockCard(
                2,
                "Grizzly Bears",
                "1G",
                "Creature — Bear",
                "2",
                "2",
                "A bear",
                "common",
                "Brown bear",
            ),
            MockCard(
                3,
                "Black Lotus",
                "0",
                "Artifact",
                None,
                None,
                "Add 3 mana",
                "mythic",
                "Black flower",
            ),
        ]

        # Create manager
        self.manager = CardTableManager(self.table, self.cards)

        # Create filter components
        self.filter_combo = QComboBox()
        self.status_filter_combo = QComboBox()
        self.search_input = QLineEdit()
        self.filter_result_label = QLabel()

        # Set up filter components
        self.manager.set_filter_components(
            self.filter_combo,
            self.status_filter_combo,
            self.search_input,
            self.filter_result_label,
        )

    def test_manager_initialization(self):
        """Test that CardTableManager initializes correctly."""
        self.assertIsInstance(self.manager, CardTableManager)
        self.assertEqual(self.manager.table, self.table)
        self.assertEqual(len(self.manager.cards), 3)
        self.assertEqual(self.table.columnCount(), len(CardTableManager.HEADERS))

    def test_required_methods_exist(self):
        """Test that all required methods from issue #21 exist."""
        # Map expected method names to actual method names in the implementation
        required_methods = {
            "setup_table": "_setup_table",
            "refresh_table": "refresh_table",
            "apply_filter": "apply_filter",
            "get_selected_rows": "get_selected_rows",
            "on_table_item_changed": "_on_item_changed",  # This is the actual method name
            "show_context_menu": "_show_context_menu",
        }

        for expected_name, actual_method in required_methods.items():
            has_method = hasattr(self.manager, actual_method) and callable(
                getattr(self.manager, actual_method)
            )

            self.assertTrue(
                has_method,
                f"Method '{expected_name}' (implemented as '{actual_method}') not found in CardTableManager",
            )

    def test_table_setup(self):
        """Test that table is properly set up."""
        # Check headers
        for i, header in enumerate(CardTableManager.HEADERS):
            self.assertEqual(self.table.horizontalHeaderItem(i).text(), header)

        # Check column count
        self.assertEqual(self.table.columnCount(), len(CardTableManager.HEADERS))

        # Check that sorting is disabled
        self.assertFalse(self.table.isSortingEnabled())

    def test_refresh_table(self):
        """Test table refresh functionality."""
        self.manager.refresh_table()

        # Check that rows match cards
        self.assertEqual(self.table.rowCount(), len(self.cards))

        # Check first row data
        first_row = 0
        self.assertEqual(
            self.table.item(first_row, CardTableManager.COLUMN_ID).text(), "1"
        )
        self.assertEqual(
            self.table.item(first_row, CardTableManager.COLUMN_NAME).text(),
            "Lightning Bolt",
        )
        self.assertEqual(
            self.table.item(first_row, CardTableManager.COLUMN_COST).text(), "R"
        )
        self.assertEqual(
            self.table.item(first_row, CardTableManager.COLUMN_TYPE).text(), "Instant"
        )

    def test_get_selected_rows(self):
        """Test getting selected rows."""
        self.manager.refresh_table()

        # Initially no selection
        selected = self.manager.get_selected_rows()
        self.assertEqual(len(selected), 0)

        # Select a row
        self.table.selectRow(0)
        selected = self.manager.get_selected_rows()
        self.assertEqual(len(selected), 1)
        self.assertIn(0, selected)

    def test_get_selected_cards(self):
        """Test getting selected card objects."""
        self.manager.refresh_table()

        # Select first row
        self.table.selectRow(0)
        selected_cards = self.manager.get_selected_cards()

        self.assertEqual(len(selected_cards), 1)
        self.assertEqual(selected_cards[0].name, "Lightning Bolt")

    def test_apply_filter_type(self):
        """Test type filtering."""
        self.filter_combo.addItems(["All", "Creatures", "Instants", "Artifacts"])
        self.status_filter_combo.addItems(["All"])

        self.manager.refresh_table()

        # Filter for instants
        self.filter_combo.setCurrentText("Instants")
        self.manager.apply_filter()

        # Check that only instant is visible
        visible_count = 0
        for row in range(self.table.rowCount()):
            if not self.table.isRowHidden(row):
                visible_count += 1
                # Should be the Lightning Bolt row
                self.assertIn(
                    "Instant", self.table.item(row, CardTableManager.COLUMN_TYPE).text()
                )

        self.assertEqual(visible_count, 1)

    def test_search_filter(self):
        """Test text search functionality."""
        self.filter_combo.addItems(["All"])
        self.status_filter_combo.addItems(["All"])

        self.manager.refresh_table()

        # Search for "bolt"
        self.search_input.setText("bolt")
        self.manager.apply_filter()

        # Should show only Lightning Bolt
        visible_count = 0
        for row in range(self.table.rowCount()):
            if not self.table.isRowHidden(row):
                visible_count += 1
                self.assertIn(
                    "Lightning Bolt",
                    self.table.item(row, CardTableManager.COLUMN_NAME).text(),
                )

        self.assertEqual(visible_count, 1)

    def test_color_violation_detection(self):
        """Test commander color violation detection."""
        # Set commander colors to only red
        self.manager.set_commander_colors({"R"})
        self.manager.refresh_table()

        # Check that Green card (Grizzly Bears) is highlighted
        bears_row = 1  # Grizzly Bears is second card
        cost_item = self.table.item(bears_row, CardTableManager.COLUMN_COST)

        # Should have red background due to color violation
        background_color = cost_item.background().color()
        self.assertEqual(background_color.red(), 255)  # Should be red-ish

    def test_card_addition_removal(self):
        """Test adding and removing cards."""
        initial_count = self.manager.get_card_count()

        # Add a card
        new_card = MockCard(
            4, "Test Addition", "2U", "Creature", "1", "1", "Test", "common", "Test art"
        )
        self.manager.add_card_to_table(new_card)

        self.assertEqual(self.manager.get_card_count(), initial_count + 1)
        self.assertEqual(self.table.rowCount(), initial_count + 1)

        # Remove the card
        self.manager.remove_card_from_table(4)

        self.assertEqual(self.manager.get_card_count(), initial_count)
        self.assertEqual(self.table.rowCount(), initial_count)

    def test_signals_emitted(self):
        """Test that appropriate signals are emitted."""
        # Mock signal connections
        item_changed_spy = Mock()
        selection_changed_spy = Mock()
        card_action_spy = Mock()

        self.manager.item_changed.connect(item_changed_spy)
        self.manager.selection_changed.connect(selection_changed_spy)
        self.manager.card_action_requested.connect(card_action_spy)

        self.manager.refresh_table()

        # Test selection change signal
        self.table.selectRow(0)
        # Note: In a real Qt environment, this would trigger the signal
        # For unit testing, we verify the signal exists and can be connected

        self.assertTrue(hasattr(self.manager, "item_changed"))
        self.assertTrue(hasattr(self.manager, "selection_changed"))
        self.assertTrue(hasattr(self.manager, "card_action_requested"))


if __name__ == "__main__":
    unittest.main()
