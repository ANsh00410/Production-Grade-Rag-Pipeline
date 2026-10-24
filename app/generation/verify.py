from dataclasses import dataclass

from app.generation.citations import split_into_claims
from app.generation.judge import judge_claim, parse_verdict
from app.retrieval.search import SearchResult


@dataclass
class ClaimResult:
    claim: str
    citations: list[int]
    verdict: str   # SUPPORTED | PARTIAL | NOT_SUPPORTED | UNKNOWN | UNCITED
    reason: str

@dataclass
class VerificationReport:
    """
    Aggregated result after judging every claim in an answer.
    'overall' is PASS only when every single claim is SUPPORTED.
    Anything flagged (PARTIAL / NOT_SUPPORTED / UNKNOWN / UNCITED) → REVIEW.
    """
    total:int
    count: dict[str,int] #eg. {"SUPPORTED": 2, "UNCITED": 1}
    flagged: list[ClaimResult] # claims that are NOT purely SUPPORTED
    overall:str #PASS/REVIEW
    claims: list[ClaimResult] #all claims, for full transparency


def verify_claims(answer_text: str, chunks: list[SearchResult]) -> list[ClaimResult]:
    claims = split_into_claims(answer_text, num_chunks=len(chunks))

    results: list[ClaimResult] = []
    for claim_text, citation_numbers in claims:
        if not citation_numbers:
            results.append(ClaimResult(
                claim=claim_text,
                citations=[],
                verdict="UNCITED",
                reason="No valid citation attached to this claim.",
            ))
            continue

        cited_text = "\n\n".join(chunks[n - 1].payload["text"] for n in citation_numbers)
        raw_response = judge_claim(claim_text, cited_text)
        verdict, reason = parse_verdict(raw_response)

        results.append(ClaimResult(
            claim=claim_text,
            citations=citation_numbers,
            verdict=verdict,
            reason=reason,
        ))

    return results


def summarize_results(claim_results: list[ClaimResult]) -> VerificationReport:
    total = len(claim_results)
    flagged = []
    overall = ""
    count = {}
    for cr in claim_results:
        count[cr.verdict] = count.get(cr.verdict, 0) + 1

        if cr.verdict != "SUPPORTED":
            flagged.append(cr)   
    if len(flagged) == 0 and total > 0:
        overall = "PASS"
    else:
        overall = "REVIEW"

    return VerificationReport(
        total=total,
        count=count,
        flagged=flagged,
        overall=overall,
        claims=claim_results,
    )
    
