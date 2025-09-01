"""
Color Selector Widget

A reusable widget for selecting MTG color combinations.
Supports auto, manual, and preset color selection modes.
"""


from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)


class ColorSelector(QWidget):
    """
    Reusable color selection widget for MTG color identity.

    Provides three modes:
    - Auto: Colors determined by theme analysis
    - Manual: Individual color checkboxes
    - Preset: Common color combinations
    """

    # Signal emitted when color selection changes
    colors_changed = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()

        # Color selection mode radio buttons
        self.auto_color_radio = QRadioButton("Auto (based on theme)")
        self.manual_color_radio = QRadioButton("Manual Selection:")
        self.preset_color_radio = QRadioButton("Preset Combination:")
        self.auto_color_radio.setChecked(True)

        layout.addWidget(self.auto_color_radio)
        layout.addWidget(self.manual_color_radio)

        # Manual color checkboxes
        self._setup_manual_colors(layout)

        layout.addWidget(self.preset_color_radio)

        # Preset combinations
        self._setup_preset_colors(layout)

        self.setLayout(layout)

    def _setup_manual_colors(self, layout: QVBoxLayout):
        """Setup manual color selection checkboxes."""
        color_checkbox_layout = QHBoxLayout()

        self.color_checkboxes = {
            "W": QCheckBox("W (White)"),
            "U": QCheckBox("U (Blue)"),
            "B": QCheckBox("B (Black)"),
            "R": QCheckBox("R (Red)"),
            "G": QCheckBox("G (Green)"),
        }

        for checkbox in self.color_checkboxes.values():
            checkbox.setEnabled(False)
            color_checkbox_layout.addWidget(checkbox)

        layout.addLayout(color_checkbox_layout)

    def _setup_preset_colors(self, layout: QVBoxLayout):
        """Setup preset color combination dropdown."""
        self.preset_color_combo = QComboBox()
        self.preset_color_combo.addItems(
            [
                "Azorius (WU)",
                "Dimir (UB)",
                "Rakdos (BR)",
                "Gruul (RG)",
                "Selesnya (WG)",
                "Orzhov (WB)",
                "Izzet (UR)",
                "Golgari (BG)",
                "Boros (WR)",
                "Simic (UG)",
                "Bant (WUG)",
                "Esper (WUB)",
                "Grixis (UBR)",
                "Jund (BRG)",
                "Naya (WRG)",
                "WUBRG (All colors)",
            ]
        )
        self.preset_color_combo.setEnabled(False)

        layout.addWidget(self.preset_color_combo)

    def _connect_signals(self):
        """Connect signals for radio button and checkbox interactions."""
        # Radio button toggling
        self.manual_color_radio.toggled.connect(self._toggle_manual_colors)
        self.preset_color_radio.toggled.connect(self._toggle_preset_colors)

        # Color change notifications
        for checkbox in self.color_checkboxes.values():
            checkbox.toggled.connect(self._on_colors_changed)
        self.preset_color_combo.currentTextChanged.connect(self._on_colors_changed)

        # Mode change notifications
        self.auto_color_radio.toggled.connect(self._on_colors_changed)
        self.manual_color_radio.toggled.connect(self._on_colors_changed)
        self.preset_color_radio.toggled.connect(self._on_colors_changed)

    def _toggle_manual_colors(self, checked: bool):
        """Enable/disable manual color checkboxes."""
        for checkbox in self.color_checkboxes.values():
            checkbox.setEnabled(checked)

    def _toggle_preset_colors(self, checked: bool):
        """Enable/disable preset color combo."""
        self.preset_color_combo.setEnabled(checked)

    def _on_colors_changed(self):
        """Emit signal when colors change."""
        colors = self.get_colors()
        self.colors_changed.emit(colors)

    def get_colors(self) -> list[str]:
        """
        Get the currently selected colors.

        Returns:
            List of color strings (W, U, B, R, G) or empty list for auto mode.
        """
        if self.auto_color_radio.isChecked():
            return []  # Will be determined by AI
        elif self.manual_color_radio.isChecked():
            return self._get_manual_colors()
        else:  # preset_color_radio is checked
            return self._get_preset_colors()

    def _get_manual_colors(self) -> list[str]:
        """Get colors from manual checkboxes."""
        colors = []
        for color, checkbox in self.color_checkboxes.items():
            if checkbox.isChecked():
                colors.append(color)
        return colors

    def _get_preset_colors(self) -> list[str]:
        """Parse colors from preset combination."""
        combo_text = self.preset_color_combo.currentText()

        # Color combination mappings
        color_mappings = {
            "WU": ["W", "U"],
            "UB": ["U", "B"],
            "BR": ["B", "R"],
            "RG": ["R", "G"],
            "WG": ["W", "G"],
            "WB": ["W", "B"],
            "UR": ["U", "R"],
            "BG": ["B", "G"],
            "WR": ["W", "R"],
            "UG": ["U", "G"],
            "WUG": ["W", "U", "G"],
            "WUB": ["W", "U", "B"],
            "UBR": ["U", "B", "R"],
            "BRG": ["B", "R", "G"],
            "WRG": ["W", "R", "G"],
            "WUBRG": ["W", "U", "B", "R", "G"],
        }

        for pattern, colors in color_mappings.items():
            if pattern in combo_text:
                return colors

        return []

    def set_colors(self, colors: list[str]):
        """
        Set the selected colors programmatically.

        Args:
            colors: List of color strings to select
        """
        if not colors:
            self.auto_color_radio.setChecked(True)
        else:
            # Check if it matches a preset combination
            preset_match = self._find_preset_match(colors)
            if preset_match:
                self.preset_color_radio.setChecked(True)
                self.preset_color_combo.setCurrentText(preset_match)
            else:
                # Use manual selection
                self.manual_color_radio.setChecked(True)
                for color, checkbox in self.color_checkboxes.items():
                    checkbox.setChecked(color in colors)

    def _find_preset_match(self, colors: list[str]) -> str:
        """Find a preset combination that matches the given colors."""
        sorted_colors = sorted(colors)

        preset_mappings = {
            "['U', 'W']": "Azorius (WU)",
            "['B', 'U']": "Dimir (UB)",
            "['B', 'R']": "Rakdos (BR)",
            "['G', 'R']": "Gruul (RG)",
            "['G', 'W']": "Selesnya (WG)",
            "['B', 'W']": "Orzhov (WB)",
            "['R', 'U']": "Izzet (UR)",
            "['B', 'G']": "Golgari (BG)",
            "['R', 'W']": "Boros (WR)",
            "['G', 'U']": "Simic (UG)",
            "['G', 'U', 'W']": "Bant (WUG)",
            "['B', 'U', 'W']": "Esper (WUB)",
            "['B', 'R', 'U']": "Grixis (UBR)",
            "['B', 'G', 'R']": "Jund (BRG)",
            "['G', 'R', 'W']": "Naya (WRG)",
            "['B', 'G', 'R', 'U', 'W']": "WUBRG (All colors)",
        }

        return preset_mappings.get(str(sorted_colors), "")

    def get_selection_mode(self) -> str:
        """
        Get the current selection mode.

        Returns:
            'auto', 'manual', or 'preset'
        """
        if self.auto_color_radio.isChecked():
            return "auto"
        elif self.manual_color_radio.isChecked():
            return "manual"
        else:
            return "preset"
