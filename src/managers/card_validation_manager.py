#!/usr/bin/env python3
"""
Card Validation Manager

This module provides a manager class for handling all validation-related functionality
in the MTG Card Generator application. It encapsulates commander color identity
validation, mana cost checking, and violation reporting.
"""

from typing import Optional


class CardValidationManager:
    """
    Manager class for handling all MTG card validation operations.

    This class encapsulates validation-related functionality including:
    - Commander color identity detection
    - Mana cost validation against commander colors
    - Color violation logging and reporting
    """

    def __init__(self, cards: Optional[list] = None, logger=None):
        """
        Initialize the validation manager.

        Args:
            cards: List of MTG cards to validate
            logger: Logger instance for output messages
        """
        self.cards = cards or []
        self.logger = logger
        self.commander_colors: set[str] = set()

    def update_cards(self, cards: list) -> None:
        """Update the cards list and refresh commander colors."""
        self.cards = cards
        self.commander_colors = self.get_commander_colors()

    def get_commander_colors(self) -> set[str]:
        """Get the color identity of the commander (first card or legendary creature)"""
        commander_colors = set()

        for card in self.cards:
            # Commander is usually the first card or a legendary creature
            if card.id == 1 or ("Legendary" in card.type and "Creature" in card.type):
                if self.logger and hasattr(self.logger, "log_message"):
                    self.logger.log_message(
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
                    if self.logger and hasattr(self.logger, "log_message"):
                        self.logger.log_message(
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

        # For colorless commanders (empty commander_colors set), only colorless cards are allowed
        # We need to distinguish between "not initialized" and "colorless commander"
        # If commander_colors is a set (even empty), it means it's been initialized

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
        if violation and card_colors and self.logger:
            if hasattr(self.logger, "log_message"):
                self.logger.log_message(
                    "DEBUG",
                    f"Color violation: Card has {card_colors}, Commander allows {self.commander_colors}",
                )

        return violation

    def log_color_violations(self) -> None:
        """Log all cards that violate commander color identity"""
        if not self.logger or not hasattr(self.logger, "log_message"):
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
            self.logger.log_message(
                "WARNING", f"Found {len(violations)} cards with color violations:"
            )
            for violation in violations:
                self.logger.log_message("WARNING", f"   {violation}")
            self.logger.log_message(
                "INFO", f"Commander colors allowed: {self.commander_colors}"
            )

    def validate_deck(self) -> dict:
        """
        Perform comprehensive deck validation.

        Returns:
            dict: Validation results with violations and statistics
        """
        result = {
            "commander_colors": self.commander_colors,
            "total_cards": len(self.cards),
            "violations": [],
            "valid_cards": [],
            "has_violations": False,
        }

        for card in self.cards:
            if self.check_color_violation(card.cost):
                result["violations"].append(
                    {
                        "card": card,
                        "name": card.name,
                        "cost": card.cost,
                        "reason": "Color identity violation",
                    }
                )
            else:
                result["valid_cards"].append(card)

        result["has_violations"] = len(result["violations"]) > 0
        result["violation_count"] = len(result["violations"])
        result["valid_count"] = len(result["valid_cards"])

        return result

    def set_commander_colors(self, colors: set[str]) -> None:
        """Manually set commander colors."""
        self.commander_colors = colors

    def get_card_colors(self, card_cost: str) -> set[str]:
        """Extract colors from a card's mana cost."""
        if not card_cost or card_cost == "-":
            return set()

        cost_str = str(card_cost).upper().replace("{", "").replace("}", "")
        card_colors = set()

        for color in ["W", "U", "B", "R", "G"]:
            if color in cost_str:
                card_colors.add(color)

        return card_colors

    def validate_card_data(self, card) -> tuple[bool, list[str]]:
        """
        Validate all aspects of a card's data.

        Args:
            card: MTG card object to validate

        Returns:
            tuple: (is_valid, list_of_errors)
        """
        errors = []

        # Handle None card
        if card is None:
            errors.append("Card object cannot be None")
            return False, errors

        # Check required fields with safe attribute access
        try:
            card_name = getattr(card, "name", None)
            if not card_name or (
                isinstance(card_name, str) and card_name.strip() == ""
            ):
                errors.append("Card name is required and cannot be empty")
            elif isinstance(card_name, str) and len(card_name.strip()) > 200:
                errors.append("Card name cannot exceed 200 characters")
        except:
            errors.append("Error accessing card name")

        try:
            card_type = getattr(card, "type", None)
            if not card_type or (
                isinstance(card_type, str) and card_type.strip() == ""
            ):
                errors.append("Card type is required and cannot be empty")
        except:
            errors.append("Error accessing card type")

        # Validate mana cost if present
        try:
            card_cost = getattr(card, "cost", None)
            if card_cost is not None:
                cost_valid, cost_errors = self.validate_mana_cost(card_cost)
                if not cost_valid:
                    errors.extend(cost_errors)
        except:
            errors.append("Error accessing card cost")

        # Validate type-specific requirements
        try:
            type_valid, type_errors = self.validate_card_type(card)
            if not type_valid:
                errors.extend(type_errors)
        except:
            errors.append("Error validating card type")

        # Validate power/toughness for creatures
        try:
            card_type = getattr(card, "type", "")
            if card_type and "Creature" in str(card_type):
                pt_valid, pt_errors = self.validate_power_toughness(card)
                if not pt_valid:
                    errors.extend(pt_errors)
        except:
            errors.append("Error validating power/toughness")

        # Validate card text
        try:
            card_text = getattr(card, "text", None)
            if card_text:
                text_valid, text_errors = self.validate_card_text(card_text)
                if not text_valid:
                    errors.extend(text_errors)
        except:
            errors.append("Error validating card text")

        return len(errors) == 0, errors

    def check_card_format(
        self, card, format_name: str = "commander"
    ) -> tuple[bool, list[str]]:
        """
        Check if a card is legal in the specified format.

        Args:
            card: MTG card object to check
            format_name: Format to check against (commander, standard, modern, etc.)

        Returns:
            tuple: (is_legal, list_of_issues)
        """
        issues = []

        # Format-specific banned lists (simplified for demonstration)
        banned_lists = {
            "commander": [
                "Black Lotus",
                "Ancestral Recall",
                "Time Walk",
                "Timetwister",
                "Mox Sapphire",
                "Mox Jet",
                "Mox Ruby",
                "Mox Emerald",
                "Mox Pearl",
            ],
            "standard": [
                "Black Lotus",
                "Lightning Bolt",
                "Counterspell",
                "Dark Ritual",
            ],
            "modern": [
                "Black Lotus",
                "Mental Misstep",
                "Gitaxian Probe",
                "Faithless Looting",
            ],
        }

        if not hasattr(card, "name") or not card.name:
            issues.append("Cannot check format legality - card has no name")
            return False, issues

        banned_cards = banned_lists.get(format_name.lower(), [])
        if card.name in banned_cards:
            issues.append(f"Card '{card.name}' is banned in {format_name} format")

        # Check color identity for Commander format
        if format_name.lower() == "commander":
            if hasattr(card, "cost") and self.check_color_violation(card.cost):
                issues.append(f"Card '{card.name}' violates commander color identity")

        return len(issues) == 0, issues

    def validate_mana_cost(self, mana_cost: str) -> tuple[bool, list[str]]:
        """
        Validate mana cost format and content.

        Args:
            mana_cost: Mana cost string to validate

        Returns:
            tuple: (is_valid, list_of_errors)
        """
        errors = []

        if not mana_cost:
            return True, []  # Empty mana cost is valid (0 cost spells)

        cost_str = str(mana_cost).strip()

        # Check for valid mana symbols
        valid_symbols = [
            "W",
            "U",
            "B",
            "R",
            "G",  # Basic colors
            "C",  # Colorless
            "X",
            "Y",
            "Z",  # Variable costs
            "{W}",
            "{U}",
            "{B}",
            "{R}",
            "{G}",  # Bracketed colors
            "{C}",
            "{X}",
            "{Y}",
            "{Z}",  # Bracketed variables
        ]

        # Add numbers 0-20 as valid
        for i in range(21):
            valid_symbols.extend([str(i), f"{{{i}}}"])

        # Add hybrid mana symbols
        hybrid_symbols = [
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
            "{2/W}",
            "{2/U}",
            "{2/B}",
            "{2/R}",
            "{2/G}",
        ]
        valid_symbols.extend(hybrid_symbols)

        # Simple validation - check if cost contains only valid characters
        import re

        if not re.match(r"^[0-9WUBRGCXYZ{}/]*$", cost_str):
            errors.append(f"Mana cost contains invalid characters: {cost_str}")

        # Check for balanced braces
        if cost_str.count("{") != cost_str.count("}"):
            errors.append("Mana cost has unbalanced braces")

        return len(errors) == 0, errors

    def validate_card_type(self, card) -> tuple[bool, list[str]]:
        """
        Validate card type line format and requirements.

        Args:
            card: MTG card object to validate

        Returns:
            tuple: (is_valid, list_of_errors)
        """
        errors = []

        if not hasattr(card, "type") or not card.type:
            errors.append("Card type is required")
            return False, errors

        type_line = card.type.strip()

        # Valid card types
        valid_types = [
            "Artifact",
            "Creature",
            "Enchantment",
            "Instant",
            "Land",
            "Planeswalker",
            "Sorcery",
            "Tribal",
            "Battle",
        ]

        valid_supertypes = ["Basic", "Legendary", "Snow", "World"]

        # Check if type line contains at least one valid type
        has_valid_type = any(card_type in type_line for card_type in valid_types)
        if not has_valid_type:
            errors.append(
                f"Card type must include at least one valid type: {', '.join(valid_types)}"
            )

        # Validate specific type requirements
        if "Creature" in type_line:
            # Creatures should have subtypes after the dash
            if "—" not in type_line and "-" not in type_line:
                errors.append(
                    "Creature cards should have subtypes (e.g., 'Creature — Human Wizard')"
                )

        if "Planeswalker" in type_line:
            # Planeswalkers should have subtypes
            if "—" not in type_line and "-" not in type_line:
                errors.append(
                    "Planeswalker cards should have subtypes (e.g., 'Planeswalker — Jace')"
                )

        return len(errors) == 0, errors

    def validate_power_toughness(self, card) -> tuple[bool, list[str]]:
        """
        Validate power and toughness values for creatures.

        Args:
            card: MTG card object to validate

        Returns:
            tuple: (is_valid, list_of_errors)
        """
        errors = []

        # Only validate P/T for creatures
        if not hasattr(card, "type") or not card.type or "Creature" not in card.type:
            return True, []  # Not a creature, P/T validation not needed

        # Check power
        if not hasattr(card, "power") or card.power is None:
            errors.append("Creature cards must have power defined")
        else:
            power_valid, power_errors = self._validate_pt_value(card.power, "power")
            errors.extend(power_errors)

        # Check toughness
        if not hasattr(card, "toughness") or card.toughness is None:
            errors.append("Creature cards must have toughness defined")
        else:
            toughness_valid, toughness_errors = self._validate_pt_value(
                card.toughness, "toughness"
            )
            errors.extend(toughness_errors)

        return len(errors) == 0, errors

    def _validate_pt_value(self, value, field_name: str) -> tuple[bool, list[str]]:
        """Helper method to validate a single power or toughness value."""
        errors = []

        if value is None:
            errors.append(f"{field_name.capitalize()} cannot be None")
            return False, errors

        # Convert to string for validation
        value_str = str(value).strip()

        # Valid P/T values: numbers, *, X, *+1, etc.
        import re

        if not re.match(r"^[\*X0-9\+\-\*]+$|^\d+$", value_str):
            errors.append(f"Invalid {field_name} value: {value_str}")

        # Check for negative numbers (usually invalid except for special cases)
        if value_str.startswith("-") and not value_str.startswith("-0"):
            errors.append(f"{field_name.capitalize()} cannot be negative: {value_str}")

        return len(errors) == 0, errors

    def check_card_rules(self, card) -> tuple[bool, list[str]]:
        """
        Check card against fundamental Magic rules.

        Args:
            card: MTG card object to check

        Returns:
            tuple: (follows_rules, list_of_violations)
        """
        violations = []

        # Rule checks
        if hasattr(card, "type") and card.type:
            # Lands shouldn't have mana costs (with rare exceptions)
            if (
                "Land" in card.type
                and hasattr(card, "cost")
                and card.cost
                and str(card.cost) != "0"
            ):
                # Check if it's a basic land
                if any(
                    basic in card.type
                    for basic in ["Plains", "Island", "Swamp", "Mountain", "Forest"]
                ):
                    violations.append("Basic lands should not have mana costs")

            # Instants and Sorceries shouldn't have power/toughness
            if any(spell_type in card.type for spell_type in ["Instant", "Sorcery"]):
                if (hasattr(card, "power") and card.power is not None) or (
                    hasattr(card, "toughness") and card.toughness is not None
                ):
                    violations.append(
                        "Instant and Sorcery cards cannot have power/toughness"
                    )

        # Check for required fields based on card type
        if hasattr(card, "type") and "Planeswalker" in card.type:
            if (
                not hasattr(card, "text")
                or not card.text
                or not any(char in card.text for char in ["+", "-"])
            ):
                violations.append(
                    "Planeswalker cards should have loyalty abilities (+ or - abilities)"
                )

        return len(violations) == 0, violations

    def validate_card_text(self, card_text: str) -> tuple[bool, list[str]]:
        """
        Validate card text content and formatting.

        Args:
            card_text: Card text to validate

        Returns:
            tuple: (is_valid, list_of_errors)
        """
        errors = []

        if not card_text:
            return True, []  # Empty text is valid

        text = card_text.strip()

        # Check text length (Oracle text is usually under 2000 characters)
        if len(text) > 2000:
            errors.append("Card text is too long (maximum 2000 characters)")

        # Check for balanced parentheses and brackets
        if text.count("(") != text.count(")"):
            errors.append("Card text has unbalanced parentheses")

        if text.count("[") != text.count("]"):
            errors.append("Card text has unbalanced brackets")

        # Check for proper ability formatting (abilities usually end with periods)
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if (
                line
                and not line.endswith(".")
                and not line.endswith(":")
                and not any(line.endswith(punct) for punct in ['"', "'", ")", "]"])
            ):
                # Allow exceptions for flavor text in quotes or special formatting
                if not (
                    line.startswith('"')
                    or line.startswith("'")
                    or any(
                        keyword in line.lower()
                        for keyword in ["tap:", "untap:", "{t}:", "{q}:"]
                    )
                ):
                    errors.append(
                        f"Ability text should end with proper punctuation: '{line}'"
                    )

        return len(errors) == 0, errors

    def enforce_format_constraints(
        self, cards: list, format_name: str = "commander"
    ) -> tuple[bool, list[str], dict]:
        """
        Enforce format-specific constraints on a deck.

        Args:
            cards: List of cards in the deck
            format_name: Format to check against

        Returns:
            tuple: (is_legal, list_of_violations, statistics)
        """
        violations = []
        stats = {
            "total_cards": len(cards),
            "unique_cards": 0,
            "color_identity": set(),
            "format": format_name,
        }

        if format_name.lower() == "commander":
            return self._enforce_commander_constraints(cards, violations, stats)
        elif format_name.lower() == "standard":
            return self._enforce_standard_constraints(cards, violations, stats)
        elif format_name.lower() == "modern":
            return self._enforce_modern_constraints(cards, violations, stats)
        else:
            violations.append(f"Unknown format: {format_name}")
            return False, violations, stats

    def _enforce_commander_constraints(
        self, cards: list, violations: list[str], stats: dict
    ) -> tuple[bool, list[str], dict]:
        """Enforce Commander format constraints."""
        # Commander should have exactly 100 cards
        if len(cards) != 100:
            violations.append(
                f"Commander decks must have exactly 100 cards (found {len(cards)})"
            )

        # Check for commander (legendary creature or planeswalker)
        commanders = [
            card
            for card in cards
            if hasattr(card, "type")
            and "Legendary" in card.type
            and ("Creature" in card.type or "Planeswalker" in card.type)
        ]

        if len(commanders) == 0:
            violations.append(
                "Commander deck must have a legendary creature or planeswalker as commander"
            )
        elif len(commanders) > 1:
            violations.append("Commander deck can only have one commander")

        # Check singleton rule (except basic lands)
        card_counts = {}
        basic_lands = ["Plains", "Island", "Swamp", "Mountain", "Forest"]

        for card in cards:
            if hasattr(card, "name"):
                card_counts[card.name] = card_counts.get(card.name, 0) + 1

        for card_name, count in card_counts.items():
            if count > 1 and not any(basic in card_name for basic in basic_lands):
                violations.append(
                    f"Commander allows only one copy of '{card_name}' (found {count})"
                )

        stats["unique_cards"] = len(card_counts)
        return len(violations) == 0, violations, stats

    def _enforce_standard_constraints(
        self, cards: list, violations: list[str], stats: dict
    ) -> tuple[bool, list[str], dict]:
        """Enforce Standard format constraints."""
        # Standard should have at least 60 cards
        if len(cards) < 60:
            violations.append(
                f"Standard decks must have at least 60 cards (found {len(cards)})"
            )

        # Check 4-of rule
        card_counts = {}
        basic_lands = ["Plains", "Island", "Swamp", "Mountain", "Forest"]

        for card in cards:
            if hasattr(card, "name"):
                card_counts[card.name] = card_counts.get(card.name, 0) + 1

        for card_name, count in card_counts.items():
            if count > 4 and not any(basic in card_name for basic in basic_lands):
                violations.append(
                    f"Standard allows maximum 4 copies of '{card_name}' (found {count})"
                )

        stats["unique_cards"] = len(card_counts)
        return len(violations) == 0, violations, stats

    def _enforce_modern_constraints(
        self, cards: list, violations: list[str], stats: dict
    ) -> tuple[bool, list[str], dict]:
        """Enforce Modern format constraints."""
        # Modern should have at least 60 cards
        if len(cards) < 60:
            violations.append(
                f"Modern decks must have at least 60 cards (found {len(cards)})"
            )

        # Check 4-of rule (same as Standard)
        card_counts = {}
        basic_lands = ["Plains", "Island", "Swamp", "Mountain", "Forest"]

        for card in cards:
            if hasattr(card, "name"):
                card_counts[card.name] = card_counts.get(card.name, 0) + 1

        for card_name, count in card_counts.items():
            if count > 4 and not any(basic in card_name for basic in basic_lands):
                violations.append(
                    f"Modern allows maximum 4 copies of '{card_name}' (found {count})"
                )

        stats["unique_cards"] = len(card_counts)
        return len(violations) == 0, violations, stats
