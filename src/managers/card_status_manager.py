#!/usr/bin/env python3
"""
Card Status Manager

This module provides a manager class for handling card status operations
in the MTG Card Generator application. It encapsulates status tracking,
progress monitoring, and status-based filtering.

Extracted from CardManagementTab as part of issue #26 to improve code organization
and maintainability.
"""

from pathlib import Path
from typing import Any, Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QLabel


class CardStatusManager(QObject):
    """
    Manager class for handling card status operations.

    This class encapsulates status-related functionality including:
    - Status tracking and updates
    - Progress monitoring
    - Status synchronization with files
    - Statistics generation
    - Batch status operations
    """

    # Signals
    status_changed = pyqtSignal(object, str, str)  # card, old_status, new_status
    batch_status_updated = pyqtSignal(list, str)  # cards, new_status
    progress_updated = pyqtSignal(int, str)  # card_id, status
    generation_completed = pyqtSignal(int, bool, str)  # card_id, success, message
    stats_updated = pyqtSignal(dict)  # statistics dictionary

    # Status constants
    STATUS_PENDING = "pending"
    STATUS_GENERATING = "generating"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"

    VALID_STATUSES = {
        STATUS_PENDING,
        STATUS_GENERATING,
        STATUS_COMPLETED,
        STATUS_FAILED,
    }

    # Status display mapping
    STATUS_DISPLAY_MAP = {
        "completed": ("✅ Completed", "#d4edda"),  # Light green
        "generating": ("🔄 Generating", "#fff3cd"),  # Light yellow
        "failed": ("❌ Failed", "#f8d7da"),  # Light red
        "pending": ("⏸️ Pending", None),  # Default
    }

    def __init__(
        self,
        cards: list = None,
        table_manager=None,
        file_operations=None,
        logger=None,
    ):
        """
        Initialize the CardStatusManager.

        Args:
            cards: List of card objects to manage
            table_manager: Reference to table manager for UI updates
            file_operations: Reference to file operations manager
            logger: Logger for message logging
        """
        super().__init__()
        self.cards = cards or []
        self.table_manager = table_manager
        self.file_operations = file_operations
        self.logger = logger
        self.generation_stats_label = None

    def set_generation_stats_label(self, label: QLabel):
        """Set the generation stats label for UI updates"""
        self.generation_stats_label = label

    def _log_message(self, level: str, message: str):
        """Log a message using available logger"""
        if self.logger and hasattr(self.logger, "log_message"):
            self.logger.log_message(level, message)

    def _get_main_window(self):
        """Get reference to main window for logging"""
        try:
            from PyQt6.QtWidgets import QApplication

            app = QApplication.instance()
            if app:
                for widget in app.topLevelWidgets():
                    if widget.__class__.__name__ == "MainWindow":
                        return widget
        except:
            pass
        return None

    # Core status management methods

    def update_card_status(
        self, card_id: int, new_status: str, reason: str = ""
    ) -> bool:
        """
        Update the status of a specific card.

        Args:
            card_id: ID of the card to update
            new_status: New status value
            reason: Optional reason for status change

        Returns:
            True if update successful, False otherwise
        """
        if new_status not in self.VALID_STATUSES:
            self._log_message("ERROR", f"Invalid status: {new_status}")
            return False

        for card in self.cards:
            if card.id == card_id:
                old_status = getattr(card, "status", self.STATUS_PENDING)
                card.status = new_status

                # Emit signal
                self.status_changed.emit(card, old_status, new_status)

                # Log if reason provided
                if reason:
                    self._log_message(
                        "INFO",
                        f"Card {card.name} status: {old_status} → {new_status} ({reason})",
                    )

                return True

        return False

    def get_card_status(self, card_id: int) -> Optional[str]:
        """
        Get the status of a specific card.

        Args:
            card_id: ID of the card

        Returns:
            Status string or None if card not found
        """
        for card in self.cards:
            if card.id == card_id:
                return getattr(card, "status", self.STATUS_PENDING)
        return None

    def set_card_active(self, card_id: int) -> bool:
        """
        Set a card as active (ready for generation).

        Args:
            card_id: ID of the card

        Returns:
            True if successful
        """
        return self.update_card_status(card_id, self.STATUS_PENDING, "Set as active")

    def set_card_inactive(self, card_id: int) -> bool:
        """
        Set a card as inactive (skip generation).

        Args:
            card_id: ID of the card

        Returns:
            True if successful
        """
        for card in self.cards:
            if card.id == card_id:
                # Mark as completed to skip generation
                old_status = getattr(card, "status", self.STATUS_PENDING)
                card.status = self.STATUS_COMPLETED
                card.skip_generation = True  # Add flag for skipping
                self.status_changed.emit(card, old_status, self.STATUS_COMPLETED)
                return True
        return False

    def toggle_card_status(self, card_id: int) -> bool:
        """
        Toggle card status between pending and completed.

        Args:
            card_id: ID of the card

        Returns:
            True if successful
        """
        current_status = self.get_card_status(card_id)
        if current_status == self.STATUS_PENDING:
            return self.update_card_status(card_id, self.STATUS_COMPLETED, "Toggled")
        elif current_status == self.STATUS_COMPLETED:
            return self.update_card_status(card_id, self.STATUS_PENDING, "Toggled")
        return False

    def batch_status_update(
        self, card_ids: list[int], new_status: str
    ) -> dict[int, bool]:
        """
        Update status for multiple cards at once.

        Args:
            card_ids: List of card IDs to update
            new_status: New status to apply

        Returns:
            Dictionary mapping card ID to success status
        """
        if new_status not in self.VALID_STATUSES:
            self._log_message("ERROR", f"Invalid status for batch update: {new_status}")
            return {card_id: False for card_id in card_ids}

        results = {}
        updated_cards = []

        for card_id in card_ids:
            success = self.update_card_status(card_id, new_status, "Batch update")
            results[card_id] = success
            if success:
                for card in self.cards:
                    if card.id == card_id:
                        updated_cards.append(card)
                        break

        if updated_cards:
            self.batch_status_updated.emit(updated_cards, new_status)

        return results

    def filter_by_status(self, status: str) -> list:
        """
        Get all cards with a specific status.

        Args:
            status: Status to filter by

        Returns:
            List of cards with the specified status
        """
        if status not in self.VALID_STATUSES and status != "All":
            return []

        if status == "All":
            return self.cards

        return [
            card
            for card in self.cards
            if getattr(card, "status", self.STATUS_PENDING) == status
        ]

    def get_status_statistics(self) -> dict[str, Any]:
        """
        Get comprehensive statistics about card statuses.

        Returns:
            Dictionary with status counts and percentages
        """
        total = len(self.cards)
        stats = {
            "total": total,
            "completed": 0,
            "pending": 0,
            "generating": 0,
            "failed": 0,
            "completed_percentage": 0,
            "pending_percentage": 0,
            "generating_percentage": 0,
            "failed_percentage": 0,
        }

        if total == 0:
            return stats

        # Count statuses
        for card in self.cards:
            status = getattr(card, "status", self.STATUS_PENDING)
            if status == self.STATUS_COMPLETED:
                stats["completed"] += 1
            elif status == self.STATUS_PENDING:
                stats["pending"] += 1
            elif status == self.STATUS_GENERATING:
                stats["generating"] += 1
            elif status == self.STATUS_FAILED:
                stats["failed"] += 1

        # Calculate percentages
        stats["completed_percentage"] = int((stats["completed"] / total) * 100)
        stats["pending_percentage"] = int((stats["pending"] / total) * 100)
        stats["generating_percentage"] = int((stats["generating"] / total) * 100)
        stats["failed_percentage"] = int((stats["failed"] / total) * 100)

        return stats

    # Synchronization methods

    def manual_sync_status(self) -> int:
        """
        Manually sync card status based on whether cards have been generated.

        Returns:
            Number of cards updated
        """
        updated_count = 0

        for card in self.cards:
            old_status = getattr(card, "status", self.STATUS_PENDING)

            if hasattr(card, "card_path") and card.card_path:
                # Card has been generated (has a card image)
                if old_status != self.STATUS_COMPLETED:
                    card.status = self.STATUS_COMPLETED
                    updated_count += 1
                    self.status_changed.emit(card, old_status, self.STATUS_COMPLETED)
            else:
                # No card image, should be pending
                if old_status == self.STATUS_COMPLETED:
                    card.status = self.STATUS_PENDING
                    updated_count += 1
                    self.status_changed.emit(card, old_status, self.STATUS_PENDING)

        # Log the sync
        self._log_message(
            "INFO",
            f"🔄 Synchronized {updated_count} card statuses based on generated images",
        )

        # Update statistics
        stats = self.get_status_statistics()
        self._log_message(
            "SUCCESS",
            f"✅ Status synchronized: {stats['completed']} completed, {stats['pending']} pending",
        )

        # Emit stats update
        self.stats_updated.emit(stats)

        return updated_count

    def sync_card_status_with_rendered_files(self) -> int:
        """
        Synchronize card status based on existing rendered files.

        Returns:
            Number of cards updated
        """
        if self.file_operations:
            updated = self.file_operations.sync_card_status_with_files(self.cards)

            # Update statistics after sync
            stats = self.get_status_statistics()
            self.stats_updated.emit(stats)

            return updated
        return 0

    # Progress tracking methods

    def on_generation_progress(self, card_id: int, status: str):
        """
        Handle generation progress updates.

        Args:
            card_id: ID of the card being processed
            status: Current generation status message
        """
        # Find the card being processed
        current_card = None
        current_index = 0

        for i, card in enumerate(self.cards):
            if card.id == card_id:
                current_card = card
                current_index = i + 1
                break

        if current_card:
            total = len(self.cards)

            # Update the card status
            old_status = getattr(current_card, "status", self.STATUS_PENDING)
            current_card.status = self.STATUS_GENERATING

            if old_status != self.STATUS_GENERATING:
                self.status_changed.emit(
                    current_card, old_status, self.STATUS_GENERATING
                )

            # Update generation stats
            self.update_generation_stats()

            # Emit progress signal
            self.progress_updated.emit(card_id, status)

            # Log progress
            self._log_message(
                "INFO",
                f"[{current_index}/{total}] Generating {current_card.name}: {status}",
            )

    def on_generation_completed(
        self,
        card_id: int,
        success: bool,
        message: str,
        image_path: str = None,
        card_path: str = None,
    ):
        """
        Handle generation completion for a card.

        Args:
            card_id: ID of the completed card
            success: Whether generation was successful
            message: Completion message
            image_path: Path to generated artwork (optional)
            card_path: Path to generated card (optional)
        """
        # Find the card
        for card in self.cards:
            if card.id == card_id:
                old_status = getattr(card, "status", self.STATUS_PENDING)

                if success:
                    card.status = self.STATUS_COMPLETED
                    if image_path:
                        card.image_path = image_path
                    if card_path:
                        card.card_path = card_path
                else:
                    card.status = self.STATUS_FAILED

                # Emit status change
                self.status_changed.emit(card, old_status, card.status)

                # Update generation stats
                self.update_generation_stats()

                # Emit completion signal
                self.generation_completed.emit(card_id, success, message)

                # Log completion
                log_type = "INFO" if success else "ERROR"
                self._log_message(log_type, message)

                break

    def update_generation_stats(self):
        """Update the generation progress indicator"""
        # Get statistics
        stats = self.get_status_statistics()

        # Update label if available
        if self.generation_stats_label:
            total = stats["total"]
            completed = stats["completed"]
            pending = stats["pending"]
            failed = stats["failed"]
            generating = stats["generating"]
            percentage = stats["completed_percentage"]

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

        # Emit updated statistics
        self.stats_updated.emit(stats)

    def get_generation_progress(self) -> dict[str, Any]:
        """
        Get current generation progress information.

        Returns:
            Dictionary with progress details
        """
        stats = self.get_status_statistics()

        return {
            "total_cards": stats["total"],
            "completed": stats["completed"],
            "pending": stats["pending"],
            "generating": stats["generating"],
            "failed": stats["failed"],
            "percentage_complete": stats["completed_percentage"],
            "is_generating": stats["generating"] > 0,
            "all_completed": stats["completed_percentage"] == 100,
        }

    def reset_failed_cards(self) -> int:
        """
        Reset all failed cards back to pending status.

        Returns:
            Number of cards reset
        """
        reset_count = 0

        for card in self.cards:
            if getattr(card, "status", self.STATUS_PENDING) == self.STATUS_FAILED:
                card.status = self.STATUS_PENDING
                self.status_changed.emit(card, self.STATUS_FAILED, self.STATUS_PENDING)
                reset_count += 1

        if reset_count > 0:
            self._log_message("INFO", f"Reset {reset_count} failed cards to pending")
            self.update_generation_stats()

        return reset_count

    def get_cards_for_generation(self) -> list:
        """
        Get list of cards that need generation (pending or failed).

        Returns:
            List of cards ready for generation
        """
        return [
            card
            for card in self.cards
            if getattr(card, "status", self.STATUS_PENDING)
            in [self.STATUS_PENDING, self.STATUS_FAILED]
            and not getattr(card, "skip_generation", False)
        ]

    def set_cards(self, cards: list):
        """
        Update the cards list managed by this manager.

        Args:
            cards: New list of cards to manage
        """
        self.cards = cards
        self.update_generation_stats()
