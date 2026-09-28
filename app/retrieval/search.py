"""
The two retrieval "halves" that get fused later.

Each function does ONE type of search and returns a ranked list — that's it.
Fusion (combining these two rankings into one) is a deliberately separate
concern, handled in fusion.py. Keeping them separate means you can test,
swap, or debug each retrieval method independently of the fusion logic.
"""

from dataclasses import dataclass
from qdrant_client import models
from app.indexing.qdrant_store import get_client
from app.indexing.embedder import embed_dense, embed_sparse
from app.config import settings


@dataclass
class SearchResult:
    chunk_id: str          # our short hex chunk_id (from payload, not the Qdrant UUID)
    point_id: str           # the Qdrant UUID (needed if we want to re-fetch this exact point)
    score: float
    payload: dict


def dense_search(query: str, top_k: int = settings.hybrid_top_k) -> list[SearchResult]:
    client = get_client()
    query_vector = embed_dense([query])[0]

    hits = client.query_points(
        collection_name=settings.collection_name,
        query=query_vector,
        using="dense",
        limit=top_k,
        with_payload=True,
    ).points

    return [
        SearchResult(
            chunk_id=h.payload["chunk_id"],
            point_id=str(h.id),
            score=h.score,
            payload=h.payload,
        )
        for h in hits
    ]


def sparse_search(query: str, top_k: int = settings.hybrid_top_k) -> list[SearchResult]:
    client = get_client()
    query_sparse = embed_sparse([query])[0]

    hits = client.query_points(
        collection_name=settings.collection_name,
        query=models.SparseVector(
            indices=query_sparse.indices,
            values=query_sparse.values,
        ),
        using="sparse",
        limit=top_k,
        with_payload=True,
    ).points

    return [
        SearchResult(
            chunk_id=h.payload["chunk_id"],
            point_id=str(h.id),
            score=h.score,
            payload=h.payload,
        )
        for h in hits
    ]
