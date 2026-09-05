import logging
from typing import List

from app.config import settings
from app.openrouter_client import get_openrouter_client
from app.openrouter_utils import call_openrouter_with_retry

logger = logging.getLogger("medical_rag.embeddings")

def get_mistral_client():
    """Backward compatibility alias returning OpenRouter client."""
    return get_openrouter_client()

def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate vector embeddings for a list of text strings using OpenRouter with retry logic."""
    client = get_openrouter_client()
    try:
        cleaned_texts = [text.replace("\n", " ") for text in texts]
        response = call_openrouter_with_retry(
            lambda: client.embeddings.create(
                input=cleaned_texts,
                model=settings.EMBEDDING_MODEL
            )
        )
        return [data.embedding for data in response.data]
    except Exception as e:
        logger.error(f"Failed to generate embeddings via OpenRouter: {e}")
        raise e

def get_single_embedding(text: str) -> List[float]:
    """Generate single vector embedding for query string."""
    return get_embeddings([text])[0]
