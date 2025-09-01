"""
DeckValidator - Comprehensive MTG format rule validation

This module provides validation for various MTG formats including Commander,
Standard, Modern, Legacy, Vintage, and Pauper. It checks format-specific
rules such as card counts, singleton restrictions, color identity, and
banned/restricted lists.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Set
from enum import Enum
from collections import Counter, defaultdict

from ...domain.models.mtg_card import MTGCard
from ...domain.models.card_collection import CardCollection


class DeckFormat(Enum):
    """MTG format enumeration."""
    COMMANDER = "commander"
    STANDARD = "standard"
    MODERN = "modern"
    LEGACY = "legacy"
    VINTAGE = "vintage"
    PAUPER = "pauper"


@dataclass
class ValidationResult:
    """Result of deck validation containing errors, warnings, and suggestions."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]

    def __post_init__(self):
        """Ensure all lists are initialized."""
        self.errors = self.errors or []
        self.warnings = self.warnings or []
        self.suggestions = self.suggestions or []


class DeckValidator:
    """Validates decks against MTG format rules."""

    # Basic land names for singleton validation
    BASIC_LANDS = {
        "Plains", "Island", "Swamp", "Mountain", "Forest",
        "Snow-Covered Plains", "Snow-Covered Island", "Snow-Covered Swamp",
        "Snow-Covered Mountain", "Snow-Covered Forest", "Wastes"
    }

    # Color identity mapping
    COLOR_SYMBOLS = {'W', 'U', 'B', 'R', 'G'}

    # Format-specific banned lists (simplified for demonstration)
    BANNED_CARDS = {
        DeckFormat.COMMANDER: {
            "Black Lotus", "Mox Pearl", "Mox Sapphire", "Mox Jet", "Mox Ruby", "Mox Emerald",
            "Time Walk", "Ancestral Recall", "Timetwister", "Library of Alexandria",
            "Tolarian Academy", "Griselbrand", "Primeval Titan", "Sylvan Primordial",
            "Prophet of Kruphix", "Braids, Cabal Minion", "Erayo, Soratami Ascendant",
            "Fastbond", "Gifts Ungiven", "Recurring Nightmare", "Sway of the Stars",
            "Sundering Titan", "Worldfire", "Coalition Victory", "Biorhythm",
            "Limited Resources", "Painter's Servant", "Panoptic Mirror", "Trade Secrets"
        },
        DeckFormat.STANDARD: {
            "Once Upon a Time", "Oko, Thief of Crowns", "Wilderness Reclamation",
            "Teferi, Time Raveler", "Growth Spiral", "Cauldron Familiar"
        },
        DeckFormat.MODERN: {
            "Splinter Twin", "Birthing Pod", "Blazing Shoal", "Cloudpost", "Dark Depths",
            "Dread Return", "Glimpse of Nature", "Golgari Grave-Troll", "Green Sun's Zenith",
            "Hypergenesis", "Jace, the Mind Sculptor", "Mental Misstep", "Ponder",
            "Preordain", "Punishing Fire", "Rite of Flame", "Seething Song",
            "Second Sunrise", "Stoneforge Mystic", "Umezawa's Jitte", "Wild Nacatl"
        },
        DeckFormat.LEGACY: {
            "Bazaar of Baghdad", "Library of Alexandria", "Mishra's Workshop", "Strip Mine",
            "Tolarian Academy", "Chaos Orb", "Falling Star", "Shahrazad"
        },
        DeckFormat.VINTAGE: set(),  # Only restricted list in Vintage
        DeckFormat.PAUPER: {
            "Cranial Plating", "Empty the Warrens", "Frantic Search", "Gitaxian Probe",
            "Grapeshot", "High Tide", "Hymn to Tourach", "Invigorate", "Sinkhole",
            "Temporal Fissure", "Treasure Cruise", "Cloud of Faeries", "Daze",
            "Gush", "Peregrine Drake"
        }
    }

    # Restricted cards (mostly for Vintage)
    RESTRICTED_CARDS = {
        DeckFormat.VINTAGE: {
            "Ancestral Recall", "Balance", "Black Lotus", "Brainstorm", "Channel",
            "Demonic Consultation", "Demonic Tutor", "Dig Through Time", "Flash",
            "Force of Will", "Gitaxian Probe", "Gush", "Imperial Seal",
            "Library of Alexandria", "Lodestone Golem", "Lotus Petal", "Mana Crypt",
            "Mana Vault", "Memory Jar", "Mental Misstep", "Merchant Scroll",
            "Mindtwist", "Mox Emerald", "Mox Jet", "Mox Pearl", "Mox Ruby",
            "Mox Sapphire", "Mystical Tutor", "Necropotence", "Oath of Druids",
            "Ponder", "Preordain", "Sol Ring", "Strip Mine", "Thorn of Amethyst",
            "Time Vault", "Time Walk", "Timetwister", "Tinker", "Tolarian Academy",
            "Treasure Cruise", "Trinisphere", "Vampiric Tutor", "Wheel of Fortune",
            "Windfall", "Yawgmoth's Will"
        }
    }

    def __init__(self, format_rules: DeckFormat = DeckFormat.COMMANDER):
        """Initialize validator with format-specific rules."""
        self.format = format_rules
        self.rules = self._load_format_rules()

    def _load_format_rules(self) -> Dict:
        """Load format-specific rules."""
        rules = {
            DeckFormat.COMMANDER: {
                'min_cards': 100,
                'max_cards': 100,
                'singleton': True,
                'max_copies': 1,
                'requires_commander': True,
                'sideboard_size': 0
            },
            DeckFormat.STANDARD: {
                'min_cards': 60,
                'max_cards': None,
                'singleton': False,
                'max_copies': 4,
                'requires_commander': False,
                'sideboard_size': 15
            },
            DeckFormat.MODERN: {
                'min_cards': 60,
                'max_cards': None,
                'singleton': False,
                'max_copies': 4,
                'requires_commander': False,
                'sideboard_size': 15
            },
            DeckFormat.LEGACY: {
                'min_cards': 60,
                'max_cards': None,
                'singleton': False,
                'max_copies': 4,
                'requires_commander': False,
                'sideboard_size': 15
            },
            DeckFormat.VINTAGE: {
                'min_cards': 60,
                'max_cards': None,
                'singleton': False,
                'max_copies': 4,
                'requires_commander': False,
                'sideboard_size': 15
            },
            DeckFormat.PAUPER: {
                'min_cards': 60,
                'max_cards': None,
                'singleton': False,
                'max_copies': 4,
                'requires_commander': False,
                'sideboard_size': 15
            }
        }
        return rules[self.format]

    def validate(self, deck: CardCollection, commander: Optional[MTGCard] = None) -> ValidationResult:
        """Validate deck against format rules."""
        errors = []
        warnings = []
        suggestions = []

        # Validate card count
        errors.extend(self.validate_card_count(deck))

        # Validate singleton rule if applicable
        if self.rules['singleton']:
            errors.extend(self.validate_singleton(deck))

        # Validate commander requirements
        if self.rules['requires_commander']:
            if not commander:
                errors.append("Commander format requires a commander.")
            else:
                errors.extend(self.validate_commander_identity(deck, commander))
                warnings.extend(self._validate_commander_legality(commander))

        # Check banned/restricted lists
        errors.extend(self.check_banned_list(deck))
        
        # Format-specific validations
        if self.format == DeckFormat.VINTAGE:
            errors.extend(self._check_restricted_list(deck))
        elif self.format == DeckFormat.PAUPER:
            errors.extend(self._validate_pauper_rarity(deck))

        # Generate suggestions
        suggestions.extend(self._generate_suggestions(deck, commander))

        # Add warnings for deck composition
        warnings.extend(self._analyze_deck_composition(deck))

        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )

    def validate_commander_identity(self, deck: CardCollection, commander: MTGCard) -> List[str]:
        """Check color identity rules for Commander."""
        errors = []
        
        if not commander:
            return ["No commander specified for Commander format deck."]

        commander_identity = self.get_color_identity(commander)
        
        for card in deck:
            card_identity = self.get_color_identity(card)
            if not card_identity.issubset(commander_identity):
                invalid_colors = card_identity - commander_identity
                errors.append(
                    f"Card '{card.name}' has colors {invalid_colors} not in commander's "
                    f"color identity {commander_identity}."
                )

        return errors

    def validate_singleton(self, deck: CardCollection) -> List[str]:
        """Check singleton rule (one of each non-basic land)."""
        errors = []
        card_counts = deck.get_card_counts()

        for card_name, count in card_counts.items():
            if count > 1 and not self._is_basic_land_by_name(card_name):
                errors.append(
                    f"Card '{card_name}' appears {count} times, but singleton "
                    f"formats allow only 1 copy of non-basic lands."
                )

        return errors

    def validate_card_count(self, deck: CardCollection) -> List[str]:
        """Validate card count for format."""
        errors = []
        total_cards = deck.get_total_count()
        
        if total_cards < self.rules['min_cards']:
            errors.append(
                f"Deck has {total_cards} cards but requires at least "
                f"{self.rules['min_cards']} cards for {self.format.value} format."
            )

        if self.rules['max_cards'] and total_cards > self.rules['max_cards']:
            errors.append(
                f"Deck has {total_cards} cards but allows maximum "
                f"{self.rules['max_cards']} cards for {self.format.value} format."
            )

        # Check individual card limits
        if not self.rules['singleton']:
            card_counts = deck.get_card_counts()
            max_copies = self.rules['max_copies']
            
            for card_name, count in card_counts.items():
                if count > max_copies and not self._is_basic_land_by_name(card_name):
                    errors.append(
                        f"Card '{card_name}' appears {count} times, but "
                        f"{self.format.value} format allows maximum {max_copies} copies."
                    )

        return errors

    def check_banned_list(self, deck: CardCollection) -> List[str]:
        """Check for banned cards in format."""
        errors = []
        banned_cards = self.BANNED_CARDS.get(self.format, set())
        
        for card in deck:
            if card.name in banned_cards:
                errors.append(f"Card '{card.name}' is banned in {self.format.value} format.")

        return errors

    def _check_restricted_list(self, deck: CardCollection) -> List[str]:
        """Check restricted cards for Vintage format."""
        errors = []
        restricted_cards = self.RESTRICTED_CARDS.get(self.format, set())
        card_counts = deck.get_card_counts()
        
        for card_name, count in card_counts.items():
            if card_name in restricted_cards and count > 1:
                errors.append(
                    f"Card '{card_name}' is restricted in {self.format.value} format "
                    f"(found {count} copies, maximum 1 allowed)."
                )

        return errors

    def _validate_pauper_rarity(self, deck: CardCollection) -> List[str]:
        """Validate that all cards are commons in Pauper format."""
        errors = []
        
        for card in deck:
            if card.rarity.lower() != 'common':
                errors.append(
                    f"Card '{card.name}' has rarity '{card.rarity}' but Pauper "
                    f"format only allows common cards."
                )

        return errors

    def _validate_commander_legality(self, commander: MTGCard) -> List[str]:
        """Validate that the commander can legally be a commander."""
        warnings = []
        
        # Check if it's a legendary creature or planeswalker
        if not self._can_be_commander(commander):
            warnings.append(
                f"'{commander.name}' may not be a legal commander. Commanders must "
                f"typically be legendary creatures or planeswalkers with specific rules text."
            )

        return warnings

    def _can_be_commander(self, card: MTGCard) -> bool:
        """Check if a card can be a commander."""
        type_lower = card.type.lower()
        text_lower = card.text.lower() if card.text else ""
        
        # Legendary creatures can be commanders
        if 'legendary' in type_lower and 'creature' in type_lower:
            return True
            
        # Planeswalkers with "can be your commander" text
        if 'planeswalker' in type_lower and 'can be your commander' in text_lower:
            return True
            
        # Some specific exceptions (simplified check)
        if 'partner' in text_lower:
            return True
            
        return False

    def is_basic_land(self, card: MTGCard) -> bool:
        """Check if a card is a basic land."""
        return self._is_basic_land_by_name(card.name)

    def _is_basic_land_by_name(self, card_name: str) -> bool:
        """Check if a card name is a basic land."""
        return card_name in self.BASIC_LANDS

    def get_color_identity(self, card: MTGCard) -> Set[str]:
        """Extract color identity from a card."""
        colors = set()
        
        # Extract from mana cost
        if card.cost:
            colors.update(self._extract_colors_from_cost(card.cost))
        
        # Extract from rules text (simplified)
        if card.text:
            colors.update(self._extract_colors_from_text(card.text))
            
        return colors

    def _extract_colors_from_cost(self, cost: str) -> Set[str]:
        """Extract color symbols from mana cost."""
        colors = set()
        if not cost:
            return colors
            
        for char in cost.upper():
            if char in self.COLOR_SYMBOLS:
                colors.add(char)
                
        return colors

    def _extract_colors_from_text(self, text: str) -> Set[str]:
        """Extract color symbols from rules text (simplified)."""
        colors = set()
        if not text:
            return colors
            
        # Look for mana symbols in braces
        i = 0
        while i < len(text):
            if text[i] == '{':
                j = i + 1
                while j < len(text) and text[j] != '}':
                    j += 1
                if j < len(text):
                    symbol = text[i+1:j].upper()
                    if symbol in self.COLOR_SYMBOLS:
                        colors.add(symbol)
                i = j + 1
            else:
                i += 1
                
        return colors

    def is_legal_in_format(self, card: MTGCard, format: DeckFormat) -> bool:
        """Check if a card is legal in the specified format."""
        # Check banned list
        banned_cards = self.BANNED_CARDS.get(format, set())
        if card.name in banned_cards:
            return False
            
        # Check format-specific restrictions
        if format == DeckFormat.PAUPER:
            return card.rarity.lower() == 'common'
            
        # For other formats, assume legal unless banned
        # In a real implementation, this would check legality databases
        return True

    def _generate_suggestions(self, deck: CardCollection, commander: Optional[MTGCard]) -> List[str]:
        """Generate helpful suggestions for deck improvement."""
        suggestions = []
        
        total_cards = deck.get_total_count()
        
        # Mana curve suggestions
        curve = deck.get_mana_curve()
        if curve:
            high_cmc_count = sum(count for cmc, count in curve.items() if cmc >= 6)
            if high_cmc_count > total_cards * 0.2:  # More than 20% high CMC
                suggestions.append(
                    "Consider reducing high mana cost cards for better curve."
                )

        # Land count suggestions for 60-card formats
        if self.format != DeckFormat.COMMANDER:
            land_count = len(deck.get_cards_by_type("Land"))
            if land_count < total_cards * 0.35:  # Less than 35% lands
                suggestions.append(
                    f"Consider adding more lands (currently {land_count}, "
                    f"recommended ~{int(total_cards * 0.4)})."
                )

        # Commander-specific suggestions
        if self.format == DeckFormat.COMMANDER and commander:
            # Suggest ramp for high-cost commanders
            if self._calculate_cmc_from_card(commander) >= 5:
                ramp_cards = [card for card in deck if 'mana' in card.text.lower()]
                if len(ramp_cards) < 8:
                    suggestions.append(
                        "Consider adding more mana ramp for your high-cost commander."
                    )

        return suggestions

    def _calculate_cmc_from_card(self, card: MTGCard) -> int:
        """Calculate CMC from a card object."""
        return CardCollection()._calculate_cmc(card.cost) if card.cost else 0

    def _analyze_deck_composition(self, deck: CardCollection) -> List[str]:
        """Analyze deck composition and generate warnings."""
        warnings = []
        
        if not deck:
            return warnings
            
        total_cards = deck.get_total_count()
        
        # Check creature count
        creatures = deck.get_cards_by_type("Creature")
        creature_ratio = len(creatures) / total_cards if total_cards > 0 else 0
        
        if self.format == DeckFormat.COMMANDER:
            if creature_ratio < 0.25:  # Less than 25% creatures
                warnings.append(
                    f"Low creature count ({len(creatures)}/{total_cards}). "
                    f"Consider adding more creatures for board presence."
                )
        else:
            if creature_ratio < 0.15:  # Less than 15% creatures
                warnings.append(
                    f"Very low creature count ({len(creatures)}/{total_cards}). "
                    f"Ensure you have win conditions."
                )

        # Check for removal spells
        removal_keywords = ['destroy', 'exile', 'counter', 'bounce', 'return to hand']
        removal_cards = [
            card for card in deck 
            if any(keyword in card.text.lower() for keyword in removal_keywords)
            if card.text
        ]
        
        removal_ratio = len(removal_cards) / total_cards if total_cards > 0 else 0
        if removal_ratio < 0.1:  # Less than 10% removal
            warnings.append(
                "Consider adding more removal spells to handle opponents' threats."
            )

        return warnings