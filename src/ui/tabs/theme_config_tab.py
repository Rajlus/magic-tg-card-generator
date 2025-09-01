"""Theme configuration tab for MTG deck builder."""

from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.ai_services.ai_worker import AIWorker
from src.domain.models import MTGCard

from ..widgets.color_selector import ColorSelector
from ..widgets.theme_input import ThemeInput


class ThemeConfigTab(QWidget):
    """Tab for theme & configuration selection.

    This tab allows users to:
    1. Select a theme (preset or custom)
    2. Choose color identity for the deck
    3. Set an optional commander
    4. Analyze the theme with AI
    5. Generate a full 100-card Commander deck

    Signals:
        theme_analyzed: Emitted when theme analysis is complete
        cards_generated: Emitted when cards are generated from the theme
    """

    theme_analyzed = pyqtSignal(str)
    cards_generated = pyqtSignal(list)

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the theme configuration tab.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.ai_worker = AIWorker()
        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        """Initialize the user interface components."""
        layout = QVBoxLayout()

        # Theme input widget
        self.theme_input = ThemeInput()
        layout.addWidget(self.theme_input)

        # Color selector widget
        self.color_selector = ColorSelector()
        layout.addWidget(self.color_selector)

        # Deck structure configuration
        config_layout = QHBoxLayout()
        config_layout.addWidget(QLabel("Deck Structure:"))
        self.config_combo = QComboBox()
        self.config_combo.addItems(
            ["standard_commander.yaml", "spell_heavy.yaml", "creature_tribal.yaml"]
        )
        config_layout.addWidget(self.config_combo)
        config_layout.addStretch()
        layout.addLayout(config_layout)

        # Action buttons
        button_layout = QHBoxLayout()
        self.analyze_button = QPushButton(" Analyze Theme")
        self.generate_button = QPushButton(" Generate Full Deck")
        self.generate_button.setEnabled(False)

        button_layout.addWidget(self.analyze_button)
        button_layout.addWidget(self.generate_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Output area for theme analysis
        layout.addWidget(QLabel("Theme Analysis:"))
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMaximumHeight(200)
        layout.addWidget(self.output_text)

        layout.addStretch()
        self.setLayout(layout)

    def _connect_signals(self) -> None:
        """Connect internal signals and slots."""
        # Connect AI worker signals
        self.ai_worker.result_ready.connect(self.on_ai_result)
        self.ai_worker.error_occurred.connect(self.on_ai_error)

        # Connect button signals
        self.analyze_button.clicked.connect(self.analyze_theme)
        self.generate_button.clicked.connect(self.generate_cards)

    def get_theme(self) -> str:
        """Get the selected theme.

        Returns:
            Selected theme string
        """
        return self.theme_input.get_theme()

    def get_commander(self) -> str:
        """Get the entered commander.

        Returns:
            Commander string, or empty if none entered
        """
        # Commander is handled in the card management tab, not here
        return ""

    def get_colors(self) -> list[str]:
        """Get the selected colors.

        Returns:
            List of selected color letters (W, U, B, R, G), or empty list for auto mode
        """
        return self.color_selector.get_colors()

    def get_config(self) -> str:
        """Get the selected deck structure configuration.

        Returns:
            Selected configuration filename
        """
        return self.config_combo.currentText()

    def set_theme(self, theme: str) -> None:
        """Set the theme programmatically.

        Args:
            theme: Theme to set
        """
        self.theme_input.set_theme(theme)

    def set_commander(self, commander: str) -> None:
        """Set the commander programmatically.

        Args:
            commander: Commander to set
        """
        # Commander is handled by separate input field - no action needed

    def set_colors(self, colors: list[str]) -> None:
        """Set the colors programmatically.

        Args:
            colors: List of color letters to set
        """
        self.color_selector.set_colors(colors)

    def analyze_theme(self) -> None:
        """Analyze the selected theme using AI."""
        # Validate input
        theme = self.get_theme()
        if not theme:
            QMessageBox.warning(self, "Warning", "Please enter a theme!")
            return

        # Get parent for logging
        parent = self._get_main_window()
        if parent and hasattr(parent, "log_message"):
            parent.log_message("INFO", f"Starting theme analysis for: {theme}")

        commander = self.get_commander()
        colors = self.get_colors()

        if parent and hasattr(parent, "log_message"):
            if commander:
                parent.log_message("DEBUG", f"Commander specified: {commander}")
            if colors:
                parent.log_message("DEBUG", f"Colors: {', '.join(colors)}")
            else:
                parent.log_message("DEBUG", "Colors: Auto (based on theme)")

        # Build prompt for AI analysis
        prompt = f"Theme: {theme}"
        if commander:
            prompt += f"\\nCommander: {commander}"
        if colors:
            prompt += f"\\nColors: {', '.join(colors)}"

        # Update UI
        self.output_text.append(f"Analyzing theme: {theme}...")
        self.analyze_button.setEnabled(False)

        if parent and hasattr(parent, "log_message"):
            parent.log_message("GENERATING", "Sending theme analysis request to AI...")

        # Start AI analysis
        self.ai_worker.set_task("analyze_theme", prompt)
        self.ai_worker.start()

    def generate_cards(self) -> None:
        """Generate a complete 100-card Commander deck based on the theme."""
        theme = self.get_theme()
        analysis = self.output_text.toPlainText()
        colors = self.get_colors()
        commander = self.get_commander() or f"{theme} Commander"

        # Get parent for logging
        parent = self._get_main_window()
        if parent and hasattr(parent, "log_message"):
            parent.log_message("INFO", "Starting full deck generation")
            parent.log_message("INFO", f"Theme: {theme}")
            parent.log_message("INFO", f"Commander: {commander}")
            parent.log_message(
                "INFO", f"Colors: {', '.join(colors) if colors else 'Auto'}"
            )
            parent.log_message("DEBUG", f"Analysis length: {len(analysis)} characters")

        # Build generation prompt
        prompt = f"""Theme: {theme}
Commander: {commander}
Colors: {', '.join(colors) if colors else 'Based on theme'}

{analysis}

NOW GENERATE ALL 100 CARDS:
Start with card 1 (the commander) and continue through card 100.
Remember the exact distribution: 1 commander, 37 lands, 30 creatures, 10 instants, 10 sorceries, 7 artifacts, 5 enchantments.
Generate them in order as specified in the system prompt.
DO NOT STOP until you reach card 100."""

        # Update UI
        self.output_text.append("\\nGenerating 100 cards (this may take a moment)...")
        self.generate_button.setEnabled(False)

        if parent and hasattr(parent, "log_message"):
            parent.log_message("GENERATING", "Requesting 100 cards from AI...")
            parent.log_message(
                "DEBUG",
                "Expected: 1 commander, 37 lands, 30 creatures, 10 instants, 10 sorceries, 7 artifacts, 5 enchantments",
            )

        # Start card generation
        self.ai_worker.set_task("generate_cards", prompt)
        self.ai_worker.start()

    def on_ai_result(self, result: str) -> None:
        """Handle AI response.

        Args:
            result: AI response text
        """
        if self.ai_worker.task == "analyze_theme":
            self.output_text.clear()
            self.output_text.append(result)
            self.analyze_button.setEnabled(True)
            self.generate_button.setEnabled(True)
            self.theme_analyzed.emit(result)
        elif self.ai_worker.task == "generate_cards":
            # Parse the generated cards
            cards = self.parse_cards(result)
            self.output_text.append(f"\\n Generated {len(cards)} cards")

            # Emit cards directly without art descriptions (will be generated on demand)
            self.cards_generated.emit(cards)
            self.generate_button.setEnabled(True)

            if len(cards) < 100:
                QMessageBox.warning(
                    self,
                    "Incomplete Generation",
                    f"Only {len(cards)} cards generated. Expected 100.\\nTry generating again.",
                )
            else:
                QMessageBox.information(
                    self, "Success", f"Generated {len(cards)} cards!"
                )

    def on_ai_error(self, error: str) -> None:
        """Handle AI error.

        Args:
            error: Error message
        """
        QMessageBox.critical(self, "Error", error)
        self.analyze_button.setEnabled(True)
        self.generate_button.setEnabled(True)

    def parse_cards(self, text: str) -> list[MTGCard]:
        """Parse AI response into card objects.

        Args:
            text: AI response text containing card data

        Returns:
            List of parsed MTGCard objects
        """
        parent = self._get_main_window()
        if parent and hasattr(parent, "log_message"):
            parent.log_message("DEBUG", f"Parsing AI response: {len(text)} characters")

        cards = []
        lines = text.split("\\n")

        if parent and hasattr(parent, "log_message"):
            parent.log_message("DEBUG", f"Response has {len(lines)} lines")

        current_card = {}
        card_id = 1

        for line in lines:
            line = line.strip()

            # Check for card number and name
            if line and line[0].isdigit() and ". " in line:
                # Save previous card if exists
                if current_card and "name" in current_card:
                    card = MTGCard(
                        id=card_id,
                        name=current_card.get("name", ""),
                        type=current_card.get("type", ""),
                        cost=current_card.get("cost", ""),
                        text=current_card.get("text", ""),
                        power=current_card.get("power"),
                        toughness=current_card.get("toughness"),
                        flavor=current_card.get("flavor", ""),
                        rarity=current_card.get("rarity", "common"),
                        art="",  # Will be generated separately
                    )
                    cards.append(card)
                    card_id += 1

                # Parse new card name and type
                parts = line.split(". ", 1)[1].split(" | ")
                if len(parts) == 2:
                    current_card = {"name": parts[0].strip(), "type": parts[1].strip()}

            # Parse card attributes
            elif line.startswith("Cost:"):
                current_card["cost"] = line.replace("Cost:", "").strip()
            elif line.startswith("Text:"):
                current_card["text"] = line.replace("Text:", "").strip()
            elif line.startswith("P/T:"):
                pt = line.replace("P/T:", "").strip()
                if pt != "-" and "/" in pt:
                    parts = pt.split("/")
                    try:
                        current_card["power"] = int(parts[0])
                        current_card["toughness"] = int(parts[1])
                    except ValueError:
                        pass
            elif line.startswith("Flavor:"):
                current_card["flavor"] = line.replace("Flavor:", "").strip()
            elif line.startswith("Rarity:"):
                current_card["rarity"] = line.replace("Rarity:", "").strip().lower()

        # Add last card
        if current_card and "name" in current_card:
            card = MTGCard(
                id=card_id,
                name=current_card.get("name", ""),
                type=current_card.get("type", ""),
                cost=current_card.get("cost", ""),
                text=current_card.get("text", ""),
                power=current_card.get("power"),
                toughness=current_card.get("toughness"),
                flavor=current_card.get("flavor", ""),
                rarity=current_card.get("rarity", "common"),
                art="",
            )
            cards.append(card)

        return cards

    def _get_main_window(self) -> Optional[QWidget]:
        """Get reference to the main window for logging.

        Returns:
            Main window widget, or None if not found
        """
        return self.parent().parent() if hasattr(self, "parent") else None

    def _validate_theme_input(self) -> tuple[bool, str]:
        """
        Validate theme input.

        Returns:
            Tuple of (is_valid, error_message). If valid, error_message is empty.
        """
        theme = self.get_theme()
        if not theme or not theme.strip():
            return False, "Theme cannot be empty"

        return True, ""

    def validate_configuration(self) -> tuple[bool, str]:
        """Validate the current configuration state.

        Returns:
            Tuple of (is_valid, error_message). If valid, error_message is empty.
        """
        # Validate theme input
        theme_valid, theme_error = self._validate_theme_input()
        if not theme_valid:
            return False, theme_error

        return True, ""

    def get_configuration_summary(self) -> dict:
        """Get a summary of the current configuration.

        Returns:
            Dictionary containing configuration details
        """
        return {
            "theme": self.get_theme(),
            "commander": self.get_commander(),
            "colors": self.get_colors(),
            "config": self.get_config(),
            "color_mode": "auto"
            if self.color_selector.is_auto_mode()
            else "manual"
            if self.color_selector.is_manual_mode()
            else "preset",
            "theme_mode": "preset" if self.theme_input.is_preset_mode() else "custom",
        }
