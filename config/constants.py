"""
constants.py - System-wide configuration constants for UST Bannu RAG Pipeline.
Updated 2026-11-20: Real PHP URLs from live browser exploration.
"""
from pathlib import Path

# Base URLs
BASE_URL = "https://www.ustb.edu.pk"

# ---------------------------------------------------------------------------
# SCRAPER TARGETS
# Every URL here is a confirmed, working PHP endpoint discovered by browser.
# The spider visits each URL, saves the HTML, and auto-downloads any PDFs found.
# ---------------------------------------------------------------------------
SCRAPER_TARGETS = {

    # ------------------------------------------------------------------
    # ADMISSIONS — apply, eligibility, merit lists, test results
    # ------------------------------------------------------------------
    "admissions": [
        "https://www.ustb.edu.pk/apply.php",           # Full program list + eligibility criteria
        "https://www.ustb.edu.pk/merit-list.php",      # 128+ merit list PDFs (all programs)
        "https://www.ustb.edu.pk/advertisement.php",   # Admission schedule banners with dates & quotas
        "https://www.ustb.edu.pk/test-results.php",    # Entry test result page
        "https://www.ustb.edu.pk/index.php",           # Homepage — latest news & announcements
    ],

    # ------------------------------------------------------------------
    # FEES — semester fee schedules (PDFs auto-downloaded from fees.php)
    # ------------------------------------------------------------------
    "fees": [
        "https://www.ustb.edu.pk/fees.php",            # Links to 3 fee schedule PDFs
    ],

    # ------------------------------------------------------------------
    # RULES & POLICIES — hostel rules, semester migration, MS/PhD regs
    # (new namespace — these are PDFs students always ask about)
    # ------------------------------------------------------------------
    "rules_policies": [
        "https://www.ustb.edu.pk/rules.php",           # 11 policy PDFs: hostel, semester, MS/PhD, library
        "https://www.ustb.edu.pk/downloads.php",       # 12 student forms: hostel form, degree form, etc.
    ],

    # ------------------------------------------------------------------
    # PROGRAMS & CLASSES — all 17 departments, 3 sub-pages each
    # Pattern: dept-content.php?type=<home|programs|faculty>&page=<slug>
    #   type=home      → dept overview, mission, programs listed
    #   type=programs  → 8-semester course outlines (most valuable)
    #   type=faculty   → faculty member names and designations
    # ------------------------------------------------------------------
    "programs_classes": [
        # --- Faculty of Physical & Computing Sciences ---
        "https://www.ustb.edu.pk/dept-content.php?type=home&page=it",
        "https://www.ustb.edu.pk/dept-content.php?type=programs&page=it",
        "https://www.ustb.edu.pk/dept-content.php?type=faculty&page=it",

        "https://www.ustb.edu.pk/dept-content.php?type=home&page=chem",
        "https://www.ustb.edu.pk/dept-content.php?type=programs&page=chem",
        "https://www.ustb.edu.pk/dept-content.php?type=faculty&page=chem",

        "https://www.ustb.edu.pk/dept-content.php?type=home&page=math",
        "https://www.ustb.edu.pk/dept-content.php?type=programs&page=math",
        "https://www.ustb.edu.pk/dept-content.php?type=faculty&page=math",

        "https://www.ustb.edu.pk/dept-content.php?type=home&page=phy",
        "https://www.ustb.edu.pk/dept-content.php?type=programs&page=phy",
        "https://www.ustb.edu.pk/dept-content.php?type=faculty&page=phy",

        # --- Faculty of Engineering & Technology ---
        "https://www.ustb.edu.pk/dept-content.php?type=home&page=ee",
        "https://www.ustb.edu.pk/dept-content.php?type=programs&page=ee",
        "https://www.ustb.edu.pk/dept-content.php?type=faculty&page=ee",

        # --- Faculty of Biological & Health Sciences ---
        "https://www.ustb.edu.pk/dept-content.php?type=home&page=biotech",
        "https://www.ustb.edu.pk/dept-content.php?type=programs&page=biotech",
        "https://www.ustb.edu.pk/dept-content.php?type=faculty&page=biotech",

        "https://www.ustb.edu.pk/dept-content.php?type=home&page=botany",
        "https://www.ustb.edu.pk/dept-content.php?type=programs&page=botany",
        "https://www.ustb.edu.pk/dept-content.php?type=faculty&page=botany",

        "https://www.ustb.edu.pk/dept-content.php?type=home&page=zoology",
        "https://www.ustb.edu.pk/dept-content.php?type=programs&page=zoology",
        "https://www.ustb.edu.pk/dept-content.php?type=faculty&page=zoology",

        # --- Faculty of Social Sciences ---
        "https://www.ustb.edu.pk/dept-content.php?type=home&page=eco",
        "https://www.ustb.edu.pk/dept-content.php?type=programs&page=eco",
        "https://www.ustb.edu.pk/dept-content.php?type=faculty&page=eco",

        "https://www.ustb.edu.pk/dept-content.php?type=home&page=edu",
        "https://www.ustb.edu.pk/dept-content.php?type=programs&page=edu",
        "https://www.ustb.edu.pk/dept-content.php?type=faculty&page=edu",

        "https://www.ustb.edu.pk/dept-content.php?type=home&page=ims",
        "https://www.ustb.edu.pk/dept-content.php?type=programs&page=ims",
        "https://www.ustb.edu.pk/dept-content.php?type=faculty&page=ims",

        "https://www.ustb.edu.pk/dept-content.php?type=home&page=isl",
        "https://www.ustb.edu.pk/dept-content.php?type=programs&page=isl",
        "https://www.ustb.edu.pk/dept-content.php?type=faculty&page=isl",

        "https://www.ustb.edu.pk/dept-content.php?type=home&page=eng",
        "https://www.ustb.edu.pk/dept-content.php?type=programs&page=eng",
        "https://www.ustb.edu.pk/dept-content.php?type=faculty&page=eng",

        "https://www.ustb.edu.pk/dept-content.php?type=home&page=urdu",
        "https://www.ustb.edu.pk/dept-content.php?type=programs&page=urdu",
        "https://www.ustb.edu.pk/dept-content.php?type=faculty&page=urdu",

        "https://www.ustb.edu.pk/dept-content.php?type=home&page=pak",
        "https://www.ustb.edu.pk/dept-content.php?type=programs&page=pak",
        "https://www.ustb.edu.pk/dept-content.php?type=faculty&page=pak",

        "https://www.ustb.edu.pk/dept-content.php?type=home&page=media",
        "https://www.ustb.edu.pk/dept-content.php?type=programs&page=media",
        "https://www.ustb.edu.pk/dept-content.php?type=faculty&page=media",

        "https://www.ustb.edu.pk/dept-content.php?type=home&page=law",
        "https://www.ustb.edu.pk/dept-content.php?type=programs&page=law",
        "https://www.ustb.edu.pk/dept-content.php?type=faculty&page=law",
    ],

    # ------------------------------------------------------------------
    # CAMPUS & ADMINISTRATION — location, contacts, offices, facilities
    # ------------------------------------------------------------------
    "campus_admin": [
        "https://www.ustb.edu.pk/about.php",               # Uni history (est. 2005), vision, mission
        "https://www.ustb.edu.pk/colleges.php",            # List of affiliated colleges
        "https://www.ustb.edu.pk/staff.php?page=dst",      # Directorate of Student Affairs
        "https://www.ustb.edu.pk/staff.php?page=coe",      # Controller of Examinations
        "https://www.ustb.edu.pk/staff.php?page=transport",# Transport section & bus routes
        "https://www.ustb.edu.pk/staff.php?page=sports",   # Directorate of Sports
        "https://www.ustb.edu.pk/staff.php?page=itrc",     # IT Resource Centre
        "https://www.ustb.edu.pk/staff.php?page=pro",      # Public Relations Office
        "https://www.ustb.edu.pk/office.php?page=qec",     # Quality Enhancement Cell
        "https://www.ustb.edu.pk/office.php?page=oric",    # Research & Innovation Office
    ],
}

# ---------------------------------------------------------------------------
# PINECONE NAMESPACES
# ---------------------------------------------------------------------------
NAMESPACE_ADMISSIONS   = "admissions"
NAMESPACE_FEES         = "fees"
NAMESPACE_RULES        = "rules-policies"       # NEW
NAMESPACE_PROGRAMS     = "programs-classes"
NAMESPACE_CAMPUS       = "campus-admin"

ALL_NAMESPACES = [
    NAMESPACE_ADMISSIONS,
    NAMESPACE_FEES,
    NAMESPACE_RULES,
    NAMESPACE_PROGRAMS,
    NAMESPACE_CAMPUS,
]

# ---------------------------------------------------------------------------
# PROJECT DIRECTORIES
# ---------------------------------------------------------------------------
ROOT_DIR      = Path(__file__).resolve().parent.parent
DATA_DIR      = ROOT_DIR / "data"
RAW_HTML_DIR  = DATA_DIR / "raw" / "html"
RAW_PDF_DIR   = DATA_DIR / "raw" / "pdfs"
INTERIM_DIR   = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"

# ---------------------------------------------------------------------------
# PROCESSED JSON TARGETS (one file per namespace)
# ---------------------------------------------------------------------------
PROCESSED_FILES = {
    NAMESPACE_ADMISSIONS : PROCESSED_DIR / "admissions.json",
    NAMESPACE_FEES       : PROCESSED_DIR / "fees.json",
    NAMESPACE_RULES      : PROCESSED_DIR / "rules_policies.json",   # NEW
    NAMESPACE_PROGRAMS   : PROCESSED_DIR / "programs_classes.json",
    NAMESPACE_CAMPUS     : PROCESSED_DIR / "campus_admin.json",
}

# ---------------------------------------------------------------------------
# SCRAPER CATEGORY → NAMESPACE MAPPING
# Used by script 02 to route each HTML file into the right namespace
# ---------------------------------------------------------------------------
CATEGORY_TO_NAMESPACE = {
    "admissions"    : NAMESPACE_ADMISSIONS,
    "fees"          : NAMESPACE_FEES,
    "rules_policies": NAMESPACE_RULES,
    "programs_classes": NAMESPACE_PROGRAMS,
    "campus_admin"  : NAMESPACE_CAMPUS,
}

# ---------------------------------------------------------------------------
# VOICE NORMALIZATION — Acronym expansion for TTS pronunciation
# ---------------------------------------------------------------------------
ACRONYM_MAP = {
    r"\bBS\b"      : "Bachelor of Science",
    r"\bBSc\b"     : "Bachelor of Science",
    r"\bB\.Sc\b"   : "Bachelor of Science",
    r"\bMS\b"      : "Master of Science",
    r"\bM\.Phil\b" : "Master of Philosophy",
    r"\bMPhil\b"   : "Master of Philosophy",
    r"\bPhD\b"     : "Doctor of Philosophy",
    r"\bCS\b"      : "Computer Science",
    r"\bSE\b"      : "Software Engineering",
    r"\bAI\b"      : "Artificial Intelligence",
    r"\bIT\b"      : "Information Technology",
    r"\bMLT\b"     : "Medical Laboratory Technology",
    r"\bDPT\b"     : "Doctor of Physical Therapy",
    r"\bLLB\b"     : "Bachelor of Laws",
    r"\bBBA\b"     : "Bachelor of Business Administration",
    r"\bMBA\b"     : "Master of Business Administration",
    r"\bFSc\b"     : "Faculty of Science",
    r"\bF\.Sc\b"   : "Faculty of Science",
    r"\bFA\b"      : "Faculty of Arts",
    r"\bHOD\b"     : "Head of Department",
    r"\bETEA\b"    : "Educational Testing and Evaluation Agency",
    r"\bNAT\b"     : "National Aptitude Test",
    r"\bGAT\b"     : "Graduate Assessment Test",
    r"\bHEC\b"     : "Higher Education Commission",
    r"\bPEC\b"     : "Pakistan Engineering Council",
    r"\bUSTB\b"    : "University of Science and Technology Bannu",
    r"\bHBL\b"     : "Habib Bank Limited",
    r"\bNBP\b"     : "National Bank of Pakistan",
    r"\bKPK\b"     : "Khyber Pakhtunkhwa",
    r"\bQEC\b"     : "Quality Enhancement Cell",
    r"\bORIC\b"    : "Office of Research Innovation and Commercialization",
    r"\bIMS\b"     : "Institute of Management Sciences",
    r"\bCGPA\b"    : "Cumulative Grade Point Average",
    r"\bGPA\b"     : "Grade Point Average",
}
