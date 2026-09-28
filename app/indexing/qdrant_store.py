"""
Qdrant collection setup + upsert.

The collection schema is the important part here: it declares TWO named
vectors per point ("dense" and "sparse"), so a single query can search both
representations of the same underlying chunks, and a single point ID always
maps back to one chunk with one payload (no separate systems to keep in sync).
"""

from qdrant_client import QdrantClient, models
from app.config import settings
from app.ingestion.models import Chunk
from app.indexing.embedder import embed_dense, embed_sparse

_client: QdrantClient | None = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    return _client


def ensure_collection(recreate: bool = False):
    """
    Creates the collection if it doesn't exist (or recreates it if
    `recreate=True`, useful during dev when you're iterating on chunking
    and want a clean slate each time).
    """
    client = get_client()
    exists = client.collection_exists(settings.collection_name)

    if exists and not recreate:
        return

    if exists and recreate:
        client.delete_collection(settings.collection_name)

    client.create_collection(
        collection_name=settings.collection_name,
        vectors_config={
            # 384-dim dense vector from bge-small, cosine similarity.
            "dense": models.VectorParams(size=384, distance=models.Distance.COSINE),
        },
        sparse_vectors_config={
            # Sparse vectors don't have a fixed "size" — dimensionality is
            # effectively the vocabulary size, and only non-zero entries are
            # stored, so Qdrant just needs to know this vector name exists
            # and is sparse.
            "sparse": models.SparseVectorParams(),
        },
    )


def upsert_chunks(chunks: list[Chunk], batch_size: int = 32):
    """
    Embeds and upserts chunks in batches. Batching matters here for two
    reasons: (1) embedding models run much faster on a batch than one text
    at a time (GPU/CPU vectorization), and (2) Qdrant's upsert call has
    per-request overhead you don't want to pay per-chunk.
    """
    client = get_client()
    ensure_collection()

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [c.text for c in batch]

        dense_vectors = embed_dense(texts)
        sparse_vectors = embed_sparse(texts)

        points = []
        for chunk, dense_vec, sparse_vec in zip(batch, dense_vectors, sparse_vectors):
            points.append(models.PointStruct(
                id=chunk.chunk_id_as_uuid(),
                vector={
                    "dense": dense_vec,
                    "sparse": models.SparseVector(
                        indices=sparse_vec.indices,
                        values=sparse_vec.values,
                    ),
                },
                payload={
                    "text": chunk.text,
                    "source_file": chunk.source_file,
                    "source_type": chunk.source_type,
                    "heading_path": chunk.heading_path,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                    "chunk_id": chunk.chunk_id,  # keep the original short id too
                },
            ))

        client.upsert(collection_name=settings.collection_name, points=points)
        print(f"  upserted batch {i // batch_size + 1} ({len(points)} points)")
