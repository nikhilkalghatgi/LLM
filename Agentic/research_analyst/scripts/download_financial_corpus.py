"""Download REAL public financial PDFs for the corpus (best-effort, online).

These are public regulatory/filing URLs. They can change or rate-limit, so this
script is best-effort: anything that fails is skipped with a warning, and you can
always fall back to ``make_financial_corpus.py`` for an offline-safe corpus.

Run::

    python -m scripts.download_financial_corpus
    python -m scripts.download_financial_corpus --to-inbox risk-team

Only public, non-paywalled documents are listed. Verify you are permitted to use
any document for your purpose before ingesting it.
"""

import argparse
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import load_config

# Public document URLs. Edit/extend freely. Kept short and well-known.
SOURCES = {
    # RBI — Basel III capital regulations master direction (public).
    "rbi_basel_iii_master_direction.pdf":
        "https://rbidocs.rbi.org.in/rdocs/notification/PDFs/"
        "MD1234BASELIII.pdf",
    # SEBI — LODR (public). Placeholder path; replace with a current link if it 404s.
    "sebi_lodr_circular.pdf":
        "https://www.sebi.gov.in/sebi_data/attachdocs/lodr.pdf",
}

_HEADERS = {"User-Agent": "research-analyst-corpus/1.0 (educational use)"}


def _download(url: str, dest: str, timeout: int = 30) -> bool:
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
        if not data[:4] == b"%PDF":
            print(f"[Download] Skipped (not a PDF): {url}")
            return False
        with open(dest, "wb") as fh:
            fh.write(data)
        print(f"[Download] Saved {dest} ({len(data)//1024} KB)")
        return True
    except Exception as exc:  # network/HTTP errors are expected & non-fatal
        print(f"[Download] FAILED {url}\n            -> {exc}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Download public financial PDFs.")
    parser.add_argument("--to-inbox", metavar="TENANT_ID",
                        help="Copy downloads into inbox/<TENANT_ID>/ for the watcher.")
    args = parser.parse_args()

    config = load_config()
    out_dir = os.path.join(config["paths"]["sample_pdfs"], "financial")
    os.makedirs(out_dir, exist_ok=True)

    ok = []
    for filename, url in SOURCES.items():
        dest = os.path.join(out_dir, filename)
        if _download(url, dest):
            ok.append(dest)

    if not ok:
        print("\n[Download] No PDFs fetched. Run "
              "`python -m scripts.make_financial_corpus` for an offline corpus.")
        return

    if args.to_inbox:
        inbox_dir = os.path.join(config["paths"]["inbox"], args.to_inbox)
        os.makedirs(inbox_dir, exist_ok=True)
        for path in ok:
            dest = os.path.join(inbox_dir, os.path.basename(path))
            with open(path, "rb") as src, open(dest, "wb") as dst:
                dst.write(src.read())
            print(f"[Download] Copied to inbox: {dest}")

    print(f"\n[Download] Done. {len(ok)} PDFs in {out_dir}")


if __name__ == "__main__":
    main()
