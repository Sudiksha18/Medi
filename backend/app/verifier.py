import json
import logging
from typing import Dict, Any, List

from app.config import settings
from app.openrouter_client import get_openrouter_client
from app.openrouter_utils import call_openrouter_with_retry

logger = logging.getLogger("medical_rag.verifier")

VERIFIER_SYSTEM_PROMPT = """You are a meticulous Medical Fact-Checking Auditor AI. 
Your sole duty is to independently verify whether an AI-generated answer about a patient's medical records is 100% strictly supported by the provided context excerpts.

VERIFICATION RULES:
1. Examine every claim, medical metric, dosage, lab result, diagnosis, and date in the GENERATED ANSWER against the CONTEXT EXCERPTS.
2. If ANY statement in the answer makes claims NOT explicitly stated in the context, flag it as an unsupported claim.
3. If the answer correctly responds "Information not found in medical records." when the context indeed lacks the information, mark it as VERIFIED.
4. If the answer contains outside general medical knowledge not present in the context, flag it as NEEDS_REVIEW.
5. You MUST return your evaluation in valid JSON format matching the schema below.

JSON SCHEMA OUTPUT REQUIRED:
{
  "status": "VERIFIED" | "NEEDS_REVIEW",
  "confidence_score": 0.95,
  "reasoning": "Clear explanation of audit findings...",
  "flagged_claims": ["List of unsupported or hallucinated statements if any"]
}
"""

def verify_answer(question: str, context_chunks: List[Dict[str, Any]], answer: str) -> Dict[str, Any]:
    """Perform Second LLM Call to independently audit and verify the generated answer."""
    # Handle simple 'not found' case cleanly
    if answer.strip() == "Information not found in medical records." or not context_chunks:
        return {
            "status": "VERIFIED",
            "confidence_score": 1.0,
            "reasoning": "Answer correctly indicates absence of records in database.",
            "flagged_claims": []
        }

    # Format context for auditor
    context_text = "\n\n".join([
        f"[Source {idx+1}: {c['filename']} (Page {c['page']})]\n{c['text']}"
        for idx, c in enumerate(context_chunks)
    ])
    
    verifier_prompt = f"""USER QUESTION: {question}

RETRIEVED CONTEXT EXCERPTS:
{context_text}

GENERATED ANSWER TO AUDIT:
{answer}

Evaluate the generated answer against the retrieved context excerpts. Check every claim for strict accuracy and grounding.
Return JSON ONLY."""

    try:
        client = get_openrouter_client()
        response = call_openrouter_with_retry(
            lambda: client.chat.completions.create(
                model=settings.VERIFIER_LLM_MODEL,
                temperature=0.0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": VERIFIER_SYSTEM_PROMPT},
                    {"role": "user", "content": verifier_prompt}
                ]
            )
        )
        
        result_content = response.choices[0].message.content.strip()
        parsed_result = json.loads(result_content)
        if not isinstance(parsed_result, dict):
            raise ValueError("OpenRouter verification response must be a JSON object.")
        
        # Ensure fallback defaults if key missing
        return {
            "status": str(parsed_result.get("status", "NEEDS_REVIEW")).upper(),
            "confidence_score": float(parsed_result.get("confidence_score", 0.5)),
            "reasoning": parsed_result.get("reasoning", "Audit completed."),
            "flagged_claims": parsed_result.get("flagged_claims", [])
        }
    except Exception as e:
        logger.error(f"Error during self-verification LLM call: {e}")
        return {
            "status": "NEEDS_REVIEW",
            "confidence_score": 0.0,
            "reasoning": f"Verification completed with caution: {str(e)}",
            "flagged_claims": ["Unable to complete 2nd-stage verification audit."]
        }
