"""
AIWorker class - QThread wrapper for AI services.

This module provides the AIWorker class that maintains backward compatibility
with the existing GUI while using the new AI service architecture.
"""

from PyQt6.QtCore import QThread, pyqtSignal

from .art_description_generator import ArtDescriptionGenerator
from .base_ai_service import AIService
from .card_generator import CardGenerator
from .theme_analyzer import ThemeAnalyzer


class AIWorker(QThread):
    """Worker thread for AI API calls using the new AI service architecture."""

    result_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    progress_update = pyqtSignal(str)
    log_message = pyqtSignal(str, str)  # level, message - for thread-safe logging

    def __init__(self, ai_service: AIService = None):
        """
        Initialize AIWorker with an AI service.

        Args:
            ai_service: Specific AI service to use, or None to auto-select
        """
        super().__init__()
        self.ai_service = ai_service
        self.task = ""
        self.prompt = ""

        # Service instances for auto-selection
        self._theme_analyzer = None
        self._card_generator = None
        self._art_generator = None

    def set_task(self, task: str, prompt: str):
        """Set the task and prompt for the AI worker."""
        self.task = task
        self.prompt = prompt

    def _get_service_for_task(self) -> AIService:
        """Get the appropriate AI service for the current task."""
        if self.ai_service:
            # Use explicitly provided service
            return self.ai_service

        # Auto-select service based on task
        if self.task == "analyze_theme":
            if not self._theme_analyzer:
                self._theme_analyzer = ThemeAnalyzer()
            return self._theme_analyzer
        elif self.task == "generate_cards":
            if not self._card_generator:
                self._card_generator = CardGenerator()
            return self._card_generator
        elif self.task == "generate_art":
            if not self._art_generator:
                self._art_generator = ArtDescriptionGenerator()
            return self._art_generator
        else:
            # Default to theme analyzer for unknown tasks
            if not self._theme_analyzer:
                self._theme_analyzer = ThemeAnalyzer()
            return self._theme_analyzer

    def run(self):
        """Execute AI request using the appropriate service."""
        try:
            service = self._get_service_for_task()

            # Create callback functions for progress and logging
            def progress_callback(message: str):
                self.progress_update.emit(message)

            def log_callback(level: str, message: str):
                self.log_message.emit(level, message)

            # Make the API call through the service
            if self.task == "analyze_theme":
                result = service.analyze_theme(
                    self.prompt,
                    progress_callback=progress_callback,
                    log_callback=log_callback,
                )
            elif self.task == "generate_cards":
                result = service.generate_cards(
                    self.prompt,
                    progress_callback=progress_callback,
                    log_callback=log_callback,
                )
            elif self.task == "generate_art":
                result = service.generate_art_descriptions(
                    self.prompt,
                    progress_callback=progress_callback,
                    log_callback=log_callback,
                )
            else:
                # Generic API call for other tasks
                result = service.make_api_call(
                    self.prompt,
                    task_type=self.task,
                    progress_callback=progress_callback,
                    log_callback=log_callback,
                )

            self.result_ready.emit(result)

        except Exception as e:
            error_msg = f"AI Worker Error: {str(e)}"
            self.log_message.emit("ERROR", error_msg)
            self.error_occurred.emit(error_msg)
