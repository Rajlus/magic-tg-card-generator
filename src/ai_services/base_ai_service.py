"""
Base AI Service class for MTG card generation.

This module provides the base AIService class that handles common AI API functionality.
"""

import json
import os
from abc import ABC, abstractmethod
from typing import Any, Optional

import requests


class AIService(ABC):
    """Base class for AI services with OpenRouter API integration."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        """
        Initialize AI service with API configuration.

        Args:
            api_key: OpenRouter API key (defaults to env variable)
            model: AI model to use (defaults to openai/gpt-oss-120b)
        """
        self.api_key = api_key or os.getenv(
            "OPENROUTER_API_KEY",
            "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",
        )
        self.model = model or "openai/gpt-oss-120b"
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this AI service."""
        pass

    def get_default_parameters(self, task_type: str) -> dict[str, Any]:
        """
        Get default parameters for AI API calls based on task type.

        Args:
            task_type: Type of task being performed

        Returns:
            Dictionary of default parameters
        """
        task_params = {
            "generate_cards": {"temperature": 0.7, "max_tokens": 32000, "timeout": 120},
            "analyze_theme": {"temperature": 0.7, "max_tokens": 4000, "timeout": 60},
            "generate_art": {"temperature": 0.8, "max_tokens": 4000, "timeout": 60},
        }
        return task_params.get(
            task_type, {"temperature": 0.7, "max_tokens": 4000, "timeout": 60}
        )

    def make_api_call(
        self,
        prompt: str,
        task_type: str = "default",
        progress_callback=None,
        log_callback=None,
    ) -> str:
        """
        Make an API call to the AI service.

        Args:
            prompt: User prompt to send
            task_type: Type of task for parameter selection
            progress_callback: Optional callback for progress updates
            log_callback: Optional callback for logging

        Returns:
            AI response content

        Raises:
            requests.RequestException: If API call fails
            ValueError: If response is invalid
        """
        # Get parameters for this task type
        params = self.get_default_parameters(task_type)

        # Log AI call parameters
        if log_callback:
            log_callback("GENERATING", f"AI Call: {task_type}")
            log_callback(
                "DEBUG",
                f"Parameters: model={self.model}, max_tokens={params['max_tokens']}, "
                f"temperature={params['temperature']}, timeout={params['timeout']}s",
            )

        if progress_callback:
            progress_callback(f"Calling {self.model}...")

        # Prepare request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        # Log request size
        request_size = len(json.dumps(messages))
        if log_callback:
            log_callback("DEBUG", f"Request size: {request_size} characters")

        # Make API call
        response = requests.post(
            self.base_url,
            headers=headers,
            json={
                "model": self.model,
                "messages": messages,
                "temperature": params["temperature"],
                "max_tokens": params["max_tokens"],
            },
            timeout=params["timeout"],
        )

        # Handle response
        if response.status_code != 200:
            error_msg = f"API Error {response.status_code}: {response.text}"
            if log_callback:
                log_callback("ERROR", error_msg)
            raise requests.RequestException(error_msg)

        try:
            response_data = response.json()
            content = response_data["choices"][0]["message"]["content"]

            # Log success
            if log_callback:
                response_size = len(content)
                log_callback(
                    "SUCCESS", f"Response received: {response_size} characters"
                )

            return content

        except (KeyError, IndexError, json.JSONDecodeError) as e:
            error_msg = f"Invalid API response format: {str(e)}"
            if log_callback:
                log_callback("ERROR", error_msg)
            raise ValueError(error_msg) from e
