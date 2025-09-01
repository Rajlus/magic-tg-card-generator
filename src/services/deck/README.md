# Deck Validator Service

## Overview

The DeckValidator service provides comprehensive MTG format rule validation for the Magic: The Gathering Card Generator. It validates decks against format-specific rules including card counts, singleton restrictions, color identity, and banned lists.

## Features

### Supported Formats
- **Commander**: 100 cards, singleton, color identity validation
- **Standard**: 60+ cards, max 4 copies per non-basic
- **Modern**: 60+ cards, max 4 copies per non-basic
- **Legacy**: 60+ cards, max 4 copies per non-basic
- **Vintage**: 60+ cards, restricted list support
- **Pauper**: 60+ cards, commons only

### Core Validation Rules
- Card count validation (format-specific minimums/maximums)
- Copy limits (singleton for Commander, 4x for others)
- Color identity validation (Commander format)
- Banned card detection (format-specific lists)
- Restricted card detection (Vintage)
- Rarity restrictions (Pauper commons-only)

### Advanced Features
- Comprehensive error reporting with specific messages
- Helpful suggestions for deck improvement
- Warning system for suboptimal deck composition
- Mana curve analysis and recommendations
- Color distribution analysis

## Classes

### DeckValidator
Main validation engine that checks decks against format rules.

```python
validator = DeckValidator(DeckFormat.COMMANDER)
result = validator.validate(deck, commander)
```

### DeckFormat (Enum)
Enumeration of supported MTG formats:
- `COMMANDER`
- `STANDARD` 
- `MODERN`
- `LEGACY`
- `VINTAGE`
- `PAUPER`

### ValidationResult (Dataclass)
Structured validation results containing:
- `is_valid: bool` - Overall validation status
- `errors: List[str]` - Validation failures that prevent legality
- `warnings: List[str]` - Suboptimal choices that don't affect legality
- `suggestions: List[str]` - Recommendations for improvement

### CardCollection
Utility class for managing groups of MTG cards with methods for:
- Card counting and uniqueness checking
- Mana curve calculation
- Color distribution analysis
- Type-based filtering

## Helper Methods

### DeckValidator Methods
- `is_basic_land(card: MTGCard) -> bool` - Check if card is basic land
- `get_color_identity(card: MTGCard) -> Set[str]` - Extract color identity
- `is_legal_in_format(card: MTGCard, format: DeckFormat) -> bool` - Check format legality

### Validation Methods
- `validate_commander_identity()` - Check color identity rules
- `validate_singleton()` - Check singleton restrictions  
- `validate_card_count()` - Check deck size requirements
- `check_banned_list()` - Check for banned cards

## Usage Examples

### Basic Commander Validation
```python
from src.services.deck import DeckValidator, DeckFormat, CardCollection
from src.domain.models.mtg_card import MTGCard

# Setup
validator = DeckValidator(DeckFormat.COMMANDER)
deck = CardCollection()
commander = MTGCard(id=1, name="Alesha", type="Legendary Creature", cost="{2}{R}")

# Add cards to deck
deck.add_card(MTGCard(id=2, name="Lightning Bolt", type="Instant", cost="{R}"))

# Validate
result = validator.validate(deck, commander)
if result.is_valid:
    print("Deck is legal!")
else:
    print("Validation errors:")
    for error in result.errors:
        print(f"  - {error}")
```

### Standard Validation
```python
validator = DeckValidator(DeckFormat.STANDARD)
deck = CardCollection()

# Build 60-card Standard deck...
result = validator.validate(deck)
print(f"Valid: {result.is_valid}")
```

### Pauper Validation
```python
validator = DeckValidator(DeckFormat.PAUPER) 
deck = CardCollection()

# Add only common cards...
result = validator.validate(deck)
for warning in result.warnings:
    print(f"Warning: {warning}")
```

## Testing

The implementation includes comprehensive unit tests covering:
- All format validations
- Error conditions and edge cases
- Helper method functionality
- Suggestion and warning generation

Run tests with:
```bash
python -m pytest tests/services/deck/test_deck_validator.py -v
```

## Integration

The DeckValidator integrates seamlessly with the existing MTG Card Generator:
- Uses existing `MTGCard` domain model
- Follows established project patterns
- Provides structured error reporting for UI integration
- Thread-safe for concurrent validation