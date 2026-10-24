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


# Here's the full trace:

# 1. Source file


# data/sample_docs/onboarding.md
#  — the only doc you indexed. You can see in your earlier command output:

# ✓ onboarding.md: 6 chunks
# 2. Ingestion & chunking


# app/indexing/build_index.py
#  reads that file, parses it by Markdown headings, and splits it into 6 chunks using tiktoken (450 token max per chunk, 60 token overlap — set in 

# config.py
# ).

# 3. Stored in Qdrant


# app/indexing/qdrant_store.py → upsert_chunks()
#  embeds each chunk as both a dense vector (bge-small, 384-dim) and a sparse vector (BM25-style), then upserts them into the internal_docs collection.

# 4. list_all_chunks reads from Qdrant


# tests/list_all_chunks.py
#  calls client.scroll() on that collection — no search/ranking, just dumps every stored point raw.

# So the 6 chunks you see are the 6 heading sections from onboarding.md. If you add more files to data/sample_docs/ and re-run:

# powershell
# python -m app.indexing.build_index data/sample_docs --recreate
# ...those new docs will also show up in list_all_chunks.