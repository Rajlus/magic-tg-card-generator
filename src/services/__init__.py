"""Services layer for business logic and orchestration.

This module provides various services for the MTG card generator application.
It includes AI services and deck analysis services.

Submodules:
    ai: AI worker services for card generation
    deck: Deck validation, statistics and analysis services
"""

try:
    from .deck import DeckValidator, DeckFormat, ValidationResult, CardCollection
    DECK_SERVICES_AVAILABLE = True
except ImportError:
    DECK_SERVICES_AVAILABLE = False

try:
    from .deck import DeckStatistics, ManaCurveData, ColorStats, TypeDistribution
    DECK_STATS_AVAILABLE = True
except ImportError:
    DECK_STATS_AVAILABLE = False

__all__ = []

if DECK_SERVICES_AVAILABLE:
    __all__.extend(['DeckValidator', 'DeckFormat', 'ValidationResult', 'CardCollection'])

if DECK_STATS_AVAILABLE:
    __all__.extend(['DeckStatistics', 'ManaCurveData', 'ColorStats', 'TypeDistribution'])