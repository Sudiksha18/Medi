"""Clinical Analytics Suite: Lab Trends, Longitudinal Timeline, Drug Safety & Clinical Summaries.

Extracts structured health metrics, time-series lab trends, patient chronological events,
and generates clinical discharge/consultation briefs.
"""
import re
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.config import settings
from app.openrouter_client import get_openrouter_client
from app.qdrant_client import get_qdrant_client
from app.openrouter_utils import call_openrouter_with_retry

logger = logging.getLogger("medical_rag.analytics")

# Common Lab & Vital Reference Ranges for adult patients
LAB_REFERENCE_RANGES = {
    "blood_pressure_systolic": {"unit": "mmHg", "min": 90, "max": 120, "name": "Systolic BP"},
    "blood_pressure_diastolic": {"unit": "mmHg", "min": 60, "max": 80, "name": "Diastolic BP"},
    "glucose": {"unit": "mg/dL", "min": 70, "max": 99, "name": "Fasting Glucose"},
    "hba1c": {"unit": "%", "min": 4.0, "max": 5.6, "name": "Hemoglobin A1c"},
    "total_cholesterol": {"unit": "mg/dL", "min": 125, "max": 200, "name": "Total Cholesterol"},
    "ldl_cholesterol": {"unit": "mg/dL", "min": 50, "max": 100, "name": "LDL Cholesterol"},
    "hdl_cholesterol": {"unit": "mg/dL", "min": 40, "max": 60, "name": "HDL Cholesterol"},
    "triglycerides": {"unit": "mg/dL", "min": 50, "max": 150, "name": "Triglycerides"},
    "creatinine": {"unit": "mg/dL", "min": 0.6, "max": 1.2, "name": "Serum Creatinine"},
    "heart_rate": {"unit": "bpm", "min": 60, "max": 100, "name": "Heart Rate"},
    "body_mass_index": {"unit": "kg/m2", "min": 18.5, "max": 24.9, "name": "Body Mass Index (BMI)"},
    "body_temperature": {"unit": "degC", "min": 36.5, "max": 37.5, "name": "Body Temperature"}
}

def get_all_patient_chunks(patient_id: str) -> List[Dict[str, Any]]:
    """Retrieve all document chunks associated with a patient from Qdrant."""
    client = get_qdrant_client()
    try:
        from qdrant_client.http.models import Filter, FieldCondition, MatchValue
        scroll_filter = Filter(
            must=[FieldCondition(key="patient_id", match=MatchValue(value=patient_id.strip().upper()))]
        )
        scroll_res, _ = client.scroll(
            collection_name=settings.QDRANT_COLLECTION,
            scroll_filter=scroll_filter,
            limit=200,
            with_payload=True,
            with_vectors=False
        )
        return [p.payload for p in scroll_res if p.payload]
    except Exception as e:
        logger.error(f"Error fetching patient chunks for analytics: {e}")
        return []

def extract_lab_trends(patient_id: str) -> Dict[str, Any]:
    """Extract time-series lab and vital measurements for a patient."""
    chunks = get_all_patient_chunks(patient_id)
    if not chunks:
        return {"patient_id": patient_id, "metrics": {}, "total_records": 0}

    trends: Dict[str, List[Dict[str, Any]]] = {k: [] for k in LAB_REFERENCE_RANGES}
    
    # Regex patterns for clinical lines and values
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2})?)")
    
    for c in chunks:
        text = c.get("text", "")
        lines = text.splitlines()
        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue
                
            # Date extraction
            date_match = date_pattern.search(line_clean)
            record_date = date_match.group(1)[:10] if date_match else "Undated"
            
            # 1. Blood pressure extraction (e.g. 120/80, Systolic Blood Pressure 130 mmHg)
            bp_match = re.search(r"(?:BP|Blood Pressure|systolic/diastolic)[^\d]*(\d{2,3})\s*/\s*(\d{2,3})", line_clean, re.IGNORECASE)
            if bp_match:
                sys_val = float(bp_match.group(1))
                dia_val = float(bp_match.group(2))
                trends["blood_pressure_systolic"].append({
                    "date": record_date,
                    "value": sys_val,
                    "status": "High" if sys_val > 130 else ("Normal" if sys_val >= 90 else "Low"),
                    "source": c.get("filename", "record.json")
                })
                trends["blood_pressure_diastolic"].append({
                    "date": record_date,
                    "value": dia_val,
                    "status": "High" if dia_val > 85 else ("Normal" if dia_val >= 60 else "Low"),
                    "source": c.get("filename", "record.json")
                })

            # 2. Glucose extraction
            if "glucose" in line_clean.lower() or "blood sugar" in line_clean.lower():
                val_match = re.search(r"(?:value|is|:)[^\d]*(\d{2,3}(?:\.\d+)?)", line_clean, re.IGNORECASE)
                if val_match:
                    val = float(val_match.group(1))
                    trends["glucose"].append({
                        "date": record_date,
                        "value": val,
                        "status": "High" if val > 125 else ("Elevated" if val >= 100 else "Normal"),
                        "source": c.get("filename", "record.json")
                    })

            # 3. HbA1c extraction
            if "hba1c" in line_clean.lower() or "hemoglobin a1c" in line_clean.lower():
                val_match = re.search(r"(?:value|is|:)[^\d]*(\d{1,2}(?:\.\d+)?)", line_clean, re.IGNORECASE)
                if val_match:
                    val = float(val_match.group(1))
                    trends["hba1c"].append({
                        "date": record_date,
                        "value": val,
                        "status": "Diabetic Range" if val >= 6.5 else ("Prediabetes" if val >= 5.7 else "Normal"),
                        "source": c.get("filename", "record.json")
                    })

            # 4. Cholesterol
            if "cholesterol" in line_clean.lower() or "lipid" in line_clean.lower():
                val_match = re.search(r"(?:value|is|:)[^\d]*(\d{2,3}(?:\.\d+)?)", line_clean, re.IGNORECASE)
                if val_match:
                    val = float(val_match.group(1))
                    trends["total_cholesterol"].append({
                        "date": record_date,
                        "value": val,
                        "status": "High" if val > 200 else "Normal",
                        "source": c.get("filename", "record.json")
                    })

            # 5. Creatinine
            if "creatinine" in line_clean.lower():
                val_match = re.search(r"(?:value|is|:)[^\d]*(\d{1,2}(?:\.\d+)?)", line_clean, re.IGNORECASE)
                if val_match:
                    val = float(val_match.group(1))
                    trends["creatinine"].append({
                        "date": record_date,
                        "value": val,
                        "status": "High" if val > 1.2 else "Normal",
                        "source": c.get("filename", "record.json")
                    })

            # 6. BMI / Heart rate / Observation general parser
            if "body mass index" in line_clean.lower() or "bmi" in line_clean.lower():
                val_match = re.search(r"(?:value|is|:)[^\d]*(\d{2}(?:\.\d+)?)", line_clean, re.IGNORECASE)
                if val_match:
                    val = float(val_match.group(1))
                    trends["body_mass_index"].append({
                        "date": record_date,
                        "value": val,
                        "status": "Overweight/Obese" if val >= 25 else ("Normal" if val >= 18.5 else "Underweight"),
                        "source": c.get("filename", "record.json")
                    })
                    
            if "heart rate" in line_clean.lower() or "pulse" in line_clean.lower():
                val_match = re.search(r"(?:value|is|:)[^\d]*(\d{2,3})", line_clean, re.IGNORECASE)
                if val_match:
                    val = float(val_match.group(1))
                    trends["heart_rate"].append({
                        "date": record_date,
                        "value": val,
                        "status": "Tachycardia" if val > 100 else ("Bradycardia" if val < 60 else "Normal"),
                        "source": c.get("filename", "record.json")
                    })

    # Sort time series by date
    active_metrics = {}
    for key, data_points in trends.items():
        if data_points:
            # Sort by date, placing undated at end
            data_points.sort(key=lambda x: x["date"] if x["date"] != "Undated" else "1900-01-01")
            active_metrics[key] = {
                "name": LAB_REFERENCE_RANGES[key]["name"],
                "unit": LAB_REFERENCE_RANGES[key]["unit"],
                "reference_range": f"{LAB_REFERENCE_RANGES[key]['min']} - {LAB_REFERENCE_RANGES[key]['max']} {LAB_REFERENCE_RANGES[key]['unit']}",
                "latest_value": data_points[-1]["value"],
                "latest_status": data_points[-1]["status"],
                "data_points": data_points
            }

    return {
        "patient_id": patient_id,
        "metrics": active_metrics,
        "total_categories": len(active_metrics)
    }

def extract_patient_timeline(patient_id: str) -> List[Dict[str, Any]]:
    """Extract chronological medical timeline (Encounters, Conditions, Procedures, Prescriptions)."""
    chunks = get_all_patient_chunks(patient_id)
    if not chunks:
        return []

    events = []
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})")

    for c in chunks:
        text = c.get("text", "")
        filename = c.get("filename", "record.json")
        for line in text.splitlines():
            line_str = line.strip()
            if not line_str:
                continue

            date_match = date_pattern.search(line_str)
            event_date = date_match.group(1) if date_match else "Undated"

            if line_str.startswith("Condition:") or "clinicalStatus:" in line_str:
                events.append({
                    "date": event_date,
                    "type": "Condition / Diagnosis",
                    "badge_color": "#f59e0b",
                    "title": line_str.split(";")[0].replace("Condition:", "").strip(),
                    "details": line_str,
                    "source": filename
                })
            elif line_str.startswith("Procedure:") or "Procedure" in line_str:
                events.append({
                    "date": event_date,
                    "type": "Medical Procedure",
                    "badge_color": "#3b82f6",
                    "title": line_str.split(";")[0].replace("Procedure:", "").strip(),
                    "details": line_str,
                    "source": filename
                })
            elif line_str.startswith("MedicationRequest:") or "Medication" in line_str:
                events.append({
                    "date": event_date,
                    "type": "Medication Prescription",
                    "badge_color": "#10b981",
                    "title": line_str.split(";")[0].replace("MedicationRequest:", "").strip(),
                    "details": line_str,
                    "source": filename
                })
            elif line_str.startswith("Immunization:"):
                events.append({
                    "date": event_date,
                    "type": "Immunization / Vaccine",
                    "badge_color": "#8b5cf6",
                    "title": line_str.split(";")[0].replace("Immunization:", "").strip(),
                    "details": line_str,
                    "source": filename
                })
            elif line_str.startswith("Observation:"):
                events.append({
                    "date": event_date,
                    "type": "Clinical Observation",
                    "badge_color": "#14b8a6",
                    "title": line_str.split(";")[0].replace("Observation:", "").strip(),
                    "details": line_str,
                    "source": filename
                })

    # Sort reverse chronological (newest first)
    events.sort(key=lambda x: x["date"] if x["date"] != "Undated" else "1900-01-01", reverse=True)
    return events[:50]  # Cap at 50 most recent events

def generate_clinical_summary(patient_id: str) -> Dict[str, Any]:
    """Generate a structured clinical discharge/consultation summary using LLM."""
    chunks = get_all_patient_chunks(patient_id)
    if not chunks:
        return {
            "patient_id": patient_id,
            "summary_markdown": "No medical records found for this patient.",
            "generated_at": datetime.now().isoformat()
        }

    combined_text = "\n\n".join([f"--- Excerpt {idx+1} ({c['filename']}) ---\n{c['text']}" for idx, c in enumerate(chunks[:10])])

    prompt = f"""You are a clinical physician assistant. Generate a professional, structured Clinical Consultation & Discharge Summary for PATIENT ID: {patient_id}.

PATIENT RECORD EXCERPTS:
{combined_text}

STRUCTURE REQUIRED:
1. **Patient Demographics & Identification** (Name, DOB, Gender if recorded)
2. **Active Clinical Diagnoses & Medical History**
3. **Documented Medications & Active Prescriptions**
4. **Recent Clinical Observations & Key Lab Findings**
5. **Completed Procedures & Care Plans**
6. **Clinical Recommendations & Follow-Up Plan**

Ground every bullet point strictly in the provided excerpts with inline citations [Source: filename]. If any section is unrecorded, state 'None documented in records.'"""

    try:
        client = get_openrouter_client()
        response = call_openrouter_with_retry(
            lambda: client.chat.completions.create(
                model=settings.PRIMARY_LLM_MODEL,
                temperature=0.0,
                messages=[
                    {"role": "system", "content": "You are a professional Medical Document Summarizer. Output only factual, clinical notes."},
                    {"role": "user", "content": prompt}
                ]
            )
        )
        content = response.choices[0].message.content.strip()
        return {
            "patient_id": patient_id,
            "summary_markdown": content,
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error generating clinical summary: {e}")
        return {
            "patient_id": patient_id,
            "summary_markdown": f"Clinical summary currently unavailable: {str(e)}",
            "generated_at": datetime.now().isoformat()
        }

def check_drug_safety(patient_id: str, proposed_drug: str) -> Dict[str, Any]:
    """Analyze potential contraindications, drug-drug interactions, or allergy warnings for a patient."""
    chunks = get_all_patient_chunks(patient_id)
    if not chunks:
        return {
            "patient_id": patient_id,
            "safety_status": "NO_RECORDS",
            "alerts": ["No medical records found for active patient."],
            "recommendation": "Obtain medical history before prescribing."
        }

    combined_text = "\n\n".join([f"[{c['filename']}]\n{c['text']}" for c in chunks[:8]])

    prompt = f"""Analyze drug safety and contraindications for PATIENT ID: {patient_id}.
PROPOSED DRUG TO EVALUATE: {proposed_drug}

PATIENT RECORD CONTEXT:
{combined_text}

Evaluate if the proposed drug has any documented:
1. Documented allergy or adverse reaction in patient's file.
2. Conflict or interaction with active medications.
3. Contraindication with diagnosed conditions (e.g. renal failure, hypertension, asthma).

Return JSON ONLY:
{{
  "safety_status": "SAFE" | "CAUTION" | "CONTRAINDICATED",
  "alerts": ["List of specific contraindications or warnings"],
  "active_medications_found": ["List of current meds in file"],
  "reasoning": "Clear clinical explanation..."
}}"""

    try:
        client = get_openrouter_client()
        response = call_openrouter_with_retry(
            lambda: client.chat.completions.create(
                model=settings.PRIMARY_LLM_MODEL,
                temperature=0.0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You are an automated clinical pharmacology safety auditor. Return JSON only."},
                    {"role": "user", "content": prompt}
                ]
            )
        )
        data = json.loads(response.choices[0].message.content.strip())
        return {
            "patient_id": patient_id,
            "proposed_drug": proposed_drug,
            "safety_status": data.get("safety_status", "CAUTION"),
            "alerts": data.get("alerts", []),
            "active_medications_found": data.get("active_medications_found", []),
            "reasoning": data.get("reasoning", "Safety audit completed.")
        }
    except Exception as e:
        logger.error(f"Drug safety check failed: {e}")
        return {
            "patient_id": patient_id,
            "proposed_drug": proposed_drug,
            "safety_status": "CAUTION",
            "alerts": [f"Automated check error: {str(e)}"],
            "active_medications_found": [],
            "reasoning": "Unable to complete automated safety check."
        }
