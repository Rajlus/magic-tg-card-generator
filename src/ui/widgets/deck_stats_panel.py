"""Deck statistics panel widget for MTG deck builder.

This widget provides comprehensive deck statistics display functionality,
including generation progress, card type distribution, and color identity information.
"""

from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class DeckStatsPanel(QWidget):
    """Statistics panel widget for displaying deck information.

    This widget provides display for:
    1. Generation progress (completed/total cards and percentage)
    2. Card type distribution statistics
    3. Deck color identity and commander information
    4. Color identity warnings and violations

    All statistics are updated via methods to maintain clean separation
    between UI display and data calculation logic.
    """

    # Signals for user interactions (if any are added in future)
    stats_clicked = pyqtSignal(str)  # Future: clicking stats could trigger actions

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the deck statistics panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize the user interface components."""
        # Main vertical layout for all statistics
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)

        # Generation progress section
        self._create_generation_stats_section(main_layout)

        # Card type statistics section
        self._create_type_stats_section(main_layout)

        # Color identity section
        self._create_color_stats_section(main_layout)

        self.setLayout(main_layout)

    def _create_generation_stats_section(self, parent_layout: QVBoxLayout) -> None:
        """Create the generation statistics section.

        Args:
            parent_layout: Parent layout to add the section to
        """
        # Generation progress layout
        gen_stats_layout = QHBoxLayout()

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
        self.generation_stats_label.setToolTip("Shows current generation progress")

        gen_stats_layout.addWidget(self.generation_stats_label)
        gen_stats_layout.addStretch()  # Push to left

        parent_layout.addLayout(gen_stats_layout)

    def _create_type_stats_section(self, parent_layout: QVBoxLayout) -> None:
        """Create the card type statistics section.

        Args:
            parent_layout: Parent layout to add the section to
        """
        # Type statistics layout
        type_stats_layout = QHBoxLayout()

        # Card type stats label
        self.type_stats_label = QLabel(
            "📊 Total: 0 | Lands: 0 | Creatures: 0 | Instants: 0 | Sorceries: 0"
        )
        self.type_stats_label.setStyleSheet("padding: 5px; color: #888;")
        self.type_stats_label.setToolTip("Shows distribution of card types in the deck")

        type_stats_layout.addWidget(self.type_stats_label)
        type_stats_layout.addStretch()  # Push to left

        parent_layout.addLayout(type_stats_layout)

    def _create_color_stats_section(self, parent_layout: QVBoxLayout) -> None:
        """Create the color identity statistics section.

        Args:
            parent_layout: Parent layout to add the section to
        """
        # Color identity section
        self.color_label = QLabel("🎨 Colors: -")
        self.color_label.setWordWrap(True)
        self.color_label.setStyleSheet(
            "font-weight: bold; color: #ce9178; padding: 5px;"
        )
        self.color_label.setToolTip(
            "Shows deck color identity and commander information"
        )

        parent_layout.addWidget(self.color_label)

    # Generation Statistics Methods

    def update_generation_progress(
        self, completed: int, total: int, generating: int = 0
    ) -> None:
        """Update the generation progress display.

        Args:
            completed: Number of completed cards
            total: Total number of cards in deck
            generating: Number of cards currently being generated (optional)
        """
        if total == 0:
            percentage = 0
        else:
            percentage = int((completed / total) * 100)

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

    def set_generation_status(
        self, status_text: str, status_type: str = "normal"
    ) -> None:
        """Set a custom generation status message.

        Args:
            status_text: Custom status text to display
            status_type: Status type ("normal", "generating", "completed", "error")
        """
        self.generation_stats_label.setText(status_text)

        if status_type == "completed":
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
        elif status_type == "generating":
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
        elif status_type == "error":
            self.generation_stats_label.setStyleSheet(
                """
                QLabel {
                    font-weight: bold;
                    font-size: 14px;
                    padding: 8px;
                    background-color: #4a2a2a;
                    border: 1px solid #f44336;
                    border-radius: 4px;
                    color: #f44336;
                }
            """
            )
        else:  # normal
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

    # Type Statistics Methods

    def update_type_statistics(
        self,
        total: int = 0,
        lands: int = 0,
        creatures: int = 0,
        instants: int = 0,
        sorceries: int = 0,
        artifacts: int = 0,
        enchantments: int = 0,
    ) -> None:
        """Update the card type distribution display.

        Args:
            total: Total number of cards
            lands: Number of land cards
            creatures: Number of creature cards
            instants: Number of instant cards
            sorceries: Number of sorcery cards
            artifacts: Number of artifact cards
            enchantments: Number of enchantment cards
        """
        stats_text = (
            f"📊 Total: {total} | Lands: {lands} | Creatures: {creatures} | "
            f"Instants: {instants} | Sorceries: {sorceries} | "
            f"Artifacts: {artifacts} | Enchantments: {enchantments}"
        )
        self.type_stats_label.setText(stats_text)

    def set_type_statistics_text(self, stats_text: str) -> None:
        """Set custom type statistics text.

        Args:
            stats_text: Custom statistics text to display
        """
        self.type_stats_label.setText(stats_text)

    # Color Identity Methods

    def update_color_identity(
        self,
        deck_colors: str,
        commander_name: str = "",
        commander_colors: str = "",
        has_warnings: bool = False,
        warning_text: str = "",
    ) -> None:
        """Update the color identity and commander information display.

        Args:
            deck_colors: Deck color identity text
            commander_name: Name of the commander (optional)
            commander_colors: Commander color identity (optional)
            has_warnings: Whether there are color identity violations
            warning_text: Warning text for violations (optional)
        """
        # Build color label text
        color_label_text = f"🎨 Deck Colors: {deck_colors}\n"

        if commander_name:
            # Truncate long commander names for display
            display_name = (
                commander_name[:30] if len(commander_name) > 30 else commander_name
            )
            color_label_text += f"👑 Commander ({display_name}): {commander_colors}"

        if warning_text:
            color_label_text += f"\n{warning_text}"

        self.color_label.setText(color_label_text)

        # Set appropriate styling based on warnings
        if has_warnings:
            self.color_label.setStyleSheet(
                "font-weight: bold; color: #f48771; padding: 5px;"
            )  # Red for warning
        else:
            self.color_label.setStyleSheet(
                "font-weight: bold; color: #4ec9b0; padding: 5px;"
            )  # Green for valid

    def set_color_text(self, color_text: str, has_warnings: bool = False) -> None:
        """Set custom color identity text.

        Args:
            color_text: Custom color identity text to display
            has_warnings: Whether to style as warning (red) or normal (green)
        """
        self.color_label.setText(color_text)

        if has_warnings:
            self.color_label.setStyleSheet(
                "font-weight: bold; color: #f48771; padding: 5px;"
            )
        else:
            self.color_label.setStyleSheet(
                "font-weight: bold; color: #4ec9b0; padding: 5px;"
            )

    # Theme Information Methods (for future use)

    def update_theme_info(self, theme_text: str) -> None:
        """Update theme information display.

        Args:
            theme_text: Current theme text to display
        """
        # For now, we can add this to the generation stats if needed
        # This method is provided for future theme display requirements
        pass

    # Utility Methods

    def get_generation_label(self) -> QLabel:
        """Get the generation statistics label widget.

        Returns:
            The generation statistics QLabel widget
        """
        return self.generation_stats_label

    def get_type_label(self) -> QLabel:
        """Get the type statistics label widget.

        Returns:
            The type statistics QLabel widget
        """
        return self.type_stats_label

    def get_color_label(self) -> QLabel:
        """Get the color identity label widget.

        Returns:
            The color identity QLabel widget
        """
        return self.color_label

    def reset_all_statistics(self) -> None:
        """Reset all statistics to default values."""
        self.update_generation_progress(0, 0)
        self.update_type_statistics()
        self.set_color_text("🎨 Colors: -")

    def set_all_enabled(self, enabled: bool) -> None:
        """Enable or disable all statistics displays.

        Args:
            enabled: Whether the statistics should be enabled
        """
        self.generation_stats_label.setEnabled(enabled)
        self.type_stats_label.setEnabled(enabled)
        self.color_label.setEnabled(enabled)

    def get_current_statistics(self) -> dict[str, str]:
        """Get the current text of all statistics displays.

        Returns:
            Dictionary containing current statistics text
        """
        return {
            "generation": self.generation_stats_label.text(),
            "types": self.type_stats_label.text(),
            "colors": self.color_label.text(),
        }
