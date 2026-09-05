"""Advanced Retrieval Module: Medical Query Expansion & Hybrid Keyword Re-ranking.

Expands clinical abbreviations (e.g. HTN -> Hypertension) and fuses vector similarity
scores with keyword BM25/lexical term frequencies for precise medication, lab, and diagnosis matching.
"""
import re
from typing import List, Dict, Any

# Clinical abbreviations and canonical expansion map
MEDICAL_ACRONYMS: Dict[str, str] = {
    "htn": "hypertension high blood pressure",
    "bp": "blood pressure",
    "dm": "diabetes mellitus",
    "dm2": "type 2 diabetes mellitus",
    "t2d": "type 2 diabetes mellitus",
    "t1d": "type 1 diabetes mellitus",
    "mi": "myocardial infarction heart attack",
    "cad": "coronary artery disease",
    "chf": "congestive heart failure",
    "copd": "chronic obstructive pulmonary disease",
    "sob": "shortness of breath dyspnea",
    "ckd": "chronic kidney disease",
    "aki": "acute kidney injury",
    "gerd": "gastroesophageal reflux disease acid reflux",
    "uti": "urinary tract infection",
    "dvt": "deep vein thrombosis blood clot",
    "pe": "pulmonary embolism",
    "cva": "cerebrovascular accident stroke",
    "tia": "transient ischemic attack mini stroke",
    "hba1c": "glycated hemoglobin a1c glucose",
    "wbc": "white blood cell count leukocytes",
    "rbc": "red blood cell count erythrocytes",
    "hgb": "hemoglobin",
    "hct": "hematocrit",
    "plt": "platelets thrombocytes",
    "bun": "blood urea nitrogen kidney function",
    "cr": "creatinine kidney function",
    "gfr": "glomerular filtration rate",
    "alt": "alanine aminotransferase liver function",
    "ast": "aspartate aminotransferase liver function",
    "tsh": "thyroid stimulating hormone",
    "cxr": "chest x-ray radiograph",
    "ecg": "electrocardiogram ekg",
    "ekg": "electrocardiogram",
    "ct": "computed tomography scan",
    "mri": "magnetic resonance imaging scan",
    "prn": "as needed pro re nata",
    "po": "orally by mouth per os",
    "bid": "twice daily bis in die",
    "tid": "three times daily ter in die",
    "qid": "four times daily quater in die",
    "qd": "once daily quaque die",
    "npo": "nothing by mouth nil per os",
    "rx": "prescription medication",
    "dx": "diagnosis",
    "hx": "history",
    "sx": "symptoms",
    "tx": "treatment therapy"
}

def expand_medical_query(query: str) -> str:
    """Expand clinical abbreviations and acronyms within the user query."""
    if not query:
        return query
        
    words = re.findall(r"\b[\w'-]+\b", query)
    expanded_terms = []
    
    for word in words:
        clean_w = word.lower()
        if clean_w in MEDICAL_ACRONYMS:
            expanded_terms.append(f"({word} OR {MEDICAL_ACRONYMS[clean_w]})")
        else:
            expanded_terms.append(word)
            
    # Return query augmented with expansions
    expanded_query = " ".join(expanded_terms)
    return expanded_query if expanded_query != query else query

def compute_lexical_score(query: str, text: str) -> float:
    """Simple term-frequency matching score between query terms and chunk text."""
    if not query or not text:
        return 0.0
        
    query_tokens = set(re.findall(r"\b\w{3,}\b", query.lower()))
    if not query_tokens:
        return 0.0
        
    text_lower = text.lower()
    matches = sum(1 for token in query_tokens if token in text_lower)
    return matches / len(query_tokens)

def hybrid_rerank(chunks: List[Dict[str, Any]], query: str, vector_weight: float = 0.7, lexical_weight: float = 0.3) -> List[Dict[str, Any]]:
    """Re-score and re-rank chunks using a hybrid fusion of vector cosine similarity and lexical overlap."""
    if not chunks:
        return []
        
    scored_chunks = []
    for chunk in chunks:
        v_score = chunk.get("score", 0.0)
        l_score = compute_lexical_score(query, chunk.get("text", ""))
        
        # Hybrid combined score
        hybrid_score = (v_score * vector_weight) + (l_score * lexical_weight)
        
        chunk_copy = dict(chunk)
        chunk_copy["hybrid_score"] = round(hybrid_score, 4)
        chunk_copy["lexical_score"] = round(l_score, 4)
        scored_chunks.append(chunk_copy)
        
    # Sort descending by hybrid score
    scored_chunks.sort(key=lambda x: x["hybrid_score"], reverse=True)
    return scored_chunks
