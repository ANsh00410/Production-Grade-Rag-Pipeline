"""
Full pipeline test: real hybrid search + re-ranking + real Groq generation.

Usage:
    python -m tests.quick_generate "how do I deploy to production"
"""

import sys
from app.retrieval.retrieve import retrieve
from app.generation.generate import generate_answer


def quick_generate(query: str):
    print(f"Query: {query!r}\n")

    chunks = retrieve(query)
    print(f"Retrieved {len(chunks)} chunks after re-ranking:")
    for i, c in enumerate(chunks, start=1):
        print(f"  [{i}] {c.payload['heading_path']} (score={c.score:.2f})")

    print("\nGenerating answer...\n")
    answer = generate_answer(query, chunks)

    print("=" * 60)
    print(answer)
    print("=" * 60)


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or "how do I deploy to production"
    quick_generate(query)