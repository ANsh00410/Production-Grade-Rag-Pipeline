import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()  # must run before Settings is defined — os.getenv() in class body runs at import time


@dataclass
class Settings:
    # --- Qdrant ---
    qdrant_host: str = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port: int = int(os.getenv("QDRANT_PORT", "6333"))
    collection_name: str = "internal_docs"

    # --- Chunking ---
    # Measured in tokens, not characters -> consistent across languages/models.
    chunk_size_tokens: int = 450
    chunk_overlap_tokens: int = 60   # ~15% overlap: keeps context across chunk boundaries

    # --- Embeddings ---
    # bge-small: 384-dim, fast, runs locally on CPU. Good default for learning + demos.
    # Swap to "BAAI/bge-large-en-v1.5" later to benchmark quality vs cost/latency.
    dense_model_name: str = "BAAI/bge-small-en-v1.5"
    sparse_model_name: str = "Qdrant/bm25"  # fastembed's BM25-style sparse encoder

    # --- Retrieval ---
    hybrid_top_k: int = 30      # candidates pulled from each of dense/sparse before fusion
    rrf_k: int = 60             # RRF smoothing constant (see README for why 60)

    # --- Re-ranking ---
    rerank_top_k: int = 6       # final chunks passed to the LLM after re-ranking
    reranker_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # --- LLM ---
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    generation_model: str = "openai/gpt-oss-120b"
    judge_model: str = "openai/gpt-oss-120b"


settings = Settings()