"""
Card Collection Domain Model

This module contains the CardCollection class for managing collections of MTG cards,
including decks and sideboards with validation and thread-safe operations.
"""

from typing import Optional, List, Dict, Any
import threading
from .mtg_card import MTGCard


class CardCollection:
    """Collection of cards (deck or sideboard) with size limits and card count management."""
    
    def __init__(self, max_size: Optional[int] = None):
        """
        Initialize a new card collection.
        
        Args:
            max_size: Maximum number of cards allowed in this collection (None for unlimited)
        """
        self.cards: List[MTGCard] = []
        self.max_size = max_size
        self._card_counts: Dict[str, int] = {}
        self._lock = threading.RLock()  # Re-entrant lock for thread safety
        
    def add(self, card: MTGCard, quantity: int = 1) -> bool:
        """
        Add card to collection with quantity validation.
        
        Args:
            card: The MTGCard to add
            quantity: Number of copies to add (default: 1)
            
        Returns:
            bool: True if cards were added successfully, False if limits exceeded
        """
        if quantity <= 0:
            return False
            
        with self._lock:
            # Check size limit
            if self.max_size is not None and (len(self.cards) + quantity) > self.max_size:
                return False
                
            # Add cards to collection
            for _ in range(quantity):
                self.cards.append(card)
                
            # Update card counts
            card_name = card.name.lower()
            self._card_counts[card_name] = self._card_counts.get(card_name, 0) + quantity
            
            return True
    
    def remove(self, card_id: str) -> bool:
        """
        Remove card from collection by card ID.
        
        Args:
            card_id: The ID of the card to remove (as string)
            
        Returns:
            bool: True if card was removed, False if not found
        """
        with self._lock:
            try:
                card_id_int = int(card_id)
            except ValueError:
                return False
                
            # Find and remove first matching card
            for i, card in enumerate(self.cards):
                if card.id == card_id_int:
                    removed_card = self.cards.pop(i)
                    
                    # Update card counts
                    card_name = removed_card.name.lower()
                    if card_name in self._card_counts:
                        self._card_counts[card_name] -= 1
                        if self._card_counts[card_name] <= 0:
                            del self._card_counts[card_name]
                    
                    return True
            
            return False
    
    def get_card_count(self, card_name: str) -> int:
        """
        Get the number of copies of a specific card in the collection.
        
        Args:
            card_name: Name of the card to count
            
        Returns:
            int: Number of copies of the card
        """
        with self._lock:
            return self._card_counts.get(card_name.lower(), 0)
    
    def clear(self) -> None:
        """Remove all cards from the collection."""
        with self._lock:
            self.cards.clear()
            self._card_counts.clear()
    
    def contains(self, card_name: str) -> bool:
        """
        Check if collection contains any copies of a specific card.
        
        Args:
            card_name: Name of the card to check
            
        Returns:
            bool: True if collection contains the card, False otherwise
        """
        with self._lock:
            return card_name.lower() in self._card_counts
    
    def get_unique_cards(self) -> List[MTGCard]:
        """
        Get list of unique cards in the collection (one instance per card name).
        
        Returns:
            List[MTGCard]: List of unique cards
        """
        with self._lock:
            unique_cards = {}
            for card in self.cards:
                card_name = card.name.lower()
                if card_name not in unique_cards:
                    unique_cards[card_name] = card
            
            return list(unique_cards.values())
    
    @property
    def total_cards(self) -> int:
        """
        Get total number of cards in the collection.
        
        Returns:
            int: Total number of cards
        """
        with self._lock:
            return len(self.cards)
    
    @property
    def unique_card_count(self) -> int:
        """
        Get number of unique cards in the collection.
        
        Returns:
            int: Number of unique cards
        """
        with self._lock:
            return len(self._card_counts)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize collection to dictionary.
        
        Returns:
            Dict: Serialized collection data
        """
        with self._lock:
            # Group cards by name for efficient serialization
            card_data = {}
            for card in self.cards:
                card_name = card.name
                if card_name not in card_data:
                    card_data[card_name] = {
                        'card': {
                            'id': card.id,
                            'name': card.name,
                            'type': card.type,
                            'cost': card.cost,
                            'text': card.text,
                            'power': card.power,
                            'toughness': card.toughness,
                            'flavor': card.flavor,
                            'rarity': card.rarity,
                            'art': card.art,
                            'set': card.set,
                            'status': card.status,
                            'image_path': card.image_path,
                            'card_path': card.card_path,
                            'generated_at': card.generated_at,
                            'generation_status': card.generation_status,
                            'custom_image_path': card.custom_image_path,
                        },
                        'quantity': 0
                    }
                card_data[card_name]['quantity'] += 1
            
            return {
                'max_size': self.max_size,
                'total_cards': self.total_cards,
                'unique_card_count': self.unique_card_count,
                'cards': list(card_data.values())
            }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CardCollection':
        """
        Deserialize collection from dictionary.
        
        Args:
            data: Dictionary containing collection data
            
        Returns:
            CardCollection: New instance with loaded data
        """
        collection = cls(max_size=data.get('max_size'))
        
        if 'cards' in data:
            for card_entry in data['cards']:
                card_data = card_entry['card']
                quantity = card_entry.get('quantity', 1)
                
                # Create MTGCard instance
                card = MTGCard(
                    id=card_data['id'],
                    name=card_data['name'],
                    type=card_data['type'],
                    cost=card_data.get('cost', ''),
                    text=card_data.get('text', ''),
                    power=card_data.get('power'),
                    toughness=card_data.get('toughness'),
                    flavor=card_data.get('flavor', ''),
                    rarity=card_data.get('rarity', 'common'),
                    art=card_data.get('art', ''),
                    set=card_data.get('set', 'CMD'),
                    status=card_data.get('status', 'pending'),
                    image_path=card_data.get('image_path'),
                    card_path=card_data.get('card_path'),
                    generated_at=card_data.get('generated_at'),
                    generation_status=card_data.get('generation_status', 'pending'),
                    custom_image_path=card_data.get('custom_image_path'),
                )
                
                # Add card with specified quantity
                collection.add(card, quantity)
        
        return collection
    
    def __len__(self) -> int:
        """Return total number of cards in collection."""
        return self.total_cards
    
    def __bool__(self) -> bool:
        """Return True if collection has any cards."""
        return self.total_cards > 0
    
    def __repr__(self) -> str:
        """Return string representation of collection."""
        return f"CardCollection(total_cards={self.total_cards}, unique_cards={self.unique_card_count}, max_size={self.max_size})"