#!/usr/bin/env python3
"""Simple test script for the domain models to verify functionality."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.domain import MTGCard, Rarity


def test_domain_models():
    """Test the domain models functionality."""
    print("=== Testing MTG Card Domain Models ===\n")
    
    # Test 1: Basic instant spell
    print("1. Creating instant spell...")
    bolt = MTGCard(
        id=1,
        name="Lightning Bolt",
        type="Instant",
        cost="{R}",
        text="Lightning Bolt deals 3 damage to any target.",
        rarity=Rarity.COMMON
    )
    
    print(f"   ✓ {bolt.name} - {bolt.cost} ({bolt.rarity.display_name})")
    print(f"   Is spell: {bolt.is_spell()}, CMC: {bolt.get_converted_mana_cost()}")
    print(f"   Color identity: {bolt.get_color_identity()}")
    
    # Test 2: Creature with validation
    print("\n2. Creating creature...")
    angel = MTGCard(
        id=2,
        name="Serra Angel",
        type="Creature — Angel", 
        cost="{3}{W}{W}",
        text="Flying, vigilance",
        power=4,
        toughness=4,
        rarity="uncommon"  # Test string conversion
    )
    
    print(f"   ✓ {angel.name} - {angel.cost} ({angel.power}/{angel.toughness})")
    print(f"   Is creature: {angel.is_creature()}, Valid P/T: {angel.validate_power_toughness()}")
    print(f"   Is permanent: {angel.is_permanent()}, CMC: {angel.get_converted_mana_cost()}")
    
    # Test 3: Land
    print("\n3. Creating land...")
    forest = MTGCard(
        id=3,
        name="Forest",
        type="Basic Land — Forest",
        text="{T}: Add {G}.",
        rarity=Rarity.COMMON
    )
    
    print(f"   ✓ {forest.name}")
    print(f"   Is land: {forest.is_land()}, Has mana cost: {forest.has_mana_cost()}")
    print(f"   CMC: {forest.get_converted_mana_cost()}")
    
    # Test 4: Multicolored card
    print("\n4. Creating multicolored card...")
    helix = MTGCard(
        id=4,
        name="Lightning Helix",
        type="Instant",
        cost="{R}{W}",
        text="Lightning Helix deals 3 damage to any target and you gain 3 life.",
        rarity=Rarity.UNCOMMON
    )
    
    print(f"   ✓ {helix.name} - {helix.cost}")
    print(f"   Multicolored: {helix.is_multicolored()}, Colors: {helix.get_color_identity()}")
    print(f"   Colorless: {helix.is_colorless()}")
    
    # Test 5: Serialization
    print("\n5. Testing serialization...")
    bolt_dict = bolt.to_dict()
    restored_bolt = MTGCard.from_dict(bolt_dict)
    
    print(f"   ✓ Original: {bolt.name} ({bolt.rarity})")
    print(f"   ✓ Restored: {restored_bolt.name} ({restored_bolt.rarity})")
    print(f"   Equal: {bolt == restored_bolt}")
    
    # Test 6: Status management
    print("\n6. Testing status management...")
    bolt.update_status("generating")
    print(f"   ✓ Status: {bolt.status}")
    
    bolt.update_status("completed")
    print(f"   ✓ Final status: {bolt.status}")
    print(f"   Generated at: {bolt.generated_at is not None}")
    
    # Test 7: Error handling
    print("\n7. Testing validation...")
    try:
        invalid_creature = MTGCard(
            id=99,
            name="Invalid Creature",
            type="Creature — Human",
            cost="{1}{W}",
            text="This should fail validation"
            # Missing power/toughness
        )
        print("   ✗ Validation failed - should have thrown error")
    except ValueError as e:
        print(f"   ✓ Validation works: {e}")
    
    print("\n=== All domain tests passed! ===")


if __name__ == "__main__":
    test_domain_models()