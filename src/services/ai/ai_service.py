"""
AI Service Module

Core AI service logic for the Magic: The Gathering Card Generator.
This module provides high-level AI operations and service orchestration.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Optional, Union

from src.domain.models.mtg_card import MTGCard

from .ai_worker import AIWorker
from .prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class AIService:
    """
    High-level AI service for Magic: The Gathering card generation.

    This service orchestrates AI workers and provides a simplified interface
    for AI-powered operations in the card generator application.
    """

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        output_dir: Path | None = None,
        max_workers: int = 2,
    ):
        """
        Initialize the AI service.

        Args:
            config: Configuration dictionary
            output_dir: Output directory for generated files
            max_workers: Maximum number of AI workers
        """
        self.config = config or {}
        self.output_dir = output_dir or Path("output")
        self.max_workers = max_workers

        # Initialize components
        self.prompt_builder = PromptBuilder(config=self.config)
        self.workers: list[AIWorker] = []
        self._worker_pool = None
        self.is_initialized = False

        logger.info(f"AIService initialized with {max_workers} max workers")
        logger.debug(f"Output directory: {self.output_dir}")

    async def initialize(self) -> bool:
        """
        Initialize the AI service and all workers.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            logger.info("Initializing AI Service...")

            # Create and initialize workers
            for i in range(self.max_workers):
                worker = AIWorker(
                    config=self.config, output_dir=self.output_dir / f"worker_{i}"
                )

                if await worker.initialize():
                    self.workers.append(worker)
                    logger.info(f"Worker {i} initialized successfully")
                else:
                    logger.error(f"Failed to initialize worker {i}")

            if not self.workers:
                logger.error("No workers initialized successfully")
                return False

            self.is_initialized = True
            logger.info(f"AI Service initialized with {len(self.workers)} workers")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize AI Service: {e}")
            return False

    def _get_available_worker(self) -> AIWorker | None:
        """Get an available worker from the pool."""
        for worker in self.workers:
            if worker.current_task is None:
                return worker
        return None

    async def _wait_for_worker(self, timeout: float = 30.0) -> AIWorker | None:
        """Wait for a worker to become available."""
        start_time = asyncio.get_event_loop().time()

        while True:
            worker = self._get_available_worker()
            if worker:
                return worker

            # Check timeout
            if asyncio.get_event_loop().time() - start_time > timeout:
                logger.warning("Timeout waiting for available worker")
                return None

            # Wait a bit before checking again
            await asyncio.sleep(0.1)

    async def generate_card_text(
        self,
        card_name: str,
        card_type: str,
        mana_cost: str = "",
        additional_context: dict[str, Any] | None = None,
    ) -> dict[str, str] | None:
        """
        Generate card text using AI.

        Args:
            card_name: Name of the card
            card_type: Type of the card
            mana_cost: Mana cost string
            additional_context: Additional context for generation

        Returns:
            Dictionary with generated text fields or None if failed
        """
        if not self.is_initialized:
            await self.initialize()

        worker = await self._wait_for_worker()
        if not worker:
            logger.error("No worker available for text generation")
            return None

        try:
            # Build enhanced prompt using prompt builder
            context = additional_context or {}
            enhanced_prompt = self.prompt_builder.build_card_text_prompt(
                card_name=card_name, card_type=card_type, mana_cost=mana_cost, **context
            )

            # Generate text using worker
            result = await worker.generate_card_text(
                card_name=card_name,
                card_type=card_type,
                mana_cost=mana_cost,
                prompt_enhancement=enhanced_prompt,
            )

            return result

        except Exception as e:
            logger.error(f"Text generation failed: {e}")
            return None

    async def generate_card_artwork(
        self,
        card: MTGCard,
        style: str = "mtg_modern",
        custom_prompt: str | None = None,
    ) -> Path | None:
        """
        Generate artwork for a card.

        Args:
            card: MTGCard instance
            style: Art style to use
            custom_prompt: Custom art prompt

        Returns:
            Path to generated artwork or None if failed
        """
        if not self.is_initialized:
            await self.initialize()

        worker = await self._wait_for_worker()
        if not worker:
            logger.error("No worker available for art generation")
            return None

        try:
            # Build art prompt if not provided
            if not custom_prompt:
                custom_prompt = self.prompt_builder.build_art_prompt(
                    card=card, style=style
                )

            # Generate artwork using worker
            result = await worker.generate_card_art(
                card=card, art_prompt=custom_prompt, style=style
            )

            return result

        except Exception as e:
            logger.error(f"Art generation failed: {e}")
            return None

    async def generate_complete_card(
        self,
        card_name: str,
        card_type: str,
        requirements: dict[str, Any] | None = None,
    ) -> MTGCard | None:
        """
        Generate a complete card with all fields.

        Args:
            card_name: Name of the card
            card_type: Type of the card
            requirements: Additional requirements and constraints

        Returns:
            Complete MTGCard instance or None if failed
        """
        if not self.is_initialized:
            await self.initialize()

        worker = await self._wait_for_worker()
        if not worker:
            logger.error("No worker available for complete card generation")
            return None

        try:
            # Generate complete card using worker
            result = await worker.generate_complete_card(
                card_name=card_name, card_type=card_type, **(requirements or {})
            )

            return result

        except Exception as e:
            logger.error(f"Complete card generation failed: {e}")
            return None

    async def batch_generate_cards(
        self,
        card_specifications: list[dict[str, Any]],
        max_concurrent: int | None = None,
    ) -> list[MTGCard]:
        """
        Generate multiple cards in batch.

        Args:
            card_specifications: List of card specifications
            max_concurrent: Maximum concurrent generations

        Returns:
            List of successfully generated cards
        """
        if not self.is_initialized:
            await self.initialize()

        max_concurrent = max_concurrent or len(self.workers)

        # Distribute cards across available workers
        chunk_size = max(1, len(card_specifications) // len(self.workers))
        tasks = []

        for i, worker in enumerate(self.workers):
            start_idx = i * chunk_size
            end_idx = (
                start_idx + chunk_size
                if i < len(self.workers) - 1
                else len(card_specifications)
            )

            if start_idx < len(card_specifications):
                worker_specs = card_specifications[start_idx:end_idx]
                task = worker.batch_generate_cards(
                    card_specs=worker_specs,
                    max_concurrent=max_concurrent // len(self.workers),
                )
                tasks.append(task)

        # Wait for all workers to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine results from all workers
        all_cards = []
        for result in results:
            if isinstance(result, list):
                all_cards.extend(result)

        logger.info(f"Batch generation completed: {len(all_cards)} cards generated")
        return all_cards

    def get_service_status(self) -> dict[str, Any]:
        """
        Get status of the AI service and all workers.

        Returns:
            Comprehensive status dictionary
        """
        worker_statuses = [worker.get_status() for worker in self.workers]

        return {
            "service_initialized": self.is_initialized,
            "total_workers": len(self.workers),
            "available_workers": len(
                [w for w in self.workers if w.current_task is None]
            ),
            "busy_workers": len(
                [w for w in self.workers if w.current_task is not None]
            ),
            "worker_details": worker_statuses,
            "prompt_builder_status": {
                "templates_loaded": len(self.prompt_builder.templates),
                "styles_available": list(self.prompt_builder.art_styles.keys()),
            },
        }

    async def optimize_generation_settings(
        self, feedback_data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Optimize generation settings based on feedback.

        Args:
            feedback_data: List of feedback entries with quality ratings

        Returns:
            Recommended settings adjustments
        """
        logger.info(f"Analyzing {len(feedback_data)} feedback entries for optimization")

        # Analyze feedback patterns
        quality_scores = [entry.get("quality_score", 0) for entry in feedback_data]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0

        # Generate recommendations based on analysis
        recommendations = {
            "current_avg_quality": avg_quality,
            "recommendations": [],
            "settings_adjustments": {},
        }

        if avg_quality < 7.0:  # Quality score out of 10
            recommendations["recommendations"].append(
                "Consider increasing generation steps for better quality"
            )
            recommendations["settings_adjustments"]["num_inference_steps"] = 50

        if avg_quality > 8.5:
            recommendations["recommendations"].append(
                "Quality is high - consider reducing steps for faster generation"
            )
            recommendations["settings_adjustments"]["num_inference_steps"] = 25

        logger.info(
            f"Generated {len(recommendations['recommendations'])} optimization recommendations"
        )
        return recommendations

    async def shutdown(self) -> None:
        """Shutdown the AI service and all workers."""
        logger.info("Shutting down AI Service...")

        # Shutdown all workers
        shutdown_tasks = [worker.shutdown() for worker in self.workers]
        await asyncio.gather(*shutdown_tasks, return_exceptions=True)

        self.workers.clear()
        self.is_initialized = False

        logger.info("AI Service shutdown complete")


# Singleton instance for global access
_ai_service_instance: AIService | None = None


def get_ai_service(config: dict[str, Any] | None = None, **kwargs) -> AIService:
    """
    Get the global AI service instance.

    Args:
        config: Configuration dictionary
        **kwargs: Additional initialization parameters

    Returns:
        AIService instance
    """
    global _ai_service_instance

    if _ai_service_instance is None:
        _ai_service_instance = AIService(config=config, **kwargs)

    return _ai_service_instance


async def initialize_ai_service(config: dict[str, Any] | None = None, **kwargs) -> bool:
    """
    Initialize the global AI service.

    Args:
        config: Configuration dictionary
        **kwargs: Additional initialization parameters

    Returns:
        True if initialization successful
    """
    service = get_ai_service(config=config, **kwargs)
    return await service.initialize()
