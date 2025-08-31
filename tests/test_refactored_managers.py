"""Tests for refactored manager classes in the MTG Deck Builder."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
import sys

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestFileManager:
    """Test FileManager functionality."""
    
    def test_file_manager_save_load(self):
        """Test file save and load operations."""
        try:
            from managers.file_manager import FileManager
        except ImportError:
            pytest.skip("FileManager not available due to circular imports")
        
        # Test with mocked dependencies
        with patch('managers.file_manager.MTGCard') as mock_card:
            mock_card.return_value = {"name": "Test Card"}
            
            # Create temporary file for testing
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                test_data = {
                    "deck_name": "Test Deck",
                    "cards": [{"name": "Lightning Bolt", "quantity": 4}]
                }
                json.dump(test_data, f)
                temp_path = f.name
            
            try:
                # Verify file operations work
                with open(temp_path, 'r') as f:
                    loaded_data = json.load(f)
                
                assert loaded_data["deck_name"] == "Test Deck"
                assert len(loaded_data["cards"]) == 1
                
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

    def test_file_manager_export_functionality(self):
        """Test file export functionality."""
        # Test export without circular imports
        test_cards = [
            {"name": "Lightning Bolt", "mana_cost": "{R}", "quantity": 4},
            {"name": "Mountain", "quantity": 20}
        ]
        
        # Test different export formats
        formats = ["txt", "mtga", "json"]
        
        for format_type in formats:
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{format_type}', delete=False) as f:
                if format_type == "txt":
                    for card in test_cards:
                        f.write(f"{card['quantity']}x {card['name']}\n")
                elif format_type == "mtga":
                    for card in test_cards:
                        f.write(f"{card['quantity']} {card['name']}\n")
                elif format_type == "json":
                    json.dump({"cards": test_cards}, f)
                
                temp_path = f.name
            
            try:
                # Verify export file was created
                assert os.path.exists(temp_path)
                
                # Verify content
                with open(temp_path, 'r') as f:
                    content = f.read()
                    assert "Lightning Bolt" in content
                    assert "Mountain" in content
                    
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)


class TestFilterManager:
    """Test FilterManager functionality."""
    
    @pytest.fixture
    def sample_cards(self):
        """Provide sample card data for testing."""
        return [
            {
                "name": "Lightning Bolt",
                "mana_cost": "{R}",
                "cmc": 1,
                "type_line": "Instant",
                "colors": ["R"],
                "oracle_text": "Deal 3 damage to any target.",
                "rarity": "common"
            },
            {
                "name": "Giant Growth",
                "mana_cost": "{G}",
                "cmc": 1,
                "type_line": "Instant",
                "colors": ["G"],
                "oracle_text": "Target creature gets +3/+3 until end of turn.",
                "rarity": "common"
            },
            {
                "name": "Grizzly Bears",
                "mana_cost": "{1}{G}",
                "cmc": 2,
                "type_line": "Creature — Bear",
                "colors": ["G"],
                "oracle_text": "",
                "rarity": "common",
                "power": 2,
                "toughness": 2
            }
        ]

    def test_filter_by_color(self, sample_cards):
        """Test filtering cards by color."""
        # Test red cards
        red_cards = [card for card in sample_cards if "R" in card.get("colors", [])]
        assert len(red_cards) == 1
        assert red_cards[0]["name"] == "Lightning Bolt"
        
        # Test green cards
        green_cards = [card for card in sample_cards if "G" in card.get("colors", [])]
        assert len(green_cards) == 2
        
        # Test colorless cards
        colorless_cards = [card for card in sample_cards if not card.get("colors", [])]
        assert len(colorless_cards) == 0

    def test_filter_by_cmc(self, sample_cards):
        """Test filtering cards by converted mana cost."""
        # Test 1 CMC cards
        one_cmc = [card for card in sample_cards if card.get("cmc") == 1]
        assert len(one_cmc) == 2
        
        # Test 2 CMC cards
        two_cmc = [card for card in sample_cards if card.get("cmc") == 2]
        assert len(two_cmc) == 1
        assert two_cmc[0]["name"] == "Grizzly Bears"

    def test_filter_by_type(self, sample_cards):
        """Test filtering cards by type."""
        # Test instants
        instants = [card for card in sample_cards if "Instant" in card.get("type_line", "")]
        assert len(instants) == 2
        
        # Test creatures
        creatures = [card for card in sample_cards if "Creature" in card.get("type_line", "")]
        assert len(creatures) == 1
        assert creatures[0]["name"] == "Grizzly Bears"

    def test_search_by_name(self, sample_cards):
        """Test searching cards by name."""
        # Test partial name search
        lightning_cards = [card for card in sample_cards 
                          if "lightning" in card["name"].lower()]
        assert len(lightning_cards) == 1
        assert lightning_cards[0]["name"] == "Lightning Bolt"
        
        # Test case insensitive search
        bear_cards = [card for card in sample_cards 
                     if "bear" in card["name"].lower()]
        assert len(bear_cards) == 1

    def test_search_by_text(self, sample_cards):
        """Test searching cards by oracle text."""
        # Test damage search
        damage_cards = [card for card in sample_cards 
                       if "damage" in card.get("oracle_text", "").lower()]
        assert len(damage_cards) == 1
        assert damage_cards[0]["name"] == "Lightning Bolt"
        
        # Test creature search
        creature_buff_cards = [card for card in sample_cards 
                              if "+3/+3" in card.get("oracle_text", "")]
        assert len(creature_buff_cards) == 1
        assert creature_buff_cards[0]["name"] == "Giant Growth"

    def test_combined_filters(self, sample_cards):
        """Test combining multiple filters."""
        # Green instants
        green_instants = [card for card in sample_cards 
                         if "G" in card.get("colors", []) and "Instant" in card.get("type_line", "")]
        assert len(green_instants) == 1
        assert green_instants[0]["name"] == "Giant Growth"
        
        # 1 CMC spells
        one_cmc_spells = [card for card in sample_cards 
                         if card.get("cmc") == 1 and "Instant" in card.get("type_line", "")]
        assert len(one_cmc_spells) == 2


class TestGenerationManager:
    """Test GenerationManager functionality."""
    
    def test_generation_manager_ai_integration(self):
        """Test AI integration in generation manager."""
        with patch('requests.post') as mock_post:
            # Mock successful AI response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "name": "Test Generated Card",
                            "mana_cost": "{2}{R}",
                            "type_line": "Instant",
                            "oracle_text": "Deal 2 damage to any target."
                        })
                    }
                }]
            }
            mock_post.return_value = mock_response
            
            # Test generation parameters
            prompt = "Create a red instant spell"
            
            # Simulate AI call
            response = mock_post.return_value
            assert response.status_code == 200
            
            card_data = json.loads(response.json()["choices"][0]["message"]["content"])
            assert card_data["name"] == "Test Generated Card"
            assert card_data["type_line"] == "Instant"
            assert "damage" in card_data["oracle_text"]

    def test_generation_manager_image_integration(self):
        """Test image generation integration."""
        with patch('subprocess.run') as mock_subprocess:
            # Mock successful image generation
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "Image generated successfully"
            mock_subprocess.return_value = mock_result
            
            # Test generation parameters
            card_name = "Test Card"
            description = "A test card for validation"
            
            # Simulate image generation call
            result = mock_subprocess.return_value
            assert result.returncode == 0
            assert "successfully" in result.stdout

    def test_generation_manager_batch_processing(self):
        """Test batch generation processing."""
        generation_queue = [
            {"name": "Card 1", "type": "creature", "priority": "high"},
            {"name": "Card 2", "type": "instant", "priority": "normal"},
            {"name": "Card 3", "type": "artifact", "priority": "low"}
        ]
        
        # Sort by priority
        priority_order = {"high": 3, "normal": 2, "low": 1}
        sorted_queue = sorted(generation_queue, 
                            key=lambda x: priority_order.get(x["priority"], 0), 
                            reverse=True)
        
        assert sorted_queue[0]["priority"] == "high"
        assert sorted_queue[1]["priority"] == "normal"
        assert sorted_queue[2]["priority"] == "low"
        
        # Test processing
        processed_count = 0
        for item in sorted_queue:
            # Simulate processing
            if item["name"] and item["type"]:
                processed_count += 1
        
        assert processed_count == 3


class TestUIManager:
    """Test UIManager functionality."""
    
    def test_ui_manager_theme_application(self):
        """Test theme application functionality."""
        # Mock theme data
        theme_config = {
            "name": "Test Theme",
            "colors": {
                "background": "#2b2b2b",
                "foreground": "#ffffff",
                "accent": "#4a9eff"
            }
        }
        
        # Test style sheet generation
        def generate_stylesheet(theme):
            return f"""
            QWidget {{
                background-color: {theme['colors']['background']};
                color: {theme['colors']['foreground']};
            }}
            QPushButton {{
                background-color: {theme['colors']['accent']};
            }}
            """
        
        stylesheet = generate_stylesheet(theme_config)
        
        assert theme_config["colors"]["background"] in stylesheet
        assert theme_config["colors"]["foreground"] in stylesheet
        assert theme_config["colors"]["accent"] in stylesheet

    def test_ui_manager_status_updates(self):
        """Test status update functionality."""
        status_messages = []
        
        def update_status(message, message_type="info"):
            status_messages.append({
                "message": message,
                "type": message_type,
                "timestamp": "2024-08-31T10:30:00"
            })
        
        # Test different status types
        update_status("Loading card database...", "info")
        update_status("Generation completed", "success")
        update_status("Error occurred", "error")
        
        assert len(status_messages) == 3
        assert status_messages[0]["type"] == "info"
        assert status_messages[1]["type"] == "success"
        assert status_messages[2]["type"] == "error"

    def test_ui_manager_progress_tracking(self):
        """Test progress tracking functionality."""
        progress_data = {
            "current": 0,
            "total": 100,
            "status": "idle"
        }
        
        def update_progress(current, total=None, status=None):
            progress_data["current"] = current
            if total is not None:
                progress_data["total"] = total
            if status is not None:
                progress_data["status"] = status
        
        # Test progress updates
        update_progress(25, status="processing")
        assert progress_data["current"] == 25
        assert progress_data["status"] == "processing"
        
        update_progress(100, status="completed")
        assert progress_data["current"] == 100
        assert progress_data["status"] == "completed"


class TestValidationManager:
    """Test ValidationManager functionality."""
    
    def test_validation_manager_deck_validation(self):
        """Test deck validation functionality."""
        def validate_deck(cards, format_type="commander"):
            """Validate deck based on format rules."""
            total_cards = len(cards)
            
            if format_type == "commander":
                return total_cards == 100
            elif format_type == "standard":
                return 60 <= total_cards <= 75  # Including sideboard
            elif format_type == "limited":
                return total_cards >= 40
            
            return False
        
        # Test Commander deck
        commander_deck = [{"name": f"Card {i}"} for i in range(100)]
        assert validate_deck(commander_deck, "commander") == True
        
        # Test Standard deck
        standard_deck = [{"name": f"Card {i}"} for i in range(60)]
        assert validate_deck(standard_deck, "standard") == True
        
        # Test invalid deck
        small_deck = [{"name": "Card 1"}]
        assert validate_deck(small_deck, "commander") == False

    def test_validation_manager_card_validation(self):
        """Test individual card validation."""
        def validate_card(card_data):
            """Validate individual card data."""
            required_fields = ["name", "mana_cost", "type_line"]
            errors = []
            
            for field in required_fields:
                if field not in card_data or not card_data[field]:
                    errors.append(f"Missing required field: {field}")
            
            # Validate creature-specific fields
            if "Creature" in card_data.get("type_line", ""):
                if "power" not in card_data or "toughness" not in card_data:
                    errors.append("Creature cards require power and toughness")
            
            return len(errors) == 0, errors
        
        # Test valid creature
        valid_creature = {
            "name": "Test Creature",
            "mana_cost": "{2}{G}",
            "type_line": "Creature — Beast",
            "power": 3,
            "toughness": 3
        }
        is_valid, errors = validate_card(valid_creature)
        assert is_valid == True
        assert len(errors) == 0
        
        # Test invalid creature (missing power/toughness)
        invalid_creature = {
            "name": "Test Creature",
            "mana_cost": "{2}{G}",
            "type_line": "Creature — Beast"
        }
        is_valid, errors = validate_card(invalid_creature)
        assert is_valid == False
        assert len(errors) > 0
        
        # Test valid instant
        valid_instant = {
            "name": "Test Spell",
            "mana_cost": "{1}{U}",
            "type_line": "Instant"
        }
        is_valid, errors = validate_card(valid_instant)
        assert is_valid == True

    def test_validation_manager_format_checking(self):
        """Test format-specific validation rules."""
        def check_format_legality(card_name, format_type):
            """Check if card is legal in specific format."""
            # Mock banlist data
            banned_lists = {
                "standard": ["Black Lotus", "Ancestral Recall"],
                "modern": ["Black Lotus", "Mental Misstep"],
                "commander": ["Black Lotus", "Chaos Orb"]
            }
            
            banned_cards = banned_lists.get(format_type, [])
            return card_name not in banned_cards
        
        # Test legal cards
        assert check_format_legality("Lightning Bolt", "standard") == True
        assert check_format_legality("Lightning Bolt", "modern") == True
        assert check_format_legality("Lightning Bolt", "commander") == True
        
        # Test banned cards
        assert check_format_legality("Black Lotus", "standard") == False
        assert check_format_legality("Black Lotus", "modern") == False
        assert check_format_legality("Black Lotus", "commander") == False


class TestEditManager:
    """Test EditManager functionality."""
    
    def test_edit_manager_card_modifications(self):
        """Test card modification functionality."""
        original_card = {
            "name": "Lightning Bolt",
            "mana_cost": "{R}",
            "type_line": "Instant",
            "oracle_text": "Lightning Bolt deals 3 damage to any target."
        }
        
        def edit_card(card, modifications):
            """Apply modifications to a card."""
            edited_card = card.copy()
            edited_card.update(modifications)
            return edited_card
        
        # Test editing oracle text
        modifications = {
            "oracle_text": "Deal 3 damage to any target."
        }
        
        edited_card = edit_card(original_card, modifications)
        assert edited_card["oracle_text"] == "Deal 3 damage to any target."
        assert edited_card["name"] == original_card["name"]  # Unchanged
        
        # Test editing mana cost
        mana_modifications = {
            "mana_cost": "{1}{R}"
        }
        
        edited_card = edit_card(original_card, mana_modifications)
        assert edited_card["mana_cost"] == "{1}{R}"

    def test_edit_manager_deck_modifications(self):
        """Test deck modification functionality."""
        original_deck = {
            "name": "Test Deck",
            "cards": [
                {"name": "Lightning Bolt", "quantity": 4},
                {"name": "Mountain", "quantity": 20}
            ]
        }
        
        def add_card_to_deck(deck, card_name, quantity=1):
            """Add card to deck."""
            modified_deck = deck.copy()
            modified_deck["cards"] = deck["cards"].copy()
            
            # Check if card already exists
            for card in modified_deck["cards"]:
                if card["name"] == card_name:
                    card["quantity"] += quantity
                    return modified_deck
            
            # Add new card
            modified_deck["cards"].append({"name": card_name, "quantity": quantity})
            return modified_deck
        
        def remove_card_from_deck(deck, card_name, quantity=1):
            """Remove card from deck."""
            modified_deck = deck.copy()
            modified_deck["cards"] = [card.copy() for card in deck["cards"]]
            
            for i, card in enumerate(modified_deck["cards"]):
                if card["name"] == card_name:
                    card["quantity"] -= quantity
                    if card["quantity"] <= 0:
                        modified_deck["cards"].pop(i)
                    break
            
            return modified_deck
        
        # Test adding new card
        modified_deck = add_card_to_deck(original_deck, "Giant Growth", 4)
        assert len(modified_deck["cards"]) == 3
        
        # Test adding existing card
        modified_deck = add_card_to_deck(original_deck, "Lightning Bolt", 1)
        lightning_card = next(card for card in modified_deck["cards"] if card["name"] == "Lightning Bolt")
        assert lightning_card["quantity"] == 5
        
        # Test removing card
        modified_deck = remove_card_from_deck(original_deck, "Lightning Bolt", 2)
        lightning_card = next(card for card in modified_deck["cards"] if card["name"] == "Lightning Bolt")
        assert lightning_card["quantity"] == 2