"""
Prompt for the LLM-as-judge verification step.

Design choice: force a rigid, constrained response format (two labeled
lines) rather than free-form prose. A judge that responds in whatever
style it likes is much harder to parse reliably — we already learned this
lesson the hard way with citation brackets drifting format despite clear
instructions. A tight format doesn't guarantee compliance, but it makes
deviations easier to detect and narrows how many ways things can go wrong.
"""

JUDGE_SYSTEM_PROMPT = """You are a strict fact-checker. You will be given a CLAIM and a SOURCE CHUNK.

Determine whether the source chunk supports the claim, then respond in EXACTLY this format and nothing else:

VERDICT: <SUPPORTED|NOT_SUPPORTED|PARTIAL>
REASON: <one short sentence>

Definitions:
- SUPPORTED: the source chunk fully supports the claim as stated.
- NOT_SUPPORTED: the source chunk does not mention this, or contradicts the claim.
- PARTIAL: the source chunk supports part of the claim, but the claim adds detail the chunk doesn't actually contain.
"""


def build_judge_message(claim_text: str, source_chunk_text: str) -> str:
    return f"""CLAIM: {claim_text}

SOURCE CHUNK: {source_chunk_text}"""