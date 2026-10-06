"""
Ingestion: turn the raw sample documents (CSV evidence, Markdown policies)
into page/row-level chunks with metadata, ready for indexing.

Real, minimal implementation for v1 scope: CSV rows -> one chunk per row
(grouped in small batches for context), Markdown files -> one chunk per
section (## heading).
"""
import csv
import re
import json
from pathlib import Path
from dataclasses import dataclass, asdict

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data/sample_documents"
FRAMEWORKS_DIR = ROOT / "data/frameworks"
OUT_PATH = ROOT / "data/processed/chunks/chunks.jsonl"


@dataclass
class Chunk:
    chunk_id: str
    document_name: str
    document_type: str  # policy | evidence_csv | control_catalog
    section_or_row: str
    text: str
    metadata: dict


def chunk_markdown(path: Path, doc_type="policy"):
    text = path.read_text()
    # split on '## ' headers
    sections = re.split(r"\n(?=## )", text)
    chunks = []
    for i, section in enumerate(sections):
        section = section.strip()
        if not section or section.startswith(">"):
            continue
        title_match = re.match(r"##\s*(.+)", section)
        title = title_match.group(1) if title_match else f"section_{i}"
        chunks.append(Chunk(
            chunk_id=f"{path.stem}_{i:03d}",
            document_name=path.name,
            document_type=doc_type,
            section_or_row=title,
            text=section,
            metadata={"source_path": str(path.relative_to(ROOT))},
        ))
    return chunks


def chunk_csv(path: Path, doc_type="evidence_csv", rows_per_chunk=4):
    with open(path) as f:
        lines = [l for l in f if not l.startswith("#")]
    reader = csv.DictReader(lines)
    rows = list(reader)
    chunks = []
    # Use parent-dir prefix too: several vendor_risk/<vendor>/ subfolders share the
    # same filename (scrm_questionnaire_responses.csv), so path.stem alone collides.
    id_prefix = f"{path.parent.name}_{path.stem}" if path.parent.name != DATA_DIR.name else path.stem
    display_name = f"{path.parent.name}/{path.name}" if path.parent.name != DATA_DIR.name else path.name
    for i in range(0, len(rows), rows_per_chunk):
        batch = rows[i:i + rows_per_chunk]
        text_lines = [", ".join(f"{k}={v}" for k, v in r.items()) for r in batch]
        text = f"Evidence file: {display_name}\n" + "\n".join(text_lines)
        chunks.append(Chunk(
            chunk_id=f"{id_prefix}_{i:04d}",
            document_name=display_name,
            document_type=doc_type,
            section_or_row=f"rows_{i}-{i+len(batch)-1}",
            text=text,
            metadata={"source_path": str(path.relative_to(ROOT)), "row_count": len(batch)},
        ))
    return chunks


def chunk_controls_csv(path: Path):
    with open(path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    chunks = []
    for r in rows:
        text = (
            f"NIST SP 800-53 Rev5 Control {r['control_id']} ({r['control_name']}): "
            f"{r['requirement_text']} Assessment objective: {r['assessment_objective']}"
        )
        chunks.append(Chunk(
            chunk_id=f"control_{r['control_id']}",
            document_name="controls.csv",
            document_type="control_catalog",
            section_or_row=r["control_id"],
            text=text,
            metadata={"control_family": r["control_family"], "nist_csf_function": r["nist_csf_function"],
                      "source": r["source"]},
        ))
    return chunks


def main():
    all_chunks = []

    for md_path in (DATA_DIR / "access_control/policy").glob("*.md"):
        all_chunks.extend(chunk_markdown(md_path))

    for csv_path in (DATA_DIR / "access_control/evidence").glob("*.csv"):
        all_chunks.extend(chunk_csv(csv_path))

    for csv_path in (DATA_DIR / "access_control/metadata").glob("*.csv"):
        all_chunks.extend(chunk_csv(csv_path, doc_type="metadata_csv", rows_per_chunk=6))

    sec_signals_path = ROOT / "data/raw/sec_edgar/filings_metadata/sec_risk_signals.csv"
    if sec_signals_path.exists():
        all_chunks.extend(chunk_csv(sec_signals_path, doc_type="sec_risk_signal", rows_per_chunk=1))

    for csv_path in (DATA_DIR / "vendor_risk").glob("*/scrm_questionnaire_responses.csv"):
        all_chunks.extend(chunk_csv(csv_path, doc_type="vendor_scrm_response", rows_per_chunk=1))

    controls_path = FRAMEWORKS_DIR / "nist_sp_800_53/controls.csv"
    if controls_path.exists():
        all_chunks.extend(chunk_controls_csv(controls_path))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        for c in all_chunks:
            f.write(json.dumps(asdict(c)) + "\n")

    print(f"Wrote {len(all_chunks)} chunks to {OUT_PATH}")
    by_type = {}
    for c in all_chunks:
        by_type[c.document_type] = by_type.get(c.document_type, 0) + 1
    for t, n in by_type.items():
        print(f"  {t}: {n}")


if __name__ == "__main__":
    main()
