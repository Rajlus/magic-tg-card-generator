"""Card filter bar widget for MTG deck builder.

This widget provides all filtering functionality for the Card Management Tab,
including search, type filtering, status filtering, and filter result display.
"""

from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)


class CardFilterBar(QWidget):
    """Filter bar widget for card filtering operations.

    This widget provides controls for:
    1. Card type filtering (All, Creatures, Lands, etc.)
    2. Generation status filtering (All, Completed, Pending, etc.)
    3. Text search across card fields
    4. Filter result display
    5. Reset filters functionality

    All filter changes are communicated via signals to maintain clean separation
    between UI and filtering logic.
    """

    # Filter change signals
    type_filter_changed = pyqtSignal(str)
    status_filter_changed = pyqtSignal(str)
    search_text_changed = pyqtSignal(str)
    reset_filters_requested = pyqtSignal()

    # Filter state signals (for external components that need filter components)
    filter_components_ready = pyqtSignal(QComboBox, QComboBox, QLineEdit, QLabel)

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the card filter bar.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        """Initialize the user interface components."""
        # Main horizontal layout
        filter_layout = QHBoxLayout()
        filter_layout.setContentsMargins(5, 5, 5, 5)

        # Type filter
        filter_layout.addWidget(QLabel("Type:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(
            [
                "All",
                "Creatures",
                "Lands",
                "Instants",
                "Sorceries",
                "Artifacts",
                "Enchantments",
            ]
        )
        self.filter_combo.setToolTip("Filter cards by card type")
        filter_layout.addWidget(self.filter_combo)

        # Status filter
        filter_layout.addWidget(QLabel("Status:"))
        self.status_filter_combo = QComboBox()
        self.status_filter_combo.addItems(
            ["All", "✅ Completed", "⏸️ Pending", "❌ Failed", "🔄 Generating"]
        )
        self.status_filter_combo.setToolTip("Filter cards by generation status")
        filter_layout.addWidget(self.status_filter_combo)

        # Search input
        filter_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search name, cost, type, text...")
        self.search_input.setToolTip(
            "Search across card name, cost, type, and text fields"
        )
        filter_layout.addWidget(self.search_input)

        # Reset button
        self.reset_button = QPushButton("🔄 Reset Filters")
        self.reset_button.setToolTip("Clear all active filters")
        self.reset_button.setStyleSheet(
            """
            QPushButton {
                background-color: #555;
                color: white;
                border: 1px solid #777;
                border-radius: 3px;
                padding: 5px 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #666;
            }
            QPushButton:pressed {
                background-color: #444;
            }
        """
        )
        filter_layout.addWidget(self.reset_button)

        # Filter result label
        self.filter_result_label = QLabel("")
        self.filter_result_label.setStyleSheet(
            """
            QLabel {
                font-weight: bold;
                color: #ff9800;
                padding: 5px;
                background-color: #3a3a3a;
                border: 1px solid #555;
                border-radius: 3px;
                margin-left: 10px;
            }
        """
        )
        self.filter_result_label.setVisible(False)  # Hidden initially
        filter_layout.addWidget(self.filter_result_label)

        # Add stretch to push result label to the right
        filter_layout.addStretch()

        self.setLayout(filter_layout)

    def _connect_signals(self) -> None:
        """Connect UI element signals to emit custom signals."""
        # Filter change signals
        self.filter_combo.currentTextChanged.connect(self.type_filter_changed.emit)
        self.status_filter_combo.currentTextChanged.connect(
            self.status_filter_changed.emit
        )
        self.search_input.textChanged.connect(self.search_text_changed.emit)
        self.reset_button.clicked.connect(self.reset_filters_requested.emit)

        # Also emit the reset signal when reset button is clicked
        self.reset_button.clicked.connect(self._reset_filters)

        # Emit components ready signal after initialization
        self.filter_components_ready.emit(
            self.filter_combo,
            self.status_filter_combo,
            self.search_input,
            self.filter_result_label,
        )

    def _reset_filters(self) -> None:
        """Reset all filters to their default state."""
        # Block signals temporarily to avoid triggering multiple change events
        self.filter_combo.blockSignals(True)
        self.status_filter_combo.blockSignals(True)
        self.search_input.blockSignals(True)

        try:
            # Reset to default values
            self.filter_combo.setCurrentText("All")
            self.status_filter_combo.setCurrentText("All")
            self.search_input.clear()
            self.filter_result_label.setVisible(False)
        finally:
            # Re-enable signals
            self.filter_combo.blockSignals(False)
            self.status_filter_combo.blockSignals(False)
            self.search_input.blockSignals(False)

    def get_filter_components(self) -> tuple[QComboBox, QComboBox, QLineEdit, QLabel]:
        """Get the filter UI components for external use.

        This method provides access to the internal filter components for managers
        that need direct access to the UI elements (like CardTableManager).

        Returns:
            Tuple of (type_filter_combo, status_filter_combo, search_input, result_label)
        """
        return (
            self.filter_combo,
            self.status_filter_combo,
            self.search_input,
            self.filter_result_label,
        )

    def get_current_filters(self) -> dict[str, str]:
        """Get the current state of all filters.

        Returns:
            Dictionary containing current filter values
        """
        return {
            "type_filter": self.filter_combo.currentText(),
            "status_filter": self.status_filter_combo.currentText(),
            "search_text": self.search_input.text(),
        }

    def set_filters(
        self,
        type_filter: str = None,
        status_filter: str = None,
        search_text: str = None,
    ) -> None:
        """Set filter values programmatically.

        Args:
            type_filter: Type filter value (optional)
            status_filter: Status filter value (optional)
            search_text: Search text value (optional)
        """
        # Block signals to avoid triggering change events during programmatic updates
        self.filter_combo.blockSignals(True)
        self.status_filter_combo.blockSignals(True)
        self.search_input.blockSignals(True)

        try:
            if type_filter is not None:
                index = self.filter_combo.findText(type_filter)
                if index >= 0:
                    self.filter_combo.setCurrentIndex(index)

            if status_filter is not None:
                index = self.status_filter_combo.findText(status_filter)
                if index >= 0:
                    self.status_filter_combo.setCurrentIndex(index)

            if search_text is not None:
                self.search_input.setText(search_text)

        finally:
            # Re-enable signals
            self.filter_combo.blockSignals(False)
            self.status_filter_combo.blockSignals(False)
            self.search_input.blockSignals(False)

    def update_filter_result(self, visible_count: int, total_count: int) -> None:
        """Update the filter result display.

        Args:
            visible_count: Number of visible cards after filtering
            total_count: Total number of cards
        """
        if visible_count == total_count:
            # No filtering active or all cards visible
            self.filter_result_label.setVisible(False)
        else:
            # Show filter results
            self.filter_result_label.setText(
                f"Showing {visible_count} of {total_count} cards"
            )
            self.filter_result_label.setVisible(True)

    def set_type_filter_items(self, items: list[str]) -> None:
        """Set the items in the type filter dropdown.

        Args:
            items: List of type filter options
        """
        current_text = self.filter_combo.currentText()
        self.filter_combo.clear()
        self.filter_combo.addItems(items)

        # Try to restore previous selection
        index = self.filter_combo.findText(current_text)
        if index >= 0:
            self.filter_combo.setCurrentIndex(index)

    def set_status_filter_items(self, items: list[str]) -> None:
        """Set the items in the status filter dropdown.

        Args:
            items: List of status filter options
        """
        current_text = self.status_filter_combo.currentText()
        self.status_filter_combo.clear()
        self.status_filter_combo.addItems(items)

        # Try to restore previous selection
        index = self.status_filter_combo.findText(current_text)
        if index >= 0:
            self.status_filter_combo.setCurrentIndex(index)

    def is_filtering_active(self) -> bool:
        """Check if any filters are currently active.

        Returns:
            True if any filter is active, False otherwise
        """
        return (
            self.filter_combo.currentText() != "All"
            or self.status_filter_combo.currentText() != "All"
            or bool(self.search_input.text().strip())
        )

    def set_search_focus(self) -> None:
        """Set focus to the search input field."""
        self.search_input.setFocus()
        self.search_input.selectAll()

    def get_search_text(self) -> str:
        """Get the current search text.

        Returns:
            Current search text
        """
        return self.search_input.text()

    def clear_search(self) -> None:
        """Clear the search text."""
        self.search_input.clear()

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable all filter controls.

        Args:
            enabled: Whether the filter controls should be enabled
        """
        self.filter_combo.setEnabled(enabled)
        self.status_filter_combo.setEnabled(enabled)
        self.search_input.setEnabled(enabled)
        self.reset_button.setEnabled(enabled)
