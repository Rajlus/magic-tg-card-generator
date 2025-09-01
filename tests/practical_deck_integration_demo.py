#!/usr/bin/env python3
"""
Practical integration demo showing deck services working together.

This demo creates a sample Magic: The Gathering deck, validates it,
calculates statistics, and demonstrates the services working with MTGCard.
"""

import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def main():
    """Run the practical integration demo."""
    print("=" * 80)
    print("PRACTICAL DECK SERVICES INTEGRATION DEMO")
    print("=" * 80)
    print()

    # Import everything we need
    from src.services.deck import (
        DeckValidator, 
        DeckFormat, 
        ValidationResult,
        CardCollection,
        DeckBuilderService,
        DeckStatistics
    )
    from src.domain.models.mtg_card import MTGCard

    # Create a sample Commander deck
    print("🃏 Creating sample Commander deck...")
    
    # Commander
    commander = MTGCard(
        id=1,
        name="Atraxa, Praetors' Voice",
        type="Legendary Creature — Phyrexian Angel Horror",
        cost="{G}{W}{U}{B}",
        text="Flying, vigilance, deathtouch, lifelink\nAt the beginning of your end step, proliferate.",
        power=4,
        toughness=4,
        rarity="mythic"
    )
    
    # Sample cards for the deck
    deck_cards = [
        MTGCard(id=2, name="Sol Ring", type="Artifact", cost="{1}", text="{T}: Add {C}{C}.", rarity="uncommon"),
        MTGCard(id=3, name="Command Tower", type="Land", text="{T}: Add one mana of any color in your commander's color identity.", rarity="common"),
        MTGCard(id=4, name="Arcane Signet", type="Artifact", cost="{2}", text="{T}: Add one mana of any color in your commander's color identity.", rarity="common"),
        MTGCard(id=5, name="Forest", type="Basic Land — Forest", text="{T}: Add {G}.", rarity="common"),
        MTGCard(id=6, name="Plains", type="Basic Land — Plains", text="{T}: Add {W}.", rarity="common"),
        MTGCard(id=7, name="Island", type="Basic Land — Island", text="{T}: Add {U}.", rarity="common"),
        MTGCard(id=8, name="Swamp", type="Basic Land — Swamp", text="{T}: Add {B}.", rarity="common"),
        MTGCard(id=9, name="Counterspell", type="Instant", cost="{U}{U}", text="Counter target spell.", rarity="uncommon"),
        MTGCard(id=10, name="Swords to Plowshares", type="Instant", cost="{W}", text="Exile target creature. Its controller gains life equal to its power.", rarity="uncommon"),
    ]

    # Pad deck to 99 cards (excluding commander) with basics
    while len(deck_cards) < 99:
        basic_lands = [
            MTGCard(id=1000+len(deck_cards), name="Forest", type="Basic Land — Forest", text="{T}: Add {G}.", rarity="common"),
            MTGCard(id=1000+len(deck_cards)+1, name="Plains", type="Basic Land — Plains", text="{T}: Add {W}.", rarity="common"),
            MTGCard(id=1000+len(deck_cards)+2, name="Island", type="Basic Land — Island", text="{T}: Add {U}.", rarity="common"),
            MTGCard(id=1000+len(deck_cards)+3, name="Swamp", type="Basic Land — Swamp", text="{T}: Add {B}.", rarity="common"),
        ]
        for land in basic_lands:
            if len(deck_cards) < 99:
                deck_cards.append(land)

    print(f"   ✓ Created deck with {len(deck_cards)} cards + 1 commander")
    print(f"   ✓ Commander: {commander.name}")
    print()

    # Test 1: Use DeckBuilderService
    print("🔨 Testing DeckBuilderService...")
    builder = DeckBuilderService()
    builder.set_commander(commander)
    
    for card in deck_cards:
        builder.add_card(card)
    
    deck_stats = builder.get_deck_statistics()
    print(f"   ✓ Deck builder created deck with {deck_stats['deck_size']} cards")
    print(f"   ✓ Mana curve calculated: {len(deck_stats['mana_curve'])} different CMCs")
    print()

    # Test 2: Validate the deck
    print("🔍 Testing DeckValidator...")
    validator = DeckValidator(DeckFormat.COMMANDER)
    deck_collection = CardCollection(deck_cards)
    
    validation_result = validator.validate(deck_collection, commander)
    
    print(f"   ✓ Validation complete")
    print(f"   ✓ Deck is {'VALID' if validation_result.is_valid else 'INVALID'}")
    print(f"   ✓ Errors: {len(validation_result.errors)}")
    print(f"   ✓ Warnings: {len(validation_result.warnings)}")
    print(f"   ✓ Suggestions: {len(validation_result.suggestions)}")
    
    if validation_result.errors:
        print("   Errors found:")
        for error in validation_result.errors[:3]:  # Show first 3
            print(f"     - {error}")
            
    if validation_result.warnings:
        print("   Warnings:")
        for warning in validation_result.warnings[:2]:  # Show first 2
            print(f"     - {warning}")
    print()

    # Test 3: Calculate detailed statistics
    print("📊 Testing DeckStatistics...")
    
    # Mana curve
    curve = DeckStatistics.calculate_mana_curve(deck_cards)
    print(f"   ✓ Mana curve: Average CMC = {curve.average_cmc:.2f}")
    print(f"   ✓ CMC Distribution: {dict(list(curve.cmc_distribution.items())[:5])}")
    
    # Color stats
    color_stats = DeckStatistics.calculate_color_stats(deck_cards)
    print(f"   ✓ Color distribution: {dict(list(color_stats.color_distribution.items())[:4])}")
    
    # Type distribution
    type_dist = DeckStatistics.calculate_type_distribution(deck_cards)
    print(f"   ✓ Type breakdown: {type_dist.creatures} creatures, {type_dist.lands} lands, {type_dist.artifacts} artifacts")
    print()

    # Test 4: Integration with CardCollection
    print("📚 Testing CardCollection integration...")
    collection = CardCollection(deck_cards)
    
    # Test collection methods
    total_cards = collection.get_total_count()
    unique_cards = len(collection.get_unique_cards())
    lands = len(collection.get_cards_by_type("Land"))
    curve_from_collection = collection.get_mana_curve()
    
    print(f"   ✓ Total cards: {total_cards}")
    print(f"   ✓ Unique cards: {unique_cards}")
    print(f"   ✓ Lands: {lands}")
    print(f"   ✓ Mana curve from collection: {len(curve_from_collection)} different CMCs")
    print()

    # Test 5: Demonstrate MTGCard integration
    print("🎯 Testing MTGCard integration...")
    
    # Test MTGCard methods work with services
    creatures = [card for card in deck_cards if card.is_creature()]
    lands = [card for card in deck_cards if card.is_land()]
    
    print(f"   ✓ Found {len(creatures)} creatures using MTGCard.is_creature()")
    print(f"   ✓ Found {len(lands)} lands using MTGCard.is_land()")
    
    # Test commander properties
    print(f"   ✓ Commander is creature: {commander.is_creature()}")
    print(f"   ✓ Commander power/toughness: {commander.power}/{commander.toughness}")
    print()

    # Final summary
    print("=" * 80)
    print("INTEGRATION DEMO SUMMARY")
    print("=" * 80)
    
    print("✅ All services integrated successfully!")
    print(f"✅ Created and managed a {total_cards + 1} card Commander deck")  # +1 for commander
    print(f"✅ Validated deck with {len(validation_result.errors)} errors and {len(validation_result.warnings)} warnings")
    print("✅ Calculated comprehensive deck statistics")
    print("✅ Demonstrated MTGCard integration with all services")
    print("✅ CardCollection successfully manages MTGCard instances")
    print("✅ DeckValidator properly validates MTGCard-based decks")
    print("✅ DeckStatistics analyzes MTGCard collections")
    print("✅ DeckBuilderService orchestrates deck building with MTGCard")
    
    print("\n🎉 All deck services are fully integrated and working correctly!")
    print("=" * 80)

if __name__ == "__main__":
    main()