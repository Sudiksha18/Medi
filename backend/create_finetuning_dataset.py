"""Generate fine-tuning instruction datasets from Synthea EHR records.

Creates grounded question-answering training and validation pairs with:
1. Positive answerable pairs: answers strictly derived from record excerpts with citations.
2. Negative unanswerable pairs: queries about absent data requiring exact abstention
   "Information not found in medical records."
Compatible with Hugging Face SFTTrainer, Mistral fine-tuning, and OpenAI fine-tuning formats.
"""
import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path(__file__).parent
MANIFEST = ROOT / "data" / "processed" / "synthea_manifest.jsonl"
OUTPUT_DIR = ROOT / "data" / "processed"

SYSTEM_PROMPT = (
    "You are a strict, precise Medical RAG AI Assistant. Your task is to answer questions about a "
    "patient's medical records based EXCLUSIVELY on the provided document excerpts.\n\n"
    "CRITICAL RULES:\n"
    "1. Rely ONLY on the provided Context excerpts below. NEVER use general medical knowledge or assumptions.\n"
    "2. If the answer cannot be found or directly inferred from the provided context, respond EXACTLY with: "
    "\"Information not found in medical records.\"\n"
    "3. Never mix data from other patients or fabricate medical metrics, diagnoses, or prescriptions.\n"
    "4. For every statement you make, cite the source using: [Source 1: <filename>, Page 1].\n"
    "5. Keep your answer factual, professional, clear, and direct."
)

ABSTENTION_ANSWER = "Information not found in medical records."

UNANSWERABLE_QUESTIONS = [
    "What is the patient's blood type and Rh factor?",
    "What was the MRI brain scan result from last month?",
    "What was the dosage prescribed for Amoxicillin?",
    "What is the patient's genetic test result for BRCA1?",
    "What was the patient's COVID-19 antibody titer level?",
    "Has the patient undergone a coronary artery bypass graft (CABG)?",
    "What is the patient's psychiatric evaluation summary?",
    "What is the family history of Huntington's disease?",
    "What was the result of the patient's latest echocardiogram ejection fraction?",
    "Does the patient have documented allergies to penicillin or cephalosporins?"
]


def extract_specific_claims(text: str) -> List[Dict[str, str]]:
    """Extract factual question-answer candidate pairs from EHR text lines."""
    pairs = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    # Demographics line is usually line 0
    demographics = lines[0] if lines else ""
    
    for line in lines[1:]:
        if line.startswith("Condition:") and "clinicalStatus:" in line:
            pairs.append({
                "question": "What medical conditions or diagnoses are recorded for this patient?",
                "excerpt": line,
                "answer": f"The medical record documents: {line} [Source 1: patient_record.json, Page 1]"
            })
        elif line.startswith("Observation:") and "effectiveDateTime:" in line:
            pairs.append({
                "question": "What observation and clinical measurements are documented in the records?",
                "excerpt": line,
                "answer": f"The record documents the following clinical observation: {line} [Source 1: patient_record.json, Page 1]"
            })
        elif line.startswith("Procedure:") and "code:" in line:
            pairs.append({
                "question": "What medical procedures has the patient undergone?",
                "excerpt": line,
                "answer": f"The record indicates the following completed procedure: {line} [Source 1: patient_record.json, Page 1]"
            })
        elif line.startswith("Immunization:") and "status:" in line:
            pairs.append({
                "question": "What immunization history is recorded for this patient?",
                "excerpt": line,
                "answer": f"The immunization record states: {line} [Source 1: patient_record.json, Page 1]"
            })
        elif line.startswith("MedicationRequest:") or "Medication" in line:
            pairs.append({
                "question": "What medication requests or active prescriptions are in the patient's file?",
                "excerpt": line,
                "answer": f"The record specifies the medication entry: {line} [Source 1: patient_record.json, Page 1]"
            })
        elif line.startswith("CarePlan:"):
            pairs.append({
                "question": "What care plans are documented for the patient?",
                "excerpt": line,
                "answer": f"The record documents the care plan status: {line} [Source 1: patient_record.json, Page 1]"
            })
        elif line.startswith("DiagnosticReport:"):
            pairs.append({
                "question": "What diagnostic reports are available in the patient record?",
                "excerpt": line,
                "answer": f"The record lists the diagnostic report: {line} [Source 1: patient_record.json, Page 1]"
            })
            
    if not pairs and len(lines) > 1:
        # Fallback to general line excerpt
        sample_line = lines[1]
        pairs.append({
            "question": "What clinical encounters or events are documented in the record?",
            "excerpt": sample_line,
            "answer": f"The record states: {sample_line} [Source 1: patient_record.json, Page 1]"
        })
        
    return pairs


def build_chat_example(patient_id: str, filename: str, context_excerpt: str, question: str, answer: str) -> Dict[str, Any]:
    """Format single sample into standard Chat Completion message format."""
    clean_filename = Path(filename).name if filename else "record.json"
    user_prompt = (
        f"PATIENT ID: {patient_id}\n\n"
        f"PROVIDED MEDICAL RECORD CONTEXT:\n"
        f"--- Source 1: {clean_filename} (Page 1) ---\n"
        f"{context_excerpt}\n\n"
        f"USER QUESTION: {question}\n\n"
        f"Provide your factual answer with inline source citations [Source N: filename, Page X]. "
        f"If the answer is not present in the context above, output \"Information not found in medical records.\"."
    )
    
    # Standard ChatML / OpenAI / Mistral message structure
    return {
        "patient_id": patient_id,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": answer}
        ]
    }


def main():
    parser = argparse.ArgumentParser(description="Create fine-tuning datasets from Synthea manifest")
    parser.add_argument("--manifest", type=Path, default=MANIFEST, help="Path to synthea_manifest.jsonl")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="Output directory for SFT JSONL files")
    parser.add_argument("--max-train", type=int, default=2000, help="Maximum training examples to generate")
    parser.add_argument("--max-val", type=int, default=400, help="Maximum validation examples to generate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    random.seed(args.seed)

    if not args.manifest.exists():
        raise SystemExit(f"Manifest not found at {args.manifest}. Please ensure dataset is prepared.")

    print(f"Reading dataset from {args.manifest}...")
    records = []
    with args.manifest.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    train_records = [r for r in records if r.get("split") == "train"]
    val_records = [r for r in records if r.get("split") == "test"]

    print(f"Loaded {len(train_records)} train patients and {len(val_records)} test patients.")

    def process_split(split_records: List[Dict[str, Any]], max_count: int) -> List[Dict[str, Any]]:
        dataset = []
        for r in split_records:
            pid = r["patient_id"]
            filename = r.get("filename", "patient_record.json")
            text = r["text"]
            
            # Deterministic pseudo-random selection
            hash_val = int(hashlib.sha256(pid.encode()).hexdigest(), 16)
            is_answerable = (hash_val % 2 == 0)
            
            candidates = extract_specific_claims(text)
            if not candidates:
                continue
                
            chosen = candidates[hash_val % len(candidates)]
            lines = [x.strip() for x in text.splitlines() if x.strip()]
            demographics = lines[0] if lines else f"Patient ID: {pid}"
            context_excerpt = f"{demographics}\n{chosen['excerpt']}"
            
            if is_answerable:
                clean_filename = Path(filename).name
                answer = chosen["answer"].replace("patient_record.json", clean_filename)
                item = build_chat_example(pid, filename, context_excerpt, chosen["question"], answer)
            else:
                unanswerable_q = UNANSWERABLE_QUESTIONS[hash_val % len(UNANSWERABLE_QUESTIONS)]
                item = build_chat_example(pid, filename, context_excerpt, unanswerable_q, ABSTENTION_ANSWER)
                
            dataset.append(item)
            if max_count and len(dataset) >= max_count:
                break
                
        return dataset

    train_dataset = process_split(train_records, args.max_train)
    val_dataset = process_split(val_records, args.max_val)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    train_out = args.output_dir / "train_sft.jsonl"
    val_out = args.output_dir / "val_sft.jsonl"

    with train_out.open("w", encoding="utf-8") as f:
        for item in train_dataset:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    with val_out.open("w", encoding="utf-8") as f:
        for item in val_dataset:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"Generated {len(train_dataset)} training examples -> {train_out}")
    print(f"Generated {len(val_dataset)} validation examples -> {val_out}")
    print("Dataset preparation complete.")


if __name__ == "__main__":
    main()
