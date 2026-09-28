"""
End-to-end indexing script: point it at a directory, get a populated
Qdrant collection ready for hybrid search.

Usage:
    python -m app.indexing.build_index data/raw_docs
"""

import sys
from app.ingestion.ingest import ingest_directory
from app.indexing.qdrant_store import ensure_collection, upsert_chunks


def build_index(source_dir: str, recreate: bool = False):
    print(f"Step 1/2: Ingesting documents from {source_dir}")
    chunks = ingest_directory(source_dir)
    print(f"  -> {len(chunks)} chunks total\n")

    if not chunks:
        print("No chunks produced — nothing to index.")
        return

    print("Step 2/2: Embedding + upserting into Qdrant")
    ensure_collection(recreate=recreate)
    upsert_chunks(chunks)
    print(f"\nDone. Collection now contains chunks from {source_dir}.")


if __name__ == "__main__":
    source_dir = sys.argv[1] if len(sys.argv) > 1 else "data/sample_docs"
    recreate = "--recreate" in sys.argv
    build_index(source_dir, recreate=recreate)
