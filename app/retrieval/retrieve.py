"""
The full retrieval pipeline in one call: hybrid search (dense + sparse +
RRF fusion) narrows the whole index down to a candidate shortlist, then the
cross-encoder re-ranks that shortlist down to the final, most-relevant
chunks. This is the one function the generation stage should call — it
shouldn't need to know hybrid_search and rerank are two separate steps.
"""

from app.retrieval.hybrid import hybrid_search
# pyrefly: ignore [missing-import]
from app.retrieval.rerank import rerank
from app.retrieval.search import SearchResult
from app.config import settings


def retrieve(
    query: str,
    candidate_k: int = settings.hybrid_top_k,
    final_k: int = settings.rerank_top_k,
) -> list[SearchResult]:
    candidates = hybrid_search(query, top_k=candidate_k)
    return rerank(query, candidates, top_k=final_k)