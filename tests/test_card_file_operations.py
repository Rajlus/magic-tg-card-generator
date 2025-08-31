#!/usr/bin/env python3
"""
Test suite for CardFileOperations class functionality.
This tests the extracted file I/O operations.
"""

import tempfile
import yaml
import csv
from pathlib import Path
from unittest.mock import Mock, MagicMock

import pytest
from PyQt6.QtWidgets import QWidget

# Import the module we're testing
import sys
sys.path.append('src')
from managers.card_file_operations import CardFileOperations

# Import the main MTGCard class
from mtg_deck_builder import MTGCard


class TestCardFileOperations:
    """Test the CardFileOperations class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create a mock parent widget
        self.parent_widget = Mock(spec=QWidget)
        
        # Create a mock logger
        self.logger = Mock()
        
        # Create a mock dialog provider
        self.dialog_provider = Mock()
        
        # Create the CardFileOperations instance
        self.file_ops = CardFileOperations(
            parent_widget=self.parent_widget,
            logger=self.logger,
            dialog_provider=self.dialog_provider
        )
        
        # Create test cards
        self.test_cards = [
            MTGCard(
                id=1,
                name="Lightning Bolt",
                type="Instant",
                cost="{R}",
                text="Deal 3 damage to any target.",
                rarity="common"
            ),
            MTGCard(
                id=2,
                name="Black Lotus",
                type="Artifact",
                cost="{0}",
                text="Add three mana of any one color.",
                rarity="rare"
            )
        ]
    
    def test_ensure_safe_filename(self):
        """Test filename sanitization."""
        # Test basic functionality
        assert self.file_ops._ensure_safe_filename("Lightning Bolt") == "Lightning_Bolt"
        
        # Test with problematic characters
        unsafe_name = 'Card/with\\bad:chars*?"|<>'
        safe_name = self.file_ops._ensure_safe_filename(unsafe_name)
        assert "/" not in safe_name
        assert "\\" not in safe_name
        assert ":" not in safe_name
        
        # Test empty string
        assert self.file_ops._ensure_safe_filename("") == "unnamed_card"
        assert self.file_ops._ensure_safe_filename(".hidden") == "unnamed_card"
    
    def test_mtg_card_conversion(self):
        """Test MTGCard to dict and back conversion."""
        card = self.test_cards[0]
        
        # Convert to dict
        card_dict = self.file_ops._mtg_card_to_dict(card)
        
        # Verify all fields are present
        assert card_dict["id"] == 1
        assert card_dict["name"] == "Lightning Bolt"
        assert card_dict["type"] == "Instant"
        assert card_dict["cost"] == "{R}"
        assert card_dict["text"] == "Deal 3 damage to any target."
        assert card_dict["rarity"] == "common"
        
        # Convert back to MTGCard
        converted_card = self.file_ops._dict_to_mtg_card(card_dict, card_dict["id"])
        
        # Verify fields match
        assert converted_card.id == card.id
        assert converted_card.name == card.name
        assert converted_card.type == card.type
        assert converted_card.cost == card.cost
        assert converted_card.text == card.text
        assert converted_card.rarity == card.rarity
    
    def test_deck_directory_management(self):
        """Test deck directory structure creation and retrieval."""
        deck_name = "test_deck"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Override the saved decks directory for testing
            old_dir = self.file_ops.SAVED_DECKS_DIR
            self.file_ops.SAVED_DECKS_DIR = temp_dir
            
            try:
                # Test directory creation
                deck_dir = self.file_ops._create_deck_directory_structure(deck_name)
                
                # Verify main directory exists
                assert deck_dir.exists()
                assert deck_dir.name == deck_name
                
                # Verify subdirectories exist
                assert (deck_dir / self.file_ops.RENDERED_CARDS_SUBDIR).exists()
                assert (deck_dir / self.file_ops.ARTWORK_SUBDIR).exists()
                assert (deck_dir / self.file_ops.BACKUPS_SUBDIR).exists()
                
                # Test directory getters
                self.file_ops.current_deck_name = deck_name
                
                assert self.file_ops.get_deck_directory() == deck_dir
                assert self.file_ops.get_rendered_cards_directory() == deck_dir / self.file_ops.RENDERED_CARDS_SUBDIR
                assert self.file_ops.get_artwork_directory() == deck_dir / self.file_ops.ARTWORK_SUBDIR
                
            finally:
                self.file_ops.SAVED_DECKS_DIR = old_dir
    
    def test_yaml_save_and_load(self):
        """Test saving and loading YAML decks."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Override the saved decks directory for testing
            old_dir = self.file_ops.SAVED_DECKS_DIR
            self.file_ops.SAVED_DECKS_DIR = temp_dir
            
            try:
                # Test saving
                success = self.file_ops.save_deck_to_yaml(self.test_cards, "test_deck")
                assert success
                
                # Verify file exists
                yaml_file = Path(temp_dir) / "test_deck" / "test_deck.yaml"
                assert yaml_file.exists()
                
                # Test loading
                loaded_cards = self.file_ops.load_deck_from_file(str(yaml_file))
                assert loaded_cards is not None
                assert len(loaded_cards) == 2
                
                # Verify cards match
                assert loaded_cards[0].name == "Lightning Bolt"
                assert loaded_cards[1].name == "Black Lotus"
                
            finally:
                self.file_ops.SAVED_DECKS_DIR = old_dir
    
    def test_csv_export_and_import(self):
        """Test CSV export and import functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_file = Path(temp_dir) / "test_deck.csv"
            
            # Test export
            success = self.file_ops.export_csv_to_file(self.test_cards, str(csv_file))
            assert success
            assert csv_file.exists()
            
            # Test import
            imported_cards = self.file_ops.import_csv_from_file(str(csv_file))
            assert imported_cards is not None
            assert len(imported_cards) == 2
            
            # Verify card data
            assert imported_cards[0].name == "Lightning Bolt"
            assert imported_cards[0].type == "Instant"
            assert imported_cards[1].name == "Black Lotus"
            assert imported_cards[1].type == "Artifact"
    
    def test_file_validation(self):
        """Test file validation methods."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create valid YAML file
            yaml_file = Path(temp_dir) / "valid.yaml"
            with open(yaml_file, 'w') as f:
                yaml.dump({"cards": []}, f)
            
            # Create valid CSV file
            csv_file = Path(temp_dir) / "valid.csv"
            with open(csv_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.file_ops.CSV_FIELDNAMES, delimiter=";")
                writer.writeheader()
            
            # Create invalid files
            invalid_yaml = Path(temp_dir) / "invalid.yaml"
            with open(invalid_yaml, 'w') as f:
                f.write("invalid: yaml: content: [")
            
            # Test validation
            valid, error = self.file_ops.validate_yaml_file(str(yaml_file))
            assert valid
            assert error is None
            
            valid, error = self.file_ops.validate_yaml_file(str(invalid_yaml))
            assert not valid
            assert error is not None
            
            valid, error = self.file_ops.validate_csv_file(str(csv_file))
            assert valid
            assert error is None
            
            # Test non-existent file
            valid, error = self.file_ops.validate_yaml_file("nonexistent.yaml")
            assert not valid
            assert "File not found" in error
    
    def test_rendered_files_sync(self):
        """Test synchronization with rendered files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up directory structure
            old_dir = self.file_ops.SAVED_DECKS_DIR
            self.file_ops.SAVED_DECKS_DIR = temp_dir
            self.file_ops.current_deck_name = "test_deck"
            
            try:
                # Create deck directory structure
                self.file_ops.ensure_deck_directories()
                
                # Create some "rendered" files
                rendered_dir = self.file_ops.get_rendered_cards_directory()
                (rendered_dir / "Lightning_Bolt.png").touch()
                
                # Test file detection
                rendered_files = self.file_ops.get_rendered_card_files()
                assert "Lightning_Bolt" in rendered_files
                assert "Black_Lotus" not in rendered_files
                
                # Test status sync
                test_cards = self.test_cards.copy()
                for card in test_cards:
                    card.status = "pending"
                
                updated_count = self.file_ops.sync_card_status_with_files(test_cards)
                assert updated_count == 1  # Only Lightning Bolt should be updated
                assert test_cards[0].status == "completed"
                assert test_cards[1].status == "pending"
                
            finally:
                self.file_ops.SAVED_DECKS_DIR = old_dir


if __name__ == "__main__":
    # Run a simple test
    test_instance = TestCardFileOperations()
    test_instance.setup_method()
    
    print("Testing filename sanitization...")
    test_instance.test_ensure_safe_filename()
    print("✓ Filename sanitization works")
    
    print("Testing MTGCard conversion...")
    test_instance.test_mtg_card_conversion()
    print("✓ MTGCard conversion works")
    
    print("Testing directory management...")
    test_instance.test_deck_directory_management()
    print("✓ Directory management works")
    
    print("Testing YAML save/load...")
    test_instance.test_yaml_save_and_load()
    print("✓ YAML save/load works")
    
    print("Testing CSV import/export...")
    test_instance.test_csv_export_and_import()
    print("✓ CSV import/export works")
    
    print("Testing file validation...")
    test_instance.test_file_validation()
    print("✓ File validation works")
    
    print("Testing rendered files sync...")
    test_instance.test_rendered_files_sync()
    print("✓ Rendered files sync works")
    
    print("\n🎉 All tests passed! CardFileOperations extraction is complete.")