#!/usr/bin/env python3
"""
Deck Format Validator - Überprüft alle Formatierungsregeln mit farbigen Warnings
"""
import re
from pathlib import Path

import yaml
from colorama import Back, Fore, Style, init

# Initialize colorama for cross-platform colored output
init()


class DeckValidator:
    def __init__(self, deck_path):
        self.deck_path = Path(deck_path)
        self.warnings = []
        self.errors = []
        self.deck_data = None

    def load_deck(self):
        """Load the deck YAML file"""
        try:
            with open(self.deck_path, encoding="utf-8") as f:
                self.deck_data = yaml.safe_load(f)
            return True
        except yaml.YAMLError as e:
            self.errors.append(f"YAML Parsing Error: {e}")
            return False
        except Exception as e:
            self.errors.append(f"File Error: {e}")
            return False

    def check_mana_costs(self, card):
        """Check if mana costs are properly quoted"""
        cost = card.get("cost", "")
        if cost and "{" in cost:
            # If we loaded it successfully, it's already properly quoted
            # Just check if it's a string
            if not isinstance(cost, str):
                return False, "Manakosten müssen in Anführungszeichen stehen"
        return True, None

    def check_em_dash(self, card):
        """Check for em-dash in card type"""
        card_type = card.get("type", "")
        if "—" in card_type:  # Em-dash character
            return (
                False,
                f"Em-Dash (—) gefunden! Verwende normalen Bindestrich (-). Type: {card_type}",
            )
        return True, None

    def check_creature_types(self, card):
        """Check for non-German creature types"""
        card_type = card.get("type", "")
        problematic_types = {
            "Automaton": "Konstrukt",
            "Dragon": "Drache",
            "Wizard": "Zauberer",
            "Warrior": "Krieger",
            "Elf": "Elf",
            "Human": "Mensch",
            "God": "Gott",
            "Angel": "Engel",
            "Demon": "Dämon",
        }

        for eng, ger in problematic_types.items():
            if eng in card_type and eng != "Elf":  # Elf ist auf Deutsch gleich
                return (
                    False,
                    f"Englischer Kreaturentyp '{eng}' gefunden! Verwende '{ger}'",
                )

        # Check for Automaton specifically (common issue)
        if "Automaton" in card_type or "Automaton" in card.get("text", ""):
            return False, "Kreaturentyp 'Automaton' sollte 'Konstrukt' sein"

        return True, None

    def check_text_formatting(self, card):
        """Check if card text has proper line breaks"""
        text = card.get("text", "")
        if not text:
            return True, None

        warnings = []

        # Check for keyword abilities without line breaks
        keywords = [
            "Fliegend",
            "Erstschlag",
            "Todesberührung",
            "Lebensverknüpfung",
            "Wachsamkeit",
            "Bedrohlich",
            "Reichweite",
            "Fluchsicher",
            "Unzerstörbar",
            "Doppelschlag",
            "Mentor",
            "Unaufhaltbar",
            "Eile",
            "Verteidiger",
        ]

        # Check if text has multiple abilities but no line breaks
        has_keyword = any(keyword in text for keyword in keywords)
        has_triggered = any(
            trigger in text
            for trigger in ["Wenn", "Immer wenn", "Zu Beginn", "Am Ende"]
        )
        has_activated = bool(re.search(r"{[^}]+}(?:,\s*{[^}]+})*:", text))

        ability_count = sum([has_keyword, has_triggered, has_activated])

        if ability_count > 1 and "\n" not in text:
            warnings.append("Mehrere Fähigkeiten gefunden, aber keine Zeilenumbrüche")

        # Check for specific patterns that should be on separate lines
        if (
            re.search(r"\.\s+(Wenn|Immer wenn|Zu Beginn|Am Ende)", text)
            and "\n" not in text
        ):
            warnings.append("Ausgelöste Fähigkeiten sollten in neuer Zeile stehen")

        if re.search(r"\.\s+{[^}]+}:", text) and "\n" not in text:
            warnings.append("Aktivierte Fähigkeiten sollten in neuer Zeile stehen")

        if warnings:
            return False, "; ".join(warnings)

        return True, None

    def check_special_characters(self, card):
        """Check for other problematic special characters"""
        text = card.get("text", "")
        type_line = card.get("type", "")
        name = card.get("name", "")

        # Check for smart quotes and other problematic characters
        # Note: Regular quotes (") in ability text are OK for formatting abilities
        problematic_chars = {
            '"': '"',  # Left smart quote
            '"': '"',  # Right smart quote
            """: "'",  # Left smart apostrophe
            """: "'",  # Right smart apostrophe
            "–": "-",  # En-dash
            "—": "-",  # Em-dash
            "„": '"',  # German low quote
            "‚": "'",  # German low single quote
        }

        warnings = []
        for field, value in [("Name", name), ("Type", type_line)]:
            for char, replacement in problematic_chars.items():
                if char in value:
                    warnings.append(
                        f"{field} enthält '{char}' - verwende '{replacement}'"
                    )

        if warnings:
            return False, "; ".join(warnings)

        return True, None

    def check_required_fields(self, card):
        """Check if all required fields are present"""
        required = ["id", "name", "type", "cost", "rarity", "set", "status"]
        missing = []

        for field in required:
            if field not in card:
                missing.append(field)

        if missing:
            return False, f"Fehlende Pflichtfelder: {', '.join(missing)}"

        return True, None

    def check_rarity(self, card):
        """Check if rarity is valid"""
        valid_rarities = ["common", "uncommon", "rare", "mythic"]
        rarity = card.get("rarity", "")

        if rarity and rarity not in valid_rarities:
            return (
                False,
                f"Ungültige Seltenheit '{rarity}'. Erlaubt: {', '.join(valid_rarities)}",
            )

        return True, None

    def validate_card(self, card):
        """Run all validation checks on a single card"""
        card_warnings = []

        # List of all check functions
        checks = [
            ("Pflichtfelder", self.check_required_fields),
            ("Manakosten", self.check_mana_costs),
            ("Em-Dash", self.check_em_dash),
            ("Kreaturentypen", self.check_creature_types),
            ("Textformatierung", self.check_text_formatting),
            ("Sonderzeichen", self.check_special_characters),
            ("Seltenheit", self.check_rarity),
        ]

        for check_name, check_func in checks:
            passed, message = check_func(card)
            if not passed and message:
                card_warnings.append((check_name, message))

        return card_warnings

    def print_warning(self, card_id, card_name, warning_type, message):
        """Print a formatted warning in yellow"""
        # Full line in yellow background
        warning_line = (
            f"⚠️  Card #{card_id:3} - {card_name:30} | {warning_type:15} | {message}"
        )
        print(Back.YELLOW + Fore.BLACK + warning_line + Style.RESET_ALL)

    def print_error(self, message):
        """Print a formatted error in red"""
        print(Back.RED + Fore.WHITE + f"❌ ERROR: {message}" + Style.RESET_ALL)

    def print_success(self, message):
        """Print a success message in green"""
        print(Fore.GREEN + f"✅ {message}" + Style.RESET_ALL)

    def validate(self):
        """Run validation on the entire deck"""
        print(f"\n🔍 Validating deck: {self.deck_path}")
        print("=" * 80)

        # Try to load the deck
        if not self.load_deck():
            for error in self.errors:
                self.print_error(error)
            return False

        if not self.deck_data or "cards" not in self.deck_data:
            self.print_error("Keine Karten im Deck gefunden")
            return False

        # Validate each card
        total_warnings = 0
        cards_with_warnings = 0

        print(f"\n📋 Überprüfe {len(self.deck_data['cards'])} Karten...\n")

        for card in self.deck_data["cards"]:
            card_warnings = self.validate_card(card)

            if card_warnings:
                cards_with_warnings += 1
                for warning_type, message in card_warnings:
                    self.print_warning(
                        card.get("id", "?"),
                        card.get("name", "Unknown")[:30],
                        warning_type,
                        message,
                    )
                    total_warnings += 1

        # Print summary
        print("\n" + "=" * 80)
        print("\n📊 Validierungsergebnis:")

        if total_warnings == 0:
            self.print_success(
                f"Alle {len(self.deck_data['cards'])} Karten sind korrekt formatiert!"
            )
            return True
        else:
            print(
                f"\n⚠️  {Fore.YELLOW}{total_warnings} Warnungen{Style.RESET_ALL} in "
                f"{Fore.YELLOW}{cards_with_warnings} Karten{Style.RESET_ALL} gefunden"
            )

            # Group warnings by type
            print("\n📝 Zusammenfassung nach Typ:")
            warning_types = {}
            for card in self.deck_data["cards"]:
                card_warnings = self.validate_card(card)
                for warning_type, _ in card_warnings:
                    warning_types[warning_type] = warning_types.get(warning_type, 0) + 1

            for wtype, count in sorted(
                warning_types.items(), key=lambda x: x[1], reverse=True
            ):
                print(f"  • {wtype}: {Fore.YELLOW}{count}{Style.RESET_ALL} Vorkommen")

            print(
                f"\n💡 Tipp: Verwende {Fore.CYAN}fix_deck_format.py{Style.RESET_ALL} um die meisten Probleme automatisch zu beheben"
            )

            return False


def main():
    """Main function"""
    import sys

    if len(sys.argv) > 1:
        deck_path = sys.argv[1]
    else:
        # Default deck path
        deck_path = "saved_decks/deck_heroes_of_camp_halfblood/deck_heroes_of_camp_halfblood.yaml"

    validator = DeckValidator(deck_path)
    success = validator.validate()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
