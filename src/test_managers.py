#!/usr/bin/env python3
"""
test_managers.py
Simple test script to validate the manager classes
"""

import sys
from PyQt6.QtWidgets import QApplication, QWidget, QTableWidget, QComboBox, QLineEdit, QLabel
from CardTableManager import CardTableManager
from src.domain.models import MTGCard
from CardFileOperations import CardFileOperations
from CardGenerationController import CardGenerationController
from CardFilterManager import CardFilterManager
from CardStatusManager import CardStatusManager


def test_table_manager():
    """Test CardTableManager functionality."""
    print("Testing CardTableManager...")
    
    # Create test cards
    test_cards = [
        MTGCard(1, "Lightning Bolt", "Instant", "{R}", "Deal 3 damage to any target.", rarity="common"),
        MTGCard(2, "Serra Angel", "Creature — Angel", "{3}{W}{W}", "Flying, vigilance", 4, 4, rarity="uncommon"),
        MTGCard(3, "Black Lotus", "Artifact", "{0}", "{T}, Sacrifice Black Lotus: Add three mana of any one color.", rarity="mythic")
    ]
    
    # Create table widget and manager
    table = QTableWidget()
    manager = CardTableManager(table)
    
    # Test loading cards
    manager.load_cards(test_cards)
    assert len(manager.get_all_cards()) == 3, "Failed to load cards"
    
    # Test adding a card
    new_card = MTGCard(4, "Counterspell", "Instant", "{U}{U}", "Counter target spell.", rarity="common")
    manager.add_card(new_card)
    assert len(manager.get_all_cards()) == 4, "Failed to add card"
    
    # Test status update
    manager.update_card_status(1, "completed")
    card = manager.get_card_by_row(0)
    assert card.generation_status == "completed", "Failed to update card status"
    
    print("✅ CardTableManager tests passed")


def test_file_operations():
    """Test CardFileOperations functionality."""
    print("Testing CardFileOperations...")
    
    # Create test cards
    test_cards = [
        MTGCard(1, "Lightning Bolt", "Instant", "{R}", "Deal 3 damage to any target.", rarity="common"),
        MTGCard(2, "Serra Angel", "Creature — Angel", "{3}{W}{W}", "Flying, vigilance", 4, 4, rarity="uncommon")
    ]
    
    manager = CardFileOperations()
    
    # Test file validation (for non-existent file)
    assert not manager.validate_deck_file("nonexistent.json"), "Should fail for non-existent file"
    
    # Test auto-save settings
    manager.set_auto_save_enabled(False)
    assert not manager.is_auto_save_enabled(), "Auto-save should be disabled"
    
    manager.set_auto_save_enabled(True)
    assert manager.is_auto_save_enabled(), "Auto-save should be enabled"
    
    print("✅ CardFileOperations tests passed")


def test_generation_controller():
    """Test CardGenerationController functionality."""
    print("Testing CardGenerationController...")
    
    controller = CardGenerationController()
    
    # Test generation statistics
    test_cards = [
        MTGCard(1, "Test Card 1", "Instant", generation_status="pending"),
        MTGCard(2, "Test Card 2", "Creature", generation_status="completed"),
        MTGCard(3, "Test Card 3", "Sorcery", generation_status="failed")
    ]
    
    stats = controller.get_generation_statistics(test_cards)
    assert stats["total"] == 3, "Wrong total count"
    assert stats["pending"] == 1, "Wrong pending count"
    assert stats["completed"] == 1, "Wrong completed count"
    assert stats["failed"] == 1, "Wrong failed count"
    
    # Test validation
    invalid_cards = [MTGCard(1, "", "")]  # Missing name and type
    issues = controller.validate_cards_for_generation(invalid_cards)
    assert len(issues) > 0, "Should detect validation issues"
    
    print("✅ CardGenerationController tests passed")


def test_filter_manager():
    """Test CardFilterManager functionality."""
    print("Testing CardFilterManager...")
    
    # Create test cards
    test_cards = [
        MTGCard(1, "Lightning Bolt", "Instant", "{R}", "Deal 3 damage", generation_status="completed"),
        MTGCard(2, "Serra Angel", "Creature — Angel", "{3}{W}{W}", "Flying", 4, 4, generation_status="pending"),
        MTGCard(3, "Counterspell", "Instant", "{U}{U}", "Counter target spell", generation_status="completed")
    ]
    
    manager = CardFilterManager()
    manager.set_cards(test_cards)
    
    # Test type filter
    manager.set_type_filter("Instants")
    visible_cards = manager.get_visible_cards()
    assert len(visible_cards) == 2, "Should show 2 instants"
    
    # Test status filter  
    manager.clear_filters()
    manager.set_status_filter("✅ Completed")
    visible_cards = manager.get_visible_cards()
    assert len(visible_cards) == 2, "Should show 2 completed cards"
    
    # Test search filter
    manager.clear_filters()
    manager.set_search_text("Lightning")
    visible_cards = manager.get_visible_cards()
    assert len(visible_cards) == 1, "Should find Lightning Bolt"
    assert visible_cards[0].name == "Lightning Bolt", "Should find correct card"
    
    print("✅ CardFilterManager tests passed")


def test_status_manager():
    """Test CardStatusManager functionality."""
    print("Testing CardStatusManager...")
    
    manager = CardStatusManager()
    
    # Create test cards
    test_cards = [
        MTGCard(1, "Lightning Bolt", "Instant", "{R}", generation_status="pending"),
        MTGCard(2, "Serra Angel", "Creature — Angel", "{3}{W}{W}", generation_status="completed"),
        MTGCard(3, "Black Lotus", "Artifact", "{0}", generation_status="failed")
    ]
    
    manager.set_cards(test_cards)
    
    # Test statistics
    stats = manager.get_generation_statistics()
    assert stats["total"] == 3, "Wrong total count"
    assert stats["pending"] == 1, "Wrong pending count"
    assert stats["completed"] == 1, "Wrong completed count"
    assert stats["failed"] == 1, "Wrong failed count"
    
    # Test status update
    success = manager.update_card_status(1, "completed")
    assert success, "Should successfully update status"
    
    updated_stats = manager.get_generation_statistics()
    assert updated_stats["completed"] == 2, "Should have 2 completed cards now"
    assert updated_stats["pending"] == 0, "Should have 0 pending cards now"
    
    # Test color distribution
    color_dist = manager.get_color_distribution()
    assert "Red" in color_dist, "Should detect red cards"
    assert "Colorless" in color_dist, "Should detect colorless cards"
    
    print("✅ CardStatusManager tests passed")


def main():
    """Run all tests."""
    print("Running manager class tests...\n")
    
    # Initialize QApplication for GUI components
    app = QApplication(sys.argv)
    
    try:
        test_table_manager()
        test_file_operations()
        test_generation_controller()
        test_filter_manager()
        test_status_manager()
        
        print("\n🎉 All tests passed! Manager classes are working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())