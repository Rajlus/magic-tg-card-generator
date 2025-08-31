"""Comprehensive tests for MTG Deck Builder GUI application."""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from PyQt6.QtCore import QThread, QTimer, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mtg_deck_builder import (
    AIWorker,
    CardGeneratorWorker,
    CardManagementTab,
    MTGCard,
    MTGDeckBuilder,
    ThemeConfigTab,
    convert_mana_cost,
    escape_for_shell,
    make_safe_filename,
)


@pytest.fixture
def qapp():
    """Provide a QApplication instance for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # Don't quit the app here as it might be needed for other tests


@pytest.fixture
def sample_mtg_card():
    """Provide a sample MTG card for testing."""
    return MTGCard(
        name="Lightning Bolt",
        mana_cost="{R}",
        cmc=1,
        type_line="Instant",
        colors=["R"],
        color_identity=["R"],
        power=None,
        toughness=None,
        oracle_text="Lightning Bolt deals 3 damage to any target.",
        rarity="common"
    )


class TestHelperFunctions:
    """Test helper utility functions."""
    
    def test_make_safe_filename(self):
        """Test filename sanitization."""
        # Test normal case
        assert make_safe_filename("Lightning Bolt") == "Lightning_Bolt"
        
        # Test special characters
        assert make_safe_filename("Jace/Vryn's") == "Jace_Vryns"
        
        # Test complex case
        assert make_safe_filename("Æther Vial — Test") == "Æther_Vial___Test"
        
        # Test empty string
        assert make_safe_filename("") == ""
        
        # Test with problematic characters
        assert make_safe_filename('Path/To\\File:Name*?<>|"') == "Path_To_File_Name______"

    def test_escape_for_shell(self):
        """Test shell escaping functionality."""
        # Test normal string
        assert escape_for_shell("test") == '"test"'
        
        # Test string with quotes
        assert escape_for_shell('test "quoted"') == '"test \\"quoted\\""'
        
        # Test empty string
        assert escape_for_shell("") == '""'
        
        # Test integer input
        assert escape_for_shell(123) == '"123"'

    def test_convert_mana_cost(self):
        """Test mana cost conversion."""
        # Test normal case
        assert convert_mana_cost("2UR") == "{2}{U}{R}"
        
        # Test empty/None cases
        assert convert_mana_cost("") == ""
        assert convert_mana_cost(None) == ""
        assert convert_mana_cost("-") == ""
        
        # Test already formatted
        assert convert_mana_cost("{2}{U}{R}") == "{2}{U}{R}"
        
        # Test integer input
        assert convert_mana_cost(5) == "{5}"


class TestMTGCard:
    """Test MTG Card dataclass."""
    
    def test_card_initialization(self, sample_mtg_card):
        """Test card initialization."""
        assert sample_mtg_card.name == "Lightning Bolt"
        assert sample_mtg_card.mana_cost == "{R}"
        assert sample_mtg_card.cmc == 1
        assert sample_mtg_card.type_line == "Instant"
        assert sample_mtg_card.colors == ["R"]
        assert sample_mtg_card.color_identity == ["R"]
        assert sample_mtg_card.oracle_text == "Lightning Bolt deals 3 damage to any target."
        assert sample_mtg_card.rarity == "common"

    def test_card_with_power_toughness(self):
        """Test creature card with power/toughness."""
        creature = MTGCard(
            name="Lightning Bolt Dragon",
            mana_cost="{3}{R}{R}",
            cmc=5,
            type_line="Creature — Dragon",
            colors=["R"],
            color_identity=["R"],
            power=4,
            toughness=4,
            oracle_text="Flying, haste",
            rarity="rare"
        )
        assert creature.power == 4
        assert creature.toughness == 4

    def test_card_minimal_fields(self):
        """Test card with minimal required fields."""
        minimal_card = MTGCard(
            name="Test Card",
            mana_cost="",
            cmc=0,
            type_line="Artifact",
            colors=[],
            color_identity=[],
            power=None,
            toughness=None,
            oracle_text="",
            rarity="common"
        )
        assert minimal_card.name == "Test Card"
        assert minimal_card.colors == []
        assert minimal_card.power is None


class TestAIWorker:
    """Test AI Worker thread functionality."""
    
    def test_ai_worker_initialization(self, qapp):
        """Test AI Worker initialization."""
        worker = AIWorker("Generate a red creature", "creature")
        assert worker.prompt == "Generate a red creature"
        assert worker.generation_type == "creature"
        assert isinstance(worker, QThread)

    @patch('mtg_deck_builder.requests.post')
    def test_ai_worker_run_success(self, mock_post, qapp):
        """Test successful AI worker execution."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Generated card content"}}]
        }
        mock_post.return_value = mock_response
        
        worker = AIWorker("Generate a red creature", "creature")
        
        # Mock environment variable
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test_key'}):
            # Mock the signal
            with patch.object(worker, 'response_ready') as mock_signal:
                worker.run()
                # Worker should emit the signal with result
                mock_signal.emit.assert_called()

    @patch('mtg_deck_builder.requests.post')
    def test_ai_worker_run_failure(self, mock_post, qapp):
        """Test AI worker handling API failures."""
        # Mock failed API response
        mock_post.side_effect = Exception("API Error")
        
        worker = AIWorker("Generate a red creature", "creature")
        
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test_key'}):
            with patch.object(worker, 'error_occurred') as mock_signal:
                worker.run()
                # Worker should emit error signal
                mock_signal.emit.assert_called()


class TestCardGeneratorWorker:
    """Test Card Generator Worker thread functionality."""
    
    def test_card_generator_worker_initialization(self, qapp):
        """Test Card Generator Worker initialization."""
        worker = CardGeneratorWorker(
            "Lightning Bolt Dragon",
            "A fierce dragon creature",
            "creature"
        )
        assert worker.card_name == "Lightning Bolt Dragon"
        assert worker.description == "A fierce dragon creature"
        assert worker.card_type == "creature"
        assert isinstance(worker, QThread)

    @patch('mtg_deck_builder.subprocess.run')
    def test_card_generator_worker_run_success(self, mock_subprocess, qapp):
        """Test successful card generation."""
        # Mock successful subprocess execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Card generated successfully"
        mock_subprocess.return_value = mock_result
        
        worker = CardGeneratorWorker("Test Card", "Test description", "creature")
        
        with patch.object(worker, 'finished') as mock_signal:
            worker.run()
            mock_signal.emit.assert_called()

    @patch('mtg_deck_builder.subprocess.run')
    def test_card_generator_worker_run_failure(self, mock_subprocess, qapp):
        """Test card generation failure handling."""
        # Mock failed subprocess execution
        mock_subprocess.side_effect = Exception("Generation failed")
        
        worker = CardGeneratorWorker("Test Card", "Test description", "creature")
        
        with patch.object(worker, 'error_occurred') as mock_signal:
            worker.run()
            mock_signal.emit.assert_called()


class TestThemeConfigTab:
    """Test Theme Configuration Tab functionality."""
    
    @pytest.fixture
    def theme_tab(self, qapp):
        """Provide a ThemeConfigTab instance."""
        return ThemeConfigTab()

    def test_theme_config_tab_initialization(self, theme_tab):
        """Test theme configuration tab initialization."""
        assert theme_tab is not None
        assert hasattr(theme_tab, 'theme_combo')
        assert hasattr(theme_tab, 'color_buttons')

    def test_load_themes(self, theme_tab):
        """Test loading themes functionality."""
        # Mock the themes directory
        with patch('mtg_deck_builder.Path.exists', return_value=True), \
             patch('mtg_deck_builder.Path.glob') as mock_glob:
            
            mock_theme_file = Mock()
            mock_theme_file.stem = "test_theme"
            mock_glob.return_value = [mock_theme_file]
            
            theme_tab.load_themes()
            
            # Check that theme combo has items
            assert theme_tab.theme_combo.count() > 0

    def test_apply_theme(self, theme_tab):
        """Test theme application."""
        with patch.object(theme_tab, 'theme_applied') as mock_signal:
            theme_tab.apply_theme()
            mock_signal.emit.assert_called()

    def test_reset_theme(self, theme_tab):
        """Test theme reset functionality."""
        with patch.object(theme_tab, 'theme_applied') as mock_signal:
            theme_tab.reset_theme()
            mock_signal.emit.assert_called()


class TestCardManagementTab:
    """Test Card Management Tab functionality."""
    
    @pytest.fixture
    def card_tab(self, qapp):
        """Provide a CardManagementTab instance."""
        with patch('mtg_deck_builder.QSettings'):
            return CardManagementTab()

    def test_card_management_tab_initialization(self, card_tab):
        """Test card management tab initialization."""
        assert card_tab is not None
        assert hasattr(card_tab, 'search_input')
        assert hasattr(card_tab, 'card_table')
        assert hasattr(card_tab, 'deck_cards')

    def test_search_cards(self, card_tab):
        """Test card search functionality."""
        # Add some test cards
        test_cards = [
            {"name": "Lightning Bolt", "type_line": "Instant"},
            {"name": "Lightning Strike", "type_line": "Instant"},
            {"name": "Giant Growth", "type_line": "Instant"}
        ]
        card_tab.deck_cards = test_cards
        
        # Test search
        with patch.object(card_tab, 'update_card_table') as mock_update:
            card_tab.search_input.setText("Lightning")
            card_tab.search_cards()
            mock_update.assert_called()

    def test_filter_by_type(self, card_tab):
        """Test filtering cards by type."""
        # Add test cards with different types
        test_cards = [
            {"name": "Lightning Bolt", "type_line": "Instant"},
            {"name": "Grizzly Bears", "type_line": "Creature — Bear"},
            {"name": "Sol Ring", "type_line": "Artifact"}
        ]
        card_tab.deck_cards = test_cards
        
        with patch.object(card_tab, 'update_card_table') as mock_update:
            card_tab.filter_by_type("Creature")
            mock_update.assert_called()

    def test_add_card_to_deck(self, card_tab):
        """Test adding card to deck."""
        test_card = {
            "name": "Lightning Bolt",
            "mana_cost": "{R}",
            "type_line": "Instant"
        }
        
        initial_count = len(card_tab.deck_cards)
        card_tab.add_card_to_deck(test_card)
        
        assert len(card_tab.deck_cards) == initial_count + 1
        assert test_card in card_tab.deck_cards

    def test_remove_card_from_deck(self, card_tab):
        """Test removing card from deck."""
        test_card = {
            "name": "Lightning Bolt",
            "mana_cost": "{R}",
            "type_line": "Instant"
        }
        card_tab.deck_cards = [test_card]
        
        card_tab.remove_card_from_deck(0)
        assert len(card_tab.deck_cards) == 0


class TestMTGDeckBuilder:
    """Test main MTG Deck Builder application."""
    
    @pytest.fixture
    def deck_builder(self, qapp):
        """Provide a MTGDeckBuilder instance."""
        with patch('mtg_deck_builder.QSettings'), \
             patch.object(MTGDeckBuilder, 'load_card_database'), \
             patch.object(MTGDeckBuilder, 'setup_ui'):
            return MTGDeckBuilder()

    def test_deck_builder_initialization(self, deck_builder):
        """Test deck builder initialization."""
        assert deck_builder is not None
        assert hasattr(deck_builder, 'card_database')
        assert hasattr(deck_builder, 'filtered_cards')
        assert hasattr(deck_builder, 'deck_cards')

    @patch('mtg_deck_builder.requests.get')
    def test_load_card_database_success(self, mock_get, deck_builder):
        """Test successful card database loading."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "name": "Lightning Bolt",
                    "mana_cost": "{R}",
                    "type_line": "Instant",
                    "colors": ["R"]
                }
            ]
        }
        mock_get.return_value = mock_response
        
        deck_builder.load_card_database()
        
        assert len(deck_builder.card_database) > 0
        assert deck_builder.card_database[0]["name"] == "Lightning Bolt"

    @patch('mtg_deck_builder.requests.get')
    def test_load_card_database_failure(self, mock_get, deck_builder):
        """Test card database loading failure handling."""
        # Mock failed API response
        mock_get.side_effect = Exception("API Error")
        
        with patch.object(deck_builder, 'show_error_message') as mock_error:
            deck_builder.load_card_database()
            mock_error.assert_called()

    def test_save_deck(self, deck_builder):
        """Test deck saving functionality."""
        # Add some test cards to deck
        deck_builder.deck_cards = [
            {"name": "Lightning Bolt", "mana_cost": "{R}"},
            {"name": "Giant Growth", "mana_cost": "{G}"}
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            with patch('mtg_deck_builder.QFileDialog.getSaveFileName', 
                      return_value=(temp_path, 'JSON Files (*.json)')):
                deck_builder.save_deck()
                
                # Verify file was created and contains correct data
                with open(temp_path, 'r') as f:
                    saved_data = json.load(f)
                    assert len(saved_data["cards"]) == 2
                    assert saved_data["cards"][0]["name"] == "Lightning Bolt"
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_load_deck(self, deck_builder):
        """Test deck loading functionality."""
        test_deck_data = {
            "deck_name": "Test Deck",
            "cards": [
                {"name": "Lightning Bolt", "mana_cost": "{R}"},
                {"name": "Giant Growth", "mana_cost": "{G}"}
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_deck_data, f)
            temp_path = f.name
        
        try:
            with patch('mtg_deck_builder.QFileDialog.getOpenFileName', 
                      return_value=(temp_path, 'JSON Files (*.json)')):
                deck_builder.load_deck()
                
                # Verify deck was loaded correctly
                assert len(deck_builder.deck_cards) == 2
                assert deck_builder.deck_cards[0]["name"] == "Lightning Bolt"
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_export_deck(self, deck_builder):
        """Test deck export functionality."""
        deck_builder.deck_cards = [
            {"name": "Lightning Bolt", "mana_cost": "{R}"},
            {"name": "Giant Growth", "mana_cost": "{G}"}
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            temp_path = f.name
        
        try:
            with patch('mtg_deck_builder.QFileDialog.getSaveFileName', 
                      return_value=(temp_path, 'Text Files (*.txt)')):
                deck_builder.export_deck()
                
                # Verify export file was created
                assert os.path.exists(temp_path)
                with open(temp_path, 'r') as f:
                    content = f.read()
                    assert "Lightning Bolt" in content
                    assert "Giant Growth" in content
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_filter_cards_by_color(self, deck_builder):
        """Test filtering cards by color."""
        deck_builder.card_database = [
            {"name": "Lightning Bolt", "colors": ["R"]},
            {"name": "Giant Growth", "colors": ["G"]},
            {"name": "Counterspell", "colors": ["U"]},
            {"name": "Sol Ring", "colors": []}
        ]
        
        deck_builder.filter_cards_by_color("R")
        
        red_cards = [card for card in deck_builder.filtered_cards if "R" in card.get("colors", [])]
        assert len(red_cards) == 1
        assert red_cards[0]["name"] == "Lightning Bolt"

    def test_filter_cards_by_mana_cost(self, deck_builder):
        """Test filtering cards by converted mana cost."""
        deck_builder.card_database = [
            {"name": "Lightning Bolt", "cmc": 1},
            {"name": "Counterspell", "cmc": 2},
            {"name": "Wrath of God", "cmc": 4},
            {"name": "Sol Ring", "cmc": 1}
        ]
        
        deck_builder.filter_cards_by_cmc(1)
        
        one_cmc_cards = [card for card in deck_builder.filtered_cards if card.get("cmc") == 1]
        assert len(one_cmc_cards) == 2
        assert any(card["name"] == "Lightning Bolt" for card in one_cmc_cards)
        assert any(card["name"] == "Sol Ring" for card in one_cmc_cards)

    def test_search_functionality(self, deck_builder):
        """Test card search functionality."""
        deck_builder.card_database = [
            {"name": "Lightning Bolt", "oracle_text": "deals 3 damage"},
            {"name": "Lightning Strike", "oracle_text": "deals 3 damage"},
            {"name": "Giant Growth", "oracle_text": "+3/+3 until end of turn"}
        ]
        
        deck_builder.search_cards("Lightning")
        
        lightning_cards = [card for card in deck_builder.filtered_cards 
                          if "Lightning" in card["name"]]
        assert len(lightning_cards) == 2

    def test_deck_validation(self, deck_builder):
        """Test deck validation functionality."""
        # Test valid 100-card Commander deck
        commander_deck = [{"name": f"Card {i}"} for i in range(100)]
        assert deck_builder.validate_deck(commander_deck, "commander")
        
        # Test invalid deck size
        small_deck = [{"name": "Card 1"}]
        assert not deck_builder.validate_deck(small_deck, "commander")
        
        # Test standard deck
        standard_deck = [{"name": f"Card {i}"} for i in range(60)]
        assert deck_builder.validate_deck(standard_deck, "standard")

    def test_mana_curve_analysis(self, deck_builder):
        """Test mana curve analysis."""
        deck_builder.deck_cards = [
            {"cmc": 1}, {"cmc": 1}, {"cmc": 1},  # 3 one-drops
            {"cmc": 2}, {"cmc": 2},              # 2 two-drops
            {"cmc": 3}, {"cmc": 3}, {"cmc": 3}, {"cmc": 3},  # 4 three-drops
            {"cmc": 4},                          # 1 four-drop
            {"cmc": 5}, {"cmc": 5}               # 2 five-drops
        ]
        
        curve = deck_builder.analyze_mana_curve()
        
        assert curve[1] == 3  # 3 one-drops
        assert curve[2] == 2  # 2 two-drops
        assert curve[3] == 4  # 4 three-drops
        assert curve[4] == 1  # 1 four-drop
        assert curve[5] == 2  # 2 five-drops


class TestIntegration:
    """Integration tests for the complete application."""
    
    @pytest.fixture
    def app_with_mocks(self, qapp):
        """Provide a fully mocked application for integration testing."""
        with patch('mtg_deck_builder.QSettings'), \
             patch('mtg_deck_builder.requests.get') as mock_get:
            
            # Mock card database response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": [
                    {
                        "name": "Lightning Bolt",
                        "mana_cost": "{R}",
                        "cmc": 1,
                        "type_line": "Instant",
                        "colors": ["R"],
                        "color_identity": ["R"],
                        "oracle_text": "Lightning Bolt deals 3 damage to any target.",
                        "rarity": "common"
                    }
                ]
            }
            mock_get.return_value = mock_response
            
            app = MTGDeckBuilder()
            return app

    def test_full_deck_creation_workflow(self, app_with_mocks):
        """Test complete deck creation workflow."""
        app = app_with_mocks
        
        # 1. Load card database
        app.load_card_database()
        assert len(app.card_database) > 0
        
        # 2. Search for cards
        app.search_cards("Lightning")
        
        # 3. Add cards to deck
        test_card = app.card_database[0]
        app.add_card_to_deck(test_card)
        assert len(app.deck_cards) == 1
        
        # 4. Save deck
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            with patch('mtg_deck_builder.QFileDialog.getSaveFileName', 
                      return_value=(temp_path, 'JSON Files (*.json)')):
                app.save_deck()
                assert os.path.exists(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_ai_integration_workflow(self, app_with_mocks):
        """Test AI integration workflow."""
        app = app_with_mocks
        
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test_key'}), \
             patch('mtg_deck_builder.requests.post') as mock_post:
            
            # Mock AI response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Generated creature card"}}]
            }
            mock_post.return_value = mock_response
            
            # Start AI worker
            worker = AIWorker("Generate a red creature", "creature")
            
            with patch.object(worker, 'response_ready') as mock_signal:
                worker.run()
                mock_signal.emit.assert_called()

    def test_theme_application_workflow(self, app_with_mocks):
        """Test theme application workflow."""
        app = app_with_mocks
        theme_tab = app.findChild(ThemeConfigTab)
        
        if theme_tab:
            with patch.object(theme_tab, 'theme_applied') as mock_signal:
                theme_tab.apply_theme()
                mock_signal.emit.assert_called()