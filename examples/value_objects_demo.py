#!/usr/bin/env python3
"""
Demo script showing the ManaCost and CardColors value objects in action.
This demonstrates real-world Magic: The Gathering mana cost parsing and color identity.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.domain.value_objects.mana_cost import ManaCost
from src.domain.value_objects.card_colors import CardColors


def demo_mana_costs():
    """Demonstrate ManaCost value object functionality."""
    print("=== ManaCost Value Object Demo ===\n")
    
    # Famous MTG cards with their mana costs
    cards = [
        ("Lightning Bolt", "{R}"),
        ("Counterspell", "{U}{U}"),
        ("Black Lotus", "{0}"),
        ("Tarmogoyf", "{1}{G}"),
        ("Jace, the Mind Sculptor", "{2}{U}{U}"),
        ("Force of Will", "{3}{U}{U}"),
        ("Eldrazi Titan", "{15}"),
        ("Fireball", "{X}{R}"),
        ("Boros Charm", "{R}{W}"),
        ("Manamorphose", "{1}{R/G}"),
        ("Phyrexian Obliterator", "{B}{B}{B}{B}"),
        ("Gitaxian Probe", "{U/P}"),
    ]
    
    for name, cost_str in cards:
        cost = ManaCost(cost_str)
        colors = CardColors.from_mana_cost(cost)
        
        print(f"Card: {name}")
        print(f"  Mana Cost: {cost}")
        print(f"  CMC: {cost.converted_mana_cost}")
        print(f"  Color Identity: {colors} ({colors.color_count} colors)")
        
        # Additional info based on type
        if cost.is_free:
            print(f"  ✓ Free spell")
        if cost.has_x_cost:
            print(f"  ✓ Variable cost (X)")
        if cost.has_hybrid_mana:
            print(f"  ✓ Hybrid mana")
        if cost.has_phyrexian_mana:
            print(f"  ✓ Phyrexian mana")
        
        print()


def demo_color_identity():
    """Demonstrate CardColors value object functionality."""
    print("=== CardColors Value Object Demo ===\n")
    
    # Different color combinations
    combinations = [
        ("Colorless Artifact", CardColors.colorless()),
        ("Mono-White", CardColors.white()),
        ("Azorius (WU)", CardColors.from_colors('W', 'U')),
        ("Bant Shard (WUG)", CardColors.from_colors('W', 'U', 'G')),
        ("Abzan Wedge (WBG)", CardColors.from_colors('W', 'B', 'G')),
        ("Four-Color (WUBR)", CardColors.from_colors('W', 'U', 'B', 'R')),
        ("WUBRG", CardColors.all_colors()),
    ]
    
    for name, colors in combinations:
        print(f"Color Identity: {name}")
        print(f"  Colors: {colors}")
        print(f"  Color Names: {', '.join(colors.color_names)}")
        print(f"  Count: {colors.color_count}")
        
        # Classification
        if colors.is_colorless:
            print(f"  Type: Colorless")
        elif colors.is_monocolored:
            print(f"  Type: Monocolored")
        elif colors.is_guild:
            print(f"  Type: Guild ({colors.guild_name})")
        elif colors.is_shard:
            print(f"  Type: Shard ({colors.shard_name})")
        elif colors.is_wedge:
            print(f"  Type: Wedge ({colors.wedge_name})")
        elif colors.is_four_color:
            print(f"  Type: Four-color")
        elif colors.is_five_color:
            print(f"  Type: Five-color (WUBRG)")
        
        print()


def demo_advanced_operations():
    """Demonstrate advanced operations with value objects."""
    print("=== Advanced Operations Demo ===\n")
    
    # Create some mana costs
    bolt = ManaCost("{R}")
    counterspell = ManaCost("{U}{U}")
    boros_charm = ManaCost("{R}{W}")
    
    print("Mana Cost Operations:")
    print(f"Lightning Bolt: {bolt}")
    print(f"Counterspell: {counterspell}")
    print(f"Boros Charm: {boros_charm}")
    print()
    
    # Color operations
    red_colors = CardColors.from_mana_cost(bolt)
    blue_colors = CardColors.from_mana_cost(counterspell)
    boros_colors = CardColors.from_mana_cost(boros_charm)
    
    print("Color Operations:")
    print(f"Red ∪ Blue = {red_colors | blue_colors}")
    print(f"Boros ∩ Red = {boros_colors & red_colors}")
    print(f"Boros - Red = {boros_colors - red_colors}")
    print()
    
    print("Color Relationships:")
    print(f"Boros shares colors with Red: {boros_colors.shares_colors_with(red_colors)}")
    print(f"Red is subset of Boros: {red_colors.is_subset_of(boros_colors)}")
    print(f"Can pay Bolt with Boros colors: {bolt.can_be_paid_with_colors(boros_colors.colors)}")
    print()
    
    # Mana cost arithmetic
    print("Mana Cost Arithmetic:")
    expensive_bolt = bolt + "{2}"
    print(f"Lightning Bolt + {2} = {expensive_bolt} (CMC: {expensive_bolt.converted_mana_cost})")
    
    # Building complex costs
    complex_cost = ManaCost.from_components(generic=3, white=1, blue=2, red=1)
    print(f"Built from components: {complex_cost}")
    print(f"Color requirements: {complex_cost.color_requirements}")


def demo_real_world_examples():
    """Demonstrate with real MTG cards and scenarios."""
    print("=== Real-World MTG Examples ===\n")
    
    # Deck building scenario
    print("Deck Building Analysis:")
    print("Building a deck with these cards:")
    
    deck_cards = [
        ("Lightning Bolt", "{R}"),
        ("Monastery Swiftspear", "{R}"),
        ("Snapcaster Mage", "{1}{U}"),
        ("Lightning Helix", "{R}{W}"),
        ("Jeskai Charm", "{U}{R}{W}"),
        ("Teferi, Hero of Dominaria", "{3}{W}{U}"),
    ]
    
    deck_colors = CardColors.colorless()  # Start with no colors
    
    for name, cost_str in deck_cards:
        cost = ManaCost(cost_str)
        colors = CardColors.from_mana_cost(cost)
        deck_colors = deck_colors | colors  # Add to deck colors
        
        print(f"  {name} ({cost}) - adds {colors}")
    
    print(f"\nDeck Color Identity: {deck_colors}")
    print(f"Guild/Wedge: {deck_colors.wedge_name or deck_colors.guild_name or 'Custom'}")
    print(f"Mana base needs: {', '.join(deck_colors.color_names)}")
    print()
    
    # Commander legality check
    print("Commander Format Analysis:")
    commander_identity = CardColors.from_colors('U', 'R', 'W')  # Jeskai commander
    
    for name, cost_str in deck_cards:
        colors = CardColors.from_mana_cost(cost_str)
        legal = colors.is_subset_of(commander_identity)
        print(f"  {name}: {'✓ Legal' if legal else '✗ Illegal'} in Jeskai deck")


if __name__ == "__main__":
    demo_mana_costs()
    demo_color_identity()
    demo_advanced_operations()
    demo_real_world_examples()
    
    print("=== Summary ===")
    print("The ManaCost and CardColors value objects provide:")
    print("• Immutable, self-validating mana cost representation")
    print("• Comprehensive MTG color identity support")
    print("• Rich behavioral methods for game logic")
    print("• Support for hybrid, Phyrexian, and variable costs")
    print("• Guild, shard, and wedge classification")
    print("• Mathematical operations and comparisons")
    print("• Perfect for deck building, format legality, and game rules")