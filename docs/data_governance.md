# Data Governance Statement

This project uses only:
1. **Publicly available regulatory/framework material** — NIST SP 800-53
   Rev5 (official OSCAL catalog; NIST CSF 2.0 function names are used only
   as an editorial grouping label in code, not as a separately stored
   dataset) and the CISA Vendor SCRM Template (public-domain U.S.
   government work).
2. **Publicly accessible SEC EDGAR filings** — live-fetched CrowdStrike
   10-Ks (FY2022, FY2025), plus a downloader script
   (`scripts/download_sec_filings.py`) for 6 sector-diverse public
   companies' filings from `data.sec.gov` and `www.sec.gov`.
3. **Synthetic internal compliance artifacts**, created solely for
   demonstration (`scripts/generate_synthetic_evidence.py` for access
   control, `scripts/generate_vendor_responses.py` for fictional vendors
   answering the real CISA questions). Every synthetic file carries the
   notice: *"Synthetic sample created solely for portfolio demonstration.
   This document contains no real company, client, employee, customer,
   vendor, financial, security, or confidential data."*

It contains **no client, employer, customer, employee, personal, confidential,
or nonpublic financial data**. This is an educational decision-support
prototype and does **not** provide legal, audit, compliance, security, or
investment advice.

## Provenance ledger
| Artifact | Real or synthetic | Source |
|---|---|---|
| `data/frameworks/oscal/NIST_SP-800-53_rev5_catalog.json` | Real | github.com/usnistgov/oscal-content (official NIST repo) |
| `data/frameworks/nist_sp_800_53/controls.csv` | Real (extracted subset) | Derived from the file above |
| `data/frameworks/cisa_scrm/scrm_questions.csv` | Real | CISA Vendor SCRM Template PDF (public-domain U.S. government work) |
| `data/raw/sec_edgar/filings_metadata/company_tickers_subset.json` | Real | sec.gov/files/company_tickers.json |
| `data/raw/sec_edgar/filings_metadata/sec_risk_signals.csv` | Real (extracted facts, no verbatim filing text) | Live-fetched CrowdStrike 10-Ks (FY2022, FY2025) via SEC EDGAR |
| `data/raw/sec_edgar/filings_html/*` (populated when you run the downloader) | Real | data.sec.gov + sec.gov EDGAR archives |
| `data/sample_documents/access_control/**` | Synthetic | Generated locally, seeded (`random.seed(42)`) for reproducibility |
| `data/sample_documents/vendor_risk/**/scrm_questionnaire_responses.csv` | Synthetic (answers) to real questions | Three fictional vendors answering the real CISA template questions above |
| `backend/tests/fixtures/sample_10k_synthetic.html` | Synthetic | Fabricated 10-K structure ("Northstar CloudSec, Inc.") for testing `sec_filing_parser.py` without reproducing a real filing's text |
