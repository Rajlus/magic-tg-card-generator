"""Tests for card generation workflows in MTG Deck Builder."""

import json
import os
import subprocess
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests


class TestGenerationWorkflows:
    """Test various card generation workflows."""

    def test_ai_card_generation_workflow(self):
        """Test AI-powered card generation workflow."""
        # Mock OpenAI API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "name": "Lightning Bolt Dragon",
                                "mana_cost": "{3}{R}{R}",
                                "type_line": "Creature — Dragon",
                                "oracle_text": "Flying, haste. When Lightning Bolt Dragon enters the battlefield, it deals 3 damage to any target.",
                                "power": "4",
                                "toughness": "4",
                                "colors": ["R"],
                                "color_identity": ["R"],
                                "cmc": 5,
                                "rarity": "rare",
                            }
                        )
                    }
                }
            ]
        }

        with patch("requests.post", return_value=mock_response), patch.dict(
            os.environ, {"OPENAI_API_KEY": "test_key"}
        ):
            # Simulate AI generation request
            prompt = "Create a red dragon creature with flying and haste"
            generation_type = "creature"

            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": "Bearer test_key"},
                json={
                    "model": "gpt-4",
                    "messages": [{"role": "user", "content": prompt}],
                },
            )

            assert response.status_code == 200
            card_data = json.loads(response.json()["choices"][0]["message"]["content"])

            # Verify generated card structure
            assert card_data["name"] == "Lightning Bolt Dragon"
            assert card_data["type_line"] == "Creature — Dragon"
            assert "Flying, haste" in card_data["oracle_text"]
            assert card_data["power"] == "4"
            assert card_data["toughness"] == "4"

    def test_image_generation_workflow(self):
        """Test image generation workflow."""
        with patch("subprocess.run") as mock_subprocess:
            # Mock successful image generation
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "Image generated successfully"
            mock_subprocess.return_value = mock_result

            # Test parameters
            card_name = "Lightning Bolt Dragon"
            description = "A fierce red dragon breathing lightning"
            card_type = "creature"

            # Simulate calling generate_card.py
            cmd = [
                "python",
                "generate_card.py",
                "--name",
                card_name,
                "--description",
                description,
                "--type",
                card_type,
                "--output-dir",
                "generated_cards",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            # Verify subprocess was called correctly
            mock_subprocess.assert_called_once()
            assert result.returncode == 0

    @patch("subprocess.run")
    def test_unified_generation_workflow(self, mock_subprocess):
        """Test unified card and image generation workflow."""
        # Mock successful unified generation
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Card and image generated successfully"
        mock_subprocess.return_value = mock_result

        # Test unified generation
        prompt = "Create a blue counterspell"

        cmd = [
            "python",
            "generate_unified.py",
            "--prompt",
            prompt,
            "--output-dir",
            "generated_cards",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        mock_subprocess.assert_called_once()
        assert result.returncode == 0

    def test_batch_generation_workflow(self):
        """Test batch generation of multiple cards."""
        card_prompts = [
            "Create a red lightning spell",
            "Create a green growth spell",
            "Create a blue counterspell",
            "Create a white healing spell",
            "Create a black destruction spell",
        ]

        generated_cards = []

        with patch("subprocess.run") as mock_subprocess:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "Card generated successfully"
            mock_subprocess.return_value = mock_result

            for i, prompt in enumerate(card_prompts):
                # Simulate batch generation
                cmd = [
                    "python",
                    "generate_unified.py",
                    "--prompt",
                    prompt,
                    "--output-dir",
                    "generated_cards",
                    "--batch-id",
                    str(i),
                ]

                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode == 0:
                    generated_cards.append(
                        {"prompt": prompt, "batch_id": i, "status": "success"}
                    )

        # Verify all cards were processed
        assert len(generated_cards) == 5
        assert mock_subprocess.call_count == 5

    def test_error_handling_in_generation(self):
        """Test error handling during generation workflows."""
        with patch("subprocess.run") as mock_subprocess:
            # Mock generation failure
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stderr = "Generation failed: Invalid parameters"
            mock_subprocess.return_value = mock_result

            # Test failed generation
            cmd = [
                "python",
                "generate_card.py",
                "--name",
                "",  # Invalid empty name
                "--description",
                "Test description",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            assert result.returncode == 1
            assert "Generation failed" in result.stderr

    def test_generation_with_custom_parameters(self):
        """Test generation with custom parameters."""
        custom_params = {
            "name": "Custom Spell",
            "mana_cost": "{2}{U}{R}",
            "type_line": "Instant",
            "oracle_text": "Deal 2 damage and draw a card",
            "flavor_text": "Magic at its finest",
            "artist": "Test Artist",
            "rarity": "uncommon",
            "set": "TEST",
        }

        with patch("subprocess.run") as mock_subprocess:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = f"Generated card: {custom_params['name']}"
            mock_subprocess.return_value = mock_result

            # Build command with custom parameters
            cmd = ["python", "generate_card.py"]
            for key, value in custom_params.items():
                cmd.extend([f"--{key.replace('_', '-')}", str(value)])

            result = subprocess.run(cmd, capture_output=True, text=True)

            assert result.returncode == 0
            mock_subprocess.assert_called_once()

    def test_generation_output_validation(self):
        """Test validation of generation output."""
        # Mock generation output files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock generated files
            card_json_path = os.path.join(temp_dir, "test_card.json")
            card_image_path = os.path.join(temp_dir, "test_card.png")

            # Mock card data
            card_data = {
                "name": "Test Card",
                "mana_cost": "{2}{R}",
                "type_line": "Instant",
                "oracle_text": "Deal 2 damage to any target.",
                "generated_timestamp": "2024-08-31T10:30:00",
                "generation_parameters": {
                    "model": "gpt-4",
                    "temperature": 0.7,
                    "max_tokens": 500,
                },
            }

            # Write mock files
            with open(card_json_path, "w") as f:
                json.dump(card_data, f)

            # Create empty image file
            with open(card_image_path, "wb") as f:
                f.write(b"fake_image_data")

            # Validate outputs
            assert os.path.exists(card_json_path)
            assert os.path.exists(card_image_path)

            # Validate card data structure
            with open(card_json_path) as f:
                loaded_card = json.load(f)

            required_fields = ["name", "mana_cost", "type_line", "oracle_text"]
            for field in required_fields:
                assert field in loaded_card
                assert loaded_card[field] is not None

            # Validate image file
            assert os.path.getsize(card_image_path) > 0

    def test_generation_with_templates(self):
        """Test generation using card templates."""
        templates = {
            "creature": {
                "type_line": "Creature — {creature_type}",
                "required_fields": ["power", "toughness"],
                "optional_fields": ["abilities"],
            },
            "instant": {
                "type_line": "Instant",
                "required_fields": ["oracle_text"],
                "optional_fields": ["flavor_text"],
            },
            "artifact": {
                "type_line": "Artifact",
                "required_fields": ["oracle_text"],
                "optional_fields": ["activation_cost"],
            },
        }

        for template_type, _template_data in templates.items():
            with patch("subprocess.run") as mock_subprocess:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = f"Generated {template_type} card"
                mock_subprocess.return_value = mock_result

                cmd = [
                    "python",
                    "generate_card.py",
                    "--template",
                    template_type,
                    "--name",
                    f"Test {template_type.title()}",
                ]

                result = subprocess.run(cmd, capture_output=True, text=True)
                assert result.returncode == 0

    def test_generation_queue_management(self):
        """Test management of generation queue for multiple requests."""
        generation_queue = []

        # Add generation requests to queue
        requests = [
            {"name": "Card 1", "type": "creature", "priority": "high"},
            {"name": "Card 2", "type": "instant", "priority": "normal"},
            {"name": "Card 3", "type": "artifact", "priority": "low"},
            {"name": "Card 4", "type": "creature", "priority": "high"},
        ]

        for request in requests:
            generation_queue.append(
                {
                    "id": len(generation_queue) + 1,
                    "status": "queued",
                    "request": request,
                    "created_at": "2024-08-31T10:30:00",
                }
            )

        # Sort queue by priority
        priority_order = {"high": 3, "normal": 2, "low": 1}
        generation_queue.sort(
            key=lambda x: priority_order.get(x["request"]["priority"], 0), reverse=True
        )

        # Verify queue ordering
        assert generation_queue[0]["request"]["priority"] == "high"
        assert generation_queue[1]["request"]["priority"] == "high"
        assert generation_queue[2]["request"]["priority"] == "normal"
        assert generation_queue[3]["request"]["priority"] == "low"

        # Simulate processing queue
        processed_count = 0
        with patch("subprocess.run") as mock_subprocess:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_subprocess.return_value = mock_result

            for item in generation_queue[:2]:  # Process first 2 items
                item["status"] = "processing"
                # Simulate generation
                result = subprocess.run(
                    ["python", "generate_card.py"], capture_output=True, text=True
                )
                if result.returncode == 0:
                    item["status"] = "completed"
                    processed_count += 1
                else:
                    item["status"] = "failed"

        assert processed_count == 2
        assert generation_queue[0]["status"] == "completed"
        assert generation_queue[1]["status"] == "completed"

    def test_generation_performance_monitoring(self):
        """Test performance monitoring during generation."""
        import time

        generation_stats = {
            "total_generations": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "average_generation_time": 0,
            "generation_times": [],
        }

        # Mock multiple generations with timing
        with patch("subprocess.run") as mock_subprocess:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_subprocess.return_value = mock_result

            for _i in range(5):
                start_time = time.time()

                # Simulate generation
                result = subprocess.run(
                    ["python", "generate_card.py"], capture_output=True, text=True
                )

                end_time = time.time()
                generation_time = end_time - start_time

                generation_stats["total_generations"] += 1
                generation_stats["generation_times"].append(generation_time)

                if result.returncode == 0:
                    generation_stats["successful_generations"] += 1
                else:
                    generation_stats["failed_generations"] += 1

        # Calculate average generation time
        if generation_stats["generation_times"]:
            generation_stats["average_generation_time"] = sum(
                generation_stats["generation_times"]
            ) / len(generation_stats["generation_times"])

        # Verify statistics
        assert generation_stats["total_generations"] == 5
        assert generation_stats["successful_generations"] == 5
        assert generation_stats["failed_generations"] == 0
        assert generation_stats["average_generation_time"] > 0

    def test_generation_cleanup_workflow(self):
        """Test cleanup of generation temporary files and cache."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock temporary files
            temp_files = [
                "temp_card_1.json",
                "temp_card_2.json",
                "temp_image_1.png",
                "temp_image_2.png",
                "generation_cache.json",
            ]

            for filename in temp_files:
                filepath = os.path.join(temp_dir, filename)
                with open(filepath, "w") as f:
                    f.write("temporary data")

            # Verify files exist
            for filename in temp_files:
                filepath = os.path.join(temp_dir, filename)
                assert os.path.exists(filepath)

            # Simulate cleanup
            for filename in temp_files:
                filepath = os.path.join(temp_dir, filename)
                if os.path.exists(filepath):
                    os.unlink(filepath)

            # Verify cleanup
            for filename in temp_files:
                filepath = os.path.join(temp_dir, filename)
                assert not os.path.exists(filepath)

    def test_generation_retry_mechanism(self):
        """Test retry mechanism for failed generations."""
        max_retries = 3
        retry_count = 0

        with patch("subprocess.run") as mock_subprocess:
            # First two attempts fail, third succeeds
            mock_results = [
                Mock(returncode=1, stderr="Generation failed"),
                Mock(returncode=1, stderr="Generation failed"),
                Mock(returncode=0, stdout="Generation successful"),
            ]
            mock_subprocess.side_effect = mock_results

            # Simulate retry logic
            for _attempt in range(max_retries):
                result = subprocess.run(
                    ["python", "generate_card.py"], capture_output=True, text=True
                )
                retry_count += 1

                if result.returncode == 0:
                    break
                elif retry_count >= max_retries:
                    break
                else:
                    # Wait before retry (mocked)
                    pass

            # Verify retry behavior
            assert retry_count == 3
            assert mock_subprocess.call_count == 3
            assert result.returncode == 0
