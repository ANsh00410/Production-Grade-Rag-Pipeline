"""
Shows every chunk currently sitting in the Qdrant collection — the full
pool that dense/sparse search choose FROM. Useful for understanding
retrieval as "compare the query against ALL of these, then rank," rather
than a black box that just hands back a few results.

Usage:
    python -m tests.list_all_chunks
"""

from app.indexing.qdrant_store import get_client
from app.config import settings


def list_all_chunks():
    client = get_client()

    # scroll() pages through every point in the collection — unlike
    # search(), it doesn't rank anything, it just returns what's stored.
    points, _ = client.scroll(
        collection_name=settings.collection_name,
        limit=100,          # fine for a small demo corpus; would need
                             # pagination via the second return value for
                             # a large real index
        with_payload=True,
        with_vectors=False,  # we don't need the raw vectors just to read text
    )

    print(f"Total chunks in '{settings.collection_name}': {len(points)}\n")
    for i, p in enumerate(points, start=1):
        payload = p.payload
        print(f"{i}. {payload.get('heading_path') or payload.get('source_file')}")
        print(f"   {payload['text'][:120]}...")
        print()


if __name__ == "__main__":
    list_all_chunks()