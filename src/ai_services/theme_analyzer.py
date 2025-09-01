"""
Theme Analyzer AI Service for MTG deck themes.

This module provides the ThemeAnalyzer service for analyzing MTG deck themes.
"""

from .base_ai_service import AIService


class ThemeAnalyzer(AIService):
    """AI service specialized for analyzing MTG deck themes."""

    def get_system_prompt(self) -> str:
        """Get the system prompt for theme analysis."""
        return """You are an MTG Set Design Expert. Analyze the given theme and provide:
1. Color Identity (primary and secondary colors with reasoning)
2. Suggested Commander(s)
3. Key mechanics that fit the theme
4. Important characters/locations for legendary cards
5. Overall deck strategy

Format your response clearly with sections."""

    def analyze_theme(
        self, theme: str, progress_callback=None, log_callback=None
    ) -> str:
        """
        Analyze a deck theme and provide strategic recommendations.

        Args:
            theme: The deck theme to analyze
            progress_callback: Optional callback for progress updates
            log_callback: Optional callback for logging

        Returns:
            Theme analysis with color identity, commanders, mechanics, etc.
        """
        return self.make_api_call(
            prompt=theme,
            task_type="analyze_theme",
            progress_callback=progress_callback,
            log_callback=log_callback,
        )
