#!/usr/bin/env python3
"""
Integration example showing how the new value objects work with the existing Card model.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.domain.value_objects.mana_cost import ManaCost
from src.domain.value_objects.card_colors import CardColors


def create_enhanced_card_example():
    """Show how value objects enhance card representation."""
    print("=== Enhanced Card Representation ===\n")
    
    # Simulate card data with proper MTG mana cost format
    card_data = {
        "name": "Lightning Bolt",
        "mana_cost": "{R}",
        "text": "Lightning Bolt deals 3 damage to any target.",
        "rarity": "Common"
    }
    
    print(f"Card: {card_data['name']}")
    print(f"Mana Cost (string): {card_data['mana_cost']}")
    print()
    
    # Enhance with value objects
    mana_cost_vo = ManaCost(card_data['mana_cost'])
    color_identity_vo = CardColors.from_mana_cost(card_data['mana_cost'])
    
    print("Enhanced with Value Objects:")
    print(f"ManaCost VO: {mana_cost_vo}")
    print(f"  CMC: {mana_cost_vo.converted_mana_cost}")
    print(f"  Color Requirements: {mana_cost_vo.color_requirements}")
    print(f"  Has X Cost: {mana_cost_vo.has_x_cost}")
    print(f"  Generic Mana: {mana_cost_vo.generic_mana}")
    print()
    
    print(f"CardColors VO: {color_identity_vo}")
    print(f"  Color Count: {color_identity_vo.color_count}")
    print(f"  Is Monocolored: {color_identity_vo.is_monocolored}")
    print(f"  Color Names: {', '.join(color_identity_vo.color_names)}")
    print(f"  String Representation: {str(color_identity_vo)}")
    print()


def deck_validation_example():
    """Show deck validation using value objects."""
    print("=== Deck Validation Example ===\n")
    
    # Define a commander's color identity
    commander_identity = CardColors.from_colors('U', 'B', 'R')  # Grixis
    print(f"Commander Color Identity: {commander_identity} ({commander_identity.wedge_name})")
    print()
    
    # Cards to check
    deck_cards = [
        ("Lightning Bolt", "{R}"),
        ("Counterspell", "{U}{U}"),
        ("Doom Blade", "{1}{B}"),
        ("Nicol Bolas", "{U}{B}{B}{R}"),
        ("Lightning Helix", "{R}{W}"),  # Should be illegal
        ("Sol Ring", "{1}"),
    ]
    
    print("Deck Legality Check:")
    for name, cost_str in deck_cards:
        card_colors = CardColors.from_mana_cost(cost_str)
        mana_cost = ManaCost(cost_str)
        
        is_legal = card_colors.is_subset_of(commander_identity)
        status = "✓ Legal" if is_legal else "✗ Illegal"
        
        print(f"  {name} ({cost_str}): {status}")
        if not is_legal:
            illegal_colors = card_colors - commander_identity
            print(f"    Reason: Contains {illegal_colors}")
    print()


def mana_curve_analysis():
    """Analyze mana curve using value objects."""
    print("=== Mana Curve Analysis ===\n")
    
    deck = [
        ("Lightning Bolt", "{R}"),
        ("Monastery Swiftspear", "{R}"),
        ("Snapcaster Mage", "{1}{U}"),
        ("Lightning Strike", "{1}{R}"),
        ("Counterspell", "{U}{U}"),
        ("Lightning Helix", "{R}{W}"),
        ("Jeskai Charm", "{U}{R}{W}"),
        ("Cryptic Command", "{U}{U}{U}{1}"),
        ("Teferi, Hero of Dominaria", "{3}{W}{U}"),
    ]
    
    # Analyze mana curve
    curve = {}
    color_distribution = {}
    
    for name, cost_str in deck:
        mana_cost = ManaCost(cost_str)
        colors = CardColors.from_mana_cost(cost_str)
        
        # Mana curve
        cmc = mana_cost.converted_mana_cost
        curve[cmc] = curve.get(cmc, 0) + 1
        
        # Color distribution
        for color in colors:
            color_distribution[color] = color_distribution.get(color, 0) + 1
    
    print("Mana Curve:")
    for cmc in sorted(curve.keys()):
        count = curve[cmc]
        bar = "█" * count
        print(f"  {cmc} mana: {bar} ({count} cards)")
    print()
    
    print("Color Distribution:")
    color_names = {'W': 'White', 'U': 'Blue', 'B': 'Black', 'R': 'Red', 'G': 'Green'}
    for color in sorted(color_distribution.keys()):
        count = color_distribution[color]
        name = color_names.get(color, color)
        bar = "█" * count
        print(f"  {name}: {bar} ({count} cards)")
    print()


def format_legality_check():
    """Check format legality based on mana costs."""
    print("=== Format Legality Analysis ===\n")
    
    cards = [
        ("Lightning Bolt", "{R}"),
        ("Black Lotus", "{0}"),
        ("Ancestral Recall", "{U}"),
        ("Force of Will", "{3}{U}{U}"),
        ("Emrakul, the Aeons Torn", "{15}"),
        ("One with Nothing", "{B}"),
    ]
    
    # Simplified format rules based on CMC
    format_rules = {
        "Pauper": {"max_cmc": 20, "description": "Commons only"},
        "Modern": {"max_cmc": 20, "description": "No cards before 8th Edition"},
        "Legacy": {"max_cmc": 20, "description": "All cards except banned"},
        "Standard": {"max_cmc": 15, "description": "Recent sets only"},
    }
    
    print("Format Legality (simplified by CMC):")
    for name, cost_str in cards:
        mana_cost = ManaCost(cost_str)
        cmc = mana_cost.converted_mana_cost
        
        print(f"\n{name} ({cost_str}) - CMC {cmc}:")
        
        for format_name, rules in format_rules.items():
            legal = cmc <= rules["max_cmc"]
            status = "✓ Legal" if legal else "✗ Too expensive"
            print(f"  {format_name}: {status}")
            if not legal:
                print(f"    (Max CMC: {rules['max_cmc']})")


def advanced_mana_analysis():
    """Advanced mana cost analysis."""
    print("\n=== Advanced Mana Analysis ===\n")
    
    complex_cards = [
        ("Karn Liberated", "{7}"),
        ("Sphinx's Revelation", "{X}{W}{U}{U}"),
        ("Manamorphose", "{1}{R/G}"),
        ("Gitaxian Probe", "{U/P}"),
        ("Fire // Ice", "{1}{R} // {1}{U}"),  # Split card representation
    ]
    
    for name, cost_str in complex_cards:
        if "//" in cost_str:
            # Handle split cards
            sides = cost_str.split(" // ")
            print(f"{name} (Split Card):")
            for i, side_cost in enumerate(sides, 1):
                mana_cost = ManaCost(side_cost)
                colors = CardColors.from_mana_cost(side_cost)
                print(f"  Side {i}: {side_cost} (CMC {mana_cost.converted_mana_cost}, Colors: {colors})")
        else:
            mana_cost = ManaCost(cost_str)
            colors = CardColors.from_mana_cost(cost_str)
            
            print(f"{name}:")
            print(f"  Mana Cost: {cost_str}")
            print(f"  CMC: {mana_cost.converted_mana_cost}")
            print(f"  Colors: {colors}")
            
            # Special properties
            properties = []
            if mana_cost.has_x_cost:
                properties.append("Variable cost")
            if mana_cost.has_hybrid_mana:
                properties.append("Hybrid mana")
            if mana_cost.has_phyrexian_mana:
                properties.append("Phyrexian mana")
            if mana_cost.generic_mana > 10:
                properties.append("High generic cost")
            
            if properties:
                print(f"  Properties: {', '.join(properties)}")
        
        print()


if __name__ == "__main__":
    create_enhanced_card_example()
    deck_validation_example()
    mana_curve_analysis()
    format_legality_check()
    advanced_mana_analysis()
    
    print("=== Integration Benefits ===")
    print("The value objects enhance the existing system by providing:")
    print("• Type-safe mana cost handling")
    print("• Accurate color identity calculation") 
    print("• Format and deck validation logic")
    print("• Mana curve and statistical analysis")
    print("• Support for complex MTG mechanics")
    print("• Immutable, reliable data structures")
    print("• Rich domain behavior beyond simple data storage")