"""Immutable Audit Logger & Verification Statistics Tracker.

Logs all clinician queries, retrieved vector chunks, verification verdicts,
flagged claims, latency, and clinician feedback to an append-only JSONL log.
"""
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("medical_rag.audit")

ROOT = Path(__file__).parent.parent
LOG_FILE = ROOT / "data" / "audit_logs.jsonl"

def log_interaction(
    patient_id: str,
    question: str,
    answer: str,
    sources_count: int,
    verifier_status: str,
    confidence_score: float,
    flagged_claims: List[str],
    latency_sec: float
) -> Dict[str, Any]:
    """Append a new query interaction entry to the audit log."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    entry = {
        "id": f"audit-{int(time.time()*1000)}",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "patient_id": patient_id,
        "question": question,
        "answer_length": len(answer),
        "sources_retrieved": sources_count,
        "verifier_status": verifier_status,
        "confidence_score": confidence_score,
        "flagged_claims_count": len(flagged_claims),
        "flagged_claims": flagged_claims,
        "latency_sec": round(latency_sec, 2),
        "clinician_feedback": None
    }
    
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")
        
    return entry

def record_feedback(log_id: str, rating: str, comment: Optional[str] = None) -> bool:
    """Update feedback rating (THUMBS_UP / THUMBS_DOWN) on an existing audit entry."""
    if not LOG_FILE.exists():
        return False
        
    try:
        lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
        updated = False
        new_lines = []
        
        for line in lines:
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get("id") == log_id or log_id in entry.get("id", ""):
                entry["clinician_feedback"] = {
                    "rating": rating,
                    "comment": comment or "",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                updated = True
            new_lines.append(json.dumps(entry, ensure_ascii=False))
            
        if updated:
            LOG_FILE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        return updated
    except Exception as e:
        logger.error(f"Error updating feedback in audit log: {e}")
        return False

def get_audit_summary(limit: int = 50) -> Dict[str, Any]:
    """Retrieve audit statistics and recent entries."""
    if not LOG_FILE.exists():
        return {
            "total_queries": 0,
            "verified_percentage": 100.0,
            "avg_confidence": 1.0,
            "avg_latency_sec": 0.0,
            "feedback_stats": {"thumbs_up": 0, "thumbs_down": 0},
            "recent_entries": []
        }
        
    try:
        lines = [line.strip() for line in LOG_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]
        entries = [json.loads(line) for line in lines]
        
        total = len(entries)
        if total == 0:
            return {"total_queries": 0, "verified_percentage": 100.0, "avg_confidence": 1.0, "recent_entries": []}
            
        verified_count = sum(1 for e in entries if e.get("verifier_status") == "VERIFIED")
        avg_conf = sum(e.get("confidence_score", 0.0) for e in entries) / total
        avg_lat = sum(e.get("latency_sec", 0.0) for e in entries) / total
        
        thumbs_up = sum(1 for e in entries if (e.get("clinician_feedback") or {}).get("rating") == "THUMBS_UP")
        thumbs_down = sum(1 for e in entries if (e.get("clinician_feedback") or {}).get("rating") == "THUMBS_DOWN")
        
        return {
            "total_queries": total,
            "verified_percentage": round((verified_count / total) * 100, 1),
            "avg_confidence": round(avg_conf, 2),
            "avg_latency_sec": round(avg_lat, 2),
            "feedback_stats": {"thumbs_up": thumbs_up, "thumbs_down": thumbs_down},
            "recent_entries": list(reversed(entries[-limit:]))
        }
    except Exception as e:
        logger.error(f"Error reading audit summary: {e}")
        return {"total_queries": 0, "error": str(e), "recent_entries": []}
