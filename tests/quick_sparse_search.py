"""
Sparse-only search sanity check — isolates the BM25/keyword half of hybrid
search so you can see its raw scores and ranking BEFORE fusion, separate
from hybrid_search()'s RRF-fused output.

Usage:
    python -m tests.quick_sparse_search "how do I deploy to production"
"""

import sys
from app.retrieval.search import sparse_search


def quick_sparse_search(query: str, top_k: int = 10):
    results = sparse_search(query, top_k=top_k)

    print(f"SPARSE-ONLY results for: {query!r}\n")
    for i, r in enumerate(results, 1):
        print(f"{i}. score={r.score:.4f}  [{r.payload['heading_path']}]")
        print(f"   {r.payload['text'][:100]}...\n")


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or "how do I deploy to production"
    quick_sparse_search(query)