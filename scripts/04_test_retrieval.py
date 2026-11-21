"""
04_test_retrieval.py - UST Bannu plain-text chatbot with automatic namespace routing.

Usage:
    python scripts/04_test_retrieval.py              # auto-routing chatbot (default)
    python scripts/04_test_retrieval.py --test       # run automated retrieval test suite
"""
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Project root on sys.path
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from config.constants import (
    NAMESPACE_ADMISSIONS, NAMESPACE_FEES, NAMESPACE_RULES,
    NAMESPACE_PROGRAMS, NAMESPACE_CAMPUS
)
from src.rag.retriever import USTBRetriever
from src.rag.llm import GroqLLM
from src.rag.query_router import detect_namespace
from src.common.logger import logger

# ---------------------------------------------------------------------------
# Automated test suite (run with --test flag)
# ---------------------------------------------------------------------------
TEST_SUITE = [
    {
        "namespace": NAMESPACE_FEES,
        "query": "What is the fee per semester for BS Computer Science?",
    },
    {
        "namespace": NAMESPACE_ADMISSIONS,
        "query": "What is the minimum eligibility percentage for engineering admission?",
    },
    {
        "namespace": NAMESPACE_RULES,
        "query": "What is the policy for semester migration and hostel admission?",
    },
    {
        "namespace": NAMESPACE_PROGRAMS,
        "query": "What degrees are offered in Faculty of Allied Health Sciences?",
    },
    {
        "namespace": NAMESPACE_CAMPUS,
        "query": "Where is the main campus located and what are the admission phone numbers?",
    },
]


def run_automated_tests(retriever: USTBRetriever, llm: GroqLLM):
    logger.info("=====================================================")
    logger.info("   Running Automated Retrieval & Latency Test Suite  ")
    logger.info("=====================================================")

    passed = 0
    total = len(TEST_SUITE)

    for idx, test in enumerate(TEST_SUITE, start=1):
        ns = test["namespace"]
        query = test["query"]

        logger.info(f"\n[Test #{idx}] Namespace: '{ns}'")
        logger.info(f"Question: \"{query}\"")

        t0 = time.time()
        results = retriever.query_namespace(namespace=ns, query=query, top_k=3)
        retrieval_latency = (time.time() - t0) * 1000

        if results:
            top_hit = results[0]
            logger.info(
                f" Retrieved from '{ns}' "
                f"(Score: {top_hit.score:.4f}, Latency: {retrieval_latency:.1f}ms)"
            )
            logger.info(f"   Context: \"{top_hit.spoken_text[:120]}...\"")

            context_str = "\n".join([r.spoken_text for r in results])
            answer = llm.generate_answer(query=query, context=context_str)
            logger.info(f"   Answer: \"{answer}\"")
            passed += 1
        else:
            logger.warning(f" No match found in namespace '{ns}'")

    logger.info("=====================================================")
    logger.info(f"Test Suite Result: {passed}/{total} tests completed.")
    logger.info("=====================================================")


def format_citations(results: list) -> str:
    """Extracts deduplicated, verifiable source citations from retrieved Pinecone matches."""
    if not results:
        return ""

    citations = []
    seen = set()

    for r in results:
        meta = r.metadata or {}
        src = meta.get("source_file") or meta.get("title") or r.id
        doc_type = meta.get("doc_type", "")

        # Clean display name for readability
        src_clean = str(src)
        if src_clean.startswith("UST Bannu PDF:"):
            src_clean = src_clean.replace("UST Bannu PDF:", "").strip() + ".pdf"
        elif src_clean.startswith("UST Bannu Table:"):
            src_clean = src_clean.replace("UST Bannu Table:", "").strip() + " (Table)"

        key = (src_clean, r.namespace)
        if key not in seen and r.score >= 0.35:
            seen.add(key)
            pct = int(r.score * 100)
            tag = f" [{doc_type}]" if doc_type else ""
            citations.append(f"  [{len(citations)+1}] {src_clean}{tag} (Namespace: {r.namespace} | Match: {pct}%)")
            if len(citations) >= 3:
                break

    if not citations:
        return ""

    return "  Sources & Citations:\n" + "\n".join(citations)


# ---------------------------------------------------------------------------
# Main chatbot — auto-routing, plain text, no menus
# ---------------------------------------------------------------------------
SEPARATOR = "-" * 60

def chatbot(retriever: USTBRetriever, llm: GroqLLM):
    """
    Plain-text interactive chatbot.
    - User types any question in English.
    - System auto-detects the right Pinecone namespace.
    - Retrieves relevant facts, generates a plain-text answer.
    - Prints verifiable source citations (document name, namespace, match %).
    - No manual namespace selection required.
    """
    print()
    print(SEPARATOR)
    print("  UST Bannu Admissions Assistant")
    print("  Powered by Pinecone RAG + Groq LLM")
    print(SEPARATOR)
    print("  Ask anything about USTB: admissions, fees, programs, campus.")
    print("  Type 'exit' or press Ctrl+C to quit.")
    print(SEPARATOR)
    print()

    while True:
        try:
            query = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not query:
            continue

        if query.lower() in {"exit", "quit", "q", "bye"}:
            print("Goodbye!")
            break

        # --- 1. Auto-route to namespace ---
        namespace, reason = detect_namespace(query)

        # --- 2. Retrieve from Pinecone ---
        t0 = time.time()
        results = retriever.query_namespace(namespace=namespace, query=query, top_k=4)
        latency_ms = (time.time() - t0) * 1000

        logger.info(
            f"Routed to '{namespace}' ({reason}) | "
            f"Retrieved {len(results)} chunk(s) in {latency_ms:.0f}ms"
        )

        # --- 3. Generate answer ---
        if results:
            context_str = "\n".join([r.spoken_text for r in results])
            answer = llm.generate_answer(query=query, context=context_str)
        else:
            answer = (
                "I could not find specific information on that topic in the university records. "
                "Please contact the USTB Admissions Office directly at 0928-633817 "
                "or visit www.ustb.edu.pk for the most up-to-date details."
            )

        # --- 4. Print plain-text answer & source citations ---
        print()
        print(f"Assistant: {answer}")

        citations = format_citations(results)
        if citations:
            print(f"\n{citations}")
        print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    retriever = USTBRetriever()
    llm = GroqLLM()

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_automated_tests(retriever, llm)
    else:
        chatbot(retriever, llm)


if __name__ == "__main__":
    main()
