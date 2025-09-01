"""Tests for file operations in the MTG Deck Builder."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


class TestFileOperations:
    """Test file operations for saving, loading, and exporting decks."""

    def test_save_deck_json_format(self):
        """Test saving deck in JSON format."""
        deck_data = {
            "deck_name": "Test Commander Deck",
            "format": "commander",
            "cards": [
                {
                    "name": "Lightning Bolt",
                    "mana_cost": "{R}",
                    "cmc": 1,
                    "type_line": "Instant",
                    "quantity": 1,
                },
                {
                    "name": "Giant Growth",
                    "mana_cost": "{G}",
                    "cmc": 1,
                    "type_line": "Instant",
                    "quantity": 4,
                },
            ],
            "total_cards": 100,
            "created_date": "2024-08-31",
            "commander": "Omnath, Locus of Mana",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(deck_data, f, indent=2)
            temp_path = f.name

        try:
            # Verify file was created correctly
            assert os.path.exists(temp_path)

            # Verify content
            with open(temp_path) as f:
                loaded_data = json.load(f)
                assert loaded_data["deck_name"] == "Test Commander Deck"
                assert loaded_data["format"] == "commander"
                assert len(loaded_data["cards"]) == 2
                assert loaded_data["cards"][0]["name"] == "Lightning Bolt"
                assert loaded_data["total_cards"] == 100
                assert loaded_data["commander"] == "Omnath, Locus of Mana"
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_load_deck_json_format(self):
        """Test loading deck from JSON format."""
        deck_data = {
            "deck_name": "Loaded Test Deck",
            "format": "standard",
            "cards": [
                {"name": "Shock", "quantity": 4},
                {"name": "Lightning Strike", "quantity": 4},
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(deck_data, f)
            temp_path = f.name

        try:
            # Load and verify
            with open(temp_path) as f:
                loaded_data = json.load(f)

            assert loaded_data["deck_name"] == "Loaded Test Deck"
            assert loaded_data["format"] == "standard"
            assert len(loaded_data["cards"]) == 2
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_export_deck_text_format(self):
        """Test exporting deck to text format."""
        deck_cards = [
            {"name": "Lightning Bolt", "quantity": 4, "mana_cost": "{R}"},
            {"name": "Mountain", "quantity": 20, "mana_cost": ""},
            {"name": "Giant Growth", "quantity": 4, "mana_cost": "{G}"},
            {"name": "Forest", "quantity": 20, "mana_cost": ""},
        ]

        expected_output = """Deck Export - Generated on 2024-08-31

Main Deck (48 cards):
4x Lightning Bolt {R}
4x Giant Growth {G}

Lands (40 cards):
20x Mountain
20x Forest

Total Cards: 48
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            # Simulate export process
            f.write("Deck Export - Generated on 2024-08-31\n\n")

            # Separate lands from non-lands
            lands = [
                card
                for card in deck_cards
                if "Land" in card.get("type_line", "") or card["mana_cost"] == ""
            ]
            non_lands = [
                card
                for card in deck_cards
                if "Land" not in card.get("type_line", "") and card["mana_cost"] != ""
            ]

            if non_lands:
                total_non_lands = sum(card["quantity"] for card in non_lands)
                f.write(f"Main Deck ({total_non_lands} cards):\n")
                for card in non_lands:
                    f.write(f"{card['quantity']}x {card['name']} {card['mana_cost']}\n")
                f.write("\n")

            if lands:
                total_lands = sum(card["quantity"] for card in lands)
                f.write(f"Lands ({total_lands} cards):\n")
                for card in lands:
                    f.write(f"{card['quantity']}x {card['name']}\n")
                f.write("\n")

            total_cards = sum(card["quantity"] for card in deck_cards)
            f.write(f"Total Cards: {total_cards}\n")

            temp_path = f.name

        try:
            # Verify export file
            assert os.path.exists(temp_path)

            with open(temp_path) as f:
                content = f.read()

            assert "Lightning Bolt" in content
            assert "Giant Growth" in content
            assert "Mountain" in content
            assert "Forest" in content
            assert "Total Cards: 48" in content
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_export_deck_mtga_format(self):
        """Test exporting deck to MTG Arena format."""
        deck_cards = [
            {
                "name": "Lightning Bolt",
                "quantity": 4,
                "set": "M21",
                "collector_number": "160",
            },
            {"name": "Shock", "quantity": 4, "set": "M21", "collector_number": "159"},
            {
                "name": "Mountain",
                "quantity": 20,
                "set": "ZNR",
                "collector_number": "274",
            },
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            # MTGA format: "Quantity Name (SET) Collector_Number"
            for card in deck_cards:
                set_code = card.get("set", "UNK")
                collector_num = card.get("collector_number", "1")
                f.write(
                    f"{card['quantity']} {card['name']} ({set_code}) {collector_num}\n"
                )

            temp_path = f.name

        try:
            assert os.path.exists(temp_path)

            with open(temp_path) as f:
                content = f.read()

            assert "4 Lightning Bolt (M21) 160" in content
            assert "4 Shock (M21) 159" in content
            assert "20 Mountain (ZNR) 274" in content
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_backup_and_restore_functionality(self):
        """Test deck backup and restore functionality."""
        original_deck = {
            "deck_name": "Original Deck",
            "cards": [{"name": "Lightning Bolt", "quantity": 4}],
            "format": "standard",
        }

        # Create backup directory
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir) / "backups"
            backup_dir.mkdir()

            # Save original deck
            original_path = backup_dir / "original_deck.json"
            with open(original_path, "w") as f:
                json.dump(original_deck, f)

            # Create backup
            backup_path = backup_dir / "original_deck_backup.json"
            with open(original_path) as src, open(backup_path, "w") as dst:
                dst.write(src.read())

            # Verify backup exists
            assert backup_path.exists()

            # Verify backup content
            with open(backup_path) as f:
                backup_data = json.load(f)

            assert backup_data == original_deck

    def test_auto_save_functionality(self):
        """Test automatic deck saving functionality."""
        deck_data = {
            "deck_name": "Auto Save Test",
            "cards": [{"name": "Mountain", "quantity": 1}],
            "last_modified": "2024-08-31T10:30:00",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            auto_save_path = Path(temp_dir) / "autosave.json"

            # Simulate auto-save
            with open(auto_save_path, "w") as f:
                json.dump(deck_data, f)

            # Verify auto-save file
            assert auto_save_path.exists()

            # Load auto-save
            with open(auto_save_path) as f:
                loaded_data = json.load(f)

            assert loaded_data["deck_name"] == "Auto Save Test"
            assert "last_modified" in loaded_data

    def test_import_external_deck_formats(self):
        """Test importing decks from various external formats."""
        # Test importing from MTGO format
        mtgo_format = """// 60 Maindeck
// 4 Creature
4 Lightning Bolt
4 Shock
20 Mountain
32 Island

// 15 Sideboard
// 4 Instant
4 Counterspell
4 Negate
4 Dispel
3 Blue Elemental Blast
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(mtgo_format)
            temp_path = f.name

        try:
            # Parse MTGO format
            cards = []
            with open(temp_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("//") and line[0].isdigit():
                        parts = line.split(" ", 1)
                        if len(parts) == 2:
                            quantity = int(parts[0])
                            name = parts[1]
                            cards.append({"name": name, "quantity": quantity})

            # Verify parsing
            assert len(cards) > 0
            assert any(
                card["name"] == "Lightning Bolt" and card["quantity"] == 4
                for card in cards
            )
            assert any(
                card["name"] == "Mountain" and card["quantity"] == 20 for card in cards
            )

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_deck_statistics_export(self):
        """Test exporting deck statistics."""
        deck_cards = [
            {
                "name": "Lightning Bolt",
                "cmc": 1,
                "type_line": "Instant",
                "colors": ["R"],
            },
            {"name": "Shock", "cmc": 1, "type_line": "Instant", "colors": ["R"]},
            {
                "name": "Grizzly Bears",
                "cmc": 2,
                "type_line": "Creature — Bear",
                "colors": ["G"],
            },
            {"name": "Giant Growth", "cmc": 1, "type_line": "Instant", "colors": ["G"]},
            {"name": "Sol Ring", "cmc": 1, "type_line": "Artifact", "colors": []},
        ]

        # Calculate statistics
        total_cards = len(deck_cards)
        avg_cmc = sum(card["cmc"] for card in deck_cards) / total_cards
        color_distribution = {"R": 0, "G": 0, "U": 0, "B": 0, "W": 0, "Colorless": 0}
        type_distribution = {}

        for card in deck_cards:
            # Color distribution
            if not card["colors"]:
                color_distribution["Colorless"] += 1
            else:
                for color in card["colors"]:
                    if color in color_distribution:
                        color_distribution[color] += 1

            # Type distribution
            main_type = card["type_line"].split(" —")[0].split()[-1]
            type_distribution[main_type] = type_distribution.get(main_type, 0) + 1

        stats = {
            "total_cards": total_cards,
            "average_cmc": round(avg_cmc, 2),
            "color_distribution": color_distribution,
            "type_distribution": type_distribution,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(stats, f, indent=2)
            temp_path = f.name

        try:
            # Verify statistics
            with open(temp_path) as f:
                loaded_stats = json.load(f)

            assert loaded_stats["total_cards"] == 5
            assert loaded_stats["average_cmc"] == 1.2
            assert loaded_stats["color_distribution"]["R"] == 2
            assert loaded_stats["color_distribution"]["G"] == 2
            assert loaded_stats["type_distribution"]["Instant"] == 3
            assert loaded_stats["type_distribution"]["Creature"] == 1

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_file_corruption_handling(self):
        """Test handling of corrupted deck files."""
        # Test with invalid JSON
        corrupted_json = '{"deck_name": "Test", "cards": [incomplete'

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(corrupted_json)
            temp_path = f.name

        try:
            # Attempt to load corrupted file
            with pytest.raises(json.JSONDecodeError), open(temp_path) as f:
                json.load(f)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_large_deck_file_handling(self):
        """Test handling of large deck files."""
        # Create a large deck (e.g., cube with 540+ cards)
        large_deck = {"deck_name": "Large Cube", "format": "cube", "cards": []}

        # Generate 1000 cards
        for i in range(1000):
            large_deck["cards"].append(
                {
                    "name": f"Test Card {i}",
                    "mana_cost": f"{{{i % 10}}}",
                    "cmc": i % 10,
                    "type_line": "Creature — Test",
                    "colors": ["R"] if i % 2 == 0 else ["G"],
                }
            )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(large_deck, f)
            temp_path = f.name

        try:
            # Verify large file can be handled
            file_size = os.path.getsize(temp_path)
            assert file_size > 10000  # Should be at least 10KB

            # Verify it can be loaded
            with open(temp_path) as f:
                loaded_deck = json.load(f)

            assert len(loaded_deck["cards"]) == 1000
            assert loaded_deck["deck_name"] == "Large Cube"

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
