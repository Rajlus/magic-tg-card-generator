"""
Theme Input Widget

A reusable widget for theme selection supporting both preset themes
and custom theme input.
"""

from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QComboBox, QLineEdit, QRadioButton, QVBoxLayout, QWidget


class ThemeInput(QWidget):
    """
    Reusable theme input widget.

    Provides two modes:
    - Preset: Selection from predefined themes
    - Custom: Free text input for custom themes
    """

    # Signal emitted when theme changes
    theme_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()

        # Theme selection mode radio buttons
        self.preset_radio = QRadioButton("Preset Theme:")
        self.custom_radio = QRadioButton("Custom Theme:")
        self.preset_radio.setChecked(True)

        layout.addWidget(self.preset_radio)

        # Preset theme dropdown
        self._setup_preset_themes(layout)

        layout.addWidget(self.custom_radio)

        # Custom theme input
        self._setup_custom_input(layout)

        self.setLayout(layout)

    def _setup_preset_themes(self, layout: QVBoxLayout):
        """Setup preset theme dropdown."""
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(
            [
                "Percy Jackson",
                "Harry Potter",
                "Lord of the Rings",
                "Star Wars",
                "Marvel",
                "Game of Thrones",
                "Avatar (ATLA)",
                "Witcher",
                "Pokemon",
                "Final Fantasy",
                "World of Warcraft",
                "Dungeons & Dragons",
                "Norse Mythology",
                "Greek Mythology",
                "Egyptian Mythology",
            ]
        )

        layout.addWidget(self.preset_combo)

    def _setup_custom_input(self, layout: QVBoxLayout):
        """Setup custom theme input field."""
        self.custom_input = QLineEdit()
        self.custom_input.setPlaceholderText("Enter your custom theme...")
        self.custom_input.setEnabled(False)

        layout.addWidget(self.custom_input)

    def _connect_signals(self):
        """Connect signals for radio button and input interactions."""
        # Radio button toggling
        self.preset_radio.toggled.connect(self._toggle_preset_mode)
        self.custom_radio.toggled.connect(self._toggle_custom_mode)

        # Theme change notifications
        self.preset_combo.currentTextChanged.connect(self._on_theme_changed)
        self.custom_input.textChanged.connect(self._on_theme_changed)

    def _toggle_preset_mode(self, checked: bool):
        """Enable/disable preset theme selection."""
        self.preset_combo.setEnabled(checked)

    def _toggle_custom_mode(self, checked: bool):
        """Enable/disable custom theme input."""
        self.custom_input.setEnabled(checked)

    def _on_theme_changed(self):
        """Emit signal when theme changes."""
        theme = self.get_theme()
        if theme:  # Only emit if there's a valid theme
            self.theme_changed.emit(theme)

    def get_theme(self) -> str:
        """
        Get the currently selected theme.

        Returns:
            The selected theme string, or empty string if none selected.
        """
        if self.preset_radio.isChecked():
            return self.preset_combo.currentText()
        else:
            return self.custom_input.text().strip()

    def set_theme(self, theme: str):
        """
        Set the theme programmatically.

        Args:
            theme: Theme name to select
        """
        # Check if it's a preset theme
        preset_index = self.preset_combo.findText(theme)
        if preset_index >= 0:
            self.preset_radio.setChecked(True)
            self.preset_combo.setCurrentIndex(preset_index)
        else:
            # Use custom input
            self.custom_radio.setChecked(True)
            self.custom_input.setText(theme)

    def get_selection_mode(self) -> str:
        """
        Get the current selection mode.

        Returns:
            'preset' or 'custom'
        """
        return "preset" if self.preset_radio.isChecked() else "custom"

    def add_preset_theme(self, theme: str):
        """
        Add a new preset theme option.

        Args:
            theme: Theme name to add to presets
        """
        if self.preset_combo.findText(theme) == -1:
            self.preset_combo.addItem(theme)

    def remove_preset_theme(self, theme: str):
        """
        Remove a preset theme option.

        Args:
            theme: Theme name to remove from presets
        """
        index = self.preset_combo.findText(theme)
        if index >= 0:
            self.preset_combo.removeItem(index)

    def get_preset_themes(self) -> list[str]:
        """
        Get all available preset themes.

        Returns:
            List of preset theme names
        """
        return [self.preset_combo.itemText(i) for i in range(self.preset_combo.count())]

    def clear_custom_input(self):
        """Clear the custom theme input field."""
        self.custom_input.clear()

    def is_theme_valid(self) -> bool:
        """
        Check if the current theme selection is valid.

        Returns:
            True if a valid theme is selected, False otherwise
        """
        theme = self.get_theme()
        return bool(theme and theme.strip())

    def set_placeholder_text(self, text: str):
        """
        Set the placeholder text for custom input.

        Args:
            text: Placeholder text to display
        """
        self.custom_input.setPlaceholderText(text)
