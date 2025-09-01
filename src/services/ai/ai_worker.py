"""
AI Worker Module

Refactored AIWorker class for handling AI-powered card generation tasks.
This class provides a clean interface for AI operations while maintaining
compatibility with the existing codebase.
"""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.domain.models.mtg_card import MTGCard

logger = logging.getLogger(__name__)


class AIWorker:
    """
    AI Worker for handling card generation tasks using AI services.

    This class provides an abstraction layer for AI-powered operations,
    including text generation, image generation, and card creation workflows.
    """

    def __init__(
        self, config: dict[str, Any] | None = None, output_dir: Path | None = None
    ):
        """
        Initialize the AI Worker.

        Args:
            config: Configuration dictionary for AI services
            output_dir: Directory for output files
        """
        self.config = config or {}
        self.output_dir = output_dir or Path("output")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize logging
        self._setup_logging()

        # Track worker state
        self.is_initialized = False
        self.current_task = None
        self.task_history = []

        logger.info("AIWorker initialized")

    def _setup_logging(self) -> None:
        """Set up logging configuration for the AI worker."""
        log_level = self.config.get("log_level", "INFO")
        logging.basicConfig(
            level=getattr(logging, log_level),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    async def initialize(self) -> bool:
        """
        Initialize the AI worker and all required services.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            logger.info("Initializing AI Worker services...")

            # Initialize AI services here
            # This would include setting up connections to AI APIs,
            # loading models, validating credentials, etc.

            # Simulate async initialization
            await asyncio.sleep(0.1)

            self.is_initialized = True
            logger.info("AI Worker initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize AI Worker: {e}")
            self.is_initialized = False
            return False

    async def generate_card_text(
        self,
        card_name: str,
        card_type: str,
        mana_cost: str = "",
        power: int | None = None,
        toughness: int | None = None,
        **kwargs,
    ) -> dict[str, str]:
        """
        Generate card text using AI.

        Args:
            card_name: Name of the card
            card_type: Type of the card (e.g., "Creature", "Instant")
            mana_cost: Mana cost string
            power: Power value for creatures
            toughness: Toughness value for creatures
            **kwargs: Additional parameters

        Returns:
            Dictionary containing generated text fields
        """
        if not self.is_initialized:
            raise RuntimeError("AI Worker not initialized. Call initialize() first.")

        self.current_task = f"Generating text for {card_name}"
        logger.info(f"Starting text generation: {self.current_task}")

        try:
            # This would integrate with actual AI text generation services
            # For now, return a structured response
            result = {
                "text": f"Generated rules text for {card_name}",
                "flavor": f"Generated flavor text for {card_name}",
                "art_description": f"Art prompt for {card_name}",
            }

            # Log the task completion
            self.task_history.append(
                {
                    "task": self.current_task,
                    "timestamp": datetime.now().isoformat(),
                    "status": "completed",
                    "result_summary": f"Generated text fields for {card_name}",
                }
            )

            logger.info(f"Text generation completed for {card_name}")
            return result

        except Exception as e:
            logger.error(f"Text generation failed for {card_name}: {e}")

            self.task_history.append(
                {
                    "task": self.current_task,
                    "timestamp": datetime.now().isoformat(),
                    "status": "failed",
                    "error": str(e),
                }
            )

            raise
        finally:
            self.current_task = None

    async def generate_card_art(
        self,
        card: MTGCard,
        art_prompt: str | None = None,
        style: str = "mtg_modern",
        **kwargs,
    ) -> Path | None:
        """
        Generate card artwork using AI.

        Args:
            card: MTGCard instance
            art_prompt: Custom art prompt (if None, will be generated)
            style: Art style to use
            **kwargs: Additional generation parameters

        Returns:
            Path to generated image or None if failed
        """
        if not self.is_initialized:
            raise RuntimeError("AI Worker not initialized. Call initialize() first.")

        self.current_task = f"Generating artwork for {card.name}"
        logger.info(f"Starting art generation: {self.current_task}")

        try:
            # Generate art prompt if not provided
            if not art_prompt:
                art_prompt = card.art or f"Fantasy artwork for {card.name}"

            # This would integrate with actual image generation services
            # For now, simulate the process
            await asyncio.sleep(0.5)  # Simulate generation time

            # In a real implementation, this would call image generation APIs
            # and return the actual path to the generated image
            output_path = self.output_dir / f"{card.name}_art.png"

            # Log the task completion
            self.task_history.append(
                {
                    "task": self.current_task,
                    "timestamp": datetime.now().isoformat(),
                    "status": "completed",
                    "result_summary": f"Generated artwork at {output_path}",
                }
            )

            logger.info(f"Art generation completed for {card.name}")
            return output_path

        except Exception as e:
            logger.error(f"Art generation failed for {card.name}: {e}")

            self.task_history.append(
                {
                    "task": self.current_task,
                    "timestamp": datetime.now().isoformat(),
                    "status": "failed",
                    "error": str(e),
                }
            )

            return None
        finally:
            self.current_task = None

    async def generate_complete_card(
        self, card_name: str, card_type: str, **kwargs
    ) -> MTGCard | None:
        """
        Generate a complete card with all fields populated using AI.

        Args:
            card_name: Name of the card
            card_type: Type of the card
            **kwargs: Additional parameters

        Returns:
            Complete MTGCard instance or None if failed
        """
        if not self.is_initialized:
            raise RuntimeError("AI Worker not initialized. Call initialize() first.")

        self.current_task = f"Generating complete card: {card_name}"
        logger.info(f"Starting complete card generation: {self.current_task}")

        try:
            # Generate text content
            text_data = await self.generate_card_text(
                card_name=card_name, card_type=card_type, **kwargs
            )

            # Create the card instance
            card = MTGCard(
                id=int(time.time()),  # Simple ID generation
                name=card_name,
                type=card_type,
                text=text_data.get("text", ""),
                flavor=text_data.get("flavor", ""),
                art=text_data.get("art_description", ""),
                **kwargs,
            )

            # Generate artwork
            art_path = await self.generate_card_art(card)
            if art_path:
                card.image_path = str(art_path)

            # Log the task completion
            self.task_history.append(
                {
                    "task": self.current_task,
                    "timestamp": datetime.now().isoformat(),
                    "status": "completed",
                    "result_summary": f"Generated complete card: {card_name}",
                }
            )

            logger.info(f"Complete card generation finished for {card_name}")
            return card

        except Exception as e:
            logger.error(f"Complete card generation failed for {card_name}: {e}")

            self.task_history.append(
                {
                    "task": self.current_task,
                    "timestamp": datetime.now().isoformat(),
                    "status": "failed",
                    "error": str(e),
                }
            )

            return None
        finally:
            self.current_task = None

    async def batch_generate_cards(
        self, card_specs: list[dict[str, Any]], max_concurrent: int = 3
    ) -> list[MTGCard]:
        """
        Generate multiple cards concurrently.

        Args:
            card_specs: List of card specification dictionaries
            max_concurrent: Maximum number of concurrent generations

        Returns:
            List of generated MTGCard instances
        """
        if not self.is_initialized:
            raise RuntimeError("AI Worker not initialized. Call initialize() first.")

        logger.info(f"Starting batch generation of {len(card_specs)} cards")

        semaphore = asyncio.Semaphore(max_concurrent)

        async def generate_single(spec):
            async with semaphore:
                return await self.generate_complete_card(**spec)

        tasks = [generate_single(spec) for spec in card_specs]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out failed generations and exceptions
        successful_cards = [result for result in results if isinstance(result, MTGCard)]

        logger.info(
            f"Batch generation completed: {len(successful_cards)}/{len(card_specs)} successful"
        )
        return successful_cards

    def get_status(self) -> dict[str, Any]:
        """
        Get current status of the AI worker.

        Returns:
            Status dictionary with current state information
        """
        return {
            "initialized": self.is_initialized,
            "current_task": self.current_task,
            "total_tasks_completed": len(
                [
                    task
                    for task in self.task_history
                    if task.get("status") == "completed"
                ]
            ),
            "total_tasks_failed": len(
                [task for task in self.task_history if task.get("status") == "failed"]
            ),
            "recent_tasks": self.task_history[-5:] if self.task_history else [],
        }

    def clear_history(self) -> None:
        """Clear the task history."""
        self.task_history.clear()
        logger.info("Task history cleared")

    async def shutdown(self) -> None:
        """Shutdown the AI worker and cleanup resources."""
        logger.info("Shutting down AI Worker...")

        # Cancel current task if running
        if self.current_task:
            logger.warning(f"Interrupting current task: {self.current_task}")
            self.current_task = None

        # Cleanup resources
        self.is_initialized = False

        logger.info("AI Worker shutdown complete")
