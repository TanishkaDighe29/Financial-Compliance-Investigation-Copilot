"""
Download REAL SEC EDGAR 10-K filings (Item 1A Risk Factors + Item 1C Cybersecurity)
for a small, sector-diverse set of public companies.

This uses only official, public, zero-cost SEC sources:
  - https://www.sec.gov/files/company_tickers.json  (ticker -> CIK)
  - https://data.sec.gov/submissions/CIK##########.json  (filing history)
  - https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}  (filing text)

SEC access rules (see https://www.sec.gov/os/webmaster-faq#developers):
  - Must send a descriptive User-Agent with a real contact.
  - Do not hammer the API -- this script sleeps between requests and caches
    results to data/raw/sec_edgar/.

USAGE:
    python scripts/download_sec_filings.py --email you@example.com

Edit YOUR_NAME / YOUR_EMAIL below or pass --email.
"""
import argparse
import json
import time
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
COMPANIES = json.load(open(ROOT / "data/raw/sec_edgar/filings_metadata/company_tickers_subset.json"))["companies"]

OUT_HTML = ROOT / "data/raw/sec_edgar/filings_html"
OUT_META = ROOT / "data/raw/sec_edgar/filings_metadata"


def fetch(url: str, user_agent: str) -> bytes:
    req = Request(url, headers={"User-Agent": user_agent})
    with urlopen(req, timeout=30) as resp:
        return resp.read()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True, help="Your email, required by SEC's fair-access policy")
    parser.add_argument("--name", default="Financial Compliance Copilot (portfolio project)")
    args = parser.parse_args()
    user_agent = f"{args.name} {args.email}"

    OUT_HTML.mkdir(parents=True, exist_ok=True)
    OUT_META.mkdir(parents=True, exist_ok=True)

    for company in COMPANIES:
        cik = company["cik"]
        cik_padded = str(cik).zfill(10)
        print(f"\n=== {company['ticker']} (CIK {cik}) ===")

        submissions_url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
        data = json.loads(fetch(submissions_url, user_agent))
        (OUT_META / f"{company['ticker']}_submissions.json").write_text(json.dumps(data, indent=2))

        recent = data["filings"]["recent"]
        forms = recent["form"]
        accessions = recent["accessionNumber"]
        docs = recent["primaryDocument"]
        dates = recent["filingDate"]

        # find the most recent 10-K
        found = False
        for form, accession, doc, filed in zip(forms, accessions, docs, dates):
            if form == "10-K":
                accession_nodash = accession.replace("-", "")
                filing_url = (
                    f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_nodash}/{doc}"
                )
                print(f"  Latest 10-K: {filed}  {filing_url}")
                time.sleep(0.4)  # be polite to SEC servers
                html = fetch(filing_url, user_agent)
                out_path = OUT_HTML / f"{company['ticker']}_10K_{filed}.html"
                out_path.write_bytes(html)
                print(f"  Saved -> {out_path}")
                found = True
                break
        if not found:
            print("  No 10-K found in recent filings window.")
        time.sleep(0.4)

    print("\nDone. Next: run scripts/parse_documents.py to extract Item 1A / Item 1C sections.")


if __name__ == "__main__":
    main()
