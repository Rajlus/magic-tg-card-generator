"""Deck management services."""

from .deck_validator import DeckValidator, DeckFormat, ValidationResult
from ...domain.models.card_collection import CardCollection

try:
    from .deck_builder_service import DeckBuilderService
except ImportError:
    DeckBuilderService = None

try:
    from .deck_statistics import DeckStatistics, ManaCurveData, ColorStats, TypeDistribution
except ImportError:
    DeckStatistics = ManaCurveData = ColorStats = TypeDistribution = None

__all__ = [
    "DeckValidator",
    "DeckFormat", 
    "ValidationResult",
    "CardCollection"
]

# Add optional imports if available
if DeckBuilderService is not None:
    __all__.append("DeckBuilderService")

if DeckStatistics is not None:
    __all__.extend(["DeckStatistics", "ManaCurveData", "ColorStats", "TypeDistribution"])