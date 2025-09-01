"""Batch operations widget for MTG deck builder.

This widget provides all batch operation functionality that was previously
in the CardManagementTab, including generation, regeneration, and deletion
of selected cards or all cards.
"""

from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QWidget,
)


class BatchOperationsWidget(QWidget):
    """Widget for batch operations on cards.

    This widget provides buttons and controls for:
    1. Generate Selected Cards - Generate only selected pending cards
    2. Regenerate Selected with Image - Regenerate selected cards with new artwork
    3. Regenerate Selected Card Only - Regenerate selected cards keeping existing artwork
    4. Delete Selected Files - Delete generated files for selected cards
    5. Regenerate All Cards Only - Regenerate all cards keeping existing images

    All operations are communicated via signals to maintain clean separation
    between UI and business logic. The parent should handle the actual operations
    through managers and controllers.
    """

    # Selection-based operation signals
    generate_selected_requested = pyqtSignal()  # Generate selected pending cards
    regenerate_selected_with_image_requested = (
        pyqtSignal()
    )  # Regenerate selected with new image
    regenerate_selected_card_only_requested = (
        pyqtSignal()
    )  # Regenerate selected keeping image
    delete_selected_files_requested = pyqtSignal()  # Delete files for selected cards

    # Global operation signals
    regenerate_all_cards_only_requested = (
        pyqtSignal()
    )  # Regenerate all cards keeping images

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the batch operations widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        """Initialize the user interface components."""
        # Main horizontal layout
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Selection-based operation buttons (left side)
        # Generate Selected button (initially hidden - shown only for non-generated cards)
        self.generate_selected_btn = QPushButton("🎯 Generate Selected")
        self.generate_selected_btn.setToolTip("Generate all selected pending cards")
        self.generate_selected_btn.setVisible(False)  # Initially hidden

        # Regeneration buttons for selected cards (initially hidden)
        self.regen_with_image_btn = QPushButton("🖼️ Regenerate with New Image")
        self.regen_with_image_btn.setToolTip(
            "Regenerate selected cards with new artwork"
        )
        self.regen_with_image_btn.setVisible(False)  # Initially hidden

        self.regen_card_only_btn = QPushButton("🃏 Regenerate Card Only")
        self.regen_card_only_btn.setToolTip(
            "Regenerate selected cards using existing artwork"
        )
        self.regen_card_only_btn.setVisible(False)  # Initially hidden

        # Delete files button for selected cards (initially hidden)
        self.delete_files_btn = QPushButton("🗑️ Delete Files")
        self.delete_files_btn.setToolTip("Delete generated files for selected cards")
        self.delete_files_btn.setVisible(False)  # Initially hidden

        # Add selection-based buttons to layout
        layout.addWidget(self.generate_selected_btn)
        layout.addWidget(self.regen_with_image_btn)
        layout.addWidget(self.regen_card_only_btn)
        layout.addWidget(self.delete_files_btn)

        # Add stretch to push global operations to the right
        layout.addStretch()

        # Global operation buttons (right side)
        # Regenerate All Cards Only button (always visible on the right)
        self.regen_all_cards_only_btn = QPushButton("♻️ Regenerate All Cards Only")
        self.regen_all_cards_only_btn.setToolTip(
            "Regenerate all cards keeping existing images where available"
        )
        self.regen_all_cards_only_btn.setStyleSheet(
            "QPushButton { background-color: #5c4528; color: white; font-weight: bold; padding: 5px; }"
        )

        layout.addWidget(self.regen_all_cards_only_btn)

        self.setLayout(layout)

    def _connect_signals(self) -> None:
        """Connect button signals to emit custom signals."""
        # Selection-based operation signals
        self.generate_selected_btn.clicked.connect(
            self.generate_selected_requested.emit
        )
        self.regen_with_image_btn.clicked.connect(
            self.regenerate_selected_with_image_requested.emit
        )
        self.regen_card_only_btn.clicked.connect(
            self.regenerate_selected_card_only_requested.emit
        )
        self.delete_files_btn.clicked.connect(self.delete_selected_files_requested.emit)

        # Global operation signals
        self.regen_all_cards_only_btn.clicked.connect(
            self.regenerate_all_cards_only_requested.emit
        )

    def update_button_visibility(
        self, has_pending: bool, has_generated: bool, selected_count: int
    ) -> None:
        """Update visibility of buttons based on card selection and status.

        Args:
            has_pending: Whether any selected cards are pending (not generated)
            has_generated: Whether any selected cards are generated
            selected_count: Number of cards currently selected
        """
        # Show Generate Selected only if there are pending cards selected
        self.generate_selected_btn.setVisible(has_pending and selected_count > 0)

        # Show regeneration and delete buttons only if there are generated cards selected
        show_generated_ops = has_generated and selected_count > 0
        self.regen_with_image_btn.setVisible(show_generated_ops)
        self.regen_card_only_btn.setVisible(show_generated_ops)
        self.delete_files_btn.setVisible(show_generated_ops)

        # Regenerate All Cards Only is always visible (not dependent on selection)

    def set_buttons_enabled(self, enabled: bool) -> None:
        """Enable or disable all batch operation buttons.

        Args:
            enabled: Whether buttons should be enabled
        """
        self.generate_selected_btn.setEnabled(enabled)
        self.regen_with_image_btn.setEnabled(enabled)
        self.regen_card_only_btn.setEnabled(enabled)
        self.delete_files_btn.setEnabled(enabled)
        self.regen_all_cards_only_btn.setEnabled(enabled)

    def set_generation_buttons_enabled(self, enabled: bool) -> None:
        """Enable or disable generation-related buttons only.

        Args:
            enabled: Whether generation buttons should be enabled
        """
        self.generate_selected_btn.setEnabled(enabled)
        self.regen_with_image_btn.setEnabled(enabled)
        self.regen_card_only_btn.setEnabled(enabled)
        self.regen_all_cards_only_btn.setEnabled(enabled)

    def set_delete_button_enabled(self, enabled: bool) -> None:
        """Enable or disable the delete files button.

        Args:
            enabled: Whether the delete files button should be enabled
        """
        self.delete_files_btn.setEnabled(enabled)

    def get_button_states(self) -> dict:
        """Get the current enabled/disabled and visible state of all buttons.

        Returns:
            Dictionary containing button states for debugging/testing
        """
        return {
            "generate_selected": {
                "enabled": self.generate_selected_btn.isEnabled(),
                "visible": self.generate_selected_btn.isVisible(),
            },
            "regen_with_image": {
                "enabled": self.regen_with_image_btn.isEnabled(),
                "visible": self.regen_with_image_btn.isVisible(),
            },
            "regen_card_only": {
                "enabled": self.regen_card_only_btn.isEnabled(),
                "visible": self.regen_card_only_btn.isVisible(),
            },
            "delete_files": {
                "enabled": self.delete_files_btn.isEnabled(),
                "visible": self.delete_files_btn.isVisible(),
            },
            "regen_all_cards_only": {
                "enabled": self.regen_all_cards_only_btn.isEnabled(),
                "visible": self.regen_all_cards_only_btn.isVisible(),
            },
        }

    def reset_button_visibility(self) -> None:
        """Reset all buttons to their initial visibility state (hidden except global operations)."""
        self.generate_selected_btn.setVisible(False)
        self.regen_with_image_btn.setVisible(False)
        self.regen_card_only_btn.setVisible(False)
        self.delete_files_btn.setVisible(False)
        # regen_all_cards_only_btn stays visible

    def has_visible_buttons(self) -> bool:
        """Check if any buttons are currently visible.

        Returns:
            True if at least one button is visible, False otherwise
        """
        return (
            self.generate_selected_btn.isVisible()
            or self.regen_with_image_btn.isVisible()
            or self.regen_card_only_btn.isVisible()
            or self.delete_files_btn.isVisible()
            or self.regen_all_cards_only_btn.isVisible()
        )
