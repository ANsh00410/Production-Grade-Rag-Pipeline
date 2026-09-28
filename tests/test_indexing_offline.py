"""
Tests the indexing pipeline structurally, without needing network access to
either Hugging Face (for real embedding models) or a real Qdrant server.

Two techniques make this possible:
1. Qdrant's in-memory client (`QdrantClient(":memory:")`) runs a real Qdrant
   engine inside the process — same API, same validation, no server needed.
2. We monkeypatch `embed_dense`/`embed_sparse` with fakes that return
   correctly-shaped (but meaningless) vectors, so we're testing "does our
   code build valid points and upsert them correctly," not "is bge-small
   a good embedding model" (a separate concern, tested separately, for real,
   once you have network access on your own machine).
"""

import random
from qdrant_client import QdrantClient
import app.indexing.qdrant_store as qdrant_store
from app.ingestion.models import Chunk
from app.indexing.embedder import SparseVector


def fake_embed_dense(texts: list[str]) -> list[list[float]]:
    random.seed(42)  # deterministic, so test output is reproducible
    return [[random.random() for _ in range(384)] for _ in texts]


def fake_embed_sparse(texts: list[str]) -> list[SparseVector]:
    return [SparseVector(indices=[1, 5, 9], values=[0.5, 0.3, 0.9]) for _ in texts]


def run_test():
    # 1. Point the module at an in-memory Qdrant instance instead of a real server.
    qdrant_store._client = QdrantClient(":memory:")

    # 2. Swap the real (network-dependent) embedders for fakes.
    qdrant_store.embed_dense = fake_embed_dense
    qdrant_store.embed_sparse = fake_embed_sparse

    # 3. Build some test chunks (reuse our real Chunk model + real chunk_id logic).
    chunks = [
        Chunk(text=f"This is test chunk number {i}.", source_file="test.md",
              source_type="markdown", heading_path="Test Section", chunk_index=i)
        for i in range(5)
    ]

    print(f"Testing with {len(chunks)} chunks...")
    qdrant_store.ensure_collection(recreate=True)
    qdrant_store.upsert_chunks(chunks, batch_size=2)  # small batch to test batching loop

    # 4. Verify: query the collection back and check point count + payload integrity.
    client = qdrant_store.get_client()
    count = client.count(collection_name="internal_docs").count
    assert count == 5, f"expected 5 points, got {count}"

    # Fetch one point back and check the payload round-tripped correctly.
    points = client.retrieve(
        collection_name="internal_docs",
        ids=[chunks[0].chunk_id_as_uuid()],
        with_payload=True,
        with_vectors=True,
    )
    assert len(points) == 1
    p = points[0]
    assert p.payload["text"] == chunks[0].text
    assert p.payload["heading_path"] == "Test Section"
    assert "dense" in p.vector
    assert "sparse" in p.vector
    assert len(p.vector["dense"]) == 384

    print("\n[OK] All checks passed:")
    print(f"   - collection created with {count} points")
    print(f"   - batching loop ran correctly (batch_size=2, 5 chunks -> 3 batches)")
    print(f"   - payload round-trips correctly (text, heading_path)")
    print(f"   - both 'dense' (384-dim) and 'sparse' vectors stored per point")
    print(f"   - chunk_id -> UUID mapping is stable and retrievable")


if __name__ == "__main__":
    run_test()
