import sys
import logging
from app.qdrant_client import (
    close_qdrant_client,
    get_qdrant_client,
    init_qdrant_collection,
)
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def main():
    print("============================================")
    print("   Medical RAG - Qdrant Setup Script        ")
    print("============================================")
    print(f"Qdrant URL: {settings.QDRANT_URL}")
    print(f"Target Collection: {settings.QDRANT_COLLECTION}")
    print(f"Vector Dimensions: {settings.EMBEDDING_VECTOR_SIZE}")
    print("--------------------------------------------")

    exit_code = 0
    try:
        client = get_qdrant_client()
        collections_res = client.get_collections()
        print(f"[+] Connected to Qdrant server. Found {len(collections_res.collections)} collections.")
        
        success = init_qdrant_collection()
        if success:
            print(f"[OK] Collection '{settings.QDRANT_COLLECTION}' is ready with payload index for 'patient_id'.")
        else:
            print("[X] Failed to setup collection.")
            exit_code = 1
    except Exception as e:
        print(f"[X] Connection Error: Could not connect to Qdrant at {settings.QDRANT_URL}.")
        print(f"    Ensure Qdrant Docker container is running: docker run -p 6333:6333 qdrant/qdrant")
        print(f"    Error details: {e}")
        exit_code = 1
    finally:
        close_qdrant_client()

    if exit_code:
        sys.exit(exit_code)

if __name__ == "__main__":
    main()
