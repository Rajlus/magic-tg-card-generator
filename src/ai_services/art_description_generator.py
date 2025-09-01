"""
Art Description Generator AI Service for MTG card artwork.

This module provides the ArtDescriptionGenerator service for creating card art descriptions.
"""

from .base_ai_service import AIService


class ArtDescriptionGenerator(AIService):
    """AI service specialized for generating MTG card art descriptions."""

    def get_system_prompt(self) -> str:
        """Get the system prompt for art description generation."""
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

    def generate_art_descriptions(
        self, card_list: str, progress_callback=None, log_callback=None
    ) -> str:
        """
        Generate detailed art descriptions for a list of MTG cards.

        Args:
            card_list: The formatted card list to generate art for
            progress_callback: Optional callback for progress updates
            log_callback: Optional callback for logging

        Returns:
            Detailed art descriptions for each card
        """
        return self.make_api_call(
            prompt=card_list,
            task_type="generate_art",
            progress_callback=progress_callback,
            log_callback=log_callback,
        )
