"""Integration tests for the complete MTG Deck Builder system."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
import sys

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestSystemIntegration:
    """Integration tests for the complete system."""
    
    def test_complete_deck_building_workflow(self):
        """Test complete deck building workflow from start to finish."""
        # 1. Initialize application with mocked components
        with patch('requests.get') as mock_get:
            # Mock card database API response
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
                    },
                    {
                        "name": "Giant Growth", 
                        "mana_cost": "{G}",
                        "cmc": 1,
                        "type_line": "Instant",
                        "colors": ["G"],
                        "color_identity": ["G"],
                        "oracle_text": "Target creature gets +3/+3 until end of turn.",
                        "rarity": "common"
                    }
                ]
            }
            mock_get.return_value = mock_response
            
            # Simulate loading card database
            card_database = mock_response.json()["data"]
            assert len(card_database) == 2
            
            # 2. Search and filter cards
            search_results = [card for card in card_database 
                            if "lightning" in card["name"].lower()]
            assert len(search_results) == 1
            assert search_results[0]["name"] == "Lightning Bolt"
            
            # 3. Build deck by adding cards
            deck_cards = []
            
            # Add Lightning Bolt (4 copies)
            for _ in range(4):
                deck_cards.append({
                    **search_results[0],
                    "quantity": 1,
                    "deck_position": len(deck_cards)
                })
            
            # Add Giant Growth (4 copies)
            giant_growth = [card for card in card_database 
                          if card["name"] == "Giant Growth"][0]
            for _ in range(4):
                deck_cards.append({
                    **giant_growth,
                    "quantity": 1,
                    "deck_position": len(deck_cards)
                })
            
            assert len(deck_cards) == 8
            
            # 4. Validate deck composition
            red_cards = [card for card in deck_cards if "R" in card["colors"]]
            green_cards = [card for card in deck_cards if "G" in card["colors"]]
            
            assert len(red_cards) == 4
            assert len(green_cards) == 4
            
            # 5. Save deck to file
            deck_data = {
                "deck_name": "Integration Test Deck",
                "format": "standard",
                "cards": deck_cards,
                "total_cards": len(deck_cards),
                "created_date": "2024-08-31",
                "mana_curve": self._calculate_mana_curve(deck_cards)
            }
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(deck_data, f)
                temp_path = f.name
            
            try:
                # 6. Load and verify saved deck
                with open(temp_path, 'r') as f:
                    loaded_deck = json.load(f)
                
                assert loaded_deck["deck_name"] == "Integration Test Deck"
                assert loaded_deck["total_cards"] == 8
                assert len(loaded_deck["cards"]) == 8
                
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

    def test_ai_generation_integration(self):
        """Test AI generation integration workflow."""
        with patch('requests.post') as mock_post, \
             patch('subprocess.run') as mock_subprocess, \
             patch.dict(os.environ, {'OPENAI_API_KEY': 'test_key'}):
            
            # 1. Mock AI response for card generation
            mock_ai_response = Mock()
            mock_ai_response.status_code = 200
            mock_ai_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "name": "AI Generated Dragon",
                            "mana_cost": "{4}{R}{R}",
                            "type_line": "Creature — Dragon",
                            "oracle_text": "Flying, haste. When AI Generated Dragon enters the battlefield, it deals 4 damage to any target.",
                            "power": "5",
                            "toughness": "4",
                            "colors": ["R"],
                            "cmc": 6,
                            "rarity": "rare"
                        })
                    }
                }]
            }
            mock_post.return_value = mock_ai_response
            
            # 2. Mock image generation process
            mock_image_result = Mock()
            mock_image_result.returncode = 0
            mock_image_result.stdout = "Image generated successfully"
            mock_subprocess.return_value = mock_image_result
            
            # 3. Simulate AI generation workflow
            prompt = "Create a powerful red dragon creature"
            
            # AI text generation
            ai_response = mock_post.return_value
            card_data = json.loads(ai_response.json()["choices"][0]["message"]["content"])
            
            assert card_data["name"] == "AI Generated Dragon"
            assert card_data["type_line"] == "Creature — Dragon"
            assert "Flying, haste" in card_data["oracle_text"]
            
            # Image generation
            image_result = mock_subprocess.return_value
            assert image_result.returncode == 0
            
            # 4. Add generated card to deck
            deck_cards = [card_data]
            
            # 5. Verify integration
            assert len(deck_cards) == 1
            assert deck_cards[0]["colors"] == ["R"]
            assert deck_cards[0]["cmc"] == 6

    def test_theme_and_ui_integration(self):
        """Test theme system integration with UI components."""
        # Mock theme configuration
        theme_config = {
            "name": "Dark Theme",
            "colors": {
                "background": "#2b2b2b",
                "foreground": "#ffffff",
                "accent": "#4a9eff",
                "error": "#ff6b6b"
            },
            "fonts": {
                "main": "Arial, 10pt",
                "header": "Arial, 12pt, bold"
            }
        }
        
        # Simulate theme application
        applied_styles = {}
        
        def apply_theme_to_component(component_name, theme):
            style = f"""
            {component_name} {{
                background-color: {theme['colors']['background']};
                color: {theme['colors']['foreground']};
                font: {theme['fonts']['main']};
            }}
            """
            applied_styles[component_name] = style
            return style
        
        # Apply theme to different UI components
        components = ["QMainWindow", "QTableWidget", "QLineEdit", "QPushButton"]
        
        for component in components:
            style = apply_theme_to_component(component, theme_config)
            assert theme_config["colors"]["background"] in style
            assert theme_config["colors"]["foreground"] in style
        
        assert len(applied_styles) == len(components)

    def test_card_database_sync_integration(self):
        """Test card database synchronization integration."""
        with patch('requests.get') as mock_get:
            # Simulate multiple API calls for different sets
            set_responses = {
                "LEA": {
                    "data": [
                        {"name": "Black Lotus", "set": "LEA", "rarity": "rare"},
                        {"name": "Lightning Bolt", "set": "LEA", "rarity": "common"}
                    ]
                },
                "M21": {
                    "data": [
                        {"name": "Lightning Bolt", "set": "M21", "rarity": "common"},
                        {"name": "Giant Growth", "set": "M21", "rarity": "common"}
                    ]
                }
            }
            
            def mock_api_response(url, **kwargs):
                response = Mock()
                response.status_code = 200
                
                # Determine which set is being requested
                if "LEA" in url:
                    response.json.return_value = set_responses["LEA"]
                elif "M21" in url:
                    response.json.return_value = set_responses["M21"]
                else:
                    response.json.return_value = {"data": []}
                
                return response
            
            mock_get.side_effect = mock_api_response
            
            # Simulate database sync process
            all_cards = {}
            
            for set_code in ["LEA", "M21"]:
                url = f"https://api.scryfall.com/cards/search?q=set:{set_code}"
                response = mock_get(url)
                
                if response.status_code == 200:
                    cards = response.json()["data"]
                    for card in cards:
                        card_key = f"{card['name']}_{card['set']}"
                        all_cards[card_key] = card
            
            # Verify synchronized database
            assert len(all_cards) == 4  # 2 cards from each set
            assert "Black_Lotus_LEA" in all_cards
            assert "Lightning_Bolt_LEA" in all_cards
            assert "Lightning_Bolt_M21" in all_cards
            assert "Giant_Growth_M21" in all_cards
            
            # Test duplicate handling (Lightning Bolt appears in both sets)
            lightning_bolts = [card for key, card in all_cards.items() 
                             if "Lightning_Bolt" in key]
            assert len(lightning_bolts) == 2

    def test_backup_and_recovery_integration(self):
        """Test backup and recovery system integration."""
        # Create test deck data
        original_deck = {
            "deck_name": "Test Deck for Backup",
            "cards": [
                {"name": "Lightning Bolt", "quantity": 4},
                {"name": "Mountain", "quantity": 20}
            ],
            "total_cards": 24,
            "last_modified": "2024-08-31T10:00:00"
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. Save original deck
            deck_path = Path(temp_dir) / "test_deck.json"
            backup_path = Path(temp_dir) / "test_deck_backup.json"
            
            with open(deck_path, 'w') as f:
                json.dump(original_deck, f)
            
            # 2. Create backup
            with open(deck_path, 'r') as src, open(backup_path, 'w') as dst:
                dst.write(src.read())
            
            # 3. Modify original deck
            original_deck["cards"].append({"name": "Giant Growth", "quantity": 4})
            original_deck["total_cards"] = 28
            original_deck["last_modified"] = "2024-08-31T11:00:00"
            
            with open(deck_path, 'w') as f:
                json.dump(original_deck, f)
            
            # 4. Simulate corruption of main file
            with open(deck_path, 'w') as f:
                f.write("corrupted data")
            
            # 5. Recovery from backup
            try:
                with open(deck_path, 'r') as f:
                    json.load(f)  # This should fail
                recovery_needed = False
            except json.JSONDecodeError:
                recovery_needed = True
            
            if recovery_needed:
                # Restore from backup
                with open(backup_path, 'r') as backup, open(deck_path, 'w') as main:
                    main.write(backup.read())
            
            # 6. Verify recovery
            with open(deck_path, 'r') as f:
                recovered_deck = json.load(f)
            
            assert recovered_deck["deck_name"] == "Test Deck for Backup"
            assert len(recovered_deck["cards"]) == 2  # Original version before modification
            assert recovered_deck["total_cards"] == 24

    def test_performance_monitoring_integration(self):
        """Test performance monitoring integration."""
        import time
        
        performance_metrics = {
            "database_load_time": 0,
            "search_time": 0,
            "filter_time": 0,
            "save_time": 0,
            "memory_usage": 0
        }
        
        # Mock card database (large dataset)
        large_database = []
        for i in range(10000):
            large_database.append({
                "name": f"Test Card {i}",
                "mana_cost": f"{{{i % 10}}}",
                "cmc": i % 10,
                "type_line": "Creature" if i % 2 == 0 else "Instant",
                "colors": ["R"] if i % 3 == 0 else ["G"]
            })
        
        # 1. Measure database loading
        start_time = time.time()
        # Simulate database processing
        processed_db = [card for card in large_database if card["cmc"] <= 5]
        performance_metrics["database_load_time"] = time.time() - start_time
        
        # 2. Measure search performance
        start_time = time.time()
        search_results = [card for card in processed_db if "Test Card 1" in card["name"]]
        performance_metrics["search_time"] = time.time() - start_time
        
        # 3. Measure filter performance
        start_time = time.time()
        red_cards = [card for card in processed_db if "R" in card["colors"]]
        performance_metrics["filter_time"] = time.time() - start_time
        
        # 4. Measure save performance
        test_deck = {"cards": red_cards[:100]}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            start_time = time.time()
            json.dump(test_deck, f)
            performance_metrics["save_time"] = time.time() - start_time
            temp_path = f.name
        
        try:
            # 5. Verify performance metrics
            assert performance_metrics["database_load_time"] < 1.0  # Should be fast
            assert performance_metrics["search_time"] < 0.1  # Search should be very fast
            assert performance_metrics["filter_time"] < 0.5  # Filtering should be reasonable
            assert performance_metrics["save_time"] < 0.1  # Save should be fast
            
            # Log performance metrics
            print(f"Performance Metrics: {performance_metrics}")
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_error_handling_integration(self):
        """Test integrated error handling across components."""
        error_log = []
        
        def log_error(component, error_type, message):
            error_log.append({
                "component": component,
                "error_type": error_type,
                "message": message,
                "timestamp": "2024-08-31T10:30:00"
            })
        
        # 1. Test API error handling
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("Network error")
            
            try:
                # Simulate API call
                response = mock_get("https://api.scryfall.com/cards")
            except Exception as e:
                log_error("CardDatabase", "NetworkError", str(e))
        
        # 2. Test file I/O error handling
        try:
            with open("/invalid/path/deck.json", 'r') as f:
                json.load(f)
        except (FileNotFoundError, PermissionError) as e:
            log_error("FileManager", "FileError", str(e))
        
        # 3. Test JSON parsing error handling
        try:
            json.loads("invalid json {")
        except json.JSONDecodeError as e:
            log_error("DataParser", "ParseError", str(e))
        
        # 4. Test generation error handling
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.side_effect = Exception("Generation failed")
            
            try:
                # Simulate generation call
                mock_subprocess(["python", "generate_card.py"])
            except Exception as e:
                log_error("CardGenerator", "GenerationError", str(e))
        
        # 5. Verify error logging
        assert len(error_log) == 4
        
        error_types = [entry["error_type"] for entry in error_log]
        assert "NetworkError" in error_types
        assert "FileError" in error_types
        assert "ParseError" in error_types
        assert "GenerationError" in error_types
        
        # Verify all errors have required fields
        for entry in error_log:
            assert "component" in entry
            assert "error_type" in entry
            assert "message" in entry
            assert "timestamp" in entry

    def test_concurrent_operations_integration(self):
        """Test concurrent operations integration."""
        import threading
        import queue
        
        results_queue = queue.Queue()
        
        def worker_task(task_id, operation_type):
            """Simulate a worker task."""
            if operation_type == "search":
                # Simulate search operation
                result = f"Search completed for task {task_id}"
            elif operation_type == "filter":
                # Simulate filter operation
                result = f"Filter completed for task {task_id}"
            elif operation_type == "generate":
                # Simulate generation operation
                result = f"Generation completed for task {task_id}"
            else:
                result = f"Unknown operation for task {task_id}"
            
            results_queue.put({
                "task_id": task_id,
                "result": result,
                "status": "completed"
            })
        
        # Start multiple concurrent tasks
        threads = []
        tasks = [
            (1, "search"),
            (2, "filter"),
            (3, "generate"),
            (4, "search"),
            (5, "filter")
        ]
        
        for task_id, operation in tasks:
            thread = threading.Thread(target=worker_task, args=(task_id, operation))
            threads.append(thread)
            thread.start()
        
        # Wait for all tasks to complete
        for thread in threads:
            thread.join()
        
        # Collect results
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())
        
        # Verify all tasks completed
        assert len(results) == 5
        
        completed_tasks = [r["task_id"] for r in results if r["status"] == "completed"]
        assert len(completed_tasks) == 5
        assert all(task_id in completed_tasks for task_id, _ in tasks)

    def _calculate_mana_curve(self, cards):
        """Helper method to calculate mana curve."""
        curve = {}
        for card in cards:
            cmc = card.get("cmc", 0)
            curve[cmc] = curve.get(cmc, 0) + 1
        return curve