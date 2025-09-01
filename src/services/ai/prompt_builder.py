"""
Prompt Builder Module

This module provides sophisticated prompt building capabilities for AI services,
including templates for different types of card generation and style variations.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union

from src.domain.models.mtg_card import MTGCard

logger = logging.getLogger(__name__)


@dataclass
class PromptTemplate:
    """Template for building prompts."""

    name: str
    template: str
    variables: list[str] = field(default_factory=list)
    description: str = ""
    category: str = "general"


class PromptBuilder:
    """
    Advanced prompt builder for AI-powered card generation.

    This class provides templates and utilities for building effective prompts
    for both text and image generation AI models.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize the prompt builder.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.templates: dict[str, PromptTemplate] = {}
        self.art_styles: dict[str, dict[str, str]] = {}

        # Initialize default templates and styles
        self._load_default_templates()
        self._load_art_styles()

        logger.info(f"PromptBuilder initialized with {len(self.templates)} templates")

    def _load_default_templates(self) -> None:
        """Load default prompt templates."""

        # Card text generation templates
        self.templates["creature_text"] = PromptTemplate(
            name="creature_text",
            template="""Generate rules text for a Magic: The Gathering creature card with the following specifications:

Name: {card_name}
Type: {card_type}
Mana Cost: {mana_cost}
Power/Toughness: {power}/{toughness}

Requirements:
- Create balanced, flavorful abilities that fit the mana cost
- Use proper Magic: The Gathering templating and keywords
- Make abilities synergistic with the creature's theme
- Consider the power level appropriate for the mana cost
{additional_requirements}

Generate ONLY the rules text, no flavor text.""",
            variables=[
                "card_name",
                "card_type",
                "mana_cost",
                "power",
                "toughness",
                "additional_requirements",
            ],
            description="Template for generating creature card rules text",
            category="text_generation",
        )

        self.templates["spell_text"] = PromptTemplate(
            name="spell_text",
            template="""Generate rules text for a Magic: The Gathering {card_type} spell with these specifications:

Name: {card_name}
Type: {card_type}
Mana Cost: {mana_cost}

Requirements:
- Create an effect that matches the card name and mana cost
- Use proper Magic: The Gathering templating
- Balance the power level with the mana cost
- Consider the card type's typical effects and limitations
{additional_requirements}

Generate ONLY the rules text.""",
            variables=[
                "card_name",
                "card_type",
                "mana_cost",
                "additional_requirements",
            ],
            description="Template for generating spell card rules text",
            category="text_generation",
        )

        self.templates["flavor_text"] = PromptTemplate(
            name="flavor_text",
            template="""Generate evocative flavor text for a Magic: The Gathering card:

Card Name: {card_name}
Type: {card_type}
Rules Text: {rules_text}
Setting/Theme: {theme}

Requirements:
- 1-2 sentences maximum
- Capture the card's essence and mood
- Use evocative, fantasy-appropriate language
- Avoid explaining game mechanics
- Make it memorable and atmospheric
{additional_requirements}

Generate ONLY the flavor text in quotes.""",
            variables=[
                "card_name",
                "card_type",
                "rules_text",
                "theme",
                "additional_requirements",
            ],
            description="Template for generating flavor text",
            category="text_generation",
        )

        # Art generation templates
        self.templates["creature_art"] = PromptTemplate(
            name="creature_art",
            template="""{card_name}, {creature_description}, Magic: The Gathering card art, {art_style}, highly detailed fantasy illustration, dynamic pose, dramatic lighting, rich colors, professional game art quality, {additional_details}""",
            variables=[
                "card_name",
                "creature_description",
                "art_style",
                "additional_details",
            ],
            description="Template for creature artwork generation",
            category="art_generation",
        )

        self.templates["spell_art"] = PromptTemplate(
            name="spell_art",
            template="""{spell_effect_description}, Magic: The Gathering spell art, {art_style}, mystical energy, magical effects, dramatic composition, vibrant magical colors, professional game art quality, {additional_details}""",
            variables=["spell_effect_description", "art_style", "additional_details"],
            description="Template for spell artwork generation",
            category="art_generation",
        )

        self.templates["land_art"] = PromptTemplate(
            name="land_art",
            template="""{landscape_description}, Magic: The Gathering land art, {art_style}, sweeping vista, natural beauty, atmospheric perspective, rich environmental details, professional game art quality, {additional_details}""",
            variables=["landscape_description", "art_style", "additional_details"],
            description="Template for land artwork generation",
            category="art_generation",
        )

    def _load_art_styles(self) -> None:
        """Load predefined art styles."""
        self.art_styles = {
            "mtg_modern": {
                "description": "modern Magic: The Gathering art style",
                "keywords": "highly detailed, fantasy realism, professional TCG art, dramatic lighting",
            },
            "mtg_classic": {
                "description": "classic Magic: The Gathering art style",
                "keywords": "traditional fantasy art, oil painting style, detailed illustration",
            },
            "mtg_digital": {
                "description": "digital Magic: The Gathering art style",
                "keywords": "digital painting, high contrast, vibrant colors, sharp details",
            },
            "oil_painting": {
                "description": "oil painting style",
                "keywords": "oil painting, traditional art, painterly, rich textures",
            },
            "watercolor": {
                "description": "watercolor style",
                "keywords": "watercolor, soft edges, flowing colors, artistic",
            },
            "fantasy_realism": {
                "description": "fantasy realism style",
                "keywords": "photorealistic fantasy, detailed, cinematic lighting",
            },
        }

    def build_card_text_prompt(
        self,
        card_name: str,
        card_type: str,
        mana_cost: str = "",
        power: int | None = None,
        toughness: int | None = None,
        **kwargs,
    ) -> str:
        """
        Build a prompt for card text generation.

        Args:
            card_name: Name of the card
            card_type: Type of the card
            mana_cost: Mana cost string
            power: Creature power (if applicable)
            toughness: Creature toughness (if applicable)
            **kwargs: Additional variables for the template

        Returns:
            Generated prompt string
        """
        try:
            # Determine template based on card type
            if "creature" in card_type.lower() or "kreatur" in card_type.lower():
                template = self.templates["creature_text"]
                variables = {
                    "card_name": card_name,
                    "card_type": card_type,
                    "mana_cost": mana_cost or "Unknown",
                    "power": power if power is not None else "?",
                    "toughness": toughness if toughness is not None else "?",
                    "additional_requirements": kwargs.get(
                        "additional_requirements", ""
                    ),
                }
            else:
                template = self.templates["spell_text"]
                variables = {
                    "card_name": card_name,
                    "card_type": card_type,
                    "mana_cost": mana_cost or "Unknown",
                    "additional_requirements": kwargs.get(
                        "additional_requirements", ""
                    ),
                }

            # Add any additional variables from kwargs
            variables.update(kwargs)

            # Format the template
            prompt = template.template.format(**variables)
            logger.debug(f"Generated text prompt for {card_name}")
            return prompt

        except Exception as e:
            logger.error(f"Failed to build text prompt for {card_name}: {e}")
            return (
                f"Generate rules text for Magic: The Gathering card named {card_name}"
            )

    def build_flavor_text_prompt(
        self,
        card_name: str,
        card_type: str,
        rules_text: str = "",
        theme: str = "fantasy",
        **kwargs,
    ) -> str:
        """
        Build a prompt for flavor text generation.

        Args:
            card_name: Name of the card
            card_type: Type of the card
            rules_text: Rules text of the card
            theme: Thematic setting
            **kwargs: Additional variables

        Returns:
            Generated flavor text prompt
        """
        try:
            template = self.templates["flavor_text"]
            variables = {
                "card_name": card_name,
                "card_type": card_type,
                "rules_text": rules_text or "No rules text",
                "theme": theme,
                "additional_requirements": kwargs.get("additional_requirements", ""),
            }

            variables.update(kwargs)
            prompt = template.template.format(**variables)
            logger.debug(f"Generated flavor text prompt for {card_name}")
            return prompt

        except Exception as e:
            logger.error(f"Failed to build flavor text prompt for {card_name}: {e}")
            return f"Generate evocative flavor text for {card_name}"

    def build_art_prompt(
        self, card: MTGCard, style: str = "mtg_modern", additional_details: str = ""
    ) -> str:
        """
        Build a prompt for artwork generation.

        Args:
            card: MTGCard instance
            style: Art style to use
            additional_details: Additional details to include

        Returns:
            Generated art prompt
        """
        try:
            # Get style information
            style_info = self.art_styles.get(style, self.art_styles["mtg_modern"])
            art_style = f"{style_info['description']}, {style_info['keywords']}"

            # Determine template based on card type
            if card.is_creature():
                template = self.templates["creature_art"]
                creature_desc = self._generate_creature_description(card)
                variables = {
                    "card_name": card.name,
                    "creature_description": creature_desc,
                    "art_style": art_style,
                    "additional_details": additional_details,
                }
            elif card.is_land():
                template = self.templates["land_art"]
                landscape_desc = self._generate_landscape_description(card)
                variables = {
                    "landscape_description": landscape_desc,
                    "art_style": art_style,
                    "additional_details": additional_details,
                }
            else:
                template = self.templates["spell_art"]
                effect_desc = self._generate_spell_effect_description(card)
                variables = {
                    "spell_effect_description": effect_desc,
                    "art_style": art_style,
                    "additional_details": additional_details,
                }

            # Use existing art description if available
            if card.art and card.art.strip():
                # Enhance existing description with style
                prompt = f"{card.art}, {art_style}"
                if additional_details:
                    prompt += f", {additional_details}"
            else:
                # Generate from template
                prompt = template.template.format(**variables)

            logger.debug(f"Generated art prompt for {card.name}")
            return prompt

        except Exception as e:
            logger.error(f"Failed to build art prompt for {card.name}: {e}")
            return f"{card.name}, Magic: The Gathering card art, fantasy illustration"

    def _generate_creature_description(self, card: MTGCard) -> str:
        """Generate creature description from card data."""
        desc_parts = []

        # Add type-based description
        type_lower = card.type.lower()
        if "human" in type_lower:
            desc_parts.append("human")
        if "warrior" in type_lower:
            desc_parts.append("warrior")
        if "wizard" in type_lower:
            desc_parts.append("wizard")
        if "dragon" in type_lower:
            desc_parts.append("majestic dragon")
        if "angel" in type_lower:
            desc_parts.append("angelic being")
        if "demon" in type_lower:
            desc_parts.append("demonic creature")

        # Add power/toughness hints
        if card.power and card.toughness:
            if card.power >= 6:
                desc_parts.append("powerful")
            if card.toughness >= 6:
                desc_parts.append("resilient")
            if card.power == card.toughness:
                desc_parts.append("balanced")

        # Fallback if no specific description
        if not desc_parts:
            desc_parts = ["fantasy creature"]

        return ", ".join(desc_parts)

    def _generate_landscape_description(self, card: MTGCard) -> str:
        """Generate landscape description from card data."""
        name_lower = card.name.lower()

        if "mountain" in name_lower:
            return "towering mountain peaks, rocky terrain"
        elif "forest" in name_lower:
            return "lush forest, ancient trees"
        elif "island" in name_lower:
            return "tropical island, crystal clear waters"
        elif "plains" in name_lower:
            return "rolling plains, open grasslands"
        elif "swamp" in name_lower:
            return "dark swampland, murky waters"
        else:
            return "mystical landscape, magical terrain"

    def _generate_spell_effect_description(self, card: MTGCard) -> str:
        """Generate spell effect description from card data."""
        name_lower = card.name.lower()

        if "lightning" in name_lower or "bolt" in name_lower:
            return "crackling lightning bolt, electrical energy"
        elif "fire" in name_lower or "burn" in name_lower:
            return "raging flames, intense heat"
        elif "heal" in name_lower or "life" in name_lower:
            return "healing light, restorative magic"
        elif "counter" in name_lower:
            return "magical barrier, protective ward"
        elif "draw" in name_lower:
            return "swirling magical knowledge, mystical insight"
        else:
            return "magical spell effect, arcane energy"

    def add_custom_template(self, template: PromptTemplate) -> None:
        """
        Add a custom prompt template.

        Args:
            template: PromptTemplate instance to add
        """
        self.templates[template.name] = template
        logger.info(f"Added custom template: {template.name}")

    def add_custom_style(self, style_name: str, style_config: dict[str, str]) -> None:
        """
        Add a custom art style.

        Args:
            style_name: Name of the style
            style_config: Style configuration dictionary
        """
        self.art_styles[style_name] = style_config
        logger.info(f"Added custom art style: {style_name}")

    def list_templates(self, category: str | None = None) -> list[str]:
        """
        List available templates, optionally filtered by category.

        Args:
            category: Optional category filter

        Returns:
            List of template names
        """
        if category:
            return [
                name
                for name, template in self.templates.items()
                if template.category == category
            ]
        return list(self.templates.keys())

    def list_styles(self) -> list[str]:
        """
        List available art styles.

        Returns:
            List of style names
        """
        return list(self.art_styles.keys())

    def get_template(self, name: str) -> PromptTemplate | None:
        """
        Get a template by name.

        Args:
            name: Template name

        Returns:
            PromptTemplate instance or None if not found
        """
        return self.templates.get(name)

    def validate_prompt(self, prompt: str, min_length: int = 10) -> bool:
        """
        Validate a generated prompt.

        Args:
            prompt: Prompt string to validate
            min_length: Minimum required length

        Returns:
            True if prompt is valid
        """
        if not prompt or len(prompt.strip()) < min_length:
            return False

        # Check for placeholder variables that weren't replaced
        if "{" in prompt and "}" in prompt:
            logger.warning("Prompt contains unreplaced variables")
            return False

        return True

    def enhance_prompt(
        self,
        base_prompt: str,
        enhancements: list[str] | None = None,
        quality_modifiers: bool = True,
    ) -> str:
        """
        Enhance a base prompt with quality modifiers and additional details.

        Args:
            base_prompt: Base prompt to enhance
            enhancements: List of enhancement strings
            quality_modifiers: Whether to add quality modifiers

        Returns:
            Enhanced prompt string
        """
        enhanced = base_prompt.strip()

        # Add enhancements
        if enhancements:
            enhanced += ", " + ", ".join(enhancements)

        # Add quality modifiers
        if quality_modifiers:
            quality_terms = ["high quality", "detailed", "professional", "masterpiece"]
            enhanced += ", " + ", ".join(quality_terms)

        return enhanced

    def get_style_keywords(self, style: str) -> str:
        """
        Get keywords for a specific art style.

        Args:
            style: Style name

        Returns:
            Style keywords string
        """
        style_info = self.art_styles.get(style, self.art_styles["mtg_modern"])
        return style_info.get("keywords", "")
