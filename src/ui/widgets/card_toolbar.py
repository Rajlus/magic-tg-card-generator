"""Card toolbar widget for MTG deck builder.

This widget provides all toolbar functionality for the Card Management Tab,
including deck operations, import/export, and generation controls.
"""

from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)


class CardToolbar(QWidget):
    """Toolbar widget for card management operations.

    This widget provides buttons and controls for:
    1. Deck loading and reloading
    2. CSV import/export
    3. Card generation controls
    4. Configuration access
    5. Auto-save status display

    All operations are communicated via signals to maintain clean separation
    between UI and business logic.
    """

    # File operation signals
    load_deck_requested = pyqtSignal()
    reload_deck_requested = pyqtSignal()

    # Import/Export signals
    import_csv_requested = pyqtSignal()
    export_csv_requested = pyqtSignal()

    # Generation signals
    generate_all_requested = pyqtSignal()

    # Configuration signals
    toggle_config_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the card toolbar.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        """Initialize the user interface components."""
        # Main horizontal layout
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(0, 0, 0, 0)

        # File operation buttons
        self.load_button = QPushButton("📁 Load Deck")
        self.load_button.setToolTip("Load deck from file")

        self.reload_button = QPushButton("🔄 Reload (F5)")
        self.reload_button.setToolTip("Reload current deck from file (F5)")
        self.reload_button.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; font-weight: bold; padding: 5px; }"
        )

        # Auto-save indicator
        self.auto_save_label = QLabel("💾 Auto-Save: Active")
        self.auto_save_label.setStyleSheet(
            "color: #4ec9b0; font-weight: bold; padding: 5px;"
        )

        # CSV Import/Export buttons
        self.csv_import_button = QPushButton("📥 Import CSV")
        self.csv_import_button.setToolTip("Import deck from CSV file")

        self.csv_export_button = QPushButton("📤 Export CSV")
        self.csv_export_button.setToolTip("Export deck to CSV file")

        # Generate All button
        self.generate_all_btn = QPushButton("🚀 Generate All")
        self.generate_all_btn.setStyleSheet(
            "QPushButton { font-weight: bold; padding: 6px; background-color: #4CAF50; }"
        )
        self.generate_all_btn.setToolTip("Generate all pending cards")

        # Configuration button
        self.config_button = QPushButton("⚙️ Config")
        self.config_button.setToolTip("Toggle generation settings")

        # Add widgets to layout
        toolbar_layout.addWidget(self.load_button)
        toolbar_layout.addWidget(self.reload_button)
        toolbar_layout.addWidget(self.auto_save_label)
        toolbar_layout.addWidget(self.csv_import_button)
        toolbar_layout.addWidget(self.csv_export_button)
        toolbar_layout.addStretch()  # Push generation and config buttons to the right
        toolbar_layout.addWidget(self.generate_all_btn)
        toolbar_layout.addWidget(self.config_button)

        self.setLayout(toolbar_layout)

    def _connect_signals(self) -> None:
        """Connect button signals to emit custom signals."""
        # File operation signals
        self.load_button.clicked.connect(self.load_deck_requested.emit)
        self.reload_button.clicked.connect(self.reload_deck_requested.emit)

        # Import/Export signals
        self.csv_import_button.clicked.connect(self.import_csv_requested.emit)
        self.csv_export_button.clicked.connect(self.export_csv_requested.emit)

        # Generation signals
        self.generate_all_btn.clicked.connect(self.generate_all_requested.emit)

        # Configuration signals
        self.config_button.clicked.connect(self.toggle_config_requested.emit)

    def set_auto_save_status(self, is_active: bool) -> None:
        """Update the auto-save status indicator.

        Args:
            is_active: Whether auto-save is currently active
        """
        if is_active:
            self.auto_save_label.setText("💾 Auto-Save: Active")
            self.auto_save_label.setStyleSheet(
                "color: #4ec9b0; font-weight: bold; padding: 5px;"
            )
        else:
            self.auto_save_label.setText("💾 Auto-Save: Inactive")
            self.auto_save_label.setStyleSheet(
                "color: #f44336; font-weight: bold; padding: 5px;"
            )

    def set_reload_enabled(self, enabled: bool) -> None:
        """Enable or disable the reload button.

        Args:
            enabled: Whether the reload button should be enabled
        """
        self.reload_button.setEnabled(enabled)

    def set_generation_enabled(self, enabled: bool) -> None:
        """Enable or disable the generation button.

        Args:
            enabled: Whether the generate all button should be enabled
        """
        self.generate_all_btn.setEnabled(enabled)

    def set_export_enabled(self, enabled: bool) -> None:
        """Enable or disable the export button.

        Args:
            enabled: Whether the CSV export button should be enabled
        """
        self.csv_export_button.setEnabled(enabled)

    def update_config_button_state(self, is_expanded: bool) -> None:
        """Update the config button text to show current state.

        Args:
            is_expanded: Whether the configuration panel is currently expanded
        """
        if is_expanded:
            self.config_button.setText("⚙️ Config ▼")
        else:
            self.config_button.setText("⚙️ Config ▲")

    def get_button_states(self) -> dict:
        """Get the current enabled/disabled state of all buttons.

        Returns:
            Dictionary containing button states for debugging/testing
        """
        return {
            "load_enabled": self.load_button.isEnabled(),
            "reload_enabled": self.reload_button.isEnabled(),
            "import_enabled": self.csv_import_button.isEnabled(),
            "export_enabled": self.csv_export_button.isEnabled(),
            "generate_enabled": self.generate_all_btn.isEnabled(),
            "config_enabled": self.config_button.isEnabled(),
        }

    def set_all_buttons_enabled(self, enabled: bool) -> None:
        """Enable or disable all toolbar buttons at once.

        Args:
            enabled: Whether all buttons should be enabled
        """
        self.load_button.setEnabled(enabled)
        self.reload_button.setEnabled(enabled)
        self.csv_import_button.setEnabled(enabled)
        self.csv_export_button.setEnabled(enabled)
        self.generate_all_btn.setEnabled(enabled)
        self.config_button.setEnabled(enabled)
