"""Compatibility module forwarding mistral_utils to openrouter_utils."""
from app.openrouter_utils import call_openrouter_with_retry as call_mistral_with_retry
from app.openrouter_utils import call_openrouter_with_retry

__all__ = ["call_mistral_with_retry", "call_openrouter_with_retry"]
