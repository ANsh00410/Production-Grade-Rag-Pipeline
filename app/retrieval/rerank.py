"""
Cross-encoder re-ranking.

Unlike dense_search (a bi-encoder — embeds query and chunk SEPARATELY, then
compares vectors), a cross-encoder takes the query and chunk text TOGETHER
as one input and outputs a single relevance score via full cross-attention
between them. This lets it catch things a bi-encoder's independent
embeddings structurally can't — e.g. noticing a chunk merely MENTIONS a
query term without actually being ABOUT what the query is asking.

Trade-off: this joint processing is much slower per (query, chunk) pair
than a bi-encoder's precomputed, reusable embeddings. So it's only run on
hybrid_search()'s already-narrowed candidate list (e.g. top 30), never the
full index — this is the standard "retrieve cheap, then re-rank precisely"
two-stage pattern.
"""

from app.retrieval.search import SearchResult
from app.config import settings

_reranker_model = None


def _get_reranker():
    global _reranker_model
    if _reranker_model is None:
        from sentence_transformers import CrossEncoder
        _reranker_model = CrossEncoder(settings.reranker_model_name)
    return _reranker_model


def rerank(
    query: str,
    candidates: list[SearchResult],
    top_k: int = settings.rerank_top_k,
) -> list[SearchResult]:
    if not candidates:
        return []

    model = _get_reranker()

    # Cross-encoders take a list of (query, document_text) PAIRS and score
    # each jointly — this is the "processes them together" step.
    pairs = [(query, c.payload["text"]) for c in candidates]
    scores = model.predict(pairs)

    # Re-attach the cross-encoder's score (replacing the RRF fused score —
    # downstream stages should see one final, trustworthy relevance signal,
    # not a mix of scoring schemes from earlier stages).
    reranked = [
        SearchResult(
            chunk_id=c.chunk_id,
            point_id=c.point_id,
            score=float(score),
            payload=c.payload,
        )
        for c, score in zip(candidates, scores)
    ]

    reranked.sort(key=lambda r: r.score, reverse=True)
    return reranked[:top_k]