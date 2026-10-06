"""
Parse a downloaded 10-K HTML file (from scripts/download_sec_filings.py) into
labeled sections, then run a keyword-based risk-flag scan over Item 1A (Risk
Factors) and Item 1C (Cybersecurity, if present -- required since FY2023).

This is real, generic parsing logic -- it works on any real 10-K you download
locally. It is NOT tested here against a bundled real filing, because storing
a real company's risk-factor prose in this repo would reproduce copyrighted
text; instead it's tested against `tests/fixtures/sample_10k_synthetic.html`,
a fabricated filing with the same structure, and validated manually against
a real fetch during development (see docs/DATA_SOURCES.md's provenance notes
and data/raw/sec_edgar/filings_metadata/sec_risk_signals.csv for the real,
factual, sourced findings from that validation).
"""
import re
from bs4 import BeautifulSoup

ITEM_PATTERNS = {
    "item_1a_risk_factors": r"item\s*1a\.?\s*risk factors",
    "item_1c_cybersecurity": r"item\s*1c\.?\s*cybersecurity",
    "item_1b_end": r"item\s*1b\.?\s*unresolved staff comments",
    "item_2_end": r"item\s*2\.?\s*properties",
}

RISK_KEYWORDS = {
    "material_weakness": ["material weakness", "significant deficiency"],
    "data_breach_or_incident": ["data breach", "security incident", "unauthorized access",
                                 "cyberattack", "cyber incident", "system outage", "service disruption"],
    "going_concern": ["going concern", "substantial doubt"],
    "litigation_or_investigation": ["class action", "securities litigation", "sec investigation",
                                     "government investigation", "subpoena"],
    "restatement": ["restate", "restatement of our", "correction of an error"],
    "regulatory_action": ["consent order", "regulatory action", "cease and desist", "civil penalty"],
}


def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ")).strip()


def extract_section(full_text: str, start_pattern: str, end_patterns: list) -> str:
    start_match = re.search(start_pattern, full_text, re.IGNORECASE)
    if not start_match:
        return ""
    start = start_match.start()
    end = len(full_text)
    for pat in end_patterns:
        m = re.search(pat, full_text[start + 50:], re.IGNORECASE)
        if m:
            end = min(end, start + 50 + m.start())
    return full_text[start:end].strip()


def scan_risk_keywords(section_text: str) -> dict:
    lowered = section_text.lower()
    hits = {}
    for flag, keywords in RISK_KEYWORDS.items():
        matched = [kw for kw in keywords if kw in lowered]
        if matched:
            hits[flag] = matched
    return hits


def analyze_filing(html_path: str) -> dict:
    with open(html_path, encoding="utf-8", errors="ignore") as f:
        html = f.read()
    full_text = extract_text(html)

    risk_factors = extract_section(
        full_text, ITEM_PATTERNS["item_1a_risk_factors"],
        [ITEM_PATTERNS["item_1b_end"], ITEM_PATTERNS["item_2_end"]],
    )
    cybersecurity = extract_section(
        full_text, ITEM_PATTERNS["item_1c_cybersecurity"],
        [ITEM_PATTERNS["item_1b_end"], ITEM_PATTERNS["item_2_end"]],
    )

    return {
        "risk_factors_char_count": len(risk_factors),
        "cybersecurity_char_count": len(cybersecurity),
        "risk_keyword_flags": scan_risk_keywords(risk_factors),
        "cybersecurity_keyword_flags": scan_risk_keywords(cybersecurity),
        "risk_factors_excerpt": risk_factors[:200],
        "cybersecurity_excerpt": cybersecurity[:200],
    }


if __name__ == "__main__":
    import sys
    import json
    path = sys.argv[1] if len(sys.argv) > 1 else "backend/tests/fixtures/sample_10k_synthetic.html"
    print(json.dumps(analyze_filing(path), indent=2))
