"""
Card Generator AI Service for MTG card creation.

This module provides the CardGenerator service for generating MTG cards.
"""

from .base_ai_service import AIService


class CardGenerator(AIService):
    """AI service specialized for generating MTG cards."""

    def get_system_prompt(self) -> str:
        """Get the system prompt for card generation."""
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

CRITICAL REQUIREMENTS:
- Generate ALL 100 cards in correct order
- Follow MTG rules and formatting exactly
- Ensure cards fit the specified theme
- Include proper mana costs and abilities
- Create balanced, playable cards
- Use appropriate rarities (1 mythic commander, ~8 rares, rest uncommon/common)

DO NOT provide explanations or commentary - ONLY the card list in the specified format."""

    def generate_cards(
        self, theme_prompt: str, progress_callback=None, log_callback=None
    ) -> str:
        """
        Generate a complete 100-card MTG Commander deck.

        Args:
            theme_prompt: The theme and requirements for the deck
            progress_callback: Optional callback for progress updates
            log_callback: Optional callback for logging

        Returns:
            Complete formatted card list for 100 cards
        """
        return self.make_api_call(
            prompt=theme_prompt,
            task_type="generate_cards",
            progress_callback=progress_callback,
            log_callback=log_callback,
        )
