"""
Calls Groq to judge a single (claim, source chunk) pair.

Deliberately one claim at a time, not the whole answer at once — the judge
should only ever see the ONE chunk a claim actually cited, never the full
context. If it saw everything, it might "support" a claim using a
DIFFERENT chunk than the one actually cited, which would defeat the
purpose: we're verifying the citation is honest, not just that the claim
is true somewhere in the corpus.
"""

from groq import Groq
from app.generation.judge_prompt import JUDGE_SYSTEM_PROMPT, build_judge_message
from app.config import settings

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=settings.groq_api_key)
    return _client


def judge_claim(claim_text: str, source_chunk_text: str) -> str:
    client = _get_client()
    message = build_judge_message(claim_text, source_chunk_text)

    response = client.chat.completions.create(
        model=settings.judge_model,
        max_completion_tokens=200,
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
    )

    return response.choices[0].message.content