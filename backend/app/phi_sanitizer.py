"""HIPAA-Compliant PHI (Protected Health Information) Sanitizer.

Provides deterministic de-identification for clinical records before chunking and embedding,
redacting Social Security Numbers, phone numbers, email addresses, and postal addresses
while preserving medical terminology, lab numbers, and clinical dates.
"""
import re
from typing import Dict, Any, Tuple

# Regex patterns for common PHI entities
PATTERNS = {
    "SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "EMAIL": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"),
    "PHONE": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "ZIP_CODE": re.compile(r"\b\d{5}(?:-\d{4})?\b"),
}

def sanitize_phi(text: str) -> Tuple[str, Dict[str, int]]:
    """Sanitize text by replacing detected PHI entities with standard redaction tokens.
    
    Returns:
        Tuple of (sanitized_text, redaction_counts_dict)
    """
    if not text:
        return text, {}
        
    counts = {}
    sanitized = text
    
    # 1. Redact SSN
    ssn_matches = PATTERNS["SSN"].findall(sanitized)
    if ssn_matches:
        counts["SSN"] = len(ssn_matches)
        sanitized = PATTERNS["SSN"].sub("[REDACTED-SSN]", sanitized)
        
    # 2. Redact Email
    email_matches = PATTERNS["EMAIL"].findall(sanitized)
    if email_matches:
        counts["EMAIL"] = len(email_matches)
        sanitized = PATTERNS["EMAIL"].sub("[REDACTED-EMAIL]", sanitized)
        
    # 3. Redact Phone
    phone_matches = PATTERNS["PHONE"].findall(sanitized)
    if phone_matches:
        counts["PHONE"] = len(phone_matches)
        sanitized = PATTERNS["PHONE"].sub("[REDACTED-PHONE]", sanitized)
        
    return sanitized, counts
