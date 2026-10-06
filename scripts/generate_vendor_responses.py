"""
Generate SYNTHETIC vendor SCRM questionnaire responses for three fictional
vendors, answering the real CISA SCRM Template questions (data/frameworks/
cisa_scrm/scrm_questions.csv). No real vendor's actual data is used.

Vendors (all fictional):
  - Northstar CloudSec  -- mostly compliant, one real gap (no MFA)
  - Apex Payments       -- several gaps (payments vendor, higher stakes)
  - Redbridge Data      -- minimal documentation, treat as high risk
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS = list(csv.DictReader(open(ROOT / "data/frameworks/cisa_scrm/scrm_questions.csv")))
OUT_DIR = ROOT / "data/sample_documents/vendor_risk"

NOTICE = ("Synthetic sample created solely for portfolio demonstration. This document "
          "contains no real vendor, client, employee, or confidential data.")

# answer overrides per vendor: question_id -> (answer, notes)
VENDOR_PROFILES = {
    "northstar_cloud": {
        "name": "Northstar CloudSec, Inc. (fictional)",
        "criticality": "high",  # handles production cloud infra
        "overrides": {
            "4.15": ("No", "MFA not enforced for all end-user roles; rollout planned Q1 2026."),  # GAP
        },
        "default_answer": "Yes",
    },
    "apex_payments": {
        "name": "Apex Payments LLC (fictional)",
        "criticality": "high",  # payments processor
        "overrides": {
            "4.1": ("No", "Certification lapsed; SOC 2 Type II renewal in progress, not yet issued."),  # GAP
            "4.25": ("Alternate", "Incident response handled by parent company's shared CSIRT; no dedicated team."),
            "8.3": ("No", "No formal business continuity plan on file."),  # GAP
        },
        "default_answer": "Yes",
    },
    "redbridge_data": {
        "name": "Redbridge Data Analytics (fictional)",
        "criticality": "medium",
        "overrides": {
            "2.5": ("No", "No bill of materials provided for software components."),  # GAP
            "4.21": ("No", "No centralized incident detection/logging described."),  # GAP
            "6.9": ("No", "No formal annual SCRM training requirement for personnel."),  # GAP
            "7.1": ("N/A", "Vendor states product integrity standards not applicable to their offering."),
        },
        "default_answer": "Alternate",
    },
}


def main():
    for vendor_key, profile in VENDOR_PROFILES.items():
        out_dir = OUT_DIR / vendor_key
        out_dir.mkdir(parents=True, exist_ok=True)
        rows = []
        for q in QUESTIONS:
            qid = q["question_id"]
            if qid in profile["overrides"]:
                answer, notes = profile["overrides"][qid]
            else:
                answer, notes = profile["default_answer"], ""
            rows.append({
                "vendor": profile["name"], "question_id": qid, "category": q["category"],
                "subcategory": q["subcategory"], "question_text": q["question_text"],
                "answer": answer, "notes": notes,
            })

        out_path = out_dir / "scrm_questionnaire_responses.csv"
        with open(out_path, "w", newline="") as f:
            f.write(f"# {NOTICE}\n")
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {out_path} ({len(rows)} responses, criticality={profile['criticality']})")


if __name__ == "__main__":
    main()
