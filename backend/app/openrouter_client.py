import os
import logging
from typing import Optional
from openai import OpenAI

from app.config import settings

logger = logging.getLogger("medical_rag.openrouter_client")

_openrouter_client_instance: Optional[OpenAI] = None

def get_openrouter_client() -> OpenAI:
    """Initialize and return singleton OpenAI client configured for OpenRouter API."""
    global _openrouter_client_instance
    if _openrouter_client_instance is None:
        api_key = settings.OPENROUTER_API_KEY
        if not api_key:
            raise ValueError(
                "OPENROUTER_API_KEY environment variable is missing. "
                "Please set OPENROUTER_API_KEY in your environment or .env file."
            )
        
        headers = {
            "HTTP-Referer": "https://github.com/medical-rag",
            "X-Title": "Medical RAG Clinical Platform"
        }
        
        _openrouter_client_instance = OpenAI(
            base_url=settings.OPENROUTER_BASE_URL,
            api_key=api_key,
            default_headers=headers
        )
        logger.info(f"OpenRouter API client initialized (Base URL: {settings.OPENROUTER_BASE_URL}).")
        
    return _openrouter_client_instance
