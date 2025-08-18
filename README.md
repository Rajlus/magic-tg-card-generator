# Magic: The Gathering Card Generator

A Python application for generating Magic: The Gathering cards with modern development practices.

## Features

- Generate custom Magic: The Gathering cards
- Type-safe models with Pydantic
- Rich CLI interface
- Comprehensive test coverage
- Pre-commit hooks for code quality
- Fully typed with MyPy support

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Poetry (for dependency management)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/magic-tg-card-generator.git
cd magic-tg-card-generator
```

2. Install dependencies:
```bash
make dev-install
```

Or using Poetry directly:
```bash
poetry install --with dev,docs
poetry run pre-commit install
```

3. Copy the environment file:
```bash
cp .env.example .env
```

4. Run tests to verify installation:
```bash
make test
```

## Usage

### Quick Examples

Run the examples script to see all options:
```bash
./examples.sh
```

### CLI Usage

Generate a creature card:
```bash
poetry run python -m magic_tg_card_generator generate "Lightning Dragon" \
  --type Creature \
  --mana-cost "3RR" \
  --color Red \
  --power 5 \
  --toughness 4 \
  --text "Flying, haste"
```

Generate an instant spell:
```bash
poetry run python -m magic_tg_card_generator generate "Counterspell" \
  --type Instant \
  --mana-cost "UU" \
  --color Blue \
  --text "Counter target spell."
```

### Parameters

- `name` - Card name (required, use quotes for multi-word names)
- `--type` - Card type (required): Creature, Instant, Sorcery, Enchantment, Artifact, Planeswalker, Land
- `--mana-cost` - Mana cost (required): Use numbers and letters (W=White, U=Blue, B=Black, R=Red, G=Green, X=Variable)
- `--color` - Card color (optional): White, Blue, Black, Red, Green, Colorless, Multicolor
- `--power` - Power value (creatures only)
- `--toughness` - Toughness value (creatures only)
- `--text` - Card abilities/rules text (optional)

### Python API Usage

```python
from magic_tg_card_generator import CardGenerator, CardType, Color

generator = CardGenerator()

# Create a creature card
creature = generator.generate_card(
    name="Goblin Warrior",
    card_type=CardType.CREATURE,
    mana_cost="1R",
    color=Color.RED,
    power=2,
    toughness=1,
    text="Haste"
)

print(creature.model_dump_json(indent=2))
```

## Development

### Quick Commands

```bash
make install   # Install everything (first time setup)
make test      # Run tests with coverage report
make format    # Auto-format code
make lint      # Check code style
make clean     # Clean cache files
```

### Coverage Report

Nach `make test` findest du:
- **Terminal**: Coverage-Zusammenfassung mit fehlenden Zeilen
- **HTML Report**: Öffne `htmlcov/index.html` für detaillierte Ansicht
- **Aktuell**: 79% Coverage ✅

### Project Structure

```
magic-tg-card-generator/
├── src/magic_tg_card_generator/
│   ├── __init__.py     # Package initialization
│   ├── __main__.py     # Entry point
│   ├── cli.py          # CLI interface
│   ├── config.py       # Configuration
│   ├── core.py         # Core logic & card saving
│   └── models.py       # Data models
├── tests/              # Test files
├── output/cards/       # Generated cards (auto-created)
├── pyproject.toml      # Project configuration
├── poetry.lock         # Locked dependencies
└── Makefile           # Simple commands
```

### Tools

- **Black**: Code formatting
- **Ruff**: Fast linting
- **Pytest**: Testing
- **Pre-commit**: Auto-format on commit

### Testing

Run tests with coverage:
```bash
make test
```

Run specific test file:
```bash
poetry run pytest tests/test_models.py -v
```

Generate HTML coverage report:
```bash
poetry run pytest --cov=src --cov-report=html
open htmlcov/index.html
```

### Pre-commit Hooks

Pre-commit hooks are automatically installed during `make dev-install`. They run on every commit to ensure code quality.

To run manually:
```bash
make pre-commit
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting (`make test lint`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Magic: The Gathering is a trademark of Wizards of the Coast LLC
- Built with modern Python development tools and best practices
