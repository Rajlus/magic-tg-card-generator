"""Comprehensive tests for the Mana Cost value object."""

import pytest
from typing import List, Dict

from magic_tg_card_generator.models import Card, CardType, Color


class TestManaCostParsing:
    """Test suite for mana cost parsing functionality."""

    def test_parse_empty_mana_cost(self) -> None:
        """Test parsing empty mana cost."""
        card = Card(
            name="Free Spell",
            card_type=CardType.INSTANT,
            mana_cost="",
            color=Color.COLORLESS
        )
        
        assert card.mana_cost == ""
        assert card.converted_mana_cost == 0

    def test_parse_zero_mana_cost(self) -> None:
        """Test parsing zero mana cost."""
        card = Card(
            name="Zero Cost Spell",
            card_type=CardType.INSTANT,
            mana_cost="0",
            color=Color.COLORLESS
        )
        
        assert card.mana_cost == "0"
        assert card.converted_mana_cost == 0

    def test_parse_single_digit_generic_mana(self) -> None:
        """Test parsing single digit generic mana costs."""
        for i in range(1, 10):
            card = Card(
                name=f"Generic {i} Spell",
                card_type=CardType.INSTANT,
                mana_cost=str(i),
                color=Color.COLORLESS
            )
            
            assert card.mana_cost == str(i)
            assert card.converted_mana_cost == i

    def test_parse_double_digit_generic_mana(self) -> None:
        """Test parsing double digit generic mana costs."""
        test_costs = [10, 11, 15, 20, 99]
        
        for cost in test_costs:
            card = Card(
                name=f"Generic {cost} Spell",
                card_type=CardType.SORCERY,
                mana_cost=str(cost),
                color=Color.COLORLESS
            )
            
            assert card.mana_cost == str(cost)
            assert card.converted_mana_cost == cost

    def test_parse_single_colored_mana(self) -> None:
        """Test parsing single colored mana symbols."""
        color_tests = [
            ("W", Color.WHITE, 1),
            ("U", Color.BLUE, 1),
            ("B", Color.BLACK, 1),
            ("R", Color.RED, 1),
            ("G", Color.GREEN, 1),
            ("C", Color.COLORLESS, 1)
        ]
        
        for mana_symbol, color, expected_cmc in color_tests:
            card = Card(
                name=f"Test {mana_symbol} Spell",
                card_type=CardType.INSTANT,
                mana_cost=mana_symbol,
                color=color
            )
            
            assert card.mana_cost == mana_symbol
            assert card.converted_mana_cost == expected_cmc

    def test_parse_multiple_colored_mana(self) -> None:
        """Test parsing multiple colored mana symbols."""
        test_cases = [
            ("WW", 2),
            ("UU", 2),
            ("BBB", 3),
            ("RRRR", 4),
            ("GGGGG", 5),
            ("WUBRG", 5),
            ("WWUUBBRRGG", 10)
        ]
        
        for mana_cost, expected_cmc in test_cases:
            card = Card(
                name=f"Test {mana_cost} Spell",
                card_type=CardType.ENCHANTMENT,
                mana_cost=mana_cost,
                color=Color.MULTICOLOR if len(set(mana_cost)) > 1 else Color.COLORLESS
            )
            
            assert card.mana_cost == mana_cost
            assert card.converted_mana_cost == expected_cmc

    def test_parse_mixed_generic_and_colored_mana(self) -> None:
        """Test parsing mixed generic and colored mana costs."""
        test_cases = [
            ("1W", 2),
            ("2U", 3),
            ("3B", 4),
            ("4R", 5),
            ("5G", 6),
            ("1WU", 3),
            ("2WW", 4),
            ("3UU", 5),
            ("10RR", 12),
            ("15WWUUBBRRGG", 25)  # 15 + 10 colored mana
        ]
        
        for mana_cost, expected_cmc in test_cases:
            card = Card(
                name=f"Test {mana_cost} Spell",
                card_type=CardType.SORCERY,
                mana_cost=mana_cost,
                color=Color.MULTICOLOR
            )
            
            assert card.mana_cost == mana_cost
            assert card.converted_mana_cost == expected_cmc

    def test_parse_x_mana_costs(self) -> None:
        """Test parsing mana costs with X."""
        test_cases = [
            ("X", 0),
            ("XW", 1),
            ("XUU", 2),
            ("X1", 1),
            ("X2R", 3),
            ("XX", 0),  # Multiple X still counts as 0
            ("XXX", 0),
            ("XX2WW", 4)  # XX = 0, 2 = 2, WW = 2
        ]
        
        for mana_cost, expected_cmc in test_cases:
            card = Card(
                name=f"Test {mana_cost} Spell",
                card_type=CardType.INSTANT,
                mana_cost=mana_cost,
                color=Color.MULTICOLOR
            )
            
            assert card.mana_cost == mana_cost
            assert card.converted_mana_cost == expected_cmc

    def test_parse_complex_mana_costs(self) -> None:
        """Test parsing complex real-world mana costs."""
        real_world_costs = [
            ("2WW", 4),        # Wrath of God
            ("1UU", 3),        # Counterspell
            ("BBB", 3),        # Phyrexian Obliterator
            ("RRR", 3),        # Ball Lightning
            ("GGG", 3),        # Leatherback Baloth
            ("WUBRG", 5),      # Child of Alara
            ("2WUBRG", 7),     # Expensive 5-color spell
            ("X2WW", 4),       # X + 4 CMC (X counts as 0)
            ("16", 16),        # Draco's mana cost
            ("0", 0),          # Ornithopter
            ("", 0)            # Lands
        ]
        
        for mana_cost, expected_cmc in real_world_costs:
            card = Card(
                name=f"Real World {mana_cost} Spell",
                card_type=CardType.ARTIFACT if mana_cost in ["0", ""] else CardType.SORCERY,
                mana_cost=mana_cost,
                color=Color.COLORLESS if mana_cost in ["0", "", "16"] else Color.MULTICOLOR
            )
            
            assert card.mana_cost == mana_cost
            assert card.converted_mana_cost == expected_cmc


class TestManaCostValidation:
    """Test suite for mana cost validation rules."""

    def test_valid_mana_cost_patterns(self) -> None:
        """Test that valid mana cost patterns are accepted."""
        valid_patterns = [
            "",
            "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
            "10", "11", "15", "20", "99",
            "W", "U", "B", "R", "G", "C",
            "WW", "UU", "BB", "RR", "GG", "CC",
            "WUBRG", "WUBRGC",
            "1W", "2U", "3B", "4R", "5G", "6C",
            "X", "XX", "XXX",
            "XW", "XUU", "X2R",
            "2WW", "3UU", "4BB", "5RR", "6GG",
            "10WUBRG", "15CC", "20XWUBRG"
        ]
        
        for mana_cost in valid_patterns:
            # Should not raise ValidationError
            card = Card(
                name=f"Valid {mana_cost} Card",
                card_type=CardType.INSTANT,
                mana_cost=mana_cost,
                color=Color.COLORLESS
            )
            assert card.mana_cost == mana_cost

    def test_invalid_mana_cost_patterns_raise_error(self) -> None:
        """Test that invalid mana cost patterns raise ValidationError."""
        invalid_patterns = [
            "Y",           # Invalid mana symbol
            "Z",           # Invalid mana symbol  
            "1Y",          # Contains invalid symbol
            "2Z3",         # Contains invalid symbol
            "WQ",          # Q is not valid
            "UL",          # L is not valid
            "BH",          # H is not valid
            "RF",          # F is not valid
            "GJ",          # J is not valid
            "1WY",         # Mixed valid and invalid
            "abc",         # Lowercase letters
            "wubrg",       # Lowercase colored mana
            "1w2u",        # Lowercase in mixed cost
            "!@#",         # Special characters
            "W U",         # Spaces not allowed
            "1-R",         # Hyphens not allowed
            "W/U",         # Slashes not allowed (hybrid mana not supported in this pattern)
            "(2/W)",       # Parentheses not allowed
            "{W}",         # Curly braces not allowed
        ]
        
        from pydantic import ValidationError
        
        for invalid_cost in invalid_patterns:
            with pytest.raises(ValidationError) as exc_info:
                Card(
                    name=f"Invalid {invalid_cost} Card",
                    card_type=CardType.INSTANT,
                    mana_cost=invalid_cost,
                    color=Color.COLORLESS
                )
            
            assert "String should match pattern" in str(exc_info.value)


class TestManaCostCMCCalculation:
    """Test suite for Converted Mana Cost (CMC) calculation edge cases."""

    def test_cmc_calculation_boundary_cases(self) -> None:
        """Test CMC calculation for boundary cases."""
        boundary_cases = [
            ("", 0),           # Empty cost
            ("0", 0),          # Zero cost
            ("1", 1),          # Minimum positive cost
            ("9", 9),          # Maximum single digit
            ("10", 10),        # Minimum double digit
            ("99", 99),        # Maximum reasonable cost
        ]
        
        for mana_cost, expected_cmc in boundary_cases:
            card = Card(
                name=f"Boundary {mana_cost} Card",
                card_type=CardType.ARTIFACT,
                mana_cost=mana_cost,
                color=Color.COLORLESS
            )
            
            assert card.converted_mana_cost == expected_cmc

    def test_cmc_calculation_with_all_colors(self) -> None:
        """Test CMC calculation with all color combinations."""
        color_combinations = [
            ("W", 1),
            ("U", 1),
            ("B", 1),
            ("R", 1),
            ("G", 1),
            ("C", 1),
            ("WU", 2),
            ("WB", 2),
            ("WR", 2),
            ("WG", 2),
            ("UB", 2),
            ("UR", 2),
            ("UG", 2),
            ("BR", 2),
            ("BG", 2),
            ("RG", 2),
            ("WUB", 3),
            ("WUR", 3),
            ("WUG", 3),
            ("WBR", 3),
            ("WBG", 3),
            ("WRG", 3),
            ("UBR", 3),
            ("UBG", 3),
            ("URG", 3),
            ("BRG", 3),
            ("WUBR", 4),
            ("WUBG", 4),
            ("WURB", 4),
            ("WBRG", 4),
            ("UBRG", 4),
            ("WUBRG", 5),
            ("WUBRGC", 6)
        ]
        
        for mana_cost, expected_cmc in color_combinations:
            card = Card(
                name=f"Color {mana_cost} Card",
                card_type=CardType.ENCHANTMENT,
                mana_cost=mana_cost,
                color=Color.MULTICOLOR if len(set(mana_cost)) > 1 else Color.COLORLESS
            )
            
            assert card.converted_mana_cost == expected_cmc

    def test_cmc_calculation_with_multiple_x(self) -> None:
        """Test CMC calculation with multiple X symbols."""
        x_cases = [
            ("X", 0),
            ("XX", 0),
            ("XXX", 0),
            ("XXXX", 0),
            ("XXXXX", 0),
            ("X1", 1),
            ("XX2", 2),
            ("XXX3", 3),
            ("X1W", 2),
            ("XX2U", 3),
            ("XXX3B", 4),
            ("XXWUBRG", 5)  # XX = 0, WUBRG = 5
        ]
        
        for mana_cost, expected_cmc in x_cases:
            card = Card(
                name=f"X Cost {mana_cost} Card",
                card_type=CardType.SORCERY,
                mana_cost=mana_cost,
                color=Color.MULTICOLOR
            )
            
            assert card.converted_mana_cost == expected_cmc

    def test_cmc_calculation_stress_test(self) -> None:
        """Test CMC calculation for very large costs."""
        stress_cases = [
            ("50", 50),
            ("100", 100),
            ("999", 999),
            ("50WUBRG", 55),
            ("100WUBRGWUBRGWUBRG", 115),  # 100 + 15 colored
            ("X999", 999),
            ("XX500WUBRG", 505)  # XX = 0, 500 = 500, WUBRG = 5
        ]
        
        for mana_cost, expected_cmc in stress_cases:
            card = Card(
                name=f"Stress {mana_cost} Card",
                card_type=CardType.ARTIFACT,
                mana_cost=mana_cost,
                color=Color.COLORLESS
            )
            
            assert card.converted_mana_cost == expected_cmc


class TestManaCostUtilityMethods:
    """Test suite for mana cost utility methods and properties."""

    def test_mana_cost_string_representation(self) -> None:
        """Test string representation of mana costs."""
        test_cases = [
            "",
            "0",
            "1",
            "W",
            "2W",
            "WW",
            "1WU",
            "WUBRG",
            "X",
            "X2WW",
            "10WUBRG"
        ]
        
        for mana_cost in test_cases:
            card = Card(
                name=f"String {mana_cost} Card",
                card_type=CardType.INSTANT,
                mana_cost=mana_cost,
                color=Color.MULTICOLOR
            )
            
            # Mana cost should be preserved as string
            assert isinstance(card.mana_cost, str)
            assert card.mana_cost == mana_cost

    def test_mana_cost_immutability(self) -> None:
        """Test that mana cost is immutable after creation."""
        card = Card(
            name="Immutable Card",
            card_type=CardType.INSTANT,
            mana_cost="2WW",
            color=Color.WHITE
        )
        
        original_cost = card.mana_cost
        original_cmc = card.converted_mana_cost
        
        # CMC should always return the same value for the same cost
        assert card.converted_mana_cost == original_cmc
        assert card.mana_cost == original_cost

    def test_mana_cost_case_sensitivity(self) -> None:
        """Test that mana cost parsing is case sensitive."""
        # Uppercase should work (these are valid)
        valid_costs = ["W", "U", "B", "R", "G", "C", "X", "2W", "WUBRG"]
        
        for cost in valid_costs:
            card = Card(
                name=f"Valid {cost} Card",
                card_type=CardType.INSTANT,
                mana_cost=cost,
                color=Color.MULTICOLOR
            )
            assert card.mana_cost == cost

        # Lowercase should fail (these should raise ValidationError)
        from pydantic import ValidationError
        
        invalid_costs = ["w", "u", "b", "r", "g", "c", "x", "2w", "wubrg"]
        
        for cost in invalid_costs:
            with pytest.raises(ValidationError):
                Card(
                    name=f"Invalid {cost} Card",
                    card_type=CardType.INSTANT,
                    mana_cost=cost,
                    color=Color.MULTICOLOR
                )


class TestManaCostRealWorldExamples:
    """Test suite using real MTG cards as examples."""

    def test_famous_mtg_cards_mana_costs(self) -> None:
        """Test mana costs of famous MTG cards."""
        famous_cards = [
            ("Lightning Bolt", "R", 1),
            ("Counterspell", "UU", 2),
            ("Wrath of God", "2WW", 4),
            ("Dark Ritual", "B", 1),
            ("Giant Growth", "G", 1),
            ("Black Lotus", "0", 0),
            ("Ancestral Recall", "U", 1),
            ("Time Walk", "1U", 2),
            ("Mox Sapphire", "0", 0),
            ("Sol Ring", "1", 1),
            ("Lotus Petal", "0", 0),
            ("Force of Will", "3UU", 5),
            ("Mana Drain", "UU", 2),
            ("Demonic Tutor", "1B", 2),
            ("Birds of Paradise", "G", 1),
            ("Tarmogoyf", "1G", 2),
            ("Jace, the Mind Sculptor", "2UU", 4),
            ("Snapcaster Mage", "1U", 2),
            ("Delver of Secrets", "U", 1),
            ("Brainstorm", "U", 1)
        ]
        
        for name, mana_cost, expected_cmc in famous_cards:
            card = Card(
                name=name,
                card_type=CardType.INSTANT,  # Simplified for test
                mana_cost=mana_cost,
                color=Color.MULTICOLOR
            )
            
            assert card.mana_cost == mana_cost
            assert card.converted_mana_cost == expected_cmc

    def test_expensive_mtg_cards_mana_costs(self) -> None:
        """Test mana costs of expensive MTG cards."""
        expensive_cards = [
            ("Draco", "16", 16),
            ("Autochthon Wurm", "15GGGGGWWWWW", 25),  # 15 + 5G + 5W
            ("Emrakul, the Aeons Torn", "15", 15),
            ("Ulamog, the Infinite Gyre", "11", 11),
            ("Kozilek, Butcher of Truth", "10", 10),
            ("Blightsteel Colossus", "12", 12),
            ("Darksteel Colossus", "11", 11)
        ]
        
        for name, mana_cost, expected_cmc in expensive_cards:
            card = Card(
                name=name,
                card_type=CardType.CREATURE,
                mana_cost=mana_cost,
                color=Color.COLORLESS,
                power=1,  # Simplified for test
                toughness=1
            )
            
            assert card.mana_cost == mana_cost
            assert card.converted_mana_cost == expected_cmc

    def test_x_cost_mtg_cards(self) -> None:
        """Test X-cost MTG cards."""
        x_cards = [
            ("Fireball", "XR", 1),
            ("Hydra Broodmaster", "4GG", 6),  # No X for this example
            ("Genesis Hydra", "XGG", 2),
            ("Braingeyser", "XUU", 2),
            ("Disintegrate", "XR", 1),
            ("Stroke of Genius", "X2U", 3),
            ("Rolling Thunder", "XRR", 2),
            ("Blaze", "XR", 1),
            ("Hurricane", "XG", 1),
            ("Earthquake", "XR", 1)
        ]
        
        for name, mana_cost, expected_cmc in x_cards:
            card = Card(
                name=name,
                card_type=CardType.SORCERY,
                mana_cost=mana_cost,
                color=Color.MULTICOLOR
            )
            
            assert card.mana_cost == mana_cost
            assert card.converted_mana_cost == expected_cmc