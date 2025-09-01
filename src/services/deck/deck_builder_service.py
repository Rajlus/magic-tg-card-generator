"""
Deck Builder Service

Main service for deck building operations including deck management,
validation, statistics, and import/export functionality.
"""

import json
import threading
from typing import Dict, List, Optional, Any
from collections import Counter, defaultdict

from ...domain.models.card_collection import CardCollection
from ...domain.models.mtg_card import MTGCard


class DeckBuilderService:
    """Service for deck building operations with thread-safe state management."""
    
    def __init__(self):
        """Initialize the deck builder service."""
        self.deck = CardCollection()
        self.sideboard = CardCollection(max_size=15)
        self._commander: Optional[MTGCard] = None
        self._lock = threading.RLock()  # Re-entrant lock for thread safety
        
    def add_card(self, card: MTGCard, quantity: int = 1, to_sideboard: bool = False) -> bool:
        """
        Add card to deck or sideboard with validation.
        
        Args:
            card: The MTGCard to add
            quantity: Number of copies to add (default: 1)
            to_sideboard: Whether to add to sideboard instead of deck
            
        Returns:
            bool: True if cards were added successfully, False if limits exceeded
            
        Raises:
            ValueError: If quantity is invalid or card is None
        """
        if card is None:
            raise ValueError("Card cannot be None")
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
            
        with self._lock:
            target_collection = self.sideboard if to_sideboard else self.deck
            
            # Additional validation for legendary cards in Commander format
            if not to_sideboard and self._is_legendary(card) and not card.is_land():
                # In Commander, only one copy of legendary non-land cards allowed
                if target_collection.contains(card.name) and quantity > 0:
                    return False
                    
            return target_collection.add(card, quantity)
    
    def remove_card(self, card_id: str, from_sideboard: bool = False) -> bool:
        """
        Remove card from deck or sideboard.
        
        Args:
            card_id: The ID of the card to remove (as string)
            from_sideboard: Whether to remove from sideboard instead of deck
            
        Returns:
            bool: True if card was removed, False if not found
        """
        with self._lock:
            target_collection = self.sideboard if from_sideboard else self.deck
            return target_collection.remove(card_id)
    
    def move_to_sideboard(self, card_id: str) -> bool:
        """
        Move card from deck to sideboard.
        
        Args:
            card_id: The ID of the card to move
            
        Returns:
            bool: True if card was moved successfully, False otherwise
        """
        with self._lock:
            # Find the card in the deck
            try:
                card_id_int = int(card_id)
            except ValueError:
                return False
                
            card_to_move = None
            for card in self.deck.cards:
                if card.id == card_id_int:
                    card_to_move = card
                    break
                    
            if card_to_move is None:
                return False
                
            # Check if sideboard has space
            if self.sideboard.total_cards >= (self.sideboard.max_size or 15):
                return False
                
            # Remove from deck and add to sideboard
            if self.deck.remove(card_id) and self.sideboard.add(card_to_move):
                return True
            else:
                # Rollback if sideboard add failed
                self.deck.add(card_to_move)
                return False
    
    def move_to_deck(self, card_id: str) -> bool:
        """
        Move card from sideboard to deck.
        
        Args:
            card_id: The ID of the card to move
            
        Returns:
            bool: True if card was moved successfully, False otherwise
        """
        with self._lock:
            # Find the card in the sideboard
            try:
                card_id_int = int(card_id)
            except ValueError:
                return False
                
            card_to_move = None
            for card in self.sideboard.cards:
                if card.id == card_id_int:
                    card_to_move = card
                    break
                    
            if card_to_move is None:
                return False
                
            # Remove from sideboard and add to deck
            if self.sideboard.remove(card_id) and self.deck.add(card_to_move):
                return True
            else:
                # Rollback if deck add failed
                self.sideboard.add(card_to_move)
                return False
    
    def validate_commander_deck(self) -> Dict[str, bool]:
        """
        Validate deck for Commander format.
        
        Returns:
            Dict with validation results:
            - has_commander: Has a valid commander
            - valid_deck_size: Deck has exactly 99 cards (excluding commander)
            - singleton_rule: No duplicates except basic lands
            - color_identity: All cards match commander's color identity
            - valid_sideboard_size: Sideboard has 0-15 cards
        """
        with self._lock:
            validation = {
                'has_commander': self._commander is not None,
                'valid_deck_size': self.deck.total_cards == 99,
                'singleton_rule': self._validate_singleton_rule(),
                'color_identity': self._validate_color_identity(),
                'valid_sideboard_size': self.sideboard.total_cards <= 15
            }
            
        return validation
    
    def get_mana_curve(self) -> Dict[int, int]:
        """
        Calculate mana curve distribution.
        
        Returns:
            Dict mapping mana cost to number of cards
        """
        with self._lock:
            curve = defaultdict(int)
            
            for card in self.deck.cards:
                cmc = self._calculate_cmc(card)
                curve[cmc] += 1
                
            # Convert to regular dict and ensure 0-10+ range
            result = {}
            for i in range(11):  # 0-10
                result[i] = curve.get(i, 0)
                
            # Handle cards with CMC > 10
            high_cmc_count = sum(count for cmc, count in curve.items() if cmc > 10)
            if high_cmc_count > 0:
                result[10] = result[10] + high_cmc_count  # Add to "10+" category
                
        return result
    
    def get_color_distribution(self) -> Dict[str, int]:
        """
        Get color distribution of deck.
        
        Returns:
            Dict mapping color symbols to count of cards containing that color
        """
        with self._lock:
            colors = {'W': 0, 'U': 0, 'B': 0, 'R': 0, 'G': 0, 'C': 0}
            
            for card in self.deck.cards:
                card_colors = self._extract_colors_from_cost(card.cost)
                for color in card_colors:
                    if color in colors:
                        colors[color] += 1
                        
        return colors
    
    def suggest_lands(self) -> Dict[str, int]:
        """
        Suggest land distribution based on color requirements.
        
        Returns:
            Dict with suggested land counts by type:
            - basic_lands: Dict of basic land types to counts
            - total_lands: Recommended total number of lands
            - fixing_lands: Recommended number of multicolor/fixing lands
        """
        with self._lock:
            color_dist = self.get_color_distribution()
            total_nonland_cards = sum(1 for card in self.deck.cards if not card.is_land())
            
            # Basic land calculation based on color intensity
            total_color_symbols = sum(color_dist.values())
            
            if total_color_symbols == 0:
                # Colorless deck
                return {
                    'basic_lands': {'Wastes': 35},
                    'total_lands': 35,
                    'fixing_lands': 0
                }
            
            # Calculate proportions
            color_proportions = {
                color: count / total_color_symbols 
                for color, count in color_dist.items() 
                if count > 0
            }
            
            # Recommend 36-38 lands for Commander
            recommended_total_lands = 37
            fixing_lands = max(5, len([c for c in color_proportions if color_proportions[c] > 0.1]))
            basic_land_slots = recommended_total_lands - fixing_lands
            
            basic_lands = {}
            land_names = {'W': 'Plains', 'U': 'Island', 'B': 'Swamp', 'R': 'Mountain', 'G': 'Forest'}
            
            for color, proportion in color_proportions.items():
                if color in land_names and proportion > 0.05:  # Only suggest if 5%+ representation
                    basic_lands[land_names[color]] = max(1, int(basic_land_slots * proportion))
            
            return {
                'basic_lands': basic_lands,
                'total_lands': recommended_total_lands,
                'fixing_lands': fixing_lands
            }
    
    def get_deck_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive deck statistics.
        
        Returns:
            Dict with various deck statistics
        """
        with self._lock:
            stats = {
                'deck_size': self.deck.total_cards,
                'sideboard_size': self.sideboard.total_cards,
                'unique_cards': self.deck.unique_card_count,
                'commander': self._commander.name if self._commander else None,
                'mana_curve': self.get_mana_curve(),
                'color_distribution': self.get_color_distribution(),
                'type_distribution': self._get_type_distribution(),
                'rarity_distribution': self._get_rarity_distribution(),
                'average_cmc': self._calculate_average_cmc(),
                'land_count': sum(1 for card in self.deck.cards if card.is_land()),
                'creature_count': sum(1 for card in self.deck.cards if card.is_creature()),
            }
            
        return stats
    
    def export_deck(self, format_type: str) -> str:
        """
        Export deck in specified format.
        
        Args:
            format_type: Export format ('text', 'json', 'arena')
            
        Returns:
            String representation of the deck in specified format
            
        Raises:
            ValueError: If format_type is not supported
        """
        with self._lock:
            if format_type.lower() == 'text':
                return self._export_as_text()
            elif format_type.lower() == 'json':
                return self._export_as_json()
            elif format_type.lower() == 'arena':
                return self._export_as_arena()
            else:
                raise ValueError(f"Unsupported export format: {format_type}")
    
    def import_deck(self, data: str, format_type: str) -> bool:
        """
        Import deck from string data.
        
        Args:
            data: String data containing deck information
            format_type: Import format ('text', 'json', 'arena')
            
        Returns:
            bool: True if import was successful, False otherwise
            
        Raises:
            ValueError: If format_type is not supported
        """
        try:
            with self._lock:
                if format_type.lower() == 'json':
                    return self._import_from_json(data)
                elif format_type.lower() == 'text':
                    return self._import_from_text(data)
                elif format_type.lower() == 'arena':
                    return self._import_from_arena(data)
                else:
                    raise ValueError(f"Unsupported import format: {format_type}")
        except Exception:
            return False
    
    def clear_deck(self) -> None:
        """Clear all cards from deck and sideboard."""
        with self._lock:
            self.deck.clear()
            self.sideboard.clear()
            self._commander = None
    
    def get_commander(self) -> Optional[MTGCard]:
        """
        Get the current commander card.
        
        Returns:
            The commander card, or None if no commander is set
        """
        with self._lock:
            return self._commander
    
    def set_commander(self, card: MTGCard) -> bool:
        """
        Set a card as the commander.
        
        Args:
            card: The card to set as commander
            
        Returns:
            bool: True if commander was set successfully, False otherwise
        """
        if card is None:
            return False
            
        with self._lock:
            # Validate commander eligibility
            if self._can_be_commander(card):
                self._commander = card
                return True
            return False
    
    # Private helper methods
    
    def _is_legendary(self, card: MTGCard) -> bool:
        """Check if a card is legendary."""
        return 'legendary' in card.type.lower()
    
    def _can_be_commander(self, card: MTGCard) -> bool:
        """Check if a card can be a commander."""
        card_type = card.type.lower()
        return ('legendary' in card_type and 'creature' in card_type) or \
               ('planeswalker' in card_type and 'can be your commander' in card.text.lower())
    
    def _validate_singleton_rule(self) -> bool:
        """Validate singleton rule (no duplicates except basic lands)."""
        card_counts = Counter(card.name.lower() for card in self.deck.cards)
        
        basic_lands = {'plains', 'island', 'swamp', 'mountain', 'forest', 'wastes'}
        
        for card_name, count in card_counts.items():
            if count > 1 and card_name not in basic_lands:
                return False
        return True
    
    def _validate_color_identity(self) -> bool:
        """Validate color identity matches commander."""
        if self._commander is None:
            return True
            
        commander_colors = self._extract_colors_from_cost(self._commander.cost)
        
        for card in self.deck.cards:
            card_colors = self._extract_colors_from_cost(card.cost)
            if not set(card_colors).issubset(set(commander_colors)):
                return False
        return True
    
    def _calculate_cmc(self, card: MTGCard) -> int:
        """Calculate converted mana cost of a card."""
        if not card.cost or card.is_land():
            return 0
            
        cmc = 0
        cost = card.cost.replace('{', '').replace('}', '')
        
        i = 0
        while i < len(cost):
            char = cost[i]
            if char.isdigit():
                # Multi-digit numbers
                num_str = ''
                while i < len(cost) and cost[i].isdigit():
                    num_str += cost[i]
                    i += 1
                cmc += int(num_str)
            elif char.upper() in 'WUBRG':
                cmc += 1
                i += 1
            elif char.upper() == 'X':
                # X costs are treated as 0 for curve calculations
                i += 1
            else:
                i += 1
                
        return cmc
    
    def _extract_colors_from_cost(self, cost: str) -> List[str]:
        """Extract color symbols from mana cost."""
        if not cost:
            return []
            
        colors = []
        cost = cost.upper()
        
        for char in cost:
            if char in 'WUBRG' and char not in colors:
                colors.append(char)
                
        return colors
    
    def _get_type_distribution(self) -> Dict[str, int]:
        """Get distribution of card types in deck."""
        type_counts = defaultdict(int)
        
        for card in self.deck.cards:
            # Extract primary type (before any subtypes or supertypes)
            card_type = card.type.lower()
            if '—' in card_type:
                card_type = card_type.split('—')[0].strip()
            if '-' in card_type:
                card_type = card_type.split('-')[0].strip()
                
            # Handle compound types
            types = card_type.split()
            primary_type = None
            
            # Prioritize main types
            type_priority = ['creature', 'instant', 'sorcery', 'artifact', 'enchantment', 'planeswalker', 'land']
            for ptype in type_priority:
                if ptype in types:
                    primary_type = ptype.title()
                    break
            
            if primary_type:
                type_counts[primary_type] += 1
            elif types:
                type_counts[types[-1].title()] += 1
                
        return dict(type_counts)
    
    def _get_rarity_distribution(self) -> Dict[str, int]:
        """Get distribution of card rarities in deck."""
        rarity_counts = defaultdict(int)
        
        for card in self.deck.cards:
            rarity_counts[card.rarity.title()] += 1
            
        return dict(rarity_counts)
    
    def _calculate_average_cmc(self) -> float:
        """Calculate average converted mana cost of non-land cards."""
        nonland_cards = [card for card in self.deck.cards if not card.is_land()]
        
        if not nonland_cards:
            return 0.0
            
        total_cmc = sum(self._calculate_cmc(card) for card in nonland_cards)
        return round(total_cmc / len(nonland_cards), 2)
    
    def _export_as_text(self) -> str:
        """Export deck as plain text format."""
        lines = []
        
        if self._commander:
            lines.append(f"Commander: {self._commander.name}")
            lines.append("")
        
        lines.append("Deck:")
        
        # Group cards by name and count
        card_counts = Counter(card.name for card in self.deck.cards)
        for card_name in sorted(card_counts.keys()):
            count = card_counts[card_name]
            lines.append(f"{count} {card_name}")
        
        if self.sideboard.cards:
            lines.append("")
            lines.append("Sideboard:")
            sideboard_counts = Counter(card.name for card in self.sideboard.cards)
            for card_name in sorted(sideboard_counts.keys()):
                count = sideboard_counts[card_name]
                lines.append(f"{count} {card_name}")
        
        return "\n".join(lines)
    
    def _export_as_json(self) -> str:
        """Export deck as JSON format."""
        deck_data = {
            'commander': self._commander.name if self._commander else None,
            'deck': self.deck.to_dict(),
            'sideboard': self.sideboard.to_dict(),
            'statistics': self.get_deck_statistics()
        }
        return json.dumps(deck_data, indent=2)
    
    def _export_as_arena(self) -> str:
        """Export deck in MTG Arena format."""
        lines = []
        
        if self._commander:
            lines.append(f"Commander")
            lines.append(f"1 {self._commander.name}")
            lines.append("")
        
        lines.append("Deck")
        card_counts = Counter(card.name for card in self.deck.cards)
        for card_name in sorted(card_counts.keys()):
            count = card_counts[card_name]
            lines.append(f"{count} {card_name}")
        
        if self.sideboard.cards:
            lines.append("")
            lines.append("Sideboard")
            sideboard_counts = Counter(card.name for card in self.sideboard.cards)
            for card_name in sorted(sideboard_counts.keys()):
                count = sideboard_counts[card_name]
                lines.append(f"{count} {card_name}")
        
        return "\n".join(lines)
    
    def _import_from_json(self, data: str) -> bool:
        """Import deck from JSON format."""
        try:
            deck_data = json.loads(data)
            
            # Clear current deck
            self.clear_deck()
            
            # Import commander
            if deck_data.get('commander'):
                # This would need actual card lookup functionality
                # For now, just store the name
                pass
            
            # Import deck
            if 'deck' in deck_data:
                self.deck = CardCollection.from_dict(deck_data['deck'])
            
            # Import sideboard
            if 'sideboard' in deck_data:
                self.sideboard = CardCollection.from_dict(deck_data['sideboard'])
            
            return True
        except (json.JSONDecodeError, KeyError, ValueError):
            return False
    
    def _import_from_text(self, data: str) -> bool:
        """Import deck from text format."""
        # This would require card database lookup functionality
        # Placeholder implementation
        return False
    
    def _import_from_arena(self, data: str) -> bool:
        """Import deck from MTG Arena format."""
        # This would require card database lookup functionality
        # Placeholder implementation
        return False