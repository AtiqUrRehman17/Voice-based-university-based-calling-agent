"""
test_llm.py - Quick 1-second diagnostic script to test Groq LLM connection.

Usage:
    python scripts/test_llm.py
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from src.rag.llm import GroqLLM
from src.common.logger import logger

def main():
    print("\n--- Testing Groq LLM Connection ---")
    llm = GroqLLM()

    if not llm.is_ready:
        print("[FAIL] Groq LLM could not be initialized. Check GROQ_API_KEY in .env")
        return

    print(f"\nActive Model Selected: {llm.model_name}")
    print("Testing answer generation with sample context...")

    sample_context = (
        "For Bachelor of Science Computer Science, the first semester fee is 42,500 Pakistani Rupees. "
        "Subsequent semesters are 36,000 Pakistani Rupees."
    )
    query = "What is the fee for BS Computer Science?"

    answer = llm.generate_answer(query=query, context=sample_context)

    print("\n" + "="*50)
    print(f"Generated Answer:\n{answer}")
    print("="*50 + "\n")
    print("[SUCCESS] Groq LLM is working properly!\n")

if __name__ == "__main__":
    main()
