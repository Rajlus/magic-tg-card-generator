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
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

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
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
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
                    self.log_message.emit(
                        "INFO", f"Card-only regeneration mode for: {card.name}"
                    )
                    self.log_message.emit(
                        "DEBUG", f"Existing artwork path: {card.image_path}"
                    )

                    # If we have an image path, use --custom-image instead of generating new artwork
                    if card.image_path and Path(card.image_path).exists():
                        # Use --custom-image flag with the existing artwork
                        command += f" --custom-image {escape_for_shell(str(Path(card.image_path).absolute()))}"
                        self.log_message.emit(
                            "DEBUG",
                            f"Using existing artwork with --custom-image: {card.image_path}",
                        )
                    else:
                        # If no existing image, still skip image generation (will use placeholder)
                        command += " --skip-image"
                        self.log_message.emit(
                            "WARNING",
                            "No existing artwork found for card-only regeneration",
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
                            if "" in line or "SUCCESS" in line:
                                self.log_message.emit("SUCCESS", line)
                            elif "" in line or "ERROR" in line or "Failed" in line:
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
                            elif "" in line or "WARNING" in line:
                                self.log_message.emit("WARNING", line)
                            elif "" in line or "Generating" in line:
                                self.log_message.emit("GENERATING", line)
                            elif "INFO" in line or "" in line or "" in line:
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
                        # Get the most recently created PNG file in the directory
                        # This is more reliable than pattern matching for custom images
                        recent_files = sorted(
                            cards_dir.glob("*.png"),
                            key=lambda p: p.stat().st_mtime,
                            reverse=True,
                        )

                        if recent_files:
                            # Check if the most recent file was created within last 10 seconds
                            import time

                            current_time = time.time()
                            for recent_file in recent_files[
                                :3
                            ]:  # Check the 3 most recent files
                                file_mtime = recent_file.stat().st_mtime
                                if (
                                    current_time - file_mtime < 10
                                ):  # Created within last 10 seconds
                                    default_card_path = recent_file
                                    self.log_message.emit(
                                        "INFO",
                                        f"Found recently generated card at: {default_card_path}",
                                    )
                                    break

                        # If not found by recency, try pattern matching
                        if not default_card_path:
                            # First try with normal safe name
                            normal_safe_name = card.name.replace(" ", "_").replace(
                                "/", "_"
                            )
                            pattern = f"{normal_safe_name}_*.png"
                            matching_files = list(cards_dir.glob(pattern))

                            # If not found, try with the heavily escaped safe name
                            if not matching_files:
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

                    # Use the actual generated file paths
                    card_path = ""
                    image_path = ""

                    if default_card_path and default_card_path.exists():
                        # For custom images, keep the original filename from generation
                        # Don't rename to safe_name as it may not match
                        if self.style == "custom_image":
                            final_path = default_card_path
                        else:
                            # Target path without timestamp for non-custom images
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
                                            "ERROR", " Creature missing P/T values!"
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

                            # For custom images, just use the path as-is
                            # For other images, rename to remove timestamp
                            if (
                                self.style == "custom_image"
                                or final_path == default_card_path
                            ):
                                # Don't move/rename for custom images
                                card_path = str(default_card_path)
                            else:
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

                    # Set image_path from artwork if found
                    if default_art_path and default_art_path.exists():
                        image_path = str(default_art_path)

                    # Log the successful generation with file paths
                    # Make sure we have absolute paths
                    if card_path and not Path(card_path).is_absolute():
                        card_path = str(Path(card_path).resolve())
                    if image_path and not Path(image_path).is_absolute():
                        image_path = str(Path(image_path).resolve())

                    # Debug: log what we're emitting
                    self.log_message.emit(
                        "DEBUG",
                        f"Emitting completed signal for card {card.name} with ID: {card.id}",
                    )
                    self.log_message.emit("DEBUG", f"Card path: {card_path}")
                    self.log_message.emit("DEBUG", f"Image path: {image_path}")
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

        self.init_ui()

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
        self.filter_combo.currentTextChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.filter_combo)

        # Add status filter
        filter_layout.addWidget(QLabel("Status:"))
        self.status_filter_combo = QComboBox()
        self.status_filter_combo.addItems(
            ["All", "✅ Completed", "⏸️ Pending", "❌ Failed", "🔄 Generating"]
        )
        self.status_filter_combo.currentTextChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.status_filter_combo)

        filter_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.textChanged.connect(self.apply_filter)
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

        # Connect itemChanged signal to auto-save when cells are edited
        self.table.itemChanged.connect(self.on_table_item_changed)

        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        # Add context menu for right-click
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        # Connect selection change to update button visibility
        self.table.itemSelectionChanged.connect(self.update_button_visibility)

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
            with contextlib.suppress(ValueError):
                card.id = int(new_value)
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

    def load_deck(self):
        """Open file dialog to load a deck"""
        self.load_deck_file()

    def reload_current_deck(self):
        """Reload the currently loaded deck from file without dialog"""
        parent = get_main_window()
        if (
            parent
            and hasattr(parent, "last_loaded_deck_path")
            and parent.last_loaded_deck_path
        ):
            deck_path = parent.last_loaded_deck_path
            if Path(deck_path).exists():
                # Log the reload action
                if parent and hasattr(parent, "log_message"):
                    parent.log_message(
                        "INFO", f"🔄 Reloading deck: {Path(deck_path).name}"
                    )

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

                # Load the deck file
                self.load_deck_file(deck_path)

                # Restore selection if we had one, otherwise select commander
                if selected_row >= 0 and selected_row < self.table.rowCount():
                    self.table.selectRow(selected_row)
                elif self.table.rowCount() > 0:
                    # Select commander if no previous selection
                    self.table.selectRow(0)
                    selected_row = 0

                # Re-enable auto-save after a short delay
                from PyQt6.QtCore import QTimer

                QTimer.singleShot(1000, lambda: self._restore_auto_save(old_auto_save))

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
            else:
                QMessageBox.warning(
                    self, "File Not Found", f"Deck file not found: {deck_path}"
                )
        else:
            QMessageBox.information(
                self, "No Deck Loaded", "Please load a deck first before reloading."
            )

    def _restore_auto_save(self, old_text):
        """Restore auto-save indicator after reload"""
        self.auto_save_label.setText(old_text)
        self.auto_save_label.setStyleSheet(
            "color: #4ec9b0; font-weight: bold; padding: 5px;"
        )

    def load_deck_file(self, filename=None):
        """Load a deck from a YAML file"""
        if filename is None:
            filename, _ = QFileDialog.getOpenFileName(
                self, "Load Deck", "saved_decks/", "YAML Files (*.yaml);;All Files (*)"
            )

        if filename:
            try:
                import yaml

                with open(filename) as f:
                    deck_data = yaml.safe_load(f)

                # Convert to MTGCard objects
                cards = []

                # Handle both old format (with separate commander) and new format (all in cards)
                if "commander" in deck_data:
                    # Old format with separate commander
                    cmd_data = deck_data["commander"]
                    commander = MTGCard(
                        id=cmd_data.get("id", 1),
                        name=cmd_data.get("name", "Unknown Commander"),
                        type=cmd_data.get("type", "Legendary Creature"),
                    )
                    # Set other attributes but skip status initially
                    for key, value in cmd_data.items():
                        if key not in ["id", "name", "type", "status"]:
                            setattr(commander, key, value)
                    cards.append(commander)

                # Add other cards
                if "cards" in deck_data:
                    for i, card_data in enumerate(deck_data["cards"], start=2):
                        card = MTGCard(
                            id=card_data.get("id", i),
                            name=card_data.get("name", f"Card {i}"),
                            type=card_data.get("type", "Unknown"),
                        )
                        # Set other attributes but skip status initially
                        # Status will be determined by sync_card_status_with_rendered_files
                        for key, value in card_data.items():
                            if key not in ["id", "name", "type", "status"]:
                                setattr(card, key, value)
                        # Don't set status from YAML, let it be determined by actual files
                        # This prevents status from one deck affecting another
                        cards.append(card)

                # Update deck name BEFORE loading cards (for status sync)
                parent = get_main_window()
                if parent:
                    from pathlib import Path

                    try:
                        deck_name = Path(filename).stem
                        parent.current_deck_name = deck_name
                        parent.last_loaded_deck_path = filename

                        # Update deck name display
                        if hasattr(parent, "update_deck_display"):
                            parent.update_deck_display()

                        # Update file watcher to watch this deck file
                        if hasattr(parent, "file_watcher"):
                            # Remove old file from watcher
                            if (
                                hasattr(parent, "watching_file")
                                and parent.watching_file
                            ):
                                parent.file_watcher.removePath(parent.watching_file)

                            # Add new file to watcher
                            parent.file_watcher.addPath(filename)
                            parent.watching_file = filename
                            parent.log_message(
                                "DEBUG",
                                f"Now watching deck file for changes: {Path(filename).name}",
                            )
                    except ValueError as ve:
                        # Handle Path errors separately
                        print(f"Path error: {ve}")

                # NOW load the cards after deck name is set
                self.load_cards(cards)

                # Select and preview the commander (first card)
                if len(cards) > 0:
                    # Select first row in table
                    self.table.selectRow(0)
                    # Update preview with commander
                    if parent and hasattr(parent, "update_card_preview"):
                        parent.update_card_preview(cards[0])
                        if parent and hasattr(parent, "log_message"):
                            parent.log_message(
                                "DEBUG", f"Auto-selected commander: {cards[0].name}"
                            )
                else:
                    # Clear the preview if no cards
                    if parent and hasattr(parent, "clear_card_preview"):
                        parent.clear_card_preview()

                # Log success message
                if (
                    parent
                    and hasattr(parent, "log_message")
                    and hasattr(parent, "current_deck_name")
                ):
                    parent.log_message(
                        "INFO",
                        f"Loaded deck: {parent.current_deck_name} ({len(cards)} cards)",
                    )
            except yaml.YAMLError as ye:
                QMessageBox.critical(
                    self, "Load Failed", f"YAML parsing error: {str(ye)}"
                )
            except Exception as e:
                import traceback

                print(f"Load error: {traceback.format_exc()}")
                QMessageBox.critical(
                    self, "Load Failed", f"Failed to load deck: {str(e)}"
                )

    def manual_sync_status(self):
        """Manually reset and sync card status with rendered files"""
        parent = get_main_window()

        # Reset ALL cards to pending first
        for card in self.cards:
            card.status = "pending"

        # Log the reset
        if parent and hasattr(parent, "log_message"):
            parent.log_message("INFO", "🔄 Resetting all card status to pending...")

        # Now sync with actual rendered files
        self.sync_card_status_with_rendered_files()

        # Refresh the display
        self.refresh_table()
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
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

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
        csv_file, _ = QFileDialog.getOpenFileName(
            self, "Import CSV Deck", "", "CSV Files (*.csv);;All Files (*)"
        )

        if csv_file:
            try:
                import csv
                from pathlib import Path

                cards = []
                with open(csv_file, encoding="utf-8") as f:
                    reader = csv.DictReader(f, delimiter=";")
                    for i, row in enumerate(reader, start=1):
                        card = MTGCard(
                            id=int(row.get("ID", i)),
                            name=row.get("Name", f"Card {i}"),
                            type=row.get("Type", "Unknown"),
                        )
                        # Set other attributes
                        card.cost = row.get("Cost", "")
                        card.text = row.get("Text", "")
                        card.power = (
                            int(row["Power"])
                            if row.get("Power") and row["Power"].isdigit()
                            else None
                        )
                        card.toughness = (
                            int(row["Toughness"])
                            if row.get("Toughness") and row["Toughness"].isdigit()
                            else None
                        )
                        card.flavor = row.get("Flavor", "")
                        card.rarity = row.get("Rarity", "common")
                        card.art = row.get("Art", "")
                        card.status = row.get("Status", "pending")
                        cards.append(card)

                if cards:
                    self.load_cards(cards)
                    parent = get_main_window()
                    if parent and hasattr(parent, "log_message"):
                        parent.log_message(
                            "SUCCESS", f"✅ Imported {len(cards)} cards from CSV"
                        )
                    QMessageBox.information(
                        self,
                        "Import Success",
                        f"Successfully imported {len(cards)} cards from CSV",
                    )
                else:
                    QMessageBox.warning(self, "No Cards", "No cards found in CSV file")

            except Exception as e:
                QMessageBox.critical(
                    self, "Import Failed", f"Failed to import CSV:\n{str(e)}"
                )
                parent = get_main_window()
                if parent and hasattr(parent, "log_message"):
                    parent.log_message("ERROR", f"❌ CSV import failed: {str(e)}")

    def export_csv(self):
        """Export current deck to CSV file"""
        if not self.cards:
            QMessageBox.warning(self, "No Deck", "Please load a deck first!")
            return

        from pathlib import Path

        # Get deck name and create default path in deck folder
        parent = get_main_window()
        default_path = "deck_export.csv"
        if parent and hasattr(parent, "current_deck_name"):
            # Use the deck's own folder in saved_decks
            deck_folder = Path("saved_decks") / parent.current_deck_name
            deck_folder.mkdir(parents=True, exist_ok=True)  # Ensure folder exists
            default_path = str(deck_folder / f"{parent.current_deck_name}.csv")

        # Ask user for CSV save location (with deck folder as default)
        csv_file, _ = QFileDialog.getSaveFileName(
            self, "Export Deck to CSV", default_path, "CSV Files (*.csv);;All Files (*)"
        )

        if csv_file:
            try:
                import csv

                # Write CSV with semicolon delimiter for better Excel compatibility
                with open(csv_file, "w", newline="", encoding="utf-8") as f:
                    fieldnames = [
                        "ID",
                        "Name",
                        "Type",
                        "Cost",
                        "Power",
                        "Toughness",
                        "Text",
                        "Flavor",
                        "Rarity",
                        "Art",
                        "Status",
                    ]
                    writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")

                    # Write header
                    writer.writeheader()

                    # Write cards
                    for card in self.cards:
                        writer.writerow(
                            {
                                "ID": card.id,
                                "Name": card.name,
                                "Type": card.type,
                                "Cost": card.cost if card.cost else "",
                                "Power": card.power if card.power else "",
                                "Toughness": card.toughness if card.toughness else "",
                                "Text": card.text if card.text else "",
                                "Flavor": card.flavor if card.flavor else "",
                                "Rarity": card.rarity if card.rarity else "",
                                "Art": card.art if card.art else "",
                                "Status": card.status
                                if hasattr(card, "status")
                                else "pending",
                            }
                        )

                # Log success
                if parent and hasattr(parent, "log_message"):
                    parent.log_message(
                        "SUCCESS",
                        f"✅ Exported {len(self.cards)} cards to CSV: {Path(csv_file).name}",
                    )

                QMessageBox.information(
                    self,
                    "Export Success",
                    f"Successfully exported {len(self.cards)} cards to:\n{Path(csv_file).name}",
                )

            except Exception as e:
                QMessageBox.critical(
                    self, "Export Failed", f"Failed to export CSV:\n{str(e)}"
                )
                if parent and hasattr(parent, "log_message"):
                    parent.log_message("ERROR", f"❌ CSV export failed: {str(e)}")

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
            self.refresh_table()
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
            self.refresh_table()

    def delete_selected_cards(self):
        """Delete selected cards from the deck"""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

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

            self.refresh_table()
            self.update_stats()
            self.update_generation_stats()

    def edit_card(self):
        """Edit selected card details including art description"""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

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

                self.refresh_table()

    def edit_selected_art_prompt(self):
        """Edit art prompt for selected card"""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

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
        """Generate only cards that haven't been generated yet"""
        missing_cards = [
            card
            for card in self.cards
            if not hasattr(card, "status") or card.status == "pending"
        ]

        if not missing_cards:
            QMessageBox.information(
                self, "All Complete", "All cards have been generated!"
            )
            return

        if hasattr(self, "generator_worker"):
            self.generator_worker.set_cards(
                missing_cards,
                self.model_combo.currentText()
                if hasattr(self, "model_combo")
                else "sdxl",
                self.style_combo.currentText()
                if hasattr(self, "style_combo")
                else "mtg_modern",
            )
            self.generator_worker.start()

            parent = get_main_window()
            if parent and hasattr(parent, "log_message"):
                parent.log_message(
                    "INFO", f"Generating {len(missing_cards)} missing cards"
                )

    def generate_art_descriptions(self):
        """Generate art descriptions for cards using AI"""
        if not self.cards:
            QMessageBox.warning(self, "No Cards", "No cards to generate art for!")
            return

        parent = get_main_window()
        if parent and hasattr(parent, "deck_builder_tab"):
            theme = getattr(parent.deck_builder_tab, "current_theme", "Fantasy")

            cards_needing_art = [
                card
                for card in self.cards
                if not hasattr(card, "art_prompt") or not card.art_prompt
            ]

            if not cards_needing_art:
                QMessageBox.information(
                    self, "Complete", "All cards have art descriptions!"
                )

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
        """Regenerate selected cards with new images"""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            QMessageBox.warning(
                self, "No Selection", "Please select cards to regenerate!"
            )
            return

        cards_to_regenerate = []
        for row in selected_rows:
            if 0 <= row < len(self.cards):
                card = self.cards[row]
                card.status = "pending"
                cards_to_regenerate.append(card)

        if cards_to_regenerate:
            self.refresh_generation_queue()

            # Start generation with new images
            self.generator_worker.set_cards(
                cards_to_regenerate,
                self.model_combo.currentText(),
                self.style_combo.currentText(),
                "regeneration_with_image",
            )
            self.generator_worker.start()

            parent = get_main_window()
            if parent and hasattr(parent, "log_message"):
                parent.log_message(
                    "INFO",
                    f"Regenerating {len(cards_to_regenerate)} cards with new images",
                )

    def regenerate_selected_card_only(self):
        """Regenerate selected cards using existing artwork"""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            QMessageBox.warning(
                self, "No Selection", "Please select cards to regenerate!"
            )
            return

        cards_to_regenerate = []
        for row in selected_rows:
            if 0 <= row < len(self.cards):
                card = self.cards[row]

                # Check if artwork exists
                safe_name = make_safe_filename(card.name)
                artwork_found = False

                # Get current deck name for deck-specific paths
                parent = get_main_window()
                deck_name = None
                if parent and hasattr(parent, "current_deck_name"):
                    deck_name = parent.current_deck_name

                # Check deck-specific artwork directory FIRST (for custom images)
                if deck_name:
                    artwork_dir = Path("saved_decks") / deck_name / "artwork"
                    if artwork_dir.exists():
                        # Check for artwork with various extensions
                        for ext in [".jpg", ".jpeg", ".png"]:
                            artwork_path = artwork_dir / f"{safe_name}{ext}"
                            if artwork_path.exists():
                                artwork_found = True
                                # UPDATE the card's image_path with the found artwork
                                card.image_path = str(artwork_path)
                                if parent and hasattr(parent, "log_message"):
                                    parent.log_message(
                                        "DEBUG", f"Found artwork at: {artwork_path}"
                                    )
                                    parent.log_message(
                                        "DEBUG",
                                        f"Updated card.image_path to: {card.image_path}",
                                    )
                                break

                # If not found, check image_path (might be custom image path)
                if (
                    not artwork_found
                    and hasattr(card, "image_path")
                    and card.image_path
                ):
                    if Path(card.image_path).exists():
                        artwork_found = True
                        # Already has correct path
                        if parent and hasattr(parent, "log_message"):
                            parent.log_message(
                                "DEBUG",
                                f"Found artwork at image_path: {card.image_path}",
                            )

                # Finally check old output/images location as fallback
                if not artwork_found:
                    for ext in [".jpg", ".jpeg", ".png"]:
                        artwork_path = Path(f"output/images/{safe_name}{ext}")
                        if artwork_path.exists():
                            artwork_found = True
                            # UPDATE the card's image_path with the found artwork
                            card.image_path = str(artwork_path)
                            if parent and hasattr(parent, "log_message"):
                                parent.log_message(
                                    "DEBUG",
                                    f"Found artwork at output/images: {artwork_path}",
                                )
                                parent.log_message(
                                    "DEBUG",
                                    f"Updated card.image_path to: {card.image_path}",
                                )
                            break

                if not artwork_found:
                    reply = QMessageBox.question(
                        self,
                        "No Artwork",
                        f"No artwork found for '{card.name}'. Generate with new artwork instead?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        card.status = "pending"
                        cards_to_regenerate.append(card)
                else:
                    card.status = "pending"
                    cards_to_regenerate.append(card)

        if cards_to_regenerate:
            self.refresh_generation_queue()

            # Start card-only regeneration
            self.generator_worker.set_cards(
                cards_to_regenerate,
                self.model_combo.currentText(),
                self.style_combo.currentText(),
                "card_only_regeneration",
            )
            self.generator_worker.start()

            parent = get_main_window()
            if parent and hasattr(parent, "log_message"):
                parent.log_message(
                    "INFO",
                    f"Regenerating {len(cards_to_regenerate)} cards (keeping artwork)",
                )

    def use_custom_image_for_selected(self):
        """Use custom image for selected cards"""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

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
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

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
            self.refresh_table()  # Also refresh the main table

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
        self.commander_colors = self.get_commander_colors()

        # ALWAYS reset ALL card status to pending first
        # This ensures clean state when switching decks
        for card in self.cards:
            card.status = "pending"

        # Now synchronize card status with existing rendered cards
        # This will only update to 'completed' if files actually exist for THIS deck
        self.sync_card_status_with_rendered_files()

        # Log all cards with color violations
        self.log_color_violations()

        self.refresh_table()
        self.update_stats()
        self.update_generation_stats()

    def sync_card_status_with_rendered_files(self):
        """Synchronize card status based on existing rendered files"""
        parent = get_main_window()
        if not parent or not hasattr(parent, "current_deck_name"):
            return

        deck_name = parent.current_deck_name
        if not deck_name:
            return

        # Check for rendered cards directory
        from pathlib import Path

        rendered_dir = Path("saved_decks") / deck_name / "rendered_cards"

        if not rendered_dir.exists():
            return

        # Get list of rendered cards
        rendered_files = set()
        for file_path in rendered_dir.glob("*.png"):
            rendered_files.add(file_path.stem)  # Get filename without extension

        # Update card status based on rendered files
        updated_count = 0
        for card in self.cards:
            safe_name = make_safe_filename(card.name)
            if safe_name in rendered_files:
                if not hasattr(card, "status") or card.status != "completed":
                    card.status = "completed"
                    updated_count += 1
            elif not hasattr(card, "status"):
                card.status = "pending"

        if updated_count > 0 and parent and hasattr(parent, "log_message"):
            parent.log_message(
                "INFO",
                f"📊 Synchronized status for {updated_count} cards based on existing rendered files",
            )

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
                main_window.log_message("WARNING", f"   {violation}")
            main_window.log_message(
                "INFO", f"Commander colors allowed: {self.commander_colors}"
            )

    def refresh_table(self):
        """Refresh table display with color validation"""
        # Temporarily disconnect itemChanged signal to avoid triggering saves during refresh
        with contextlib.suppress(Exception):
            self.table.itemChanged.disconnect()

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
                    f" Color violation! Contains colors not in commander identity: {self.commander_colors}"
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

            # Generation Status column (8)
            gen_status = getattr(card, "status", "pending")
            if gen_status == "completed":
                status_text = "✅ Done"
                status_item = QTableWidgetItem(status_text)
                if violates_colors:
                    status_item.setBackground(
                        QBrush(QColor(200, 150, 150))
                    )  # Red-tinted green
                else:
                    status_item.setBackground(QBrush(QColor(100, 200, 100)))  # Green
            elif gen_status == "generating":
                status_text = "⏳ Processing"
                status_item = QTableWidgetItem(status_text)
                if violates_colors:
                    status_item.setBackground(
                        QBrush(QColor(255, 150, 100))
                    )  # Red-tinted yellow
                else:
                    status_item.setBackground(QBrush(QColor(200, 200, 100)))  # Yellow
            elif gen_status == "failed":
                status_text = "❌ Failed"
                status_item = QTableWidgetItem(status_text)
                status_item.setBackground(QBrush(QColor(200, 100, 100)))  # Red
            else:  # pending
                status_text = "⏸️ Pending"
                status_item = QTableWidgetItem(status_text)
                if violates_colors:
                    status_item.setBackground(
                        QBrush(QColor(255, 200, 200))
                    )  # Light red
                else:
                    status_item.setBackground(
                        QBrush(QColor(220, 220, 220))
                    )  # Light gray
            self.table.setItem(row, 8, status_item)

            # Image Status column (9)
            has_image = (
                hasattr(card, "card_path")
                and card.card_path
                and Path(card.card_path).exists()
            ) or (
                hasattr(card, "image_path")
                and card.image_path
                and Path(card.image_path).exists()
            )

            image_text = "🖼️ Yes" if has_image else "❌ No"
            image_item = QTableWidgetItem(image_text)
            if violates_colors:
                image_item.setBackground(QBrush(QColor(255, 200, 200)))  # Light red
            self.table.setItem(row, 9, image_item)

        # Keep sorting disabled
        self.table.setSortingEnabled(False)

        # Reconnect itemChanged signal for auto-save
        self.table.itemChanged.connect(self.on_table_item_changed)

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

    def apply_filter(self):
        """Apply filter to table"""
        filter_text = self.filter_combo.currentText()
        status_filter = (
            self.status_filter_combo.currentText()
            if hasattr(self, "status_filter_combo")
            else "All"
        )
        search_text = self.search_input.text().lower()

        visible_count = 0
        total_count = self.table.rowCount()

        for row in range(total_count):
            show = True

            # Type filter - check both English and German terms
            if filter_text != "All":
                card_type = self.table.item(row, 3).text().lower()
                if (  # noqa: SIM114
                    filter_text == "Creatures"
                    and "kreatur" not in card_type
                    and "creature" not in card_type
                ):
                    show = False
                elif filter_text == "Lands" and "land" not in card_type:  # noqa: SIM114
                    show = False
                elif (  # noqa: SIM114
                    filter_text == "Instants"
                    and "spontanzauber" not in card_type
                    and "instant" not in card_type
                ):
                    show = False
                elif (  # noqa: SIM114
                    filter_text == "Sorceries"
                    and "hexerei" not in card_type
                    and "sorcery" not in card_type
                ):
                    show = False
                elif (  # noqa: SIM114
                    filter_text == "Artifacts"
                    and "artefakt" not in card_type
                    and "artifact" not in card_type
                ):
                    show = False
                elif (  # noqa: SIM114
                    filter_text == "Enchantments"
                    and "verzauberung" not in card_type
                    and "enchantment" not in card_type
                ):
                    show = False

            # Status filter
            if show and status_filter != "All":
                status_item = self.table.item(row, 8)  # Gen. Status column
                if status_item:
                    status_text = status_item.text().lower()
                    if (
                        status_filter == "✅ Completed" and "done" not in status_text
                    ):  # noqa: SIM114
                        show = False
                    elif (
                        status_filter == "⏸️ Pending" and "pending" not in status_text
                    ):  # noqa: SIM114
                        show = False
                    elif (
                        status_filter == "❌ Failed" and "failed" not in status_text
                    ):  # noqa: SIM114
                        show = False
                    elif (  # noqa: SIM114
                        status_filter == "🔄 Generating"
                        and "generating" not in status_text
                    ):
                        show = False

            # Search filter - search in ALL columns
            if show and search_text:
                found = False
                # Check all columns for the search text
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item and search_text in item.text().lower():
                        found = True
                        break

                # If not found in any column, hide the row
                if not found:
                    show = False

            self.table.setRowHidden(row, not show)
            if show:
                visible_count += 1

        # Update filter result label
        if filter_text != "All" or status_filter != "All" or search_text:
            # Filters are active - show the label
            hidden_count = total_count - visible_count
            self.filter_result_label.setText(
                f"📊 {visible_count}/{total_count} Cards - {hidden_count} Hidden"
            )
            self.filter_result_label.setVisible(True)
        else:
            # No filters active - hide the label
            self.filter_result_label.setVisible(False)

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
        add_action = menu.addAction(" Add New Card")
        edit_action = menu.addAction(" Edit Card")
        duplicate_action = menu.addAction(" Duplicate Card")
        menu.addSeparator()
        delete_action = menu.addAction(" Delete Card(s)")
        menu.addSeparator()
        regenerate_action = menu.addAction(" Regenerate Card")

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
        """Regenerate selected cards with new images"""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            QMessageBox.warning(
                self, "No Selection", "Please select cards to regenerate!"
            )
            return

        cards_to_regenerate = []
        for row in selected_rows:
            if 0 <= row < len(self.cards):
                card = self.cards[row]
                card.status = "pending"
                cards_to_regenerate.append(card)

        if cards_to_regenerate:
            self.refresh_generation_queue()

            # Start generation with new images
            self.generator_worker.set_cards(
                cards_to_regenerate,
                self.model_combo.currentText(),
                self.style_combo.currentText(),
                "regeneration_with_image",
            )
            self.generator_worker.start()

            parent = get_main_window()
            if parent and hasattr(parent, "log_message"):
                parent.log_message(
                    "INFO",
                    f"Regenerating {len(cards_to_regenerate)} cards with new images",
                )

    def regenerate_selected_card_only(self):
        """Regenerate selected cards using existing artwork"""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            QMessageBox.warning(
                self, "No Selection", "Please select cards to regenerate!"
            )
            return

        cards_to_regenerate = []
        for row in selected_rows:
            if 0 <= row < len(self.cards):
                card = self.cards[row]

                # Check if artwork exists
                safe_name = make_safe_filename(card.name)
                artwork_found = False

                # Get current deck name for deck-specific paths
                parent = get_main_window()
                deck_name = None
                if parent and hasattr(parent, "current_deck_name"):
                    deck_name = parent.current_deck_name

                # Check deck-specific artwork directory FIRST (for custom images)
                if deck_name:
                    artwork_dir = Path("saved_decks") / deck_name / "artwork"
                    if artwork_dir.exists():
                        # Check for artwork with various extensions
                        for ext in [".jpg", ".jpeg", ".png"]:
                            artwork_path = artwork_dir / f"{safe_name}{ext}"
                            if artwork_path.exists():
                                artwork_found = True
                                # UPDATE the card's image_path with the found artwork
                                card.image_path = str(artwork_path)
                                if parent and hasattr(parent, "log_message"):
                                    parent.log_message(
                                        "DEBUG", f"Found artwork at: {artwork_path}"
                                    )
                                    parent.log_message(
                                        "DEBUG",
                                        f"Updated card.image_path to: {card.image_path}",
                                    )
                                break

                # If not found, check image_path (might be custom image path)
                if (
                    not artwork_found
                    and hasattr(card, "image_path")
                    and card.image_path
                ):
                    if Path(card.image_path).exists():
                        artwork_found = True
                        # Already has correct path
                        if parent and hasattr(parent, "log_message"):
                            parent.log_message(
                                "DEBUG",
                                f"Found artwork at image_path: {card.image_path}",
                            )

                # Finally check old output/images location as fallback
                if not artwork_found:
                    for ext in [".jpg", ".jpeg", ".png"]:
                        artwork_path = Path(f"output/images/{safe_name}{ext}")
                        if artwork_path.exists():
                            artwork_found = True
                            # UPDATE the card's image_path with the found artwork
                            card.image_path = str(artwork_path)
                            if parent and hasattr(parent, "log_message"):
                                parent.log_message(
                                    "DEBUG",
                                    f"Found artwork at output/images: {artwork_path}",
                                )
                                parent.log_message(
                                    "DEBUG",
                                    f"Updated card.image_path to: {card.image_path}",
                                )
                            break

                if not artwork_found:
                    reply = QMessageBox.question(
                        self,
                        "No Artwork",
                        f"No artwork found for '{card.name}'. Generate with new artwork instead?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        card.status = "pending"
                        cards_to_regenerate.append(card)
                else:
                    card.status = "pending"
                    cards_to_regenerate.append(card)

        if cards_to_regenerate:
            self.refresh_generation_queue()

            # Start card-only regeneration
            self.generator_worker.set_cards(
                cards_to_regenerate,
                self.model_combo.currentText(),
                self.style_combo.currentText(),
                "card_only_regeneration",
            )
            self.generator_worker.start()

            parent = get_main_window()
            if parent and hasattr(parent, "log_message"):
                parent.log_message(
                    "INFO",
                    f"Regenerating {len(cards_to_regenerate)} cards (keeping artwork)",
                )

    def use_custom_image_for_selected(self):
        """Use custom image for selected cards"""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

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
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

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
            self.refresh_table()  # Also refresh the main table

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
        self.refresh_table()  # Call existing refresh_table method

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
            self.refresh_table()
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
        self.refresh_table()
        self.update_button_visibility()  # Update button visibility after refresh
        self.update_generation_stats()  # Update generation progress indicator
        # Re-apply filters after updating the table
        self.apply_filter()

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
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

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


# class GenerationTab(QWidget):
#     """Tab 3: Image & Card Generation with Enhanced Controls"""
#    def __init__(self):
#        super().__init__()
#        self.cards = []
#        self.generator_worker = CardGeneratorWorker()
#        self.generator_worker.progress.connect(self.on_generation_progress)
#        self.generator_worker.completed.connect(self.on_generation_completed)
#        self.init_ui()

#    def init_ui(self):
#        main_layout = QVBoxLayout()

# Top Section: Generation Settings & Stats
#        top_section = QWidget()
#        top_layout = QVBoxLayout()

# Generation settings in a more compact layout
#        settings_group = QGroupBox(" Generation Settings")
#        settings_layout = QGridLayout()

# Row 1: Model and Style
#        settings_layout.addWidget(QLabel("Model:"), 0, 0)
#        self.model_combo = QComboBox()
#        self.model_combo.addItems(["sdxl", "sdxl-lightning", "flux-schnell", "flux-dev"])
#        self.model_combo.setToolTip("Select the AI model for image generation")
#        settings_layout.addWidget(self.model_combo, 0, 1)

#        settings_layout.addWidget(QLabel("Style:"), 0, 2)
#        self.style_combo = QComboBox()
#        self.style_combo.addItems(["mtg_modern", "mtg_classic", "realistic", "anime", "oil_painting"])
#        self.style_combo.setToolTip("Select the art style for cards")
#        settings_layout.addWidget(self.style_combo, 0, 3)

# Row 2: Statistics
#        self.stats_label = QLabel(" Status: Ready")
#        settings_layout.addWidget(self.stats_label, 1, 0, 1, 2)

#        self.progress_bar = QProgressBar()
#        self.progress_bar.setTextVisible(True)
#        settings_layout.addWidget(self.progress_bar, 1, 2, 1, 2)

#        settings_layout.setColumnStretch(4, 1)  # Add stretch to the right
#        settings_group.setLayout(settings_layout)
#        top_layout.addWidget(settings_group)

#        top_section.setLayout(top_layout)
#        main_layout.addWidget(top_section)

# Middle Section: Card Queue with Enhanced Controls
#        queue_section = QWidget()
#        queue_layout = QVBoxLayout()

# Queue header with filter controls
#        queue_header = QWidget()
#        header_layout = QHBoxLayout()

#        header_layout.addWidget(QLabel(" Card Queue"))

# Filter buttons
#        self.filter_all_btn = QPushButton("All")
#        self.filter_pending_btn = QPushButton("Pending")
#        self.filter_completed_btn = QPushButton("Completed")
#        self.filter_failed_btn = QPushButton("Failed")

#        for btn in [self.filter_all_btn, self.filter_pending_btn, self.filter_completed_btn, self.filter_failed_btn]:
#            btn.setCheckable(True)
#            btn.setMaximumWidth(80)
#            btn.clicked.connect(self.apply_filter)

#        self.filter_all_btn.setChecked(True)

#        header_layout.addWidget(self.filter_all_btn)
#        header_layout.addWidget(self.filter_pending_btn)
#        header_layout.addWidget(self.filter_completed_btn)
#        header_layout.addWidget(self.filter_failed_btn)

#        header_layout.addStretch()

# Search box
#        self.search_box = QLineEdit()
#        self.search_box.setPlaceholderText(" Search cards...")
#        self.search_box.setMaximumWidth(200)
#        self.search_box.textChanged.connect(self.apply_filter)
#        header_layout.addWidget(self.search_box)

# Generate All Pending button (moved to top right)
#        self.generate_all_btn = QPushButton(" Generate All Pending")
#        self.generate_all_btn.setStyleSheet("QPushButton { font-weight: bold; padding: 8px; }")
#        self.generate_all_btn.clicked.connect(self.generate_all)
#        header_layout.addWidget(self.generate_all_btn)

#        queue_header.setLayout(header_layout)
#        queue_layout.addWidget(queue_header)

# Queue table without action buttons
#        self.table = QTableWidget()
#        #        #            "ID", "Name", "Type", "Set", "Status", "Time"
#        ])

# Set column widths
#        header = #        header.resizeSection(0, 50)   # ID
#        header.resizeSection(1, 300)  # Name - slightly less space to fit Set
#        header.resizeSection(2, 150)  # Type
#        header.resizeSection(3, 80)   # Set
#        header.resizeSection(4, 120)  # Status
#        header.resizeSection(5, 100)  # Time

#        #
# Set minimum row height to accommodate buttons
#
#        queue_layout.addWidget(self.table)

#        queue_section.setLayout(queue_layout)
#        main_layout.addWidget(queue_section)

# Bottom Section: Control Panel
#        control_panel = QWidget()
#        control_panel.setMaximumHeight(100)
#        control_layout = QVBoxLayout()

# Row 1: Main generation controls (dynamic based on selection)
#        main_controls = QHBoxLayout()

# These buttons will be shown/hidden based on selected card status
#        self.generate_selected_btn = QPushButton(" Generate Selected")
#        self.generate_selected_btn.setVisible(False)  # Hidden by default
#        main_controls.addWidget(self.generate_selected_btn)

# Regeneration options (only shown for completed cards)
#        self.regen_with_image_btn = QPushButton(" Regenerate with New Image")
#        self.regen_with_image_btn.setToolTip("Regenerate selected card with new artwork")
#        self.regen_with_image_btn.setVisible(False)  # Hidden by default
#        main_controls.addWidget(self.regen_with_image_btn)

#        self.regen_card_only_btn = QPushButton(" Regenerate Card Only")
#        self.regen_card_only_btn.setToolTip("Regenerate card using existing artwork")
#        self.regen_card_only_btn.setVisible(False)  # Hidden by default
#        main_controls.addWidget(self.regen_card_only_btn)

# Custom image option
#        self.use_custom_image_btn = QPushButton(" Use Custom Image")
#        self.use_custom_image_btn.setToolTip("Select your own image as artwork for selected cards")
#        self.use_custom_image_btn.setVisible(False)  # Hidden by default
#        main_controls.addWidget(self.use_custom_image_btn)

# Delete (only shown for completed cards)
#        self.delete_files_btn = QPushButton(" Delete Files")
#        self.delete_files_btn.setVisible(False)  # Hidden by default
#        main_controls.addWidget(self.delete_files_btn)

#        main_controls.addStretch()

#        control_layout.addLayout(main_controls)

# Row 2: Current status
#        status_layout = QHBoxLayout()
#        self.current_card_label = QLabel(" Ready to generate cards")
#        self.current_card_label.setStyleSheet("color: #4ec9b0; font-weight: bold;")
#        status_layout.addWidget(self.current_card_label)

#        status_layout.addStretch()

#        self.eta_label = QLabel("ETA: --:--")
#        status_layout.addWidget(self.eta_label)

#        control_layout.addLayout(status_layout)

#        control_panel.setLayout(control_layout)
#        main_layout.addWidget(control_panel)

# Connect signals
#        self.generate_selected_btn.clicked.connect(self.generate_selected_cards)
#        self.regen_with_image_btn.clicked.connect(self.regenerate_selected_with_image)
#        self.regen_card_only_btn.clicked.connect(self.regenerate_selected_card_only)
#        self.use_custom_image_btn.clicked.connect(self.use_custom_image_for_selected)
#        self.delete_files_btn.clicked.connect(self.delete_selected_files)

# Double-click to edit
#
#        self.setLayout(main_layout)

#    def refresh_table(self):
#        """Refresh the queue table with current cards"""
#
#        completed = 0
#        pending = 0
#        failed = 0

#        for row, card in enumerate(self.cards):
# ID
#
# Name
#
# Type
#            card_type = card.type.split('')[0].strip() if '' in card.type else card.type
#
# Set
#            card_set = card.set if hasattr(card, 'set') and card.set else "CMD"
#
# Status with icon
#            if card.status == "completed":
#                status_text = " Done"
#                status_item = QTableWidgetItem(status_text)
#                status_item.setBackground(QBrush(QColor(100, 200, 100)))
#                completed += 1
#            elif card.status == "generating":
#                status_text = " Processing"
#                status_item = QTableWidgetItem(status_text)
#                status_item.setBackground(QBrush(QColor(200, 200, 100)))
#            elif card.status == "failed":
#                status_text = " Failed"
#                status_item = QTableWidgetItem(status_text)
#                status_item.setBackground(QBrush(QColor(200, 100, 100)))
#                failed += 1
#            else:  # pending
#                status_text = " Pending"
#                status_item = QTableWidgetItem(status_text)
#                status_item.setBackground(QBrush(QColor(150, 150, 150)))
#                pending += 1
#
# Time
#            if card.generated_at:
#                #            else:
#
# Update statistics
#        total = len(self.cards)
#        self.stats_label.setText(f" Total: {total} |  Done: {completed} |  Pending: {pending} |  Failed: {failed}")

# Update progress bar
#        if total > 0:
#            self.progress_bar.setMaximum(total)
#            self.progress_bar.setValue(completed)
#            self.progress_bar.setFormat(f"{completed}/{total} ({int(completed/total*100)}%)")

#    def delete_card_files(self, row: int):
#        """Delete generated files for a card"""
#        if 0 <= row < len(self.cards):
#            card = self.cards[row]
#            reply = QMessageBox.question(
#                self, "Delete Files",
#                f"Delete generated files for '{card.name}'?",
#                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
#            )

#            if reply == QMessageBox.StandardButton.Yes:
#                import os
#                from pathlib import Path

# Delete files (reuse logic from CardManagementTab)
#                deleted_files = []

#                if card.card_path and Path(card.card_path).exists():
#                    try:
#                        os.remove(card.card_path)
#                        deleted_files.append(Path(card.card_path).name)
#                        card.card_path = None
#                    except Exception as e:
#                        print(f"Error deleting: {e}")

#                if card.image_path and Path(card.image_path).exists():
#                    try:
#                        os.remove(card.image_path)
#                        deleted_files.append(Path(card.image_path).name)
#                        card.image_path = None
#                    except Exception as e:
#                        print(f"Error deleting: {e}")

# Try pattern-based deletion in deck-specific directories
#                safe_name = make_safe_filename(card.name)

# Get deck-specific directories
#                parent = self.parent().parent() if hasattr(self, 'parent') else None
#                if parent and hasattr(parent, 'current_deck_name') and parent.current_deck_name:
#                    deck_dir = Path("saved_decks") / parent.current_deck_name
#                    cards_dir = deck_dir / "rendered_cards"
#                    images_dir = deck_dir / "artwork"
#                else:
# Fallback to old directories
#                    cards_dir = Path("output/cards")
#                    images_dir = Path("output/images")

# Delete from cards directory
#                if cards_dir.exists():
#                    for file in cards_dir.glob(f"{safe_name}_*.png"):
#                        try:
#                            os.remove(file)
#                            deleted_files.append(file.name)
#                        except: pass

#                    for file in cards_dir.glob(f"{safe_name}_*.json"):
#                        try:
#                            os.remove(file)
#                            deleted_files.append(file.name)
#                        except: pass

# Delete from images directory
#                if images_dir.exists():
#                    for file in images_dir.glob(f"{safe_name}*.jpg"):
#                        try:
#                            os.remove(file)
#                            deleted_files.append(file.name)
#                        except: pass
#                    for file in images_dir.glob(f"{safe_name}*.png"):
#                        try:
#                            os.remove(file)
#                            deleted_files.append(file.name)
#                        except: pass

# Reset status
#                card.status = "pending"
#                card.generated_at = None
#                self.refresh_table()

# Log
#                parent = self.parent().parent() if hasattr(self, 'parent') else None
#                if parent and hasattr(parent, 'log_message'):
#                    if deleted_files:
#                        parent.log_message("INFO", f"Deleted: {', '.join(deleted_files)}")

#    def regenerate_selected_with_image(self):
#        """Regenerate selected card with new image"""
#        selected_rows = set()
#        for item in #            selected_rows.add(item.row())

#        if not selected_rows:
#            QMessageBox.warning(self, "No Selection", "Please select a card to regenerate!")
#            return

#        row = min(selected_rows)  # Get first selected row
#        if 0 <= row < len(self.cards):
#            card = self.cards[row]
#            card.status = "pending"
#            self.refresh_table()

# Start generation with new image
#            self.generator_worker.set_cards([card],
#                                          self.model_combo.currentText(),
#                                          self.style_combo.currentText(),
#                                          "regeneration_with_image")
#            self.generator_worker.start()

#            parent = self.parent().parent() if hasattr(self, 'parent') else None
#            if parent and hasattr(parent, 'log_message'):
#                parent.log_message("INFO", f"Regenerating with new image: {card.name}")

#    def regenerate_selected_card_only(self):
#        """Regenerate selected card using existing artwork"""
#        selected_rows = set()
#        for item in #            selected_rows.add(item.row())

#        if not selected_rows:
#            QMessageBox.warning(self, "No Selection", "Please select a card to regenerate!")
#            return

#        row = min(selected_rows)  # Get first selected row
#        if 0 <= row < len(self.cards):
#            card = self.cards[row]

# Check multiple possible artwork locations
#            artwork_path = None

# First check if image_path is set and exists
#            if card.image_path and Path(card.image_path).exists():
#                artwork_path = card.image_path
#            else:
# Try to find artwork in standard locations
#                safe_name = make_safe_filename(card.name)

# Check output/images/ directory with different extensions
#                for ext in ['.jpg', '.jpeg', '.png']:
#                    potential_path = Path(f"output/images/{safe_name}{ext}")
#                    if potential_path.exists():
#                        artwork_path = str(potential_path)
#                        card.image_path = artwork_path  # Update the card object
#                        break

# Also check for files with similar names (e.g., Mountain.jpg for Mountain card)
#                if not artwork_path:
#                    simple_name = card.name.split(',')[0].strip()  # Get first part of name
#                    for ext in ['.jpg', '.jpeg', '.png']:
#                        potential_path = Path(f"output/images/{simple_name}{ext}")
#                        if potential_path.exists():
#                            artwork_path = str(potential_path)
#                            card.image_path = artwork_path
#                            break

#            if not artwork_path:
#                reply = QMessageBox.question(
#                    self, "No Artwork",
#                    f"No artwork found for '{card.name}'. Generate new artwork?",
#                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
#                )
#                if reply == QMessageBox.StandardButton.Yes:
#                    self.regenerate_selected_with_image()
#                return

#            card.status = "pending"
#            self.refresh_table()

# Start card-only regeneration with found artwork
#            self.generator_worker.set_cards([card],
#                                          self.model_combo.currentText(),
#                                          self.style_combo.currentText(),
#                                          "card_only_regeneration")
#            self.generator_worker.start()

#            parent = self.parent().parent() if hasattr(self, 'parent') else None
#            if parent and hasattr(parent, 'log_message'):
#                parent.log_message("INFO", f"Regenerating card only (keeping artwork): {card.name}")
#                parent.log_message("DEBUG", f"Using artwork: {artwork_path}")

#    def edit_selected_art(self):
#        """Edit art prompt for selected card"""
#        selected_rows = set()
#        for item in #            selected_rows.add(item.row())

#        if not selected_rows:
#            QMessageBox.warning(self, "No Selection", "Please select a card!")
#            return

#        row = min(selected_rows)
#        self.edit_art_prompt(row)

#    def use_custom_image_for_selected(self):
#        """Allow user to select custom image for selected cards"""
#        selected_rows = set()
#        for item in #            selected_rows.add(item.row())

#        if not selected_rows:
#            QMessageBox.warning(self, "No Selection", "Please select cards to set custom image!")
#            return

# Get the current deck's artwork folder
#        parent = get_main_window()  # Use get_main_window() for reliability
#        default_dir = ""

#        if parent and hasattr(parent, 'current_deck_name') and parent.current_deck_name:
# Use the deck-specific artwork folder with absolute path
#            artwork_dir = (Path.cwd() / "saved_decks" / parent.current_deck_name / "artwork").resolve()

# Create the artwork directory if it doesn't exist
#            if not artwork_dir.exists():
#                artwork_dir.mkdir(parents=True, exist_ok=True)
#                if parent and hasattr(parent, 'log_message'):
#                    parent.log_message("INFO", f"Created artwork folder: {artwork_dir}")

#            default_dir = str(artwork_dir)
#            if parent and hasattr(parent, 'log_message'):
#                parent.log_message("INFO", f"[CUSTOM IMAGE] Opening file dialog")
#                parent.log_message("INFO", f"[CUSTOM IMAGE] Deck: {parent.current_deck_name}")
#                parent.log_message("INFO", f"[CUSTOM IMAGE] Artwork folder: {artwork_dir}")
#                parent.log_message("DEBUG", f"[CUSTOM IMAGE] Path exists: {artwork_dir.exists()}")
#                parent.log_message("DEBUG", f"[CUSTOM IMAGE] Path is absolute: {artwork_dir.is_absolute()}")
#        else:
#            if parent and hasattr(parent, 'log_message'):
#                parent.log_message("WARNING", "No deck loaded - using current directory for file dialog")

# Open file dialog to select image
# Create dialog explicitly to ensure directory is set
#        dialog = QFileDialog(self)
#        dialog.setWindowTitle("Select Custom Artwork")
#        dialog.setNameFilter("Image Files (*.png *.jpg *.jpeg *.gif *.bmp);;All Files (*.*)")
#        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)

#        if default_dir and Path(default_dir).exists():
#            dialog.setDirectory(default_dir)
# Also try to set as URLs for better compatibility
#            from PyQt6.QtCore import QUrl
#            dialog.setDirectoryUrl(QUrl.fromLocalFile(default_dir))

#            if parent and hasattr(parent, 'log_message'):
#                parent.log_message("DEBUG", f"Dialog directory set to: {default_dir}")

#        if dialog.exec():
#            selected_files = dialog.selectedFiles()
#            if selected_files:
#                image_path = selected_files[0]
#            else:
#                image_path = None
#        else:
#            image_path = None

#        if not image_path:
#            return  # User cancelled

# Verify the image exists
#        if not Path(image_path).exists():
#            QMessageBox.warning(self, "File Error", f"Selected file does not exist: {image_path}")
#            return

# Apply custom image to all selected cards and regenerate
#        cards_to_generate = []
#        for row in selected_rows:
#            if 0 <= row < len(self.cards):
#                card = self.cards[row]
# Store custom image path
#                card.custom_image_path = image_path
# Mark for regeneration
#                card.status = "pending"
#                cards_to_generate.append(card)

#        if cards_to_generate:
# Update table to show pending status
#            self.refresh_table()

# Log the action
#            parent = self.parent().parent() if hasattr(self, 'parent') else None
#            if parent and hasattr(parent, 'log_message'):
#                parent.log_message("INFO", f"Generating {len(cards_to_generate)} cards with custom image: {Path(image_path).name}")

# Start generation with custom image
#            parent = get_main_window()  # Use get_main_window() for reliability
#            deck_name = parent.current_deck_name if parent and hasattr(parent, 'current_deck_name') else None

# Debug logging
#            if parent and hasattr(parent, 'log_message'):
#                parent.log_message("DEBUG", f"Using deck_name for generation: {deck_name}")
#                parent.log_message("DEBUG", f"Parent type: {type(parent).__name__}")
#                parent.log_message("DEBUG", f"Has current_deck_name: {hasattr(parent, 'current_deck_name')}")
#                if hasattr(parent, 'current_deck_name'):
#                    parent.log_message("DEBUG", f"current_deck_name value: {parent.current_deck_name}")

#            self.generator_worker.set_cards(cards_to_generate,
#                                          self.model_combo.currentText(),
#                                          self.style_combo.currentText(),
#                                          "custom_image",
#                                          deck_name)
#            self.generator_worker.start()

#    def delete_selected_files(self):
#        """Delete files for selected card"""
#        selected_rows = set()
#        for item in #            selected_rows.add(item.row())

#        if not selected_rows:
#            QMessageBox.warning(self, "No Selection", "Please select a card!")
#            return

#        row = min(selected_rows)
#        self.delete_card_files(row)

#    def regenerate_single_card(self, row: int):
#        """Regenerate a single card"""
#        if 0 <= row < len(self.cards):
#            card = self.cards[row]
#            card.status = "pending"
#            self.refresh_table()

# Start generation for just this card
#            self.generator_worker.set_cards([card],
#                                          self.model_combo.currentText(),
#                                          self.style_combo.currentText(),
#                                          "regeneration")
#            self.generator_worker.start()

#            parent = self.parent().parent() if hasattr(self, 'parent') else None
#            if parent and hasattr(parent, 'log_message'):
#                parent.log_message("INFO", f"Regenerating: {card.name}")

#    def edit_art_prompt(self, row: int):
#        """Edit art prompt for a card"""
#        if 0 <= row < len(self.cards):
#            card = self.cards[row]

#            dialog = QDialog(self)
#            dialog.setWindowTitle(f"Edit Art - {card.name}")
#            dialog.setModal(True)
#            dialog.resize(500, 200)

#            layout = QVBoxLayout()

#            label = QLabel(f"Art description for '{card.name}':")
#            layout.addWidget(label)

#            text_edit = QTextEdit()
#            text_edit.setPlainText(card.art or f"Fantasy art of {card.name}")
#            layout.addWidget(text_edit)

#            buttons = QDialogButtonBox(
#                QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
#            )
#            buttons.accepted.connect(dialog.accept)
#            buttons.rejected.connect(dialog.reject)
#            layout.addWidget(buttons)

#            dialog.setLayout(layout)

#            if dialog.exec() == QDialog.DialogCode.Accepted:
#                new_art = text_edit.toPlainText().strip()
#                if new_art != card.art:
#                    card.art = new_art
#                    self.refresh_table()

#                    reply = QMessageBox.question(
#                        self, "Regenerate?",
#                        "Regenerate card with new art?",
#                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
#                    )

#                    if reply == QMessageBox.StandardButton.Yes:
#                        self.regenerate_single_card(row)

#    def apply_filter(self):
#        """Apply filters to the table"""
#        search_text = self.search_box.text().lower()

# Determine which filter is active
#        show_all = self.filter_all_btn.isChecked()
#        show_pending = self.filter_pending_btn.isChecked()
#        show_completed = self.filter_completed_btn.isChecked()
#        show_failed = self.filter_failed_btn.isChecked()

#        for row in range(#            show = True

# Status filter
#            if not show_all:
#                status_item = #                if status_item:
#                    status = status_item.text()
#                    if status == "pending" and not show_pending:
#                        show = False
#                    elif status == "completed" and not show_completed:
#                        show = False
#                    elif status == "failed" and not show_failed:
#                        show = False

# Search filter
#            if show and search_text:
#                name_item = #                type_item = #                if name_item and type_item:
#                    if search_text not in name_item.text().lower() and search_text not in type_item.text().lower():
#                        show = False

#
#    def on_selection_changed(self):
#        """Handle selection change in the table"""
# Update preview if main window exists
#        selected_rows = set()
#        for item in #            selected_rows.add(item.row())

# Always show custom image button when there's a selection
#        has_selection = bool(selected_rows)
#        self.use_custom_image_btn.setVisible(has_selection)

#        if not has_selection:
# No selection - hide all context-sensitive buttons
#            self.generate_selected_btn.setVisible(False)
#            self.regen_with_image_btn.setVisible(False)
#            self.regen_card_only_btn.setVisible(False)
#            self.delete_files_btn.setVisible(False)
#            return

# Get the first selected card to determine button visibility
#        row = min(selected_rows)
#        if 0 <= row < len(self.cards):
#            card = self.cards[row]

# Show buttons based on card status
#            if card.status == "pending":
# Show only Generate Selected for pending cards
#                self.generate_selected_btn.setVisible(True)
#                self.regen_with_image_btn.setVisible(False)
#                self.regen_card_only_btn.setVisible(False)
#                self.delete_files_btn.setVisible(False)
#            elif card.status == "completed":
# Show regenerate and delete options for completed cards
#                self.generate_selected_btn.setVisible(False)
#                self.regen_with_image_btn.setVisible(True)
#                self.regen_card_only_btn.setVisible(True)
#                self.delete_files_btn.setVisible(True)
#            elif card.status == "failed":
# Show generate for failed cards (retry)
#                self.generate_selected_btn.setVisible(True)
#                self.regen_with_image_btn.setVisible(False)
#                self.regen_card_only_btn.setVisible(False)
#                self.delete_files_btn.setVisible(False)
#            else:
# Default: hide all except custom image
#                self.generate_selected_btn.setVisible(False)
#                self.regen_with_image_btn.setVisible(False)
#                self.regen_card_only_btn.setVisible(False)
#                self.delete_files_btn.setVisible(False)

# Trigger preview update in main window
#            parent = self.parent().parent() if hasattr(self, 'parent') else None
#            if parent and hasattr(parent, 'update_card_preview'):
#                parent.update_card_preview(card)

#    def batch_delete_files(self):
#        """Delete files for all selected cards"""
#        selected_rows = set()
#        for item in #            selected_rows.add(item.row())

#        if not selected_rows:
#            QMessageBox.warning(self, "No Selection", "Please select cards to delete files")
#            return

#        reply = QMessageBox.question(
#            self, "Batch Delete",
#            f"Delete files for {len(selected_rows)} selected cards?",
#            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
#        )

#        if reply == QMessageBox.StandardButton.Yes:
#            for row in selected_rows:
#                if 0 <= row < len(self.cards):
# Delete without confirmation (already confirmed)
#                    self.delete_card_files_silent(row)
#            self.refresh_table()

#    def delete_card_files_silent(self, row: int):
#        """Delete files without confirmation dialog"""
#        if 0 <= row < len(self.cards):
#            card = self.cards[row]
#            import os
#            from pathlib import Path

# Same deletion logic but silent
#            if card.card_path and Path(card.card_path).exists():
#                try: os.remove(card.card_path)
#                except: pass
#                card.card_path = None

#            if card.image_path and Path(card.image_path).exists():
#                try: os.remove(card.image_path)
#                except: pass
#                card.image_path = None

#            safe_name = make_safe_filename(card.name)
#            for pattern in [f"{safe_name}_*.png", f"{safe_name}_*.json"]:
#                for file in Path("output/cards").glob(pattern):
#                    try: os.remove(file)
#                    except: pass

#            for file in Path("output/images").glob(f"{safe_name}*.jpg"):
#                try: os.remove(file)
#                except: pass

#            card.status = "pending"
#            card.generated_at = None

#    def generate_selected_cards(self):
#        """Generate only selected cards"""
#        selected_rows = set()
#        for item in #            selected_rows.add(item.row())

#        if not selected_rows:
#            QMessageBox.warning(self, "No Selection", "Please select cards to generate")
#            return

#        cards_to_generate = []
#        for row in selected_rows:
#            if 0 <= row < len(self.cards):
#                card = self.cards[row]
#                if card.status != "completed":
#                    card.status = "pending"
#                    cards_to_generate.append(card)

#        if cards_to_generate:
#            self.refresh_table()
#            parent = self.parent().parent() if hasattr(self, 'parent') else None
#            deck_name = parent.current_deck_name if parent and hasattr(parent, 'current_deck_name') else None
#            self.generator_worker.set_cards(cards_to_generate,
#                                          self.model_combo.currentText(),
#                                          self.style_combo.currentText(),
#                                          "selected",
#                                          deck_name)
#            self.generator_worker.start()

#            parent = self.parent().parent() if hasattr(self, 'parent') else None
#            if parent and hasattr(parent, 'log_message'):
#                parent.log_message("INFO", f"Generating {len(cards_to_generate)} selected cards")

#    def load_cards(self, cards: List[MTGCard]):
#        """Load cards for generation"""
# Get main window for logging
#        main_window = get_main_window()

#        if main_window and hasattr(main_window, 'log_message'):
#            main_window.log_message("INFO", f"Loading {len(cards)} cards into Generation Tab")

# Count status
#            completed = sum(1 for c in cards if c.status == "completed")
#            pending = sum(1 for c in cards if c.status == "pending")
#            failed = sum(1 for c in cards if c.status == "failed")

#            main_window.log_message("DEBUG", f"Status: {completed} completed, {pending} pending, {failed} failed")

#        self.cards = cards
#        self.refresh_table()  # Use the new refresh_table method

#    def generate_all(self):
#        """Start generating all cards"""
#        if not self.cards:
#            QMessageBox.warning(self, "Warning", "No cards to generate!")
#            return

#        try:
# Count cards needing art descriptions
#            cards_needing_art = 0

# Reset status for pending cards and check art descriptions
#            for i, card in enumerate(self.cards):
#                if card.status != "completed":
#                    card.status = "pending"

# Check if art description is needed
#                if not card.art or card.art == "":
#                    cards_needing_art += 1

# Generate art descriptions with progress updates
#            if cards_needing_art > 0:
# Get main window for status updates
#                main_window = get_main_window()

#                if main_window and hasattr(main_window, 'update_status'):
#                    main_window.update_status("generating", f"Adding art descriptions (0/{cards_needing_art})...")

#                for i, card in enumerate(self.cards):
#                    if not card.art or card.art == "":
#                        if main_window:
#                            main_window.update_status("generating", f"Art description {i+1}/{len(self.cards)}: {card.name}")
#                            main_window.log_message("INFO", f"Generating art for: {card.name}")
#                        card.art = self.get_default_art_description(card)
#                        QApplication.processEvents()  # Keep UI responsive

#            self.refresh_table()  # Use refresh_table instead

# Start generation
#            model = self.model_combo.currentText()
#            style = self.style_combo.currentText()

#            pending_cards = [c for c in self.cards if c.status == "pending"]

#            if pending_cards:
# Get theme for folder organization
#                theme = "default"
#                if main_window and hasattr(main_window, 'theme_tab'):
#                    theme = main_window.theme_tab.get_theme()

# Get current deck name
#                deck_name = main_window.current_deck_name if main_window and hasattr(main_window, 'current_deck_name') else None
#                self.generator_worker.set_cards(pending_cards, model, style, theme, deck_name)
#                self.generator_worker.start()

#                self.generate_all_btn.setEnabled(False)
#                self.pause_btn.setEnabled(True)

#                if main_window:
#                    main_window.log_message("INFO", f"Starting image generation for {len(pending_cards)} cards")
#            else:
#                QMessageBox.information(self, "Info", "All cards are already generated!")

#        except Exception as e:
#            QMessageBox.critical(self, "Error", f"Failed to start generation: {str(e)}")
#            if main_window:
#                main_window.log_message("ERROR", f"Generation failed: {str(e)}")

#    def get_default_art_description(self, card: MTGCard) -> str:
#        """Get default art description based on card name and type"""
# Percy Jackson specific characters
#        if "Percy" in card.name:
#            return "teenage boy with messy black hair and sea-green eyes, wearing orange Camp Half-Blood t-shirt and jeans, holding bronze sword Riptide, water swirling around him"
#        elif "Annabeth" in card.name:
#            return "teenage girl with curly blonde hair and stormy gray eyes, wearing Camp Half-Blood t-shirt, holding bronze dagger, architectural blueprints floating around her"
#        elif "Grover" in card.name:
#            return "teenage satyr with curly brown hair, small horns, goat legs, wearing Camp Half-Blood t-shirt, playing reed pipes"
#        elif "Camp Half-Blood" in card.name:
#            return "summer camp with Greek architecture, wooden cabins arranged in U-shape, strawberry fields, Big House with blue roof, magical barrier shimmering"
#        elif "Poseidon" in card.name or "Sea" in card.name:
#            return "majestic ocean scene with towering waves, sea creatures, trident glowing with power"

# Generic by type
#        elif "Land" in card.type:
#            if "Island" in card.name:
#                return "mystical island surrounded by crystal blue waters, magical energy emanating"
#            elif "Mountain" in card.name:
#                return "towering mountain peak with lightning striking, red mana crystals glowing"
#            elif "Forest" in card.name:
#                return "ancient forest with massive trees, green magical light filtering through"
#            else:
#                return f"mystical landscape depicting {card.name}, magical energy visible"
#        elif "Creature" in card.type:
#            return f"fantasy creature {card.name} in dynamic action pose, magical aura surrounding it"
#        elif "Instant" in card.type or "Sorcery" in card.type:
#            return f"magical spell effect showing {card.name}, energy swirling dramatically"
#        elif "Artifact" in card.type:
#            return f"ancient magical artifact {card.name}, glowing with arcane power"
#        elif "Enchantment" in card.type:
#            return f"ethereal magical aura representing {card.name}, shimmering with power"
#        else:
#            return f"fantasy art depicting {card.name}"


#    def on_item_double_clicked(self, item):
#        """Handle double-click on table item - open edit dialog"""
#        row = #        if 0 <= row < len(self.cards):
#            self.edit_art_prompt(row)

#    def pause_generation(self):
#        """Pause generation"""
#        self.generator_worker.pause()
#        self.pause_btn.setEnabled(False)
#        self.resume_btn.setEnabled(True)

#    def resume_generation(self):
#        """Resume generation"""
#        self.generator_worker.resume()
#        self.pause_btn.setEnabled(True)
#        self.resume_btn.setEnabled(False)

#    def retry_failed(self):
#        """Retry failed cards"""
#        failed_cards = [c for c in self.cards if c.status == "failed"]
#        if not failed_cards:
#            QMessageBox.information(self, "Info", "No failed cards to retry!")
#            return

#        for card in failed_cards:
#            card.status = "pending"

#        self.refresh_table()  # Use refresh_table instead of update_queue_display

#        model = self.model_combo.currentText()
#        style = self.style_combo.currentText()

# Get theme
#        main_window = get_main_window()

#        theme = "default"
#        if main_window and hasattr(main_window, 'theme_tab'):
#            theme = main_window.theme_tab.get_theme()

# Get current deck name
#        deck_name = main_window.current_deck_name if main_window and hasattr(main_window, 'current_deck_name') else None
#        self.generator_worker.set_cards(failed_cards, model, style, theme, deck_name)
#        self.generator_worker.start()

#    def on_generation_progress(self, card_id: int, status: str):
#        """Handle generation progress"""
# Get main window for logging
#        main_window = get_main_window()

#        for card in self.cards:
#            if str(card.id) == str(card_id):
#                card.status = status
#                if main_window and hasattr(main_window, 'log_message'):
#                    if status == "generating":
#                        main_window.log_message("INFO", f"Processing card {card_id}: {card.name}")
#                        self.current_card_label.setText(f" Generating: {card.name}")
#                    elif status == "completed":
#                        main_window.log_message("SUCCESS", f" Card {card_id} completed: {card.name}")
#                    elif status == "failed":
#                        main_window.log_message("ERROR", f" Card {card_id} failed: {card.name}")
#                break

#        self.refresh_table()  # Use refresh_table instead of update_queue_display

#    def on_generation_completed(self, card_id, success: bool, message: str, image_path: str = "", card_path: str = ""):
#        """Handle generation completion with file paths"""
# Get main window for logging
#        main_window = get_main_window()

# Debug log to see what IDs we're working with
#        if main_window and hasattr(main_window, 'log_message'):
#            main_window.log_message("DEBUG", f"Looking for card with ID {card_id} (type: {type(card_id)})")
#            main_window.log_message("DEBUG", f"Available card IDs: {[f'{c.id} (type: {type(c.id)})' for c in self.cards[:5]]}")

# Convert card_id to string for comparison if needed
#        for card in self.cards:
# Handle both string and int IDs for compatibility
#            if str(card.id) == str(card_id) or card.id == card_id:
#                card.status = "completed" if success else "failed"
#                if success:
#                    card.generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#                    if image_path:
#                        card.image_path = image_path
#                        if main_window and hasattr(main_window, 'log_message'):
#                            main_window.log_message("INFO", f"Art image saved: {image_path}")
#                    if card_path:
#                        card.card_path = card_path
#                        if main_window and hasattr(main_window, 'log_message'):
#                            main_window.log_message("INFO", f"Card image saved: {card_path}")
#                    if main_window and hasattr(main_window, 'log_message'):
#                        main_window.log_message("SUCCESS", f"Card {card_id} ({card.name}) generated successfully")
#                else:
#                    if main_window and hasattr(main_window, 'log_message'):
#                        main_window.log_message("ERROR", f"Card {card_id} ({card.name}) failed: {message}")
#                break

#        self.refresh_table()  # Use refresh_table instead

# Update the card in all tabs and refresh preview
#        if main_window:
# Update cards tab
#            if hasattr(main_window, 'cards_tab'):
# Find and update the card in cards_tab
#                for i, c in enumerate(main_window.cards_tab.cards):
#                    if str(c.id) == str(card_id):
# Update the card object in cards_tab with the one from generation_tab
#                        for gen_card in self.cards:
#                            if str(gen_card.id) == str(card_id):
#                                main_window.cards_tab.cards[i] = gen_card
#                                break
#                        break
#                main_window.cards_tab.refresh_table()

# Update preview if this card is selected
#            if hasattr(main_window, 'current_preview_card') and main_window.current_preview_card:
#                if str(main_window.current_preview_card.id) == str(card_id):
#                    main_window.update_card_preview(card)

# Auto-save deck with updated paths
#            if success and hasattr(main_window, 'auto_save_deck'):
#                main_window.auto_save_deck(self.cards, new_generation=False)

#        if not success:
#            QMessageBox.critical(
#                self,
#                "Generation Failed",
#                f"Card {card_id} failed:\n{message}\n\nGeneration stopped."
#            )
#            self.generate_all_btn.setEnabled(True)
# self.pause_button.setEnabled(False)  # pause_button doesn't exist in new UI
#        else:
# Check if all cards are done
#            if all(c.status in ["completed", "failed"] for c in self.cards):
#                self.generate_all_btn.setEnabled(True)
# self.pause_button.setEnabled(False)  # pause_button doesn't exist in new UI

#                completed = sum(1 for c in self.cards if c.status == "completed")
#                failed = sum(1 for c in self.cards if c.status == "failed")

#                if main_window:
#                    main_window.update_status("idle", f"Generation complete: {completed} success, {failed} failed")
#                    main_window.log_message("INFO", f"Generation batch complete: {completed} successful, {failed} failed")

# Auto-save deck with updated file paths
#                    if hasattr(main_window, 'auto_save_deck'):
#                        main_window.auto_save_deck(self.cards, "Generation completed")


#    def refresh_cards_table(self):
#        """Refresh the main cards table (renamed from refresh_table)"""
#        self.refresh_table()  # Call existing refresh_table method


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
        # self.generation_tab = GenerationTab()  # Merged into CardManagementTab

        # Add tabs
        self.tabs.addTab(self.theme_tab, " Theme & Config")
        self.tabs.addTab(self.cards_tab, " Card Management")
        # self.tabs.addTab(self.generation_tab, " Generation")  # Merged with Card Management

        # Set default tab to Card Management (Tab 2, index 1)
        self.tabs.setCurrentIndex(1)

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
        """Handle cards updated from management tab"""
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

        # Load all cards to generation tab (it will only generate pending ones)
        self.cards_tab.load_cards(current_cards)

        # Switch to cards tab (generation is now merged there)
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
