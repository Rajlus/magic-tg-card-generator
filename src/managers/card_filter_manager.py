#!/usr/bin/env python3
"""
Card Filter Manager

This module provides a manager class for handling all filtering functionality
in the MTG Card Generator application. It encapsulates filtering logic for
card types, status, and search operations.
"""

from typing import Any, Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QComboBox, QLabel, QLineEdit, QTableWidget


class CardFilterManager(QObject):
    """
    Manager class for handling all MTG card filtering operations.

    This class encapsulates filtering functionality including:
    - Type-based filtering
    - Status-based filtering
    - Text search filtering
    - Filter result tracking
    """

    # Signals
    filter_applied = pyqtSignal(int, int)  # visible_count, total_count
    filter_cleared = pyqtSignal()  # Emitted when all filters are cleared
    search_performed = pyqtSignal(str, int)  # search_text, result_count
    type_filter_changed = pyqtSignal(str)  # filter_type
    status_filter_changed = pyqtSignal(str)  # filter_status

    def __init__(
        self,
        cards: list[Any] = None,
        table_widget: QTableWidget = None,
        logger=None,
    ):
        """
        Initialize the CardFilterManager.

        Args:
            cards: List of MTG cards to filter
            table_widget: QTableWidget to apply filters to
            logger: Logger for message logging
        """
        super().__init__()
        self.cards = cards or []
        self.table = table_widget
        self.logger = logger

        # Filter components
        self.filter_combo: Optional[QComboBox] = None
        self.status_filter_combo: Optional[QComboBox] = None
        self.search_input: Optional[QLineEdit] = None
        self.filter_result_label: Optional[QLabel] = None

        # Current filter states
        self.current_type_filter = "All"
        self.current_status_filter = "All"
        self.current_search_text = ""

        # Table column indices (from CardTableManager)
        self.COLUMN_ID = 0
        self.COLUMN_NAME = 1
        self.COLUMN_COST = 2
        self.COLUMN_TYPE = 3
        self.COLUMN_PT = 4
        self.COLUMN_TEXT = 5
        self.COLUMN_RARITY = 6
        self.COLUMN_ART = 7
        self.COLUMN_STATUS = 8
        self.COLUMN_IMAGE = 9

    def set_cards(self, cards: list[Any]):
        """
        Set the cards list for filtering.

        Args:
            cards: List of MTG cards to filter
        """
        self.cards = cards

    def set_table(self, table: QTableWidget):
        """
        Set the table widget for filtering operations.

        Args:
            table: The QTableWidget to filter
        """
        self.table = table

    def set_filter_components(
        self,
        filter_combo: QComboBox,
        status_filter_combo: QComboBox,
        search_input: QLineEdit,
        filter_result_label: QLabel,
    ):
        """Set the filter UI components and connect signals."""
        self.filter_combo = filter_combo
        self.status_filter_combo = status_filter_combo
        self.search_input = search_input
        self.filter_result_label = filter_result_label

        # Connect filter signals
        if self.filter_combo:
            self.filter_combo.currentTextChanged.connect(self._on_type_filter_changed)
        if self.status_filter_combo:
            self.status_filter_combo.currentTextChanged.connect(
                self._on_status_filter_changed
            )
        if self.search_input:
            self.search_input.textChanged.connect(self._on_search_text_changed)

    def set_type_filter(self, filter_text: str):
        """Set the type filter."""
        self.current_type_filter = filter_text
        self.apply_filter()

    def set_status_filter(self, filter_text: str):
        """Set the status filter."""
        self.current_status_filter = filter_text
        self.apply_filter()

    def set_search_text(self, search_text: str):
        """Set the search text filter."""
        self.current_search_text = search_text.lower()
        self.apply_filter()

    def clear_filters(self):
        """Clear all filters."""
        self.current_type_filter = "All"
        self.current_status_filter = "All"
        self.current_search_text = ""
        self.apply_filter()

    def clear_all_filters(self):
        """Clear all filters (alias for backward compatibility)."""
        self.clear_filters()
        self.filter_cleared.emit()

    def get_visible_cards(self) -> list[Any]:
        """
        Get the list of cards that match current filters.

        Returns:
            List of cards that pass all active filters
        """
        visible_cards = []

        for card in self.cards:
            if self._card_matches_filters(card):
                visible_cards.append(card)

        return visible_cards

    def _card_matches_filters(self, card: Any) -> bool:
        """
        Check if a card matches all active filters.

        Args:
            card: Card object to check

        Returns:
            True if card matches all filters
        """
        # Type filter
        if self.current_type_filter != "All":
            if not self._matches_type_filter(
                card.type.lower(), self.current_type_filter
            ):
                return False

        # Status filter
        if self.current_status_filter != "All":
            status_display = self._get_status_display_text(card)
            if not self._matches_status_filter(
                status_display, self.current_status_filter
            ):
                return False

        # Search filter
        if self.current_search_text:
            if not self._matches_search_filter(card, self.current_search_text):
                return False

        return True

    def _get_status_display_text(self, card: Any) -> str:
        """Get the display text for a card's status."""
        status = getattr(
            card, "generation_status", getattr(card, "status", "pending")
        ).lower()

        status_map = {
            "completed": "✅ Completed",
            "generating": "🔄 Generating",
            "failed": "❌ Failed",
        }

        return status_map.get(status, "⏸️ Pending")

    def apply_filter(self):
        """Apply current filters to the table display."""
        if not self.table:
            return

        filter_text = self.current_type_filter
        status_filter = self.current_status_filter
        search_text = self.current_search_text

        visible_count = 0
        total_count = self.table.rowCount()

        for row in range(total_count):
            show = self._should_show_row(row, filter_text, status_filter, search_text)
            self.table.setRowHidden(row, not show)
            if show:
                visible_count += 1

        # Update filter result label
        self._update_filter_result_label(visible_count, total_count)

        # Emit signal
        self.filter_applied.emit(visible_count, total_count)

    def _should_show_row(
        self, row: int, type_filter: str, status_filter: str, search_text: str
    ) -> bool:
        """
        Determine if a table row should be visible based on filters.

        Args:
            row: Row index
            type_filter: Type filter text
            status_filter: Status filter text
            search_text: Search text

        Returns:
            True if row should be visible
        """
        if not self.table:
            return True

        # Type filter
        if type_filter != "All":
            type_item = self.table.item(row, self.COLUMN_TYPE)
            if not type_item:
                return False

            card_type = type_item.text().lower()
            if not self._matches_type_filter(card_type, type_filter):
                return False

        # Status filter
        if status_filter != "All":
            status_item = self.table.item(row, self.COLUMN_STATUS)
            if not status_item:
                return False

            if not self._matches_status_filter(status_item.text(), status_filter):
                return False

        # Search filter
        if search_text:
            if not self._matches_search_filter_by_row(row, search_text):
                return False

        return True

    def _matches_type_filter(self, card_type: str, filter_text: str) -> bool:
        """Check if card type matches the type filter."""
        type_mappings = {
            "Creatures": ["kreatur", "creature"],
            "Lands": ["land"],
            "Instants": ["spontanzauber", "instant"],
            "Sorceries": ["hexerei", "sorcery"],
            "Artifacts": ["artefakt", "artifact"],
            "Enchantments": ["verzauberung", "enchantment"],
        }

        if filter_text in type_mappings:
            return any(keyword in card_type for keyword in type_mappings[filter_text])

        return True

    def _matches_status_filter(self, status_text: str, status_filter: str) -> bool:
        """Check if status text matches the status filter."""
        status_mappings = {
            "✅ Completed": "✅",
            "⏸️ Pending": "⏸️",
            "❌ Failed": "❌",
            "🔄 Generating": "🔄",
        }

        if status_filter in status_mappings:
            return status_mappings[status_filter] in status_text

        return True

    def _matches_search_filter(self, card: Any, search_text: str) -> bool:
        """Check if card matches search text across searchable fields."""
        searchable_fields = [
            getattr(card, "name", "").lower(),
            getattr(card, "cost", "").lower(),
            getattr(card, "type", "").lower(),
            getattr(card, "text", "").lower(),
            getattr(card, "art", "").lower(),
        ]

        return any(search_text in field for field in searchable_fields)

    def _matches_search_filter_by_row(self, row: int, search_text: str) -> bool:
        """Check if any cell in the table row matches the search text."""
        if not self.table:
            return False

        searchable_columns = [
            self.COLUMN_NAME,
            self.COLUMN_COST,
            self.COLUMN_TYPE,
            self.COLUMN_TEXT,
            self.COLUMN_ART,
        ]

        for col in searchable_columns:
            item = self.table.item(row, col)
            if item and search_text in item.text().lower():
                return True

        return False

    def _update_filter_result_label(self, visible_count: int, total_count: int):
        """Update the filter result label."""
        if not self.filter_result_label:
            return

        if visible_count == total_count:
            self.filter_result_label.setVisible(False)
        else:
            self.filter_result_label.setText(
                f"Showing {visible_count} of {total_count} cards"
            )
            self.filter_result_label.setVisible(True)

    def _on_type_filter_changed(self, text: str):
        """Handle type filter changes."""
        self.current_type_filter = text
        self.type_filter_changed.emit(text)
        self.apply_filter()

    def _on_status_filter_changed(self, text: str):
        """Handle status filter changes."""
        self.current_status_filter = text
        self.status_filter_changed.emit(text)
        self.apply_filter()

    def _on_search_text_changed(self, text: str):
        """Handle search text changes."""
        self.current_search_text = text.lower()
        self.apply_filter()

        # Emit search performed signal
        if text:
            visible_cards = self.get_visible_cards()
            self.search_performed.emit(text, len(visible_cards))

    def get_visible_rows(self) -> list[int]:
        """Get list of visible row indices."""
        if not self.table:
            return []

        visible_rows = []
        for row in range(self.table.rowCount()):
            if not self.table.isRowHidden(row):
                visible_rows.append(row)
        return visible_rows

    def get_filtered_cards(self) -> list[Any]:
        """Get list of currently visible cards after filtering."""
        visible_rows = self.get_visible_rows()
        return [self.cards[row] for row in visible_rows if row < len(self.cards)]

    def get_filter_state(self) -> dict[str, Any]:
        """Get current filter state."""
        return {
            "type_filter": self.current_type_filter,
            "status_filter": self.current_status_filter,
            "search_text": self.current_search_text,
        }

    def set_filter_state(self, filter_state: dict[str, Any]):
        """Set filter state from dictionary."""
        self.current_type_filter = filter_state.get("type_filter", "All")
        self.current_status_filter = filter_state.get("status_filter", "All")
        self.current_search_text = filter_state.get("search_text", "")

        # Update UI components if they exist
        if self.filter_combo:
            self.filter_combo.setCurrentText(self.current_type_filter)
        if self.status_filter_combo:
            self.status_filter_combo.setCurrentText(self.current_status_filter)
        if self.search_input:
            self.search_input.setText(self.current_search_text)

        self.apply_filter()
