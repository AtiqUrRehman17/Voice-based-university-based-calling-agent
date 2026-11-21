"""
llm.py - Language Model generation module using Groq Inference API.
Generates concise, plain-text answers from retrieved Pinecone RAG facts.
Free tier at console.groq.com — no payment required.
"""
import os
from src.common.logger import logger

SYSTEM_PROMPT = """You are the official Admissions Advisor for the University of Science and Technology Bannu (USTB), Pakistan.
Your job is to answer prospective students' questions based ONLY on the provided official university facts.

CRITICAL RULES:
1. Answer in 2 to 4 plain sentences maximum. Be concise and direct.
2. Do NOT use markdown, bullet points, asterisks, tables, or numbered lists.
3. Write out numbers and currency naturally: say "42,000 Pakistani Rupees" not "Rs. 42k/-".
4. Speak in a polite, helpful, and natural conversational tone.
5. If the provided facts do not contain the answer, say: "For the most accurate information on this topic, please contact the USTB Admissions Office at 0928-633817 or visit the official website at www.ustb.edu.pk."
6. Never make up information. Only use what is in the provided facts.
"""


class GroqLLM:
    """LLM client backed by Groq's free inference API (llama-3.1-8b-instant)."""

    DEFAULT_MODEL = "llama-3.1-8b-instant"

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.model_name = os.getenv("GROQ_MODEL", self.DEFAULT_MODEL)
        self._client = None

        if not self.api_key:
            logger.warning(
                "GROQ_API_KEY is not set in .env — LLM answers will be skipped. "
                "Get a free key at https://console.groq.com"
            )
            return

        try:
            from groq import Groq
            self._client = Groq(api_key=self.api_key)
            self._available_chat_models = []

            # 1. Fetch live models available for this specific API key
            try:
                models_resp = self._client.models.list()
                all_ids = [m.id for m in models_resp.data if hasattr(m, "id")]
                logger.info(f"Connected to Groq API. Account models: {all_ids}")

                # 2. Filter out non-chat models (Whisper, Prompt Guard, Vision, Embeddings)
                banned_terms = ["guard", "whisper", "embed", "vision", "audio", "moderation", "safeguard", "classification"]
                candidates = [
                    mid for mid in all_ids 
                    if not any(term in mid.lower() for term in banned_terms)
                ]

                # Priority ranking: qwen, llama, mistral, allam
                def rank_model(mid: str) -> int:
                    m = mid.lower()
                    if "qwen" in m: return 0
                    if "llama" in m: return 1
                    if "mistral" in m: return 2
                    if "allam" in m: return 3
                    return 4

                candidates.sort(key=rank_model)

                # Prioritize configured model if in candidates
                if self.model_name in candidates:
                    candidates.remove(self.model_name)
                    candidates.insert(0, self.model_name)

                # 3. Live verification probe: test with 1 token to guarantee it generates chat responses
                working_model = None
                for cand in candidates:
                    try:
                        self._client.chat.completions.create(
                            model=cand,
                            messages=[{"role": "user", "content": "test"}],
                            max_tokens=1
                        )
                        working_model = cand
                        logger.info(f"Verified working Groq chat model: '{working_model}'")
                        break
                    except Exception as probe_err:
                        logger.warning(f"Probe failed for model '{cand}': {probe_err}")

                if working_model:
                    self.model_name = working_model
                    self._available_chat_models = [m for m in candidates if m != working_model]
                else:
                    logger.warning("No candidate model passed the probe test. Using default.")

            except Exception as model_err:
                logger.warning(f"Could not probe Groq models: {model_err}. Proceeding with '{self.model_name}'.")

        except ImportError:
            logger.error(
                "groq package not found. Run: pip install groq"
            )
        except Exception as e:
            logger.error(f"Failed to initialise Groq client: {e}")

    @property
    def is_ready(self) -> bool:
        return self._client is not None

    def generate_answer(self, query: str, context: str) -> str:
        """
        Generates a plain-text answer based on retrieved RAG context.
        Falls back to a formatted context summary if Groq is unavailable.
        """
        if not self.is_ready:
            # Graceful fallback: return formatted raw context
            return _format_context_fallback(context)

        user_content = (
            f"Official University Facts:\n{context}\n\n"
            f"Student Question: {query}\n\n"
            f"Answer (plain text, no markdown, 2-4 sentences):"
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_content},
        ]

        try:
            response = self._client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=300,
                temperature=0.3,
            )
            answer = response.choices[0].message.content.strip()
            # Strip any stray markdown the model sneaks in
            answer = answer.replace("**", "").replace("*", "").replace("##", "").replace("#", "")
            return answer
        except Exception as e:
            logger.error(f"Groq LLM generation error with model '{self.model_name}': {e}")
            # Try other verified chat models if available
            for fallback_model in getattr(self, "_available_chat_models", []):
                try:
                    logger.info(f"Retrying with fallback model '{fallback_model}'...")
                    res = self._client.chat.completions.create(
                        model=fallback_model,
                        messages=messages,
                        max_tokens=300,
                        temperature=0.3
                    )
                    self.model_name = fallback_model
                    ans = res.choices[0].message.content.strip()
                    return ans.replace("**", "").replace("*", "").replace("##", "").replace("#", "")
                except Exception:
                    continue
            return _format_context_fallback(context)


def _format_context_fallback(context: str) -> str:
    """Returns a readable plain-text summary from raw context chunks."""
    lines = [line.strip() for line in context.strip().splitlines() if line.strip()]
    if not lines:
        return (
            "I could not find specific information on that topic. "
            "Please contact the USTB Admissions Office at 0928-633817."
        )
    # Return up to 3 sentences of context, cleanly joined
    return " ".join(lines[:3])


# ---------------------------------------------------------------------------
# Backward-compat alias — old code that imports HuggingFaceVoiceLLM still works
# ---------------------------------------------------------------------------
HuggingFaceVoiceLLM = GroqLLM
