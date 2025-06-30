"""Domain interfaces for configuration access.

This module provides interfaces that domain services can use to access
configuration without depending on infrastructure implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ConfigurationInterface(ABC):
    """Interface for accessing application configuration.

    This interface allows domain services to access configuration
    without depending on infrastructure configuration implementations.
    """

    @abstractmethod
    def get_api_key(self, service: str) -> str:
        """Get API key for a specific service.

        Args:
            service: Name of the service (e.g., 'gemini', 'openai')

        Returns:
            API key for the service or empty string if not configured
        """
        pass

    @abstractmethod
    def get_project_id(self) -> str:
        """Get GCP project ID.

        Returns:
            GCP project ID or empty string if not configured
        """
        pass

    @abstractmethod
    def get_region(self) -> str:
        """Get GCP region.

        Returns:
            GCP region (default: us-central1)
        """
        pass

    @abstractmethod
    def get_model_name(self, service: str) -> str:
        """Get model name for a specific service.

        Args:
            service: Name of the service (e.g., 'gemini')

        Returns:
            Model name or default model for the service
        """
        pass

    @abstractmethod
    def get_credentials_path(self) -> str:
        """Get path to service account credentials.

        Returns:
            Path to credentials file or empty string if not configured
        """
        pass

    @abstractmethod
    def use_vertex_ai(self) -> bool:
        """Check if Vertex AI should be used instead of direct API.

        Returns:
            True if Vertex AI should be used, False for direct API
        """
        pass

    @abstractmethod
    def has_service_config(self, service: str) -> bool:
        """Check if configuration is available for a service.

        Args:
            service: Name of the service (e.g., 'gemini')

        Returns:
            True if service is properly configured, False otherwise
        """
        pass

    @abstractmethod
    def get_database_path(self) -> str:
        """Get database file path.

        Returns:
            Path to SQLite database file
        """
        pass

    @abstractmethod
    def get_questions_data_path(self) -> str:
        """Get path to questions dataset.

        Returns:
            Path to questions JSON file
        """
        pass


class APIConfigurationInterface(ABC):
    """Specialized interface for AI service configuration.

    This interface provides a simplified view for domain services
    that need to interact with AI services like Gemini.
    """

    @abstractmethod
    def is_gemini_available(self) -> bool:
        """Check if Gemini API is available and configured.

        Returns:
            True if Gemini can be used, False otherwise
        """
        pass

    @abstractmethod
    def get_gemini_config(self) -> dict[str, Any]:
        """Get Gemini configuration for API calls.

        Returns:
            Dictionary with Gemini configuration parameters
            Empty dict if not configured
        """
        pass

    @abstractmethod
    def is_developer_mode_required(self) -> bool:
        """Check if developer mode is required for API access.

        Returns:
            True if developer mode must be enabled for API calls
        """
        pass
