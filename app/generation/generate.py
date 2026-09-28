"""
Calls a Groq-hosted model with the constructed prompt to produce a grounded answer.

This function is deliberately "dumb" — it just sends the prompt and returns
the raw text. It doesn't know anything about parsing citations out of that
text (that's citations.py's job) or about verifying them (that's the
LLM-judge stage's job). Keeping generation, parsing, and verification as
three separate functions means each is independently testable and each
failure mode is traceable to exactly one place.
"""

from groq import Groq
from app.generation.prompt import SYSTEM_PROMPT, build_user_message
from app.retrieval.search import SearchResult
from app.config import settings

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=settings.groq_api_key)
    return _client


def generate_answer(query: str, chunks: list[SearchResult]) -> str:
    if not chunks:
        return "I don't have any relevant context to answer this question."

    client = _get_client()
    user_message = build_user_message(query, chunks)

    response = client.chat.completions.create(
        model=settings.generation_model,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    return response.choices[0].message.content