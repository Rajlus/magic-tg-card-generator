#!/usr/bin/env python3
"""
Card CRUD Manager

This module provides a manager class for handling all CRUD operations
for MTG cards in the MTG Card Generator application. It encapsulates
card creation, reading, updating, and deletion operations.

Extracted from CardManagementTab as part of issue #25 to improve code organization
and maintainability.
"""

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTextEdit,
    QWidget,
)

# Add parent path to sys.path for imports
root_path = Path(__file__).parent.parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

# Import domain model
from src.domain.models import MTGCard


def get_main_window():
    """Get the main application window"""
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app:
        for widget in app.topLevelWidgets():
            if widget.objectName() == "MainWindow":
                return widget
    return None


class CardCRUDManager(QObject):
    """
    Manager class for handling all MTG card CRUD operations.

    This class encapsulates CRUD functionality including:
    - Card creation with validation
    - Card reading and data synchronization
    - Card updating with form dialogs
    - Card deletion with confirmation
    - Integration with existing managers
    """

    # Signals for UI updates and external notifications
    card_created = pyqtSignal(object)  # Emitted when card is created
    card_updated = pyqtSignal(object)  # Emitted when card is updated
    card_deleted = pyqtSignal(int)  # Emitted when card is deleted (card_id)
    cards_loaded = pyqtSignal(list)  # Emitted when cards are loaded
    cards_updated = pyqtSignal(list)  # Emitted when card list changes

    def __init__(
        self,
        parent_widget: QWidget = None,
        cards: list = None,
        table_manager=None,
        validation_manager=None,
        logger=None,
    ):
        """
        Initialize the CRUD manager.

        Args:
            parent_widget: Parent widget for dialogs
            cards: List of MTG cards to manage
            table_manager: CardTableManager instance for UI updates
            validation_manager: CardValidationManager for validation
            logger: Logger instance for operation logging
        """
        # Handle Mock objects for testing and real QWidget for production
        try:
            super().__init__(
                parent_widget
                if parent_widget and isinstance(parent_widget, QWidget)
                else None
            )
        except TypeError:
            # In testing, parent_widget might be a Mock object
            super().__init__(None)

        self.parent_widget = parent_widget
        self.cards = cards if cards is not None else []
        self.table_manager = table_manager
        self.validation_manager = validation_manager
        self.logger = logger

    def _log_message(self, level: str, message: str):
        """Log a message using available logger"""
        if self.logger and hasattr(self.logger, "log_message"):
            self.logger.log_message(level, message)
        else:
            # Try to get main window logger
            main_window = get_main_window()
            if main_window and hasattr(main_window, "log_message"):
                main_window.log_message(level, message)

    def _get_parent_window(self):
        """Get the parent window for auto-save and logging"""
        if self.parent_widget:
            # Try to get main window through parent hierarchy
            parent = self.parent_widget.parent()
            while parent:
                if hasattr(parent, "auto_save_deck"):
                    return parent
                parent = parent.parent() if hasattr(parent, "parent") else None
        return get_main_window()

    def get_next_card_id(self) -> int:
        """Get next available card ID."""
        max_id = 0
        for card in self.cards:
            try:
                card_id = int(card.id) if isinstance(card.id, str | int) else 0
                max_id = max(max_id, card_id)
            except (ValueError, TypeError):
                continue
        return max_id + 1

    # CREATE operations
    def add_new_card(self):
        """Add a new blank card to the deck"""
        next_id = self.get_next_card_id()

        # Create a new card with default values
        new_card = MTGCard(
            id=next_id,
            name="New Card",
            cost="{1}",
            type="Creature",
            text="",
            power=1,
            toughness=1,
            rarity="common",
            art="",
            flavor="",
            status="pending",
        )

        # Add to cards list
        self.cards.append(new_card)

        # Refresh table if available
        if self.table_manager:
            self.table_manager.refresh_table()

        # Select the new card (last row) if table widget is available
        if self.parent_widget and hasattr(self.parent_widget, "table"):
            table = self.parent_widget.table
            last_row = table.rowCount() - 1
            table.selectRow(last_row)

            # Open edit dialog for the new card
            self.edit_card_at_row(last_row)

        # Auto-save
        main_window = self._get_parent_window()
        if main_window and hasattr(main_window, "auto_save_deck"):
            main_window.auto_save_deck(self.cards)

        # Log the action
        self._log_message("INFO", f"Added new card: {new_card.name}")

        # Emit signals
        self.card_created.emit(new_card)
        self.cards_updated.emit(self.cards)

    def edit_card_at_row(self, row: int):
        """Edit card at specific row - delegates to edit_card"""
        if self.parent_widget and hasattr(self.parent_widget, "table"):
            self.parent_widget.table.selectRow(row)
        self.edit_card()

    # READ operations
    def load_cards(self, cards: list):
        """Load cards into table"""
        self.cards = cards

        # Update validation manager with new cards if available
        if self.validation_manager:
            self.validation_manager.update_cards(self.cards)
            commander_colors = self.validation_manager.commander_colors

            # Log all cards with color violations
            self.validation_manager.log_color_violations()
        else:
            commander_colors = set()

        # Synchronize card status based on whether they have generated images
        for card in self.cards:
            if hasattr(card, "card_path") and card.card_path:
                # Card has been generated (has a card image)
                card.status = "completed"
            else:
                # No card image means it should be pending
                # (unless it's currently generating or failed)
                if hasattr(card, "status") and card.status in ["generating", "failed"]:
                    # Keep generating or failed status
                    pass
                else:
                    # Default to pending
                    card.status = "pending"

        # Update the table manager with new cards and commander colors
        if self.table_manager:
            self.table_manager.set_cards(self.cards)
            self.table_manager.set_commander_colors(commander_colors)

        # Update stats if parent widget has these methods
        if self.parent_widget:
            if hasattr(self.parent_widget, "update_stats"):
                self.parent_widget.update_stats()
            if hasattr(self.parent_widget, "update_generation_stats"):
                self.parent_widget.update_generation_stats()
            if hasattr(self.parent_widget, "update_button_visibility"):
                self.parent_widget.update_button_visibility()

        # Emit signal
        self.cards_loaded.emit(self.cards)

    def get_card_by_id(self, card_id: int) -> Optional["MTGCard"]:
        """Get card by ID."""
        for card in self.cards:
            if card.id == card_id:
                return card
        return None

    def get_card_by_index(self, index: int) -> Optional["MTGCard"]:
        """Get card by index in list."""
        if 0 <= index < len(self.cards):
            return self.cards[index]
        return None

    # UPDATE operations
    def edit_card(self):
        """Edit selected card details including art description"""
        if not self.parent_widget or not hasattr(self.parent_widget, "table"):
            self._log_message("WARNING", "No table widget available for card editing")
            return

        table = self.parent_widget.table

        # Try to get selected rows from table manager first
        if self.table_manager and hasattr(self.table_manager, "get_selected_rows"):
            selected_rows = self.table_manager.get_selected_rows()
        else:
            # Fallback to direct table access
            current_row = table.currentRow()
            selected_rows = [current_row] if current_row >= 0 else []

        if not selected_rows:
            QMessageBox.warning(
                self.parent_widget, "No Selection", "Please select a card to edit!"
            )
            return

        row = min(selected_rows)
        if 0 <= row < len(self.cards):
            card = self.cards[row]

            dialog = QDialog(self.parent_widget)
            dialog.setWindowTitle(f"Edit Card: {card.name}")
            dialog.setModal(True)
            dialog.resize(600, 500)

            layout = QFormLayout()

            # Create input fields
            name_input = QLineEdit(card.name)
            type_input = QLineEdit(card.type)

            # Handle different attribute names for mana cost
            mana_cost = (
                getattr(card, "mana_cost", None) or getattr(card, "cost", None) or ""
            )
            mana_input = QLineEdit(mana_cost)

            text_input = QTextEdit(card.text if card.text else "")
            text_input.setMaximumHeight(100)

            # Add power/toughness for creatures
            power_input = QLineEdit(str(card.power) if card.power else "")
            toughness_input = QLineEdit(str(card.toughness) if card.toughness else "")

            # Add flavor text
            flavor_input = QTextEdit(
                card.flavor if hasattr(card, "flavor") and card.flavor else ""
            )
            flavor_input.setMaximumHeight(60)

            # Add art description field - check both 'art' and 'art_prompt' attributes
            art_text = ""
            if hasattr(card, "art") and card.art:
                art_text = card.art
            elif hasattr(card, "art_prompt") and card.art_prompt:
                art_text = card.art_prompt

            art_input = QTextEdit(art_text)
            art_input.setMaximumHeight(100)
            art_input.setPlaceholderText(
                "Enter art description for AI image generation..."
            )

            # Build form layout
            layout.addRow("Name:", name_input)
            layout.addRow("Type:", type_input)
            layout.addRow("Mana Cost:", mana_input)
            layout.addRow("Text:", text_input)

            # Power/Toughness row
            pt_widget = QWidget()
            pt_layout = QHBoxLayout()
            pt_layout.setContentsMargins(0, 0, 0, 0)
            pt_layout.addWidget(power_input)
            pt_layout.addWidget(QLabel("/"))
            pt_layout.addWidget(toughness_input)
            pt_widget.setLayout(pt_layout)
            layout.addRow("P/T:", pt_widget)

            layout.addRow("Flavor:", flavor_input)
            layout.addRow("Art Description:", art_input)

            # Add buttons
            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok
                | QDialogButtonBox.StandardButton.Cancel
            )
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addRow(buttons)

            dialog.setLayout(layout)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Update card attributes
                card.name = name_input.text()
                card.type = type_input.text()

                # Set both mana_cost and cost for compatibility
                if hasattr(card, "mana_cost"):
                    card.mana_cost = mana_input.text()
                if hasattr(card, "cost"):
                    card.cost = mana_input.text()

                card.text = text_input.toPlainText()

                # Handle power/toughness conversion
                try:
                    card.power = int(power_input.text()) if power_input.text() else None
                except ValueError:
                    card.power = power_input.text() if power_input.text() else None

                try:
                    card.toughness = (
                        int(toughness_input.text()) if toughness_input.text() else None
                    )
                except ValueError:
                    card.toughness = (
                        toughness_input.text() if toughness_input.text() else None
                    )

                card.flavor = flavor_input.toPlainText()

                # Save art description to both attributes for compatibility
                card.art = art_input.toPlainText()
                if hasattr(card, "art_prompt"):
                    card.art_prompt = art_input.toPlainText()

                # Refresh table
                if self.table_manager:
                    self.table_manager.refresh_table()

                # Auto-save
                main_window = self._get_parent_window()
                if main_window and hasattr(main_window, "auto_save_deck"):
                    main_window.auto_save_deck(self.cards)

                # Log the action
                self._log_message("INFO", f"Edited card: {card.name}")

                # Emit signals
                self.card_updated.emit(card)
                self.cards_updated.emit(self.cards)

    def update_card(self, card_id: int, updates: dict) -> bool:
        """Update card with provided data."""
        card = self.get_card_by_id(card_id)
        if not card:
            return False

        # Apply updates
        for key, value in updates.items():
            if hasattr(card, key):
                setattr(card, key, value)

        # Emit signals
        self.card_updated.emit(card)
        self.cards_updated.emit(self.cards)

        return True

    # DELETE operations
    def delete_selected_cards(self):
        """Delete selected cards from the deck"""
        if not self.table_manager:
            self._log_message("WARNING", "No table manager available for card deletion")
            return

        selected_rows = self.table_manager.get_selected_rows()

        if not selected_rows:
            QMessageBox.warning(
                self.parent_widget, "No Selection", "Please select cards to delete"
            )
            return

        # Confirm deletion
        card_count = len(selected_rows)
        reply = QMessageBox.question(
            self.parent_widget,
            "Delete Cards",
            f"Are you sure you want to delete {card_count} card(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Get cards to delete (sort in reverse to maintain indices)
            rows_to_delete = sorted(selected_rows, reverse=True)
            deleted_names = []
            deleted_ids = []

            for row in rows_to_delete:
                if 0 <= row < len(self.cards):
                    card = self.cards[row]
                    deleted_names.append(card.name)
                    deleted_ids.append(card.id)
                    del self.cards[row]

            # Refresh table
            if self.table_manager:
                self.table_manager.refresh_table()

            # Auto-save
            main_window = self._get_parent_window()
            if main_window and hasattr(main_window, "auto_save_deck"):
                main_window.auto_save_deck(self.cards)

            # Log the action
            self._log_message(
                "INFO",
                f"Deleted {card_count} card(s): {', '.join(deleted_names[:3])}{'...' if len(deleted_names) > 3 else ''}",
            )

            # Emit signals
            for card_id in deleted_ids:
                self.card_deleted.emit(card_id)
            self.cards_updated.emit(self.cards)

    # UTILITY operations
    def duplicate_selected_card(self):
        """Duplicate the selected card"""
        if not self.parent_widget or not hasattr(self.parent_widget, "table"):
            self._log_message(
                "WARNING", "No table widget available for card duplication"
            )
            return

        table = self.parent_widget.table
        current_row = table.currentRow()

        if current_row < 0:
            return

        # Find the next available ID
        next_id = self.get_next_card_id()

        # Create a copy of the selected card
        original_card = self.cards[current_row]
        new_card = MTGCard(
            id=next_id,
            name=f"{original_card.name} (Copy)",
            cost=getattr(original_card, "cost", None)
            or getattr(original_card, "mana_cost", None),
            type=original_card.type,
            text=original_card.text,
            power=original_card.power,
            toughness=original_card.toughness,
            rarity=getattr(original_card, "rarity", "common"),
            art=getattr(original_card, "art", ""),
            flavor=getattr(original_card, "flavor", ""),
            status="pending",  # Reset status for new copy
        )

        # Add after the current card
        self.cards.insert(current_row + 1, new_card)

        # Refresh and select the new card
        if self.table_manager:
            self.table_manager.refresh_table()
        table.selectRow(current_row + 1)

        # Auto-save
        main_window = self._get_parent_window()
        if main_window and hasattr(main_window, "auto_save_deck"):
            main_window.auto_save_deck(self.cards)

        # Log
        self._log_message("INFO", f"Duplicated card: {original_card.name}")

        # Emit signals
        self.card_created.emit(new_card)
        self.cards_updated.emit(self.cards)
