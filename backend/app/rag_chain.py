import logging
from typing import Dict, Any, List

from app.config import settings
from app.openrouter_client import get_openrouter_client
from app.openrouter_utils import call_openrouter_with_retry
from app.embeddings import get_single_embedding
from app.qdrant_client import search_patient_chunks
from app.retrieval import expand_medical_query, hybrid_rerank

logger = logging.getLogger("medical_rag.rag_chain")

SYSTEM_RAG_PROMPT = """You are a strict, precise Medical RAG AI Assistant. Your task is to answer questions about a patient's medical records based EXCLUSIVELY on the provided document excerpts.

CRITICAL RULES YOU MUST FOLLOW:
1. Rely ONLY on the provided Context excerpts below. NEVER use general medical knowledge, external facts, or assumptions.
2. If the answer to the user's question cannot be found or directly inferred from the provided context, respond EXACTLY with: "Information not found in medical records."
3. Never mix data from other patients or fabricate medical metrics, diagnoses, prescriptions, or dates.
4. For every statement you make, cite the source using the exact bracket format: [Source N: <filename>, Page <page>] corresponding to the Context number.
5. Keep your answer factual, professional, clear, and direct.

PROTOTYPE NOTICE: This is a prototype system using demo data for educational purposes only — not for actual medical diagnosis or clinical treatment.
"""

def generate_rag_answer(patient_id: str, question: str) -> Dict[str, Any]:
    """Retrieve relevant patient chunks from Qdrant, apply hybrid re-ranking, and generate answer with LLM Call 1."""
    # 1. Expand query clinical acronyms (e.g. HTN -> Hypertension)
    expanded_q = expand_medical_query(question)
    
    # 2. Embed user query (using expanded semantic query if expanded)
    query_vector = get_single_embedding(expanded_q if expanded_q != question else question)
    
    # 3. Vector search strictly filtered by patient_id (fetch candidate pool of 8 chunks)
    candidate_chunks = search_patient_chunks(patient_id=patient_id, query_vector=query_vector, limit=8)
    
    if not candidate_chunks:
        return {
            "answer": "Information not found in medical records.",
            "sources": [],
            "chunks_used": []
        }
        
    # 4. Apply Hybrid Re-Ranking (Dense vector score + Lexical token frequency)
    reranked_chunks = hybrid_rerank(candidate_chunks, query=question)[:5]
        
    # Build formatted context block
    context_blocks = []
    formatted_sources = []
    
    for idx, chunk in enumerate(reranked_chunks, 1):
        source_label = f"Source {idx}: {chunk['filename']} (Page {chunk['page']})"
        context_blocks.append(f"--- {source_label} ---\n{chunk['text']}")
        formatted_sources.append({
            "source_id": idx,
            "filename": chunk["filename"],
            "page": chunk["page"],
            "score": chunk.get("hybrid_score", chunk["score"]),
            "vector_score": chunk["score"],
            "lexical_score": chunk.get("lexical_score", 0.0),
            "text": chunk["text"],
            "document_type": chunk["document_type"]
        })
        
    combined_context = "\n\n".join(context_blocks)
    
    user_prompt = f"""PATIENT ID: {patient_id}

PROVIDED MEDICAL RECORD CONTEXT:
{combined_context}

USER QUESTION: {question}

Provide your factual answer with inline source citations [Source N: filename, Page X]. If the answer is not present in the context above, output "Information not found in medical records."."""

    # 5. First LLM Call (Answer Generation with Retry via OpenRouter)
    client = get_openrouter_client()
    response = call_openrouter_with_retry(
        lambda: client.chat.completions.create(
            model=settings.PRIMARY_LLM_MODEL,
            temperature=0.0,  # Zero temperature for deterministic grounding
            messages=[
                {"role": "system", "content": SYSTEM_RAG_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
        )
    )
    
    generated_answer = response.choices[0].message.content.strip()
    
    return {
        "answer": generated_answer,
        "sources": formatted_sources,
        "chunks_used": reranked_chunks
    }
