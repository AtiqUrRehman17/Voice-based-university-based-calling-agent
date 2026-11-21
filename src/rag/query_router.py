"""
query_router.py - Automatically routes a user query to the correct Pinecone namespace.
Uses keyword matching + semantic scoring to pick the best namespace without user input.
"""
import re
from typing import Tuple
from config.constants import (
    NAMESPACE_ADMISSIONS, NAMESPACE_FEES,
    NAMESPACE_RULES, NAMESPACE_PROGRAMS, NAMESPACE_CAMPUS
)

# Keyword rules per namespace - expanded for Pakistani academic context
NAMESPACE_KEYWORDS = {
    NAMESPACE_FEES: [
        "fee", "fees", "tuition", "charges", "cost", "payment",
        "challan", "pay", "semester charges", "hostel dues", "dues",
        "bank", "hbl", "nbp", "deposit", "security deposit", "rupees",
        "how much", "price", "amount", "total", "per semester",
        "pkr", "rs", "money", "afford", "expensive", "cheap"
    ],
    NAMESPACE_ADMISSIONS: [
        "admission", "apply", "application", "eligibility", "criteria",
        "merit", "merit list", "etea", "nat", "entry test", "test",
        "enroll", "enrolment", "register", "registration", "deadline",
        "last date", "schedule", "open", "how to apply", "apply online",
        "quota", "fata", "domicile", "percentage", "marks", "matric",
        "intermediate", "f.sc", "fsc", "ics", "a-level", "process",
        "roll number", "result", "gap", "year gap", "noc", "gat",
        "when", "start", "close", "open", "date", "2026", "fall", "spring"
    ],
    NAMESPACE_RULES: [
        "rule", "rules", "policy", "regulation", "hostel rule",
        "hostel policy", "hostel form", "hostel application",
        "semester rule", "migration", "transfer", "transfer department",
        "library", "library rule", "library hours", "book",
        "mphil rule", "phd rule", "thesis", "synopsis", "defense",
        "clearance", "degree form", "convocation", "academic rule",
        "financial rule", "refund", "fine", "penalty", "late fine",
        "discipline", "code of conduct", "harassment"
    ],
    NAMESPACE_PROGRAMS: [
        "program", "programme", "degree", "course", "department",
        "faculty", "bs", "b.sc", "ms", "mphil", "phd", "mba", "bba",
        "llb", "dpt", "mlt", "duration", "years", "semester",
        "computer science", "software engineering", "electrical",
        "medical", "health", "allied health", "natural sciences",
        "management", "economics", "timing", "time", "shift",
        "morning", "evening", "class", "classes", "credit hours",
        "offered", "available", "teach", "study", "subjects", "career",
        "syllabus", "outline", "curriculum", "course outline", "semester plan",
        "biotechnology", "chemistry", "physics", "mathematics", "botany",
        "zoology", "english", "urdu", "law", "media", "education",
        "islamic", "arabic", "pak studies", "pakistan studies"
    ],
    NAMESPACE_CAMPUS: [
        "location", "address", "where", "campus", "office",
        "admin", "administration", "contact", "phone", "number",
        "email", "hostel", "accommodation", "transport", "bus",
        "library", "facility", "facilities", "timings", "working hours",
        "registrar", "vc", "vice chancellor", "staff", "map",
        "direction", "how to reach", "near", "distance",
        "affiliated", "college", "affiliated college", "sports",
        "wi-fi", "wifi", "internet", "cafeteria", "canteen", "mess",
        "history", "established", "founded", "about", "overview",
        "research", "oric", "qec", "quality"
    ]
}

# High-priority primary intent keywords that define the core user intent
PRIMARY_INTENTS = {
    NAMESPACE_FEES: [
        "fee", "fees", "tuition", "challan", "dues", "charges",
        "how much", "cost", "semester fee", "hostel dues", "security deposit"
    ],
    NAMESPACE_ADMISSIONS: [
        "apply", "application", "admission", "eligibility", "criteria",
        "merit", "entry test", "last date", "deadline", "how to apply", "quota"
    ],
    NAMESPACE_RULES: [
        "policy", "rule", "rules", "regulation", "regulations",
        "migration", "transfer", "refund", "clearance", "hostel rule"
    ],
    NAMESPACE_CAMPUS: [
        "where", "location", "address", "phone", "contact", "transport", "bus"
    ]
}

def detect_namespace(query: str) -> Tuple[str, str]:
    """
    Analyses the user query and returns the best matching namespace.
    Primary intent keywords are weighted heavily so subject names (e.g. 'Computer Science')
    do not override intent words like 'fee' or 'eligibility'.
    """
    query_lower = query.lower()
    # Remove punctuation for cleaner matching
    query_clean = re.sub(r"[?!.,;:'\"()\\\-]", " ", query_lower)
    words = set(query_clean.split())

    scores = {}
    for namespace, keywords in NAMESPACE_KEYWORDS.items():
        score = 0
        matched = []

        # 1. Primary intent check (High weight: +5)
        primary_kws = PRIMARY_INTENTS.get(namespace, [])
        for pkw in primary_kws:
            # Check for whole-word or exact phrase match
            pattern = rf"\b{re.escape(pkw)}\b"
            if re.search(pattern, query_clean):
                score += 5
                matched.append(f"{pkw}*")

        # 2. General keywords check
        for kw in keywords:
            pattern = rf"\b{re.escape(kw)}\b" if " " not in kw else re.escape(kw)
            if re.search(pattern, query_clean):
                score += 2 if " " in kw else 1
                matched.append(kw)

        scores[namespace] = (score, matched)

    # Pick the highest scoring namespace
    best_ns = max(scores, key=lambda ns: scores[ns][0])
    best_score, best_matches = scores[best_ns]

    # If nothing matched, default to admissions (most common query type)
    if best_score == 0:
        return NAMESPACE_ADMISSIONS, "default (no specific keywords matched)"

    return best_ns, f"matched keywords: {best_matches[:3]}"
