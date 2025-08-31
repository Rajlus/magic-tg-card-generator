# Value Objects Implementation: ManaCost and CardColors

## Overview

This implementation provides two robust value objects for handling Magic: The Gathering mana costs and color identity within the card generator application. These value objects follow domain-driven design principles and provide immutable, self-validating representations of core MTG concepts.

## Files Created

### Core Implementation
- `/src/domain/value_objects/mana_cost.py` - ManaCost value object
- `/src/domain/value_objects/card_colors.py` - CardColors value object  
- `/src/domain/value_objects/__init__.py` - Module exports
- `/src/domain/__init__.py` - Domain layer initialization

### Test Suite
- `/tests/domain/value_objects/test_mana_cost.py` - Comprehensive ManaCost tests (21 test methods)
- `/tests/domain/value_objects/test_card_colors.py` - Comprehensive CardColors tests (45 test methods)
- `/tests/domain/value_objects/__init__.py` - Test module initialization
- `/tests/domain/__init__.py` - Test domain initialization

### Examples and Documentation
- `/examples/value_objects_demo.py` - Comprehensive demonstration script
- `/examples/integration_example.py` - Integration with existing system
- `/docs/value_objects_implementation.md` - This documentation

## ManaCost Value Object

### Features

**Core Functionality:**
- Parse MTG mana cost strings (e.g., `{2}{U}{B}`, `{X}{R}`, `{W/P}`)
- Calculate converted mana cost (CMC/Mana Value)
- Validate mana cost format according to MTG rules
- Extract color requirements and generic costs

**Supported Mana Types:**
- Generic mana: `{1}`, `{2}`, `{15}`, etc.
- Colored mana: `{W}`, `{U}`, `{B}`, `{R}`, `{G}`
- Variable costs: `{X}`, `{Y}`, `{Z}`
- Hybrid mana: `{W/U}`, `{2/R}`, etc.
- Phyrexian mana: `{W/P}`, `{U/P}`, etc.
- Snow mana: `{S}`
- Colorless mana: `{C}`

### Usage Examples

```python
from src.domain.value_objects.mana_cost import ManaCost

# Create from string
cost = ManaCost("{2}{U}{B}")
print(cost.converted_mana_cost)  # 4
print(cost.color_requirements)   # {'U': 1, 'B': 1}
print(cost.generic_mana)        # 2

# Create from components
cost = ManaCost.from_components(generic=3, blue=2, red=1)
print(cost.mana_string)         # "{3}{U}{U}{R}"

# Check properties
cost = ManaCost("{X}{R}")
print(cost.has_x_cost)          # True
print(cost.contains_color('R')) # True

# Mana cost arithmetic
bolt = ManaCost("{R}")
expensive_bolt = bolt + "{2}"
print(expensive_bolt)           # "{R}{2}"
```

### Key Methods and Properties

**Creation:**
- `ManaCost(mana_string)` - Create from string
- `ManaCost.from_string(mana_string)` - Alternative creation
- `ManaCost.from_components(**kwargs)` - Create from individual components

**Analysis:**
- `converted_mana_cost` - Calculate CMC
- `color_requirements` - Dict of color requirements
- `generic_mana` - Amount of generic mana
- `colored_mana_count` - Total colored mana symbols

**Validation:**
- `is_free` - Check if spell costs nothing
- `has_x_cost` - Check for variable costs
- `has_hybrid_mana` - Check for hybrid mana
- `has_phyrexian_mana` - Check for Phyrexian mana
- `contains_color(color)` - Check if contains specific color
- `can_be_paid_with_colors(colors)` - Check payment feasibility

## CardColors Value Object

### Features

**Core Functionality:**
- Represent MTG color identity using WUBRG system
- Calculate color identity from mana costs (including hybrid/Phyrexian)
- Classify color combinations (mono, guild, shard, wedge, etc.)
- Provide rich behavioral methods for color operations

**Color Classifications:**
- Colorless (0 colors)
- Monocolored (1 color)
- Guild (2 colors) - Named after Ravnica guilds
- Shard (3 allied colors) - Named after Alara shards
- Wedge (3 enemy colors) - Named after Khans clans
- Four-color and Five-color combinations

### Usage Examples

```python
from src.domain.value_objects.card_colors import CardColors
from src.domain.value_objects.mana_cost import ManaCost

# Create from colors
colors = CardColors.from_colors('W', 'U')
print(colors.guild_name)        # "Azorius"
print(colors.is_guild)          # True

# Create from mana cost
cost = ManaCost("{2}{R}{G}")
colors = CardColors.from_mana_cost(cost)
print(colors)                   # "RG"
print(colors.color_names)       # ['Red', 'Green']

# Convenience constructors
white = CardColors.white()
all_colors = CardColors.all_colors()
colorless = CardColors.colorless()

# Color operations
azorius = CardColors.from_colors('W', 'U')
orzhov = CardColors.from_colors('W', 'B')
white_only = azorius & orzhov   # Intersection
print(white_only.is_white)      # True

# Set operations
jeskai = CardColors.from_colors('W', 'U', 'R')
print(jeskai.wedge_name)        # "Jeskai"
print(jeskai.contains_color('U')) # True
```

### Key Methods and Properties

**Creation:**
- `CardColors.from_colors(*colors)` - Create from color symbols
- `CardColors.from_mana_cost(mana_cost)` - Derive from mana cost
- `CardColors.white()`, `.blue()`, etc. - Monocolored constructors
- `CardColors.colorless()` - Colorless constructor
- `CardColors.all_colors()` - Five-color constructor

**Classification:**
- `is_colorless`, `is_monocolored`, `is_multicolored`
- `is_guild`, `is_shard`, `is_wedge`
- `is_four_color`, `is_five_color`
- `guild_name`, `shard_name`, `wedge_name`

**Operations:**
- `union_with(other)` / `|` operator - Color union
- `intersection_with(other)` / `&` operator - Color intersection
- `without_colors(*colors)` / `-` operator - Color difference
- `add_colors(*colors)` - Add specific colors
- `shares_colors_with(other)` - Check color overlap
- `is_subset_of(other)` - Check containment

**Properties:**
- `color_count` - Number of colors
- `color_names` - Full color names in WUBRG order
- `colors` - Frozenset of color symbols

## Integration with Existing System

The value objects are designed to complement the existing Card model:

```python
# Existing Card model usage
card = Card(name="Lightning Bolt", mana_cost="{R}", ...)

# Enhanced with value objects
mana_cost_vo = ManaCost(card.mana_cost)
colors_vo = CardColors.from_mana_cost(card.mana_cost)

# Now you have rich behavior
print(f"CMC: {mana_cost_vo.converted_mana_cost}")
print(f"Color Identity: {colors_vo}")
print(f"Guild: {colors_vo.guild_name}")
```

## Use Cases

### Deck Validation
```python
def validate_commander_deck(cards, commander_colors):
    """Validate deck against commander color identity."""
    for card in cards:
        card_colors = CardColors.from_mana_cost(card.mana_cost)
        if not card_colors.is_subset_of(commander_colors):
            print(f"{card.name} is illegal in this deck")
```

### Mana Curve Analysis
```python
def analyze_mana_curve(deck):
    """Analyze deck's mana curve."""
    curve = {}
    for card in deck:
        cost = ManaCost(card.mana_cost)
        cmc = cost.converted_mana_cost
        curve[cmc] = curve.get(cmc, 0) + 1
    return curve
```

### Format Legality
```python
def check_format_legality(card, format_rules):
    """Check if card is legal in format."""
    cost = ManaCost(card.mana_cost)
    return cost.converted_mana_cost <= format_rules.max_cmc
```

## Testing

The implementation includes comprehensive test suites:

- **ManaCost**: 21 test methods covering creation, validation, CMC calculation, properties, operations, and edge cases
- **CardColors**: 45 test methods covering creation, classification, operations, representation, and advanced scenarios

Run tests with:
```bash
python -m pytest tests/domain/value_objects/ -v
```

All tests pass, providing confidence in the implementation's correctness.

## Design Principles

**Value Object Pattern:**
- Immutable (frozen dataclasses)
- Self-validating (validation in constructors)
- Equality based on value, not identity
- Rich behavior beyond simple data storage

**Domain-Driven Design:**
- Express domain concepts clearly
- Use ubiquitous language (MTG terminology)
- Encapsulate business rules
- Provide meaningful operations

**Robustness:**
- Comprehensive input validation
- Clear error messages
- Support for edge cases
- Extensive test coverage

## Future Enhancements

The value objects provide a solid foundation for future MTG-specific features:

- **Advanced Mana Costs**: Support for more complex mana costs like `{2/W/U}`
- **Alternative Costs**: Representation of alternative casting costs
- **Mana Abilities**: Integration with mana production capabilities  
- **Format Rules**: Embedded format-specific validation rules
- **Deck Statistics**: Advanced deck analysis and recommendations
- **Card Interactions**: Rules for card interactions based on color identity

## Benefits

1. **Type Safety**: Compile-time guarantees about mana cost validity
2. **Rich Behavior**: Domain operations beyond simple data storage
3. **Immutability**: Thread-safe, cache-friendly, predictable behavior
4. **Validation**: Automatic validation prevents invalid states
5. **Expressiveness**: Code reads like domain language
6. **Testability**: Easy to test with comprehensive coverage
7. **Maintainability**: Changes to mana cost logic centralized
8. **Performance**: Efficient operations with caching opportunities

The ManaCost and CardColors value objects significantly enhance the Magic: The Gathering card generator by providing robust, domain-specific representations of core MTG concepts. They follow software engineering best practices while accurately modeling the complex rules and relationships inherent in Magic: The Gathering.