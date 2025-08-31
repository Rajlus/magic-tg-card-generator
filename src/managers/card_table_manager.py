#!/usr/bin/env python3
"""
Card Table Manager

This module provides a manager class for handling all table-related functionality
in the MTG Card Generator application. It encapsulates table operations, filtering,
selection handling, and data refresh operations.
"""

import contextlib
from typing import Any, Optional

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
)


class CardTableManager(QObject):
    """
    Manager class for handling all MTG card table operations.

    This class encapsulates table-related functionality including:
    - Table setup and configuration
    - Data refresh and display
    - Filtering and search
    - Selection handling
    - Context menu operations
    - Item change tracking
    """

    # Signals
    item_changed = pyqtSignal(object)  # Emitted when table item is changed
    selection_changed = pyqtSignal()  # Emitted when selection changes
    card_action_requested = pyqtSignal(
        str, object
    )  # Emitted for card actions (edit, delete, etc.)

    # Table column indices
    COLUMN_ID = 0
    COLUMN_NAME = 1
    COLUMN_COST = 2
    COLUMN_TYPE = 3
    COLUMN_PT = 4
    COLUMN_TEXT = 5
    COLUMN_RARITY = 6
    COLUMN_ART = 7
    COLUMN_STATUS = 8
    COLUMN_IMAGE = 9

    # Column headers
    HEADERS = [
        "#",
        "Name",
        "Cost",
        "Type",
        "P/T",
        "Text",
        "Rarity",
        "Art",
        "Gen. Status",
        "Image",
    ]

    # Column widths
    COLUMN_WIDTHS = {
        COLUMN_ID: 40,
        COLUMN_NAME: 180,
        COLUMN_COST: 60,
        COLUMN_TYPE: 140,
        COLUMN_PT: 50,
        COLUMN_TEXT: 250,  # Will stretch
        COLUMN_RARITY: 70,
        COLUMN_ART: 200,  # Will stretch
        COLUMN_STATUS: 100,
        COLUMN_IMAGE: 80,
    }

    def __init__(self, table_widget: QTableWidget, cards: list[Any] = None):
        """
        Initialize the CardTableManager.

        Args:
            table_widget: The QTableWidget to manage
            cards: List of MTG cards (optional)
        """
        super().__init__()
        self.table = table_widget
        self.cards = cards or []
        self.commander_colors = set()
        self.filtered_cards = []

        # Filter components (will be set by parent)
        self.filter_combo: Optional[QComboBox] = None
        self.status_filter_combo: Optional[QComboBox] = None
        self.search_input: Optional[QLineEdit] = None
        self.filter_result_label: Optional[QLabel] = None

        self._setup_table()
        self._connect_signals()

    def set_filter_components(
        self,
        filter_combo: QComboBox,
        status_filter_combo: QComboBox,
        search_input: QLineEdit,
        filter_result_label: QLabel,
    ):
        """Set the filter UI components."""
        self.filter_combo = filter_combo
        self.status_filter_combo = status_filter_combo
        self.search_input = search_input
        self.filter_result_label = filter_result_label

        # Connect filter signals
        if self.filter_combo:
            self.filter_combo.currentTextChanged.connect(self.apply_filter)
        if self.status_filter_combo:
            self.status_filter_combo.currentTextChanged.connect(self.apply_filter)
        if self.search_input:
            self.search_input.textChanged.connect(self.apply_filter)

    def _setup_table(self):
        """Set up the table widget configuration."""
        # Set column count and headers
        self.table.setColumnCount(len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)

        # Configure column widths
        header = self.table.horizontalHeader()
        for column, width in self.COLUMN_WIDTHS.items():
            header.resizeSection(column, width)

        # Make specific columns stretch
        header.setStretchLastSection(False)
        header.setSectionResizeMode(self.COLUMN_TEXT, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.COLUMN_ART, QHeaderView.ResizeMode.Stretch)

        # Disable sorting (as noted in original code - it's broken)
        self.table.setSortingEnabled(False)

        # Set selection behavior
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        # Enable context menu
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

    def _connect_signals(self):
        """Connect table signals to handlers."""
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

    def set_cards(self, cards: list[Any]):
        """
        Set the cards list and refresh the table.

        Args:
            cards: List of MTG cards to display
        """
        self.cards = cards
        self.refresh_table()

    def set_commander_colors(self, colors: set[str]):
        """
        Set the commander colors for color validation.

        Args:
            colors: Set of commander color identities
        """
        self.commander_colors = colors
        self.refresh_table()  # Refresh to update color violations

    def refresh_table(self):
        """Refresh table display with current cards and color validation."""
        # Temporarily disconnect itemChanged signal to avoid triggering saves during refresh
        with contextlib.suppress(Exception):
            self.table.itemChanged.disconnect()

        try:
            self.table.setRowCount(len(self.cards))

            for row, card in enumerate(self.cards):
                self._populate_table_row(row, card)

            # Apply current filters after refresh
            self.apply_filter()

        finally:
            # Reconnect the signal
            self.table.itemChanged.connect(self._on_item_changed)

    def _populate_table_row(self, row: int, card: Any):
        """
        Populate a single table row with card data.

        Args:
            row: Row index
            card: MTG card object
        """
        # Check if this card violates commander color identity
        violates_colors = self._check_color_violation(card.cost)

        # ID column
        id_item = QTableWidgetItem()
        id_item.setData(Qt.ItemDataRole.DisplayRole, str(card.id))
        id_item.setData(Qt.ItemDataRole.UserRole, int(card.id))
        if violates_colors:
            id_item.setBackground(QBrush(QColor(255, 200, 200)))
        self.table.setItem(row, self.COLUMN_ID, id_item)

        # Name column
        name_item = QTableWidgetItem(card.name)
        if violates_colors:
            name_item.setBackground(QBrush(QColor(255, 200, 200)))
        self.table.setItem(row, self.COLUMN_NAME, name_item)

        # Cost column - highlight in stronger red for violations
        cost_item = QTableWidgetItem(card.cost)
        if violates_colors:
            cost_item.setBackground(QBrush(QColor(255, 150, 150)))
            cost_item.setToolTip(
                f"Color violation! Contains colors not in commander identity: {self.commander_colors}"
            )
        self.table.setItem(row, self.COLUMN_COST, cost_item)

        # Type column
        type_item = QTableWidgetItem(card.type)
        if violates_colors:
            type_item.setBackground(QBrush(QColor(255, 200, 200)))
        self.table.setItem(row, self.COLUMN_TYPE, type_item)

        # Power/Toughness column
        pt_text = ""
        if (
            hasattr(card, "power")
            and hasattr(card, "toughness")
            and card.power is not None
            and card.toughness is not None
        ):
            pt_text = f"{card.power}/{card.toughness}"
        pt_item = QTableWidgetItem(pt_text)
        if violates_colors:
            pt_item.setBackground(QBrush(QColor(255, 200, 200)))
        self.table.setItem(row, self.COLUMN_PT, pt_item)

        # Text column
        text_display = card.text[:50] + "..." if len(card.text) > 50 else card.text
        text_item = QTableWidgetItem(text_display)
        text_item.setToolTip(card.text)
        if violates_colors:
            text_item.setBackground(QBrush(QColor(255, 200, 200)))
        self.table.setItem(row, self.COLUMN_TEXT, text_item)

        # Rarity column
        rarity_item = QTableWidgetItem(card.rarity.title())
        if violates_colors:
            rarity_item.setBackground(QBrush(QColor(255, 200, 200)))
        self.table.setItem(row, self.COLUMN_RARITY, rarity_item)

        # Art description column
        art_display = card.art[:50] + "..." if len(card.art) > 50 else card.art
        art_item = QTableWidgetItem(art_display)
        art_item.setToolTip(card.art)
        if violates_colors:
            art_item.setBackground(QBrush(QColor(255, 200, 200)))
        self.table.setItem(row, self.COLUMN_ART, art_item)

        # Status column with styling
        status_text, status_color = self._get_status_display(card)
        status_item = QTableWidgetItem(status_text)
        if status_color:
            status_item.setBackground(QBrush(QColor(status_color)))
        if violates_colors and not status_color:
            status_item.setBackground(QBrush(QColor(255, 200, 200)))
        self.table.setItem(row, self.COLUMN_STATUS, status_item)

        # Image column
        image_text = (
            "✅ Yes" if (hasattr(card, "image_path") and card.image_path) else "❌ No"
        )
        image_item = QTableWidgetItem(image_text)
        if violates_colors:
            image_item.setBackground(QBrush(QColor(255, 200, 200)))
        self.table.setItem(row, self.COLUMN_IMAGE, image_item)

    def _get_status_display(self, card: Any) -> tuple[str, Optional[str]]:
        """
        Get the display text and color for a card's status.

        Args:
            card: MTG card object

        Returns:
            Tuple of (status_text, status_color)
        """
        status = getattr(card, "status", "pending").lower()

        status_map = {
            "completed": ("✅ Completed", "#d4edda"),  # Light green
            "generating": ("🔄 Generating", "#fff3cd"),  # Light yellow
            "failed": ("❌ Failed", "#f8d7da"),  # Light red
        }

        return status_map.get(status, ("⏸️ Pending", None))

    def _check_color_violation(self, mana_cost: str) -> bool:
        """
        Check if a mana cost violates the commander's color identity.

        Args:
            mana_cost: The mana cost string to check

        Returns:
            True if the cost violates commander colors
        """
        if not self.commander_colors or not mana_cost:
            return False

        # Extract color symbols from mana cost
        cost_colors = set()
        cost_upper = mana_cost.upper()

        color_symbols = ["W", "U", "B", "R", "G"]
        for symbol in color_symbols:
            if symbol in cost_upper:
                cost_colors.add(symbol)

        # Check if any cost colors are not in commander colors
        return bool(cost_colors - self.commander_colors)

    def apply_filter(self):
        """Apply current filters to the table display."""
        if not (self.filter_combo and self.status_filter_combo and self.search_input):
            return

        filter_text = self.filter_combo.currentText()
        status_filter = self.status_filter_combo.currentText()
        search_text = self.search_input.text().lower()

        visible_count = 0
        total_count = self.table.rowCount()

        for row in range(total_count):
            show = self._should_show_row(row, filter_text, status_filter, search_text)
            self.table.setRowHidden(row, not show)
            if show:
                visible_count += 1

        # Update filter result label
        self._update_filter_result_label(visible_count, total_count)

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
            if not self._matches_search_filter(row, search_text):
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

    def _matches_search_filter(self, row: int, search_text: str) -> bool:
        """Check if any cell in the row matches the search text."""
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

    def get_selected_rows(self) -> set[int]:
        """
        Get the set of currently selected row indices.

        Returns:
            Set of selected row indices
        """
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())
        return selected_rows

    def get_selected_cards(self) -> list[Any]:
        """
        Get the currently selected cards.

        Returns:
            List of selected card objects
        """
        selected_rows = self.get_selected_rows()
        return [self.cards[row] for row in selected_rows if 0 <= row < len(self.cards)]

    def clear_selection(self):
        """Clear the current table selection."""
        self.table.clearSelection()

    def select_card_by_id(self, card_id: int):
        """
        Select a card in the table by its ID.

        Args:
            card_id: The ID of the card to select
        """
        for row in range(self.table.rowCount()):
            id_item = self.table.item(row, self.COLUMN_ID)
            if id_item and id_item.data(Qt.ItemDataRole.UserRole) == card_id:
                self.table.selectRow(row)
                break

    def _on_item_changed(self, item: QTableWidgetItem):
        """Handle table item changes."""
        row = item.row()
        column = item.column()

        if row >= len(self.cards):
            return

        card = self.cards[row]
        new_value = item.text()

        # Update the card based on which column was edited
        self._update_card_from_table_edit(card, column, new_value)

        # Emit signal for parent to handle (e.g., auto-save)
        self.item_changed.emit(card)

    def _update_card_from_table_edit(self, card: Any, column: int, new_value: str):
        """
        Update a card object based on table cell edit.

        Args:
            card: The card object to update
            column: The column that was edited
            new_value: The new value from the table cell
        """
        if column == self.COLUMN_ID:
            with contextlib.suppress(ValueError):
                card.id = int(new_value)
        elif column == self.COLUMN_NAME:
            card.name = new_value
        elif column == self.COLUMN_COST:
            card.cost = new_value
        elif column == self.COLUMN_TYPE:
            card.type = new_value
        elif column == self.COLUMN_PT:
            # Parse P/T like "2/3" or "*/4"
            if "/" in new_value:
                parts = new_value.split("/")
                if len(parts) == 2:
                    card.power = parts[0].strip()
                    card.toughness = parts[1].strip()
        elif column == self.COLUMN_TEXT:
            card.text = new_value
        elif column == self.COLUMN_RARITY:
            card.rarity = new_value.lower()
        elif column == self.COLUMN_ART:
            card.art = new_value
        elif column == self.COLUMN_STATUS:
            card.status = new_value.lower()

    def _on_selection_changed(self):
        """Handle table selection changes."""
        self.selection_changed.emit()

    def _show_context_menu(self, position):
        """Show context menu on right-click."""
        if not self.table.selectedItems():
            return

        menu = QMenu()

        # Add actions
        add_action = menu.addAction("➕ Add New Card")
        edit_action = menu.addAction("✏️ Edit Card")
        duplicate_action = menu.addAction("📋 Duplicate Card")
        menu.addSeparator()
        delete_action = menu.addAction("🗑️ Delete Card(s)")
        menu.addSeparator()
        regenerate_action = menu.addAction("🔄 Regenerate Card")

        # Style delete action in red
        delete_action.setStyleSheet("color: #ff6666;")

        # Execute menu
        action = menu.exec(self.table.mapToGlobal(position))

        if action:
            self._handle_context_menu_action(
                action,
                add_action,
                edit_action,
                duplicate_action,
                delete_action,
                regenerate_action,
            )

    def _handle_context_menu_action(
        self,
        action,
        add_action,
        edit_action,
        duplicate_action,
        delete_action,
        regenerate_action,
    ):
        """Handle context menu action selection."""
        selected_cards = self.get_selected_cards()

        if action == add_action:
            self.card_action_requested.emit("add", None)
        elif action == edit_action and selected_cards:
            self.card_action_requested.emit("edit", selected_cards[0])
        elif action == duplicate_action and selected_cards:
            self.card_action_requested.emit("duplicate", selected_cards[0])
        elif action == delete_action and selected_cards:
            self.card_action_requested.emit("delete", selected_cards)
        elif action == regenerate_action and selected_cards:
            self.card_action_requested.emit("regenerate", selected_cards[0])

    def update_card_in_table(self, card: Any):
        """
        Update a specific card's display in the table.

        Args:
            card: The card object to update
        """
        # Find the row for this card
        for row, table_card in enumerate(self.cards):
            if (
                hasattr(card, "id")
                and hasattr(table_card, "id")
                and card.id == table_card.id
            ):
                self._populate_table_row(row, card)
                break

    def remove_card_from_table(self, card_id: int):
        """
        Remove a card from the table display.

        Args:
            card_id: The ID of the card to remove
        """
        # Find and remove the card from the cards list
        self.cards = [
            card for card in self.cards if getattr(card, "id", None) != card_id
        ]
        self.refresh_table()

    def add_card_to_table(self, card: Any, position: Optional[int] = None):
        """
        Add a new card to the table.

        Args:
            card: The card object to add
            position: Optional position to insert at (None = append)
        """
        if position is None:
            self.cards.append(card)
        else:
            self.cards.insert(position, card)

        self.refresh_table()

    def get_card_count(self) -> int:
        """Get the total number of cards in the table."""
        return len(self.cards)

    def get_visible_card_count(self) -> int:
        """Get the number of currently visible (not filtered) cards."""
        visible_count = 0
        for row in range(self.table.rowCount()):
            if not self.table.isRowHidden(row):
                visible_count += 1
        return visible_count
