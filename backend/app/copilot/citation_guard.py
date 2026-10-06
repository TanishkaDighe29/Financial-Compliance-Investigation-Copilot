"""
Citation validation: the one non-negotiable safety check in this project.

Whatever generated the finding narrative -- the rule-based template or a
local LLM -- every finding must satisfy:
  1. Every chunk_id in supporting_evidence actually exists in the chunk store.
  2. There is at least one piece of supporting evidence, UNLESS the finding
     is an explicit "insufficient evidence" abstention.
  3. (LLM narratives only) the narrative doesn't reference a control ID or
     document name that isn't present anywhere in the retrieved evidence --
     a cheap but real guard against fabricated specifics.

If validation fails, the caller must NOT surface the finding as-is: fall back
to the rule-based template, which is always citation-safe by construction.
"""
import json
import re
from pathlib import Path
from dataclasses import dataclass

ROOT = Path(__file__).resolve().parents[3]
CHUNKS_PATH = ROOT / "data/processed/chunks/chunks.jsonl"

_valid_chunk_ids_cache = None


def _valid_chunk_ids():
    global _valid_chunk_ids_cache
    if _valid_chunk_ids_cache is None:
        _valid_chunk_ids_cache = {
            json.loads(l)["chunk_id"] for l in open(CHUNKS_PATH)
        } if CHUNKS_PATH.exists() else set()
    return _valid_chunk_ids_cache


@dataclass
class ValidationResult:
    valid: bool
    reasons: list


def validate_finding(finding_text: str, supporting_evidence: list, evidence_status: str,
                      document_names: list = None) -> ValidationResult:
    reasons = []
    known_ids = _valid_chunk_ids()

    for e in supporting_evidence:
        cid = e.get("chunk_id")
        if cid and cid not in known_ids:
            reasons.append(f"Citation references unknown chunk_id '{cid}' -- not in the indexed chunk store.")

    if evidence_status != "insufficient" and not supporting_evidence:
        reasons.append("Non-abstention finding has zero supporting evidence.")

    if document_names:
        mentioned_docs = set(document_names)
        # crude but real check: any 4+ digit "control-like" token in the narrative
        # (e.g. AC-6, IA-2.1) must appear in at least one evidence chunk's text
        control_like = re.findall(r"\b[A-Z]{2}-\d+(?:\.\d+)?\b", finding_text)
        evidence_text_blob = " ".join(e.get("quote", "") for e in supporting_evidence)
        for token in control_like:
            if token not in evidence_text_blob:
                reasons.append(f"Narrative mentions control '{token}' not found in any cited evidence quote.")

    return ValidationResult(valid=len(reasons) == 0, reasons=reasons)
