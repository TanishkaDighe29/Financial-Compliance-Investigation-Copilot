# Data Sources — Financial Compliance Investigation Copilot

Every source below is real, public, and free. Nothing here requires a paid
account, an API key, or scraping behind a login wall.

## 1. Control frameworks (requirements layer)
| Source | Link | Used for |
|---|---|---|
| NIST Cybersecurity Framework 2.0 | https://www.nist.gov/cyberframework | Dashboard taxonomy: Govern/Identify/Protect/Detect/Respond/Recover |
| NIST CSF 2.0 overview PDF | https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf | Reference doc |
| NIST SP 800-53 Rev5 (publication) | https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final | Control library |
| NIST SP 800-53 Rev5 downloads (PDF/CSV/XML) | https://csrc.nist.gov/projects/risk-management/sp800-53-controls/downloads | Alternate download formats |
| NIST SP 800-53A Rev5 (assessment procedures) | https://csrc.nist.gov/pubs/sp/800/53/a/r5/final | Assessment-objective language |
| **OSCAL homepage** | https://pages.nist.gov/OSCAL/ | Machine-readable format spec |
| **OSCAL content repo (what this project actually downloads)** | https://github.com/usnistgov/oscal-content | `scripts/import_nist_controls.py` pulls this directly |
| NIST SP 800-53 Rev5 OSCAL catalog JSON (exact file used) | https://raw.githubusercontent.com/usnistgov/oscal-content/main/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog.json | Downloaded to `data/frameworks/oscal/` |

## 2. SEC filing data (real public-company disclosures)
| Source | Link | Used for |
|---|---|---|
| SEC EDGAR full-text search | https://www.sec.gov/edgar/search/ | Manual lookup / verification |
| SEC EDGAR APIs overview | https://www.sec.gov/search-filings/edgar-application-programming-interfaces | `submissions` + `companyfacts` endpoints |
| SEC company ticker → CIK mapping (exact file used) | https://www.sec.gov/files/company_tickers.json | `data/raw/sec_edgar/filings_metadata/company_tickers_subset.json` |
| SEC submissions API (per company) | https://data.sec.gov/submissions/CIK##########.json | `scripts/download_sec_filings.py` |
| SEC cybersecurity disclosure rule (Item 1C) | https://www.sec.gov/files/rules/final/2023/33-11216.pdf | SEC module framing |
| SEC cybersecurity compliance guide | https://www.sec.gov/resources-small-businesses/small-business-compliance-guides/cybersecurity-risk-management-strategy-governance-incident-disclosure | Reference |

Companies selected for sector diversity (real CIKs, verified against the live
`company_tickers.json` on 2026-09-13): **JPM** (banking), **WFC** (banking),
**V** (payments), **MA** (payments), **COIN** (fintech/crypto), **CRWD**
(cloud/cybersecurity software). Run `scripts/download_sec_filings.py --email you@example.com`
to fetch their actual latest 10-Ks (not included in this scaffold to keep it
small and because SEC asks that you fetch with your own identified User-Agent).

**Real facts already extracted and verified (2026-09-14)** from CrowdStrike's
actual 10-K filings — see `data/raw/sec_edgar/filings_metadata/sec_risk_signals.csv`
for the sourced, factual data (net loss, headcount, revenue, and the real
July 19, 2024 Falcon sensor incident disclosed as an ongoing risk factor).
Only factual figures and paraphrased descriptions are stored, never the
filing's copyrighted prose verbatim — see the note at the top of that CSV.

## 3. Vendor-risk template
| Source | Link |
|---|---|
| CISA Vendor SCRM Template | https://www.cisa.gov/resources-tools/resources/vendor-supply-chain-risk-management-scrm-template |
| CISA SMB Vendor SCRM Template + spreadsheet | https://www.cisa.gov/resources-tools/resources/operationalizing-vendor-scrm-template-smbs |
| **CISA Vendor SCRM Template PDF (exact document used)** | https://www.cisa.gov/sites/default/files/publications/ICTSCRMTF_Vendor-SCRM-Template_508.pdf |

**Real questions extracted (2026-09-14)** from the actual CISA template
(a U.S. federal government work — public domain, not copyrighted) into
`data/frameworks/cisa_scrm/scrm_questions.csv`: 15 questions spanning Supply
Chain Management, Secure Design, Information Security, Physical Security,
Personnel Security, Supply Chain Integrity, and Supply Chain Resilience.
Three fictional vendors (Northstar CloudSec, Apex Payments, Redbridge Data)
have synthetic, seeded answers with planted gaps — see
`scripts/generate_vendor_responses.py` and `docs/data_governance.md`.

## 4. Threat-intel enrichment (optional, later module)
| Source | Link |
|---|---|
| CISA Known Exploited Vulnerabilities catalog | https://www.cisa.gov/known-exploited-vulnerabilities-catalog |
| CISA KEV GitHub data repo | https://github.com/cisagov/kev-data |

## 5. Synthetic data (no external link — generated locally)
`scripts/generate_synthetic_evidence.py` (access-control policies/evidence)
and `scripts/generate_vendor_responses.py` (vendor SCRM questionnaire
answers) are fully synthetic, seeded for reproducibility, and labeled per
`docs/data_governance.md`.

## What's already downloaded in this scaffold vs. what you run yourself
- **Already downloaded/extracted (real data, present in this repo):** the
  full official NIST SP 800-53 Rev5 OSCAL catalog, the extracted 22-control
  subset CSV, the verified real CIK/ticker subset for 6 SEC filers, real
  facts extracted from CrowdStrike's actual FY2022/FY2025 10-Ks
  (`sec_risk_signals.csv`), and 15 real questions extracted from the actual
  CISA Vendor SCRM Template PDF.
- **You run locally:** `scripts/download_sec_filings.py` (needs your email in
  the User-Agent per SEC's access rules) to pull the actual 10-K HTML for
  the other 5 tickers and extend SEC coverage beyond CRWD.
