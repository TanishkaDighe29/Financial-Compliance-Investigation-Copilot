"""
Deterministic risk scoring -- per the project spec, the LLM must NEVER invent
a risk score. This is plain business-rule arithmetic.

Risk Score = 0.35*(Control Criticality) + 0.30*(Evidence Gap Severity)
           + 0.20*(Evidence Age) + 0.15*(LLM Confidence Penalty)
All components normalized 0-100.
"""

CONTROL_CRITICALITY = {
    "AC-6": 90, "AC-2": 85, "IA-2": 85, "IA-2.1": 90, "AU-6": 60, "SR-6": 70,
    "SCRM-VENDOR": 65,  # project-local label for vendor SCRM questionnaire gaps, not an official NIST control ID
    "SEC-1C": 75,  # SEC Item 1C cybersecurity disclosure adequacy -- not a real NIST control
                   # ID; a project-local label for the SEC filing module, documented here so
                   # it doesn't get confused with an official control.
}

GAP_SEVERITY = {
    "missing": 100,
    "partial": 65,
    "contradictory": 80,
    "complete": 0,
}


def score(control_id: str, evidence_status: str, evidence_age_score: float, confidence: float) -> dict:
    criticality = CONTROL_CRITICALITY.get(control_id, 50)
    gap = GAP_SEVERITY.get(evidence_status, 50)
    age = max(0, min(100, evidence_age_score))
    confidence_penalty = (1 - confidence) * 100  # low confidence -> higher penalty -> can't be used to LOWER risk

    raw = 0.35 * criticality + 0.30 * gap + 0.20 * age + 0.15 * confidence_penalty
    raw = round(min(100, raw), 1)

    if raw >= 80:
        level = "high"
    elif raw >= 50:
        level = "medium"
    else:
        level = "low"

    return {
        "risk_score": raw, "risk_level": level,
        "components": {"control_criticality": criticality, "evidence_gap_severity": gap,
                        "evidence_age_score": age, "confidence_penalty": round(confidence_penalty, 1)},
    }
