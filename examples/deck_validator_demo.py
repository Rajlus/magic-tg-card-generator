#!/usr/bin/env python3
"""
Deck Validator Demo

This script demonstrates the DeckValidator functionality with various
MTG format validations including Commander, Standard, and Pauper.
"""

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from domain.models.mtg_card import MTGCard
from services.deck.deck_validator import DeckValidator, DeckFormat, ValidationResult
from services.deck.card_collection import CardCollection


def create_sample_card(name: str, type_line: str, cost: str = "", rarity: str = "common", 
                      text: str = "", power: int = None, toughness: int = None) -> MTGCard:
    """Helper function to create sample MTG cards."""
    return MTGCard(
        id=hash(name) % 10000,
        name=name,
        type=type_line,
        cost=cost,
        text=text,
        power=power if "Creature" in type_line else None,
        toughness=toughness if "Creature" in type_line else None,
        rarity=rarity
    )


def print_validation_result(result: ValidationResult, format_name: str):
    """Print validation results in a formatted way."""
    print(f"\n{'='*60}")
    print(f"VALIDATION RESULT - {format_name.upper()}")
    print(f"{'='*60}")
    print(f"Valid: {'✅ YES' if result.is_valid else '❌ NO'}")
    
    if result.errors:
        print(f"\n🚨 ERRORS ({len(result.errors)}):")
        for i, error in enumerate(result.errors, 1):
            print(f"  {i}. {error}")
    
    if result.warnings:
        print(f"\n⚠️  WARNINGS ({len(result.warnings)}):")
        for i, warning in enumerate(result.warnings, 1):
            print(f"  {i}. {warning}")
    
    if result.suggestions:
        print(f"\n💡 SUGGESTIONS ({len(result.suggestions)}):")
        for i, suggestion in enumerate(result.suggestions, 1):
            print(f"  {i}. {suggestion}")


def demo_commander_validation():
    """Demonstrate Commander format validation."""
    print("\n" + "="*80)
    print("COMMANDER DECK VALIDATION DEMO")
    print("="*80)
    
    validator = DeckValidator(DeckFormat.COMMANDER)
    
    # Create a commander
    commander = create_sample_card(
        "Alesha, Who Smiles at Death",
        "Legendary Creature - Human Warrior",
        "{2}{R}",
        "rare",
        "First strike. Whenever Alesha attacks, you may pay {W/B}{W/B}. If you do, return target creature with power 2 or less from your graveyard to the battlefield tapped and attacking.",
        3, 2
    )
    
    # Create a valid Commander deck
    deck = CardCollection()
    
    # Add basic lands
    basic_lands = [
        ("Plains", "Basic Land - Plains"),
        ("Mountain", "Basic Land - Mountain"),
        ("Swamp", "Basic Land - Swamp")
    ]
    
    land_count = 0
    for name, type_line in basic_lands:
        for i in range(12):  # 12 of each basic
            deck.add_card(create_sample_card(f"{name}", type_line))
            land_count += 1
    
    # Add non-basic lands
    nonbasic_lands = [
        ("Command Tower", "Land", "{T}: Add one mana of any color in your commander's color identity."),
        ("Temple of Triumph", "Land", "Enters tapped. {T}: Add {R} or {W}."),
        ("Godless Shrine", "Land - Plains Swamp", "({T}: Add {W} or {B}.)"),
        ("Sacred Foundry", "Land - Mountain Plains", "({T}: Add {R} or {W}.)")
    ]
    
    for name, type_line, text in nonbasic_lands:
        deck.add_card(create_sample_card(name, type_line, "", "rare", text))
        land_count += 1
    
    # Add creatures in commander's colors
    creatures = [
        ("Lightning Angel", "Creature - Angel", "{1}{R}{W}{W}", "rare", "Flying, vigilance, haste", 3, 4),
        ("Mentor of the Meek", "Creature - Human Soldier", "{2}{W}", "rare", 
         "Whenever another creature with power 2 or less enters the battlefield under your control, you may pay {1}. If you do, draw a card.", 2, 2),
        ("Dark Confidant", "Creature - Human Wizard", "{1}{B}", "mythic",
         "At the beginning of your upkeep, reveal the top card of your library and put that card into your hand. You lose life equal to its mana cost.", 2, 1),
        ("Goblin Guide", "Creature - Goblin Scout", "{R}", "rare",
         "Haste. Whenever Goblin Guide attacks, defending player reveals the top card of their library.", 2, 2)
    ]
    
    creature_count = 0
    for name, type_line, cost, rarity, text, power, toughness in creatures:
        for i in range(5):  # Multiple copies of each creature type
            deck.add_card(create_sample_card(f"{name} {i+1}", type_line, cost, rarity, text, power, toughness))
            creature_count += 1
            if creature_count >= 20:
                break
        if creature_count >= 20:
            break
    
    # Add spells and artifacts
    remaining = 100 - land_count - creature_count
    spells = [
        ("Lightning Bolt", "Instant", "{R}", "common", "Lightning Bolt deals 3 damage to any target."),
        ("Path to Exile", "Instant", "{W}", "uncommon", "Exile target creature. Its controller may search their library for a basic land card."),
        ("Sol Ring", "Artifact", "{1}", "uncommon", "{T}: Add {C}{C}."),
        ("Boros Signet", "Artifact", "{2}", "common", "{1}, {T}: Add {R}{W}."),
    ]
    
    spell_count = 0
    for i in range(remaining):
        name, type_line, cost, rarity, text = spells[i % len(spells)]
        deck.add_card(create_sample_card(f"{name} {i+1}", type_line, cost, rarity, text))
        spell_count += 1
    
    print(f"Created Commander deck with {deck.get_total_count()} cards:")
    print(f"  - Commander: {commander.name}")
    print(f"  - Lands: {land_count}")
    print(f"  - Creatures: {creature_count}")
    print(f"  - Other spells: {spell_count}")
    
    # Validate the deck
    result = validator.validate(deck, commander)
    print_validation_result(result, "Commander")
    
    # Now demonstrate validation failures
    print(f"\n{'-'*60}")
    print("DEMONSTRATING VALIDATION FAILURES")
    print(f"{'-'*60}")
    
    # 1. Color identity violation
    print("\n1. Adding a card that violates color identity...")
    deck.add_card(create_sample_card("Counterspell", "Instant", "{U}{U}", "common", "Counter target spell."))
    result = validator.validate(deck, commander)
    print_validation_result(result, "Commander with Color Identity Violation")
    
    # Remove the offending card
    deck.cards = [card for card in deck.cards if card.name != "Counterspell"]
    
    # 2. Singleton violation
    print("\n2. Adding duplicate non-basic cards...")
    duplicate = create_sample_card("Duplicate Card", "Creature", "{2}{R}", "common", "", 2, 2)
    deck.add_card(duplicate)
    deck.add_card(duplicate)
    result = validator.validate(deck, commander)
    print_validation_result(result, "Commander with Singleton Violation")
    
    # Remove duplicates
    deck.cards = [card for card in deck.cards if card.name != "Duplicate Card"]
    
    # 3. Banned card
    print("\n3. Adding a banned card...")
    deck.add_card(create_sample_card("Black Lotus", "Artifact", "{0}", "mythic", "{T}, Sacrifice Black Lotus: Add three mana of any one color."))
    result = validator.validate(deck, commander)
    print_validation_result(result, "Commander with Banned Card")


def demo_standard_validation():
    """Demonstrate Standard format validation."""
    print("\n\n" + "="*80)
    print("STANDARD DECK VALIDATION DEMO")
    print("="*80)
    
    validator = DeckValidator(DeckFormat.STANDARD)
    
    # Create a valid Standard deck
    deck = CardCollection()
    
    # Add lands (24 lands for 60-card deck)
    for i in range(12):
        deck.add_card(create_sample_card("Plains", "Basic Land - Plains"))
        deck.add_card(create_sample_card("Mountain", "Basic Land - Mountain"))
    
    # Add 4 copies each of 9 different cards (36 cards total)
    standard_cards = [
        ("Lightning Bolt", "Instant", "{R}", "common", "Deal 3 damage to any target."),
        ("Monastery Swiftspear", "Creature - Human Monk", "{R}", "uncommon", "Haste, prowess", 1, 2),
        ("Ajani's Pridemate", "Creature - Cat Soldier", "{1}{W}", "uncommon", "Whenever you gain life, put a +1/+1 counter on Ajani's Pridemate.", 2, 2),
        ("Boros Elite", "Creature - Human Soldier", "{W}", "uncommon", "Battalion — Whenever Boros Elite attacks, if you control three or more attacking creatures, Boros Elite gets +2/+2 until end of turn.", 1, 1),
        ("Shock", "Instant", "{R}", "common", "Shock deals 2 damage to any target."),
        ("Lightning Strike", "Instant", "{1}{R}", "common", "Lightning Strike deals 3 damage to any target."),
        ("Boros Charm", "Instant", "{R}{W}", "uncommon", "Choose one — Boros Charm deals 4 damage to target player or planeswalker; or permanents you control gain indestructible until end of turn; or target creature gains double strike until end of turn."),
        ("Clifftop Retreat", "Land", "Clifftop Retreat enters tapped unless you control a Mountain or a Plains.", "rare"),
        ("Sacred Foundry", "Land - Mountain Plains", "({T}: Add {R} or {W}.)", "rare")
    ]
    
    for name, type_line, cost, rarity, text, *stats in standard_cards:
        power = stats[0] if len(stats) > 0 and "Creature" in type_line else None
        toughness = stats[1] if len(stats) > 1 and "Creature" in type_line else None
        
        for copy in range(4):  # 4 copies of each
            deck.add_card(create_sample_card(f"{name}", type_line, cost, rarity, text, power, toughness))
    
    print(f"Created Standard deck with {deck.get_total_count()} cards")
    
    result = validator.validate(deck)
    print_validation_result(result, "Standard")
    
    # Demonstrate violation
    print(f"\n{'-'*60}")
    print("DEMONSTRATING TOO MANY COPIES VIOLATION")
    print(f"{'-'*60}")
    
    # Add 5th copy of Lightning Bolt
    deck.add_card(create_sample_card("Lightning Bolt", "Instant", "{R}", "common", "Deal 3 damage to any target."))
    result = validator.validate(deck)
    print_validation_result(result, "Standard with Too Many Copies")


def demo_pauper_validation():
    """Demonstrate Pauper format validation."""
    print("\n\n" + "="*80)
    print("PAUPER DECK VALIDATION DEMO")
    print("="*80)
    
    validator = DeckValidator(DeckFormat.PAUPER)
    
    # Create a valid Pauper deck (all commons)
    deck = CardCollection()
    
    # Add basic lands
    for i in range(20):
        deck.add_card(create_sample_card("Mountain", "Basic Land - Mountain"))
    
    # Add common creatures and spells
    pauper_cards = [
        ("Lightning Bolt", "Instant", "{R}", "common", "Deal 3 damage to any target."),
        ("Monastery Swiftspear", "Creature - Human Monk", "{R}", "common", "Haste, prowess", 1, 2),
        ("Lava Spike", "Sorcery", "{R}", "common", "Deal 3 damage to target player or planeswalker."),
        ("Rift Bolt", "Sorcery", "{2}{R}", "common", "Suspend 1—{R}. Deal 3 damage to any target."),
        ("Chain Lightning", "Sorcery", "{R}", "common", "Deal 3 damage to any target."),
        ("Skewer the Critics", "Sorcery", "{2}{R}", "common", "Spectacle {R}. Deal 3 damage to any target."),
        ("Ghitu Lavarunner", "Creature - Human Wizard", "{R}", "common", "Haste. If there are two or more instant and/or sorcery cards in your graveyard, Ghitu Lavarunner gets +1/+0.", 1, 2),
        ("Thermo-Alchemist", "Creature - Human Wizard", "{1}{R}", "common", "Defender. {T}: Deal 1 damage to each opponent. Whenever you cast an instant or sorcery spell, untap Thermo-Alchemist.", 0, 3)
    ]
    
    for name, type_line, cost, rarity, text, *stats in pauper_cards:
        power = stats[0] if len(stats) > 0 and "Creature" in type_line else None
        toughness = stats[1] if len(stats) > 1 and "Creature" in type_line else None
        
        for copy in range(4):  # 4 copies of each
            deck.add_card(create_sample_card(f"{name}", type_line, cost, rarity, text, power, toughness))
    
    # Add more commons to reach 60 cards
    while deck.get_total_count() < 60:
        deck.add_card(create_sample_card(f"Common Filler {deck.get_total_count()}", "Creature", "{2}{R}", "common", "", 2, 1))
    
    print(f"Created Pauper deck with {deck.get_total_count()} cards (all commons)")
    
    result = validator.validate(deck)
    print_validation_result(result, "Pauper")
    
    # Demonstrate rarity violation
    print(f"\n{'-'*60}")
    print("DEMONSTRATING RARITY VIOLATION")
    print(f"{'-'*60}")
    
    # Add an uncommon card
    deck.add_card(create_sample_card("Uncommon Card", "Creature", "{2}{R}", "uncommon", "", 3, 2))
    result = validator.validate(deck)
    print_validation_result(result, "Pauper with Rarity Violation")


def main():
    """Run all validation demos."""
    print("MTG DECK VALIDATOR DEMONSTRATION")
    print("This demo showcases the DeckValidator's capabilities across different MTG formats.")
    
    try:
        demo_commander_validation()
        demo_standard_validation() 
        demo_pauper_validation()
        
        print(f"\n\n{'='*80}")
        print("DEMO COMPLETE!")
        print("="*80)
        print("The DeckValidator successfully demonstrated:")
        print("✅ Commander format validation (singleton, color identity, 100 cards)")
        print("✅ Standard format validation (60+ cards, 4-copy limit)")
        print("✅ Pauper format validation (commons only)")
        print("✅ Comprehensive error reporting")
        print("✅ Helpful suggestions and warnings")
        print("✅ Banned card detection")
        print("✅ Format-specific rule enforcement")
        
    except Exception as e:
        print(f"❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()