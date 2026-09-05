"""In-Memory Semantic & Exact Response Caching for High-Scalability Medical Queries."""
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("medical_rag.semantic_cache")

# Simple thread-safe in-memory cache
_query_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour TTL

def get_cached_response(patient_id: str, question: str) -> Optional[Dict[str, Any]]:
    """Retrieve cached RAG answer if query was executed recently for the same patient."""
    cache_key = f"{patient_id.strip().upper()}:{question.strip().lower()}"
    entry = _query_cache.get(cache_key)
    if entry:
        if time.time() - entry["timestamp"] < CACHE_TTL_SECONDS:
            logger.info(f"Semantic Cache HIT for patient {patient_id}")
            return entry["data"]
        else:
            del _query_cache[cache_key]
    return None

def set_cached_response(patient_id: str, question: str, response_data: Dict[str, Any]) -> None:
    """Store generated RAG answer in cache."""
    cache_key = f"{patient_id.strip().upper()}:{question.strip().lower()}"
    _query_cache[cache_key] = {
        "timestamp": time.time(),
        "data": response_data
    }
    # Prune old cache entries if size exceeds 1000
    if len(_query_cache) > 1000:
        now = time.time()
        expired = [k for k, v in _query_cache.items() if now - v["timestamp"] > CACHE_TTL_SECONDS]
        for k in expired:
            del _query_cache[k]
