#!/usr/bin/env python3
"""
Automatic Deck Format Fixer - Behebt automatisch Formatierungsprobleme
"""
import re
import sys
from pathlib import Path

import yaml
from colorama import Back, Fore, Style, init

# Initialize colorama
init()


class DeckFixer:
    def __init__(self, deck_path):
        self.deck_path = Path(deck_path)
        self.fixes_applied = []
        self.deck_data = None

    def load_deck(self):
        """Load the deck YAML file"""
        try:
            with open(self.deck_path, encoding="utf-8") as f:
                self.deck_data = yaml.safe_load(f)
            return True
        except Exception as e:
            print(
                Back.RED
                + Fore.WHITE
                + f"❌ ERROR: Could not load deck: {e}"
                + Style.RESET_ALL
            )
            return False

    def fix_em_dash(self, card):
        """Replace em-dash with regular dash"""
        fixed = False
        if "type" in card and "—" in card["type"]:
            card["type"] = card["type"].replace("—", "-")
            fixed = True

        if "text" in card and "—" in card["text"]:
            card["text"] = card["text"].replace("—", "-")
            fixed = True

        return fixed

    def fix_creature_types(self, card):
        """Fix non-German creature types"""
        replacements = {
            "Automaton": "Konstrukt",
            "Dragon": "Drache",
            "Wizard": "Zauberer",
            "Warrior": "Krieger",
            "Human": "Mensch",
            "God": "Gott",
            "Angel": "Engel",
            "Demon": "Dämon",
        }

        fixed = False
        for eng, ger in replacements.items():
            if "type" in card and eng in card["type"]:
                card["type"] = card["type"].replace(eng, ger)
                fixed = True

            if "text" in card and "Automaton" in card["text"]:
                card["text"] = card["text"].replace("Automaton", "Konstrukt")
                fixed = True

        return fixed

    def fix_special_characters(self, card):
        """Fix smart quotes and other special characters"""
        replacements = {
            '"': '"',  # Smart quotes (both left and right)
            "'": "'",  # Smart apostrophes (both left and right)
            "–": "-",  # En-dash
            "—": "-",  # Em-dash (backup)
        }

        fixed = False
        for field in ["name", "type", "text", "flavor"]:
            if field in card and card[field]:
                original = card[field]
                for char, replacement in replacements.items():
                    if char in card[field]:
                        card[field] = card[field].replace(char, replacement)
                if original != card[field]:
                    fixed = True

        return fixed

    def fix_text_formatting(self, card):
        """Add proper line breaks to card text"""
        text = card.get("text", "")
        if not text or "\n\n" in text:  # Skip if already formatted
            return False

        # Normalize text first
        text = re.sub(r"\n+", " ", text)
        text = re.sub(r"\s+", " ", text)
        text = text.strip()

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
            "Beharrlichkeit",
        ]

        result = []
        remaining = text

        # Check for keyword abilities at the beginning
        keyword_regex = (
            r"^(" + "|".join(keywords) + r"(?:,\s*(?:" + "|".join(keywords) + r"))*)\."
        )
        match = re.match(keyword_regex, remaining)
        if match:
            result.append(match.group(0))
            remaining = remaining[len(match.group(0)) :].strip()

        # Split remaining text into sentences
        sentences = []
        parts = remaining.split(".")

        for i, part in enumerate(parts):
            if not part.strip():
                continue

            if i < len(parts) - 1:
                sentence = part.strip() + "."
            else:
                sentence = part.strip()
                if sentence:
                    sentence += "."

            if sentence and sentence != ".":
                sentences.append(sentence)

        # Identify separate abilities
        for sentence in sentences:
            # Triggered abilities
            if re.match(r"^(Wenn|Immer wenn|Zu Beginn|Am Ende|Solange)\s+", sentence):
                result.append(sentence)
            # Activated abilities
            elif re.match(
                r"^{[^}]+}(?:,\s*{[^}]+})*(?:,\s*{T})?:\s*", sentence
            ) or re.match(r"^{T}(?:,\s*{[^}]+})*:\s*", sentence):
                result.append(sentence)
            # Sacrifice abilities
            elif re.match(r"^Opfere\s+[^:]+:\s*", sentence):
                result.append(sentence)
            # Static abilities
            elif re.match(r"^(Andere|Kreaturen|Artefaktkreaturen)\s+", sentence):
                result.append(sentence)
            # Otherwise append to last ability if exists
            elif result:
                if result[-1].strip().endswith(".") and not any(
                    trigger in result[-1]
                    for trigger in ["Wenn", "wenn", ":", "Andere", "Kreaturen"]
                ):
                    if any(
                        x in sentence
                        for x in ["{T}:", "{U}", "{R}", "{W}", "{B}", "{G}"]
                    ):
                        result.append(sentence)
                    else:
                        result[-1] = result[-1] + " " + sentence
                else:
                    result.append(sentence)
            else:
                result.append(sentence)

        formatted = "\n\n".join(result)
        formatted = re.sub(r"\n{3,}", "\n\n", formatted)

        if formatted != text:
            card["text"] = formatted.strip()
            return True

        return False

    def print_fix(self, card_id, card_name, fix_type):
        """Print a fix notification"""
        print(
            Fore.GREEN
            + f"  ✅ Fixed Card #{card_id:3} - {card_name:30} | {fix_type}"
            + Style.RESET_ALL
        )

    def fix(self):
        """Fix all formatting issues in the deck"""
        print(f"\n🔧 Fixing deck format: {self.deck_path}")
        print("=" * 80)

        if not self.load_deck():
            return False

        if not self.deck_data or "cards" not in self.deck_data:
            print(Back.RED + Fore.WHITE + "❌ No cards found in deck" + Style.RESET_ALL)
            return False

        print(f"\n📋 Processing {len(self.deck_data['cards'])} cards...\n")

        total_fixes = 0
        cards_fixed = set()

        for card in self.deck_data["cards"]:
            card_id = card.get("id", "?")
            card_name = card.get("name", "Unknown")[:30]
            fixes_for_card = []

            # Apply all fixes
            if self.fix_em_dash(card):
                fixes_for_card.append("Em-Dash")

            if self.fix_creature_types(card):
                fixes_for_card.append("Kreaturentypen")

            if self.fix_special_characters(card):
                fixes_for_card.append("Sonderzeichen")

            if self.fix_text_formatting(card):
                fixes_for_card.append("Textformatierung")

            # Print fixes for this card
            if fixes_for_card:
                cards_fixed.add(card_id)
                for fix in fixes_for_card:
                    self.print_fix(card_id, card_name, fix)
                    total_fixes += 1

        # Save the fixed deck
        if total_fixes > 0:
            # Convert text fields to literal strings if they contain newlines
            class literal_str(str):
                pass

            def literal_presenter(dumper, data):
                if "\n" in data:
                    return dumper.represent_scalar(
                        "tag:yaml.org,2002:str", data, style="|"
                    )
                return dumper.represent_scalar("tag:yaml.org,2002:str", data)

            yaml.add_representer(literal_str, literal_presenter)

            # Convert multiline text fields
            for card in self.deck_data["cards"]:
                if (
                    "text" in card
                    and isinstance(card["text"], str)
                    and "\n" in card["text"]
                ):
                    card["text"] = literal_str(card["text"])

            # Save
            with open(self.deck_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    self.deck_data,
                    f,
                    allow_unicode=True,
                    sort_keys=False,
                    default_flow_style=False,
                    width=1000,
                )

            print("\n" + "=" * 80)
            print(f"\n✨ {Back.GREEN}{Fore.WHITE} SUCCESS {Style.RESET_ALL}")
            print(f"  • Fixed {Fore.GREEN}{len(cards_fixed)} cards{Style.RESET_ALL}")
            print(f"  • Applied {Fore.GREEN}{total_fixes} fixes{Style.RESET_ALL}")
            print(f"  • Saved to: {Fore.CYAN}{self.deck_path}{Style.RESET_ALL}")

            # Run validator to show remaining issues
            print("\n💡 Running validation to check for remaining issues...")
            print("-" * 40)
            from validate_deck_format import DeckValidator

            validator = DeckValidator(self.deck_path)
            validator.validate()

            return True
        else:
            print("\n" + "=" * 80)
            print(
                f"\n✨ {Fore.GREEN}No fixes needed!{Style.RESET_ALL} Deck is already properly formatted."
            )
            return True


def main():
    """Main function"""
    if len(sys.argv) > 1:
        deck_path = sys.argv[1]
    else:
        deck_path = "saved_decks/deck_heroes_of_camp_halfblood/deck_heroes_of_camp_halfblood.yaml"

    fixer = DeckFixer(deck_path)
    success = fixer.fix()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
