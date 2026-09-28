"""
Wraps the two embedding models used for hybrid search:

- Dense: BAAI/bge-small-en-v1.5 (via sentence-transformers)
  A transformer that maps text -> a fixed-length (384-dim) vector, trained so
  that semantically similar text ends up close together (cosine similarity).
  This is what powers "find chunks about a similar CONCEPT."

- Sparse: Qdrant/bm25 (via fastembed)
  Produces a BM25-style sparse vector: mostly zeros, with non-zero weights
  on the specific vocabulary terms present in the text. This is what powers
  "find chunks containing this EXACT term" (SKUs, error codes, function
  names — things dense embeddings are weak at).

Both are loaded once, at module import, and reused across every call —
loading a transformer model is expensive (seconds), so you never want to
reload it per-chunk or per-query.
"""

from dataclasses import dataclass
from app.config import settings

_dense_model = None
_sparse_model = None


def _get_dense_model():
    global _dense_model
    if _dense_model is None:
        from sentence_transformers import SentenceTransformer
        _dense_model = SentenceTransformer(settings.dense_model_name)
    return _dense_model


def _get_sparse_model():
    global _sparse_model
    if _sparse_model is None:
        from fastembed import SparseTextEmbedding
        _sparse_model = SparseTextEmbedding(model_name=settings.sparse_model_name)
    return _sparse_model


@dataclass
class SparseVector:
    indices: list[int]
    values: list[float]


def embed_dense(texts: list[str]) -> list[list[float]]:
    """Batch-embeds texts into dense vectors. Returns list of float lists."""
    model = _get_dense_model()
    # bge models expect a normalized embedding for cosine similarity search;
    # normalize_embeddings=True does that at encode time so Qdrant can use
    # plain dot product (faster) instead of computing cosine similarity itself.
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return vectors.tolist()


def embed_sparse(texts: list[str]) -> list[SparseVector]:
    """Batch-embeds texts into sparse (BM25-style) vectors."""
    model = _get_sparse_model()
    results = list(model.embed(texts))
    return [
        SparseVector(indices=r.indices.tolist(), values=r.values.tolist())
        for r in results
    ]
