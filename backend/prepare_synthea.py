"""Download and prepare the Kaggle Synthea JSON dataset for RAG ingestion.

This project performs retrieval-augmented generation, not model fine-tuning.
"Training" means indexing the training split; the held-out test split is kept
out of Qdrant until it is evaluated.
"""
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

DATASET = "krsna540/synthea-dataset-jsons-ehr"
ROOT = Path(__file__).parent
RAW_DIR = ROOT / "data" / "raw" / "synthea"
MANIFEST = ROOT / "data" / "processed" / "synthea_manifest.jsonl"


def display(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("text") or value.get("display") or value.get("code") or "")
    if isinstance(value, list):
        return ", ".join(filter(None, (display(item) for item in value)))
    return str(value or "")


def resource_summary(resource: Dict[str, Any]) -> str:
    kind = resource.get("resourceType", "Record")
    values = []
    for field in ("status", "code", "type", "category", "description", "clinicalStatus", "value", "unit", "effectiveDateTime", "issued", "authoredOn", "recordedDate", "onsetDateTime", "start", "end", "dosageInstruction", "reasonCode"):
        value = display(resource.get(field))
        if value:
            values.append(f"{field}: {value}")
    return f"{kind}: " + "; ".join(values)


def patient_id(resource: Dict[str, Any], fallback: str) -> str:
    for identifier in resource.get("identifier", []):
        value = identifier.get("value") if isinstance(identifier, dict) else None
        if value:
            return str(value).upper()
    return str(resource.get("id") or fallback).upper()


def records_from_bundle(data: Dict[str, Any], filename: str) -> Iterable[Dict[str, str]]:
    entries = data.get("entry", []) if data.get("resourceType") == "Bundle" else []
    resources = [entry.get("resource", {}) for entry in entries if isinstance(entry, dict)]
    patient = next((r for r in resources if r.get("resourceType") == "Patient"), {})
    if not patient:
        return
    pid = patient_id(patient, Path(filename).stem)
    name = display(patient.get("name"))
    demographics = f"Patient ID: {pid}. Name: {name}. Birth date: {patient.get('birthDate', '')}. Gender: {patient.get('gender', '')}."
    details = [resource_summary(resource) for resource in resources if resource.get("resourceType") != "Patient"]
    text = "\n".join([demographics] + [line for line in details if line != "Record: "])
    yield {"patient_id": pid, "filename": filename, "text": text}


def records_from_json(data: Any, filename: str) -> Iterable[Dict[str, str]]:
    if isinstance(data, dict) and data.get("resourceType") == "Bundle":
        yield from records_from_bundle(data, filename)
        return
    patients = data.get("patients") if isinstance(data, dict) else None
    if isinstance(patients, list):
        for index, patient in enumerate(patients):
            if not isinstance(patient, dict):
                continue
            pid = patient_id(patient, f"{Path(filename).stem}-{index}")
            yield {"patient_id": pid, "filename": filename, "text": json.dumps(patient, ensure_ascii=False)}
        return
    if isinstance(data, dict):
        pid = patient_id(data, Path(filename).stem)
        yield {"patient_id": pid, "filename": filename, "text": json.dumps(data, ensure_ascii=False)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true", help="Download the 2.17 GB Kaggle dataset first.")
    parser.add_argument(
        "--source-dir",
        type=Path,
        help="Directory containing extracted Synthea JSON files. Defaults to data/raw/synthea.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Path for the generated JSONL manifest. Defaults to data/processed/synthea_manifest.jsonl.",
    )
    parser.add_argument("--max-patients", type=int, default=0, help="0 prepares every patient.")
    args = parser.parse_args()
    if args.download:
        import kagglehub
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        print(kagglehub.dataset_download(DATASET, output_dir=str(RAW_DIR)))
    source_dir = args.source_dir or RAW_DIR
    manifest_path = args.output or MANIFEST
    files = sorted(source_dir.rglob("*.json"))
    if not files:
        raise SystemExit(f"No JSON files found in {source_dir}. Download and extract the dataset first.")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with manifest_path.open("w", encoding="utf-8") as out:
        for file in files:
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                continue
            for record in records_from_json(data, str(file.relative_to(source_dir))):
                split = "test" if int(hashlib.sha256(record["patient_id"].encode()).hexdigest(), 16) % 5 == 0 else "train"
                record["split"] = split
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1
                if args.max_patients and count >= args.max_patients:
                    break
            if args.max_patients and count >= args.max_patients:
                break
    print(f"Prepared {count} patient records at {manifest_path}")


if __name__ == "__main__":
    main()
