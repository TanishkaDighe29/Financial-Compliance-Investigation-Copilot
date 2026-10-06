# Financial Compliance Investigation Copilot -- single-container image.
# Serves the FastAPI API and the static reviewer dashboard (mounted at /ui)
# from one process/port, so `docker compose up` is the whole setup.
FROM python:3.12-slim

WORKDIR /app

# System deps: none beyond what pip needs (bs4/sklearn/rank-bm25 are pure
# Python or ship wheels). Keeping the base slim on purpose.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
COPY frontend/ frontend/
COPY data/ data/
COPY scripts/ scripts/

# data/db is where SQLite lives -- mounted as a volume in docker-compose.yml
# so investigations survive container restarts. Created here so the app
# doesn't need to mkdir it at runtime inside a read-only-by-default image.
RUN mkdir -p data/db

# Build the retrieval chunk index at image build time from whatever's in
# data/sample_documents, data/frameworks, and data/raw at build time. If you
# add new evidence/policy files, rebuild the image (or exec in and re-run
# this script -- see README's Docker section).
RUN python3 backend/app/ingestion/parsers.py

EXPOSE 8000

# Uses a plain healthcheck against the root endpoint -- no extra tooling needed.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/', timeout=3)" || exit 1

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
