"""Tests for CardColors value object."""

import pytest

from src.domain.value_objects.card_colors import CardColors, MTGColor
from src.domain.value_objects.mana_cost import ManaCost


class TestCardColorsCreation:
    """Test CardColors creation and validation."""

    def test_create_from_colors(self):
        """Test creating CardColors from individual colors."""
        colors = CardColors.from_colors("W", "U")
        assert "W" in colors
        assert "U" in colors
        assert len(colors) == 2

    def test_create_from_mana_cost_string(self):
        """Test creating CardColors from mana cost string."""
        colors = CardColors.from_mana_cost("{2}{W}{U}")
        assert "W" in colors
        assert "U" in colors
        assert len(colors) == 2

    def test_create_from_mana_cost_object(self):
        """Test creating CardColors from ManaCost object."""
        mana_cost = ManaCost("{R}{G}")
        colors = CardColors.from_mana_cost(mana_cost)
        assert "R" in colors
        assert "G" in colors
        assert len(colors) == 2

    def test_create_colorless(self):
        """Test creating colorless CardColors."""
        colors = CardColors.colorless()
        assert colors.is_colorless
        assert len(colors) == 0

    def test_create_monocolored(self):
        """Test creating monocolored CardColors."""
        white = CardColors.white()
        blue = CardColors.blue()
        black = CardColors.black()
        red = CardColors.red()
        green = CardColors.green()

        assert white.is_white and white.is_monocolored
        assert blue.is_blue and blue.is_monocolored
        assert black.is_black and black.is_monocolored
        assert red.is_red and red.is_monocolored
        assert green.is_green and green.is_monocolored

    def test_create_all_colors(self):
        """Test creating five-color CardColors."""
        colors = CardColors.all_colors()
        assert colors.is_five_color
        assert len(colors) == 5
        assert all(color in colors for color in ["W", "U", "B", "R", "G"])

    def test_invalid_color_raises_error(self):
        """Test that invalid colors raise ValueError."""
        with pytest.raises(ValueError):
            CardColors.from_colors("Q")  # Q is not a valid color

        with pytest.raises(ValueError):
            CardColors(frozenset(["W", "X"]))  # X is not a valid color


class TestColorIdentityProperties:
    """Test color identity classification properties."""

    def test_colorless_properties(self):
        """Test colorless identification."""
        colors = CardColors.colorless()
        assert colors.is_colorless
        assert not colors.is_monocolored
        assert not colors.is_multicolored
        assert colors.color_count == 0

    def test_monocolored_properties(self):
        """Test monocolored identification."""
        colors = CardColors.white()
        assert not colors.is_colorless
        assert colors.is_monocolored
        assert not colors.is_multicolored
        assert colors.color_count == 1

    def test_multicolored_properties(self):
        """Test multicolored identification."""
        colors = CardColors.from_colors("W", "U")
        assert not colors.is_colorless
        assert not colors.is_monocolored
        assert colors.is_multicolored
        assert colors.color_count == 2

    def test_guild_properties(self):
        """Test two-color guild identification."""
        guild = CardColors.from_colors("W", "U")
        assert guild.is_guild
        assert guild.is_multicolored
        assert not guild.is_shard
        assert not guild.is_wedge
        assert guild.guild_name == "Azorius"

    def test_shard_properties(self):
        """Test three-color shard identification."""
        shard = CardColors.from_colors("W", "U", "G")  # Bant
        assert not shard.is_guild
        assert shard.is_shard
        assert not shard.is_wedge
        assert shard.shard_name == "Bant"

    def test_wedge_properties(self):
        """Test three-color wedge identification."""
        wedge = CardColors.from_colors("W", "B", "G")  # Abzan
        assert not wedge.is_guild
        assert not wedge.is_shard
        assert wedge.is_wedge
        assert wedge.wedge_name == "Abzan"

    def test_four_color_properties(self):
        """Test four-color identification."""
        colors = CardColors.from_colors("W", "U", "B", "R")
        assert colors.is_four_color
        assert not colors.is_guild
        assert not colors.is_shard
        assert not colors.is_wedge

    def test_five_color_properties(self):
        """Test five-color identification."""
        colors = CardColors.all_colors()
        assert colors.is_five_color
        assert not colors.is_four_color
        assert colors.color_count == 5


class TestGuildNames:
    """Test guild name identification."""

    def test_all_guild_names(self):
        """Test all ten guild names."""
        guild_tests = [
            (["W", "U"], "Azorius"),
            (["U", "B"], "Dimir"),
            (["B", "R"], "Rakdos"),
            (["R", "G"], "Gruul"),
            (["G", "W"], "Selesnya"),
            (["W", "B"], "Orzhov"),
            (["U", "R"], "Izzet"),
            (["B", "G"], "Golgari"),
            (["R", "W"], "Boros"),
            (["G", "U"], "Simic"),
        ]

        for color_list, expected_name in guild_tests:
            colors = CardColors.from_colors(*color_list)
            assert colors.guild_name == expected_name

    def test_non_guild_has_empty_name(self):
        """Test non-guild combinations return empty name."""
        colors = CardColors.from_colors("W", "U", "B")  # Three colors
        assert colors.guild_name == ""

        colors = CardColors.colorless()
        assert colors.guild_name == ""


class TestShardAndWedgeNames:
    """Test shard and wedge name identification."""

    def test_shard_names(self):
        """Test shard names."""
        shard_tests = [
            (["W", "U", "G"], "Bant"),
            (["U", "B", "R"], "Grixis"),
            (["B", "R", "G"], "Jund"),
            (["R", "G", "W"], "Naya"),
        ]

        for color_list, expected_name in shard_tests:
            colors = CardColors.from_colors(*color_list)
            assert colors.shard_name == expected_name

    def test_wedge_names(self):
        """Test wedge names."""
        wedge_tests = [
            (["W", "B", "G"], "Abzan"),
            (["U", "R", "W"], "Jeskai"),
            (["B", "G", "U"], "Sultai"),
            (["R", "W", "B"], "Mardu"),
            (["G", "U", "R"], "Temur"),
        ]

        for color_list, expected_name in wedge_tests:
            colors = CardColors.from_colors(*color_list)
            assert colors.wedge_name == expected_name

    def test_non_shard_wedge_empty_names(self):
        """Test non-shard/wedge combinations return empty names."""
        colors = CardColors.from_colors("W", "U")  # Guild
        assert colors.shard_name == ""
        assert colors.wedge_name == ""


class TestColorOperations:
    """Test color operations and methods."""

    def test_contains_color(self):
        """Test contains_color method."""
        colors = CardColors.from_colors("W", "U")
        assert colors.contains_color("W")
        assert colors.contains_color("U")
        assert not colors.contains_color("B")

        with pytest.raises(ValueError):
            colors.contains_color("Q")  # Invalid color

    def test_shares_colors_with(self):
        """Test shares_colors_with method."""
        colors1 = CardColors.from_colors("W", "U")
        colors2 = CardColors.from_colors("U", "B")
        colors3 = CardColors.from_colors("R", "G")

        assert colors1.shares_colors_with(colors2)  # Both have U
        assert not colors1.shares_colors_with(colors3)  # No common colors

    def test_subset_superset(self):
        """Test subset and superset relationships."""
        mono_white = CardColors.white()
        azorius = CardColors.from_colors("W", "U")
        bant = CardColors.from_colors("W", "U", "G")

        assert mono_white.is_subset_of(azorius)
        assert mono_white.is_subset_of(bant)
        assert azorius.is_subset_of(bant)

        assert bant.is_superset_of(azorius)
        assert bant.is_superset_of(mono_white)
        assert azorius.is_superset_of(mono_white)

    def test_union_with(self):
        """Test union_with method."""
        white = CardColors.white()
        blue = CardColors.blue()
        azorius = white.union_with(blue)

        assert azorius.is_guild
        assert azorius.guild_name == "Azorius"
        assert "W" in azorius and "U" in azorius

    def test_intersection_with(self):
        """Test intersection_with method."""
        azorius = CardColors.from_colors("W", "U")
        orzhov = CardColors.from_colors("W", "B")
        intersection = azorius.intersection_with(orzhov)

        assert intersection.is_white
        assert len(intersection) == 1

    def test_without_colors(self):
        """Test without_colors method."""
        bant = CardColors.from_colors("W", "U", "G")
        without_green = bant.without_colors("G")

        assert without_green.is_guild
        assert without_green.guild_name == "Azorius"
        assert "G" not in without_green

    def test_add_colors(self):
        """Test add_colors method."""
        azorius = CardColors.from_colors("W", "U")
        bant = azorius.add_colors("G")

        assert bant.is_shard
        assert bant.shard_name == "Bant"
        assert len(bant) == 3


class TestColorIterationAndAccess:
    """Test color iteration and access patterns."""

    def test_iteration_order(self):
        """Test colors iterate in WUBRG order."""
        colors = CardColors.from_colors("G", "B", "W")  # Out of order
        color_list = list(colors)
        assert color_list == ["W", "B", "G"]  # WUBRG order

    def test_len_operation(self):
        """Test len() operation."""
        assert len(CardColors.colorless()) == 0
        assert len(CardColors.white()) == 1
        assert len(CardColors.from_colors("W", "U")) == 2
        assert len(CardColors.all_colors()) == 5

    def test_contains_operation(self):
        """Test 'in' operator."""
        colors = CardColors.from_colors("W", "U")
        assert "W" in colors
        assert "U" in colors
        assert "B" not in colors

    def test_color_names_property(self):
        """Test color_names property."""
        colors = CardColors.from_colors("R", "W", "G")
        names = colors.color_names
        assert names == ["White", "Red", "Green"]  # WUBRG order: W, R, G


class TestColorRepresentation:
    """Test string representations and display."""

    def test_string_representation(self):
        """Test string representation in WUBRG order."""
        assert str(CardColors.colorless()) == "Colorless"
        assert str(CardColors.white()) == "W"
        assert str(CardColors.from_colors("U", "W")) == "WU"
        assert str(CardColors.from_colors("G", "R", "B")) == "BRG"
        assert str(CardColors.all_colors()) == "WUBRG"

    def test_repr_representation(self):
        """Test repr representation."""
        colorless = CardColors.colorless()
        assert repr(colorless) == "CardColors(colorless)"

        white = CardColors.white()
        assert "White" in repr(white)

        azorius = CardColors.from_colors("W", "U")
        assert "White" in repr(azorius) and "Blue" in repr(azorius)

    def test_boolean_evaluation(self):
        """Test boolean evaluation."""
        assert not CardColors.colorless()  # Colorless is falsy
        assert CardColors.white()  # Has colors is truthy
        assert CardColors.all_colors()  # Has colors is truthy


class TestColorEquality:
    """Test equality and hashing."""

    def test_equality(self):
        """Test equality comparison."""
        colors1 = CardColors.from_colors("W", "U")
        colors2 = CardColors.from_colors("U", "W")  # Same colors, different order
        colors3 = CardColors.from_colors("W", "B")

        assert colors1 == colors2  # Order doesn't matter
        assert colors1 != colors3
        assert colors1 != "not card colors"

    def test_hash(self):
        """Test hashing for use in sets/dicts."""
        colors1 = CardColors.from_colors("W", "U")
        colors2 = CardColors.from_colors("U", "W")
        colors3 = CardColors.from_colors("W", "B")

        assert hash(colors1) == hash(colors2)  # Same colors = same hash
        assert hash(colors1) != hash(colors3)

        # Can be used in sets
        color_set = {colors1, colors2, colors3}
        assert len(color_set) == 2  # colors1 and colors2 are same


class TestColorOperators:
    """Test operator overloading."""

    def test_union_operator(self):
        """Test | (union) operator."""
        white = CardColors.white()
        blue = CardColors.blue()
        azorius = white | blue

        assert azorius.is_guild
        assert azorius.guild_name == "Azorius"

    def test_intersection_operator(self):
        """Test & (intersection) operator."""
        azorius = CardColors.from_colors("W", "U")
        orzhov = CardColors.from_colors("W", "B")
        intersection = azorius & orzhov

        assert intersection.is_white

    def test_difference_operator(self):
        """Test - (difference) operator."""
        bant = CardColors.from_colors("W", "U", "G")
        azorius = CardColors.from_colors("W", "U")
        difference = bant - azorius

        assert difference == CardColors.green()


class TestColorEdgeCases:
    """Test edge cases and special scenarios."""

    def test_hybrid_mana_color_identity(self):
        """Test color identity from hybrid mana costs."""
        colors = CardColors.from_mana_cost("{W/U}{R/G}")
        # Hybrid mana should include both colors from each hybrid symbol
        expected_colors = {"W", "U", "R", "G"}
        assert colors.colors == frozenset(expected_colors)

    def test_phyrexian_mana_color_identity(self):
        """Test color identity from Phyrexian mana."""
        colors = CardColors.from_mana_cost("{W/P}{U}")
        assert "W" in colors  # Phyrexian white still contributes white identity
        assert "U" in colors
        assert len(colors) == 2

    def test_colorless_mana_cost_identity(self):
        """Test colorless identity from generic/colorless costs."""
        colors = CardColors.from_mana_cost("{5}")
        assert colors.is_colorless

        colors = CardColors.from_mana_cost("{C}{C}")
        assert colors.is_colorless  # {C} doesn't contribute color identity

    def test_empty_mana_cost_identity(self):
        """Test identity from free spells."""
        colors = CardColors.from_mana_cost("")
        assert colors.is_colorless

    def test_immutability(self):
        """Test that CardColors is immutable."""
        colors = CardColors.from_colors("W", "U")

        # Should not be able to modify colors
        with pytest.raises(AttributeError):
            colors.colors.add("B")

    def test_frozenset_conversion(self):
        """Test automatic frozenset conversion."""
        # Should work with regular set input
        colors = CardColors({"W", "U"})
        assert isinstance(colors.colors, frozenset)
        assert len(colors) == 2
