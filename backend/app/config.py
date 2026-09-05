import os
from pathlib import Path
from dotenv import load_dotenv

app_dir = Path(__file__).parent
backend_dir = app_dir.parent
load_dotenv(dotenv_path=backend_dir / ".env")
load_dotenv(dotenv_path=app_dir / ".env")
load_dotenv()

class Settings:
    # --- LLM Provider: OpenRouter (OpenAI-compatible) ---
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY") or os.getenv("MISTRAL_API_KEY") or ""

    # --- Qdrant Vector Database ---
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")
    # Set QDRANT_URL=local to use Qdrant's embedded, file-backed mode.
    QDRANT_PATH: str = os.getenv("QDRANT_PATH", "qdrant_storage")
    QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "medical_records_openrouter")

    # --- LLM Models (OpenRouter models) ---
    PRIMARY_LLM_MODEL: str = os.getenv("PRIMARY_LLM_MODEL", "meta-llama/llama-3.2-3b-instruct")
    VERIFIER_LLM_MODEL: str = os.getenv("VERIFIER_LLM_MODEL", "meta-llama/llama-3.2-3b-instruct")

    # --- Embeddings ---
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")
    EMBEDDING_VECTOR_SIZE: int = int(os.getenv("EMBEDDING_VECTOR_SIZE", "1536"))

    # --- OpenRouter API base URL ---
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

settings = Settings()

