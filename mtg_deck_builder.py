#!/usr/bin/env python3
"""
MTG Commander Deck Builder GUI
Complete tool for generating 100-card Commander decks with AI assistance
"""

import contextlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
import yaml

# Import environment variables
from dotenv import load_dotenv
from PyQt6.QtCore import QSettings, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.managers.card_file_operations import CardFileOperations
from src.managers.card_generation_controller import (
    CardGenerationController,
    CardGeneratorWorker,
)
from src.managers.card_table_manager import CardTableManager
from src.managers.card_validation_manager import CardValidationManager

load_dotenv()


# Helper functions
def make_safe_filename(name: str) -> str:
    """Convert a card name to a safe filename, matching generate_card.py logic."""
    safe_name = name
    # Replace problematic characters with underscores
    for char in [
        "/",
        "\\",
        ":",
        "*",
        "?",
        '"',
        "<",
        ">",
        "|",
        "\u202f",
        "\u00a0",
        "—",
        "–",
    ]:
        safe_name = safe_name.replace(char, "_")
    # Replace spaces, commas, and apostrophes
    safe_name = safe_name.replace(" ", "_").replace(",", "").replace("'", "")
    return safe_name


def escape_for_shell(text: str) -> str:
    """Escape text for shell command"""
    # Replace double quotes with escaped double quotes
    text = str(text).replace('"', '\\"')
    # Return with double quotes around it
    return f'"{text}"'


def convert_mana_cost(cost) -> str:
    """Convert mana cost from compact format (2UR) to MTG format ({2}{U}{R})."""
    # Convert to string if it's an integer
    cost = str(cost) if cost is not None else ""

    if not cost or cost == "-" or cost == "":
        return ""

    # If already in the correct format, return as is
    if "{" in cost and "}" in cost:
        return cost

    # Convert compact format to MTG format
    result = ""
    i = 0
    while i < len(cost):
        char = cost[i]
        # Check if it's a number (generic mana)
        if char.isdigit():
            # Look ahead for multi-digit numbers
            j = i
            while j < len(cost) and cost[j].isdigit():
                j += 1
            result += "{" + cost[i:j] + "}"
            i = j
        # Check if it's a mana symbol (W, U, B, R, G, C, X)
        elif char.upper() in "WUBRGCX":
            result += "{" + char.upper() + "}"
            i += 1
        else:
            # Skip unknown characters
            i += 1

    return result


def get_main_window():
    """Safely get the main window instance for logging."""
    for widget in QApplication.topLevelWidgets():
        if isinstance(widget, QMainWindow):
            return widget
    return None


# Data classes for card structure
@dataclass
class MTGCard:
    """Represents a single MTG card with all attributes"""

    id: int
    name: str
    type: str
    cost: str = ""
    text: str = ""
    power: Optional[int] = None
    toughness: Optional[int] = None
    flavor: str = ""
    rarity: str = "common"
    art: str = ""
    set: str = "CMD"  # Card set, defaults to Commander
    status: str = "pending"  # pending, generating, completed, failed
    image_path: Optional[str] = None  # Path to card artwork image
    card_path: Optional[str] = None  # Path to full card image
    generated_at: Optional[str] = None  # Timestamp when generated
    generation_status: str = "pending"  # For tracking individual generation
    custom_image_path: Optional[str] = None  # Path to custom uploaded image

    def is_creature(self) -> bool:
        # Check for both English and German, including compound words
        type_lower = self.type.lower()
        return any(word in type_lower for word in ["creature", "kreatur"])

    def is_land(self) -> bool:
        # Works for both English and German (both use "Land")
        return "Land" in self.type

    def get_command(self, model: str = "sdxl", style: str = "mtg_modern") -> str:
        """Generate the command for generate_card.py"""
        # Use unbuffered Python output (-u flag) to ensure logs are captured immediately
        cmd_parts = ["poetry", "run", "python", "-u", "generate_card.py"]

        # Add name
        cmd_parts.extend(["--name", escape_for_shell(self.name)])

        # Add cost if not a land (lands have no mana cost)
        if not self.is_land() and self.cost:
            # Convert mana cost to proper MTG format
            formatted_cost = convert_mana_cost(self.cost)
            if formatted_cost:
                cmd_parts.extend(["--cost", escape_for_shell(formatted_cost)])

        # Add type
        cmd_parts.extend(["--type", escape_for_shell(self.type)])

        # Add text - ALWAYS include text, even for lands
        if self.text:
            cmd_parts.extend(["--text", escape_for_shell(self.text)])

        # Add P/T if creature - with debug logging
        if self.is_creature():
            # Always add P/T for creatures, even if values might be None
            if self.power is not None and self.toughness is not None:
                cmd_parts.extend(["--power", str(self.power)])
                cmd_parts.extend(["--toughness", str(self.toughness)])
            else:
                # Log error - creature MUST have P/T
                print(
                    f"ERROR: Creature '{self.name}' has invalid P/T: power={self.power}, toughness={self.toughness}"
                )
                # Still try to add what we have to avoid black card
                if self.power is not None:
                    cmd_parts.extend(["--power", str(self.power)])
                if self.toughness is not None:
                    cmd_parts.extend(["--toughness", str(self.toughness)])

        # Add flavor if exists
        if self.flavor:
            cmd_parts.extend(["--flavor", escape_for_shell(self.flavor)])

        # Add rarity
        cmd_parts.extend(["--rarity", self.rarity])

        # Add art description
        if self.art:
            cmd_parts.extend(["--art", escape_for_shell(self.art)])

        # Add model and style
        cmd_parts.extend(["--model", model])
        cmd_parts.extend(["--style", style])

        # Add custom image path if provided
        if hasattr(self, "custom_image_path") and self.custom_image_path:
            cmd_parts.extend(
                ["--custom-image", escape_for_shell(str(self.custom_image_path))]
            )

        return " ".join(cmd_parts)


class AIWorker(QThread):
    """Worker thread for AI API calls"""

    result_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    progress_update = pyqtSignal(str)
    log_message = pyqtSignal(str, str)  # level, message - for thread-safe logging

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv(
            "OPENROUTER_API_KEY",
            "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",
        )
        self.model = "openai/gpt-oss-120b"
        self.task = ""
        self.prompt = ""

    def set_task(self, task: str, prompt: str):
        self.task = task
        self.prompt = prompt

    def run(self):
        """Execute AI request"""
        try:
            # Note: We can't directly access GUI elements from worker thread
            # Use signals instead for thread-safe communication

            # Set parameters based on task
            temperature = 0.7
            max_tokens = 32000 if self.task == "generate_cards" else 4000
            timeout = 120 if self.task == "generate_cards" else 60

            # Log AI call parameters
            self.log_message.emit("GENERATING", f"AI Call: {self.task}")
            self.log_message.emit(
                "DEBUG",
                f"Parameters: model={self.model}, max_tokens={max_tokens}, temperature={temperature}, timeout={timeout}s",
            )

            self.progress_update.emit(f"Calling {self.model}...")

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            # Different system prompts based on task
            if self.task == "analyze_theme":
                system_prompt = self.get_theme_analyzer_prompt()
            elif self.task == "generate_cards":
                system_prompt = self.get_card_generator_prompt()
            elif self.task == "generate_art":
                system_prompt = self.get_art_description_prompt()
            else:
                system_prompt = "You are a helpful assistant."

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": self.prompt},
            ]

            # Log request size
            request_size = len(json.dumps(messages))
            self.log_message.emit("DEBUG", f"Request size: {request_size} characters")

            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=timeout,
            )

            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]

                # Log response info
                usage = data.get("usage", {})
                tokens_used = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)

                self.log_message.emit(
                    "SUCCESS",
                    f"Response received: {tokens_used} completion tokens, {total_tokens} total tokens",
                )

                # Calculate and log cost
                if self.model == "openai/gpt-oss-120b":
                    # Pricing per 1M tokens
                    input_cost = (usage.get("prompt_tokens", 0) / 1_000_000) * 0.072
                    output_cost = (tokens_used / 1_000_000) * 0.28
                    total_cost = input_cost + output_cost
                    self.log_message.emit(
                        "INFO",
                        f"API Cost: ${total_cost:.4f} (Input: ${input_cost:.4f}, Output: ${output_cost:.4f})",
                    )

                self.result_ready.emit(content)
            else:
                error_msg = f"API Error {response.status_code}: {response.text[:200]}"
                self.log_message.emit("ERROR", error_msg)
                self.error_occurred.emit(error_msg)

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.log_message.emit("ERROR", error_msg)
            self.error_occurred.emit(error_msg)

    def get_theme_analyzer_prompt(self) -> str:
        """System prompt for theme analysis"""
        return """You are an MTG Set Design Expert. Analyze the given theme and provide:
1. Color Identity (primary and secondary colors with reasoning)
2. Suggested Commander(s)
3. Key mechanics that fit the theme
4. Important characters/locations for legendary cards
5. Overall deck strategy

Format your response clearly with sections."""

    def get_card_generator_prompt(self) -> str:
        """System prompt for generating 100 cards"""
        return """You MUST generate EXACTLY 100 unique MTG cards for a Commander deck. DO NOT STOP until you have generated all 100 cards.

REQUIRED DISTRIBUTION (MUST generate exactly these amounts):
- Card 1: Commander (Legendary Creature)
- Cards 2-38: Lands (37 total)
- Cards 39-68: Creatures (30 total)
- Cards 69-78: Instants (10 total)
- Cards 79-88: Sorceries (10 total)
- Cards 89-95: Artifacts (7 total)
- Cards 96-100: Enchantments (5 total)

For EACH card provide ALL fields in this EXACT format:
[NUMBER]. [NAME] | [TYPE]
Cost: [COST or "-" for lands]
Text: [ABILITIES]
P/T: [X/X for creatures or "-" for non-creatures]
Flavor: [FLAVOR TEXT]
Rarity: [mythic/rare/uncommon/common]

IMPORTANT:
- Number cards from 1 to 100
- DO NOT STOP before card 100
- Keep responses concise but complete
- Ensure thematic consistency"""

    def get_art_description_prompt(self) -> str:
        """System prompt for art descriptions"""
        return """You are an expert at creating detailed art descriptions for MTG cards.

CRITICAL RULES for fandom characters:
1. Percy Jackson: Teenage characters in MODERN clothing (Camp Half-Blood orange t-shirts, jeans, sneakers). NO ARMOR.
2. Harry Potter: Hogwarts robes OR modern muggle clothes. Wands, not medieval weapons.
3. Marvel/DC: Canonical superhero costumes or civilian clothes from comics/movies.
4. Star Wars: Exact movie/show appearances (Jedi robes, rebel uniforms, etc).

For EACH card, create a 2-3 sentence visual description that:
- Captures the character's canonical appearance
- Describes the scene/action if relevant
- Uses vivid, specific details for AI image generation
- Maintains thematic consistency

Format: [NUMBER]. [DETAILED ART DESCRIPTION]"""


# CardGeneratorWorker class moved to src/managers/card_generation_controller.py


class ThemeConfigTab(QWidget):
    """Tab 1: Theme & Configuration"""

    theme_analyzed = pyqtSignal(str)
    cards_generated = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.ai_worker = AIWorker()
        self.ai_worker.result_ready.connect(self.on_ai_result)
        self.ai_worker.error_occurred.connect(self.on_ai_error)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Theme Selection Group
        theme_group = QGroupBox("Theme Selection")
        theme_layout = QVBoxLayout()

        # Preset vs Custom
        self.preset_radio = QRadioButton("Preset Theme:")
        self.custom_radio = QRadioButton("Custom Theme:")
        self.preset_radio.setChecked(True)

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
            ]
        )

        self.custom_input = QLineEdit()
        self.custom_input.setPlaceholderText("Enter your custom theme...")
        self.custom_input.setEnabled(False)

        # Connect radio buttons
        self.preset_radio.toggled.connect(
            lambda checked: self.preset_combo.setEnabled(checked)
        )
        self.custom_radio.toggled.connect(
            lambda checked: self.custom_input.setEnabled(checked)
        )

        theme_layout.addWidget(self.preset_radio)
        theme_layout.addWidget(self.preset_combo)
        theme_layout.addWidget(self.custom_radio)
        theme_layout.addWidget(self.custom_input)

        # Commander input
        commander_label = QLabel("Commander (optional):")
        self.commander_input = QLineEdit()
        self.commander_input.setPlaceholderText("e.g., Percy Jackson, Son of Poseidon")
        theme_layout.addWidget(commander_label)
        theme_layout.addWidget(self.commander_input)

        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)

        # Color Identity Group
        color_group = QGroupBox("Color Identity")
        color_layout = QVBoxLayout()

        self.auto_color_radio = QRadioButton("Auto (based on theme)")
        self.manual_color_radio = QRadioButton("Manual Selection:")
        self.preset_color_radio = QRadioButton("Preset Combination:")
        self.auto_color_radio.setChecked(True)

        # Manual color checkboxes
        color_checkbox_layout = QHBoxLayout()
        self.color_w = QCheckBox("W (White)")
        self.color_u = QCheckBox("U (Blue)")
        self.color_b = QCheckBox("B (Black)")
        self.color_r = QCheckBox("R (Red)")
        self.color_g = QCheckBox("G (Green)")

        for cb in [
            self.color_w,
            self.color_u,
            self.color_b,
            self.color_r,
            self.color_g,
        ]:
            cb.setEnabled(False)
            color_checkbox_layout.addWidget(cb)

        # Preset combinations
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

        # Connect radio buttons
        self.manual_color_radio.toggled.connect(self.toggle_color_selection)
        self.preset_color_radio.toggled.connect(
            lambda checked: self.preset_color_combo.setEnabled(checked)
        )

        color_layout.addWidget(self.auto_color_radio)
        color_layout.addWidget(self.manual_color_radio)
        color_layout.addLayout(color_checkbox_layout)
        color_layout.addWidget(self.preset_color_radio)
        color_layout.addWidget(self.preset_color_combo)

        color_group.setLayout(color_layout)
        layout.addWidget(color_group)

        # Config selection
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

        self.analyze_button.clicked.connect(self.analyze_theme)
        self.generate_button.clicked.connect(self.generate_cards)

        button_layout.addWidget(self.analyze_button)
        button_layout.addWidget(self.generate_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Output area
        layout.addWidget(QLabel("Theme Analysis:"))
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMaximumHeight(200)
        layout.addWidget(self.output_text)

        layout.addStretch()
        self.setLayout(layout)

    def toggle_color_selection(self, checked):
        """Enable/disable manual color checkboxes"""
        for cb in [
            self.color_w,
            self.color_u,
            self.color_b,
            self.color_r,
            self.color_g,
        ]:
            cb.setEnabled(checked)

    def get_theme(self) -> str:
        """Get selected theme"""
        if self.preset_radio.isChecked():
            return self.preset_combo.currentText()
        else:
            return self.custom_input.text()

    def get_colors(self) -> list[str]:
        """Get selected colors"""
        if self.auto_color_radio.isChecked():
            return []  # Will be determined by AI
        elif self.manual_color_radio.isChecked():
            colors = []
            if self.color_w.isChecked():
                colors.append("W")
            if self.color_u.isChecked():
                colors.append("U")
            if self.color_b.isChecked():
                colors.append("B")
            if self.color_r.isChecked():
                colors.append("R")
            if self.color_g.isChecked():
                colors.append("G")
            return colors
        else:
            # Parse preset combination
            combo = self.preset_color_combo.currentText()
            if "WU" in combo:
                return ["W", "U"]
            elif "UB" in combo:
                return ["U", "B"]
            elif "BR" in combo:
                return ["B", "R"]
            elif "RG" in combo:
                return ["R", "G"]
            elif "WG" in combo:
                return ["W", "G"]
            elif "WB" in combo:
                return ["W", "B"]
            elif "UR" in combo:
                return ["U", "R"]
            elif "BG" in combo:
                return ["B", "G"]
            elif "WR" in combo:
                return ["W", "R"]
            elif "UG" in combo:
                return ["U", "G"]
            elif "WUG" in combo:
                return ["W", "U", "G"]
            elif "WUB" in combo:
                return ["W", "U", "B"]
            elif "UBR" in combo:
                return ["U", "B", "R"]
            elif "BRG" in combo:
                return ["B", "R", "G"]
            elif "WRG" in combo:
                return ["W", "R", "G"]
            elif "WUBRG" in combo:
                return ["W", "U", "B", "R", "G"]
        return []

    def analyze_theme(self):
        """Analyze the selected theme"""
        theme = self.get_theme()
        if not theme:
            QMessageBox.warning(self, "Warning", "Please enter a theme!")
            return

        # Get parent for logging
        parent = self.parent().parent() if hasattr(self, "parent") else None
        if parent and hasattr(parent, "log_message"):
            parent.log_message("INFO", f"Starting theme analysis for: {theme}")

        commander = self.commander_input.text()
        colors = self.get_colors()

        if parent and hasattr(parent, "log_message"):
            if commander:
                parent.log_message("DEBUG", f"Commander specified: {commander}")
            if colors:
                parent.log_message("DEBUG", f"Colors: {', '.join(colors)}")
            else:
                parent.log_message("DEBUG", "Colors: Auto (based on theme)")

        prompt = f"Theme: {theme}"
        if commander:
            prompt += f"\nCommander: {commander}"
        if colors:
            prompt += f"\nColors: {', '.join(colors)}"

        self.output_text.append(f"Analyzing theme: {theme}...")
        self.analyze_button.setEnabled(False)

        if parent and hasattr(parent, "log_message"):
            parent.log_message("GENERATING", "Sending theme analysis request to AI...")

        self.ai_worker.set_task("analyze_theme", prompt)
        self.ai_worker.start()

    def generate_cards(self):
        """Delegate to controller"""
        # Note: This method generates deck via AI, not individual card images
        # The actual implementation remains here for now as it's AI-based deck creation
        theme = self.get_theme()
        analysis = self.output_text.toPlainText()
        colors = self.get_colors()
        commander = self.commander_input.text() or f"{theme} Commander"

        # Get parent for logging
        parent = self.parent().parent() if hasattr(self, "parent") else None
        if parent and hasattr(parent, "log_message"):
            parent.log_message("INFO", "Starting full deck generation")
            parent.log_message("INFO", f"Theme: {theme}")
            parent.log_message("INFO", f"Commander: {commander}")
            parent.log_message(
                "INFO", f"Colors: {', '.join(colors) if colors else 'Auto'}"
            )
            parent.log_message("DEBUG", f"Analysis length: {len(analysis)} characters")

        prompt = f"""Theme: {theme}
Commander: {commander}
Colors: {', '.join(colors) if colors else 'Based on theme'}

{analysis}

NOW GENERATE ALL 100 CARDS:
Start with card 1 (the commander) and continue through card 100.
Remember the exact distribution: 1 commander, 37 lands, 30 creatures, 10 instants, 10 sorceries, 7 artifacts, 5 enchantments.
Generate them in order as specified in the system prompt.
DO NOT STOP until you reach card 100."""

        self.output_text.append("\nGenerating 100 cards (this may take a moment)...")
        self.generate_button.setEnabled(False)

        if parent and hasattr(parent, "log_message"):
            parent.log_message("GENERATING", "Requesting 100 cards from AI...")
            parent.log_message(
                "DEBUG",
                "Expected: 1 commander, 37 lands, 30 creatures, 10 instants, 10 sorceries, 7 artifacts, 5 enchantments",
            )

        self.ai_worker.set_task("generate_cards", prompt)
        self.ai_worker.start()

    def on_ai_result(self, result: str):
        """Handle AI response"""
        if self.ai_worker.task == "analyze_theme":
            self.output_text.clear()
            self.output_text.append(result)
            self.analyze_button.setEnabled(True)
            self.generate_button.setEnabled(True)
            self.theme_analyzed.emit(result)
        elif self.ai_worker.task == "generate_cards":
            # Parse the generated cards
            cards = self.parse_cards(result)
            self.output_text.append(f"\n Generated {len(cards)} cards")

            # Emit cards directly without art descriptions (will be generated on demand)
            self.cards_generated.emit(cards)
            self.generate_button.setEnabled(True)

            if len(cards) < 100:
                QMessageBox.warning(
                    self,
                    "Incomplete Generation",
                    f"Only {len(cards)} cards generated. Expected 100.\nTry generating again.",
                )
            else:
                QMessageBox.information(
                    self, "Success", f"Generated {len(cards)} cards!"
                )

    def on_ai_error(self, error: str):
        """Handle AI error"""
        QMessageBox.critical(self, "Error", error)
        self.analyze_button.setEnabled(True)
        self.generate_button.setEnabled(True)

    def parse_cards(self, text: str) -> list[MTGCard]:
        """Parse AI response into card objects"""
        parent = self.parent().parent() if hasattr(self, "parent") else None
        if parent and hasattr(parent, "log_message"):
            parent.log_message("DEBUG", f"Parsing AI response: {len(text)} characters")

        cards = []
        lines = text.split("\n")

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
                    except:
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


class CardManagementTab(QWidget):
    """Tab 2: Card Management Table"""

    cards_updated = pyqtSignal(list)
    card_deleted = pyqtSignal(int)  # Signal when card is deleted
    regenerate_card = pyqtSignal(MTGCard)  # Signal to regenerate a card

    def __init__(self):
        super().__init__()
        # Generation attributes (from merged GenerationTab)
        self.generator_worker = CardGeneratorWorker()
        self.generator_worker.progress.connect(self.on_generation_progress)
        self.generator_worker.completed.connect(self.on_generation_completed)
        self.generation_queue = []  # Track generation queue

        # Initialize cards list
        self.cards = []

        self.init_ui()

        # Initialize table manager after UI is set up
        self._setup_table_manager()

        # Initialize file operations manager
        self.file_operations = CardFileOperations(self, logger=self._create_logger())

        # Initialize validation manager
        self.validation_manager = CardValidationManager(
            self.cards, logger=self._create_logger()
        )

    def _create_logger(self):
        """Create a logger compatible with CardFileOperations."""

        class CardManagementLogger:
            def __init__(self, parent):
                self.parent = parent

            def log_message(self, level: str, message: str) -> None:
                """Log a message using the main window's log system."""
                main_window = get_main_window()
                if main_window and hasattr(main_window, "log_message"):
                    main_window.log_message(level, message)
                else:
                    # Fallback to console if main window not available
                    print(f"[{level}] {message}")

        return CardManagementLogger(self)

    def _sync_file_operations_with_main_window(self):
        """Synchronize file operations manager with main window state."""
        parent = get_main_window()
        if parent:
            # Sync current deck name
            if hasattr(parent, "current_deck_name"):
                self.file_operations.current_deck_name = parent.current_deck_name
            # Sync last loaded deck path
            if hasattr(parent, "last_loaded_deck_path"):
                self.file_operations.last_loaded_deck_path = (
                    parent.last_loaded_deck_path
                )

    def _load_cards_from_file_operations(self, cards, skip_deck_tracking=False):
        """
        Helper method to load cards from CardFileOperations and update UI.

        Args:
            cards: List of MTGCard objects from CardFileOperations
            skip_deck_tracking: If True, skip updating main window deck tracking
        """
        if not skip_deck_tracking:
            # Update main window deck tracking from file operations
            parent = get_main_window()
            if parent:
                parent.current_deck_name = self.file_operations.current_deck_name
                parent.last_loaded_deck_path = (
                    self.file_operations.last_loaded_deck_path
                )

                # Update deck name display
                if hasattr(parent, "update_deck_display"):
                    parent.update_deck_display()

                # Update file watcher to watch this deck file
                if (
                    hasattr(parent, "file_watcher")
                    and self.file_operations.last_loaded_deck_path
                ):
                    # Remove old file from watcher
                    if hasattr(parent, "watching_file") and parent.watching_file:
                        parent.file_watcher.removePath(parent.watching_file)

                    # Add new file to watcher
                    parent.file_watcher.addPath(
                        self.file_operations.last_loaded_deck_path
                    )
                    parent.watching_file = self.file_operations.last_loaded_deck_path
                    parent.log_message(
                        "DEBUG",
                        f"Now watching deck file for changes: {Path(self.file_operations.last_loaded_deck_path).name}",
                    )

        # Load the cards using existing method
        self.load_cards(cards)

        # Select and preview the commander (first card)
        if len(cards) > 0:
            # Select first row in table
            self.table.selectRow(0)
            # Update preview with commander
            parent = get_main_window()
            if parent and hasattr(parent, "update_card_preview"):
                parent.update_card_preview(cards[0])
                if parent and hasattr(parent, "log_message"):
                    parent.log_message(
                        "DEBUG", f"Auto-selected commander: {cards[0].name}"
                    )
        else:
            # Clear the preview if no cards
            parent = get_main_window()
            if parent and hasattr(parent, "clear_card_preview"):
                parent.clear_card_preview()

    def init_ui(self):
        layout = QVBoxLayout()

        # Toolbar
        toolbar = QHBoxLayout()
        self.load_button = QPushButton(" Load Deck")
        self.reload_button = QPushButton("🔄 Reload (F5)")
        self.reload_button.setToolTip("Reload current deck from file (F5)")
        self.reload_button.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; font-weight: bold; padding: 5px; }"
        )

        # CSV Import/Export buttons
        self.csv_import_button = QPushButton("📥 Import CSV")
        self.csv_import_button.setToolTip("Import deck from CSV file")
        self.csv_export_button = QPushButton("📤 Export CSV")
        self.csv_export_button.setToolTip("Export deck to CSV file")

        self.config_button = QPushButton("⚙️ Config")
        self.config_button.clicked.connect(self.toggle_generation_settings)

        # Auto-save indicator
        self.auto_save_label = QLabel(" Auto-Save: Active")
        self.auto_save_label.setStyleSheet(
            "color: #4ec9b0; font-weight: bold; padding: 5px;"
        )

        self.load_button.clicked.connect(self.load_deck)
        self.reload_button.clicked.connect(self.reload_current_deck)
        self.csv_import_button.clicked.connect(self.import_csv)
        self.csv_export_button.clicked.connect(self.export_csv)

        toolbar.addWidget(self.load_button)
        toolbar.addWidget(self.reload_button)
        toolbar.addWidget(self.auto_save_label)
        toolbar.addWidget(self.csv_import_button)
        toolbar.addWidget(self.csv_export_button)
        toolbar.addStretch()

        # Generate All Pending button (moved from generation controls)
        self.generate_all_btn = QPushButton("🚀 Generate All")
        self.generate_all_btn.setStyleSheet(
            "QPushButton { font-weight: bold; padding: 6px; background-color: #4CAF50; }"
        )
        self.generate_all_btn.setToolTip("Generate all pending cards")
        self.generate_all_btn.clicked.connect(self.generate_all_cards)
        toolbar.addWidget(self.generate_all_btn)

        toolbar.addWidget(self.config_button)
        layout.addLayout(toolbar)

        # Filter and search
        filter_layout = QHBoxLayout()
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
        # Filter connections now handled by table manager
        filter_layout.addWidget(self.filter_combo)

        # Add status filter
        filter_layout.addWidget(QLabel("Status:"))
        self.status_filter_combo = QComboBox()
        self.status_filter_combo.addItems(
            ["All", "✅ Completed", "⏸️ Pending", "❌ Failed", "🔄 Generating"]
        )
        # Status filter connections now handled by table manager
        filter_layout.addWidget(self.status_filter_combo)

        filter_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        # Search filter connections now handled by table manager
        filter_layout.addWidget(self.search_input)

        # Add filter result label
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
            }
        """
        )
        self.filter_result_label.setVisible(False)  # Hidden initially
        filter_layout.addWidget(self.filter_result_label)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(10)  # Removed Actions column
        self.table.setHorizontalHeaderLabels(
            [
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
        )

        # Set column widths and make table use full width
        header = self.table.horizontalHeader()
        header.resizeSection(0, 40)  # #
        header.resizeSection(1, 180)  # Name
        header.resizeSection(2, 60)  # Cost
        header.resizeSection(3, 140)  # Type
        header.resizeSection(4, 50)  # P/T
        header.resizeSection(5, 250)  # Text
        header.resizeSection(6, 70)  # Rarity
        header.resizeSection(7, 200)  # Art
        header.resizeSection(8, 100)  # Gen. Status
        header.resizeSection(9, 80)  # Image

        # Make the last section (or text column) stretch to fill available space
        from PyQt6.QtWidgets import QHeaderView

        header.setStretchLastSection(False)  # Don't stretch last column
        header.setSectionResizeMode(
            5, QHeaderView.ResizeMode.Stretch
        )  # Make Text column stretch
        header.setSectionResizeMode(
            7, QHeaderView.ResizeMode.Stretch
        )  # Make Art column stretch

        # Disable sorting - it's broken
        self.table.setSortingEnabled(False)
        # Sorting disabled - it's broken
        # header.sectionClicked.connect(self.sort_by_column)

        # Track sorting state for each column
        # Sorting disabled
        # self.sort_order = {}  # Column index -> Qt.SortOrder

        # Table item connections now handled by table manager

        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        # Add context menu for right-click
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        # Context menu connections now handled by table manager

        # Selection change connections now handled by table manager

        layout.addWidget(self.table)

        # Color Distribution only (stats moved to generation settings)
        self.color_label = QLabel(" Colors: -")
        self.color_label.setWordWrap(True)
        self.color_label.setStyleSheet(
            "font-weight: bold; color: #ce9178; padding: 5px;"
        )
        layout.addWidget(self.color_label)

        # Edit buttons with Add/Delete functionality
        edit_layout = QHBoxLayout()
        self.add_card_button = QPushButton(" Add Card")
        self.delete_card_button = QPushButton(" Delete Card")
        self.edit_button = QPushButton(" Edit Card")
        self.generate_missing_button = QPushButton("Generate Missing Values")
        self.generate_art_button = QPushButton("Generate Art Descriptions")

        self.add_card_button.clicked.connect(self.add_new_card)
        self.delete_card_button.clicked.connect(self.delete_selected_cards)
        self.edit_button.clicked.connect(self.edit_card)
        self.generate_missing_button.clicked.connect(self.generate_missing)
        self.generate_art_button.clicked.connect(self.generate_art_descriptions)

        # Style the delete button with red color
        self.delete_card_button.setStyleSheet(
            """
            QPushButton {
                background-color: #5c2828;
                color: white;
            }
            QPushButton:hover {
                background-color: #7c3838;
            }
        """
        )

        edit_layout.addWidget(self.add_card_button)
        edit_layout.addWidget(self.delete_card_button)
        edit_layout.addWidget(self.edit_button)
        edit_layout.addWidget(self.generate_missing_button)
        edit_layout.addWidget(self.generate_art_button)
        edit_layout.addStretch()
        layout.addLayout(edit_layout)

        # === GENERATION SECTION ===
        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        # Stats and Progress (always visible)
        stats_layout = QHBoxLayout()

        # Generation progress indicator
        self.generation_stats_label = QLabel("🎨 Generated: 0/0 Cards (0%)")
        self.generation_stats_label.setStyleSheet(
            """
            QLabel {
                font-weight: bold;
                font-size: 14px;
                padding: 8px;
                background-color: #3a3a3a;
                border: 1px solid #555;
                border-radius: 4px;
                color: #4ec9b0;
            }
        """
        )
        stats_layout.addWidget(self.generation_stats_label)

        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        # Card type statistics (separate line)
        type_stats_layout = QHBoxLayout()

        # Card type stats label
        self.type_stats_label = QLabel(
            "📊 Total: 0 | Lands: 0 | Creatures: 0 | Instants: 0 | Sorceries: 0"
        )
        self.type_stats_label.setStyleSheet("padding: 5px; color: #888;")
        type_stats_layout.addWidget(self.type_stats_label)

        type_stats_layout.addStretch()
        layout.addLayout(type_stats_layout)

        # Model/Style Settings Group (toggleable via Config button)
        self.gen_settings_group = QGroupBox("⚙️ Model & Style Settings")
        self.gen_settings_group.setVisible(False)  # Initially hidden
        gen_settings_layout = QGridLayout()

        # Model selection
        gen_settings_layout.addWidget(QLabel("Model:"), 0, 0)
        self.model_combo = QComboBox()
        self.model_combo.addItems(
            ["sdxl", "sdxl-lightning", "flux-schnell", "flux-dev", "playground"]
        )
        self.model_combo.setToolTip("Select the AI model for image generation")
        gen_settings_layout.addWidget(self.model_combo, 0, 1)

        # Style selection
        gen_settings_layout.addWidget(QLabel("Style:"), 0, 2)
        self.style_combo = QComboBox()
        self.style_combo.addItems(
            ["mtg_modern", "mtg_classic", "realistic", "anime", "oil_painting"]
        )
        self.style_combo.setToolTip("Select the art style for cards")
        gen_settings_layout.addWidget(self.style_combo, 0, 3)

        self.gen_settings_group.setLayout(gen_settings_layout)
        layout.addWidget(self.gen_settings_group)

        # Generation control buttons (conditionally visible)
        gen_controls_widget = QWidget()
        gen_controls = QHBoxLayout(gen_controls_widget)
        gen_controls.setContentsMargins(0, 5, 0, 5)

        # Custom image button (always visible, leftmost position)
        self.use_custom_image_btn = QPushButton("📷 Use Custom Image")
        self.use_custom_image_btn.setToolTip("Select your own image as artwork")
        self.use_custom_image_btn.clicked.connect(self.use_custom_image_for_selected)
        gen_controls.addWidget(self.use_custom_image_btn)

        # Generate Selected button (initially hidden - shown only for non-generated cards)
        self.generate_selected_btn = QPushButton("🎯 Generate Selected")
        self.generate_selected_btn.clicked.connect(self.generate_selected_cards)
        self.generate_selected_btn.setVisible(False)  # Initially hidden
        gen_controls.addWidget(self.generate_selected_btn)

        # Regeneration buttons (initially hidden)
        self.regen_with_image_btn = QPushButton("🖼️ Regenerate with New Image")
        self.regen_with_image_btn.setToolTip(
            "Regenerate selected card with new artwork"
        )
        self.regen_with_image_btn.clicked.connect(self.regenerate_selected_with_image)
        self.regen_with_image_btn.setVisible(False)  # Initially hidden
        gen_controls.addWidget(self.regen_with_image_btn)

        self.regen_card_only_btn = QPushButton("🃏 Regenerate Card Only")
        self.regen_card_only_btn.setToolTip("Regenerate card using existing artwork")
        self.regen_card_only_btn.clicked.connect(self.regenerate_selected_card_only)
        self.regen_card_only_btn.setVisible(False)  # Initially hidden
        gen_controls.addWidget(self.regen_card_only_btn)

        # Delete files button (initially hidden)
        self.delete_files_btn = QPushButton("🗑️ Delete Files")
        self.delete_files_btn.setToolTip("Delete generated files for selected cards")
        self.delete_files_btn.clicked.connect(self.delete_selected_files)
        self.delete_files_btn.setVisible(False)  # Initially hidden
        gen_controls.addWidget(self.delete_files_btn)

        gen_controls.addStretch()

        # Sync Status button
        self.sync_status_btn = QPushButton("🔄 Sync Status")
        self.sync_status_btn.setToolTip(
            "Reset and synchronize card status with actual rendered files"
        )
        self.sync_status_btn.clicked.connect(self.manual_sync_status)
        self.sync_status_btn.setStyleSheet("QPushButton { background-color: #4a5568; }")
        gen_controls.addWidget(self.sync_status_btn)

        # Regenerate All Cards Only button (always visible on the right)
        self.regen_all_cards_only_btn = QPushButton("♻️ Regenerate All Cards Only")
        self.regen_all_cards_only_btn.setToolTip(
            "Regenerate all cards keeping existing images where available"
        )
        self.regen_all_cards_only_btn.clicked.connect(self.regenerate_all_cards_only)
        self.regen_all_cards_only_btn.setStyleSheet(
            "QPushButton { background-color: #5c4528; }"
        )
        gen_controls.addWidget(self.regen_all_cards_only_btn)

        # Add control buttons to main layout (always visible)
        layout.addWidget(gen_controls_widget)

        # Create a scroll area for the entire content
        from PyQt6.QtGui import QKeySequence, QShortcut
        from PyQt6.QtWidgets import QScrollArea

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Create container widget for the scroll area
        container = QWidget()
        container.setLayout(layout)

        # Set the container as the scroll area's widget
        scroll.setWidget(container)

        # Add keyboard shortcut for reload (F5)
        self.reload_shortcut = QShortcut(QKeySequence("F5"), self)
        self.reload_shortcut.activated.connect(self.reload_current_deck)

        # Set the scroll area as this tab's main layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll)
        main_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        self.setLayout(main_layout)

    def _setup_table_manager(self):
        """Initialize and configure the table manager."""
        # Create the table manager
        self.table_manager = CardTableManager(self.table, self.cards)

        # Connect filter components to the manager
        self.table_manager.set_filter_components(
            self.filter_combo,
            self.status_filter_combo,
            self.search_input,
            self.filter_result_label,
        )

        # Connect table manager signals
        self.table_manager.item_changed.connect(self._on_table_manager_item_changed)
        self.table_manager.selection_changed.connect(self.update_button_visibility)
        self.table_manager.card_action_requested.connect(self._handle_card_action)

        # Remove original table signal connections since they're now handled by the manager
        # Use contextlib.suppress to avoid errors if connections don't exist
        with contextlib.suppress(Exception):
            self.table.itemChanged.disconnect()
        with contextlib.suppress(Exception):
            self.table.customContextMenuRequested.disconnect()
        with contextlib.suppress(Exception):
            self.table.itemSelectionChanged.disconnect()

    def _on_table_manager_item_changed(self, card):
        """Handle table item changes from the table manager."""
        # Auto-save the deck
        main_window = self.parent().parent() if hasattr(self, "parent") else None
        if main_window and hasattr(main_window, "auto_save_deck"):
            main_window.auto_save_deck(self.cards)
            if main_window and hasattr(main_window, "log_message"):
                main_window.log_message(
                    "DEBUG", f"Auto-saved deck after editing {card.name}"
                )

    def _handle_card_action(self, action: str, data):
        """Handle card action requests from the table manager."""
        if action == "add":
            self.add_new_card()
        elif action == "edit" and data:
            self.edit_card()
        elif action == "duplicate" and data:
            self.duplicate_selected_card()
        elif action == "delete" and data:
            self.delete_selected_cards()
        elif action == "regenerate" and data:
            self.regenerate_selected_card()

    # Sorting method removed - was broken
    # def sort_by_column(self, column: int):
    #     pass

    def load_deck(self):
        """Open file dialog to load a deck"""
        cards = self.file_operations.load_deck_with_dialog()
        if cards:
            self._load_cards_from_file_operations(cards)

    def reload_current_deck(self):
        """Reload the currently loaded deck from file without dialog"""
        # Check if we have a current deck to reload
        if not self.file_operations.last_loaded_deck_path:
            QMessageBox.information(
                self, "No Deck Loaded", "Please load a deck first before reloading."
            )
            return

        deck_path = self.file_operations.last_loaded_deck_path
        if not Path(deck_path).exists():
            QMessageBox.warning(
                self, "File Not Found", f"Deck file not found: {deck_path}"
            )
            return

        # Log the reload action
        parent = get_main_window()
        if parent and hasattr(parent, "log_message"):
            parent.log_message("INFO", f"🔄 Reloading deck: {Path(deck_path).name}")

        # Remember selected row
        selected_row = -1
        selected_items = self.table.selectedItems()
        if selected_items:
            selected_row = selected_items[0].row()

        # Disable auto-save temporarily to prevent overwriting
        old_auto_save = self.auto_save_label.text()
        self.auto_save_label.setText(" Auto-Save: Paused")
        self.auto_save_label.setStyleSheet(
            "color: #ff9800; font-weight: bold; padding: 5px;"
        )

        # Load the deck file using file operations
        cards = self.file_operations.reload_current_deck()
        if cards:
            self._load_cards_from_file_operations(cards, skip_deck_tracking=True)

            # Restore selection if we had one, otherwise select commander
            if selected_row >= 0 and selected_row < self.table.rowCount():
                self.table.selectRow(selected_row)
            elif self.table.rowCount() > 0:
                # Select commander if no previous selection
                self.table.selectRow(0)
                selected_row = 0

            # Update preview with the selected card (or commander)
            if 0 <= selected_row < len(self.cards):
                # Force preview update
                if parent and hasattr(parent, "update_card_preview"):
                    parent.update_card_preview(self.cards[selected_row])
                    parent.log_message(
                        "DEBUG",
                        f"Updated preview for card: {self.cards[selected_row].name}",
                    )

            # Show success message
            if parent and hasattr(parent, "log_message"):
                parent.log_message("SUCCESS", "✅ Deck reloaded successfully!")

        # Re-enable auto-save after a short delay
        from PyQt6.QtCore import QTimer

        QTimer.singleShot(1000, lambda: self._restore_auto_save(old_auto_save))

    def _restore_auto_save(self, old_text):
        """Restore auto-save indicator after reload"""
        self.auto_save_label.setText(old_text)
        self.auto_save_label.setStyleSheet(
            "color: #4ec9b0; font-weight: bold; padding: 5px;"
        )

    def load_deck_file(self, filename=None):
        """Load a deck from a YAML file"""
        if filename is None:
            # Use file operations for dialog
            cards = self.file_operations.load_deck_with_dialog()
            if cards:
                self._load_cards_from_file_operations(cards)
        else:
            # Load specific file using file operations
            cards = self.file_operations.load_deck_from_file(filename)
            if cards:
                self._load_cards_from_file_operations(cards)

    def manual_sync_status(self):
        """Manually sync card status based on whether cards have been generated"""
        parent = get_main_window()

        # Sync status based on whether cards have generated images
        updated_count = 0
        for card in self.cards:
            old_status = getattr(card, "status", "pending")

            if hasattr(card, "card_path") and card.card_path:
                # Card has been generated (has a card image)
                if old_status != "completed":
                    card.status = "completed"
                    updated_count += 1
            else:
                # No card image, should be pending
                if old_status == "completed":
                    card.status = "pending"
                    updated_count += 1

        # Log the sync
        if parent and hasattr(parent, "log_message"):
            parent.log_message(
                "INFO",
                f"🔄 Synchronized {updated_count} card statuses based on generated images",
            )

        # Refresh the display
        self.table_manager.refresh_table()
        self.update_stats()
        self.update_generation_stats()

        # Log completion
        if parent and hasattr(parent, "log_message"):
            completed_count = sum(1 for c in self.cards if c.status == "completed")
            pending_count = sum(1 for c in self.cards if c.status == "pending")
            parent.log_message(
                "SUCCESS",
                f"✅ Status synchronized: {completed_count} completed, {pending_count} pending",
            )

    def regenerate_all_cards_only(self):
        """Regenerate all cards while keeping existing images"""
        if not self.cards:
            QMessageBox.warning(self, "No Cards", "No cards to regenerate!")
            return

        # Confirm action
        reply = QMessageBox.question(
            self,
            "Regenerate All Cards",
            "This will regenerate ALL cards but keep existing images.\n\n"
            "Cards will be skipped if:\n"
            "• They are still pending (not generated yet)\n"
            "• Their image file is missing\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        parent = get_main_window()
        deck_name = None
        if parent and hasattr(parent, "current_deck_name"):
            deck_name = parent.current_deck_name

        if not deck_name:
            QMessageBox.warning(self, "No Deck", "Please load a deck first!")
            return

        # Check each card and prepare regeneration list
        cards_to_regenerate = []
        skipped_pending = []
        skipped_no_image = []

        from pathlib import Path

        artwork_dir = Path("saved_decks") / deck_name / "artwork"

        for card in self.cards:
            # Skip pending cards
            if not hasattr(card, "status") or card.status == "pending":
                skipped_pending.append(card.name)
                if parent and hasattr(parent, "log_message"):
                    parent.log_message(
                        "WARNING", f"⏭️ Skipping '{card.name}' - still pending"
                    )
                continue

            # Check if artwork exists
            safe_name = make_safe_filename(card.name)
            artwork_found = False
            artwork_path = None

            # Check for artwork with various extensions
            for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
                possible_path = artwork_dir / f"{safe_name}{ext}"
                if possible_path.exists():
                    artwork_found = True
                    artwork_path = str(possible_path)
                    break

            # Also check if card has image_path set
            if not artwork_found and hasattr(card, "image_path") and card.image_path:
                if Path(card.image_path).exists():
                    artwork_found = True
                    artwork_path = card.image_path

            if not artwork_found:
                skipped_no_image.append(card.name)
                if parent and hasattr(parent, "log_message"):
                    parent.log_message(
                        "WARNING", f"⚠️ Skipping '{card.name}' - no image found"
                    )
                continue

            # Set the image path and mark for regeneration
            card.image_path = artwork_path
            card.status = "pending"  # Mark as pending for regeneration
            cards_to_regenerate.append(card)
            if parent and hasattr(parent, "log_message"):
                parent.log_message(
                    "INFO", f"✅ Will regenerate '{card.name}' with existing image"
                )

        # Show summary
        summary_msg = "Regeneration Summary:\n\n"
        summary_msg += f"• Cards to regenerate: {len(cards_to_regenerate)}\n"
        summary_msg += f"• Skipped (pending): {len(skipped_pending)}\n"
        summary_msg += f"• Skipped (no image): {len(skipped_no_image)}\n"

        if skipped_pending:
            summary_msg += f"\nPending cards skipped:\n{', '.join(skipped_pending[:5])}"
            if len(skipped_pending) > 5:
                summary_msg += f" and {len(skipped_pending)-5} more..."

        if skipped_no_image:
            summary_msg += (
                f"\n\nCards without images skipped:\n{', '.join(skipped_no_image[:5])}"
            )
            if len(skipped_no_image) > 5:
                summary_msg += f" and {len(skipped_no_image)-5} more..."

        QMessageBox.information(self, "Regeneration Summary", summary_msg)

        if cards_to_regenerate:
            # Start regeneration with existing images
            self.refresh_generation_queue()
            self.generator_worker.set_cards(
                cards_to_regenerate,
                self.model_combo.currentText(),
                self.style_combo.currentText(),
                "card_only_regeneration",
                deck_name,
            )
            self.generator_worker.start()

            if parent and hasattr(parent, "log_message"):
                parent.log_message(
                    "SUCCESS",
                    f"🔄 Starting regeneration of {len(cards_to_regenerate)} cards",
                )

    def update_button_visibility(self):
        """Update visibility of buttons based on selection"""
        selected_rows = self.table_manager.get_selected_rows()

        # Check status of selected cards
        has_generated = False
        has_pending = False

        if selected_rows:
            for row in selected_rows:
                if 0 <= row < len(self.cards):
                    card = self.cards[row]
                    # Check if card has been generated (has card_path or status is completed)
                    if (hasattr(card, "card_path") and card.card_path) or (
                        hasattr(card, "status") and card.status == "completed"
                    ):
                        has_generated = True
                    else:
                        has_pending = True

        # Update button visibility
        # Show Generate Selected only if there are pending cards selected
        self.generate_selected_btn.setVisible(has_pending and len(selected_rows) > 0)

        # Show regeneration and delete buttons only for generated cards
        self.regen_with_image_btn.setVisible(has_generated)
        self.regen_card_only_btn.setVisible(has_generated)
        self.delete_files_btn.setVisible(has_generated)

    def toggle_generation_settings(self):
        """Toggle visibility of model/style settings only"""
        is_visible = self.gen_settings_group.isVisible()
        self.gen_settings_group.setVisible(not is_visible)

        # Update button text to show state
        if not is_visible:
            self.config_button.setText("⚙️ Config ▼")
        else:
            self.config_button.setText("⚙️ Config ▲")

    def import_csv(self):
        """Import deck from CSV file"""
        cards = self.file_operations.import_csv_with_dialog()
        if cards:
            self.load_cards(cards)

    def export_csv(self):
        """Export current deck to CSV file"""
        self.file_operations.export_csv_with_dialog(self.cards)

    # Removed old export_deck method - now using XML export only

    def clear_deck(self):
        """Clear all cards from the deck"""
        if not self.cards:
            return

        reply = QMessageBox.question(
            self,
            "Clear Deck",
            "Clear all cards from the current deck?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.cards = []
            self.table_manager.refresh_table()
            self.update_stats()
            self.update_generation_stats()

            parent = get_main_window()
            if parent and hasattr(parent, "log_message"):
                parent.log_message("INFO", "Deck cleared")

    def generate_deck_with_ai(self):
        """Generate a new deck using AI"""
        parent = get_main_window()
        if parent and hasattr(parent, "deck_builder_tab"):
            # Switch to deck builder tab
            parent.tabs.setCurrentWidget(parent.deck_builder_tab)

    def add_new_card(self):
        """Add a new card to the deck"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New Card")
        dialog.setModal(True)

        layout = QFormLayout()

        name_input = QLineEdit()
        type_input = QLineEdit()
        mana_input = QLineEdit()
        text_input = QTextEdit()
        text_input.setMaximumHeight(100)

        layout.addRow("Name:", name_input)
        layout.addRow("Type:", type_input)
        layout.addRow("Mana Cost:", mana_input)
        layout.addRow("Text:", text_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        dialog.setLayout(layout)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_card = MTGCard()
            new_card.id = len(self.cards) + 1
            new_card.name = name_input.text()
            new_card.type = type_input.text()
            new_card.mana_cost = mana_input.text()
            new_card.text = text_input.toPlainText()
            new_card.status = "pending"

            self.cards.append(new_card)
            self.table_manager.refresh_table()

    def delete_selected_cards(self):
        """Delete selected cards from the deck"""
        selected_rows = self.table_manager.get_selected_rows()

        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select cards to delete!")
            return

        reply = QMessageBox.question(
            self,
            "Delete Cards",
            f"Delete {len(selected_rows)} selected cards?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            for row in sorted(selected_rows, reverse=True):
                if 0 <= row < len(self.cards):
                    del self.cards[row]

            self.table_manager.refresh_table()
            self.update_stats()
            self.update_generation_stats()

    def edit_card(self):
        """Edit selected card details including art description"""
        selected_rows = self.table_manager.get_selected_rows()

        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a card to edit!")
            return

        row = min(selected_rows)
        if 0 <= row < len(self.cards):
            card = self.cards[row]

            dialog = QDialog(self)
            dialog.setWindowTitle(f"Edit Card: {card.name}")
            dialog.setModal(True)
            dialog.resize(600, 500)

            layout = QFormLayout()

            name_input = QLineEdit(card.name)
            type_input = QLineEdit(card.type)
            mana_input = QLineEdit(card.mana_cost if card.mana_cost else "")
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

            # Debug logging
            parent = get_main_window()
            if parent and hasattr(parent, "log_message"):
                parent.log_message("DEBUG", f"Checking art for card: {card.name}")
                parent.log_message(
                    "DEBUG", f"Has 'art' attribute: {hasattr(card, 'art')}"
                )
                parent.log_message(
                    "DEBUG", f"Art value: {getattr(card, 'art', 'None')}"
                )
                parent.log_message(
                    "DEBUG",
                    f"Has 'art_prompt' attribute: {hasattr(card, 'art_prompt')}",
                )
                parent.log_message(
                    "DEBUG", f"Art_prompt value: {getattr(card, 'art_prompt', 'None')}"
                )

            if hasattr(card, "art") and card.art:
                art_text = card.art
            elif hasattr(card, "art_prompt") and card.art_prompt:
                art_text = card.art_prompt

            art_input = QTextEdit(art_text)
            art_input.setMaximumHeight(100)
            art_input.setPlaceholderText(
                "Enter art description for AI image generation..."
            )

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

            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok
                | QDialogButtonBox.StandardButton.Cancel
            )
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addRow(buttons)

            dialog.setLayout(layout)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                card.name = name_input.text()
                card.type = type_input.text()
                card.mana_cost = mana_input.text()
                card.text = text_input.toPlainText()
                card.power = power_input.text() if power_input.text() else None
                card.toughness = (
                    toughness_input.text() if toughness_input.text() else None
                )
                card.flavor = flavor_input.toPlainText()
                # Save art description to both attributes for compatibility
                card.art = art_input.toPlainText()
                card.art_prompt = art_input.toPlainText()

                self.table_manager.refresh_table()

    def edit_selected_art_prompt(self):
        """Edit art prompt for selected card"""
        selected_rows = self.table_manager.get_selected_rows()

        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a card!")
            return

        row = min(selected_rows)
        if 0 <= row < len(self.cards):
            card = self.cards[row]

            current_prompt = getattr(
                card, "art_prompt", f"Fantasy artwork for {card.name}"
            )

            text, ok = QInputDialog.getMultiLineText(
                self,
                f"Edit Art Prompt: {card.name}",
                "Art Description:",
                current_prompt,
            )

            if ok:
                card.art_prompt = text
                parent = get_main_window()
                if parent and hasattr(parent, "log_message"):
                    parent.log_message("INFO", f"Updated art prompt for {card.name}")

    def generate_missing(self):
        """Delegate to controller"""
        parent = get_main_window()
        if parent and hasattr(parent, "generation_controller"):
            result = parent.generation_controller.generate_missing(
                self.cards,
                self.model_combo.currentText()
                if hasattr(self, "model_combo")
                else "sdxl",
                self.style_combo.currentText()
                if hasattr(self, "style_combo")
                else "mtg_modern",
                parent.current_deck_name
                if hasattr(parent, "current_deck_name")
                else None,
            )
            if "All cards have been generated" in result:
                QMessageBox.information(self, "All Complete", result)

    def generate_art_descriptions(self):
        """Delegate to controller"""
        parent = get_main_window()
        if parent and hasattr(parent, "generation_controller"):
            result = parent.generation_controller.generate_art_descriptions(self.cards)
            if "No cards to generate art for" in result:
                QMessageBox.warning(self, "No Cards", result)
            elif "All cards have art descriptions" in result:
                QMessageBox.information(self, "Complete", result)

    def apply_queue_filter(self):
        """Deprecated - using single table now"""
        pass

    def on_queue_selection_changed(self):
        """Deprecated - using main table selection"""
        pass

    def edit_art_prompt_for_card(self, row):
        """Edit art prompt for a specific card"""
        if 0 <= row < len(self.cards):
            card = self.cards[row]
            current_prompt = getattr(
                card, "art_prompt", f"Fantasy artwork for {card.name}"
            )

            text, ok = QInputDialog.getMultiLineText(
                self,
                f"Edit Art Prompt: {card.name}",
                "Art Description:",
                current_prompt,
            )

            if ok:
                card.art_prompt = text
                parent = get_main_window()
                if parent and hasattr(parent, "log_message"):
                    parent.log_message("INFO", f"Updated art prompt for {card.name}")

    def regenerate_selected_with_image(self):
        """Delegate to controller"""
        selected_rows = self.table_manager.get_selected_rows()
        if not selected_rows:
            QMessageBox.warning(
                self, "No Selection", "Please select cards to regenerate!"
            )
            return

        selected_cards = [
            self.cards[row] for row in selected_rows if 0 <= row < len(self.cards)
        ]
        parent = get_main_window()
        if parent and hasattr(parent, "generation_controller"):
            parent.generation_controller.regenerate_selected_with_image(
                selected_cards,
                self.model_combo.currentText(),
                self.style_combo.currentText(),
                parent.current_deck_name
                if hasattr(parent, "current_deck_name")
                else None,
            )

    def regenerate_selected_card_only(self):
        """Delegate to controller"""
        selected_rows = self.table_manager.get_selected_rows()
        if not selected_rows:
            QMessageBox.warning(
                self, "No Selection", "Please select cards to regenerate!"
            )
            return

        selected_cards = [
            self.cards[row] for row in selected_rows if 0 <= row < len(self.cards)
        ]
        parent = get_main_window()
        if parent and hasattr(parent, "generation_controller"):
            parent.generation_controller.regenerate_selected_card_only(
                selected_cards,
                self.model_combo.currentText(),
                self.style_combo.currentText(),
                parent.current_deck_name
                if hasattr(parent, "current_deck_name")
                else None,
            )

    def use_custom_image_for_selected(self):
        """Use custom image for selected cards"""
        selected_rows = self.table_manager.get_selected_rows()

        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select cards!")
            return

        # Open file dialog
        parent = get_main_window()
        default_dir = ""

        if parent and hasattr(parent, "current_deck_name") and parent.current_deck_name:
            artwork_dir = Path("saved_decks") / parent.current_deck_name / "artwork"
            artwork_dir.mkdir(parents=True, exist_ok=True)
            default_dir = str(artwork_dir)

        image_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Custom Artwork",
            default_dir,
            "Image Files (*.png *.jpg *.jpeg *.gif *.bmp);;All Files (*.*)",
        )

        if image_path:
            for row in selected_rows:
                if 0 <= row < len(self.cards):
                    card = self.cards[row]
                    card.custom_image_path = image_path
                    card.status = "pending"

                    if parent and hasattr(parent, "log_message"):
                        parent.log_message("INFO", f"Set custom image for {card.name}")

            self.refresh_generation_queue()

            # Generate cards with custom image
            cards_with_custom = [
                self.cards[row] for row in selected_rows if 0 <= row < len(self.cards)
            ]

            # Get deck name from parent
            deck_name = None
            parent = get_main_window()
            if parent and hasattr(parent, "current_deck_name"):
                deck_name = parent.current_deck_name

            self.generator_worker.set_cards(
                cards_with_custom,
                self.model_combo.currentText(),
                self.style_combo.currentText(),
                "custom_image",
                deck_name,
            )
            self.generator_worker.start()

    def delete_selected_files(self):
        """Delete generated files for selected cards"""
        selected_rows = self.table_manager.get_selected_rows()

        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select cards!")
            return

        reply = QMessageBox.question(
            self,
            "Delete Files",
            f"Delete generated files for {len(selected_rows)} selected cards?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            deleted_count = 0
            for row in selected_rows:
                if 0 <= row < len(self.cards):
                    card = self.cards[row]

                    # Delete files
                    if (
                        hasattr(card, "card_path")
                        and card.card_path
                        and Path(card.card_path).exists()
                    ):
                        try:
                            Path(card.card_path).unlink()
                            card.card_path = None
                            deleted_count += 1
                        except:
                            pass

                    if (
                        hasattr(card, "image_path")
                        and card.image_path
                        and Path(card.image_path).exists()
                    ):
                        try:
                            Path(card.image_path).unlink()
                            card.image_path = None
                            deleted_count += 1
                        except:
                            pass

                    # Reset status
                    card.status = "pending"
                    card.generated_at = None

            self.refresh_generation_queue()
            self.table_manager.refresh_table()  # Also refresh the main table

            # Update preview if current card was affected
            current_row = self.table.currentRow()
            if current_row in selected_rows and 0 <= current_row < len(self.cards):
                parent = get_main_window()
                if parent and hasattr(parent, "update_card_preview"):
                    parent.update_card_preview(self.cards[current_row])

            parent = get_main_window()
            if parent and hasattr(parent, "log_message"):
                parent.log_message("INFO", f"Deleted {deleted_count} files")

    def load_cards(self, cards: list[MTGCard]):
        """Load cards into table"""
        self.cards = cards

        # Update validation manager with new cards
        self.validation_manager.update_cards(self.cards)
        commander_colors = self.validation_manager.commander_colors

        # Synchronize card status based on whether they have generated images
        # Status should match whether the card has been generated
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

        # Log all cards with color violations
        self.validation_manager.log_color_violations()

        # Update the table manager with new cards and commander colors
        self.table_manager.set_cards(self.cards)
        self.table_manager.set_commander_colors(commander_colors)
        self.update_stats()
        self.update_generation_stats()

    def sync_card_status_with_rendered_files(self):
        """Synchronize card status based on existing rendered files"""
        # Sync file operations with main window first
        self._sync_file_operations_with_main_window()
        # Use the file operations manager to sync card status
        self.file_operations.sync_card_status_with_files(self.cards)

    def update_generation_stats(self):
        """Update the generation progress indicator"""
        # Check if UI is initialized
        if not hasattr(self, "generation_stats_label"):
            return

        total = len(self.cards)
        completed = sum(
            1 for c in self.cards if hasattr(c, "status") and c.status == "completed"
        )
        pending = sum(
            1 for c in self.cards if not hasattr(c, "status") or c.status == "pending"
        )
        failed = sum(
            1 for c in self.cards if hasattr(c, "status") and c.status == "failed"
        )
        generating = sum(
            1 for c in self.cards if hasattr(c, "status") and c.status == "generating"
        )

        # Calculate percentage
        percentage = int(completed / total * 100) if total > 0 else 0

        # Update main generation stats
        if percentage == 100:
            self.generation_stats_label.setText(f"✅ All {total} Cards Generated!")
            self.generation_stats_label.setStyleSheet(
                """
                QLabel {
                    font-weight: bold;
                    font-size: 14px;
                    padding: 8px;
                    background-color: #2d5a2d;
                    border: 1px solid #4CAF50;
                    border-radius: 4px;
                    color: #4CAF50;
                }
            """
            )
        elif generating > 0:
            self.generation_stats_label.setText(
                f"🎨 Generating... {completed}/{total} Cards ({percentage}%)"
            )
            self.generation_stats_label.setStyleSheet(
                """
                QLabel {
                    font-weight: bold;
                    font-size: 14px;
                    padding: 8px;
                    background-color: #3a4a3a;
                    border: 1px solid #ff9800;
                    border-radius: 4px;
                    color: #ff9800;
                }
            """
            )
        else:
            self.generation_stats_label.setText(
                f"🎨 Generated: {completed}/{total} Cards ({percentage}%)"
            )
            if percentage < 100:
                self.generation_stats_label.setStyleSheet(
                    """
                    QLabel {
                        font-weight: bold;
                        font-size: 14px;
                        padding: 8px;
                        background-color: #3a3a3a;
                        border: 1px solid #555;
                        border-radius: 4px;
                        color: #4ec9b0;
                    }
                """
                )

    def update_stats(self):
        """Update statistics label with detailed card type breakdown and color distribution"""
        total = len(self.cards)
        lands = sum(1 for c in self.cards if c.is_land())
        creatures = sum(1 for c in self.cards if c.is_creature())
        instants = sum(
            1 for c in self.cards if "Instant" in c.type and "Creature" not in c.type
        )
        sorceries = sum(1 for c in self.cards if "Sorcery" in c.type)
        artifacts = sum(
            1 for c in self.cards if "Artifact" in c.type and "Creature" not in c.type
        )
        enchantments = sum(
            1
            for c in self.cards
            if "Enchantment" in c.type and "Creature" not in c.type
        )

        # Calculate color distribution for all cards
        color_counts = {"W": 0, "U": 0, "B": 0, "R": 0, "G": 0, "C": 0}
        deck_colors = set()  # Track which colors appear in the deck
        commander_colors = set()  # Track commander's color identity
        commander_name = "No Commander"

        for card in self.cards:
            if card.cost and card.cost != "-":
                # Convert to string first to handle integer costs
                cost = str(card.cost).upper()
                for color in ["W", "U", "B", "R", "G"]:
                    count = cost.count(color)
                    if count > 0:
                        color_counts[color] += count
                        deck_colors.add(color)

            # Check if this is the commander (first card or legendary creature)
            if card.id == 1 or "Legendary" in card.type:
                if card.id == 1:  # This is definitely the commander
                    commander_name = card.name
                    if card.cost and card.cost != "-":
                        # Convert to string first to handle integer costs
                        cost = str(card.cost).upper()
                        for color in ["W", "U", "B", "R", "G"]:
                            if color in cost:
                                commander_colors.add(color)

        # Build color string with symbols
        color_symbols = {"W": "", "U": "", "B": "", "R": "", "G": "", "C": ""}
        colors_with_count = []
        for color, count in color_counts.items():
            if count > 0:
                colors_with_count.append(f"{color_symbols[color]}{color}:{count}")

        deck_color_text = (
            " | ".join(colors_with_count) if colors_with_count else "Colorless"
        )

        # Build commander color identity string
        commander_color_text = ""
        if commander_colors:
            commander_color_symbols = [
                color_symbols[c] + c for c in sorted(commander_colors)
            ]
            commander_color_text = "".join(commander_color_symbols)
        else:
            commander_color_text = "Colorless"

        # Check for color identity violations
        violation_colors = deck_colors - commander_colors
        warning_text = ""
        if violation_colors and commander_colors:  # Only warn if commander has colors
            violation_symbols = [color_symbols[c] + c for c in sorted(violation_colors)]
            warning_text = (
                f"  VIOLATION: {' '.join(violation_symbols)} not in commander identity!"
            )

        # Format stats text - now on single line for type_stats_label
        stats_text = (
            f"📊 Total: {total} | Lands: {lands} | Creatures: {creatures} | "
            f"Instants: {instants} | Sorceries: {sorceries} | "
            f"Artifacts: {artifacts} | Enchantments: {enchantments}"
        )

        # Update the type stats label if it exists
        if hasattr(self, "type_stats_label"):
            self.type_stats_label.setText(stats_text)

        # Update color label with commander info and warnings - split for readability
        color_label_text = f" Deck Colors: {deck_color_text}\n"
        color_label_text += (
            f" Commander ({commander_name[:30]}): {commander_color_text}"
        )
        if warning_text:
            color_label_text += f"\n{warning_text}"
            self.color_label.setStyleSheet(
                "font-weight: bold; color: #f48771; padding: 3px;"
            )  # Red for warning
        else:
            self.color_label.setStyleSheet(
                "font-weight: bold; color: #4ec9b0; padding: 3px;"
            )  # Green for valid

        self.color_label.setText(color_label_text)

    def add_new_card(self):
        """Add a new blank card to the deck"""
        # Find the next available ID (highest existing ID + 1)
        max_id = 0
        for card in self.cards:
            try:
                card_id = int(card.id) if isinstance(card.id, str | int) else 0
                max_id = max(max_id, card_id)
            except (ValueError, TypeError):
                continue

        next_id = max_id + 1

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

        # Refresh table
        self.table_manager.refresh_table()

        # Select the new card (last row)
        last_row = self.table.rowCount() - 1
        self.table.selectRow(last_row)

        # Open edit dialog for the new card
        self.edit_card_at_row(last_row)

        # Auto-save
        main_window_save = self.parent().parent() if hasattr(self, "parent") else None
        if main_window_save and hasattr(main_window_save, "auto_save_deck"):
            main_window_save.auto_save_deck(self.cards)

        # Log the action
        main_window = self.parent().parent() if hasattr(self, "parent") else None
        if main_window and hasattr(main_window, "log_message"):
            main_window.log_message("INFO", f"Added new card: {new_card.name}")

    def duplicate_selected_card(self):
        """Duplicate the selected card"""

        current_row = self.table.currentRow()
        if current_row < 0:
            return

        # Find the next available ID
        max_id = 0
        for card in self.cards:
            try:
                card_id = int(card.id) if isinstance(card.id, str | int) else 0
                max_id = max(max_id, card_id)
            except (ValueError, TypeError):
                continue

        next_id = max_id + 1

        # Create a copy of the selected card
        original_card = self.cards[current_row]
        new_card = MTGCard(
            id=next_id,
            name=f"{original_card.name} (Copy)",
            cost=original_card.cost,
            type=original_card.type,
            text=original_card.text,
            power=original_card.power,
            toughness=original_card.toughness,
            rarity=original_card.rarity,
            art=original_card.art,
            flavor=original_card.flavor,
            status="pending",
        )

        # Add after the current card
        self.cards.insert(current_row + 1, new_card)

        # Refresh and select the new card
        self.table_manager.refresh_table()
        self.table.selectRow(current_row + 1)

        # Auto-save
        main_window_save = self.parent().parent() if hasattr(self, "parent") else None
        if main_window_save and hasattr(main_window_save, "auto_save_deck"):
            main_window_save.auto_save_deck(self.cards)

        # Log
        main_window = self.parent().parent() if hasattr(self, "parent") else None
        if main_window and hasattr(main_window, "log_message"):
            main_window.log_message("INFO", f"Duplicated card: {original_card.name}")

    def regenerate_selected_card(self):
        """Regenerate the selected card"""
        current_row = self.table.currentRow()
        if current_row < 0:
            return

        card = self.cards[current_row]
        # Emit signal to regenerate this card
        self.regenerate_card.emit(card)

    def delete_selected_cards(self):
        """Delete selected cards from the deck"""
        selected_rows = self.table_manager.get_selected_rows()

        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select cards to delete")
            return

        # Confirm deletion
        card_count = len(selected_rows)
        reply = QMessageBox.question(
            self,
            "Delete Cards",
            f"Are you sure you want to delete {card_count} card(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Get cards to delete (sort in reverse to maintain indices)
            rows_to_delete = sorted(selected_rows, reverse=True)
            deleted_names = []

            for row in rows_to_delete:
                if 0 <= row < len(self.cards):
                    deleted_names.append(self.cards[row].name)
                    del self.cards[row]

            # Refresh table
            self.table_manager.refresh_table()

            # Auto-save
            main_window_save = (
                self.parent().parent() if hasattr(self, "parent") else None
            )
            if main_window_save and hasattr(main_window_save, "auto_save_deck"):
                main_window_save.auto_save_deck(self.cards)

            # Log the action
            main_window = self.parent().parent() if hasattr(self, "parent") else None
            if main_window and hasattr(main_window, "log_message"):
                main_window.log_message(
                    "INFO",
                    f"Deleted {card_count} card(s): {', '.join(deleted_names[:3])}{'...' if len(deleted_names) > 3 else ''}",
                )

            # Emit signal
            self.cards_updated.emit(self.cards)

    def edit_card(self):
        """Edit selected card"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a card to edit!")
            return

        card = self.cards[current_row]

        # Create edit dialog inline (like in the other edit_card method)
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Edit Card: {card.name}")
        dialog.setModal(True)

        from PyQt6.QtWidgets import QDialogButtonBox, QFormLayout

        layout = QFormLayout()

        name_input = QLineEdit(card.name)
        type_input = QLineEdit(card.type)
        cost_input = QLineEdit(card.cost if card.cost else "")
        text_input = QTextEdit(card.text if card.text else "")
        text_input.setMaximumHeight(100)

        # Add power/toughness for creatures
        power_input = QLineEdit(str(card.power) if card.power else "")
        toughness_input = QLineEdit(str(card.toughness) if card.toughness else "")

        layout.addRow("Name:", name_input)
        layout.addRow("Type:", type_input)
        layout.addRow("Mana Cost:", cost_input)
        layout.addRow("Text:", text_input)
        layout.addRow("Power:", power_input)
        layout.addRow("Toughness:", toughness_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        dialog.setLayout(layout)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            card.name = name_input.text()
            card.type = type_input.text()
            card.cost = cost_input.text()
            card.text = text_input.toPlainText()
            card.power = power_input.text() if power_input.text() else None
            card.toughness = toughness_input.text() if toughness_input.text() else None

            self.table_manager.refresh_table()
            self.cards_updated.emit(self.cards)

    # Preview is now handled by a permanent panel on the right side

    def generate_missing(self):
        """Generate missing values for cards"""
        # TODO: Implement AI generation for missing values
        QMessageBox.information(
            self, "Info", "This feature will generate missing card values"
        )

    def generate_art_descriptions(self):
        """Generate art descriptions for cards missing them"""
        cards_needing_art = [c for c in self.cards if not c.art or c.art == ""]

        if not cards_needing_art:
            QMessageBox.information(
                self, "Info", "All cards already have art descriptions!"
            )

    def use_custom_image_for_selected(self):
        """Use custom image for selected cards"""
        selected_rows = self.table_manager.get_selected_rows()

        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select cards!")
            return

        # Open file dialog
        parent = get_main_window()
        default_dir = ""

        if parent and hasattr(parent, "current_deck_name") and parent.current_deck_name:
            artwork_dir = Path("saved_decks") / parent.current_deck_name / "artwork"
            artwork_dir.mkdir(parents=True, exist_ok=True)
            default_dir = str(artwork_dir)

        image_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Custom Artwork",
            default_dir,
            "Image Files (*.png *.jpg *.jpeg *.gif *.bmp);;All Files (*.*)",
        )

        if image_path:
            for row in selected_rows:
                if 0 <= row < len(self.cards):
                    card = self.cards[row]
                    card.custom_image_path = image_path
                    card.status = "pending"

                    if parent and hasattr(parent, "log_message"):
                        parent.log_message("INFO", f"Set custom image for {card.name}")

            self.refresh_generation_queue()

            # Generate cards with custom image
            cards_with_custom = [
                self.cards[row] for row in selected_rows if 0 <= row < len(self.cards)
            ]

            # Get deck name from parent
            deck_name = None
            parent = get_main_window()
            if parent and hasattr(parent, "current_deck_name"):
                deck_name = parent.current_deck_name

            self.generator_worker.set_cards(
                cards_with_custom,
                self.model_combo.currentText(),
                self.style_combo.currentText(),
                "custom_image",
                deck_name,
            )
            self.generator_worker.start()

    def delete_selected_files(self):
        """Delete generated files for selected cards"""
        selected_rows = self.table_manager.get_selected_rows()

        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select cards!")
            return

        reply = QMessageBox.question(
            self,
            "Delete Files",
            f"Delete generated files for {len(selected_rows)} selected cards?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            deleted_count = 0
            for row in selected_rows:
                if 0 <= row < len(self.cards):
                    card = self.cards[row]

                    # Delete files
                    if (
                        hasattr(card, "card_path")
                        and card.card_path
                        and Path(card.card_path).exists()
                    ):
                        try:
                            Path(card.card_path).unlink()
                            card.card_path = None
                            deleted_count += 1
                        except:
                            pass

                    if (
                        hasattr(card, "image_path")
                        and card.image_path
                        and Path(card.image_path).exists()
                    ):
                        try:
                            Path(card.image_path).unlink()
                            card.image_path = None
                            deleted_count += 1
                        except:
                            pass

                    # Reset status
                    card.status = "pending"
                    card.generated_at = None

            self.refresh_generation_queue()
            self.table_manager.refresh_table()  # Also refresh the main table

            # Update preview if current card was affected
            current_row = self.table.currentRow()
            if current_row in selected_rows and 0 <= current_row < len(self.cards):
                parent = get_main_window()
                if parent and hasattr(parent, "update_card_preview"):
                    parent.update_card_preview(self.cards[current_row])

            parent = get_main_window()
            if parent and hasattr(parent, "log_message"):
                parent.log_message("INFO", f"Deleted {deleted_count} files")

    def refresh_cards_table(self):
        """Refresh the main cards table (renamed from refresh_table)"""
        self.table_manager.refresh_table()  # Call existing refresh_table method

    def on_generation_progress(self, card_id: int, status: str):
        """Handle generation progress updates"""
        # Find the card being processed
        current_card = None
        current_index = 0
        for i, card in enumerate(self.cards):
            if card.id == card_id:
                current_card = card
                current_index = i + 1
                break

        if current_card:
            # Update progress bar
            total = len(self.cards)
            # Progress bar removed - was showing generation progress

            # Update status label
            if hasattr(self, "generation_status_label"):
                self.generation_status_label.setText(f"Generating: {current_card.name}")

            # Update the card status
            current_card.status = "generating"
            self.table_manager.refresh_table()
            self.update_generation_stats()  # Update generation progress

            parent = get_main_window()
            if parent and hasattr(parent, "log_message"):
                parent.log_message(
                    "INFO",
                    f"[{current_index}/{total}] Generating {current_card.name}: {status}",
                )

    def on_generation_completed(
        self, card_id: int, success: bool, message: str, image_path: str, card_path: str
    ):
        """Handle generation completion for a card"""
        # Find the card
        updated_card = None
        for card in self.cards:
            if card.id == card_id:
                if success:
                    card.status = "completed"
                    if image_path:
                        card.image_path = image_path
                    if card_path:
                        card.card_path = card_path
                    updated_card = card
                else:
                    card.status = "failed"
                break

        # Update display
        self.table_manager.refresh_table()
        self.update_button_visibility()  # Update button visibility after refresh
        self.update_generation_stats()  # Update generation progress indicator
        # Re-apply filters after updating the table
        self.table_manager.apply_filter()

        # Update preview if this card is currently selected
        if success and updated_card:
            # Check if this card is currently selected in the table
            current_row = self.table.currentRow()
            if (
                0 <= current_row < len(self.cards)
                and self.cards[current_row].id == card_id
            ):
                # Update the preview
                parent = get_main_window()
                if parent and hasattr(parent, "update_card_preview"):
                    parent.update_card_preview(updated_card)

        # Check if all cards are done
        pending = sum(
            1 for c in self.cards if getattr(c, "status", "pending") == "pending"
        )
        if pending == 0:
            if hasattr(self, "generation_status_label"):
                self.generation_status_label.setText("All cards generated!")
        else:
            if hasattr(self, "generation_status_label"):
                self.generation_status_label.setText(f"{pending} cards remaining")

        parent = get_main_window()
        if parent and hasattr(parent, "log_message"):
            log_type = "INFO" if success else "ERROR"
            parent.log_message(log_type, message)

        # Auto-save deck after generation
        if success and parent and hasattr(parent, "auto_save_deck"):
            parent.auto_save_deck(self.cards)

    def generate_all_cards(self):
        """Generate all pending cards"""
        pending_cards = [
            card
            for card in self.cards
            if not hasattr(card, "status") or card.status == "pending"
        ]

        if not pending_cards:
            QMessageBox.information(
                self, "No Pending Cards", "All cards have been generated!"
            )
            return

        # Set cards for generation
        self.generator_worker.set_cards(
            pending_cards,
            self.model_combo.currentText(),
            self.style_combo.currentText(),
        )
        self.generator_worker.start()

        parent = get_main_window()
        if parent and hasattr(parent, "log_message"):
            parent.log_message(
                "INFO", f"Starting generation of {len(pending_cards)} cards"
            )

    def generate_selected_cards(self):
        """Generate only selected cards"""
        selected_rows = self.table_manager.get_selected_rows()

        if not selected_rows:
            QMessageBox.warning(
                self, "No Selection", "Please select cards to generate!"
            )
            return

        cards_to_generate = []
        for row in selected_rows:
            if 0 <= row < len(self.cards):
                card = self.cards[row]
                if not hasattr(card, "status") or card.status == "pending":
                    cards_to_generate.append(card)

        if not cards_to_generate:
            QMessageBox.information(
                self, "Already Generated", "Selected cards are already generated!"
            )
            return

        self.generator_worker.set_cards(
            cards_to_generate,
            self.model_combo.currentText(),
            self.style_combo.currentText(),
        )
        self.generator_worker.start()

        parent = get_main_window()
        if parent and hasattr(parent, "log_message"):
            parent.log_message(
                "INFO", f"Generating {len(cards_to_generate)} selected cards"
            )

    def refresh_generation_queue(self):
        """Refresh the generation queue table"""

        completed = 0
        pending = 0
        failed = 0

        for _row, card in enumerate(self.cards):
            # ID

            # Name

            # Type
            card_type = (
                card.type.split("—")[0].strip() if "—" in card.type else card.type
            )

            # Set
            card_set = card.set if hasattr(card, "set") and card.set else "CMD"

            # Status
            status = getattr(card, "status", "pending")
            if status == "completed":
                status_text = " Done"
                completed += 1
            elif status == "generating":
                status_text = " Processing"
            elif status == "failed":
                status_text = " Failed"
                failed += 1
            else:
                status_text = " Pending"
                pending += 1

            status_item = QTableWidgetItem(status_text)

            # Time
            generated_at = getattr(card, "generated_at", None)
            # Time column removed from single table view
        # Update progress
        total = len(self.cards)
        if total > 0:
            # Progress bar removed - was showing completion stats
            pass  # Keep the if block valid


class MTGDeckBuilder(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.generation_active = False
        self.current_preview_card = None  # Track for resize events
        self.current_deck_name = None  # Track active deck name
        self.last_loaded_deck_path = None  # Track last loaded deck for auto-loading

        # Initialize generation controller
        self.generation_controller = CardGenerationController(self)

        self.init_ui()
        self.load_settings()
        self.setup_status_timer()
        self.setup_file_watcher()

    def init_ui(self):
        self.setWindowTitle("MTG Commander Deck Builder")

        # Don't set geometry here - will be maximized in main()
        # Just get screen for max width setting
        from PyQt6.QtWidgets import QApplication

        screen = QApplication.primaryScreen()
        screen_rect = screen.availableGeometry()
        self.setMaximumWidth(screen_rect.width())

        # Set dark theme
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #2b2b2b;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QGroupBox {
                border: 1px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #0d7377;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #14a085;
            }
            QPushButton:pressed {
                background-color: #0a5d61;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
            QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {
                background-color: #3c3c3c;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 4px;
            }
            QTableWidget {
                background-color: #3c3c3c;
                gridline-color: #555;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: #0d7377;
            }
            QHeaderView::section {
                background-color: #444;
                padding: 4px;
                border: 1px solid #555;
            }
            QTabWidget::pane {
                border: 1px solid #555;
                background-color: #2b2b2b;
            }
            QTabBar::tab {
                background-color: #3c3c3c;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #0d7377;
            }
            QListWidget {
                background-color: #3c3c3c;
                border: 1px solid #555;
            }
            QListWidget::item {
                padding: 4px;
            }
            QListWidget::item:selected {
                background-color: #0d7377;
            }
        """
        )

        # Create a central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Add a status indicator bar
        self.create_status_bar()
        layout.addWidget(self.status_widget)

        # Create main horizontal splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side: Tabs and Logger in vertical splitter
        left_splitter = QSplitter(Qt.Orientation.Vertical)

        # Tab widget
        self.tabs = QTabWidget()

        # Create tabs
        self.theme_tab = ThemeConfigTab()
        self.cards_tab = CardManagementTab()
        # self.generation_tab = GenerationTab()  # Merged into CardManagementTab

        # Add tabs
        self.tabs.addTab(self.theme_tab, " Theme & Config")
        self.tabs.addTab(self.cards_tab, " Card Management")
        # self.tabs.addTab(self.generation_tab, " Generation")  # Merged with Card Management

        # Set default tab to Card Management (Tab 2, index 1)
        self.tabs.setCurrentIndex(1)

        # Logger panel
        self.create_logger_panel()

        # Add to the left splitter with better proportions for logger
        left_splitter.addWidget(self.tabs)
        left_splitter.addWidget(self.logger_widget)
        left_splitter.setSizes([450, 450])  # Equal split for better logger visibility

        # Right side: Card Preview Panel
        self.create_card_preview_panel()

        # Add to the main splitter
        main_splitter.addWidget(left_splitter)
        main_splitter.addWidget(self.card_preview_widget)
        main_splitter.setSizes([900, 500])  # 900 px for left side, 500 px for preview

        layout.addWidget(main_splitter)

        # Connect signals
        self.theme_tab.cards_generated.connect(self.on_cards_generated)
        self.cards_tab.cards_updated.connect(self.on_cards_updated)
        self.cards_tab.regenerate_card.connect(self.on_regenerate_single_card)

        # Connect card selection signals for preview
        self.cards_tab.table.itemSelectionChanged.connect(
            self.on_card_selection_changed_in_table
        )
        # Connect queue table selection if it exists
        if hasattr(self.cards_tab, "queue_table"):
            self.cards_tab.queue_table.itemSelectionChanged.connect(
                self.on_card_selection_changed_in_generation
            )

        # Connect worker signals for status updates - will be dynamically updated based on task
        self.theme_tab.ai_worker.started.connect(self.on_ai_worker_started)
        self.theme_tab.ai_worker.finished.connect(self.on_ai_worker_finished)
        self.theme_tab.ai_worker.progress_update.connect(
            lambda msg: self.log_message("INFO", msg)
        )
        self.theme_tab.ai_worker.error_occurred.connect(
            lambda err: self.log_message("ERROR", err)
        )
        # Connect log_message signal for thread-safe logging
        self.theme_tab.ai_worker.log_message.connect(self.log_message)

        self.cards_tab.generator_worker.started.connect(
            self.on_image_generation_started
        )
        self.cards_tab.generator_worker.finished.connect(self.on_generation_finished)
        self.cards_tab.generator_worker.progress.connect(
            self.on_image_generation_progress
        )
        self.cards_tab.generator_worker.completed.connect(
            self.on_card_generation_completed
        )
        # Connect log_message signal for thread-safe logging
        self.cards_tab.generator_worker.log_message.connect(self.log_message)

        # Status bar
        self.statusBar().showMessage("Ready")

    def on_cards_generated(self, cards: list[MTGCard]):
        """Handle cards generated from theme tab"""
        self.cards_tab.load_cards(cards)
        self.cards_tab.load_cards(cards)
        self.tabs.setCurrentIndex(1)  # Switch to cards tab
        self.statusBar().showMessage(f"Generated {len(cards)} cards")

        # Log the success
        self.log_message("SUCCESS", f"Successfully generated {len(cards)} cards!")
        if len(cards) < 100:
            self.log_message(
                "WARNING", f"Only {len(cards)} cards generated (expected 100)"
            )

        # Log some card details
        if cards:
            self.log_message("INFO", f"Commander: {cards[0].name if cards else 'None'}")
            lands = sum(1 for c in cards if "Land" in c.type)
            creatures = sum(1 for c in cards if "Creature" in c.type)
            self.log_message(
                "DEBUG", f"Distribution: {lands} lands, {creatures} creatures"
            )

        # Auto-save the NEW deck (only for initial generation)
        self.auto_save_deck(cards, new_generation=True)

    def on_cards_updated(self, cards: list[MTGCard]):
        """Handle cards updated from the management tab"""
        self.cards_tab.load_cards(cards)
        # Auto-save on updates (only update latest, no new timestamp)
        # Note: current_deck_name should already be set from load_deck
        self.auto_save_deck(cards, new_generation=False)

    def load_deck_file_from_main(self, filename: str):
        """Load a deck file from the main window"""
        if hasattr(self, "cards_tab") and hasattr(self.cards_tab, "load_deck_file"):
            self.cards_tab.load_deck_file(filename)

    def on_regenerate_single_card(self, card: MTGCard):
        """Handle single card regeneration request"""
        self.log_message("INFO", f"Regenerating card: {card.name}")

        # Reset card status to pending so it can be regenerated
        card.status = "pending"

        # Update the generation tab with just this card
        # But keep the full list in cards_tab
        current_cards = self.cards_tab.cards.copy()

        # Find and update the card in the list
        for i, c in enumerate(current_cards):
            if str(c.id) == str(card.id):
                current_cards[i] = card
                break

        # Load all cards to the generation tab (it will only generate pending ones)
        self.cards_tab.load_cards(current_cards)

        # Switch to the card tab (generation is now merged there)
        self.tabs.setCurrentIndex(1)

        # Start generation for pending cards (which includes our reset card)
        self.cards_tab.generate_images()

    def auto_save_deck(self, cards: list[MTGCard], new_generation: bool = False):
        """Auto-save deck to YAML file

        Args:
            cards: List of cards to save
            new_generation: If True, creates new timestamp file. If False, only updates latest.
        """
        if not cards:
            return

        # Get theme for metadata (always needed)
        theme = (
            self.theme_tab.get_theme()
            if hasattr(self, "theme_tab") and hasattr(self.theme_tab, "get_theme")
            else "deck"
        )

        # Use current deck name or derive from theme/commander
        if not self.current_deck_name:
            # Try to get deck name from first card (commander) or theme
            if cards and cards[0].name:
                commander_name = (
                    cards[0].name.lower().replace(" ", "_").replace(",", "")
                )
                self.current_deck_name = f"deck_{commander_name}"
                self.update_deck_display()
                self.log_message(
                    "INFO",
                    f"No deck name set, using commander name: {self.current_deck_name}",
                )
            else:
                theme_clean = (
                    theme.lower().replace(" ", "_").replace("(", "").replace(")", "")
                )
                self.current_deck_name = f"deck_{theme_clean}"
                self.update_deck_display()
                self.log_message(
                    "INFO", f"No deck name set, using theme: {self.current_deck_name}"
                )

        # Create deck-specific directory structure
        deck_dir = Path("saved_decks") / self.current_deck_name
        deck_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories for organization
        (deck_dir / "rendered_cards").mkdir(exist_ok=True)
        (deck_dir / "artwork").mkdir(exist_ok=True)

        # Save deck file in the deck folder
        latest_filename = deck_dir / f"{self.current_deck_name}.yaml"

        # Tell file watcher to ignore the next change (our save)
        if hasattr(self, "file_watcher"):
            self.ignore_next_change = True

        # Only create timestamp file for new generations
        timestamp_filename = None
        if new_generation:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            timestamp_filename = deck_dir / f"deck_{theme_clean}_{timestamp}.yaml"

        # Prepare deck data
        deck_data = {
            "theme": theme,
            "generated_at": datetime.now().isoformat(),
            "card_count": len(cards),
            "cards": [],
        }

        for i, card in enumerate(cards):
            # ALWAYS use sequential numeric IDs (no exceptions!)
            card.id = i + 1

            card_dict = {
                "id": card.id,
                "name": card.name,
                "type": card.type,
                "cost": card.cost,
                "text": card.text,
                "power": card.power,
                "toughness": card.toughness,
                "flavor": card.flavor,
                "rarity": card.rarity,
                "art": card.art,
                "status": card.status,
                "image_path": card.image_path,
                "card_path": card.card_path,
                "generated_at": card.generated_at,
                "set": card.set if hasattr(card, "set") else "CMD",
            }
            deck_data["cards"].append(card_dict)

        try:
            # Save main deck file
            with open(latest_filename, "w") as f:
                yaml.dump(deck_data, f, default_flow_style=False, allow_unicode=True)

            # Also save timestamped backup for new generations
            if new_generation:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_dir = deck_dir / "backups"
                backup_dir.mkdir(exist_ok=True)
                backup_filename = (
                    backup_dir / f"{self.current_deck_name}_{timestamp}.yaml"
                )
                with open(backup_filename, "w") as f:
                    yaml.dump(
                        deck_data, f, default_flow_style=False, allow_unicode=True
                    )
                self.log_message("INFO", f"Deck saved to: {deck_dir.name}/")
                self.log_message("DEBUG", f"Backup created: {backup_filename.name}")
            else:
                self.log_message(
                    "DEBUG",
                    f"Auto-saved to: {self.current_deck_name}/{latest_filename.name}",
                )

        except Exception as e:
            self.log_message("ERROR", f"Failed to auto-save deck: {str(e)}")

    def create_logger_panel(self):
        """Create the logger panel on the right side"""
        self.logger_widget = QWidget()
        self.logger_widget.setMinimumWidth(400)
        self.logger_widget.setStyleSheet(
            """
            QWidget {
                background-color: #2b2b2b;
                border-left: 2px solid #555;
            }
        """
        )

        logger_layout = QVBoxLayout(self.logger_widget)

        # Logger header
        header_widget = QWidget()
        header_widget.setFixedHeight(50)  # Fixed height to prevent cutting
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(10, 5, 10, 5)  # Better margins

        logger_label = QLabel(" Logs & Output")
        logger_label.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #4ec9b0;"
        )
        header_layout.addWidget(logger_label)

        # Log level filter
        filter_label = QLabel("Filter:")
        filter_label.setStyleSheet("color: #cccccc;")
        header_layout.addWidget(filter_label)

        self.log_filter = QComboBox()
        self.log_filter.addItems(["All", "Info", "Warning", "Error", "Debug"])
        self.log_filter.setFixedWidth(100)
        self.log_filter.setFixedHeight(30)  # Fixed height
        self.log_filter.currentTextChanged.connect(self.filter_logs)
        header_layout.addWidget(self.log_filter)

        header_layout.addStretch()

        # Clear button
        clear_logs_btn = QPushButton("Clear")
        clear_logs_btn.setFixedSize(60, 30)  # Fixed size
        clear_logs_btn.clicked.connect(self.clear_logs)
        header_layout.addWidget(clear_logs_btn)

        logger_layout.addWidget(header_widget)

        # Logger text area
        self.logger_text = QTextEdit()
        self.logger_text.setReadOnly(True)
        self.logger_text.setFont(QFont("Consolas", 10))
        self.logger_text.setStyleSheet(
            """
            QTextEdit {
                background-color: #1e1e1e;
                color: #cccccc;
                border: 1px solid #3e3e42;
                border-radius: 5px;
                padding: 5px;
            }
        """
        )
        logger_layout.addWidget(self.logger_text)

        # Auto-scroll checkbox
        self.auto_scroll_cb = QCheckBox("Auto-scroll")
        self.auto_scroll_cb.setChecked(True)
        logger_layout.addWidget(self.auto_scroll_cb)

        # Initialize with welcome message
        self.log_message("INFO", "MTG Deck Builder started", "#4ec9b0")
        self.log_message("INFO", "Ready to generate Commander decks!", "#4ec9b0")

    def create_card_preview_panel(self):
        """Create the permanent card preview panel"""
        self.card_preview_widget = QWidget()
        layout = QVBoxLayout(self.card_preview_widget)

        # Title
        title_label = QLabel("<h3>Card Preview</h3>")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #4ec9b0; font-weight: bold; padding: 10px;")
        layout.addWidget(title_label)

        # Card preview image (no tabs)
        self.card_image_label = QLabel()
        self.card_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.card_image_label.setScaledContents(False)  # Keep aspect ratio
        self.card_image_label.setStyleSheet(
            """
            QLabel {
                border: 2px solid #555;
                border-radius: 10px;
                background-color: #3c3c3c;
                color: #888;
                padding: 10px;
            }
        """
        )
        self.card_image_label.setText("Select a card to preview")
        layout.addWidget(self.card_image_label, 1)  # Stretch factor 1

        # Card Details
        details_group = QGroupBox("Card Details")
        details_layout = QVBoxLayout()

        # Card name
        self.preview_name = QLabel("No card selected")
        self.preview_name.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #4ec9b0; padding: 5px;"
        )
        self.preview_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        details_layout.addWidget(self.preview_name)

        # Card info
        info_layout = QVBoxLayout()

        self.preview_type = QLabel("Type: ")
        self.preview_cost = QLabel("Cost: ")
        self.preview_pt = QLabel("P/T: ")
        self.preview_rarity = QLabel("Rarity: ")
        self.preview_status = QLabel("Status: ")

        for label in [
            self.preview_type,
            self.preview_cost,
            self.preview_pt,
            self.preview_rarity,
            self.preview_status,
        ]:
            label.setStyleSheet("padding: 2px; color: #cccccc;")
            info_layout.addWidget(label)

        details_layout.addLayout(info_layout)

        # Card text
        self.preview_text = QLabel("Text: ")
        self.preview_text.setWordWrap(True)
        self.preview_text.setStyleSheet(
            "padding: 5px; color: #cccccc; background-color: #3c3c3c; border: 1px solid #555; border-radius: 3px;"
        )
        self.preview_text.setMaximumHeight(80)
        details_layout.addWidget(self.preview_text)

        # Flavor text
        self.preview_flavor = QLabel("Flavor: ")
        self.preview_flavor.setWordWrap(True)
        self.preview_flavor.setStyleSheet(
            "padding: 5px; color: #dcdcaa; font-style: italic; background-color: #3c3c3c; border: 1px solid #555; border-radius: 3px;"
        )
        self.preview_flavor.setMaximumHeight(60)
        details_layout.addWidget(self.preview_flavor)

        details_group.setLayout(details_layout)
        layout.addWidget(details_group)

        # Generation info
        gen_info_layout = QHBoxLayout()
        self.preview_generated_at = QLabel("Not generated")
        self.preview_generated_at.setStyleSheet("color: #969696; font-size: 10px;")
        gen_info_layout.addWidget(self.preview_generated_at)
        gen_info_layout.addStretch()
        layout.addLayout(gen_info_layout)

        layout.addStretch()

        # Current selected card
        self.current_preview_card = None

        self.card_preview_widget.setMinimumWidth(400)
        self.card_preview_widget.setMaximumWidth(450)

    def log_message(self, level: str, message: str, color: str = "#cccccc"):
        """Add a message to the logger"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Color coding for different levels
        level_colors = {
            "INFO": "#4ec9b0",
            "WARNING": "#dcdcaa",
            "ERROR": "#f48771",
            "DEBUG": "#969696",
            "SUCCESS": "#4ec9b0",
            "GENERATING": "#ce9178",
        }

        level_color = level_colors.get(level, color)

        # Format the message with HTML
        formatted_msg = f"""
        <span style="color: #969696;">[{timestamp}]</span>
        <span style="color: {level_color}; font-weight: bold;">[{level}]</span>
        <span style="color: {color};">{message}</span>
        """

        cursor = self.logger_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertHtml(formatted_msg + "<br>")

        # Auto-scroll if enabled
        if self.auto_scroll_cb.isChecked():
            self.logger_text.verticalScrollBar().setValue(
                self.logger_text.verticalScrollBar().maximum()
            )

    def clear_logs(self):
        """Clear the logger"""
        self.logger_text.clear()
        self.log_message("INFO", "Logs cleared", "#4ec9b0")

    def filter_logs(self, filter_type: str):
        """Filter logs by type (not implemented for simplicity)"""
        self.log_message("INFO", f"Filter set to: {filter_type}", "#969696")

    def create_status_bar(self):
        """Create the status indicator bar"""
        self.status_widget = QWidget()
        self.status_widget.setMaximumHeight(50)
        self.status_widget.setStyleSheet(
            """
            QWidget {
                background-color: #3c3c3c;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 5px;
                margin: 5px;
            }
        """
        )

        layout = QHBoxLayout(self.status_widget)
        layout.setContentsMargins(10, 5, 10, 5)

        # Status indicator with animated dots
        self.status_indicator = QLabel("🟢 Ready")
        self.status_indicator.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #4ec9b0;"
        )
        layout.addWidget(self.status_indicator)

        # Current task label - initially hidden
        self.current_task_label = QLabel("")
        self.current_task_label.setStyleSheet(
            "font-size: 14px; color: #cccccc; margin-left: 20px;"
        )
        self.current_task_label.setVisible(False)  # Hide when empty
        layout.addWidget(self.current_task_label)

        # Progress bar - initially hidden
        self.generation_progress = QProgressBar()
        self.generation_progress.setMaximumHeight(20)
        self.generation_progress.setMinimumWidth(200)
        self.generation_progress.setVisible(False)
        self.generation_progress.setStyleSheet(
            """
            QProgressBar {
                border: 1px solid #555;
                border-radius: 3px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #0d7377, stop: 1 #14b8a6);
                border-radius: 2px;
            }
        """
        )
        layout.addWidget(self.generation_progress)

        # Spacer
        layout.addStretch()

        # Deck selector section
        deck_separator = QLabel("|")
        deck_separator.setStyleSheet("color: #555; margin: 0 10px;")
        layout.addWidget(deck_separator)

        deck_label = QLabel("Active Deck:")
        deck_label.setStyleSheet("font-size: 14px; color: #4ec9b0; font-weight: bold;")
        layout.addWidget(deck_label)

        # Make deck name display read-only with double-click to edit
        self.deck_name_display = QLabel("No deck loaded")
        self.deck_name_display.setMinimumWidth(200)
        self.deck_name_display.setMaximumWidth(300)
        self.deck_name_display.setStyleSheet(
            """
            QLabel {
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #555;
                padding: 5px 10px;
                border-radius: 3px;
                font-weight: bold;
            }
            QLabel:hover {
                border: 1px solid #4ec9b0;
            }
        """
        )

        # Enable double-click to rename
        self.deck_name_display.setToolTip("Double-click to rename deck")
        self.deck_name_display.mouseDoubleClickEvent = (
            lambda _event: self.rename_deck_dialog()
        )
        layout.addWidget(self.deck_name_display)

        # Add deck switcher dropdown
        self.deck_switcher = QComboBox()
        self.deck_switcher.setMinimumWidth(200)
        self.deck_switcher.setMaximumWidth(300)
        self.deck_switcher.setStyleSheet(
            """
            QComboBox {
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #555;
                padding: 5px;
                border-radius: 3px;
            }
            QComboBox:hover {
                border: 1px solid #4ec9b0;
            }
            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: white;
                selection-background-color: #4ec9b0;
            }
        """
        )
        self.deck_switcher.setToolTip("Quick deck switcher")
        self.populate_deck_switcher()
        self.deck_switcher.currentTextChanged.connect(self.on_deck_switch)
        layout.addWidget(self.deck_switcher)

        # Add rename button
        self.rename_deck_button = QPushButton("✏️ Rename")
        self.rename_deck_button.setMinimumWidth(100)
        self.rename_deck_button.setToolTip("Click to rename deck")
        self.rename_deck_button.clicked.connect(self.rename_deck_dialog)
        self.rename_deck_button.setEnabled(False)  # Disabled until deck is loaded
        layout.addWidget(self.rename_deck_button)

        # Add spacer before time
        layout.addStretch()

        # Time elapsed label (for generation timing)
        self.time_label = QLabel("")
        self.time_label.setStyleSheet("font-size: 12px; color: #969696;")
        layout.addWidget(self.time_label)

    def populate_deck_switcher(self):
        """Populate the deck switcher dropdown with available decks"""
        from pathlib import Path

        saved_decks_dir = Path("saved_decks")

        # Clear and add placeholder
        self.deck_switcher.clear()
        self.deck_switcher.addItem("-- Select Deck --")

        if saved_decks_dir.exists():
            # Get all deck directories
            deck_dirs = [
                d
                for d in saved_decks_dir.iterdir()
                if d.is_dir() and d.name.startswith("deck_")
            ]
            # Sort by modification time (most recent first)
            deck_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            # Add max 10 recent decks
            for deck_dir in deck_dirs[:10]:
                deck_name = deck_dir.name
                # Check if YAML file exists
                yaml_file = deck_dir / f"{deck_name}.yaml"
                if yaml_file.exists():
                    self.deck_switcher.addItem(deck_name)

        # Select current deck if loaded
        if self.current_deck_name:
            index = self.deck_switcher.findText(self.current_deck_name)
            if index >= 0:
                self.deck_switcher.setCurrentIndex(index)

    def on_deck_switch(self, deck_name: str):
        """Handle deck selection from dropdown"""
        if not deck_name or deck_name == "-- Select Deck --":
            return

        # Don't reload if it's the same deck
        if deck_name == self.current_deck_name:
            return

        from pathlib import Path

        yaml_path = Path("saved_decks") / deck_name / f"{deck_name}.yaml"

        if yaml_path.exists():
            self.log_message("INFO", f"Switching to deck: {deck_name}")
            # Load the deck through the cards tab
            if hasattr(self, "cards_tab"):
                self.cards_tab.load_deck_file(str(yaml_path))

    def update_deck_display(self):
        """Update the deck name display"""
        if self.current_deck_name:
            self.deck_name_display.setText(self.current_deck_name)
            self.rename_deck_button.setEnabled(True)
            # Update dropdown selection
            self.populate_deck_switcher()
        else:
            self.deck_name_display.setText("No deck loaded")
            self.rename_deck_button.setEnabled(False)

    def rename_deck_dialog(self):
        """Open dialog to rename the current deck"""
        if not self.current_deck_name:
            return

        # Create input dialog
        from PyQt6.QtWidgets import QInputDialog

        new_name, ok = QInputDialog.getText(
            self,
            "Rename Deck",
            f"Enter new name for deck '{self.current_deck_name}':",
            text=self.current_deck_name,
        )

        if ok and new_name:
            # Clean the name
            clean_name = new_name.lower().replace(" ", "_")
            if not clean_name.startswith("deck_"):
                clean_name = f"deck_{clean_name}"

            # Check if name is actually different
            if clean_name == self.current_deck_name:
                return

            # Check if new name already exists
            new_deck_dir = Path("saved_decks") / clean_name
            if new_deck_dir.exists():
                reply = QMessageBox.question(
                    self,
                    "Deck Exists",
                    f"A deck named '{clean_name}' already exists.\nDo you want to overwrite it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return

            # Rename the deck folder and files
            old_deck_dir = Path("saved_decks") / self.current_deck_name

            try:
                # Rename the folder
                if old_deck_dir.exists():
                    import shutil

                    shutil.move(str(old_deck_dir), str(new_deck_dir))

                    # Rename the main deck file
                    old_yaml = new_deck_dir / f"{self.current_deck_name}.yaml"
                    new_yaml = new_deck_dir / f"{clean_name}.yaml"
                    if old_yaml.exists():
                        old_yaml.rename(new_yaml)

                    # Update current deck name
                    old_name = self.current_deck_name
                    self.current_deck_name = clean_name
                    self.last_loaded_deck_path = str(new_yaml)

                    # Update display
                    self.update_deck_display()

                    # Update file watcher
                    if hasattr(self, "file_watcher") and hasattr(self, "watching_file"):
                        self.file_watcher.removePath(self.watching_file)
                        self.file_watcher.addPath(str(new_yaml))
                        self.watching_file = str(new_yaml)

                    self.log_message(
                        "SUCCESS", f"✅ Deck renamed from '{old_name}' to '{clean_name}'"
                    )
                    QMessageBox.information(
                        self, "Success", f"Deck renamed successfully to:\n{clean_name}"
                    )
                else:
                    # Just update the name if folder doesn't exist yet
                    self.current_deck_name = clean_name
                    self.update_deck_display()
                    self.log_message("INFO", f"Deck name set to: {clean_name}")

            except Exception as e:
                QMessageBox.critical(
                    self, "Rename Failed", f"Failed to rename deck:\n{str(e)}"
                )
                self.log_message("ERROR", f"❌ Failed to rename deck: {str(e)}")
                self.log_message("INFO", f"Created new deck folder: {clean_name}")

    def setup_status_timer(self):
        """Setup timer for animated status updates"""
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status_animation)
        self.dot_count = 0
        self.start_time = None

    def update_status(self, status: str, message: str = ""):
        """Update the status indicator"""
        if status == "generating":
            self.status_indicator.setText("🔄 Generating")
            self.status_indicator.setStyleSheet(
                "font-size: 16px; font-weight: bold; color: #f48771;"
            )
            self.current_task_label.setText(message)
            self.current_task_label.setVisible(True)  # Show when generating
            self.generation_progress.setVisible(True)
            self.generation_active = True
            self.start_time = datetime.now()
            self.status_timer.start(500)  # Update every 500ms
        elif status == "ready":
            self.status_indicator.setText("🟢 Ready")
            self.status_indicator.setStyleSheet(
                "font-size: 16px; font-weight: bold; color: #4ec9b0;"
            )
            self.current_task_label.setText("")
            self.current_task_label.setVisible(False)  # Hide when ready
            self.generation_progress.setVisible(False)
            self.generation_active = False
            self.status_timer.stop()
            self.time_label.setText("")
        elif status == "error":
            self.status_indicator.setText("❌ Error")
            self.status_indicator.setStyleSheet(
                "font-size: 16px; font-weight: bold; color: #f48771;"
            )
            self.current_task_label.setText(message)
            self.current_task_label.setVisible(True)  # Show error message
            self.generation_active = False
            self.status_timer.stop()

    def update_status_animation(self):
        """Animate the status with dots"""
        if self.generation_active:
            dots = "." * (self.dot_count % 4)
            current_text = self.current_task_label.text()
            if current_text:
                base_text = current_text.rstrip(".")
                self.current_task_label.setText(base_text + dots)

            # Update time elapsed
            if self.start_time:
                elapsed = datetime.now() - self.start_time
                minutes = int(elapsed.total_seconds() // 60)
                seconds = int(elapsed.total_seconds() % 60)
                self.time_label.setText(f"Time: {minutes:02d}:{seconds:02d}")

            self.dot_count += 1

    def on_card_selection_changed_in_table(self):
        """Handle card selection in Card Management table"""
        current_row = self.cards_tab.table.currentRow()
        if (
            current_row >= 0
            and hasattr(self.cards_tab, "cards")
            and current_row < len(self.cards_tab.cards)
        ):
            card = self.cards_tab.cards[current_row]
            self.update_card_preview(card)

    def on_card_selection_changed_in_generation(self):
        """Handle card selection in Generation Tab table"""
        selected_rows = set()
        for item in self.cards_tab.queue_table.selectedItems():
            selected_rows.add(item.row())

        if selected_rows:
            row = min(selected_rows)  # Get first selected row
            if 0 <= row < len(self.cards_tab.cards):
                card = self.cards_tab.cards[row]
                self.update_card_preview(card)

    def resizeEvent(self, event):
        """Handle window resize to update card preview"""
        super().resizeEvent(event)
        # Update card preview if one is selected
        if self.current_preview_card:
            # Use a timer to avoid too many updates during resize
            if hasattr(self, "_resize_timer"):
                self._resize_timer.stop()
            else:
                from PyQt6.QtCore import QTimer

                self._resize_timer = QTimer()
                self._resize_timer.timeout.connect(self._update_preview_after_resize)
                self._resize_timer.setSingleShot(True)
            self._resize_timer.start(100)  # Update after 100ms

    def _update_preview_after_resize(self):
        """Update preview after resize completes"""
        if self.current_preview_card:
            self.update_card_images(self.current_preview_card)

    def clear_card_preview(self):
        """Clear the card preview panel"""
        self.current_preview_card = None
        self.preview_name.setText("Select a card")
        self.preview_type.setText("Type: ")
        self.preview_cost.setText("Cost: ")
        self.preview_pt.setText("P/T: ")
        self.preview_rarity.setText("Rarity: ")
        self.preview_status.setText("Status: ")
        self.preview_text.setText("Text: ")
        self.preview_flavor.setText("Flavor: ")

        # Clear card image
        self.card_image_label.setText("Select a card to preview")

    def update_card_preview(self, card: MTGCard):
        """Update the card preview panel with the selected card"""
        self.current_preview_card = card

        # Update card name
        self.preview_name.setText(card.name)

        # Update card details
        self.preview_type.setText(f"Type: {card.type}")
        self.preview_cost.setText(f"Cost: {card.cost or ''}")

        if card.power is not None and card.toughness is not None:
            self.preview_pt.setText(f"P/T: {card.power}/{card.toughness}")
        else:
            self.preview_pt.setText("P/T: ")

        self.preview_rarity.setText(f"Rarity: {card.rarity}")

        # Status with color coding
        status_colors = {
            "pending": "#dcdcaa",
            "generating": "#ce9178",
            "completed": "#4ec9b0",
            "failed": "#f48771",
        }
        status_color = status_colors.get(card.status, "#cccccc")
        self.preview_status.setText(f"Status: {card.status}")
        self.preview_status.setStyleSheet(
            f"padding: 2px; color: {status_color}; font-weight: bold;"
        )

        # Update card text
        if card.text:
            display_text = card.text.replace("\\n", "\n")
            if len(display_text) > 100:
                display_text = display_text[:100] + "..."
            self.preview_text.setText(f"Text: {display_text}")
        else:
            self.preview_text.setText("Text: ")

        # Update flavor text
        if card.flavor:
            display_flavor = card.flavor
            if len(display_flavor) > 80:
                display_flavor = display_flavor[:80] + "..."
            self.preview_flavor.setText(f"Flavor: {display_flavor}")
        else:
            self.preview_flavor.setText("Flavor: ")

        # Update generation info
        if card.generated_at:
            self.preview_generated_at.setText(f"Generated: {card.generated_at}")
        else:
            self.preview_generated_at.setText("Not generated")

        # Update images
        self.update_card_images(card)

    def update_card_images(self, card: MTGCard):
        """Update the card image previews"""
        # Get main window safely
        main_window = get_main_window()

        # Log what we're trying to load (only if main window found)
        if main_window and hasattr(main_window, "log_message"):
            main_window.log_message("DEBUG", f"Updating preview for card: {card.name}")
            main_window.log_message("DEBUG", f"Card path: {card.card_path}")
            main_window.log_message("DEBUG", f"Image path: {card.image_path}")

        # Full card image
        card_file = None
        if card.card_path:
            card_file = Path(card.card_path)
            if not card_file.exists():
                # Try to find in output directory using generate_card.py naming
                safe_name = make_safe_filename(card.name)
                card_file = self._find_card_image(safe_name)
                if card_file:
                    card.card_path = str(card_file)  # Update the card object
                    if main_window and hasattr(main_window, "log_message"):
                        main_window.log_message(
                            "DEBUG", f"Found card in output directory: {card_file}"
                        )
        else:
            # No card_path set, try to find it
            safe_name = make_safe_filename(card.name)
            card_file = self._find_card_image(safe_name)
            if card_file:
                card.card_path = str(card_file)  # Update the card object
                if main_window and hasattr(main_window, "log_message"):
                    main_window.log_message(
                        "DEBUG", f"Found card in output directory: {card_file}"
                    )

        if card_file and card_file.exists():
            if main_window and hasattr(main_window, "log_message"):
                main_window.log_message(
                    "DEBUG", f"Loading card image from: {card_file}"
                )
            pixmap = QPixmap(str(card_file))
            if not pixmap.isNull():
                # Get the available space in the preview widget
                # Standard MTG card ratio is approximately 2.5:3.5 (width:height)
                label_width = self.card_image_label.width() - 20  # Account for padding
                label_height = self.card_image_label.height() - 20

                # Scale to fit without cutting anything off
                if label_width > 0 and label_height > 0:
                    scaled_pixmap = pixmap.scaled(
                        label_width,
                        label_height,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                else:
                    # Fallback to reasonable default size
                    scaled_pixmap = pixmap.scaled(
                        350,
                        488,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )

                self.card_image_label.setPixmap(scaled_pixmap)
                print(
                    f"[SUCCESS] Card loaded (size: {scaled_pixmap.width()}x{scaled_pixmap.height()})"
                )
            else:
                self.card_image_label.setText("Card image failed to load")
                if main_window and hasattr(main_window, "log_message"):
                    main_window.log_message(
                        "ERROR", "QPixmap failed to load card image"
                    )
        else:
            self.card_image_label.setText(
                f"Card image not available\n\n{card.name}\n{card.type}"
            )
            if main_window and hasattr(main_window, "log_message"):
                main_window.log_message(
                    "WARNING", f"No card image found for {card.name}"
                )

    def _find_card_image(self, safe_name: str) -> Path:
        """Find card image in output directories, handling timestamp patterns"""
        # Check direct path first
        direct_path = Path("output") / f"{safe_name}.png"
        if direct_path.exists():
            return direct_path

        # Check in cards subdirectory with timestamp pattern
        cards_dir = Path("output/cards")
        if cards_dir.exists():
            # Look for files matching the pattern: safe_name_YYYYMMDD_HHMMSS.png
            pattern = f"{safe_name}_*.png"
            matching_files = list(cards_dir.glob(pattern))
            if matching_files:
                # Return the most recent file
                matching_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                return matching_files[0]

        # Check in images subdirectory
        images_dir = Path("output/images")
        if images_dir.exists():
            pattern = f"{safe_name}_*.png"
            matching_files = list(images_dir.glob(pattern))
            if matching_files:
                matching_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                return matching_files[0]

        # Check in root output directory with timestamp
        output_dir = Path("output")
        if output_dir.exists():
            pattern = f"{safe_name}_*.png"
            matching_files = list(output_dir.glob(pattern))
            if matching_files:
                matching_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                return matching_files[0]

        return None

    def on_ai_worker_started(self):
        """Handle AI worker start based on current task"""
        task = self.theme_tab.ai_worker.task
        if task == "analyze_theme":
            self.update_status("generating", "Analyzing theme...")
            self.log_message("GENERATING", "Starting theme analysis...")
        elif task == "generate_cards":
            self.update_status("generating", "Generating 100 cards...")
            self.log_message("GENERATING", "Generating 100 Commander deck cards...")
        elif task == "generate_art":
            self.update_status("generating", "Generating art descriptions...")
            self.log_message("GENERATING", "Creating art descriptions for cards...")
        else:
            self.update_status("generating", "Processing...")
            self.log_message("INFO", "Processing request...")

    def on_ai_worker_finished(self):
        """Handle AI worker finish"""
        self.update_status("ready", "")
        task = self.theme_tab.ai_worker.task
        if task == "analyze_theme":
            self.log_message("SUCCESS", "Theme analysis complete!")
        elif task == "generate_cards":
            self.log_message("INFO", "Card generation complete, check Tab 2")
        elif task == "generate_art":
            self.log_message("SUCCESS", "Art descriptions generated!")

    def on_image_generation_started(self):
        """Handle image generation start"""
        if hasattr(self.cards_tab, "cards"):
            total = len([c for c in self.cards_tab.cards if c.status == "pending"])
            self.update_status("generating", f"Generating images (0/{total})...")
            self.log_message(
                "GENERATING", f"Starting image generation for {total} cards..."
            )

    def on_generation_finished(self):
        """Handle generation finish"""
        self.update_status("ready", "")
        self.log_message("SUCCESS", "Image generation complete!")

    def on_card_generation_completed(self, card_id, success: bool, message: str):
        """Handle individual card completion"""
        # Debug to understand ID issues
        self.log_message(
            "DEBUG",
            f"on_card_generation_completed called with ID: {card_id} (type: {type(card_id)})",
        )
        if success:
            self.log_message("SUCCESS", f"Card {card_id} generated successfully")
        else:
            self.log_message("ERROR", f"Card {card_id} failed: {message}")

    def on_image_generation_progress(self, card_id: int, status: str):
        """Update status for individual image generation"""
        if hasattr(self.cards_tab, "cards"):
            # Find the card being processed
            current_card = None
            for card in self.cards_tab.cards:
                if str(card.id) == str(card_id):
                    current_card = card
                    break

            total = len(self.cards_tab.cards)
            completed = sum(1 for c in self.cards_tab.cards if c.status == "completed")
            processing = card_id

            if status == "generating" and current_card:
                # Show specific card being generated
                self.update_status(
                    "generating",
                    f"Generating image {processing}/{total}: {current_card.name}",
                )
                self.generation_progress.setMaximum(total)
                self.generation_progress.setValue(completed)
                self.generation_progress.setFormat(
                    f"{completed}/{total} ({int(completed/total*100)}%)"
                )
            elif status == "completed":
                self.generation_progress.setValue(completed + 1)

    def on_generation_progress(self, card_id: int, status: str):
        """Update progress bar when generating cards"""
        self.on_image_generation_progress(card_id, status)

    def load_settings(self):
        """Load application settings"""
        settings = QSettings("MTGDeckBuilder", "Settings")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        # Load last deck if available
        last_deck_path = settings.value("last_deck_path")
        if last_deck_path and Path(last_deck_path).exists():
            self.log_message(
                "INFO", f"Auto-loading last deck: {Path(last_deck_path).name}"
            )
            # Delay loading to ensure UI is fully initialized
            QTimer.singleShot(
                100, lambda: self.cards_tab.load_deck_file(last_deck_path)
            )

    def setup_file_watcher(self):
        """Setup file watcher for automatic deck reload"""
        from PyQt6.QtCore import QFileSystemWatcher

        self.file_watcher = QFileSystemWatcher()
        self.file_watcher.fileChanged.connect(self.on_deck_file_changed)
        self.watching_file = None
        self.ignore_next_change = False

    def on_deck_file_changed(self, path):
        """Handle external changes to deck file"""
        if self.ignore_next_change:
            self.ignore_next_change = False
            return

        # Show notification that file changed
        self.log_message("INFO", f"📝 Deck file changed externally: {Path(path).name}")
        self.log_message("INFO", "🔄 Auto-reloading deck...")

        # Automatically reload the deck without asking
        from PyQt6.QtCore import QTimer

        # Small delay to ensure file write is complete
        QTimer.singleShot(100, lambda: self.cards_tab.reload_current_deck())

        # Re-add the file to watcher (Qt removes it after change)
        if Path(path).exists():
            self.file_watcher.addPath(path)

    def closeEvent(self, event):
        """Save settings on close"""
        settings = QSettings("MTGDeckBuilder", "Settings")
        settings.setValue("geometry", self.saveGeometry())

        # Save current deck path if one is loaded
        if hasattr(self, "last_loaded_deck_path") and self.last_loaded_deck_path:
            settings.setValue("last_deck_path", self.last_loaded_deck_path)

        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("MTG Deck Builder")

    window = MTGDeckBuilder()

    # Force fullscreen/maximized mode
    from PyQt6.QtCore import Qt

    # Use WindowFullScreen for true fullscreen or WindowMaximized for maximized with taskbar
    window.setWindowState(Qt.WindowState.WindowFullScreen)  # Echter Vollbild-Modus
    # Alternativ: window.setWindowState(Qt.WindowState.WindowMaximized)  # Maximiert mit Taskleiste
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
