"""
SQLite engine/session setup, plus a one-time sync of the JSONL chunk store
into the documents/document_chunks tables (so findings can foreign-key to a
persisted chunk even though ingestion itself still writes JSONL as its
source of truth -- swapping JSONL for a real object store is a Phase-3+
follow-up, not required to get persistence working end to end today).
"""
import json
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.db.models import Base, Document, DocumentChunk

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data/db/compliance.db"
CHUNKS_PATH = ROOT / "data/processed/chunks/chunks.jsonl"

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)


def sync_chunks_to_db():
    """Idempotent: creates one Document per distinct filename and one
    DocumentChunk per chunk_id, skipping ones that already exist."""
    if not CHUNKS_PATH.exists():
        return 0
    session = SessionLocal()
    try:
        existing_chunk_ids = {c[0] for c in session.query(DocumentChunk.id).all()}
        doc_by_name = {d.filename: d for d in session.query(Document).all()}

        new_chunks = 0
        with open(CHUNKS_PATH) as f:
            for line in f:
                c = json.loads(line)
                if c["chunk_id"] in existing_chunk_ids:
                    continue
                doc = doc_by_name.get(c["document_name"])
                if doc is None:
                    doc = Document(
                        filename=c["document_name"],
                        document_type=c["document_type"],
                        source_path=c["metadata"].get("source_path", ""),
                    )
                    session.add(doc)
                    session.flush()
                    doc_by_name[c["document_name"]] = doc
                session.add(DocumentChunk(
                    id=c["chunk_id"], document_id=doc.id,
                    section_or_row=c["section_or_row"], text=c["text"],
                    chunk_metadata=c["metadata"],
                ))
                new_chunks += 1
        session.commit()
        return new_chunks
    finally:
        session.close()
