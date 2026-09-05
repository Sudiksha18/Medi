"""HL7 FHIR R4 Standardized EHR Data Exporter."""
import json
import logging
from typing import Dict, Any
from datetime import datetime

from app.clinical_analytics import get_all_patient_chunks, extract_patient_timeline, extract_lab_trends

logger = logging.getLogger("medical_rag.fhir")

def export_patient_fhir_bundle(patient_id: str) -> Dict[str, Any]:
    """Export all stored patient records and clinical findings as a compliant HL7 FHIR R4 JSON Bundle."""
    timeline = extract_patient_timeline(patient_id)
    labs = extract_lab_trends(patient_id)
    
    entries = []
    
    # 1. FHIR Patient Resource
    patient_resource = {
        "fullUrl": f"urn:uuid:patient-{patient_id}",
        "resource": {
            "resourceType": "Patient",
            "id": patient_id,
            "identifier": [{
                "system": "http://hospital.org/patient-ids",
                "value": patient_id
            }],
            "active": True,
            "gender": "unknown"
        }
    }
    entries.append(patient_resource)
    
    # 2. FHIR Condition Resources
    for evt in timeline:
        if evt.get("type") == "Condition / Diagnosis":
            entries.append({
                "fullUrl": f"urn:uuid:condition-{hash(evt['title'])}",
                "resource": {
                    "resourceType": "Condition",
                    "clinicalStatus": {
                        "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]
                    },
                    "verificationStatus": {
                        "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed"}]
                    },
                    "code": {
                        "text": evt["title"]
                    },
                    "subject": {"reference": f"Patient/{patient_id}"},
                    "recordedDate": evt.get("date", "2023-01-01")
                }
            })
            
    # 3. FHIR Observation Resources from Labs
    metrics = labs.get("metrics", {})
    for k, v in metrics.items():
        entries.append({
            "fullUrl": f"urn:uuid:observation-{k}",
            "resource": {
                "resourceType": "Observation",
                "status": "final",
                "code": {
                    "text": v.get("name", k)
                },
                "subject": {"reference": f"Patient/{patient_id}"},
                "valueQuantity": {
                    "value": v.get("latest_value"),
                    "unit": v.get("unit")
                }
            }
        })
        
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "timestamp": datetime.now().isoformat(),
        "total": len(entries),
        "entry": entries
    }
