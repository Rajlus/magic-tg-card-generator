#!/usr/bin/env python3
"""
Card File Operations Manager

This module provides a manager class for handling all file I/O operations
in the MTG Card Generator application. It encapsulates YAML deck operations,
CSV import/export, directory management, and file status synchronization.

Extracted from CardManagementTab as part of issue #22 to improve code organization
and maintainability.
"""

import csv
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Protocol

import yaml
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QWidget

# Import domain model
if TYPE_CHECKING:
    from src.domain.models import MTGCard
else:
    from src.domain.models import MTGCard


# Protocol definitions for dependency injection
class Logger(Protocol):
    """Protocol for logging functionality."""

    def log_message(self, level: str, message: str) -> None:
        """Log a message with the specified level."""
        ...


class DialogProvider(Protocol):
    """Protocol for file dialog operations."""

    def get_open_filename(
        self, parent: QWidget, caption: str, directory: str, filter: str
    ) -> tuple[str, str]:
        """Show open file dialog and return selected file."""
        ...

    def get_save_filename(
        self, parent: QWidget, caption: str, directory: str, filter: str
    ) -> tuple[str, str]:
        """Show save file dialog and return selected file."""
        ...


class CardFileOperations:
    """
    Manager class for handling all card file I/O operations.

    This class encapsulates file operations including:
    - YAML deck loading and saving
    - CSV import and export
    - Directory structure management
    - File status synchronization
    - Error handling for file operations

    The class is designed to be injected into CardManagementTab to separate
    file operations from UI logic and improve testability.
    """

    # Default directory paths
    SAVED_DECKS_DIR = "saved_decks"
    RENDERED_CARDS_SUBDIR = "rendered_cards"
    ARTWORK_SUBDIR = "artwork"
    BACKUPS_SUBDIR = "backups"

    # File extensions and filters
    YAML_FILTER = "YAML Files (*.yaml);;All Files (*)"
    CSV_FILTER = "CSV Files (*.csv);;All Files (*)"

    # CSV field names for export
    CSV_FIELDNAMES = [
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
        "Set",
        "Status",
        "Image_Path",
        "Card_Path",
        "Generated_At",
        "Generation_Status",
        "Custom_Image_Path",
    ]

    def __init__(
        self,
        parent_widget: QWidget,
        logger: Optional[Logger] = None,
        dialog_provider: Optional[DialogProvider] = None,
    ):
        """
        Initialize the CardFileOperations manager.

        Args:
            parent_widget: Parent widget for file dialogs
            logger: Logger instance for operation messages
            dialog_provider: Dialog provider for file operations (for testing)
        """
        self.parent_widget = parent_widget
        self.logger = logger
        self.dialog_provider = dialog_provider or self._default_dialog_provider()

        # Internal state
        self._current_deck_name: Optional[str] = None
        self._last_loaded_deck_path: Optional[str] = None
        self._ignore_next_change: bool = False

    def _default_dialog_provider(self) -> DialogProvider:
        """Create default dialog provider using PyQt6 dialogs."""

        class DefaultDialogProvider:
            def get_open_filename(
                self, parent: QWidget, caption: str, directory: str, filter: str
            ) -> tuple[str, str]:
                return QFileDialog.getOpenFileName(parent, caption, directory, filter)

            def get_save_filename(
                self, parent: QWidget, caption: str, directory: str, filter: str
            ) -> tuple[str, str]:
                return QFileDialog.getSaveFileName(parent, caption, directory, filter)

        return DefaultDialogProvider()

    # Properties for accessing current state
    @property
    def current_deck_name(self) -> Optional[str]:
        """Get the current deck name."""
        return self._current_deck_name

    @current_deck_name.setter
    def current_deck_name(self, name: Optional[str]) -> None:
        """Set the current deck name."""
        self._current_deck_name = name

    @property
    def last_loaded_deck_path(self) -> Optional[str]:
        """Get the path of the last loaded deck."""
        return self._last_loaded_deck_path

    @last_loaded_deck_path.setter
    def last_loaded_deck_path(self, path: Optional[str]) -> None:
        """Set the path of the last loaded deck."""
        self._last_loaded_deck_path = path

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

    def _show_info(self, title: str, message: str) -> None:
        """
        Show information message dialog.

        Args:
            title: Dialog title
            message: Information message
        """
        try:
            QMessageBox.information(self.parent_widget, title, message)
        except (TypeError, AttributeError):
            # Fallback for testing or when parent_widget is mock/None
            self._log("INFO", f"{title}: {message}")

    def _create_deck_directory_structure(self, deck_name: str) -> Path:
        """
        Create directory structure for a deck.

        Args:
            deck_name: Name of the deck

        Returns:
            Path to the created deck directory
        """
        deck_dir = Path(self.SAVED_DECKS_DIR) / deck_name
        deck_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (deck_dir / self.RENDERED_CARDS_SUBDIR).mkdir(exist_ok=True)
        (deck_dir / self.ARTWORK_SUBDIR).mkdir(exist_ok=True)
        (deck_dir / self.BACKUPS_SUBDIR).mkdir(exist_ok=True)

        return deck_dir

    def _ensure_safe_filename(self, filename: str) -> str:
        """
        Convert a string to a safe filename.

        Args:
            filename: Original filename

        Returns:
            Safe filename string
        """
        # Replace problematic characters with underscores
        safe_name = filename
        for char in ["/", "\\", ":", "*", "?", '"', "<", ">", "|", "'"]:
            safe_name = safe_name.replace(char, "_")
        # Remove extra spaces and clean up
        safe_name = "_".join(safe_name.split())
        # Ensure it doesn't start with a dot or be empty
        if not safe_name or safe_name.startswith("."):
            safe_name = "unnamed_card"
        return safe_name

    def _mtg_card_to_dict(self, card: MTGCard) -> dict[str, Any]:
        """
        Convert MTGCard object to dictionary for serialization.

        Args:
            card: MTGCard object to convert

        Returns:
            Dictionary representation of the card
        """
        return {
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
            "set": getattr(card, "set", "CMD"),
            "status": card.status,
            "image_path": card.image_path,
            "card_path": card.card_path,
            "generated_at": card.generated_at,
            "generation_status": getattr(card, "generation_status", "pending"),
            "custom_image_path": getattr(card, "custom_image_path", None),
        }

    def _dict_to_mtg_card(self, card_dict: dict[str, Any], card_id: int) -> MTGCard:
        """
        Convert dictionary to MTGCard object.

        Args:
            card_dict: Dictionary containing card data
            card_id: ID to assign to the card

        Returns:
            MTGCard object
        """
        # Import MTGCard at runtime to avoid circular dependencies
        if "mtg_deck_builder" not in sys.modules:
            root_path = Path(__file__).parent.parent.parent
            if str(root_path) not in sys.path:
                sys.path.insert(0, str(root_path))
            from mtg_deck_builder import MTGCard as MTGCardClass
        else:
            from mtg_deck_builder import MTGCard as MTGCardClass

        # Ensure cost is always a string (YAML might parse numbers as integers)
        cost_value = card_dict.get("cost", "")
        if isinstance(cost_value, int | float):
            cost_value = str(cost_value)

        return MTGCardClass(
            id=card_id,
            name=card_dict.get("name", f"Card {card_id}"),
            type=card_dict.get("type", "Unknown"),
            cost=cost_value,
            text=card_dict.get("text", ""),
            power=card_dict.get("power"),
            toughness=card_dict.get("toughness"),
            flavor=card_dict.get("flavor", ""),
            rarity=card_dict.get("rarity", "common"),
            art=card_dict.get("art", ""),
            set=card_dict.get("set", "CMD"),  # Default set
            status=card_dict.get("status", "pending"),
            image_path=card_dict.get("image_path"),
            card_path=card_dict.get("card_path"),
            generated_at=card_dict.get("generated_at"),
            generation_status=card_dict.get("generation_status", "pending"),
            custom_image_path=card_dict.get("custom_image_path"),
        )

    # Public API Methods - YAML Operations

    def load_deck_with_dialog(self) -> Optional[list[MTGCard]]:
        """
        Show file dialog and load a deck from YAML file.

        Returns:
            List of loaded cards, or None if cancelled/failed
        """
        filename, _ = self.dialog_provider.get_open_filename(
            self.parent_widget, "Load Deck", self.SAVED_DECKS_DIR, self.YAML_FILTER
        )

        if filename:
            return self.load_deck_from_file(filename)
        return None

    def load_deck_from_file(self, filename: str) -> Optional[list[MTGCard]]:
        """
        Load a deck from a specific YAML file.

        Args:
            filename: Path to the YAML file

        Returns:
            List of loaded cards, or None if failed
        """
        try:
            with open(filename, encoding="utf-8") as f:
                deck_data = yaml.safe_load(f)

            if not deck_data:
                self._show_error("Load Failed", "YAML file is empty or invalid")
                return None

            cards = []

            # Handle both old format (with separate commander) and new format (all in cards)
            if "commander" in deck_data:
                # Old format with separate commander
                cmd_data = deck_data["commander"]
                commander = self._dict_to_mtg_card(cmd_data, cmd_data.get("id", 1))
                cards.append(commander)

            # Add other cards
            if "cards" in deck_data:
                for i, card_data in enumerate(deck_data["cards"], start=2):
                    card = self._dict_to_mtg_card(card_data, card_data.get("id", i))
                    # Don't set status from YAML, let it be determined by actual files
                    # This prevents status from one deck affecting another
                    card.status = "pending"
                    cards.append(card)

            # Update deck tracking information
            deck_name = Path(filename).stem
            self._current_deck_name = deck_name
            self._last_loaded_deck_path = filename

            self._log("INFO", f"Loaded deck: {deck_name} ({len(cards)} cards)")
            return cards

        except yaml.YAMLError as ye:
            self._show_error("Load Failed", f"YAML parsing error: {str(ye)}")
            self._log("ERROR", f"YAML parsing error: {str(ye)}")
            return None
        except FileNotFoundError:
            self._show_error("Load Failed", f"File not found: {filename}")
            self._log("ERROR", f"File not found: {filename}")
            return None
        except Exception as e:
            self._show_error("Load Failed", f"Failed to load deck: {str(e)}")
            self._log("ERROR", f"Failed to load deck: {str(e)}")
            return None

    def reload_current_deck(self) -> Optional[list[MTGCard]]:
        """
        Reload the currently loaded deck from file.

        Returns:
            List of reloaded cards, or None if no current deck or failed
        """
        if not self._last_loaded_deck_path:
            self._show_warning(
                "No Current Deck", "No deck file currently loaded to reload"
            )
            return None

        return self.load_deck_from_file(self._last_loaded_deck_path)

    def save_deck_to_yaml(
        self,
        cards: list[MTGCard],
        deck_name: Optional[str] = None,
        theme: str = "deck",
        create_backup: bool = False,
    ) -> bool:
        """
        Save deck to YAML file with auto-generated structure.

        Args:
            cards: List of cards to save
            deck_name: Name of the deck (uses current if None)
            theme: Theme metadata for the deck
            create_backup: Whether to create timestamped backup

        Returns:
            True if save successful, False otherwise
        """
        if not cards:
            self._show_warning("No Cards", "No cards to save")
            return False

        # Use provided deck name or current deck name
        save_deck_name = deck_name or self._current_deck_name
        if not save_deck_name:
            self._show_error("No Deck Name", "Please provide a deck name")
            return False

        try:
            # Create deck directory structure
            deck_dir = self._create_deck_directory_structure(save_deck_name)

            # Create YAML file path
            yaml_path = deck_dir / f"{save_deck_name}.yaml"

            # Create backup if requested
            if create_backup and yaml_path.exists():
                backup_dir = deck_dir / self.BACKUPS_SUBDIR
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = backup_dir / f"{save_deck_name}_{timestamp}.yaml"
                yaml_path.rename(backup_path)
                self._log("INFO", f"Created backup: {backup_path.name}")

            # Prepare deck data
            deck_data = {
                "metadata": {
                    "name": save_deck_name,
                    "theme": theme,
                    "created_at": datetime.now().isoformat(),
                    "total_cards": len(cards),
                },
                "cards": [self._mtg_card_to_dict(card) for card in cards],
            }

            # Save to YAML file
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    deck_data,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )

            # Update tracking information
            self._current_deck_name = save_deck_name
            self._last_loaded_deck_path = str(yaml_path)

            self._log("SUCCESS", f"Saved deck: {save_deck_name} ({len(cards)} cards)")
            return True

        except Exception as e:
            self._show_error("Save Failed", f"Failed to save deck: {str(e)}")
            self._log("ERROR", f"Failed to save deck: {str(e)}")
            return False

    # Public API Methods - CSV Operations

    def import_csv_with_dialog(self) -> Optional[list[MTGCard]]:
        """
        Show file dialog and import deck from CSV file.

        Returns:
            List of imported cards, or None if cancelled/failed
        """
        csv_file, _ = self.dialog_provider.get_open_filename(
            self.parent_widget, "Import CSV Deck", "", self.CSV_FILTER
        )

        if csv_file:
            return self.import_csv_from_file(csv_file)
        return None

    def import_csv_from_file(self, filename: str) -> Optional[list[MTGCard]]:
        """
        Import deck from a specific CSV file.

        Args:
            filename: Path to the CSV file

        Returns:
            List of imported cards, or None if failed
        """
        try:
            cards = []
            # Import MTGCard at runtime to avoid circular dependencies
            if "mtg_deck_builder" not in sys.modules:
                root_path = Path(__file__).parent.parent.parent
                if str(root_path) not in sys.path:
                    sys.path.insert(0, str(root_path))
                from mtg_deck_builder import MTGCard as MTGCardClass
            else:
                from mtg_deck_builder import MTGCard as MTGCardClass

            with open(filename, encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=";")
                for i, row in enumerate(reader, start=1):
                    # Create card with basic data
                    card = MTGCardClass(
                        id=int(row.get("ID", i)),
                        name=row.get("Name", f"Card {i}"),
                        type=row.get("Type", "Unknown"),
                        cost=row.get("Cost", ""),
                        text=row.get("Text", ""),
                        power=int(row["Power"])
                        if row.get("Power") and row["Power"].isdigit()
                        else None,
                        toughness=int(row["Toughness"])
                        if row.get("Toughness") and row["Toughness"].isdigit()
                        else None,
                        flavor=row.get("Flavor", ""),
                        rarity=row.get("Rarity", "common"),
                        art=row.get("Art", ""),
                        set=row.get("Set", "CMD"),  # Default set
                        status=row.get("Status", "pending"),
                        image_path=row.get("Image_Path"),
                        card_path=row.get("Card_Path"),
                        generated_at=row.get("Generated_At"),
                        generation_status=row.get("Generation_Status", "pending"),
                        custom_image_path=row.get("Custom_Image_Path"),
                    )
                    cards.append(card)

            if cards:
                self._log("SUCCESS", f"Imported {len(cards)} cards from CSV")
                self._show_info(
                    "Import Success",
                    f"Successfully imported {len(cards)} cards from CSV",
                )
                return cards
            else:
                self._show_warning("No Cards", "No cards found in CSV file")
                return None

        except Exception as e:
            self._show_error("Import Failed", f"Failed to import CSV: {str(e)}")
            self._log("ERROR", f"CSV import failed: {str(e)}")
            return None

    def export_csv_with_dialog(self, cards: list[MTGCard]) -> bool:
        """
        Show file dialog and export deck to CSV file.

        Args:
            cards: List of cards to export

        Returns:
            True if export successful, False otherwise
        """
        if not cards:
            self._show_warning("No Deck", "Please load a deck first!")
            return False

        # Get default path
        default_path = self.get_default_csv_export_path()

        # Ask user for CSV save location
        csv_file, _ = self.dialog_provider.get_save_filename(
            self.parent_widget, "Export Deck to CSV", default_path, self.CSV_FILTER
        )

        if csv_file:
            return self.export_csv_to_file(cards, csv_file)
        return False

    def export_csv_to_file(self, cards: list[MTGCard], filename: str) -> bool:
        """
        Export deck to a specific CSV file.

        Args:
            cards: List of cards to export
            filename: Path to save the CSV file

        Returns:
            True if export successful, False otherwise
        """
        try:
            # Write CSV with semicolon delimiter for better Excel compatibility
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f, fieldnames=self.CSV_FIELDNAMES, delimiter=";"
                )

                # Write header
                writer.writeheader()

                # Write cards
                for card in cards:
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
                            "Set": getattr(card, "set", "CMD"),
                            "Status": getattr(card, "status", "pending"),
                            "Image_Path": getattr(card, "image_path", ""),
                            "Card_Path": getattr(card, "card_path", ""),
                            "Generated_At": getattr(card, "generated_at", ""),
                            "Generation_Status": getattr(
                                card, "generation_status", "pending"
                            ),
                            "Custom_Image_Path": getattr(card, "custom_image_path", ""),
                        }
                    )

            # Log success
            self._log(
                "SUCCESS", f"Exported {len(cards)} cards to CSV: {Path(filename).name}"
            )
            self._show_info(
                "Export Success",
                f"Successfully exported {len(cards)} cards to: {Path(filename).name}",
            )
            return True

        except Exception as e:
            self._show_error("Export Failed", f"Failed to export CSV: {str(e)}")
            self._log("ERROR", f"CSV export failed: {str(e)}")
            return False

    # Public API Methods - Directory Management

    def get_deck_directory(self, deck_name: Optional[str] = None) -> Optional[Path]:
        """
        Get the directory path for a deck.

        Args:
            deck_name: Name of the deck (uses current if None)

        Returns:
            Path to deck directory, or None if no deck name available
        """
        deck_name = deck_name or self._current_deck_name
        if not deck_name:
            return None
        return Path(self.SAVED_DECKS_DIR) / deck_name

    def get_rendered_cards_directory(
        self, deck_name: Optional[str] = None
    ) -> Optional[Path]:
        """
        Get the rendered cards directory path for a deck.

        Args:
            deck_name: Name of the deck (uses current if None)

        Returns:
            Path to rendered cards directory, or None if no deck name available
        """
        deck_dir = self.get_deck_directory(deck_name)
        if not deck_dir:
            return None
        return deck_dir / self.RENDERED_CARDS_SUBDIR

    def get_artwork_directory(self, deck_name: Optional[str] = None) -> Optional[Path]:
        """
        Get the artwork directory path for a deck.

        Args:
            deck_name: Name of the deck (uses current if None)

        Returns:
            Path to artwork directory, or None if no deck name available
        """
        deck_dir = self.get_deck_directory(deck_name)
        if not deck_dir:
            return None
        return deck_dir / self.ARTWORK_SUBDIR

    def ensure_deck_directories(self, deck_name: Optional[str] = None) -> bool:
        """
        Ensure all necessary directories exist for a deck.

        Args:
            deck_name: Name of the deck (uses current if None)

        Returns:
            True if directories created/exist, False otherwise
        """
        deck_name = deck_name or self._current_deck_name
        if not deck_name:
            return False

        try:
            self._create_deck_directory_structure(deck_name)
            return True
        except Exception as e:
            self._log(
                "ERROR", f"Failed to create directories for deck {deck_name}: {str(e)}"
            )
            return False

    # Public API Methods - Status Synchronization

    def sync_card_status_with_files(self, cards: list[MTGCard]) -> int:
        """
        Synchronize card status based on existing rendered files.

        Args:
            cards: List of cards to synchronize

        Returns:
            Number of cards whose status was updated
        """
        if not self._current_deck_name:
            self._log("WARNING", "Cannot sync card status: no deck name set")
            return 0

        # Get rendered files set
        rendered_files = self.get_rendered_card_files()

        # Update card status based on rendered files
        updated_count = 0
        for card in cards:
            safe_name = self._ensure_safe_filename(card.name)
            old_status = getattr(card, "status", "pending")

            if safe_name in rendered_files:
                # If file exists and status is not already completed, update it
                if old_status != "completed":
                    card.status = "completed"
                    updated_count += 1
            else:
                # If file doesn't exist and status is completed, mark as pending
                if old_status == "completed":
                    card.status = "pending"
                    updated_count += 1
                elif not hasattr(card, "status"):
                    card.status = "pending"

        if updated_count > 0:
            self._log(
                "INFO",
                f"Synchronized status for {updated_count} cards based on existing rendered files",
            )

        return updated_count

    def get_rendered_card_files(self, deck_name: Optional[str] = None) -> set[str]:
        """
        Get set of rendered card filenames (without extension).

        Args:
            deck_name: Name of the deck (uses current if None)

        Returns:
            Set of rendered card filenames
        """
        rendered_dir = self.get_rendered_cards_directory(deck_name)
        if not rendered_dir or not rendered_dir.exists():
            return set()

        # Get list of rendered cards
        rendered_files = set()
        for file_path in rendered_dir.glob("*.png"):
            rendered_files.add(file_path.stem)  # Get filename without extension

        return rendered_files

    # Public API Methods - File Validation

    def validate_yaml_file(self, filename: str) -> tuple[bool, Optional[str]]:
        """
        Validate that a YAML file can be loaded.

        Args:
            filename: Path to the YAML file

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            with open(filename, encoding="utf-8") as f:
                yaml.safe_load(f)
            return True, None
        except FileNotFoundError:
            return False, f"File not found: {filename}"
        except yaml.YAMLError as e:
            return False, f"YAML parsing error: {str(e)}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"

    def validate_csv_file(self, filename: str) -> tuple[bool, Optional[str]]:
        """
        Validate that a CSV file can be loaded.

        Args:
            filename: Path to the CSV file

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            with open(filename, encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=";")
                # Try to read first row to validate format
                next(reader, None)
            return True, None
        except FileNotFoundError:
            return False, f"File not found: {filename}"
        except Exception as e:
            return False, f"CSV validation error: {str(e)}"

    # Public API Methods - Utility

    def get_default_csv_export_path(self, deck_name: Optional[str] = None) -> str:
        """
        Get default path for CSV export.

        Args:
            deck_name: Name of the deck (uses current if None)

        Returns:
            Default CSV export path
        """
        deck_name = deck_name or self._current_deck_name
        if deck_name:
            # Use the deck's own folder in saved_decks
            deck_folder = Path(self.SAVED_DECKS_DIR) / deck_name
            deck_folder.mkdir(parents=True, exist_ok=True)  # Ensure folder exists
            return str(deck_folder / f"{deck_name}.csv")
        else:
            return "deck_export.csv"

    def cleanup_old_backups(
        self, deck_name: Optional[str] = None, keep_count: int = 10
    ) -> int:
        """
        Clean up old backup files, keeping only the most recent ones.

        Args:
            deck_name: Name of the deck (uses current if None)
            keep_count: Number of backups to keep

        Returns:
            Number of backups removed
        """
        deck_dir = self.get_deck_directory(deck_name)
        if not deck_dir:
            return 0

        backup_dir = deck_dir / self.BACKUPS_SUBDIR
        if not backup_dir.exists():
            return 0

        try:
            # Get all backup files sorted by modification time (newest first)
            backup_files = list(backup_dir.glob("*.yaml"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            # Remove old backups beyond keep_count
            removed_count = 0
            for old_backup in backup_files[keep_count:]:
                old_backup.unlink()
                removed_count += 1

            if removed_count > 0:
                self._log("INFO", f"Cleaned up {removed_count} old backup files")

            return removed_count

        except Exception as e:
            self._log("ERROR", f"Failed to cleanup backups: {str(e)}")
            return 0

    def get_deck_metadata(self, filename: str) -> Optional[dict[str, Any]]:
        """
        Get metadata from a deck YAML file without loading all cards.

        Args:
            filename: Path to the YAML file

        Returns:
            Dictionary of metadata, or None if failed
        """
        try:
            with open(filename, encoding="utf-8") as f:
                deck_data = yaml.safe_load(f)

            if not deck_data:
                return None

            # Return metadata section if it exists, otherwise create basic metadata
            metadata = deck_data.get("metadata", {})
            if not metadata:
                # Create basic metadata from file info
                file_path = Path(filename)
                card_count = 0
                if "cards" in deck_data:
                    card_count += len(deck_data["cards"])
                if "commander" in deck_data:
                    card_count += 1

                metadata = {
                    "name": file_path.stem,
                    "total_cards": card_count,
                    "file_size": file_path.stat().st_size,
                    "modified_at": datetime.fromtimestamp(
                        file_path.stat().st_mtime
                    ).isoformat(),
                }

            return metadata

        except Exception as e:
            self._log(
                "ERROR", f"Failed to read deck metadata from {filename}: {str(e)}"
            )
            return None

    # Context manager support for batch operations
    def __enter__(self):
        """Enter context manager for batch file operations."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and cleanup resources."""
        # Reset any temporary state
        self._ignore_next_change = False
