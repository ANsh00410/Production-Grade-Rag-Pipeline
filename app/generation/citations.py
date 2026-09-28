"""
Citation extraction and claim-splitting for the LLM-as-judge stage.

Both extract_citations() and split_into_claims() need to recognize the same
citation markers — if only one of them normalized Unicode bracket variants
(discovered as a real bug in testing: the model sometimes drifts from ASCII
[1] to visually-similar full-width 【1】 despite explicit instructions), the
two functions could disagree about what counts as a citation, which would
be a subtle, hard-to-spot inconsistency. So normalization happens once, in
one shared helper, and everything else builds on top of it.
"""

import re


def _normalize_brackets(text: str) -> str:
    """Known Unicode bracket variants -> ASCII, so every regex below sees
    a consistent format regardless of how the model chose to format it."""
    return text.replace("【", "[").replace("】", "]")


def extract_citations(answer_text: str, num_chunks: int) -> list[int]:
    """
    Extracts valid citation numbers from text: deduped, numerically sorted,
    and restricted to the 1..num_chunks range actually provided to the
    model (a hallucinated out-of-range citation is silently dropped, not
    trusted).
    """
    normalized = _normalize_brackets(answer_text)
    numbers = re.findall(r"\[(\d+)\]", normalized)
    nums = list(set(int(n) for n in numbers if int(n) <= num_chunks and int(n) > 0))
    nums.sort(key=int)
    return nums


def split_into_claims(answer_text: str, num_chunks: int) -> list[tuple[str, list[int]]]:
    """
    Splits a generated answer into (claim_text, citation_numbers) pairs,
    one per sentence — claim_text with citation markers stripped out
    entirely, citation_numbers pulled from the SAME sentence via
    extract_citations() so both stay validated and consistent.

    This is what lets the LLM-judge stage check one claim against ONLY the
    specific chunk(s) it actually cited, rather than the whole context at
    once — checking a claim against an irrelevant chunk would be a
    meaningless comparison.

    Known limitation: splitting on ". " is a simple heuristic, not true
    sentence-boundary detection (it would mis-split on abbreviations like
    "e.g." or decimal numbers like "3.5"). Good enough for this project;
    worth naming as a stated limitation rather than a silent gap if asked.
    """
    normalized = _normalize_brackets(answer_text)
    sentences = normalized.split(". ")

    claims = []
    for sentence in sentences:
        if not sentence.strip():
            continue  # guards against a stray empty segment (e.g. trailing ". ")

        clean_text = re.sub(r" ?(\[\d+\])+", ".", sentence).strip()
        citation_numbers = extract_citations(sentence, num_chunks)
        claims.append((clean_text, citation_numbers))

    return claims