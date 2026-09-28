"""
Wires the three retrieval pieces together:
    dense_search()  -> ranked list of chunk_ids (semantic)
    sparse_search() -> ranked list of chunk_ids (keyword)
    reciprocal_rank_fusion() -> one fused ranking

One design wrinkle worth understanding: RRF only operates on IDs and ranks —
it has no idea what a chunk's actual text or metadata is. But the next
stage (re-ranking, then generation) needs the real chunk text to do
anything useful. So after fusion, we look up each fused chunk_id's full
SearchResult (text + payload) from whichever search(es) found it.

We build that lookup from BOTH dense and sparse results combined, because
a chunk might only have been found by one of the two methods — if we only
looked up from dense_results, a sparse-only hit's fused ranking would have
no way to recover its actual text.
"""

from app.retrieval.search import dense_search, sparse_search, SearchResult
from app.retrieval.fusion import reciprocal_rank_fusion
from app.config import settings


def hybrid_search(query: str, top_k: int = settings.hybrid_top_k) -> list[SearchResult]:
    dense_results = dense_search(query, top_k=top_k)
    sparse_results = sparse_search(query, top_k=top_k)

    # Lookup table: chunk_id -> its SearchResult (payload/text), built from
    # both result sets so we can recover data regardless of which method
    # (or both) found a given chunk.
    lookup: dict[str, SearchResult] = {}
    for r in dense_results + sparse_results:
        lookup.setdefault(r.chunk_id, r)

    dense_ranked_ids = [r.chunk_id for r in dense_results]
    sparse_ranked_ids = [r.chunk_id for r in sparse_results]

    fused = reciprocal_rank_fusion(
        [dense_ranked_ids, sparse_ranked_ids],
        k=settings.rrf_k,
    )

    # Re-attach full chunk data, replacing each result's `.score` with the
    # fused RRF score so downstream stages see one consistent scoring scheme
    # rather than juggling cosine-similarity vs BM25 scores.
    results = []
    for chunk_id, fused_score in fused:
        original = lookup[chunk_id]
        results.append(SearchResult(
            chunk_id=original.chunk_id,
            point_id=original.point_id,
            score=fused_score,
            payload=original.payload,
        ))

    return results
