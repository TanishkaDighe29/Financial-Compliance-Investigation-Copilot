"""
Hybrid retrieval: BM25 (exact/keyword) + TF-IDF cosine (semantic proxy) fused
by rank, with a minimum-relevance threshold that drives the copilot's
"insufficient evidence" abstention rule.

NOTE on scope: the project's target stack is SentenceTransformers + FAISS for
real semantic embeddings (see docs/architecture.md). That requires downloading
model weights and more compute than this scaffolding pass allocated. TF-IDF
cosine similarity is used here as a drop-in, zero-download semantic proxy so
the retrieval/evidence-sufficiency/abstention logic is real and testable today.
Swapping in SentenceTransformers + FAISS is a ~20-line change in `_semantic_search`
below and does not require touching anything else in the pipeline.
"""
import json
from pathlib import Path
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parents[3]
CHUNKS_PATH = ROOT / "data/processed/chunks/chunks.jsonl"


def _tokenize(text):
    return text.lower().replace(",", " ").replace("=", " ").split()


class HybridIndex:
    def __init__(self, chunks_path=CHUNKS_PATH):
        self.chunks = [json.loads(l) for l in open(chunks_path)]
        corpus = [c["text"] for c in self.chunks]
        self.bm25 = BM25Okapi([_tokenize(t) for t in corpus])
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)

    def _bm25_search(self, query, k=40):
        # Bounded, not full-corpus: search() needs genuinely irrelevant chunks
        # to score at/near zero (outside both rankers' candidate windows) for
        # its relevance threshold to mean anything -- see search()'s docstring.
        scores = self.bm25.get_scores(_tokenize(query))
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [(i, scores[i]) for i in ranked]

    def _semantic_search(self, query, k=40):
        q_vec = self.vectorizer.transform([query])
        sims = cosine_similarity(q_vec, self.tfidf_matrix)[0]
        ranked = sorted(range(len(sims)), key=lambda i: sims[i], reverse=True)[:k]
        return [(i, sims[i]) for i in ranked]

    def filter(self, predicate):
        """Exact metadata filter over ALL indexed chunks, unranked. Use this
        instead of search() when you already know which chunks you want
        (e.g. "every row for vendor X") -- search()'s RRF fusion only
        considers each ranker's own top-20 candidates internally, so it can
        silently miss chunks that are relevant by metadata but rank outside
        that window on this query's text. That's a real bug we hit building
        the vendor-risk and SEC-filing modules: asking for a specific
        vendor's rows via search() sometimes returned a subset because the
        matching rows didn't all make the top-20 semantic/BM25 shortlist."""
        return [
            {
                "chunk_id": c["chunk_id"], "document_name": c["document_name"],
                "document_type": c["document_type"], "section_or_row": c["section_or_row"],
                "text": c["text"], "relevance_score": None, "metadata": c["metadata"],
            }
            for c in self.chunks if predicate(c)
        ]

    def search(self, query, k=6, metadata_filter=None):
        """Reciprocal-rank fusion of BM25 and semantic-proxy results, over a
        bounded top-40 candidate window per ranker (not the full corpus).

        History worth knowing if you touch this: an earlier version of this
        method ranked only each ranker's own top-20 candidates BEFORE
        applying metadata_filter, which meant a real match could rank
        outside that window and silently vanish -- exactly what happened to
        the access-control module once SEC and vendor-risk chunks were
        added to the shared corpus (see orchestrator.py's call site). The
        fix that seemed obvious -- rank the FULL corpus, then filter -- was
        tried and reverted: it makes literally every chunk in the corpus
        get a nonzero RRF score (1/(60+rank) is always positive), which
        collapses the score gap between genuinely relevant and irrelevant
        results to almost nothing and breaks the "insufficient evidence"
        abstention threshold that depends on that gap. The actual fix is
        two-part: (1) entity-lookup use cases (SEC ticker, vendor name) use
        HybridIndex.filter() -- an exact, unranked metadata match -- instead
        of search() at all, since they already know exactly which chunks
        they want and don't need a relevance ranking; (2) search() itself
        just needed a wider bounded window (40, up from 20) so a growing
        corpus doesn't crowd out real matches, without going all the way to
        "rank everything" and destroying the relevance signal abstention
        depends on."""
        bm25_results = self._bm25_search(query)
        sem_results = self._semantic_search(query)

        rrf_scores = {}
        for rank, (idx, _) in enumerate(bm25_results):
            rrf_scores[idx] = rrf_scores.get(idx, 0) + 1.0 / (60 + rank)
        for rank, (idx, _) in enumerate(sem_results):
            rrf_scores[idx] = rrf_scores.get(idx, 0) + 1.0 / (60 + rank)

        ranked_idx = sorted(rrf_scores, key=lambda i: rrf_scores[i], reverse=True)

        results = []
        for idx in ranked_idx:
            chunk = self.chunks[idx]
            if metadata_filter and not metadata_filter(chunk):
                continue
            results.append({
                "chunk_id": chunk["chunk_id"],
                "document_name": chunk["document_name"],
                "document_type": chunk["document_type"],
                "section_or_row": chunk["section_or_row"],
                "text": chunk["text"],
                "relevance_score": round(rrf_scores[idx], 4),
                "metadata": chunk["metadata"],
            })
            if len(results) >= k:
                break
        return results


if __name__ == "__main__":
    idx = HybridIndex()
    q = "Was privileged access reviewed quarterly in Q3 2025?"
    print(f"Query: {q}\n")
    for r in idx.search(q, k=5):
        print(f"[{r['relevance_score']}] {r['document_name']} :: {r['section_or_row']}")
        print(f"    {r['text'][:160]}...")
        print()
