"""
verify_scrape.py - Post-scrape verification report.

Run this immediately after 01_run_scraper.py to confirm that all important
categories and pages were scraped successfully.

Usage:
    python scripts/verify_scrape.py
"""
import sys
import glob
from pathlib import Path
from collections import defaultdict

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from config.constants import RAW_HTML_DIR, RAW_PDF_DIR, SCRAPER_TARGETS, CATEGORY_TO_NAMESPACE

# ─────────────────────────────────────────────────────────────────────────────
# ANSI colors for terminal output
# ─────────────────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):   print(f"  {GREEN}✓{RESET}  {msg}")
def warn(msg): print(f"  {YELLOW}!{RESET}  {msg}")
def fail(msg): print(f"  {RED}✗{RESET}  {msg}")
def head(msg): print(f"\n{BOLD}{CYAN}{msg}{RESET}")

# ─────────────────────────────────────────────────────────────────────────────
# Level 1 — File counts
# ─────────────────────────────────────────────────────────────────────────────
def check_file_counts():
    head("LEVEL 1 — FILE COUNTS")

    html_files = list(RAW_HTML_DIR.glob("*.html"))
    pdf_files  = list(RAW_PDF_DIR.glob("*.pdf"))

    print(f"  HTML files in data/raw/html/ : {BOLD}{len(html_files)}{RESET}")
    print(f"  PDF  files in data/raw/pdfs/ : {BOLD}{len(pdf_files)}{RESET}")

    # Count per category
    cat_counts = defaultdict(int)
    for f in html_files:
        for cat in SCRAPER_TARGETS:
            if f.name.startswith(cat):
                cat_counts[cat] += 1
                break

    print()
    for cat, urls in SCRAPER_TARGETS.items():
        expected = len(urls)
        actual   = cat_counts.get(cat, 0)
        pct      = int(actual / expected * 100) if expected else 0
        line     = f"  {cat:<20} {actual}/{expected} HTML files saved  ({pct}%)"
        if actual == expected:
            ok(line)
        elif actual > 0:
            warn(line)
        else:
            fail(line)

    return len(html_files), len(pdf_files)

# ─────────────────────────────────────────────────────────────────────────────
# Level 2 — Spot-check content of key files
# ─────────────────────────────────────────────────────────────────────────────
SPOT_CHECKS = [
    # (filename_prefix, must_contain_one_of, description)
    ("admissions_page_0", ["admission", "apply", "eligib", "program", "fee"],
     "Admissions page — should have program list or eligibility info"),

    ("fees_page_0", ["fee", "challan", "rupee", "structure", "semester"],
     "Fees page — should mention fee amounts or challan"),

    ("rules_policies_page_0", ["rule", "hostel", "regulation", "policy", "semester"],
     "Rules page — should have hostel or semester rules"),

    ("programs_classes_page_0", ["computer", "department", "semester", "degree", "faculty"],
     "Programs page — should have department or course info"),

    ("campus_admin_page_0", ["bannu", "university", "established", "campus", "contact"],
     "Campus page — should have university overview or contact info"),
]

def check_file_contents():
    head("LEVEL 2 — CONTENT SPOT CHECKS")

    all_html = list(RAW_HTML_DIR.glob("*.html"))
    file_map = {f.stem: f for f in all_html}

    passed = 0
    for prefix, keywords, desc in SPOT_CHECKS:
        # Find any file starting with this prefix
        matches = [f for stem, f in file_map.items() if stem.startswith(prefix)]
        if not matches:
            fail(f"{prefix}*.html — FILE NOT FOUND  |  {desc}")
            continue

        target = matches[0]
        content = target.read_text(encoding="utf-8", errors="ignore").lower()
        found   = [kw for kw in keywords if kw in content]

        if found:
            ok(f"{target.name} — contains '{found[0]}'  |  {desc}")
            passed += 1
        else:
            warn(f"{target.name} — CONTENT MISSING keywords {keywords}  |  {desc}")

    return passed

# ─────────────────────────────────────────────────────────────────────────────
# Level 3 — PDF verification
# ─────────────────────────────────────────────────────────────────────────────
IMPORTANT_PDF_KEYWORDS = {
    "fees"        : ["fee-structure", "fee_structure", "fees"],
    "rules"       : ["hostel", "regulation", "rules", "policy", "semester"],
    "admissions"  : ["merit", "merit_list", "merit-list"],
}

def check_pdfs():
    head("LEVEL 3 — PDF VERIFICATION")

    all_pdfs = list(RAW_PDF_DIR.glob("*.pdf"))
    if not all_pdfs:
        fail("NO PDFs found in data/raw/pdfs/ — the PDF downloader may not have run.")
        return 0

    ok(f"{len(all_pdfs)} total PDF files downloaded")

    # Group PDFs by category prefix
    cat_pdfs = defaultdict(list)
    for pdf in all_pdfs:
        for cat in SCRAPER_TARGETS:
            if pdf.name.startswith(cat):
                cat_pdfs[cat].append(pdf.name)
                break

    for cat, pdf_list in cat_pdfs.items():
        print(f"  {cat:<20} → {len(pdf_list)} PDFs")

    # Check important ones are present
    print()
    for group, keywords in IMPORTANT_PDF_KEYWORDS.items():
        found = [p.name for p in all_pdfs if any(kw in p.name.lower() for kw in keywords)]
        if found:
            ok(f"[{group}] Found: {found[0]} (+ {len(found)-1} more)")
        else:
            warn(f"[{group}] No PDFs matching keywords {keywords} — check if the page linked any PDFs")

    return len(all_pdfs)

# ─────────────────────────────────────────────────────────────────────────────
# Level 4 — Department pages check
# ─────────────────────────────────────────────────────────────────────────────
DEPT_SLUGS = ["it", "ee", "chem", "math", "phy", "biotech", "botany",
              "zoology", "eco", "edu", "ims", "isl", "eng", "urdu",
              "pak", "media", "law"]

def check_departments():
    head("LEVEL 4 — DEPARTMENT PAGES CHECK (17 expected)")

    all_html = list(RAW_HTML_DIR.glob("programs_classes_*.html"))
    contents = {f.name: f.read_text(encoding="utf-8", errors="ignore").lower()
                for f in all_html}

    found_depts = []
    missing_depts = []

    for slug in DEPT_SLUGS:
        # Check if any file mentions this department slug's content
        # We look inside file content for the slug word or related dept name
        found = any(f"page={slug}" in content or slug in content[:500]
                    for content in contents.values())
        if found:
            found_depts.append(slug)
        else:
            # Check filename pattern  programs_classes_pageN  - we look for dept name in content
            missing_depts.append(slug)

    # Simpler check: just count the programs_classes HTML files
    total = len(all_html)
    if total >= 45:
        ok(f"{total} programs_classes HTML files saved (expected ~51 for all dept sub-pages)")
    elif total >= 20:
        warn(f"{total} programs_classes HTML files saved — some department sub-pages may be missing")
    elif total > 0:
        warn(f"Only {total} programs_classes HTML files — many department pages failed")
    else:
        fail("NO programs_classes HTML files found — department scraping completely failed")

    return total

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  USTB Scrape Verification Report{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")

    html_count, pdf_count = check_file_counts()
    content_passed        = check_file_contents()
    pdf_count_verified    = check_pdfs()
    dept_count            = check_departments()

    head("SUMMARY")
    print(f"  Total HTML files  : {html_count}  (target: ~72)")
    print(f"  Total PDF files   : {pdf_count}  (target: 140+)")
    print(f"  Content checks    : {content_passed}/5 passed")
    print(f"  Department pages  : {dept_count} files (target: ~51)")

    print()
    if html_count >= 60 and pdf_count >= 130 and content_passed >= 4:
        print(f"  {GREEN}{BOLD}VERDICT: SCRAPE SUCCESSFUL ✓{RESET}")
        print(f"  You can proceed to: python scripts/02_process_and_clean.py")
    elif html_count >= 30:
        print(f"  {YELLOW}{BOLD}VERDICT: PARTIAL SUCCESS — review warnings above{RESET}")
        print(f"  Some categories may need URL fixes before proceeding.")
    else:
        print(f"  {RED}{BOLD}VERDICT: SCRAPE FAILED — review errors above{RESET}")
        print(f"  Re-check constants.py URLs and re-run script 01.")

    print(f"\n{BOLD}{'='*60}{RESET}\n")

if __name__ == "__main__":
    main()
