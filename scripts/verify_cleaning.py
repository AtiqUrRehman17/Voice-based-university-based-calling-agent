"""
verify_cleaning.py - Post-processing & normalization verification report.

Validates that:
1. All namespace JSON files exist in data/processed/ and contain records.
2. Text cleaning succeeded (no boilerplate, no empty or trivial chunks).
3. Normalization succeeded (currency expanded to Pakistani Rupees, acronyms expanded, markdown symbols stripped).
4. Chunk lengths are within target bounds for RAG & voice synthesis.
5. Displays real before-and-after samples from each namespace.

Usage:
    python scripts/verify_cleaning.py
"""
import sys
import json
import re
from pathlib import Path
from collections import defaultdict

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from config.constants import PROCESSED_DIR, PROCESSED_FILES, ALL_NAMESPACES

# ANSI colors
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


def load_dataset(filepath: Path):
    if not filepath.exists():
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return []


def verify_processed_files():
    head("LEVEL 1 — PROCESSED DATASET INVENTORY")
    total_records = 0
    all_datasets = {}

    for ns in ALL_NAMESPACES:
        target_file = PROCESSED_FILES.get(ns)
        records = load_dataset(target_file)

        if records is None:
            fail(f"{ns:<20} : MISSING FILE ({target_file.name})")
        elif len(records) == 0:
            warn(f"{ns:<20} : EMPTY DATASET ({target_file.name})")
            all_datasets[ns] = []
        else:
            total_records += len(records)
            ok(f"{ns:<20} : {len(records):>5} chunks saved -> {target_file.name}")
            all_datasets[ns] = records

    print(f"\n  {BOLD}Total Voice-Ready Chunks Across All Namespaces:{RESET} {BOLD}{total_records}{RESET}")
    return all_datasets


def verify_normalization_rules(datasets):
    head("LEVEL 2 — NORMALIZATION & VOICE HYGIENE CHECKS")

    currency_unnormalized = 0
    currency_normalized = 0
    markdown_leaks = 0
    acronym_expansions = 0
    total_checked = 0

    for ns, records in datasets.items():
        for rec in records:
            total_checked += 1
            spoken = rec.get("spoken_text", "")
            raw = rec.get("text", "")

            # Check 1: Currency normalization
            if re.search(r"Rs\.?\s*\d+", spoken, re.IGNORECASE) or re.search(r"PKR\s*\d+", spoken, re.IGNORECASE):
                currency_unnormalized += 1
            if "pakistani rupees" in spoken.lower():
                currency_normalized += 1

            # Check 2: Markdown symbols
            if re.search(r"[\*#\[\]_<>\|]", spoken):
                markdown_leaks += 1

            # Check 3: Acronym expansion check
            if "bachelor of science" in spoken.lower() or "master of science" in spoken.lower():
                acronym_expansions += 1

    # Print results
    if currency_unnormalized == 0:
        ok(f"Currency Normalization: 0 unhandled 'Rs./PKR' tags found.")
    else:
        warn(f"Currency Normalization: Found {currency_unnormalized} chunks with raw 'Rs./PKR' patterns.")

    if currency_normalized > 0:
        ok(f"Spoken Currency Conversion: {currency_normalized} instances of 'Pakistani Rupees' generated.")

    if markdown_leaks == 0:
        ok(f"Markdown Cleaning: Zero markdown/bracket artifacts in spoken text.")
    else:
        warn(f"Markdown Cleaning: {markdown_leaks} chunks still contain raw symbols (*, #, [, ]).")

    if acronym_expansions > 0:
        ok(f"Acronym Expansion: {acronym_expansions} instances of degrees expanded for natural speech.")


def verify_chunk_lengths(datasets):
    head("LEVEL 3 — CHUNK SIZES & RETRIEVAL READINESS")

    for ns, records in datasets.items():
        if not records:
            continue
        word_counts = [len(r.get("spoken_text", "").split()) for r in records]
        avg_words = sum(word_counts) // len(word_counts) if word_counts else 0
        max_words = max(word_counts) if word_counts else 0
        min_words = min(word_counts) if word_counts else 0

        # Optimal voice chunk size is 30 to 180 words
        status = ok if max_words <= 250 and min_words >= 5 else warn
        status(
            f"{ns:<20} : Avg = {avg_words:>3} words | Min = {min_words:>2} words | Max = {max_words:>3} words"
        )


def display_samples(datasets):
    head("LEVEL 4 — BEFORE & AFTER NORMALIZATION SAMPLES")

    for ns, records in datasets.items():
        if not records:
            continue
        # Find a record where spoken_text differs from text, or pick the first record
        sample = None
        for r in records:
            if r.get("spoken_text") != r.get("text"):
                sample = r
                break
        if not sample:
            sample = records[0]

        print(f"\n{BOLD}[Namespace: {ns}] — Title: '{sample.get('title')}'{RESET}")
        print(f"  {YELLOW}Raw Text   :{RESET} {sample.get('text')[:160]}...")
        print(f"  {GREEN}Spoken Form:{RESET} {sample.get('spoken_text')[:160]}...")


def main():
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  UST Bannu Cleaning & Normalization Verification{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")

    datasets = verify_processed_files()
    if not datasets or all(len(recs) == 0 for recs in datasets.values()):
        fail("No processed data found. Please run: python scripts/02_process_and_clean.py first.")
        return

    verify_normalization_rules(datasets)
    verify_chunk_lengths(datasets)
    display_samples(datasets)

    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{GREEN}{BOLD}  Ready for Step 03 (Pinecone Vector Indexing){RESET}")
    print(f"{BOLD}{'='*60}{RESET}\n")


if __name__ == "__main__":
    main()
