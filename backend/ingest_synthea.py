"""Embed and ingest prepared Synthea patient splits into the Qdrant vector database."""
import argparse
import json
import time
import uuid
from pathlib import Path

from qdrant_client.http.models import PointStruct
from app.document_processor import chunk_text
from app.embeddings import get_embeddings
from app.qdrant_client import init_qdrant_collection, store_chunks_in_qdrant

MANIFEST = Path(__file__).parent / "data" / "processed" / "synthea_manifest.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Synthea dataset split into Qdrant vector collection")
    parser.add_argument("--split", choices=("train", "test"), default="train", help="Dataset split to ingest")
    parser.add_argument("--limit", type=int, default=25, help="Number of patients to ingest (0 = all)")
    parser.add_argument("--batch-size", type=int, default=32, help="Embedding batch size")
    args = parser.parse_args()

    if not MANIFEST.exists():
        raise SystemExit("Dataset manifest is missing. Run prepare_synthea.py or check data/processed/")

    print(f"Loading Synthea manifest from: {MANIFEST}...")
    records = [json.loads(line) for line in MANIFEST.read_text(encoding="utf-8").splitlines() if line.strip()]
    records = [r for r in records if r.get("split") == args.split]

    total_available = len(records)
    if args.limit and args.limit > 0:
        records = records[:args.limit]

    print(f"Selected {len(records)} patients from '{args.split}' split (out of {total_available} available).")
    
    init_qdrant_collection()
    
    total_stored = 0
    start_time = time.time()

    for idx, record in enumerate(records, 1):
        pid = record["patient_id"]
        filename = record.get("filename", f"{pid}.json")
        pages = [{"page": 1, "text": record["text"], "filename": filename, "document_type": "Synthea EHR JSON"}]
        chunks = chunk_text(pages, pid)

        if not chunks:
            continue

        for start in range(0, len(chunks), args.batch_size):
            batch = chunks[start : start + args.batch_size]
            texts = [c["text"] for c in batch]
            
            try:
                vectors = get_embeddings(texts)
                points = [
                    PointStruct(
                        id=str(uuid.uuid4()),
                        vector=vector,
                        payload=chunk
                    )
                    for chunk, vector in zip(batch, vectors)
                ]
                store_chunks_in_qdrant(points)
                total_stored += len(points)
            except Exception as e:
                print(f"[X] Error embedding/upserting batch for patient {pid}: {e}")
                time.sleep(1)

        if idx % 5 == 0 or idx == len(records):
            elapsed = time.time() - start_time
            print(f"[{idx}/{len(records)}] Ingested patient {pid} -> Total chunks indexed: {total_stored} ({elapsed:.1f}s)")

    print(f"[OK] Ingestion finished! Indexed {total_stored} chunks across {len(records)} patients from split '{args.split}'.")


if __name__ == "__main__":
    main()
