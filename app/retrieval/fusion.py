"""
Reciprocal Rank Fusion (RRF).

Combines multiple ranked lists (e.g. dense search results, sparse/BM25
results) into a single fused ranking, WITHOUT needing the raw scores from
each method to be on comparable scales — cosine similarity (0-1) and BM25
scores (unbounded, corpus-dependent) can't be meaningfully averaged, but
rank *position* is comparable across any ranking method.

    RRF_score(doc) = sum over every list the doc appears in of: 1 / (k + rank)

`k` is a smoothing constant (60 is the common default from the original
paper) that dampens how much the very top ranks dominate — a large k makes
rank 1 vs rank 5 matter less; a small k makes it matter a lot.

Key property this produces: a document ranked moderately well by BOTH
retrieval methods will often outscore a document ranked #1 by only ONE
method. That's exactly the behavior you want from a fusion strategy — it
rewards agreement between independent signals over a single method's
overconfidence.

This function is intentionally pure (no I/O, no Qdrant, no embeddings) so
it's fully unit-testable with plain Python lists — see tests/test_fusion.py.
"""


def reciprocal_rank_fusion(
    ranked_lists: list[list[str]],
    k: int = 60,
) -> list[tuple[str, float]]:
    """
    ranked_lists: one or more ranked lists of doc/chunk IDs, each already
                  sorted best-to-worst by that retrieval method.
    k:            RRF smoothing constant.

    Returns: list of (doc_id, fused_score), sorted by fused_score descending.
    """
    scores: dict[str, float] = {}

    for ranked in ranked_lists:
        for rank, doc_id in enumerate(ranked, start=1):
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)

    return sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
