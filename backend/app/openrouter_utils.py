"""OpenRouter API Call Utilities with Exponential Backoff & Rate-Limit (HTTP 429 / 5xx) Handling."""
import time
import random
import logging
from typing import Callable, Any

logger = logging.getLogger("medical_rag.openrouter")

def call_openrouter_with_retry(func: Callable[[], Any], max_retries: int = 6, initial_delay: float = 3.0) -> Any:
    """Execute an OpenRouter API call with automatic exponential backoff on 429 Rate Limit or transient 5xx errors."""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            err_str = str(e).lower()
            is_rate_limit_or_transient = (
                "429" in err_str
                or "rate limit" in err_str
                or "too many requests" in err_str
                or "quota" in err_str
                or "502" in err_str
                or "503" in err_str
                or "504" in err_str
                or "overloaded" in err_str
            )

            if is_rate_limit_or_transient and attempt < max_retries - 1:
                # Try to extract Retry-After value from error string if present
                retry_after = None
                for part in str(e).split():
                    try:
                        val = float(part)
                        if 1 <= val <= 120:
                            retry_after = val
                            break
                    except ValueError:
                        continue

                if retry_after:
                    sleep_time = retry_after + random.uniform(0.5, 2.0)
                else:
                    sleep_time = min(initial_delay * (2 ** attempt), 60.0) + random.uniform(0.5, 2.0)

                logger.warning(
                    f"OpenRouter transient error / rate limit hit ({e}). Backing off {sleep_time:.1f}s... "
                    f"(Attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(sleep_time)
                continue

            if is_rate_limit_or_transient:
                logger.error("OpenRouter API rate limit exceeded after %d retries.", max_retries)
                raise RuntimeError(
                    f"OpenRouter API rate limit or service busy after {max_retries} retries: {e}. "
                    "Please wait a few moments and try again."
                ) from e

            raise e
