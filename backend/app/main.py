import time
import uuid
import logging
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from qdrant_client.http.models import PointStruct

from app.config import settings
from app.qdrant_client import (
    close_qdrant_client,
    init_qdrant_collection,
    store_chunks_in_qdrant,
    get_all_patients_from_qdrant,
    get_qdrant_client,
    delete_patient_from_qdrant,
    clear_all_patients_from_qdrant,
    get_patient_documents_summary
)
from app.document_processor import (
    extract_text_from_pdf,
    extract_text_from_image,
    extract_text_from_plaintext,
    chunk_text
)
from app.embeddings import get_embeddings
from app.rag_chain import generate_rag_answer
from app.verifier import verify_answer
from app.phi_sanitizer import sanitize_phi
from app.audit_logger import log_interaction, record_feedback, get_audit_summary
from app.clinical_analytics import (
    extract_lab_trends,
    extract_patient_timeline,
    generate_clinical_summary,
    check_drug_safety
)
from app.clinical_calculators import compute_patient_risk_profile
from app.fhir_exporter import export_patient_fhir_bundle
from app.semantic_cache import get_cached_response, set_cached_response

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger("medical_rag.main")

app = FastAPI(
    title="Medical RAG Clinical Platform API",
    description="Patient-isolated document vector search, dual-LLM verification, clinical analytics & audit logging.",
    version="2.0.0"
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    """Initialize Qdrant database collection on startup."""
    logger.info("Initializing Medical RAG API...")
    init_qdrant_collection()


@app.on_event("shutdown")
def shutdown_event():
    """Release embedded-Qdrant resources before Python begins shutdown."""
    close_qdrant_client()

# Request & Response Schemas
class CreatePatientRequest(BaseModel):
    patient_id: str = Field(..., example="PATIENT-1001", description="Unique Patient Identifier")
    name: Optional[str] = None

class ChatRequest(BaseModel):
    patient_id: str = Field(..., example="PATIENT-1001")
    question: str = Field(..., example="What were the patient's lab results and blood pressure readings?")

class SourceItem(BaseModel):
    source_id: int
    filename: str
    page: int
    score: float
    vector_score: Optional[float] = None
    lexical_score: Optional[float] = None
    text: str
    document_type: str

class VerificationResult(BaseModel):
    status: str  # "VERIFIED" or "NEEDS_REVIEW"
    confidence_score: float
    reasoning: str
    flagged_claims: List[str]

class ChatResponse(BaseModel):
    patient_id: str
    question: str
    answer: str
    sources: List[SourceItem]
    verification: VerificationResult
    audit_id: Optional[str] = None
    latency_sec: Optional[float] = None

class FeedbackRequest(BaseModel):
    audit_id: str
    rating: str  # "THUMBS_UP" or "THUMBS_DOWN"
    comment: Optional[str] = None

class SafetyCheckRequest(BaseModel):
    proposed_drug: str

@app.get("/api/health")
def health_check():
    """Health check endpoint checking Qdrant connectivity."""
    qdrant_ok = False
    try:
        get_qdrant_client().get_collections()
        qdrant_ok = True
    except Exception as e:
        logger.warning(f"Qdrant health check warning: {e}")

    return {
        "status": "online",
        "qdrant_connected": qdrant_ok,
        "primary_model": settings.PRIMARY_LLM_MODEL,
        "verifier_model": settings.VERIFIER_LLM_MODEL,
        "collection": settings.QDRANT_COLLECTION,
        "version": "2.0.0"
    }

# --- Patient Management Endpoints ---

@app.get("/api/patients")
def list_patients():
    """Retrieve list of registered patient IDs in Qdrant."""
    patient_ids = get_all_patients_from_qdrant()
    return {"patients": patient_ids}

@app.post("/api/patients")
def create_patient(payload: CreatePatientRequest):
    """Register/Select a patient ID."""
    clean_id = payload.patient_id.strip().upper()
    if not clean_id:
        raise HTTPException(status_code=400, detail="Patient ID cannot be empty.")
    return {"patient_id": clean_id, "message": f"Patient profile {clean_id} active."}

@app.delete("/api/patients")
def clear_all_patients():
    """Clear and purge all patient vector records from Qdrant."""
    success = clear_all_patients_from_qdrant()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to clear patient records from Qdrant.")
    return {"status": "success", "message": "All patient records cleared successfully."}

@app.delete("/api/patients/{patient_id}")
def delete_patient(patient_id: str):
    """Delete a specific patient and their document chunks from Qdrant."""
    clean_id = patient_id.strip().upper()
    success = delete_patient_from_qdrant(clean_id)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to delete records for patient {clean_id}.")
    return {"status": "success", "patient_id": clean_id, "message": f"Patient {clean_id} deleted."}

@app.get("/api/patient/{patient_id}/documents")
def get_patient_documents(patient_id: str):
    """Retrieve list of uploaded documents and index stats for a patient."""
    clean_id = patient_id.strip().upper()
    return get_patient_documents_summary(clean_id)

# --- Document Upload & Ingestion ---

@app.post("/api/upload")
async def upload_patient_documents(
    patient_id: str = Form(...),
    files: List[UploadFile] = File(...)
):
    """Process uploaded PDF, image, and plain-text records with PHI de-identification."""
    clean_patient_id = patient_id.strip().upper()
    if not clean_patient_id:
        raise HTTPException(status_code=400, detail="Patient ID is required.")
    
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")
        
    all_chunks = []
    processed_files = []
    phi_redaction_summary = {}

    for file in files:
        filename = file.filename
        content_type = file.content_type or ""
        file_bytes = await file.read()
        
        pages_data = []
        if filename.lower().endswith(".pdf") or "pdf" in content_type:
            pages_data = extract_text_from_pdf(file_bytes, filename)
        elif filename.lower().endswith(".txt") or content_type.startswith("text/plain"):
            pages_data = extract_text_from_plaintext(file_bytes, filename)
        elif any(filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".tiff", ".bmp"]) or "image" in content_type:
            pages_data = extract_text_from_image(file_bytes, filename)
        else:
            logger.warning(f"Skipping unsupported file type: {filename}")
            continue

        if pages_data:
            # Apply HIPAA PHI Sanitization
            sanitized_pages = []
            for p in pages_data:
                sanitized_text, red_counts = sanitize_phi(p["text"])
                for k, v in red_counts.items():
                    phi_redaction_summary[k] = phi_redaction_summary.get(k, 0) + v
                sanitized_pages.append({**p, "text": sanitized_text})
                
            chunks = chunk_text(sanitized_pages, patient_id=clean_patient_id)
            all_chunks.extend(chunks)
            processed_files.append(filename)

    if not all_chunks:
        raise HTTPException(status_code=400, detail="No readable text could be extracted from uploaded files.")

    # Generate Embeddings in batch
    chunk_texts = [c["text"] for c in all_chunks]
    embeddings = get_embeddings(chunk_texts)

    # Prepare Qdrant points
    points = []
    for idx, (chunk, vector) in enumerate(zip(all_chunks, embeddings)):
        point_id = str(uuid.uuid4())
        points.append(
            PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "patient_id": clean_patient_id,
                    "filename": chunk["filename"],
                    "page": chunk["page"],
                    "chunk_index": chunk["chunk_index"],
                    "text": chunk["text"],
                    "document_type": chunk["document_type"]
                }
            )
        )

    # Upsert points to Qdrant
    store_chunks_in_qdrant(points)

    return {
        "status": "success",
        "patient_id": clean_patient_id,
        "files_processed": processed_files,
        "total_chunks_stored": len(points),
        "phi_redactions": phi_redaction_summary
    }

# --- Verified Chat Endpoint ---

@app.post("/api/chat", response_model=ChatResponse)
def chat_with_medical_rag(req: ChatRequest):
    """Answer question using Patient-isolated RAG search and perform 2nd-stage verification."""
    start_time = time.time()
    clean_patient_id = req.patient_id.strip().upper()
    question = req.question.strip()
    
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # 0. Check Semantic Cache for Low Latency (<50ms)
    cached = get_cached_response(clean_patient_id, question)
    if cached:
        return ChatResponse(**cached)

    # 1. RAG Answer Generation (Call #1 with hybrid retrieval & acronym expansion)
    try:
        rag_result = generate_rag_answer(patient_id=clean_patient_id, question=question)
    except Exception as exc:
        logger.exception("RAG answer generation failed for patient %s", clean_patient_id)
        raise HTTPException(
            status_code=502,
            detail=f"Medical-record answer generation failed: {exc}"
        ) from exc
    
    answer = rag_result["answer"]
    sources = rag_result["sources"]
    chunks_used = rag_result["chunks_used"]

    # 2. Self-Verification Fact Check (Call #2)
    verification = verify_answer(
        question=question,
        context_chunks=chunks_used,
        answer=answer
    )
    
    latency = round(time.time() - start_time, 2)
    
    # 3. Log to Immutable Audit Trail
    audit_entry = log_interaction(
        patient_id=clean_patient_id,
        question=question,
        answer=answer,
        sources_count=len(sources),
        verifier_status=verification["status"],
        confidence_score=verification["confidence_score"],
        flagged_claims=verification.get("flagged_claims", []),
        latency_sec=latency
    )

    response_obj = ChatResponse(
        patient_id=clean_patient_id,
        question=question,
        answer=answer,
        sources=sources,
        verification=VerificationResult(
            status=verification["status"],
            confidence_score=verification["confidence_score"],
            reasoning=verification["reasoning"],
            flagged_claims=verification["flagged_claims"]
        ),
        audit_id=audit_entry.get("id"),
        latency_sec=latency
    )
    
    # Store in Semantic Cache
    set_cached_response(clean_patient_id, question, response_obj.dict())
    return response_obj

@app.post("/api/chat/stream")
def chat_stream(req: ChatRequest):
    """Server-Sent Events (SSE) streaming endpoint for real-time token delivery."""
    import json
    from app.openrouter_client import get_openrouter_client
    from app.retrieval import expand_medical_query, hybrid_rerank
    from app.embeddings import get_single_embedding
    from app.qdrant_client import search_patient_chunks

    clean_patient_id = req.patient_id.strip().upper()
    question = req.question.strip()

    def event_generator():
        # Retrieval step
        expanded_q = expand_medical_query(question)
        query_vector = get_single_embedding(expanded_q if expanded_q != question else question)
        candidate_chunks = search_patient_chunks(patient_id=clean_patient_id, query_vector=query_vector, limit=8)
        
        if not candidate_chunks:
            yield f"data: {json.dumps({'content': 'Information not found in medical records.', 'done': True})}\n\n"
            return

        reranked_chunks = hybrid_rerank(candidate_chunks, query=question)[:5]
        context_blocks = [f"--- Source {idx+1}: {c['filename']} (Page {c['page']}) ---\n{c['text']}" for idx, c in enumerate(reranked_chunks)]
        combined_context = "\n\n".join(context_blocks)
        
        user_prompt = f"PATIENT ID: {clean_patient_id}\n\nCONTEXT:\n{combined_context}\n\nQUESTION: {question}"

        client = get_openrouter_client()
        response = client.chat.completions.create(
            model=settings.PRIMARY_LLM_MODEL,
            temperature=0.0,
            messages=[
                {"role": "system", "content": "You are a strict, precise Medical RAG AI Assistant. Answer factually with citations [Source N: file, Page X]."},
                {"role": "user", "content": user_prompt}
            ],
            stream=True
        )

        for chunk in response:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                text_chunk = chunk.choices[0].delta.content
                yield f"data: {json.dumps({'content': text_chunk})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# --- Clinical Intelligence & Analytics Endpoints ---

@app.get("/api/patient/{patient_id}/labs")
def get_patient_labs(patient_id: str):
    """Retrieve time-series lab trends and vitals for the patient."""
    clean_id = patient_id.strip().upper()
    return extract_lab_trends(clean_id)

@app.get("/api/patient/{patient_id}/timeline")
def get_patient_timeline(patient_id: str):
    """Retrieve chronological medical history and clinical events."""
    clean_id = patient_id.strip().upper()
    events = extract_patient_timeline(clean_id)
    return {"patient_id": clean_id, "events": events, "total_events": len(events)}

@app.get("/api/patient/{patient_id}/risk-calculator")
def get_patient_risk_calculator(patient_id: str):
    """Compute ASCVD 10-year risk, eGFR kidney category, and ICD-10 differential diagnoses."""
    clean_id = patient_id.strip().upper()
    return compute_patient_risk_profile(clean_id)

@app.get("/api/patient/{patient_id}/fhir")
def get_patient_fhir_bundle(patient_id: str):
    """Export patient record as compliant HL7 FHIR R4 JSON Bundle."""
    clean_id = patient_id.strip().upper()
    return export_patient_fhir_bundle(clean_id)

@app.post("/api/patient/{patient_id}/summarize")
def get_clinical_summary(patient_id: str):
    """Generate structured clinical consultation / discharge brief."""
    clean_id = patient_id.strip().upper()
    return generate_clinical_summary(clean_id)

@app.post("/api/patient/{patient_id}/safety-check")
def check_medication_safety(patient_id: str, req: SafetyCheckRequest):
    """Analyze drug contraindications, allergy conflicts, and interactions."""
    clean_id = patient_id.strip().upper()
    return check_drug_safety(clean_id, req.proposed_drug)

# --- Governance & Feedback Endpoints ---

@app.post("/api/feedback")
def submit_feedback(payload: FeedbackRequest):
    """Save clinician thumbs up/down rating and annotations."""
    success = record_feedback(payload.audit_id, payload.rating, payload.comment)
    return {"status": "success" if success else "not_found", "audit_id": payload.audit_id}

@app.get("/api/audit-logs")
def list_audit_logs(limit: int = 50):
    """Retrieve audit statistics and recent entries."""
    return get_audit_summary(limit=limit)
