"""Clinical Calculators & Risk Screening Suite: ASCVD Risk, eGFR, Lab Risk Tiers & Differential Diagnosis."""
import logging
from typing import Dict, Any, List
from app.clinical_analytics import extract_lab_trends, extract_patient_timeline

logger = logging.getLogger("medical_rag.calculators")

def compute_ascvd_risk(sys_bp: float, total_chol: float, hdl_chol: float, is_smoker: bool = False, has_diabetes: bool = False) -> Dict[str, Any]:
    """Compute estimated ASCVD (Atherosclerotic Cardiovascular Disease) 10-Year Risk Category."""
    score = 0.0
    
    # Systolic BP scoring
    if sys_bp >= 160: score += 4.5
    elif sys_bp >= 140: score += 3.0
    elif sys_bp >= 130: score += 1.5
    
    # Cholesterol scoring
    if total_chol >= 240: score += 4.0
    elif total_chol >= 200: score += 2.5
    
    if hdl_chol < 40: score += 2.0
    elif hdl_chol >= 60: score -= 1.0
    
    if is_smoker: score += 3.5
    if has_diabetes: score += 3.0
    
    risk_percentage = round(min(max(score * 1.8 + 2.0, 1.0), 45.0), 1)
    
    if risk_percentage >= 20.0:
        category = "HIGH_RISK"
        recommendation = "High 10-year CVD risk. Statin therapy and aggressive BP lowering strongly recommended."
    elif risk_percentage >= 7.5:
        category = "MODERATE_RISK"
        recommendation = "Moderate risk. Consider moderate-intensity statin and lifestyle modifications."
    else:
        category = "LOW_RISK"
        recommendation = "Low 10-year cardiovascular event risk. Maintain healthy lifestyle."
        
    return {
        "risk_percentage": risk_percentage,
        "category": category,
        "recommendation": recommendation
    }

def compute_egfr_category(creatinine: float, age: int = 60, is_female: bool = False) -> Dict[str, Any]:
    """Compute estimated Glomerular Filtration Rate (eGFR) using CKD-EPI formula proxy."""
    if creatinine <= 0:
        return {"egfr": 90.0, "stage": "G1", "status": "Normal"}
        
    # CKD-EPI approximation
    kappa = 0.7 if is_female else 0.9
    alpha = -0.329 if is_female else -0.411
    
    egfr = 141 * (min(creatinine / kappa, 1.0) ** alpha) * (max(creatinine / kappa, 1.0) ** -1.209) * (0.993 ** age)
    if is_female:
        egfr *= 1.018
        
    egfr_val = round(egfr, 1)
    
    if egfr_val >= 90:
        stage = "G1 (Normal / High GFR)"
        status = "NORMAL"
    elif egfr_val >= 60:
        stage = "G2 (Mildly Decreased)"
        status = "MILD"
    elif egfr_val >= 45:
        stage = "G3a (Mildly to Moderately Decreased)"
        status = "MODERATE"
    elif egfr_val >= 30:
        stage = "G3b (Moderately to Severely Decreased)"
        status = "MODERATE_SEVERE"
    elif egfr_val >= 15:
        stage = "G4 (Severely Decreased)"
        status = "SEVERE"
    else:
        stage = "G5 (Kidney Failure)"
        status = "CRITICAL"
        
    return {
        "egfr": egfr_val,
        "stage": stage,
        "status": status,
        "creatinine_used": creatinine
    }

def compute_patient_risk_profile(patient_id: str) -> Dict[str, Any]:
    """Generate comprehensive automated clinical risk profile and differential diagnoses for patient."""
    labs = extract_lab_trends(patient_id)
    timeline = extract_patient_timeline(patient_id)
    
    metrics = labs.get("metrics", {})
    
    # Extract recent vitals
    sys_bp = (metrics.get("blood_pressure_systolic") or {}).get("latest_value", 120.0)
    total_chol = (metrics.get("total_cholesterol") or {}).get("latest_value", 180.0)
    hdl_chol = (metrics.get("hdl_cholesterol") or {}).get("latest_value", 50.0)
    glucose = (metrics.get("glucose") or {}).get("latest_value", 95.0)
    hba1c = (metrics.get("hba1c") or {}).get("latest_value", 5.4)
    creatinine = (metrics.get("creatinine") or {}).get("latest_value", 0.9)
    
    # Conditions check from timeline
    conditions_found = [e["title"] for e in timeline if e.get("type") == "Condition / Diagnosis"]
    has_diabetes = any("diabet" in c.lower() for c in conditions_found) or hba1c >= 6.5 or glucose >= 126.0
    has_htn = any("hypertension" in c.lower() or "htn" in c.lower() for c in conditions_found) or sys_bp >= 130.0
    
    # Compute clinical scores
    ascvd = compute_ascvd_risk(sys_bp=sys_bp, total_chol=total_chol, hdl_chol=hdl_chol, has_diabetes=has_diabetes)
    kidney = compute_egfr_category(creatinine=creatinine)
    
    # Generate ICD-10 aligned Differential Diagnoses / Risk Alerts
    differentials = []
    if has_diabetes:
        differentials.append({
            "code": "E11.9",
            "condition": "Type 2 Diabetes Mellitus",
            "confidence": "HIGH",
            "evidence": f"HbA1c: {hba1c}% | Fasting Glucose: {glucose} mg/dL"
        })
    if has_htn:
        differentials.append({
            "code": "I10",
            "condition": "Essential (Primary) Hypertension",
            "confidence": "HIGH",
            "evidence": f"Systolic BP: {sys_bp} mmHg"
        })
    if total_chol >= 200:
        differentials.append({
            "code": "E78.5",
            "condition": "Hyperlipidemia / Dyslipidemia",
            "confidence": "MODERATE",
            "evidence": f"Total Cholesterol: {total_chol} mg/dL"
        })
    if kidney["status"] in ["MODERATE", "MODERATE_SEVERE", "SEVERE", "CRITICAL"]:
        differentials.append({
            "code": "N18.9",
            "condition": "Chronic Kidney Disease (CKD Risk)",
            "confidence": "MODERATE",
            "evidence": f"eGFR: {kidney['egfr']} mL/min/1.73m2 (Creatinine {creatinine} mg/dL)"
        })
        
    if not differentials:
        differentials.append({
            "code": "Z00.00",
            "condition": "General Adult Medical Examination - No Acute Pathology",
            "confidence": "HIGH",
            "evidence": "Vitals and lab values within normal adult reference ranges."
        })
        
    return {
        "patient_id": patient_id,
        "ascvd_risk": ascvd,
        "kidney_function": kidney,
        "diabetes_status": "Diabetic Range" if hba1c >= 6.5 else ("Prediabetes" if hba1c >= 5.7 else "Normal"),
        "differential_diagnoses": differentials,
        "conditions_summary": conditions_found
    }
