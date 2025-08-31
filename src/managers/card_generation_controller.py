#!/usr/bin/env python3
"""
Card Generation Controller

This module provides a controller class for managing all card generation workflows
in the MTG Card Generator application. It encapsulates generation logic, queue management,
batch operations, and status tracking while maintaining clean interfaces with the UI layer.

Extracted as part of the manager refactoring pattern to improve code organization,
maintainability, and testability.
"""

import contextlib
import os
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Protocol

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import QInputDialog, QMessageBox, QProgressBar, QWidget

# Import the main MTGCard class to ensure compatibility
if TYPE_CHECKING:
    # Avoid potential circular imports at runtime by using TYPE_CHECKING
    from mtg_deck_builder import MTGCard
else:
    # Import at runtime - this is safe since mtg_deck_builder doesn't import this module directly
    # Add the root directory to the path to find mtg_deck_builder
    root_path = Path(__file__).parent.parent.parent
    if str(root_path) not in sys.path:
        sys.path.insert(0, str(root_path))

    try:
        from mtg_deck_builder import MTGCard, escape_for_shell, make_safe_filename
    except ImportError:
        # Fallback to a protocol definition if import fails
        from typing import Protocol

        class MTGCard(Protocol):
            """Protocol defining the MTGCard interface for type hints."""

            id: int
            name: str
            type: str
            cost: Optional[str]
            text: Optional[str]
            power: Optional[int]
            toughness: Optional[int]
            flavor: Optional[str]
            rarity: Optional[str]
            art: Optional[str]
            status: str
            image_path: Optional[str]
            card_path: Optional[str]
            generated_at: Optional[str]

            def get_command(self, model: str, style: str) -> str:
                """Get the command to generate this card."""
                ...

            def is_creature(self) -> bool:
                """Check if this card is a creature."""
                ...

        # Fallback functions if import fails
        def make_safe_filename(name: str) -> str:
            """Convert a card name to a safe filename."""
            return name.replace(" ", "_").replace("/", "_")

        def escape_for_shell(text: str) -> str:
            """Escape text for shell command."""
            return f'"${text}"'


# Protocol definitions for dependency injection
class Logger(Protocol):
    """Protocol for logging functionality."""

    def log_message(self, level: str, message: str) -> None:
        """Log a message with the specified level."""
        ...


class ProgressReporter(Protocol):
    """Protocol for progress reporting during generation."""

    def update_progress(self, current: int, total: int, message: str = "") -> None:
        """Update progress with current/total and optional message."""
        ...

    def set_indeterminate(self, active: bool) -> None:
        """Set progress bar to indeterminate mode."""
        ...


class StatusUpdater(Protocol):
    """Protocol for updating card generation status."""

    def update_card_status(self, card: MTGCard, status: str) -> None:
        """Update a card's generation status."""
        ...

    def refresh_card_display(self, card: MTGCard) -> None:
        """Refresh the display for a specific card."""
        ...


class GenerationWorker(Protocol):
    """Protocol for generation worker threads."""

    def start_generation(
        self, cards: list[MTGCard], generation_mode: str, **kwargs
    ) -> None:
        """Start card generation process."""
        ...

    def stop_generation(self) -> None:
        """Stop the current generation process."""
        ...

    def is_running(self) -> bool:
        """Check if generation is currently running."""
        ...


class GenerationMode(str, Enum):
    """Available generation modes."""

    CARDS_ONLY = "cards_only"  # Generate card images only
    ARTWORK_ONLY = "artwork_only"  # Generate artwork only
    COMPLETE = "complete"  # Generate both cards and artwork
    ART_DESCRIPTIONS = "art_descriptions"  # Generate AI art descriptions
    MISSING_ONLY = "missing_only"  # Generate only missing cards
    REGENERATE = "regenerate"  # Regenerate existing cards


class GenerationConfig:
    """Configuration for card generation operations."""

    def __init__(
        self,
        output_directory: Optional[Path] = None,
        concurrent_workers: int = 1,
        retry_attempts: int = 3,
        timeout_seconds: int = 300,
        generate_images: bool = True,
        generate_artwork: bool = True,
        use_existing_artwork: bool = True,
        ai_art_descriptions: bool = False,
        batch_size: int = 10,
    ):
        """
        Initialize generation configuration.

        Args:
            output_directory: Directory for generated files
            concurrent_workers: Number of concurrent generation workers
            retry_attempts: Number of retry attempts for failed generations
            timeout_seconds: Timeout for individual card generation
            generate_images: Whether to generate card images
            generate_artwork: Whether to generate artwork images
            use_existing_artwork: Whether to use existing artwork if available
            ai_art_descriptions: Whether to generate AI art descriptions
            batch_size: Number of cards to process in each batch
        """
        self.output_directory = output_directory or Path("saved_decks")
        self.concurrent_workers = concurrent_workers
        self.retry_attempts = retry_attempts
        self.timeout_seconds = timeout_seconds
        self.generate_images = generate_images
        self.generate_artwork = generate_artwork
        self.use_existing_artwork = use_existing_artwork
        self.ai_art_descriptions = ai_art_descriptions
        self.batch_size = batch_size


class GenerationStatistics:
    """Statistics for generation operations."""

    def __init__(self):
        self.total_cards = 0
        self.pending_cards = 0
        self.generating_cards = 0
        self.completed_cards = 0
        self.failed_cards = 0
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.errors: list[str] = []

    @property
    def completion_rate(self) -> float:
        """Calculate completion rate as percentage."""
        if self.total_cards == 0:
            return 0.0
        return (self.completed_cards / self.total_cards) * 100

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate as percentage."""
        if self.total_cards == 0:
            return 0.0
        return (self.failed_cards / self.total_cards) * 100

    @property
    def duration_seconds(self) -> float:
        """Calculate generation duration in seconds."""
        if not self.start_time:
            return 0.0
        end_time = self.end_time or datetime.now()
        return (end_time - self.start_time).total_seconds()

    def to_dict(self) -> dict[str, Any]:
        """Convert statistics to dictionary for serialization."""
        return {
            "total_cards": self.total_cards,
            "pending_cards": self.pending_cards,
            "generating_cards": self.generating_cards,
            "completed_cards": self.completed_cards,
            "failed_cards": self.failed_cards,
            "completion_rate": self.completion_rate,
            "failure_rate": self.failure_rate,
            "duration_seconds": self.duration_seconds,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "errors": self.errors,
        }


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


class CardGenerationController(QObject):
    """
    Controller class for managing all card generation workflows.

    This class encapsulates generation logic including:
    - Generation queue management
    - Batch processing operations
    - Progress tracking and reporting
    - Status synchronization
    - Error handling and retry logic
    - Statistics collection
    - Worker thread coordination

    The class is designed to be injected into CardManagementTab to separate
    generation logic from UI concerns and improve testability.
    """

    # Signals for UI communication
    generation_started = pyqtSignal(int, str)  # total_cards, mode
    generation_progress = pyqtSignal(int, int, str)  # current, total, message
    generation_completed = pyqtSignal(list, object)  # cards, statistics
    card_status_changed = pyqtSignal(object, str)  # card, new_status
    error_occurred = pyqtSignal(str, str)  # error_type, error_message

    def __init__(
        self,
        parent_widget: QWidget,
        logger: Optional[Logger] = None,
        progress_reporter: Optional[ProgressReporter] = None,
        status_updater: Optional[StatusUpdater] = None,
        generation_worker: Optional[GenerationWorker] = None,
        config: Optional[GenerationConfig] = None,
    ):
        """
        Initialize the CardGenerationController.

        Args:
            parent_widget: Parent widget for dialogs and UI interactions
            logger: Logger instance for operation messages
            progress_reporter: Progress reporter for UI updates
            status_updater: Status updater for card state changes
            generation_worker: Worker for background generation tasks
            config: Generation configuration settings
        """
        super().__init__()
        self.parent_widget = parent_widget
        self.logger = logger
        self.progress_reporter = progress_reporter
        self.status_updater = status_updater
        self.generation_worker = generation_worker or self._create_default_worker()
        self.config = config or GenerationConfig()

        # Internal state
        self._generation_queue: list[MTGCard] = []
        self._current_generation: Optional[GenerationMode] = None
        self._current_statistics = GenerationStatistics()
        self._is_generation_active = False
        self._batch_timer: Optional[QTimer] = None

        # Connect worker signals if available
        if hasattr(self.generation_worker, "progress"):
            self.generation_worker.progress.connect(self._on_worker_progress)
        if hasattr(self.generation_worker, "completed"):
            self.generation_worker.completed.connect(self._on_worker_completed)
        if hasattr(self.generation_worker, "error"):
            self.generation_worker.error.connect(self._on_worker_error)

        self._setup_batch_timer()

    def _create_default_worker(self) -> GenerationWorker:
        """Create a default generation worker."""

        class DefaultGenerationWorker:
            def start_generation(
                self, cards: list[MTGCard], generation_mode: str, **kwargs
            ) -> None:
                # Placeholder implementation
                pass

            def stop_generation(self) -> None:
                pass

            def is_running(self) -> bool:
                return False

        return DefaultGenerationWorker()

    def _setup_batch_timer(self):
        """Set up the batch processing timer."""
        self._batch_timer = QTimer()
        self._batch_timer.timeout.connect(self._process_batch)
        self._batch_timer.setSingleShot(False)

    def _log(self, level: str, message: str) -> None:
        """
        Log a message if logger is available.

        Args:
            level: Log level (INFO, DEBUG, ERROR, SUCCESS, WARNING)
            message: Message to log
        """
        if self.logger:
            self.logger.log_message(level, message)

    def _show_error(self, title: str, message: str) -> None:
        """
        Show error message dialog.

        Args:
            title: Dialog title
            message: Error message
        """
        try:
            QMessageBox.critical(self.parent_widget, title, message)
        except (TypeError, AttributeError):
            # Fallback for testing or when parent_widget is mock/None
            self._log("ERROR", f"{title}: {message}")
        finally:
            self.error_occurred.emit(title, message)

    def _show_warning(self, title: str, message: str) -> None:
        """
        Show warning message dialog.

        Args:
            title: Dialog title
            message: Warning message
        """
        try:
            QMessageBox.warning(self.parent_widget, title, message)
        except (TypeError, AttributeError):
            # Fallback for testing or when parent_widget is mock/None
            self._log("WARNING", f"{title}: {message}")

    def _update_progress(self, current: int, total: int, message: str = "") -> None:
        """
        Update progress indicators.

        Args:
            current: Current progress value
            total: Total progress value
            message: Optional progress message
        """
        if self.progress_reporter:
            self.progress_reporter.update_progress(current, total, message)
        self.generation_progress.emit(current, total, message)

    def _update_card_status(self, card: MTGCard, status: str) -> None:
        """
        Update a card's generation status.

        Args:
            card: The card to update
            status: New status value
        """
        old_status = getattr(card, "status", "pending")
        card.status = status

        if status == "completed":
            card.generated_at = datetime.now().isoformat()

        # Update statistics
        self._update_statistics_for_status_change(old_status, status)

        # Notify UI components
        if self.status_updater:
            self.status_updater.update_card_status(card, status)
            self.status_updater.refresh_card_display(card)

        self.card_status_changed.emit(card, status)
        self._log("DEBUG", f"Card {card.name} status changed: {old_status} -> {status}")

    def _update_statistics_for_status_change(self, old_status: str, new_status: str):
        """Update generation statistics when card status changes."""
        # Decrement old status count
        if old_status == "pending":
            self._current_statistics.pending_cards = max(
                0, self._current_statistics.pending_cards - 1
            )
        elif old_status == "generating":
            self._current_statistics.generating_cards = max(
                0, self._current_statistics.generating_cards - 1
            )
        elif old_status == "completed":
            self._current_statistics.completed_cards = max(
                0, self._current_statistics.completed_cards - 1
            )
        elif old_status == "failed":
            self._current_statistics.failed_cards = max(
                0, self._current_statistics.failed_cards - 1
            )

        # Increment new status count
        if new_status == "pending":
            self._current_statistics.pending_cards += 1
        elif new_status == "generating":
            self._current_statistics.generating_cards += 1
        elif new_status == "completed":
            self._current_statistics.completed_cards += 1
        elif new_status == "failed":
            self._current_statistics.failed_cards += 1

    # Public API Methods - Generation Control

    def start_generation(
        self, cards: list[MTGCard], mode: GenerationMode, **kwargs
    ) -> bool:
        """
        Start card generation process.

        Args:
            cards: List of cards to generate
            mode: Generation mode to use
            **kwargs: Additional generation parameters

        Returns:
            True if generation started successfully, False otherwise
        """
        if self._is_generation_active:
            self._show_warning(
                "Generation Active", "Card generation is already in progress."
            )
            return False

        if not cards:
            self._show_warning("No Cards", "No cards selected for generation.")
            return False

        try:
            # Validate cards for generation
            validation_issues = self.validate_cards_for_generation(cards)
            if validation_issues:
                issue_text = "\n".join(validation_issues)
                self._show_error(
                    "Validation Failed",
                    f"Card validation failed:\n\n{issue_text}",
                )
                return False

            # Initialize generation state
            self._generation_queue = cards.copy()
            self._current_generation = mode
            self._is_generation_active = True
            self._current_statistics = GenerationStatistics()
            self._current_statistics.total_cards = len(cards)
            self._current_statistics.start_time = datetime.now()

            # Count initial status distribution
            for card in cards:
                status = getattr(card, "status", "pending")
                if status == "pending":
                    self._current_statistics.pending_cards += 1
                elif status == "generating":
                    self._current_statistics.generating_cards += 1
                elif status == "completed":
                    self._current_statistics.completed_cards += 1
                elif status == "failed":
                    self._current_statistics.failed_cards += 1

            # Start progress indication
            if self.progress_reporter:
                self.progress_reporter.set_indeterminate(True)

            # Emit generation started signal
            self.generation_started.emit(len(cards), mode.value)

            # Start the generation worker
            if self.generation_worker:
                self.generation_worker.start_generation(cards, mode.value, **kwargs)
            else:
                # Fallback to batch processing if no worker available
                self._start_batch_processing()

            self._log("INFO", f"Started {mode.value} generation for {len(cards)} cards")
            return True

        except Exception as e:
            self._is_generation_active = False
            self._show_error(
                "Generation Failed", f"Failed to start generation: {str(e)}"
            )
            self._log("ERROR", f"Generation startup failed: {str(e)}")
            return False

    def stop_generation(self) -> bool:
        """
        Stop the current generation process.

        Returns:
            True if generation stopped successfully, False otherwise
        """
        if not self._is_generation_active:
            self._log("WARNING", "No active generation to stop")
            return False

        try:
            # Stop the worker
            if self.generation_worker:
                self.generation_worker.stop_generation()

            # Stop batch timer
            if self._batch_timer:
                self._batch_timer.stop()

            # Update remaining cards to pending status
            for card in self._generation_queue:
                if getattr(card, "status", "pending") == "generating":
                    self._update_card_status(card, "pending")

            # Finalize statistics
            self._current_statistics.end_time = datetime.now()

            # Reset state
            self._is_generation_active = False
            self._current_generation = None
            self._generation_queue.clear()

            # Update progress
            if self.progress_reporter:
                self.progress_reporter.set_indeterminate(False)

            self._log("INFO", "Generation stopped by user")
            self.generation_completed.emit([], self._current_statistics)
            return True

        except Exception as e:
            self._log("ERROR", f"Failed to stop generation: {str(e)}")
            return False

    def pause_generation(self) -> bool:
        """
        Pause the current generation process.

        Returns:
            True if generation paused successfully, False otherwise
        """
        if not self._is_generation_active:
            return False

        try:
            if self._batch_timer:
                self._batch_timer.stop()

            if self.progress_reporter:
                self.progress_reporter.set_indeterminate(False)

            self._log("INFO", "Generation paused")
            return True

        except Exception as e:
            self._log("ERROR", f"Failed to pause generation: {str(e)}")
            return False

    def resume_generation(self) -> bool:
        """
        Resume a paused generation process.

        Returns:
            True if generation resumed successfully, False otherwise
        """
        if not self._is_generation_active:
            return False

        try:
            if self._batch_timer and not self._batch_timer.isActive():
                self._batch_timer.start(1000)  # Resume batch processing

            if self.progress_reporter:
                self.progress_reporter.set_indeterminate(True)

            self._log("INFO", "Generation resumed")
            return True

        except Exception as e:
            self._log("ERROR", f"Failed to resume generation: {str(e)}")
            return False

    def is_generation_active(self) -> bool:
        """Check if generation is currently active."""
        return self._is_generation_active

    def get_generation_mode(self) -> Optional[GenerationMode]:
        """Get the current generation mode."""
        return self._current_generation

    def get_generation_queue_size(self) -> int:
        """Get the number of cards in the generation queue."""
        return len(self._generation_queue)

    # Public API Methods - Generation Statistics

    def get_generation_statistics(
        self, cards: Optional[list[MTGCard]] = None
    ) -> dict[str, Any]:
        """
        Get generation statistics for cards.

        Args:
            cards: Cards to analyze (uses current queue if None)

        Returns:
            Dictionary containing generation statistics
        """
        if self._is_generation_active:
            return self._current_statistics.to_dict()

        # Calculate statistics for provided cards
        cards = cards or []
        stats = GenerationStatistics()
        stats.total_cards = len(cards)

        for card in cards:
            status = getattr(card, "status", "pending")
            if status == "pending":
                stats.pending_cards += 1
            elif status == "generating":
                stats.generating_cards += 1
            elif status == "completed":
                stats.completed_cards += 1
            elif status == "failed":
                stats.failed_cards += 1

        return stats.to_dict()

    def get_cards_by_status(self, cards: list[MTGCard], status: str) -> list[MTGCard]:
        """
        Filter cards by generation status.

        Args:
            cards: List of cards to filter
            status: Status to filter by

        Returns:
            List of cards with the specified status
        """
        return [card for card in cards if getattr(card, "status", "pending") == status]

    def get_pending_cards(self, cards: list[MTGCard]) -> list[MTGCard]:
        """Get cards with pending status."""
        return self.get_cards_by_status(cards, "pending")

    def get_completed_cards(self, cards: list[MTGCard]) -> list[MTGCard]:
        """Get cards with completed status."""
        return self.get_cards_by_status(cards, "completed")

    def get_failed_cards(self, cards: list[MTGCard]) -> list[MTGCard]:
        """Get cards with failed status."""
        return self.get_cards_by_status(cards, "failed")

    def get_generating_cards(self, cards: list[MTGCard]) -> list[MTGCard]:
        """Get cards currently being generated."""
        return self.get_cards_by_status(cards, "generating")

    # Public API Methods - Validation

    def validate_cards_for_generation(self, cards: list[MTGCard]) -> list[str]:
        """
        Validate cards for generation requirements.

        Args:
            cards: List of cards to validate

        Returns:
            List of validation error messages (empty if all valid)
        """
        issues = []

        for i, card in enumerate(cards, 1):
            # Check required fields
            if not getattr(card, "name", "").strip():
                issues.append(f"Card {i}: Missing name")

            if not getattr(card, "type", "").strip():
                issues.append(f"Card {i}: Missing type")

            # Check for reasonable text length (for generation)
            text = getattr(card, "text", "") or ""
            if len(text) > 1000:  # Arbitrary limit for generation systems
                issues.append(f"Card {i} ({card.name}): Text too long for generation")

            # Check art description if AI generation is enabled
            if self.config.ai_art_descriptions:
                art = getattr(card, "art", "") or ""
                if not art.strip():
                    issues.append(
                        f"Card {i} ({card.name}): Missing art description for AI generation"
                    )

        return issues

    def validate_generation_environment(self) -> list[str]:
        """
        Validate that the generation environment is properly configured.

        Returns:
            List of configuration issues (empty if all valid)
        """
        issues = []

        # Check output directory
        if not self.config.output_directory.exists():
            try:
                self.config.output_directory.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                issues.append(f"Cannot create output directory: {str(e)}")

        # Check for generation scripts
        scripts_to_check = [
            "generate_card.py",
            "generate_image.py",
        ]

        for script in scripts_to_check:
            script_path = Path(script)
            if not script_path.exists():
                # Try alternative locations
                alt_locations = [
                    Path("src") / "magic_tg_card_generator" / script,
                    Path("magic_tg_card_generator") / script,
                ]
                found = any(alt_path.exists() for alt_path in alt_locations)
                if not found:
                    issues.append(f"Generation script not found: {script}")

        return issues

    # Public API Methods - Batch Operations

    def generate_missing_cards(self, cards: list[MTGCard]) -> bool:
        """
        Generate only cards that haven't been generated yet.

        Args:
            cards: List of all cards

        Returns:
            True if generation started, False otherwise
        """
        missing_cards = self.get_pending_cards(cards)
        if not missing_cards:
            self._show_warning(
                "No Missing Cards", "All cards have already been generated."
            )
            return False

        return self.start_generation(missing_cards, GenerationMode.MISSING_ONLY)

    def generate_failed_cards(self, cards: list[MTGCard]) -> bool:
        """
        Retry generation for cards that failed.

        Args:
            cards: List of all cards

        Returns:
            True if generation started, False otherwise
        """
        failed_cards = self.get_failed_cards(cards)
        if not failed_cards:
            self._show_warning("No Failed Cards", "No cards have failed generation.")
            return False

        # Reset failed cards to pending before regenerating
        for card in failed_cards:
            self._update_card_status(card, "pending")

        return self.start_generation(failed_cards, GenerationMode.REGENERATE)

    def regenerate_selected_cards(self, cards: list[MTGCard]) -> bool:
        """
        Regenerate specific cards, regardless of current status.

        Args:
            cards: List of cards to regenerate

        Returns:
            True if generation started, False otherwise
        """
        if not cards:
            self._show_warning(
                "No Cards Selected", "Please select cards to regenerate."
            )
            return False

        # Reset selected cards to pending
        for card in cards:
            self._update_card_status(card, "pending")

        return self.start_generation(cards, GenerationMode.REGENERATE)

    def generate_art_descriptions(self, cards: list[MTGCard]) -> bool:
        """
        Generate AI art descriptions for cards missing them.

        Args:
            cards: List of cards to process

        Returns:
            True if generation started, False otherwise
        """
        cards_needing_art = [
            card for card in cards if not getattr(card, "art", "").strip()
        ]

        if not cards_needing_art:
            self._show_warning(
                "No Cards Need Art",
                "All cards already have art descriptions.",
            )
            return False

        return self.start_generation(cards_needing_art, GenerationMode.ART_DESCRIPTIONS)

    # Public API Methods - Configuration

    def update_config(self, config: GenerationConfig) -> None:
        """
        Update the generation configuration.

        Args:
            config: New configuration settings
        """
        self.config = config
        self._log("INFO", "Generation configuration updated")

    def get_config(self) -> GenerationConfig:
        """Get the current generation configuration."""
        return self.config

    # Internal Methods - Worker Event Handlers

    def _on_worker_progress(self, current: int, total: int, message: str = ""):
        """Handle progress updates from the worker."""
        self._update_progress(current, total, message)

    def _on_worker_completed(self, results: list[tuple[MTGCard, bool, str]]):
        """
        Handle completion from the worker.

        Args:
            results: List of (card, success, message) tuples
        """
        completed_cards = []

        for card, success, message in results:
            if success:
                self._update_card_status(card, "completed")
                completed_cards.append(card)
            else:
                self._update_card_status(card, "failed")
                self._current_statistics.errors.append(f"{card.name}: {message}")

        # Finalize generation
        self._current_statistics.end_time = datetime.now()
        self._is_generation_active = False

        if self.progress_reporter:
            self.progress_reporter.set_indeterminate(False)

        self._log(
            "SUCCESS" if completed_cards else "WARNING",
            f"Generation completed: {len(completed_cards)} successful, {len(results) - len(completed_cards)} failed",
        )

        self.generation_completed.emit(completed_cards, self._current_statistics)

    def _on_worker_error(self, error_message: str):
        """Handle errors from the worker."""
        self._current_statistics.errors.append(error_message)
        self._log("ERROR", f"Generation worker error: {error_message}")

    # Internal Methods - Batch Processing

    def _start_batch_processing(self):
        """Start batch processing using timer-based approach."""
        if self._batch_timer:
            self._batch_timer.start(1000)  # Process batch every second

    def _process_batch(self):
        """Process a batch of cards from the queue."""
        if not self._generation_queue:
            self._batch_timer.stop()
            self._finalize_batch_generation()
            return

        # Take a batch of cards
        batch_size = min(self.config.batch_size, len(self._generation_queue))
        current_batch = self._generation_queue[:batch_size]
        self._generation_queue = self._generation_queue[batch_size:]

        # Process the batch
        for card in current_batch:
            self._update_card_status(card, "generating")
            success = self._generate_single_card(card)
            status = "completed" if success else "failed"
            self._update_card_status(card, status)

        # Update progress
        total_processed = (
            self._current_statistics.completed_cards
            + self._current_statistics.failed_cards
        )
        self._update_progress(
            total_processed,
            self._current_statistics.total_cards,
            f"Processed {batch_size} cards",
        )

    def _generate_single_card(self, card: MTGCard) -> bool:
        """
        Generate a single card using subprocess calls.

        Args:
            card: Card to generate

        Returns:
            True if successful, False otherwise
        """
        try:
            # This is a simplified implementation - in practice, this would call
            # the appropriate generation scripts based on the generation mode
            if self._current_generation == GenerationMode.CARDS_ONLY:
                return self._generate_card_image(card)
            elif self._current_generation == GenerationMode.ARTWORK_ONLY:
                return self._generate_artwork_image(card)
            elif self._current_generation == GenerationMode.COMPLETE:
                return self._generate_card_image(card) and self._generate_artwork_image(
                    card
                )
            else:
                return self._generate_card_image(card)

        except Exception as e:
            self._log("ERROR", f"Failed to generate card {card.name}: {str(e)}")
            return False

    def _generate_card_image(self, card: MTGCard) -> bool:
        """Generate card image for a single card."""
        try:
            # Placeholder for actual generation logic
            # In practice, this would call generate_card.py or similar
            self._log("DEBUG", f"Generating card image for: {card.name}")
            return True
        except Exception as e:
            self._log(
                "ERROR", f"Card image generation failed for {card.name}: {str(e)}"
            )
            return False

    def _generate_artwork_image(self, card: MTGCard) -> bool:
        """Generate artwork image for a single card."""
        try:
            # Placeholder for actual generation logic
            # In practice, this would call generate_image.py or similar
            self._log("DEBUG", f"Generating artwork for: {card.name}")
            return True
        except Exception as e:
            self._log("ERROR", f"Artwork generation failed for {card.name}: {str(e)}")
            return False

    def _finalize_batch_generation(self):
        """Finalize batch generation process."""
        self._current_statistics.end_time = datetime.now()
        self._is_generation_active = False

        if self.progress_reporter:
            self.progress_reporter.set_indeterminate(False)

        completed_cards = []  # Would be populated during actual generation
        self.generation_completed.emit(completed_cards, self._current_statistics)

    # Context manager support for batch operations
    def __enter__(self):
        """Enter context manager for batch generation operations."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and cleanup resources."""
        if self._is_generation_active:
            self.stop_generation()

        # Reset internal state
        self._generation_queue.clear()
        self._current_generation = None
        self._current_statistics = GenerationStatistics()

    # High-level generation methods extracted from main application
    def generate_missing(self, cards, model="sdxl", style="mtg_modern", deck_name=None):
        """Generate only cards that haven't been generated yet"""
        missing_cards = [
            card
            for card in cards
            if not hasattr(card, "status") or card.status == "pending"
        ]

        if not missing_cards:
            return "All cards have been generated!"

        if hasattr(self, "generation_worker"):
            self.generation_worker.set_cards(
                missing_cards, model, style, deck_name=deck_name
            )
            self.generation_worker.start()

        if self.logger:
            self.logger.log_message(
                "INFO", f"Generating {len(missing_cards)} missing cards"
            )

        return f"Started generation of {len(missing_cards)} missing cards"

    def generate_art_descriptions(self, cards):
        """Generate art descriptions for cards using AI"""
        if not cards:
            return "No cards to generate art for!"

        cards_needing_art = [
            card
            for card in cards
            if not hasattr(card, "art_prompt") or not card.art_prompt
        ]

        if not cards_needing_art:
            return "All cards have art descriptions!"

        return f"Found {len(cards_needing_art)} cards needing art descriptions"

    def regenerate_selected_with_image(
        self, selected_cards, model="sdxl", style="mtg_modern", deck_name=None
    ):
        """Regenerate selected cards with new images"""
        if not selected_cards:
            return "No cards selected!"

        cards_to_regenerate = []
        for card in selected_cards:
            card.status = "pending"
            cards_to_regenerate.append(card)

        if cards_to_regenerate and hasattr(self, "generation_worker"):
            self.generation_worker.set_cards(
                cards_to_regenerate,
                model,
                style,
                "regeneration_with_image",
                deck_name,
            )
            self.generation_worker.start()

        return (
            f"Started regeneration of {len(cards_to_regenerate)} cards with new images"
        )

    def regenerate_selected_card_only(
        self, selected_cards, model="sdxl", style="mtg_modern", deck_name=None
    ):
        """Regenerate selected cards without new images"""
        if not selected_cards:
            return "No cards selected!"

        cards_to_regenerate = []
        for card in selected_cards:
            card.status = "pending"
            cards_to_regenerate.append(card)

        if cards_to_regenerate and hasattr(self, "generation_worker"):
            self.generation_worker.set_cards(
                cards_to_regenerate,
                model,
                style,
                "card_only_regeneration",
                deck_name,
            )
            self.generation_worker.start()

        return f"Started card-only regeneration of {len(cards_to_regenerate)} cards"

    def use_custom_image_for_selected(
        self,
        selected_cards,
        image_path,
        model="sdxl",
        style="mtg_modern",
        deck_name=None,
    ):
        """Use custom image for selected cards"""
        if not selected_cards:
            return "No cards selected!"

        if not image_path:
            return "No image path provided!"

        for card in selected_cards:
            card.custom_image_path = image_path
            card.status = "pending"

        # Generate cards with custom image
        if hasattr(self, "generation_worker"):
            self.generation_worker.set_cards(
                selected_cards,
                model,
                style,
                "custom_image",
                deck_name,
            )
            self.generation_worker.start()

        return (
            f"Set custom image for {len(selected_cards)} cards and started generation"
        )

    def delete_selected_files(self, selected_cards):
        """Delete generated files for selected cards"""
        if not selected_cards:
            return "No cards selected!"

        deleted_count = 0
        for card in selected_cards:
            # Delete files
            if (
                hasattr(card, "card_path")
                and card.card_path
                and Path(card.card_path).exists()
            ):
                try:
                    Path(card.card_path).unlink()
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
                except:
                    pass

            # Reset card status
            card.status = "pending"
            card.card_path = ""
            card.image_path = ""

        return f"Deleted files for {deleted_count} cards"

    def generate_all_cards(
        self, cards, model="sdxl", style="mtg_modern", deck_name=None
    ):
        """Generate all cards in the list"""
        if not cards:
            return "No cards to generate!"

        # Reset all cards to pending
        for card in cards:
            card.status = "pending"

        if hasattr(self, "generation_worker"):
            self.generation_worker.set_cards(cards, model, style, deck_name=deck_name)
            self.generation_worker.start()

        return f"Started generation of all {len(cards)} cards"

    def generate_selected_cards(
        self, selected_cards, model="sdxl", style="mtg_modern", deck_name=None
    ):
        """Generate selected cards"""
        if not selected_cards:
            return "No cards selected!"

        for card in selected_cards:
            card.status = "pending"

        if hasattr(self, "generation_worker"):
            self.generation_worker.set_cards(
                selected_cards, model, style, deck_name=deck_name
            )
            self.generation_worker.start()

        return f"Started generation of {len(selected_cards)} selected cards"
