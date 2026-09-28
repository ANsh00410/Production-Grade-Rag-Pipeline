"""
Quick sanity check: does dense (semantic) search actually retrieve
sensible chunks for a real query? Run this after build_index.py.

Usage:
    python -m tests.quick_dense_search "how do I deploy to production"
"""

import sys
from app.indexing.qdrant_store import get_client
from app.indexing.embedder import embed_dense
from app.config import settings


def quick_search(query: str, top_k: int = 3):
    client = get_client()
    query_vector = embed_dense([query])[0]  # embed the query the same way we embedded chunks

    results = client.query_points(
        collection_name=settings.collection_name,
        query=query_vector,
        using="dense",       # search only the "dense" named vector
        limit=top_k,
        with_payload=True,
    ).points

    print(f"Query: {query!r}\n")
    for i, r in enumerate(results, 1):
        print(f"{i}. score={r.score:.4f}  [{r.payload['heading_path']}]")
        print(f"   {r.payload['text'][:150]}...\n")


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or "how do I deploy to production"
    quick_search(query)
