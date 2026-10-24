"""
Calls Groq to judge a single (claim, source chunk) pair, and parses its
verdict into a structured (verdict, reason) tuple.

Deliberately one claim at a time, not the whole answer at once — the judge
should only ever see the ONE chunk a claim actually cited, never the full
context. If it saw everything, it might "support" a claim using a
DIFFERENT chunk than the one actually cited, which would defeat the
purpose: we're verifying the citation is honest, not just that the claim
is true somewhere in the corpus.
"""

import re

from groq import Groq
from app.generation.judge_prompt import JUDGE_SYSTEM_PROMPT, build_judge_message
from app.config import settings

_client: Groq | None = None
VALID_VERDICTS = ["SUPPORTED", "NOT_SUPPORTED", "PARTIAL"]


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
        max_completion_tokens=400,
        temperature=0,
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
    )

    return response.choices[0].message.content


def parse_verdict(raw_response: str) -> tuple[str, str]:
    """
    Parses the judge's constrained-format response into (verdict, reason).

    Defensive by design: if the judge doesn't follow the VERDICT/REASON
    format, or uses a verdict word outside VALID_VERDICTS, this returns
    "UNKNOWN" rather than trusting or crashing on malformed input — and
    preserves the full raw response as the reason in that case.

    Also handles common LLM format drifts:
    - Markdown bold markers: **VERDICT:** SUPPORTED
    - Extra whitespace or colons
    - Verdict word appearing anywhere in the response as a last-resort fallback
    """
    final_verdict = "UNKNOWN"
    reason = ""

    for line in raw_response.strip().split("\n"):
        # Strip markdown bold markers the model sometimes adds
        clean = line.replace("**", "").strip()
        lower = clean.lower()

        if "verdict:" in lower:
            position = lower.find("verdict:")
            candidate = clean[position + len("verdict:"):].strip()
            # Take only the first word (guards against "SUPPORTED because...")
            candidate = candidate.split()[0] if candidate.split() else ""
            if candidate.upper() in VALID_VERDICTS:
                final_verdict = candidate.upper()

        if "reason:" in lower:
            position = lower.find("reason:")
            reason = clean[position + len("reason:"):].strip()

    # Last-resort fallback: scan entire response for a verdict keyword
    if final_verdict == "UNKNOWN":
        upper = raw_response.upper()
        for v in VALID_VERDICTS:
            if re.search(rf'\b{v}\b', upper):
                final_verdict = v
                break

    if reason == "":
        reason = raw_response.strip()

    return (final_verdict, reason)