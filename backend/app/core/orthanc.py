"""
Singleton Orthanc client for interacting with Orthanc DICOM server.
This module provides a centralized client that can be used throughout the backend.
"""

import logging
from typing import Optional

import httpx
from pyorthanc import Orthanc

from app.core.config import settings

logger = logging.getLogger(__name__)


class OrthancClient:
    """
    Singleton Orthanc client for interacting with the Orthanc DICOM server.
    Provides access to pyorthanc and httpx clients for Orthanc operations.
    """

    _instance: Optional["OrthancClient"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OrthancClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the Orthanc client if it hasn't been initialized yet."""
        if hasattr(self, "_initialized") and self._initialized:
            return

        # Initialize the pyorthanc client
        self._client = Orthanc(
            settings.ORTHANC_URL,
            username=settings.ORTHANC_USERNAME,
            password=settings.ORTHANC_PASSWORD,
        )

        # Keep an httpx client for direct API access (bypassing pyorthanc when needed)
        self._http_client = httpx.AsyncClient(
            base_url=settings.ORTHANC_URL,
            auth=(settings.ORTHANC_USERNAME, settings.ORTHANC_PASSWORD)
            if settings.ORTHANC_USERNAME
            else None,
        )

        self._initialized = True
        logger.info(f"Initialized Orthanc client connected to {settings.ORTHANC_URL}")

    @property
    def client(self) -> Orthanc:
        """Get the underlying pyorthanc client instance."""
        return self._client

    @property
    def http_client(self) -> httpx.AsyncClient:
        """Get the httpx client for direct API access."""
        return self._http_client

    async def close(self):
        """Close the httpx client when shutting down."""
        if hasattr(self, "_http_client"):
            await self._http_client.aclose()
            logger.info("Closed Orthanc HTTP client")


# Create a singleton instance to be used throughout the application
orthanc_client = OrthancClient()
