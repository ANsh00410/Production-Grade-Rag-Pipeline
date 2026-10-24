"""
The top-level pipeline orchestrator.

This is the ONE function the FastAPI route (and any test) should call.
It wires every stage together in order:

    retrieve()          → find the most relevant chunks
    generate_answer()   → produce a grounded answer with citations
    verify_claims()     → judge every claim against its cited chunk
    summarize_results() → aggregate into one final report

Each stage is kept in its own module so it stays independently testable.
This file's only job is to call them in the right order.
"""

from dataclasses import dataclass

from app.retrieval.retrieve import retrieve
from app.generation.generate import generate_answer
from app.generation.verify import verify_claims, summarize_results, VerificationReport, ClaimResult
from app.retrieval.search import SearchResult


@dataclass
class PipelineResult:
    """Everything the API (or a test) might want from one pipeline run."""
    query: str
    answer: str
    chunks: list[SearchResult]       # the retrieved + re-ranked chunks
    claims: list[ClaimResult]        # per-claim judge verdicts
    report: VerificationReport       # the aggregated PASS/REVIEW report


def run_pipeline(query: str) -> PipelineResult:
    """
    Runs the full RAG pipeline for a single query.

    YOUR TASK: fill in the 4 steps below using the imported functions.
    Each step's output feeds directly into the next one.
    """

    # Step 1 — retrieve the most relevant chunks for this query
    chunks = retrieve(query)

    # Step 2 — generate a grounded answer (with [1][2] citations) from those chunks
    answer = generate_answer(query, chunks)

    # Step 3 — judge every claim in the answer against its cited chunk
    claims = verify_claims(answer, chunks)

    # Step 4 — aggregate all claim verdicts into one final report
    report = summarize_results(claims)

    return PipelineResult(
        query=query,
        answer=answer,
        chunks=chunks,
        claims=claims,
        report=report,
    )
