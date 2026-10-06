"""
Extract a working subset of REAL NIST SP 800-53 Rev5 controls from the
official OSCAL catalog into a flat controls.csv for the compliance copilot.

Source (real, official, zero-cost):
https://github.com/usnistgov/oscal-content/blob/main/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog.json
"""
import json
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "data/frameworks/oscal/NIST_SP-800-53_rev5_catalog.json"
OUT_CSV = ROOT / "data/frameworks/nist_sp_800_53/controls.csv"

# Families we actually use in v1 (Access Control module + related)
WANTED_FAMILIES = {"ac", "ia", "au", "ir", "ra", "sr", "cm"}

# Map control family prefix -> NIST CSF 2.0 function (manual, documented mapping
# used only for dashboard grouping -- this mapping is our own editorial choice,
# not an official NIST crosswalk).
CSF_FUNCTION_MAP = {
    "ac": "Protect", "ia": "Protect", "au": "Detect", "ir": "Respond",
    "ra": "Identify", "sr": "Govern", "cm": "Protect",
}

# Controls we specifically want for the Access-Control Evidence Review v1 demo
PRIORITY_CONTROL_IDS = {
    "ac-2", "ac-3", "ac-5", "ac-6", "ac-17", "ac-2.1", "ac-6.1", "ac-6.2",
    "ia-2", "ia-2.1", "ia-5",
    "au-6", "au-2", "au-12",
    "ir-4", "ir-8",
    "ra-5", "ra-3",
    "sr-6", "sr-2",
    "cm-3", "cm-6",
}


def get_prop(props, name, default=""):
    for p in props or []:
        if p.get("name") == name:
            return p.get("value", default)
    return default


def get_part_prose(parts, name):
    for p in parts or []:
        if p.get("name") == name:
            return (p.get("prose") or "").strip()
    return ""


def walk_controls(controls, family_id, out):
    for ctrl in controls or []:
        ctrl_id = ctrl.get("id", "")
        if ctrl_id.lower() not in PRIORITY_CONTROL_IDS:
            # still recurse into enhancements in case an enhancement is on the list
            for sub in ctrl.get("controls", []) or []:
                walk_controls([sub], family_id, out)
            continue
        title = ctrl.get("title", "")
        parts = ctrl.get("parts", [])
        statement = get_part_prose(parts, "statement")
        assessment_objective = get_part_prose(parts, "assessment-objective")
        params = ctrl.get("params", [])
        out.append({
            "control_id": ctrl_id.upper(),
            "control_family": family_id.upper(),
            "control_name": title,
            "requirement_text": statement[:1200].replace("\n", " ").strip(),
            "assessment_objective": assessment_objective[:600].replace("\n", " ").strip(),
            "nist_csf_function": CSF_FUNCTION_MAP.get(family_id, ""),
            "source": "NIST SP 800-53 Rev 5 (OSCAL catalog, usnistgov/oscal-content)",
        })
        for sub in ctrl.get("controls", []) or []:
            walk_controls([sub], family_id, out)


def main():
    with open(CATALOG_PATH) as f:
        data = json.load(f)

    groups = data["catalog"]["groups"]
    rows = []
    for group in groups:
        family_id = group.get("id", "").lower()
        if family_id not in WANTED_FAMILIES:
            continue
        walk_controls(group.get("controls", []), family_id, rows)

    rows.sort(key=lambda r: r["control_id"])
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "control_id", "control_family", "control_name",
            "requirement_text", "assessment_objective",
            "nist_csf_function", "source",
        ])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} real NIST SP 800-53 Rev5 controls to {OUT_CSV}")
    for r in rows:
        print(f"  {r['control_id']}: {r['control_name']}")


if __name__ == "__main__":
    main()
