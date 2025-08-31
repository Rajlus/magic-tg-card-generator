#!/usr/bin/env python3
"""
MTG Commander Deck Builder GUI
Complete tool for generating 100-card Commander decks with AI assistance
"""

import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
import yaml

# Import environment variables
from dotenv import load_dotenv
from PyQt6.QtCore import QSettings, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QIcon, QPixmap, QTextCursor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

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

    # If already in correct format, return as is
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


class CardGeneratorWorker(QThread):
    """Worker thread for card generation"""

    progress = pyqtSignal(int, str)  # card_id, status
    completed = pyqtSignal(
        int, bool, str, str, str
    )  # card_id, success, message, image_path, card_path
    log_message = pyqtSignal(str, str)  # level, message - for thread-safe logging

    def __init__(self):
        super().__init__()
        self.cards_queue = []
        self.model = "sdxl"
        self.style = "mtg_modern"
        self.paused = False
        self.current_card = None
        self.theme = "default"
        self.output_dir = None

    def set_cards(
        self,
        cards: list[MTGCard],
        model: str,
        style: str,
        theme: str = "default",
        deck_name: str = None,
    ):
        self.cards_queue = cards.copy()
        self.model = model
        self.style = style
        self.theme = theme.lower().replace(" ", "_")
        self.deck_name = deck_name

        # Handle different regeneration types
        if theme == "card_only_regeneration":
            self.regeneration_type = "card_only"
            self.theme = "regeneration"
        elif theme == "regeneration_with_image":
            self.regeneration_type = "with_image"
            self.theme = "regeneration"
        else:
            self.regeneration_type = None

        # Use deck-specific output directory if deck name provided
        if self.deck_name:
            self.output_dir = Path("saved_decks") / self.deck_name
            self.cards_dir = self.output_dir / "rendered_cards"
            self.images_dir = self.output_dir / "artwork"
        else:
            # Fallback to old structure
            self.output_dir = Path("generated_cards") / self.theme
            self.cards_dir = self.output_dir / "cards"
            self.images_dir = self.output_dir / "images"

        # Create directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cards_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def run(self):
        """Process card generation queue"""
        # Note: We can't directly access GUI elements from worker thread
        # Use signals instead for thread-safe communication

        for card in self.cards_queue:
            if self.paused:
                while self.paused:
                    self.msleep(100)

            self.current_card = card
            # Debug logging for ID tracking
            self.log_message.emit(
                "DEBUG",
                f"Processing card: {card.name} with ID: {card.id} (type: {type(card.id)})",
            )
            self.progress.emit(card.id, "generating")

            try:
                # Build command with output directories
                command = card.get_command(self.model, self.style)

                # Add output directory parameters with absolute paths
                cards_dir_abs = self.cards_dir.absolute()
                images_dir_abs = self.images_dir.absolute()
                command += f" --output {escape_for_shell(str(cards_dir_abs))}"
                command += f" --images-output {escape_for_shell(str(images_dir_abs))}"

                self.log_message.emit(
                    "DEBUG",
                    f"Output directories: cards={cards_dir_abs}, images={images_dir_abs}",
                )

                # Check if this is card-only regeneration
                if (
                    hasattr(self, "regeneration_type")
                    and self.regeneration_type == "card_only"
                ):
                    # Add skip-image flag to prevent new artwork generation
                    command += " --skip-image"
                    self.log_message.emit(
                        "INFO", f"Card-only regeneration mode for: {card.name}"
                    )
                    self.log_message.emit(
                        "DEBUG", f"Existing artwork path: {card.image_path}"
                    )
                else:
                    # Normal generation or regeneration with new image
                    self.log_message.emit(
                        "INFO", f"Full generation mode for: {card.name}"
                    )

                self.log_message.emit("DEBUG", f"Command: {command}")

                # Execute command
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    cwd=os.path.dirname(os.path.abspath(__file__)),
                )

                # Log ALL output from the subprocess
                if result.stdout:
                    # Split stdout by lines and log each line
                    for line in result.stdout.strip().split("\n"):
                        if line.strip():
                            # Parse the line to extract log level if present
                            line_lower = line.lower()
                            if "✅" in line or "SUCCESS" in line:
                                self.log_message.emit("SUCCESS", line)
                            elif "❌" in line or "ERROR" in line or "Failed" in line:
                                self.log_message.emit("ERROR", line)
                            elif any(
                                err in line_lower
                                for err in [
                                    "missing",
                                    "invalid",
                                    "corrupted",
                                    "black regions",
                                    "too dark",
                                ]
                            ):
                                self.log_message.emit(
                                    "ERROR", f"[generate_card.py] {line}"
                                )
                            elif "⚠️" in line or "WARNING" in line:
                                self.log_message.emit("WARNING", line)
                            elif "🎨" in line or "Generating" in line:
                                self.log_message.emit("GENERATING", line)
                            elif "INFO" in line or "📋" in line or "🔍" in line:
                                self.log_message.emit("INFO", line)
                            elif "DEBUG" in line:
                                self.log_message.emit("DEBUG", line)
                            else:
                                # Default to INFO for other output
                                self.log_message.emit("INFO", line)

                # Log stderr if there are errors
                if result.stderr:
                    for line in result.stderr.strip().split("\n"):
                        if line.strip():
                            self.log_message.emit("ERROR", f"[generate_card.py] {line}")

                if result.returncode == 0:
                    # Try to locate generated files in deck-specific directories
                    safe_name = make_safe_filename(card.name)

                    # List all files in output directory for debugging
                    if self.cards_dir.exists():
                        all_files = list(self.cards_dir.glob("*.png"))
                        self.log_message.emit(
                            "DEBUG",
                            f"Files in cards directory: {[f.name for f in all_files]}",
                        )

                    # Find actual generated files
                    default_card_path = None
                    default_art_path = None

                    # Use deck-specific directories
                    cards_dir = self.cards_dir
                    images_dir = self.images_dir

                    # Check cards directory for files matching the pattern
                    if cards_dir.exists():
                        pattern = f"{safe_name}_*.png"
                        matching_files = list(cards_dir.glob(pattern))
                        if matching_files:
                            # Get the most recent file
                            matching_files.sort(
                                key=lambda p: p.stat().st_mtime, reverse=True
                            )
                            default_card_path = matching_files[0]
                            self.log_message.emit(
                                "INFO", f"Found card image at: {default_card_path}"
                            )

                    # If not found in cards, check images directory
                    if not default_card_path and images_dir.exists():
                        pattern = f"{safe_name}_*.png"
                        matching_files = list(images_dir.glob(pattern))
                        if matching_files:
                            matching_files.sort(
                                key=lambda p: p.stat().st_mtime, reverse=True
                            )
                            default_card_path = matching_files[0]
                            self.log_message.emit(
                                "INFO", f"Found card image at: {default_card_path}"
                            )

                    # Also try exact name without timestamp as fallback
                    if not default_card_path:
                        primary_path = cards_dir / f"{safe_name}.png"
                        if primary_path.exists():
                            default_card_path = primary_path
                            self.log_message.emit(
                                "INFO", f"Found card image at: {primary_path}"
                            )

                    # If still not found, try to find any recent PNG files
                    if not default_card_path and cards_dir.exists():
                        recent_files = sorted(
                            cards_dir.glob("*.png"),
                            key=lambda p: p.stat().st_mtime,
                            reverse=True,
                        )
                        if recent_files:
                            # Take the most recent file that doesn't have _art in the name
                            for f in recent_files:
                                if "_art" not in f.name and "artwork" not in f.name:
                                    default_card_path = f
                                    self.log_message.emit(
                                        "INFO", f"Using most recent card file: {f}"
                                    )
                                    break

                    # Check for art/image files in output/images/
                    if images_dir.exists():
                        # Look for artwork with various naming patterns
                        art_patterns = [
                            f"{safe_name}.jpg",
                            f"{safe_name}.jpeg",
                            f"{safe_name}.png",
                            f"{card.name.split(',')[0].strip()}.jpg",  # Try simple name (e.g., "Mountain" for "Mountain, Basic")
                            f"{card.name.split(',')[0].strip()}.jpeg",
                            f"{card.name.split(',')[0].strip()}.png",
                        ]

                        for pattern in art_patterns:
                            art_path = images_dir / pattern
                            if art_path.exists():
                                default_art_path = art_path
                                self.log_message.emit(
                                    "INFO", f"Found artwork at: {art_path}"
                                )
                                break

                    # Check for art files
                    if default_card_path and not default_art_path:
                        # Try to find corresponding art file
                        base_name = default_card_path.stem
                        possible_art_names = [
                            f"{base_name}_art",
                            f"{base_name}_artwork",
                            f"{base_name}-art",
                            base_name.replace("_card", "_art"),
                        ]

                        for art_name in possible_art_names:
                            art_path = default_card_path.parent / f"{art_name}.png"
                            if art_path.exists():
                                default_art_path = art_path
                                self.log_message.emit(
                                    "INFO", f"Found art image at: {art_path}"
                                )
                                break

                    # Rename the generated file to remove timestamp
                    card_path = ""
                    image_path = ""

                    if default_card_path and default_card_path.exists():
                        # Target path without timestamp
                        final_path = self.cards_dir / f"{safe_name}.png"

                        try:
                            # Validate the generated card before saving
                            import numpy as np
                            from PIL import Image

                            # Open and check the image
                            with Image.open(default_card_path) as img:
                                # Convert to RGB if needed
                                if img.mode != "RGB":
                                    img = img.convert("RGB")

                                # Check if image is mostly black (potential rendering error)
                                img_array = np.array(img)
                                # Calculate average brightness (0-255)
                                avg_brightness = img_array.mean()

                                # Check different regions of the card for black sections
                                height, width = img_array.shape[:2]

                                # Sample regions
                                regions = {
                                    "top (title/cost)": img_array[: height // 4],
                                    "upper-middle (artwork)": img_array[
                                        height // 4 : height // 2
                                    ],
                                    "lower-middle (type/text)": img_array[
                                        height // 2 : 3 * height // 4
                                    ],
                                    "bottom (P/T)": img_array[3 * height // 4 :],
                                }

                                # Check each region
                                black_regions = []
                                for region_name, region_data in regions.items():
                                    region_brightness = region_data.mean()
                                    self.log_message.emit(
                                        "DEBUG",
                                        f"Region '{region_name}' brightness: {region_brightness:.1f}/255",
                                    )
                                    if region_brightness < 30:
                                        black_regions.append(region_name)

                                # If image is too dark, it's likely a rendering error
                                if avg_brightness < 30:
                                    self.log_message.emit(
                                        "ERROR",
                                        f"Card appears corrupted (brightness: {avg_brightness:.1f}/255)",
                                    )
                                    self.log_message.emit(
                                        "ERROR",
                                        f"Black regions: {', '.join(black_regions) if black_regions else 'entire card'}",
                                    )

                                    # Log card data for debugging
                                    self.log_message.emit("ERROR", "Card data debug:")
                                    self.log_message.emit(
                                        "ERROR", f"  Name: {card.name}"
                                    )
                                    self.log_message.emit(
                                        "ERROR", f"  Cost: {card.cost}"
                                    )
                                    self.log_message.emit(
                                        "ERROR", f"  Type: {card.type}"
                                    )
                                    self.log_message.emit(
                                        "ERROR", f"  P/T: {card.power}/{card.toughness}"
                                    )
                                    self.log_message.emit(
                                        "ERROR", f"  Rarity: {card.rarity}"
                                    )

                                    # Check if it's a creature without P/T
                                    if card.is_creature() and (
                                        not card.power or not card.toughness
                                    ):
                                        self.log_message.emit(
                                            "ERROR", "⚠️ Creature missing P/T values!"
                                        )

                                    raise Exception(
                                        f"Card corrupted (black in: {', '.join(black_regions)})"
                                    )
                                elif black_regions:
                                    self.log_message.emit(
                                        "WARNING",
                                        f"Card has black regions in: {', '.join(black_regions)}",
                                    )
                                    self.log_message.emit(
                                        "WARNING",
                                        f"May indicate missing data for: {card.name}",
                                    )

                            # Move/rename the file to remove timestamp
                            import shutil

                            if final_path.exists():
                                final_path.unlink()  # Remove old file if exists
                            shutil.move(str(default_card_path), str(final_path))
                            card_path = str(final_path)
                            self.log_message.emit(
                                "INFO", f"Card saved: {final_path.name}"
                            )

                            # Clean up JSON file if it exists
                            json_path = default_card_path.with_suffix(".json")
                            if json_path.exists():
                                try:
                                    json_path.unlink()
                                    self.log_message.emit(
                                        "DEBUG", f"Cleaned up JSON: {json_path.name}"
                                    )
                                except:
                                    pass
                        except Exception as e:
                            # If move fails, use the original path
                            card_path = str(default_card_path)
                            self.log_message.emit(
                                "WARNING", f"Could not rename file: {e}"
                            )
                    else:
                        self.log_message.emit(
                            "WARNING", f"No card image found for {card.name}"
                        )

                    # Log the successful generation with file paths
                    # Debug: log what we're emitting
                    self.log_message.emit(
                        "DEBUG",
                        f"Emitting completed signal for card {card.name} with ID: {card.id}",
                    )
                    self.completed.emit(
                        card.id,
                        True,
                        "Card generated successfully",
                        image_path,
                        card_path,
                    )
                else:
                    # Command failed - log detailed error information
                    error_msg = (
                        result.stderr
                        if result.stderr
                        else "Command failed with no error message"
                    )

                    self.log_message.emit(
                        "ERROR", f"Card generation failed for: {card.name}"
                    )
                    self.log_message.emit("ERROR", f"Exit code: {result.returncode}")

                    # Log any stdout that might contain error info
                    if result.stdout:
                        for line in result.stdout.strip().split("\n"):
                            if line.strip():
                                self.log_message.emit("ERROR", f"[stdout] {line}")

                    # Log stderr
                    if result.stderr:
                        for line in result.stderr.strip().split("\n"):
                            if line.strip():
                                self.log_message.emit("ERROR", f"[stderr] {line}")

                    self.completed.emit(card.id, False, error_msg, "", "")
                    # Stop on error
                    break

            except Exception as e:
                self.log_message.emit(
                    "ERROR", f"Exception during card generation: {str(e)}"
                )
                self.completed.emit(card.id, False, str(e), "", "")
                break


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
        self.analyze_button = QPushButton("🔮 Analyze Theme")
        self.generate_button = QPushButton("📋 Generate Full Deck")
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
        """Generate full deck of 100 cards"""
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
            self.output_text.append(f"\n✅ Generated {len(cards)} cards")

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
        self.cards = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Toolbar
        toolbar = QHBoxLayout()
        self.load_button = QPushButton("📂 Load Deck")
        self.regenerate_button = QPushButton("🔄 Regenerate All")
        self.export_button = QPushButton("📤 Export")

        # Auto-save indicator
        self.auto_save_label = QLabel("💾 Auto-Save: Active")
        self.auto_save_label.setStyleSheet(
            "color: #4ec9b0; font-weight: bold; padding: 5px;"
        )

        self.load_button.clicked.connect(self.load_deck)
        self.regenerate_button.clicked.connect(self.regenerate_all)
        self.export_button.clicked.connect(self.export_deck)

        toolbar.addWidget(self.load_button)
        toolbar.addWidget(self.auto_save_label)
        toolbar.addWidget(self.regenerate_button)
        toolbar.addWidget(self.export_button)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Filter and search
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
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
        self.filter_combo.currentTextChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.filter_combo)

        filter_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.textChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.search_input)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(9)  # Removed Actions column
        self.table.setHorizontalHeaderLabels(
            ["#", "Name", "Cost", "Type", "P/T", "Text", "Rarity", "Art", "Status"]
        )

        # Set column widths
        header = self.table.horizontalHeader()
        header.resizeSection(0, 40)  # #
        header.resizeSection(1, 200)  # Name (increased width)
        header.resizeSection(2, 70)  # Cost
        header.resizeSection(3, 150)  # Type
        header.resizeSection(4, 60)  # P/T
        header.resizeSection(5, 250)  # Text (increased width)
        header.resizeSection(6, 80)  # Rarity
        header.resizeSection(7, 200)  # Art (increased width)
        header.resizeSection(8, 100)  # Status (increased width)

        # Disable sorting - it's broken
        self.table.setSortingEnabled(False)
        # Sorting disabled - it's broken
        # header.sectionClicked.connect(self.sort_by_column)

        # Track sorting state for each column
        # Sorting disabled
        # self.sort_order = {}  # Column index -> Qt.SortOrder

        # Connect itemChanged signal to auto-save when cells are edited
        self.table.itemChanged.connect(self.on_table_item_changed)

        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        # Add context menu for right-click
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        layout.addWidget(self.table)

        # Stats and Color Distribution - using vertical layout for better space management
        stats_container = QVBoxLayout()

        # Stats label with word wrap
        self.stats_label = QLabel("Cards: 0 | Lands: 0 | Creatures: 0 | Spells: 0")
        self.stats_label.setWordWrap(True)
        self.stats_label.setStyleSheet("padding: 3px;")

        # Color label with word wrap
        self.color_label = QLabel("🎨 Colors: -")
        self.color_label.setWordWrap(True)
        self.color_label.setStyleSheet(
            "font-weight: bold; color: #ce9178; padding: 3px;"
        )

        stats_container.addWidget(self.stats_label)
        stats_container.addWidget(self.color_label)
        layout.addLayout(stats_container)

        # Edit buttons with Add/Delete functionality
        edit_layout = QHBoxLayout()
        self.add_card_button = QPushButton("➕ Add Card")
        self.delete_card_button = QPushButton("🗑️ Delete Card")
        self.edit_button = QPushButton("✏️ Edit Card")
        self.edit_art_button = QPushButton("🎨 Edit Art")
        self.generate_missing_button = QPushButton("Generate Missing Values")
        self.generate_art_button = QPushButton("Generate Art Descriptions")

        self.add_card_button.clicked.connect(self.add_new_card)
        self.delete_card_button.clicked.connect(self.delete_selected_cards)
        self.edit_button.clicked.connect(self.edit_card)
        self.edit_art_button.clicked.connect(self.edit_selected_art_prompt)
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
        edit_layout.addWidget(self.edit_art_button)
        edit_layout.addWidget(self.generate_missing_button)
        edit_layout.addWidget(self.generate_art_button)
        edit_layout.addStretch()
        layout.addLayout(edit_layout)

        self.setLayout(layout)

        # Store commander colors for validation
        self.commander_colors = set()

    # Sorting method removed - was broken
    # def sort_by_column(self, column: int):
    #     pass

    def on_table_item_changed(self, item):
        """Handle table item changes and auto-save deck"""
        row = item.row()
        column = item.column()

        if row >= len(self.cards):
            return

        card = self.cards[row]
        new_value = item.text()

        # Update the card based on which column was edited
        # Columns: ID, Name, Cost, Type, Text, P/T, Rarity, Art, Status
        if column == 0:  # ID
            try:
                card.id = int(new_value)
            except ValueError:
                pass
        elif column == 1:  # Name
            card.name = new_value
        elif column == 2:  # Cost
            card.cost = new_value
        elif column == 3:  # Type
            card.type = new_value
        elif column == 4:  # Text
            card.text = new_value
        elif column == 5:  # P/T
            # Parse P/T like "2/3" or "*/4"
            if "/" in new_value:
                parts = new_value.split("/")
                if len(parts) == 2:
                    card.power = parts[0].strip()
                    card.toughness = parts[1].strip()
        elif column == 6:  # Rarity
            card.rarity = new_value.lower()
        elif column == 7:  # Art
            card.art = new_value
        elif column == 8:  # Status
            card.status = new_value.lower()

        # Auto-save the deck
        main_window = self.parent().parent() if hasattr(self, "parent") else None
        if main_window and hasattr(main_window, "auto_save_deck"):
            main_window.auto_save_deck(self.cards)
            if main_window and hasattr(main_window, "log_message"):
                main_window.log_message(
                    "DEBUG", f"Auto-saved deck after editing {card.name} ({column=})"
                )

    def get_commander_colors(self) -> set:
        """Get the color identity of the commander (first card or legendary creature)"""
        commander_colors = set()

        # Get main window for logging
        main_window = self.parent().parent() if hasattr(self, "parent") else None

        for card in self.cards:
            # Commander is usually the first card or a legendary creature
            if card.id == 1 or ("Legendary" in card.type and "Creature" in card.type):
                if main_window and hasattr(main_window, "log_message"):
                    main_window.log_message(
                        "DEBUG",
                        f"Found potential commander: {card.name} (ID: {card.id}, Cost: {card.cost})",
                    )

                if card.cost and card.cost != "-":
                    # Convert to string first to handle integer costs
                    cost = str(card.cost).upper()
                    # Extract colors from mana cost
                    for color in ["W", "U", "B", "R", "G"]:
                        if color in cost:
                            commander_colors.add(color)

                    # Also check card text for color indicators
                    if card.text:
                        text = card.text.upper()
                        # Check for hybrid mana symbols
                        for hybrid in [
                            "{W/U}",
                            "{U/B}",
                            "{B/R}",
                            "{R/G}",
                            "{G/W}",
                            "{W/B}",
                            "{U/R}",
                            "{B/G}",
                            "{R/W}",
                            "{G/U}",
                        ]:
                            if hybrid in text:
                                for color in ["W", "U", "B", "R", "G"]:
                                    if color in hybrid:
                                        commander_colors.add(color)

                # If this is card ID 1, it's definitely the commander
                if card.id == 1:
                    if main_window and hasattr(main_window, "log_message"):
                        main_window.log_message(
                            "INFO",
                            f"Commander identified: {card.name} with colors: {commander_colors}",
                        )
                    break

        return commander_colors

    def check_color_violation(self, card_cost: str) -> bool:
        """Check if a card's mana cost violates commander color identity"""
        # Handle different types of cost input
        if card_cost is None:
            return False

        # Convert to string if it's not already
        cost_str = str(card_cost) if not isinstance(card_cost, str) else card_cost

        if not cost_str or cost_str == "-" or cost_str == "":
            return False  # Colorless cards are always legal

        if not self.commander_colors:
            return False  # No commander colors set yet

        card_colors = set()
        # Clean up the cost string (remove curly braces) - ensure it's a string first
        if hasattr(cost_str, "upper"):
            cost = cost_str.upper().replace("{", "").replace("}", "")
        else:
            # If for some reason upper() doesn't exist, convert to string first
            cost = str(cost_str).upper().replace("{", "").replace("}", "")

        # Extract colors from the card's mana cost
        for color in ["W", "U", "B", "R", "G"]:
            if color in cost:
                card_colors.add(color)

        # Check if any card color is not in commander colors
        violation = bool(card_colors - self.commander_colors)

        # Debug log for problematic cards
        if violation and card_colors:
            main_window = self.parent().parent() if hasattr(self, "parent") else None
            if main_window and hasattr(main_window, "log_message"):
                main_window.log_message(
                    "DEBUG",
                    f"Color violation: Card has {card_colors}, Commander allows {self.commander_colors}",
                )

        return violation

    def load_cards(self, cards: list[MTGCard]):
        """Load cards into table"""
        self.cards = cards
        self.commander_colors = self.get_commander_colors()

        # Log all cards with color violations
        self.log_color_violations()

        self.refresh_table()
        self.update_stats()

    def log_color_violations(self):
        """Log all cards that violate commander color identity"""
        main_window = self.parent().parent() if hasattr(self, "parent") else None
        if not main_window or not hasattr(main_window, "log_message"):
            return

        violations = []
        for card in self.cards:
            if self.check_color_violation(card.cost):
                # Get the card's colors
                card_colors = set()
                cost_str = str(card.cost) if card.cost else ""
                # Ensure it's a string before calling upper()
                cost = str(cost_str).upper().replace("{", "").replace("}", "")
                for color in ["W", "U", "B", "R", "G"]:
                    if color in str(cost):  # Ensure cost is string
                        card_colors.add(color)

                violations.append(
                    f"{card.name} (Cost: {card.cost}, Colors: {card_colors})"
                )

        if violations:
            main_window.log_message(
                "WARNING", f"Found {len(violations)} cards with color violations:"
            )
            for violation in violations:
                main_window.log_message("WARNING", f"  ⚠️ {violation}")
            main_window.log_message(
                "INFO", f"Commander colors allowed: {self.commander_colors}"
            )

    def refresh_table(self):
        """Refresh table display with color validation"""
        # Temporarily disconnect itemChanged signal to avoid triggering saves during refresh
        try:
            self.table.itemChanged.disconnect()
        except:
            pass

        self.table.setRowCount(len(self.cards))

        # Get commander colors first
        self.commander_colors = self.get_commander_colors()

        # Sorting is already disabled
        # self.table.setSortingEnabled(False)

        for row, card in enumerate(self.cards):
            # Check if this card violates commander color identity
            violates_colors = self.check_color_violation(card.cost)

            # ID column - use numeric sorting
            id_item = QTableWidgetItem()
            id_item.setData(Qt.ItemDataRole.DisplayRole, str(card.id))
            id_item.setData(
                Qt.ItemDataRole.UserRole, int(card.id)
            )  # Store numeric value for sorting
            if violates_colors:
                id_item.setBackground(QBrush(QColor(255, 200, 200)))  # Light red
            self.table.setItem(row, 0, id_item)

            # Name column
            name_item = QTableWidgetItem(card.name)
            if violates_colors:
                name_item.setBackground(QBrush(QColor(255, 200, 200)))  # Light red
            self.table.setItem(row, 1, name_item)

            # Cost column - highlight in stronger red since this is the violation source
            cost_item = QTableWidgetItem(card.cost)
            if violates_colors:
                cost_item.setBackground(QBrush(QColor(255, 150, 150)))  # Stronger red
                cost_item.setToolTip(
                    f"⚠️ Color violation! Contains colors not in commander identity: {self.commander_colors}"
                )
            self.table.setItem(row, 2, cost_item)

            # Type column
            type_item = QTableWidgetItem(card.type)
            if violates_colors:
                type_item.setBackground(QBrush(QColor(255, 200, 200)))  # Light red
            self.table.setItem(row, 3, type_item)

            # P/T column
            pt = f"{card.power}/{card.toughness}" if card.power is not None else "-"
            pt_item = QTableWidgetItem(pt)
            if violates_colors:
                pt_item.setBackground(QBrush(QColor(255, 200, 200)))  # Light red
            self.table.setItem(row, 4, pt_item)

            # Text column
            text_item = QTableWidgetItem(
                card.text[:50] + "..." if len(card.text) > 50 else card.text
            )
            if violates_colors:
                text_item.setBackground(QBrush(QColor(255, 200, 200)))  # Light red
            self.table.setItem(row, 5, text_item)

            # Rarity column
            rarity_item = QTableWidgetItem(card.rarity)
            if violates_colors:
                rarity_item.setBackground(QBrush(QColor(255, 200, 200)))  # Light red
            self.table.setItem(row, 6, rarity_item)

            # Art column
            art_item = QTableWidgetItem(
                card.art[:50] + "..." if len(card.art) > 50 else card.art
            )
            if violates_colors:
                art_item.setBackground(QBrush(QColor(255, 200, 200)))  # Light red
            self.table.setItem(row, 7, art_item)

            # Status column - keep original coloring but overlay if violates
            status_item = QTableWidgetItem(card.status)
            if card.status == "completed":
                if violates_colors:
                    status_item.setBackground(
                        QBrush(QColor(200, 150, 150))
                    )  # Red-tinted green
                else:
                    status_item.setBackground(QBrush(QColor(100, 200, 100)))  # Green
            elif card.status == "generating":
                if violates_colors:
                    status_item.setBackground(
                        QBrush(QColor(255, 150, 100))
                    )  # Red-tinted yellow
                else:
                    status_item.setBackground(QBrush(QColor(200, 200, 100)))  # Yellow
            elif card.status == "failed":
                status_item.setBackground(QBrush(QColor(200, 100, 100)))  # Red (same)
            elif violates_colors:
                status_item.setBackground(QBrush(QColor(255, 200, 200)))  # Light red
            self.table.setItem(row, 8, status_item)

        # Keep sorting disabled
        self.table.setSortingEnabled(False)

        # Reconnect itemChanged signal for auto-save
        self.table.itemChanged.connect(self.on_table_item_changed)

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
        color_symbols = {"W": "⚪", "U": "🔵", "B": "⚫", "R": "🔴", "G": "🟢", "C": "⬜"}
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
            warning_text = f" ⚠️ VIOLATION: {' '.join(violation_symbols)} not in commander identity!"

        # Format stats text on two lines for better readability
        stats_text = (
            f"📊 Total: {total} | Lands: {lands} | Creatures: {creatures}\n"
            f"   Instants: {instants} | Sorceries: {sorceries} | "
            f"Artifacts: {artifacts} | Enchantments: {enchantments}"
        )

        self.stats_label.setText(stats_text)

        # Update color label with commander info and warnings - split for readability
        color_label_text = f"🎨 Deck Colors: {deck_color_text}\n"
        color_label_text += (
            f"👑 Commander ({commander_name[:30]}): {commander_color_text}"
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

    def apply_filter(self):
        """Apply filter to table"""
        filter_text = self.filter_combo.currentText()
        search_text = self.search_input.text().lower()

        for row in range(self.table.rowCount()):
            show = True

            # Type filter
            if filter_text != "All":
                card_type = self.table.item(row, 3).text()
                if filter_text == "Creatures" and "Creature" not in card_type:
                    show = False
                elif filter_text == "Lands" and "Land" not in card_type:
                    show = False
                elif filter_text == "Instants" and "Instant" not in card_type:
                    show = False
                elif filter_text == "Sorceries" and "Sorcery" not in card_type:
                    show = False
                elif filter_text == "Artifacts" and "Artifact" not in card_type:
                    show = False
                elif filter_text == "Enchantments" and "Enchantment" not in card_type:
                    show = False

            # Search filter
            if show and search_text:
                name = self.table.item(row, 1).text().lower()
                if search_text not in name:
                    show = False

            self.table.setRowHidden(row, not show)

    def add_new_card(self):
        """Add a new blank card to the deck"""
        # Find the next available ID (highest existing ID + 1)
        max_id = 0
        for card in self.cards:
            try:
                card_id = int(card.id) if isinstance(card.id, (str, int)) else 0
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
        self.refresh_table()

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

    def show_context_menu(self, position):
        """Show context menu on right-click"""
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
        edit_art_action = menu.addAction("🎨 Edit Art Description")
        regenerate_action = menu.addAction("🔄 Regenerate Card")

        # Style delete action in red
        delete_action.setStyleSheet("color: #ff6666;")

        # Execute menu
        action = menu.exec(self.table.mapToGlobal(position))

        # Handle actions
        if action == add_action:
            self.add_new_card()
        elif action == edit_action:
            self.edit_card()
        elif action == duplicate_action:
            self.duplicate_selected_card()
        elif action == delete_action:
            self.delete_selected_cards()
        elif action == edit_art_action:
            self.edit_selected_art_prompt()
        elif action == regenerate_action:
            self.regenerate_selected_card()

    def duplicate_selected_card(self):
        """Duplicate the selected card"""

        current_row = self.table.currentRow()
        if current_row < 0:
            return

        # Find the next available ID
        max_id = 0
        for card in self.cards:
            try:
                card_id = int(card.id) if isinstance(card.id, (str, int)) else 0
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
        self.refresh_table()
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
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

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
            self.refresh_table()

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
        dialog = CardEditDialog(card, self)
        if dialog.exec():
            self.refresh_table()
            self.cards_updated.emit(self.cards)

    # Preview is now handled by permanent panel on the right side

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
            return

        # Get parent window for logging
        parent = self.parent().parent() if hasattr(self, "parent") else None

        # Create worker for art generation
        self.art_worker = AIWorker()
        self.art_worker.result_ready.connect(self.on_art_descriptions_ready)
        self.art_worker.error_occurred.connect(self.on_art_generation_error)

        # Log start
        if parent and hasattr(parent, "log_message"):
            parent.log_message(
                "GENERATING",
                f"Generating art descriptions for {len(cards_needing_art)} cards...",
            )

        # Get theme
        theme = (
            parent.theme_tab.get_theme()
            if parent and hasattr(parent, "theme_tab")
            else "Fantasy"
        )

        # Create prompt for art descriptions
        card_list = "\n".join(
            [
                f"{i+1}. {card.name} ({card.type})"
                for i, card in enumerate(cards_needing_art)
            ]
        )

        prompt = f"""Theme: {theme}

Generate detailed art descriptions for these MTG cards.
IMPORTANT: For characters from {theme}, use their EXACT canonical appearance.

For each card, provide a vivid 2-3 sentence visual description.
Format: [NUMBER]. [ART DESCRIPTION]

Cards:
{card_list}"""

        self.art_worker.set_task("generate_art", prompt)
        self.art_worker.start()

        # Store cards for later processing
        self.cards_awaiting_art = cards_needing_art

        # Disable button during generation
        self.generate_art_button.setEnabled(False)
        self.generate_art_button.setText("Generating...")

    def on_art_descriptions_ready(self, result: str):
        """Handle art descriptions response"""
        parent = self.parent().parent() if hasattr(self, "parent") else None

        # Parse art descriptions
        lines = result.split("\n")
        art_descriptions = {}

        for line in lines:
            line = line.strip()
            if line and line[0].isdigit() and ". " in line:
                parts = line.split(". ", 1)
                if len(parts) == 2:
                    try:
                        idx = int(parts[0]) - 1
                        if 0 <= idx < len(self.cards_awaiting_art):
                            art_descriptions[idx] = parts[1].strip()
                    except:
                        pass

        # Update cards with art descriptions
        updated_count = 0
        for i, card in enumerate(self.cards_awaiting_art):
            if i in art_descriptions:
                card.art = art_descriptions[i]
                updated_count += 1

        # Refresh table
        self.load_cards(self.cards)

        # Log success
        if parent and hasattr(parent, "log_message"):
            parent.log_message(
                "SUCCESS", f"Generated art descriptions for {updated_count} cards"
            )

        # Re-enable button
        self.generate_art_button.setEnabled(True)
        self.generate_art_button.setText("Generate Art Descriptions")

        # Emit update signal
        self.cards_updated.emit(self.cards)

    def on_art_generation_error(self, error: str):
        """Handle art generation error"""
        parent = self.parent().parent() if hasattr(self, "parent") else None
        if parent and hasattr(parent, "log_message"):
            parent.log_message("ERROR", f"Art generation failed: {error}")

        QMessageBox.critical(
            self, "Error", f"Failed to generate art descriptions: {error}"
        )

        # Re-enable button
        self.generate_art_button.setEnabled(True)
        self.generate_art_button.setText("Generate Art Descriptions")

    def delete_card(self, row: int):
        """Delete generated files for a card (not the card itself from the deck)"""
        if 0 <= row < len(self.cards):
            card = self.cards[row]
            reply = QMessageBox.question(
                self,
                "Delete Generated Files",
                f"Delete generated files for '{card.name}'?\n\nThis will remove the card image and allow regeneration.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                import os
                from pathlib import Path

                deleted_files = []

                # Delete card image file if it exists
                if card.card_path and Path(card.card_path).exists():
                    try:
                        os.remove(card.card_path)
                        deleted_files.append(Path(card.card_path).name)
                        card.card_path = None
                    except Exception as e:
                        print(f"Error deleting card file: {e}")

                # Delete artwork file if it exists
                if card.image_path and Path(card.image_path).exists():
                    try:
                        os.remove(card.image_path)
                        deleted_files.append(Path(card.image_path).name)
                        card.image_path = None
                    except Exception as e:
                        print(f"Error deleting image file: {e}")

                # Try to find and delete files by pattern in output directory
                safe_name = make_safe_filename(card.name)
                output_dir = Path("output/cards")
                image_dir = Path("output/images")

                # Delete card PNG files
                for file in output_dir.glob(f"{safe_name}_*.png"):
                    try:
                        os.remove(file)
                        deleted_files.append(file.name)
                    except Exception as e:
                        print(f"Error deleting {file}: {e}")

                # Delete card JSON files
                for file in output_dir.glob(f"{safe_name}_*.json"):
                    try:
                        os.remove(file)
                        deleted_files.append(file.name)
                    except Exception as e:
                        print(f"Error deleting {file}: {e}")

                # Delete artwork JPG files
                for file in image_dir.glob(f"{safe_name}*.jpg"):
                    try:
                        os.remove(file)
                        deleted_files.append(file.name)
                    except Exception as e:
                        print(f"Error deleting {file}: {e}")

                # Reset card status to pending
                card.status = "pending"
                card.generated_at = None

                # Refresh table
                self.refresh_table()
                self.cards_updated.emit(self.cards)

                # Log
                parent = self.parent().parent() if hasattr(self, "parent") else None
                if parent and hasattr(parent, "log_message"):
                    if deleted_files:
                        parent.log_message(
                            "INFO",
                            f"Deleted files for '{card.name}': {', '.join(deleted_files)}",
                        )
                    else:
                        parent.log_message(
                            "WARNING", f"No files found to delete for '{card.name}'"
                        )
                    parent.log_message(
                        "INFO", f"Card '{card.name}' ready for regeneration"
                    )

    def regenerate_single_card(self, row: int):
        """Regenerate a single card"""
        if 0 <= row < len(self.cards):
            card = self.cards[row]

            # Ask if user wants to edit the card first
            reply = QMessageBox.question(
                self,
                "Regenerate Card",
                f"Regenerate '{card.name}'?\n\nChoose Yes to regenerate with current settings,\nNo to edit first.",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel,
            )

            if reply == QMessageBox.StandardButton.Cancel:
                return
            elif reply == QMessageBox.StandardButton.No:
                # Open edit dialog
                self.edit_card_at_row(row)
                return

            # Mark as generating
            card.status = "generating"
            self.refresh_table()

            # Emit signal to regenerate
            self.regenerate_card.emit(card)

            parent = self.parent().parent() if hasattr(self, "parent") else None
            if parent and hasattr(parent, "log_message"):
                parent.log_message("INFO", f"Regenerating card: {card.name}")

    def edit_art_prompt(self, row: int):
        """Edit the art prompt for a card"""
        if 0 <= row < len(self.cards):
            card = self.cards[row]

            # Create dialog for art prompt editing
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Edit Art Prompt - {card.name}")
            dialog.setModal(True)
            dialog.resize(500, 200)

            layout = QVBoxLayout()

            # Current art prompt
            label = QLabel(f"Edit art description for '{card.name}':")
            layout.addWidget(label)

            # Text edit
            text_edit = QTextEdit()
            text_edit.setPlainText(card.art or f"Fantasy art of {card.name}")
            layout.addWidget(text_edit)

            # Buttons
            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok
                | QDialogButtonBox.StandardButton.Cancel
            )
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)

            dialog.setLayout(layout)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_art = text_edit.toPlainText().strip()
                if new_art and new_art != card.art:
                    card.art = new_art
                    self.refresh_table()
                    self.cards_updated.emit(self.cards)

                    # Ask if user wants to regenerate the card image now
                    reply = QMessageBox.question(
                        self,
                        "Regenerate Image",
                        "Art prompt updated. Regenerate the card image now?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    )

                    if reply == QMessageBox.StandardButton.Yes:
                        card.status = "generating"
                        self.refresh_table()
                        self.regenerate_card.emit(card)

    def delete_selected_card_files(self):
        """Delete files for the selected card"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a card first!")
            return
        self.delete_card(current_row)

    def regenerate_selected_card(self):
        """Regenerate the selected card"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a card to regenerate!")
            return
        self.regenerate_single_card(current_row)

    def edit_selected_art_prompt(self):
        """Edit art prompt for the selected card"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a card to edit art!")
            return
        self.edit_art_prompt(current_row)

    def edit_card_at_row(self, row: int):
        """Edit a card at specific row"""
        if 0 <= row < len(self.cards):
            # Set current row
            self.table.selectRow(row)
            # Call existing edit_card method
            self.edit_card()

    def regenerate_all(self):
        """Regenerate all cards"""
        reply = QMessageBox.question(self, "Confirm", "Regenerate all 100 cards?")
        if reply == QMessageBox.StandardButton.Yes:
            # TODO: Trigger regeneration
            pass

    def save_deck(self):
        """Save deck to YAML file"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Deck", "", "YAML Files (*.yaml);;JSON Files (*.json)"
        )

        if filename:
            deck_data = {
                "theme": "Custom Deck",
                "cards": [asdict(card) for card in self.cards],
            }

            if filename.endswith(".yaml"):
                with open(filename, "w") as f:
                    yaml.dump(deck_data, f)
            else:
                with open(filename, "w") as f:
                    json.dump(deck_data, f, indent=2)

            QMessageBox.information(self, "Success", "Deck saved successfully!")

    def load_deck(self):
        """Load deck from file dialog"""
        # Get main window directly
        parent = get_main_window()

        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Deck", "saved_decks", "YAML Files (*.yaml);;JSON Files (*.json)"
        )

        if filename:
            self.load_deck_file(filename)

    def load_deck_file(self, filename: str):
        """Load a specific deck file"""
        # Get main window directly
        parent = get_main_window()

        if filename and Path(filename).exists():
            # Set the current deck name FIRST, before any loading
            deck_path = Path(filename)

            if parent:
                # Save the deck path for auto-loading on next start
                if hasattr(parent, "last_loaded_deck_path"):
                    parent.last_loaded_deck_path = filename
                else:
                    parent.last_loaded_deck_path = filename

                # Log the file being loaded
                if hasattr(parent, "log_message"):
                    # Show relative path from saved_decks if applicable
                    if "saved_decks" in str(deck_path):
                        parts = deck_path.parts
                        idx = parts.index("saved_decks")
                        relative_path = "/".join(parts[idx:])
                        parent.log_message(
                            "INFO", f"Loading deck from: {relative_path}"
                        )
                    else:
                        parent.log_message("INFO", f"Loading deck from: {filename}")

                # Set current deck name based on file location
                if hasattr(parent, "current_deck_name"):
                    # If file is in a deck subfolder, use that as deck name
                    if (
                        deck_path.parent.name.startswith("deck_")
                        and deck_path.parent.parent.name == "saved_decks"
                    ):
                        parent.current_deck_name = deck_path.parent.name
                        if hasattr(parent, "log_message"):
                            parent.log_message(
                                "INFO",
                                f"Active deck set to: {parent.current_deck_name}",
                            )
                    else:
                        # Otherwise derive from filename
                        parent.current_deck_name = deck_path.stem
                        if hasattr(parent, "log_message"):
                            parent.log_message(
                                "INFO",
                                f"Active deck set to: {parent.current_deck_name} (from filename)",
                            )

                    # Update the deck selector dropdown
                    if hasattr(parent, "update_deck_list"):
                        parent.update_deck_list()

            try:
                if filename.endswith(".yaml"):
                    with open(filename) as f:
                        data = yaml.safe_load(f)
                        if parent and hasattr(parent, "log_message"):
                            parent.log_message("DEBUG", "File format: YAML")
                else:
                    with open(filename) as f:
                        data = json.load(f)
                        if parent and hasattr(parent, "log_message"):
                            parent.log_message("DEBUG", "File format: JSON")

                # Log deck info
                if parent and hasattr(parent, "log_message"):
                    parent.log_message("INFO", f"Theme: {data.get('theme', 'Unknown')}")
                    parent.log_message(
                        "INFO", f"Cards in file: {len(data.get('cards', []))}"
                    )

                # Load cards - ALWAYS use sequential IDs to avoid duplicates
                self.cards = []
                failed_cards = 0

                for i, card_data in enumerate(data.get("cards", [])):
                    try:
                        # ALWAYS use sequential numbering (i + 1) to ensure no duplicates
                        card_data["id"] = i + 1

                        card = MTGCard(**card_data)
                        self.cards.append(card)
                    except Exception as e:
                        failed_cards += 1
                        if parent and hasattr(parent, "log_message"):
                            parent.log_message(
                                "WARNING", f"Card {i+1} failed to load: {str(e)[:50]}"
                            )

                # Auto-save with correct deck name (deck name was set before loading)
                if parent:
                    if hasattr(parent, "log_message"):
                        parent.log_message(
                            "INFO", "Applied sequential numbering to all cards"
                        )
                    if hasattr(parent, "auto_save_deck"):
                        # Pass False to not create new timestamp file
                        parent.auto_save_deck(self.cards, new_generation=False)

                # Refresh UI
                self.refresh_table()
                self.update_stats()

                # Update Generation Tab (Tab 3)
                if parent:
                    if hasattr(parent, "generation_tab"):
                        parent.generation_tab.load_cards(self.cards)
                        if hasattr(parent, "log_message"):
                            parent.log_message(
                                "SUCCESS",
                                f"Updated Generation Tab with {len(self.cards)} cards",
                            )

                    # Emit signal for other tabs
                    self.cards_updated.emit(self.cards)

                    if hasattr(parent, "log_message"):
                        parent.log_message(
                            "SUCCESS",
                            f"Deck loaded: {len(self.cards)} cards successful, {failed_cards} failed",
                        )

                # Success message removed - already shown in logs
                # Switch to Generation tab after loading
                if parent and hasattr(parent, "tabs"):
                    parent.tabs.setCurrentIndex(2)  # Tab 3 (index 2) is Generation

            except Exception as e:
                if parent and hasattr(parent, "log_message"):
                    parent.log_message("ERROR", f"Failed to load deck: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to load deck: {str(e)}")
        else:
            if parent and hasattr(parent, "log_message"):
                parent.log_message("ERROR", f"Deck file not found: {filename}")

    def export_deck(self):
        """Export deck list"""
        # TODO: Implement export to various formats
        QMessageBox.information(self, "Info", "Export feature coming soon!")


class CardPreviewDialog(QDialog):
    """Dialog to preview generated card images"""

    def __init__(self, card: MTGCard, parent=None):
        super().__init__(parent)
        self.card = card
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"Card Preview: {self.card.name}")
        self.setModal(True)
        self.setMinimumSize(600, 800)

        layout = QVBoxLayout()

        # Card name header
        name_label = QLabel(f"<h2>{self.card.name}</h2>")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)

        # Card image display (no tabs)
        self.card_image_label = QLabel()
        self.card_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.card_image_label.setMinimumSize(400, 560)
        self.card_image_label.setStyleSheet(
            "border: 1px solid #ccc; background: #f0f0f0;"
        )

        if self.card.card_path and Path(self.card.card_path).exists():
            pixmap = QPixmap(self.card.card_path)
            scaled_pixmap = pixmap.scaled(
                400,
                560,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.card_image_label.setPixmap(scaled_pixmap)
        else:
            self.card_image_label.setText("Card image not generated yet")

        layout.addWidget(self.card_image_label)

        # Card details
        details_group = QGroupBox("Card Details")
        details_layout = QFormLayout()

        details_layout.addRow("Type:", QLabel(self.card.type))
        details_layout.addRow("Cost:", QLabel(self.card.cost or "—"))
        if self.card.power is not None and self.card.toughness is not None:
            details_layout.addRow(
                "P/T:", QLabel(f"{self.card.power}/{self.card.toughness}")
            )
        details_layout.addRow("Rarity:", QLabel(self.card.rarity))

        if self.card.text:
            text_label = QLabel(self.card.text.replace("\\n", "\n"))
            text_label.setWordWrap(True)
            details_layout.addRow("Text:", text_label)

        if self.card.flavor:
            flavor_label = QLabel(f"<i>{self.card.flavor}</i>")
            flavor_label.setWordWrap(True)
            details_layout.addRow("Flavor:", flavor_label)

        details_group.setLayout(details_layout)
        layout.addWidget(details_group)

        # Status info
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel(f"Status: {self.card.status}"))
        if self.card.generated_at:
            status_layout.addWidget(QLabel(f"Generated: {self.card.generated_at}"))
        status_layout.addStretch()
        layout.addLayout(status_layout)

        # Buttons
        button_layout = QHBoxLayout()

        if not self.card.card_path or not Path(self.card.card_path).exists():
            generate_btn = QPushButton("Generate Card")
            generate_btn.clicked.connect(self.generate_card)
            button_layout.addWidget(generate_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def generate_card(self):
        """Trigger card generation"""
        QMessageBox.information(
            self,
            "Generate",
            f"Card generation for {self.card.name} would be triggered here",
        )
        # TODO: Implement actual generation trigger


class CardEditDialog(QDialog):
    """Dialog for editing individual cards"""

    def __init__(self, card: MTGCard, parent=None):
        super().__init__(parent)
        self.card = card
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"Edit Card: {self.card.name}")
        self.setModal(True)
        self.resize(600, 500)

        layout = QFormLayout()

        # Card fields
        self.name_input = QLineEdit(self.card.name)
        self.type_input = QLineEdit(self.card.type)
        self.cost_input = QLineEdit(self.card.cost)
        self.text_input = QPlainTextEdit(self.card.text)
        self.text_input.setMaximumHeight(100)

        self.power_input = QSpinBox()
        self.power_input.setMinimum(-1)
        self.power_input.setMaximum(99)
        self.power_input.setValue(
            self.card.power if self.card.power is not None else -1
        )

        self.toughness_input = QSpinBox()
        self.toughness_input.setMinimum(-1)
        self.toughness_input.setMaximum(99)
        self.toughness_input.setValue(
            self.card.toughness if self.card.toughness is not None else -1
        )

        self.flavor_input = QLineEdit(self.card.flavor)

        self.rarity_combo = QComboBox()
        self.rarity_combo.addItems(["common", "uncommon", "rare", "mythic"])
        self.rarity_combo.setCurrentText(self.card.rarity)

        self.art_input = QPlainTextEdit(self.card.art)
        self.art_input.setMaximumHeight(100)

        layout.addRow("Name:", self.name_input)
        layout.addRow("Type:", self.type_input)
        layout.addRow("Cost:", self.cost_input)
        layout.addRow("Text:", self.text_input)
        layout.addRow("Power:", self.power_input)
        layout.addRow("Toughness:", self.toughness_input)
        layout.addRow("Flavor:", self.flavor_input)
        layout.addRow("Rarity:", self.rarity_combo)
        layout.addRow("Art Description:", self.art_input)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addWidget(buttons)
        self.setLayout(main_layout)

    def accept(self):
        """Save changes to card"""
        self.card.name = self.name_input.text()
        self.card.type = self.type_input.text()
        self.card.cost = self.cost_input.text()
        self.card.text = self.text_input.toPlainText()
        self.card.power = (
            self.power_input.value() if self.power_input.value() >= 0 else None
        )
        self.card.toughness = (
            self.toughness_input.value() if self.toughness_input.value() >= 0 else None
        )
        self.card.flavor = self.flavor_input.text()
        self.card.rarity = self.rarity_combo.currentText()
        self.card.art = self.art_input.toPlainText()
        super().accept()


class GenerationTab(QWidget):
    """Tab 3: Image & Card Generation with Enhanced Controls"""

    def __init__(self):
        super().__init__()
        self.cards = []
        self.generator_worker = CardGeneratorWorker()
        self.generator_worker.progress.connect(self.on_generation_progress)
        self.generator_worker.completed.connect(self.on_generation_completed)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Top Section: Generation Settings & Stats
        top_section = QWidget()
        top_layout = QVBoxLayout()

        # Generation settings in a more compact layout
        settings_group = QGroupBox("⚙️ Generation Settings")
        settings_layout = QGridLayout()

        # Row 1: Model and Style
        settings_layout.addWidget(QLabel("Model:"), 0, 0)
        self.model_combo = QComboBox()
        self.model_combo.addItems(
            ["sdxl", "sdxl-lightning", "flux-schnell", "flux-dev"]
        )
        self.model_combo.setToolTip("Select the AI model for image generation")
        settings_layout.addWidget(self.model_combo, 0, 1)

        settings_layout.addWidget(QLabel("Style:"), 0, 2)
        self.style_combo = QComboBox()
        self.style_combo.addItems(
            ["mtg_modern", "mtg_classic", "realistic", "anime", "oil_painting"]
        )
        self.style_combo.setToolTip("Select the art style for cards")
        settings_layout.addWidget(self.style_combo, 0, 3)

        # Row 2: Statistics
        self.stats_label = QLabel("📊 Status: Ready")
        settings_layout.addWidget(self.stats_label, 1, 0, 1, 2)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        settings_layout.addWidget(self.progress_bar, 1, 2, 1, 2)

        settings_layout.setColumnStretch(4, 1)  # Add stretch to the right
        settings_group.setLayout(settings_layout)
        top_layout.addWidget(settings_group)

        top_section.setLayout(top_layout)
        main_layout.addWidget(top_section)

        # Middle Section: Card Queue with Enhanced Controls
        queue_section = QWidget()
        queue_layout = QVBoxLayout()

        # Queue header with filter controls
        queue_header = QWidget()
        header_layout = QHBoxLayout()

        header_layout.addWidget(QLabel("🎴 Card Queue"))

        # Filter buttons
        self.filter_all_btn = QPushButton("All")
        self.filter_pending_btn = QPushButton("Pending")
        self.filter_completed_btn = QPushButton("Completed")
        self.filter_failed_btn = QPushButton("Failed")

        for btn in [
            self.filter_all_btn,
            self.filter_pending_btn,
            self.filter_completed_btn,
            self.filter_failed_btn,
        ]:
            btn.setCheckable(True)
            btn.setMaximumWidth(80)
            btn.clicked.connect(self.apply_filter)

        self.filter_all_btn.setChecked(True)

        header_layout.addWidget(self.filter_all_btn)
        header_layout.addWidget(self.filter_pending_btn)
        header_layout.addWidget(self.filter_completed_btn)
        header_layout.addWidget(self.filter_failed_btn)

        header_layout.addStretch()

        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Search cards...")
        self.search_box.setMaximumWidth(200)
        self.search_box.textChanged.connect(self.apply_filter)
        header_layout.addWidget(self.search_box)

        # Generate All Pending button (moved to top right)
        self.generate_all_btn = QPushButton("🚀 Generate All Pending")
        self.generate_all_btn.setStyleSheet(
            "QPushButton { font-weight: bold; padding: 8px; }"
        )
        self.generate_all_btn.clicked.connect(self.generate_all)
        header_layout.addWidget(self.generate_all_btn)

        queue_header.setLayout(header_layout)
        queue_layout.addWidget(queue_header)

        # Queue table without action buttons
        self.queue_table = QTableWidget()
        self.queue_table.setColumnCount(6)
        self.queue_table.setHorizontalHeaderLabels(
            ["ID", "Name", "Type", "Set", "Status", "Time"]
        )

        # Set column widths
        header = self.queue_table.horizontalHeader()
        header.resizeSection(0, 50)  # ID
        header.resizeSection(1, 300)  # Name - slightly less space to fit Set
        header.resizeSection(2, 150)  # Type
        header.resizeSection(3, 80)  # Set
        header.resizeSection(4, 120)  # Status
        header.resizeSection(5, 100)  # Time

        self.queue_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.queue_table.itemSelectionChanged.connect(self.on_selection_changed)

        # Set minimum row height to accommodate buttons
        self.queue_table.verticalHeader().setDefaultSectionSize(35)

        queue_layout.addWidget(self.queue_table)

        queue_section.setLayout(queue_layout)
        main_layout.addWidget(queue_section)

        # Bottom Section: Control Panel
        control_panel = QWidget()
        control_panel.setMaximumHeight(100)
        control_layout = QVBoxLayout()

        # Row 1: Main generation controls (dynamic based on selection)
        main_controls = QHBoxLayout()

        # These buttons will be shown/hidden based on selected card status
        self.generate_selected_btn = QPushButton("🎯 Generate Selected")
        self.generate_selected_btn.setVisible(False)  # Hidden by default
        main_controls.addWidget(self.generate_selected_btn)

        # Regeneration options (only shown for completed cards)
        self.regen_with_image_btn = QPushButton("🖼️ Regenerate with New Image")
        self.regen_with_image_btn.setToolTip(
            "Regenerate selected card with new artwork"
        )
        self.regen_with_image_btn.setVisible(False)  # Hidden by default
        main_controls.addWidget(self.regen_with_image_btn)

        self.regen_card_only_btn = QPushButton("🃏 Regenerate Card Only")
        self.regen_card_only_btn.setToolTip("Regenerate card using existing artwork")
        self.regen_card_only_btn.setVisible(False)  # Hidden by default
        main_controls.addWidget(self.regen_card_only_btn)

        # Custom image option
        self.use_custom_image_btn = QPushButton("📷 Use Custom Image")
        self.use_custom_image_btn.setToolTip(
            "Select your own image as artwork for selected cards"
        )
        self.use_custom_image_btn.setVisible(False)  # Hidden by default
        main_controls.addWidget(self.use_custom_image_btn)

        # Delete (only shown for completed cards)
        self.delete_files_btn = QPushButton("🗑️ Delete Files")
        self.delete_files_btn.setVisible(False)  # Hidden by default
        main_controls.addWidget(self.delete_files_btn)

        main_controls.addStretch()

        control_layout.addLayout(main_controls)

        # Row 2: Current status
        status_layout = QHBoxLayout()
        self.current_card_label = QLabel("💡 Ready to generate cards")
        self.current_card_label.setStyleSheet("color: #4ec9b0; font-weight: bold;")
        status_layout.addWidget(self.current_card_label)

        status_layout.addStretch()

        self.eta_label = QLabel("ETA: --:--")
        status_layout.addWidget(self.eta_label)

        control_layout.addLayout(status_layout)

        control_panel.setLayout(control_layout)
        main_layout.addWidget(control_panel)

        # Connect signals
        self.generate_selected_btn.clicked.connect(self.generate_selected_cards)
        self.regen_with_image_btn.clicked.connect(self.regenerate_selected_with_image)
        self.regen_card_only_btn.clicked.connect(self.regenerate_selected_card_only)
        self.use_custom_image_btn.clicked.connect(self.use_custom_image_for_selected)
        self.delete_files_btn.clicked.connect(self.delete_selected_files)

        # Double-click to edit
        self.queue_table.itemDoubleClicked.connect(self.on_item_double_clicked)

        self.setLayout(main_layout)

    def refresh_table(self):
        """Refresh the queue table with current cards"""
        self.queue_table.setRowCount(len(self.cards))

        completed = 0
        pending = 0
        failed = 0

        for row, card in enumerate(self.cards):
            # ID
            self.queue_table.setItem(row, 0, QTableWidgetItem(str(card.id)))

            # Name
            self.queue_table.setItem(row, 1, QTableWidgetItem(card.name))

            # Type
            card_type = (
                card.type.split("—")[0].strip() if "—" in card.type else card.type
            )
            self.queue_table.setItem(row, 2, QTableWidgetItem(card_type))

            # Set
            card_set = card.set if hasattr(card, "set") and card.set else "CMD"
            self.queue_table.setItem(row, 3, QTableWidgetItem(card_set))

            # Status with icon
            if card.status == "completed":
                status_text = "✅ Done"
                status_item = QTableWidgetItem(status_text)
                status_item.setBackground(QBrush(QColor(100, 200, 100)))
                completed += 1
            elif card.status == "generating":
                status_text = "⏳ Processing"
                status_item = QTableWidgetItem(status_text)
                status_item.setBackground(QBrush(QColor(200, 200, 100)))
            elif card.status == "failed":
                status_text = "❌ Failed"
                status_item = QTableWidgetItem(status_text)
                status_item.setBackground(QBrush(QColor(200, 100, 100)))
                failed += 1
            else:  # pending
                status_text = "⏸️ Pending"
                status_item = QTableWidgetItem(status_text)
                status_item.setBackground(QBrush(QColor(150, 150, 150)))
                pending += 1
            self.queue_table.setItem(row, 4, status_item)

            # Time
            if card.generated_at:
                self.queue_table.setItem(row, 5, QTableWidgetItem(card.generated_at))
            else:
                self.queue_table.setItem(row, 5, QTableWidgetItem("--:--"))

        # Update statistics
        total = len(self.cards)
        self.stats_label.setText(
            f"📊 Total: {total} | ✅ Done: {completed} | ⏸️ Pending: {pending} | ❌ Failed: {failed}"
        )

        # Update progress bar
        if total > 0:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(completed)
            self.progress_bar.setFormat(
                f"{completed}/{total} ({int(completed/total*100)}%)"
            )

    def delete_card_files(self, row: int):
        """Delete generated files for a card"""
        if 0 <= row < len(self.cards):
            card = self.cards[row]
            reply = QMessageBox.question(
                self,
                "Delete Files",
                f"Delete generated files for '{card.name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                import os
                from pathlib import Path

                # Delete files (reuse logic from CardManagementTab)
                deleted_files = []

                if card.card_path and Path(card.card_path).exists():
                    try:
                        os.remove(card.card_path)
                        deleted_files.append(Path(card.card_path).name)
                        card.card_path = None
                    except Exception as e:
                        print(f"Error deleting: {e}")

                if card.image_path and Path(card.image_path).exists():
                    try:
                        os.remove(card.image_path)
                        deleted_files.append(Path(card.image_path).name)
                        card.image_path = None
                    except Exception as e:
                        print(f"Error deleting: {e}")

                # Try pattern-based deletion in deck-specific directories
                safe_name = make_safe_filename(card.name)

                # Get deck-specific directories
                parent = self.parent().parent() if hasattr(self, "parent") else None
                if (
                    parent
                    and hasattr(parent, "current_deck_name")
                    and parent.current_deck_name
                ):
                    deck_dir = Path("saved_decks") / parent.current_deck_name
                    cards_dir = deck_dir / "rendered_cards"
                    images_dir = deck_dir / "artwork"
                else:
                    # Fallback to old directories
                    cards_dir = Path("output/cards")
                    images_dir = Path("output/images")

                # Delete from cards directory
                if cards_dir.exists():
                    for file in cards_dir.glob(f"{safe_name}_*.png"):
                        try:
                            os.remove(file)
                            deleted_files.append(file.name)
                        except:
                            pass

                    for file in cards_dir.glob(f"{safe_name}_*.json"):
                        try:
                            os.remove(file)
                            deleted_files.append(file.name)
                        except:
                            pass

                # Delete from images directory
                if images_dir.exists():
                    for file in images_dir.glob(f"{safe_name}*.jpg"):
                        try:
                            os.remove(file)
                            deleted_files.append(file.name)
                        except:
                            pass
                    for file in images_dir.glob(f"{safe_name}*.png"):
                        try:
                            os.remove(file)
                            deleted_files.append(file.name)
                        except:
                            pass

                # Reset status
                card.status = "pending"
                card.generated_at = None
                self.refresh_table()

                # Log
                parent = self.parent().parent() if hasattr(self, "parent") else None
                if parent and hasattr(parent, "log_message"):
                    if deleted_files:
                        parent.log_message(
                            "INFO", f"Deleted: {', '.join(deleted_files)}"
                        )

    def regenerate_selected_with_image(self):
        """Regenerate selected card with new image"""
        selected_rows = set()
        for item in self.queue_table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            QMessageBox.warning(
                self, "No Selection", "Please select a card to regenerate!"
            )
            return

        row = min(selected_rows)  # Get first selected row
        if 0 <= row < len(self.cards):
            card = self.cards[row]
            card.status = "pending"
            self.refresh_table()

            # Start generation with new image
            self.generator_worker.set_cards(
                [card],
                self.model_combo.currentText(),
                self.style_combo.currentText(),
                "regeneration_with_image",
            )
            self.generator_worker.start()

            parent = self.parent().parent() if hasattr(self, "parent") else None
            if parent and hasattr(parent, "log_message"):
                parent.log_message("INFO", f"Regenerating with new image: {card.name}")

    def regenerate_selected_card_only(self):
        """Regenerate selected card using existing artwork"""
        selected_rows = set()
        for item in self.queue_table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            QMessageBox.warning(
                self, "No Selection", "Please select a card to regenerate!"
            )
            return

        row = min(selected_rows)  # Get first selected row
        if 0 <= row < len(self.cards):
            card = self.cards[row]

            # Check multiple possible artwork locations
            artwork_path = None

            # First check if image_path is set and exists
            if card.image_path and Path(card.image_path).exists():
                artwork_path = card.image_path
            else:
                # Try to find artwork in standard locations
                safe_name = make_safe_filename(card.name)

                # Check output/images/ directory with different extensions
                for ext in [".jpg", ".jpeg", ".png"]:
                    potential_path = Path(f"output/images/{safe_name}{ext}")
                    if potential_path.exists():
                        artwork_path = str(potential_path)
                        card.image_path = artwork_path  # Update the card object
                        break

                # Also check for files with similar names (e.g., Mountain.jpg for Mountain card)
                if not artwork_path:
                    simple_name = card.name.split(",")[
                        0
                    ].strip()  # Get first part of name
                    for ext in [".jpg", ".jpeg", ".png"]:
                        potential_path = Path(f"output/images/{simple_name}{ext}")
                        if potential_path.exists():
                            artwork_path = str(potential_path)
                            card.image_path = artwork_path
                            break

            if not artwork_path:
                reply = QMessageBox.question(
                    self,
                    "No Artwork",
                    f"No artwork found for '{card.name}'. Generate new artwork?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.regenerate_selected_with_image()
                return

            card.status = "pending"
            self.refresh_table()

            # Start card-only regeneration with found artwork
            self.generator_worker.set_cards(
                [card],
                self.model_combo.currentText(),
                self.style_combo.currentText(),
                "card_only_regeneration",
            )
            self.generator_worker.start()

            parent = self.parent().parent() if hasattr(self, "parent") else None
            if parent and hasattr(parent, "log_message"):
                parent.log_message(
                    "INFO", f"Regenerating card only (keeping artwork): {card.name}"
                )
                parent.log_message("DEBUG", f"Using artwork: {artwork_path}")

    def edit_selected_art(self):
        """Edit art prompt for selected card"""
        selected_rows = set()
        for item in self.queue_table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a card!")
            return

        row = min(selected_rows)
        self.edit_art_prompt(row)

    def use_custom_image_for_selected(self):
        """Allow user to select custom image for selected cards"""
        selected_rows = set()
        for item in self.queue_table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            QMessageBox.warning(
                self, "No Selection", "Please select cards to set custom image!"
            )
            return

        # Get the current deck's artwork folder
        parent = get_main_window()  # Use get_main_window() for reliability
        default_dir = ""

        if parent and hasattr(parent, "current_deck_name") and parent.current_deck_name:
            # Use the deck-specific artwork folder with absolute path
            artwork_dir = (
                Path.cwd() / "saved_decks" / parent.current_deck_name / "artwork"
            ).resolve()

            # Create the artwork directory if it doesn't exist
            if not artwork_dir.exists():
                artwork_dir.mkdir(parents=True, exist_ok=True)
                if parent and hasattr(parent, "log_message"):
                    parent.log_message("INFO", f"Created artwork folder: {artwork_dir}")

            default_dir = str(artwork_dir)
            if parent and hasattr(parent, "log_message"):
                parent.log_message("INFO", "[CUSTOM IMAGE] Opening file dialog")
                parent.log_message(
                    "INFO", f"[CUSTOM IMAGE] Deck: {parent.current_deck_name}"
                )
                parent.log_message(
                    "INFO", f"[CUSTOM IMAGE] Artwork folder: {artwork_dir}"
                )
                parent.log_message(
                    "DEBUG", f"[CUSTOM IMAGE] Path exists: {artwork_dir.exists()}"
                )
                parent.log_message(
                    "DEBUG",
                    f"[CUSTOM IMAGE] Path is absolute: {artwork_dir.is_absolute()}",
                )
        else:
            if parent and hasattr(parent, "log_message"):
                parent.log_message(
                    "WARNING",
                    "No deck loaded - using current directory for file dialog",
                )

        # Open file dialog to select image
        # Create dialog explicitly to ensure directory is set
        dialog = QFileDialog(self)
        dialog.setWindowTitle("Select Custom Artwork")
        dialog.setNameFilter(
            "Image Files (*.png *.jpg *.jpeg *.gif *.bmp);;All Files (*.*)"
        )
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)

        if default_dir and Path(default_dir).exists():
            dialog.setDirectory(default_dir)
            # Also try to set as URLs for better compatibility
            from PyQt6.QtCore import QUrl

            dialog.setDirectoryUrl(QUrl.fromLocalFile(default_dir))

            if parent and hasattr(parent, "log_message"):
                parent.log_message("DEBUG", f"Dialog directory set to: {default_dir}")

        if dialog.exec():
            selected_files = dialog.selectedFiles()
            if selected_files:
                image_path = selected_files[0]
            else:
                image_path = None
        else:
            image_path = None

        if not image_path:
            return  # User cancelled

        # Verify the image exists
        if not Path(image_path).exists():
            QMessageBox.warning(
                self, "File Error", f"Selected file does not exist: {image_path}"
            )
            return

        # Apply custom image to all selected cards and regenerate
        cards_to_generate = []
        for row in selected_rows:
            if 0 <= row < len(self.cards):
                card = self.cards[row]
                # Store custom image path
                card.custom_image_path = image_path
                # Mark for regeneration
                card.status = "pending"
                cards_to_generate.append(card)

        if cards_to_generate:
            # Update table to show pending status
            self.refresh_table()

            # Log the action
            parent = self.parent().parent() if hasattr(self, "parent") else None
            if parent and hasattr(parent, "log_message"):
                parent.log_message(
                    "INFO",
                    f"Generating {len(cards_to_generate)} cards with custom image: {Path(image_path).name}",
                )

            # Start generation with custom image
            parent = get_main_window()  # Use get_main_window() for reliability
            deck_name = (
                parent.current_deck_name
                if parent and hasattr(parent, "current_deck_name")
                else None
            )

            # Debug logging
            if parent and hasattr(parent, "log_message"):
                parent.log_message(
                    "DEBUG", f"Using deck_name for generation: {deck_name}"
                )
                parent.log_message("DEBUG", f"Parent type: {type(parent).__name__}")
                parent.log_message(
                    "DEBUG",
                    f"Has current_deck_name: {hasattr(parent, 'current_deck_name')}",
                )
                if hasattr(parent, "current_deck_name"):
                    parent.log_message(
                        "DEBUG", f"current_deck_name value: {parent.current_deck_name}"
                    )

            self.generator_worker.set_cards(
                cards_to_generate,
                self.model_combo.currentText(),
                self.style_combo.currentText(),
                "custom_image",
                deck_name,
            )
            self.generator_worker.start()

    def delete_selected_files(self):
        """Delete files for selected card"""
        selected_rows = set()
        for item in self.queue_table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a card!")
            return

        row = min(selected_rows)
        self.delete_card_files(row)

    def regenerate_single_card(self, row: int):
        """Regenerate a single card"""
        if 0 <= row < len(self.cards):
            card = self.cards[row]
            card.status = "pending"
            self.refresh_table()

            # Start generation for just this card
            self.generator_worker.set_cards(
                [card],
                self.model_combo.currentText(),
                self.style_combo.currentText(),
                "regeneration",
            )
            self.generator_worker.start()

            parent = self.parent().parent() if hasattr(self, "parent") else None
            if parent and hasattr(parent, "log_message"):
                parent.log_message("INFO", f"Regenerating: {card.name}")

    def edit_art_prompt(self, row: int):
        """Edit art prompt for a card"""
        if 0 <= row < len(self.cards):
            card = self.cards[row]

            dialog = QDialog(self)
            dialog.setWindowTitle(f"Edit Art - {card.name}")
            dialog.setModal(True)
            dialog.resize(500, 200)

            layout = QVBoxLayout()

            label = QLabel(f"Art description for '{card.name}':")
            layout.addWidget(label)

            text_edit = QTextEdit()
            text_edit.setPlainText(card.art or f"Fantasy art of {card.name}")
            layout.addWidget(text_edit)

            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok
                | QDialogButtonBox.StandardButton.Cancel
            )
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)

            dialog.setLayout(layout)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_art = text_edit.toPlainText().strip()
                if new_art != card.art:
                    card.art = new_art
                    self.refresh_table()

                    reply = QMessageBox.question(
                        self,
                        "Regenerate?",
                        "Regenerate card with new art?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    )

                    if reply == QMessageBox.StandardButton.Yes:
                        self.regenerate_single_card(row)

    def apply_filter(self):
        """Apply filters to the table"""
        search_text = self.search_box.text().lower()

        # Determine which filter is active
        show_all = self.filter_all_btn.isChecked()
        show_pending = self.filter_pending_btn.isChecked()
        show_completed = self.filter_completed_btn.isChecked()
        show_failed = self.filter_failed_btn.isChecked()

        for row in range(self.queue_table.rowCount()):
            show = True

            # Status filter
            if not show_all:
                status_item = self.queue_table.item(row, 3)
                if status_item:
                    status = status_item.text()
                    if status == "pending" and not show_pending:
                        show = False
                    elif status == "completed" and not show_completed:
                        show = False
                    elif status == "failed" and not show_failed:
                        show = False

            # Search filter
            if show and search_text:
                name_item = self.queue_table.item(row, 1)
                type_item = self.queue_table.item(row, 2)
                if name_item and type_item:
                    if (
                        search_text not in name_item.text().lower()
                        and search_text not in type_item.text().lower()
                    ):
                        show = False

            self.queue_table.setRowHidden(row, not show)

    def on_selection_changed(self):
        """Handle selection change in the table"""
        # Update preview if main window exists
        selected_rows = set()
        for item in self.queue_table.selectedItems():
            selected_rows.add(item.row())

        # Always show custom image button when there's a selection
        has_selection = bool(selected_rows)
        self.use_custom_image_btn.setVisible(has_selection)

        if not has_selection:
            # No selection - hide all context-sensitive buttons
            self.generate_selected_btn.setVisible(False)
            self.regen_with_image_btn.setVisible(False)
            self.regen_card_only_btn.setVisible(False)
            self.delete_files_btn.setVisible(False)
            return

        # Get the first selected card to determine button visibility
        row = min(selected_rows)
        if 0 <= row < len(self.cards):
            card = self.cards[row]

            # Show buttons based on card status
            if card.status == "pending":
                # Show only Generate Selected for pending cards
                self.generate_selected_btn.setVisible(True)
                self.regen_with_image_btn.setVisible(False)
                self.regen_card_only_btn.setVisible(False)
                self.delete_files_btn.setVisible(False)
            elif card.status == "completed":
                # Show regenerate and delete options for completed cards
                self.generate_selected_btn.setVisible(False)
                self.regen_with_image_btn.setVisible(True)
                self.regen_card_only_btn.setVisible(True)
                self.delete_files_btn.setVisible(True)
            elif card.status == "failed":
                # Show generate for failed cards (retry)
                self.generate_selected_btn.setVisible(True)
                self.regen_with_image_btn.setVisible(False)
                self.regen_card_only_btn.setVisible(False)
                self.delete_files_btn.setVisible(False)
            else:
                # Default: hide all except custom image
                self.generate_selected_btn.setVisible(False)
                self.regen_with_image_btn.setVisible(False)
                self.regen_card_only_btn.setVisible(False)
                self.delete_files_btn.setVisible(False)

            # Trigger preview update in main window
            parent = self.parent().parent() if hasattr(self, "parent") else None
            if parent and hasattr(parent, "update_card_preview"):
                parent.update_card_preview(card)

    def batch_delete_files(self):
        """Delete files for all selected cards"""
        selected_rows = set()
        for item in self.queue_table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            QMessageBox.warning(
                self, "No Selection", "Please select cards to delete files"
            )
            return

        reply = QMessageBox.question(
            self,
            "Batch Delete",
            f"Delete files for {len(selected_rows)} selected cards?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            for row in selected_rows:
                if 0 <= row < len(self.cards):
                    # Delete without confirmation (already confirmed)
                    self.delete_card_files_silent(row)
            self.refresh_table()

    def delete_card_files_silent(self, row: int):
        """Delete files without confirmation dialog"""
        if 0 <= row < len(self.cards):
            card = self.cards[row]
            import os
            from pathlib import Path

            # Same deletion logic but silent
            if card.card_path and Path(card.card_path).exists():
                try:
                    os.remove(card.card_path)
                except:
                    pass
                card.card_path = None

            if card.image_path and Path(card.image_path).exists():
                try:
                    os.remove(card.image_path)
                except:
                    pass
                card.image_path = None

            safe_name = make_safe_filename(card.name)
            for pattern in [f"{safe_name}_*.png", f"{safe_name}_*.json"]:
                for file in Path("output/cards").glob(pattern):
                    try:
                        os.remove(file)
                    except:
                        pass

            for file in Path("output/images").glob(f"{safe_name}*.jpg"):
                try:
                    os.remove(file)
                except:
                    pass

            card.status = "pending"
            card.generated_at = None

    def generate_selected_cards(self):
        """Generate only selected cards"""
        selected_rows = set()
        for item in self.queue_table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select cards to generate")
            return

        cards_to_generate = []
        for row in selected_rows:
            if 0 <= row < len(self.cards):
                card = self.cards[row]
                if card.status != "completed":
                    card.status = "pending"
                    cards_to_generate.append(card)

        if cards_to_generate:
            self.refresh_table()
            parent = self.parent().parent() if hasattr(self, "parent") else None
            deck_name = (
                parent.current_deck_name
                if parent and hasattr(parent, "current_deck_name")
                else None
            )
            self.generator_worker.set_cards(
                cards_to_generate,
                self.model_combo.currentText(),
                self.style_combo.currentText(),
                "selected",
                deck_name,
            )
            self.generator_worker.start()

            parent = self.parent().parent() if hasattr(self, "parent") else None
            if parent and hasattr(parent, "log_message"):
                parent.log_message(
                    "INFO", f"Generating {len(cards_to_generate)} selected cards"
                )

    def load_cards(self, cards: list[MTGCard]):
        """Load cards for generation"""
        # Get main window for logging
        main_window = get_main_window()

        if main_window and hasattr(main_window, "log_message"):
            main_window.log_message(
                "INFO", f"Loading {len(cards)} cards into Generation Tab"
            )

            # Count status
            completed = sum(1 for c in cards if c.status == "completed")
            pending = sum(1 for c in cards if c.status == "pending")
            failed = sum(1 for c in cards if c.status == "failed")

            main_window.log_message(
                "DEBUG",
                f"Status: {completed} completed, {pending} pending, {failed} failed",
            )

        self.cards = cards
        self.refresh_table()  # Use the new refresh_table method

    def generate_all(self):
        """Start generating all cards"""
        if not self.cards:
            QMessageBox.warning(self, "Warning", "No cards to generate!")
            return

        try:
            # Count cards needing art descriptions
            cards_needing_art = 0

            # Reset status for pending cards and check art descriptions
            for i, card in enumerate(self.cards):
                if card.status != "completed":
                    card.status = "pending"

                # Check if art description is needed
                if not card.art or card.art == "":
                    cards_needing_art += 1

            # Generate art descriptions with progress updates
            if cards_needing_art > 0:
                # Get main window for status updates
                main_window = get_main_window()

                if main_window and hasattr(main_window, "update_status"):
                    main_window.update_status(
                        "generating",
                        f"Adding art descriptions (0/{cards_needing_art})...",
                    )

                for i, card in enumerate(self.cards):
                    if not card.art or card.art == "":
                        if main_window:
                            main_window.update_status(
                                "generating",
                                f"Art description {i+1}/{len(self.cards)}: {card.name}",
                            )
                            main_window.log_message(
                                "INFO", f"Generating art for: {card.name}"
                            )
                        card.art = self.get_default_art_description(card)
                        QApplication.processEvents()  # Keep UI responsive

            self.refresh_table()  # Use refresh_table instead

            # Start generation
            model = self.model_combo.currentText()
            style = self.style_combo.currentText()

            pending_cards = [c for c in self.cards if c.status == "pending"]

            if pending_cards:
                # Get theme for folder organization
                theme = "default"
                if main_window and hasattr(main_window, "theme_tab"):
                    theme = main_window.theme_tab.get_theme()

                # Get current deck name
                deck_name = (
                    main_window.current_deck_name
                    if main_window and hasattr(main_window, "current_deck_name")
                    else None
                )
                self.generator_worker.set_cards(
                    pending_cards, model, style, theme, deck_name
                )
                self.generator_worker.start()

                self.generate_all_btn.setEnabled(False)
                self.pause_btn.setEnabled(True)

                if main_window:
                    main_window.log_message(
                        "INFO",
                        f"Starting image generation for {len(pending_cards)} cards",
                    )
            else:
                QMessageBox.information(
                    self, "Info", "All cards are already generated!"
                )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start generation: {str(e)}")
            if main_window:
                main_window.log_message("ERROR", f"Generation failed: {str(e)}")

    def get_default_art_description(self, card: MTGCard) -> str:
        """Get default art description based on card name and type"""
        # Percy Jackson specific characters
        if "Percy" in card.name:
            return "teenage boy with messy black hair and sea-green eyes, wearing orange Camp Half-Blood t-shirt and jeans, holding bronze sword Riptide, water swirling around him"
        elif "Annabeth" in card.name:
            return "teenage girl with curly blonde hair and stormy gray eyes, wearing Camp Half-Blood t-shirt, holding bronze dagger, architectural blueprints floating around her"
        elif "Grover" in card.name:
            return "teenage satyr with curly brown hair, small horns, goat legs, wearing Camp Half-Blood t-shirt, playing reed pipes"
        elif "Camp Half-Blood" in card.name:
            return "summer camp with Greek architecture, wooden cabins arranged in U-shape, strawberry fields, Big House with blue roof, magical barrier shimmering"
        elif "Poseidon" in card.name or "Sea" in card.name:
            return "majestic ocean scene with towering waves, sea creatures, trident glowing with power"

        # Generic by type
        elif "Land" in card.type:
            if "Island" in card.name:
                return "mystical island surrounded by crystal blue waters, magical energy emanating"
            elif "Mountain" in card.name:
                return "towering mountain peak with lightning striking, red mana crystals glowing"
            elif "Forest" in card.name:
                return "ancient forest with massive trees, green magical light filtering through"
            else:
                return (
                    f"mystical landscape depicting {card.name}, magical energy visible"
                )
        elif "Creature" in card.type:
            return f"fantasy creature {card.name} in dynamic action pose, magical aura surrounding it"
        elif "Instant" in card.type or "Sorcery" in card.type:
            return f"magical spell effect showing {card.name}, energy swirling dramatically"
        elif "Artifact" in card.type:
            return f"ancient magical artifact {card.name}, glowing with arcane power"
        elif "Enchantment" in card.type:
            return (
                f"ethereal magical aura representing {card.name}, shimmering with power"
            )
        else:
            return f"fantasy art depicting {card.name}"

    def on_item_double_clicked(self, item):
        """Handle double-click on table item - open edit dialog"""
        row = self.queue_table.currentRow()
        if 0 <= row < len(self.cards):
            self.edit_art_prompt(row)

    def pause_generation(self):
        """Pause generation"""
        self.generator_worker.pause()
        self.pause_btn.setEnabled(False)
        self.resume_btn.setEnabled(True)

    def resume_generation(self):
        """Resume generation"""
        self.generator_worker.resume()
        self.pause_btn.setEnabled(True)
        self.resume_btn.setEnabled(False)

    def retry_failed(self):
        """Retry failed cards"""
        failed_cards = [c for c in self.cards if c.status == "failed"]
        if not failed_cards:
            QMessageBox.information(self, "Info", "No failed cards to retry!")
            return

        for card in failed_cards:
            card.status = "pending"

        self.refresh_table()  # Use refresh_table instead of update_queue_display

        model = self.model_combo.currentText()
        style = self.style_combo.currentText()

        # Get theme
        main_window = get_main_window()

        theme = "default"
        if main_window and hasattr(main_window, "theme_tab"):
            theme = main_window.theme_tab.get_theme()

        # Get current deck name
        deck_name = (
            main_window.current_deck_name
            if main_window and hasattr(main_window, "current_deck_name")
            else None
        )
        self.generator_worker.set_cards(failed_cards, model, style, theme, deck_name)
        self.generator_worker.start()

    def on_generation_progress(self, card_id: int, status: str):
        """Handle generation progress"""
        # Get main window for logging
        main_window = get_main_window()

        for card in self.cards:
            if str(card.id) == str(card_id):
                card.status = status
                if main_window and hasattr(main_window, "log_message"):
                    if status == "generating":
                        main_window.log_message(
                            "INFO", f"Processing card {card_id}: {card.name}"
                        )
                        self.current_card_label.setText(f"🎨 Generating: {card.name}")
                    elif status == "completed":
                        main_window.log_message(
                            "SUCCESS", f"✅ Card {card_id} completed: {card.name}"
                        )
                    elif status == "failed":
                        main_window.log_message(
                            "ERROR", f"❌ Card {card_id} failed: {card.name}"
                        )
                break

        self.refresh_table()  # Use refresh_table instead of update_queue_display

    def on_generation_completed(
        self,
        card_id,
        success: bool,
        message: str,
        image_path: str = "",
        card_path: str = "",
    ):
        """Handle generation completion with file paths"""
        # Get main window for logging
        main_window = get_main_window()

        # Debug log to see what IDs we're working with
        if main_window and hasattr(main_window, "log_message"):
            main_window.log_message(
                "DEBUG", f"Looking for card with ID {card_id} (type: {type(card_id)})"
            )
            main_window.log_message(
                "DEBUG",
                f"Available card IDs: {[f'{c.id} (type: {type(c.id)})' for c in self.cards[:5]]}",
            )

        # Convert card_id to string for comparison if needed
        for card in self.cards:
            # Handle both string and int IDs for compatibility
            if str(card.id) == str(card_id) or card.id == card_id:
                card.status = "completed" if success else "failed"
                if success:
                    card.generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    if image_path:
                        card.image_path = image_path
                        if main_window and hasattr(main_window, "log_message"):
                            main_window.log_message(
                                "INFO", f"Art image saved: {image_path}"
                            )
                    if card_path:
                        card.card_path = card_path
                        if main_window and hasattr(main_window, "log_message"):
                            main_window.log_message(
                                "INFO", f"Card image saved: {card_path}"
                            )
                    if main_window and hasattr(main_window, "log_message"):
                        main_window.log_message(
                            "SUCCESS",
                            f"Card {card_id} ({card.name}) generated successfully",
                        )
                else:
                    if main_window and hasattr(main_window, "log_message"):
                        main_window.log_message(
                            "ERROR", f"Card {card_id} ({card.name}) failed: {message}"
                        )
                break

        self.refresh_table()  # Use refresh_table instead

        # Update the card in all tabs and refresh preview
        if main_window:
            # Update cards tab
            if hasattr(main_window, "cards_tab"):
                # Find and update the card in cards_tab
                for i, c in enumerate(main_window.cards_tab.cards):
                    if str(c.id) == str(card_id):
                        # Update the card object in cards_tab with the one from generation_tab
                        for gen_card in self.cards:
                            if str(gen_card.id) == str(card_id):
                                main_window.cards_tab.cards[i] = gen_card
                                break
                        break
                main_window.cards_tab.refresh_table()

            # Update preview if this card is selected
            if (
                hasattr(main_window, "current_preview_card")
                and main_window.current_preview_card
            ):
                if str(main_window.current_preview_card.id) == str(card_id):
                    main_window.update_card_preview(card)

            # Auto-save deck with updated paths
            if success and hasattr(main_window, "auto_save_deck"):
                main_window.auto_save_deck(self.cards, new_generation=False)

        if not success:
            QMessageBox.critical(
                self,
                "Generation Failed",
                f"Card {card_id} failed:\n{message}\n\nGeneration stopped.",
            )
            self.generate_all_btn.setEnabled(True)
            # self.pause_button.setEnabled(False)  # pause_button doesn't exist in new UI
        else:
            # Check if all cards are done
            if all(c.status in ["completed", "failed"] for c in self.cards):
                self.generate_all_btn.setEnabled(True)
                # self.pause_button.setEnabled(False)  # pause_button doesn't exist in new UI

                completed = sum(1 for c in self.cards if c.status == "completed")
                failed = sum(1 for c in self.cards if c.status == "failed")

                if main_window:
                    main_window.update_status(
                        "idle",
                        f"Generation complete: {completed} success, {failed} failed",
                    )
                    main_window.log_message(
                        "INFO",
                        f"Generation batch complete: {completed} successful, {failed} failed",
                    )

                    # Auto-save deck with updated file paths
                    if hasattr(main_window, "auto_save_deck"):
                        main_window.auto_save_deck(self.cards, "Generation completed")


class MTGDeckBuilder(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.generation_active = False
        self.current_preview_card = None  # Track for resize events
        self.current_deck_name = None  # Track active deck name
        self.last_loaded_deck_path = None  # Track last loaded deck for auto-loading
        self.init_ui()
        self.load_settings()
        self.setup_status_timer()

    def init_ui(self):
        self.setWindowTitle("MTG Commander Deck Builder")

        # Get screen dimensions to ensure window fits
        from PyQt6.QtWidgets import QApplication

        screen = QApplication.primaryScreen()
        screen_rect = screen.availableGeometry()

        # Set window size to 90% of screen size, max 1400x900
        width = min(int(screen_rect.width() * 0.9), 1400)
        height = min(int(screen_rect.height() * 0.9), 900)

        # Center the window on screen
        x = (screen_rect.width() - width) // 2
        y = (screen_rect.height() - height) // 2

        self.setGeometry(x, y, width, height)
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

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Add status indicator bar
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
        self.generation_tab = GenerationTab()

        # Add tabs
        self.tabs.addTab(self.theme_tab, "🎨 Theme & Config")
        self.tabs.addTab(self.cards_tab, "📋 Card Management")
        self.tabs.addTab(self.generation_tab, "🎯 Generation")

        # Set default tab to Generation (Tab 3, index 2)
        self.tabs.setCurrentIndex(2)

        # Logger panel
        self.create_logger_panel()

        # Add to left splitter with better proportions for logger
        left_splitter.addWidget(self.tabs)
        left_splitter.addWidget(self.logger_widget)
        left_splitter.setSizes([450, 450])  # Equal split for better logger visibility

        # Right side: Card Preview Panel
        self.create_card_preview_panel()

        # Add to main splitter
        main_splitter.addWidget(left_splitter)
        main_splitter.addWidget(self.card_preview_widget)
        main_splitter.setSizes([900, 500])  # 900px for left side, 500px for preview

        layout.addWidget(main_splitter)

        # Connect signals
        self.theme_tab.cards_generated.connect(self.on_cards_generated)
        self.cards_tab.cards_updated.connect(self.on_cards_updated)
        self.cards_tab.regenerate_card.connect(self.on_regenerate_single_card)

        # Connect card selection signals for preview
        self.cards_tab.table.itemSelectionChanged.connect(
            self.on_card_selection_changed_in_table
        )
        self.generation_tab.queue_table.itemSelectionChanged.connect(
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

        self.generation_tab.generator_worker.started.connect(
            self.on_image_generation_started
        )
        self.generation_tab.generator_worker.finished.connect(
            self.on_generation_finished
        )
        self.generation_tab.generator_worker.progress.connect(
            self.on_image_generation_progress
        )
        self.generation_tab.generator_worker.completed.connect(
            self.on_card_generation_completed
        )
        # Connect log_message signal for thread-safe logging
        self.generation_tab.generator_worker.log_message.connect(self.log_message)

        # Status bar
        self.statusBar().showMessage("Ready")

    def on_cards_generated(self, cards: list[MTGCard]):
        """Handle cards generated from theme tab"""
        self.cards_tab.load_cards(cards)
        self.generation_tab.load_cards(cards)
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
        """Handle cards updated from management tab"""
        self.generation_tab.load_cards(cards)
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

        # Load all cards to generation tab (it will only generate pending ones)
        self.generation_tab.load_cards(current_cards)

        # Switch to generation tab
        self.tabs.setCurrentIndex(2)

        # Start generation for pending cards (which includes our reset card)
        self.generation_tab.generate_images()

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
                self.log_message(
                    "INFO",
                    f"No deck name set, using commander name: {self.current_deck_name}",
                )
            else:
                theme_clean = (
                    theme.lower().replace(" ", "_").replace("(", "").replace(")", "")
                )
                self.current_deck_name = f"deck_{theme_clean}"
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

        logger_label = QLabel("📜 Logs & Output")
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

        self.preview_type = QLabel("Type: —")
        self.preview_cost = QLabel("Cost: —")
        self.preview_pt = QLabel("P/T: —")
        self.preview_rarity = QLabel("Rarity: —")
        self.preview_status = QLabel("Status: —")

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
        self.preview_text = QLabel("Text: —")
        self.preview_text.setWordWrap(True)
        self.preview_text.setStyleSheet(
            "padding: 5px; color: #cccccc; background-color: #3c3c3c; border: 1px solid #555; border-radius: 3px;"
        )
        self.preview_text.setMaximumHeight(80)
        details_layout.addWidget(self.preview_text)

        # Flavor text
        self.preview_flavor = QLabel("Flavor: —")
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

        # Current task label
        self.current_task_label = QLabel("")
        self.current_task_label.setStyleSheet(
            "font-size: 14px; color: #cccccc; margin-left: 20px;"
        )
        layout.addWidget(self.current_task_label)

        # Progress bar
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

        deck_label = QLabel("📚 Active Deck:")
        deck_label.setStyleSheet("font-size: 14px; color: #4ec9b0; font-weight: bold;")
        layout.addWidget(deck_label)

        self.deck_name_combo = QComboBox()
        self.deck_name_combo.setEditable(True)
        self.deck_name_combo.setMinimumWidth(250)
        self.deck_name_combo.setStyleSheet(
            """
            QComboBox {
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #555;
                padding: 3px 10px;
                border-radius: 3px;
            }
            QComboBox:hover {
                border: 1px solid #4ec9b0;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: white;
                selection-background-color: #4ec9b0;
            }
        """
        )

        # Load existing deck names
        self.update_deck_list()

        # Connect signals
        self.deck_name_combo.currentTextChanged.connect(self.on_deck_name_changed)
        layout.addWidget(self.deck_name_combo)

        # Time elapsed
        self.time_label = QLabel("")
        self.time_label.setStyleSheet("font-size: 12px; color: #969696;")
        layout.addWidget(self.time_label)

    def update_deck_list(self):
        """Update the list of available decks in the combo box"""
        if not hasattr(self, "deck_name_combo"):
            return
        self.deck_name_combo.clear()

        # Add existing deck folders
        saved_decks_dir = Path("saved_decks")
        if saved_decks_dir.exists():
            for deck_folder in saved_decks_dir.iterdir():
                if deck_folder.is_dir() and deck_folder.name.startswith("deck_"):
                    self.deck_name_combo.addItem(deck_folder.name)

        # Set current deck if it exists
        if self.current_deck_name:
            index = self.deck_name_combo.findText(self.current_deck_name)
            if index >= 0:
                self.deck_name_combo.setCurrentIndex(index)
            else:
                self.deck_name_combo.setCurrentText(self.current_deck_name)

    def on_deck_name_changed(self, new_name):
        """Handle deck name change"""
        if new_name and new_name != self.current_deck_name:
            # Clean the name
            clean_name = new_name.lower().replace(" ", "_")
            if not clean_name.startswith("deck_"):
                clean_name = f"deck_{clean_name}"

            self.current_deck_name = clean_name
            self.log_message("INFO", f"Active deck changed to: {clean_name}")

            # Create deck folder if it doesn't exist
            deck_dir = Path("saved_decks") / clean_name
            if not deck_dir.exists():
                deck_dir.mkdir(parents=True, exist_ok=True)
                (deck_dir / "rendered_cards").mkdir(exist_ok=True)
                (deck_dir / "artwork").mkdir(exist_ok=True)
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
            self.status_indicator.setText("🔴 Generating")
            self.status_indicator.setStyleSheet(
                "font-size: 16px; font-weight: bold; color: #f48771;"
            )
            self.current_task_label.setText(message)
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
        for item in self.generation_tab.queue_table.selectedItems():
            selected_rows.add(item.row())

        if selected_rows:
            row = min(selected_rows)  # Get first selected row
            if 0 <= row < len(self.generation_tab.cards):
                card = self.generation_tab.cards[row]
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

    def update_card_preview(self, card: MTGCard):
        """Update the card preview panel with the selected card"""
        self.current_preview_card = card

        # Update card name
        self.preview_name.setText(card.name)

        # Update card details
        self.preview_type.setText(f"Type: {card.type}")
        self.preview_cost.setText(f"Cost: {card.cost or '—'}")

        if card.power is not None and card.toughness is not None:
            self.preview_pt.setText(f"P/T: {card.power}/{card.toughness}")
        else:
            self.preview_pt.setText("P/T: —")

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
            self.preview_text.setText("Text: —")

        # Update flavor text
        if card.flavor:
            display_flavor = card.flavor
            if len(display_flavor) > 80:
                display_flavor = display_flavor[:80] + "..."
            self.preview_flavor.setText(f"Flavor: {display_flavor}")
        else:
            self.preview_flavor.setText("Flavor: —")

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
        if hasattr(self.generation_tab, "cards"):
            total = len([c for c in self.generation_tab.cards if c.status == "pending"])
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
        if hasattr(self.generation_tab, "cards"):
            # Find the card being processed
            current_card = None
            for card in self.generation_tab.cards:
                if str(card.id) == str(card_id):
                    current_card = card
                    break

            total = len(self.generation_tab.cards)
            completed = sum(
                1 for c in self.generation_tab.cards if c.status == "completed"
            )
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
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
