"""Generate an OFFLINE-SAFE synthetic financial document corpus.

Banks hire for "regulatory document intelligence", not "PDF Q&A". This script
writes realistic (but synthetic) financial PDFs so the demo always runs even
without internet access:

* ``rbi_capital_adequacy_circular.pdf``  -- a mock RBI master circular
* ``basel_iii_summary.pdf``              -- a mock Basel III policy summary
* ``hdfc_style_annual_report_2024.pdf``  -- a mock bank annual report excerpt
* ``sebi_disclosure_circular.pdf``       -- a mock SEBI disclosure circular

Use the real downloader (``download_financial_corpus.py``) when you want actual
public filings. Run::

    python -m scripts.make_financial_corpus
    python -m scripts.make_financial_corpus --to-inbox risk-team
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from main import load_config


DOCS = {
    "rbi_capital_adequacy_circular.pdf": {
        "title": "Reserve Bank of India — Master Circular on Capital Adequacy (Synthetic)",
        "paragraphs": [
            "1. Minimum Capital Requirements. Every commercial bank shall maintain a "
            "minimum total Capital to Risk-weighted Assets Ratio (CRAR) of 9 per cent on "
            "an ongoing basis. The Common Equity Tier 1 (CET1) capital ratio shall be at "
            "least 5.5 per cent of risk-weighted assets.",
            "2. Capital Conservation Buffer. In addition to the minimum CRAR, banks shall "
            "maintain a Capital Conservation Buffer (CCB) of 2.5 per cent of risk-weighted "
            "assets in the form of Common Equity Tier 1 capital. The CCB is designed to "
            "ensure that banks build up capital buffers during normal times which can be "
            "drawn down as losses are incurred during a stressed period.",
            "3. Tier 1 and Tier 2 Capital. Tier 1 capital comprises Common Equity Tier 1 "
            "and Additional Tier 1 capital. Tier 2 capital includes general provisions and "
            "subordinated debt instruments with a minimum original maturity of five years.",
            "4. Leverage Ratio. Banks shall maintain a minimum leverage ratio of 3.5 per "
            "cent for Domestic Systemically Important Banks and 4 per cent for other banks, "
            "computed as Tier 1 capital divided by the total exposure measure.",
            "5. Risk-Weighted Assets. Credit risk, market risk, and operational risk "
            "components shall be aggregated to compute total risk-weighted assets in "
            "accordance with the standardised approach prescribed herein.",
        ],
    },
    "basel_iii_summary.pdf": {
        "title": "Basel III Framework — Policy Summary (Synthetic)",
        "paragraphs": [
            "Overview. Basel III is an internationally agreed set of measures developed by "
            "the Basel Committee on Banking Supervision in response to the financial crisis "
            "of 2007-09. It strengthens bank capital requirements and introduces new "
            "regulatory requirements on bank liquidity and leverage.",
            "Liquidity Coverage Ratio (LCR). The LCR requires banks to hold a stock of "
            "high-quality liquid assets sufficient to cover total net cash outflows over a "
            "30-day stress period. The minimum LCR requirement is 100 per cent.",
            "Net Stable Funding Ratio (NSFR). The NSFR requires banks to maintain a stable "
            "funding profile in relation to the composition of their assets and off-balance "
            "sheet activities. The available stable funding must be at least 100 per cent of "
            "required stable funding over a one-year horizon.",
            "Countercyclical Buffer. National authorities may impose a countercyclical "
            "capital buffer of up to 2.5 per cent of risk-weighted assets when excess credit "
            "growth is judged to be associated with a build-up of system-wide risk.",
        ],
    },
    "hdfc_style_annual_report_2024.pdf": {
        "title": "Illustrative Bank — Annual Report 2024, Risk Disclosures (Synthetic)",
        "paragraphs": [
            "Risk Management Overview. The Bank's risk management framework covers credit "
            "risk, market risk, liquidity risk, operational risk, and reputational risk. The "
            "Risk Management Committee of the Board oversees the framework.",
            "Credit Risk Disclosure. Gross non-performing assets (GNPA) stood at 1.24 per "
            "cent of gross advances as at 31 March 2024, compared with 1.41 per cent in the "
            "prior year. The provision coverage ratio was 76 per cent.",
            "Capital Position. The Bank's total Capital Adequacy Ratio under Basel III was "
            "18.8 per cent as at 31 March 2024, with a CET1 ratio of 16.2 per cent, well "
            "above the regulatory minimum.",
            "Liquidity Risk Disclosure. The average Liquidity Coverage Ratio for the quarter "
            "ended March 2024 was 122 per cent, against the regulatory requirement of 100 "
            "per cent.",
            "Operational Risk. The Bank follows the standardised approach for operational "
            "risk capital and maintains a business continuity programme tested annually.",
        ],
    },
    "sebi_disclosure_circular.pdf": {
        "title": "SEBI — Circular on Continuous Disclosure Requirements (Synthetic)",
        "paragraphs": [
            "1. Applicability. This circular applies to all listed entities that have "
            "listed their specified securities on a recognised stock exchange.",
            "2. Material Events. Listed entities shall disclose to the stock exchanges all "
            "events or information which are material, within twenty-four hours of "
            "occurrence of the event.",
            "3. Financial Results. Quarterly and annual financial results shall be submitted "
            "within forty-five days of the end of each quarter, audited or with limited "
            "review by the statutory auditors.",
            "4. Related Party Transactions. All material related party transactions shall "
            "require prior approval of the shareholders through a resolution.",
        ],
    },
}


def _write_pdf(path: str, title: str, paragraphs) -> None:
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(path, pagesize=LETTER, title=title)
    story = [Paragraph(title, styles["Title"]), Spacer(1, 18)]
    for para in paragraphs:
        story.append(Paragraph(para, styles["BodyText"]))
        story.append(Spacer(1, 12))
    doc.build(story)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic financial PDFs.")
    parser.add_argument(
        "--to-inbox",
        metavar="TENANT_ID",
        help="Also copy generated PDFs into inbox/<TENANT_ID>/ for the watcher.",
    )
    args = parser.parse_args()

    config = load_config()
    out_dir = os.path.join(config["paths"]["sample_pdfs"], "financial")
    os.makedirs(out_dir, exist_ok=True)

    written = []
    for filename, spec in DOCS.items():
        path = os.path.join(out_dir, filename)
        _write_pdf(path, spec["title"], spec["paragraphs"])
        written.append(path)
        print(f"[Corpus] Wrote {path}")

    if args.to_inbox:
        inbox_dir = os.path.join(config["paths"]["inbox"], args.to_inbox)
        os.makedirs(inbox_dir, exist_ok=True)
        for path in written:
            dest = os.path.join(inbox_dir, os.path.basename(path))
            with open(path, "rb") as src, open(dest, "wb") as dst:
                dst.write(src.read())
            print(f"[Corpus] Copied to inbox: {dest}")

    print(f"\n[Corpus] Done. {len(written)} financial PDFs in {out_dir}")


if __name__ == "__main__":
    main()
