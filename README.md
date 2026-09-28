# RAG Pipeline — Hybrid Search over Internal Docs

Production-style RAG: multi-format ingestion, hybrid (dense + sparse) retrieval
in Qdrant, re-ranking, grounded generation with citations, and LLM-as-judge
citation verification. Served via FastAPI, containerized with Docker.

## Status (what's built so far)

- ✅ Multi-format ingestion (markdown, PDF, HTML) — header/page-aware chunking
- ✅ Token-based sliding-window chunker with overlap (offline fallback if `tiktoken` can't reach the network)
- ✅ Qdrant indexing — dense (`bge-small`) + sparse (BM25-style, via `fastembed`) vectors per chunk, single collection
- ✅ Offline-testable indexing logic (Qdrant in-memory mode + mocked embeddings — see `tests/test_indexing_offline.py`)
- ✅ Dense search + sparse search (`app/retrieval/search.py`)
- ✅ Reciprocal Rank Fusion (`app/retrieval/fusion.py`) — pure, unit-tested (`tests/test_fusion.py`), no network needed
- ✅ `hybrid_search()` wiring dense + sparse + fusion together (`app/retrieval/hybrid.py`)
- ⬜ Cross-encoder re-ranking — **next step**
- ⬜ Grounded generation with inline citations (Claude API)
- ⬜ LLM-as-judge citation verification
- ⬜ FastAPI service (`/ingest`, `/query`, `/health`)

## Setup on your machine

### 1. Prerequisites
- Python 3.11+
- Docker + Docker Compose (for Qdrant)
- An Anthropic API key (for the generation + judge stages, later)

### 2. Install dependencies
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Start Qdrant
```bash
docker compose up -d qdrant
```
Confirm it's up: open http://localhost:6333/dashboard in a browser.

### 4. Run ingestion + indexing on the sample doc
```bash
python -m app.indexing.build_index data/sample_docs --recreate
```
This will download `BAAI/bge-small-en-v1.5` (dense) and the BM25 sparse model
from Hugging Face on first run — that part needs real internet access, which
is exactly what failed in the sandboxed environment this was built in. On
your machine it should just work.

You should see output like:
```
Step 1/2: Ingesting documents from data/sample_docs
  ✓ onboarding.md: 6 chunks
  -> 6 chunks total

Step 2/2: Embedding + upserting into Qdrant
  upserted batch 1 (6 points)

Done. Collection now contains chunks from data/sample_docs.
```

### 5. Verify it landed in Qdrant
Open http://localhost:6333/dashboard, click into the `internal_docs`
collection, and confirm you see 6 points with both `dense` and `sparse`
vectors and readable payloads (text, heading_path, etc.).

### 6. Run the offline structural test (no network needed)
```bash
python -m tests.test_indexing_offline
```
This validates the indexing code's correctness (schema, batching, ID
stability) using Qdrant's in-memory mode and mocked embeddings — useful to
re-run any time you touch `qdrant_store.py` or `embedder.py`, without
waiting on model downloads or a running server.

## Project structure

```
app/
  ingestion/
    models.py           # Chunk dataclass (the shared data model + citation metadata)
    chunker.py           # token-based sliding-window splitter (tiktoken + offline fallback)
    markdown_parser.py   # header-aware markdown -> Chunk[]
    pdf_parser.py         # page-aware PDF -> Chunk[]
    html_parser.py       # header-aware HTML -> Chunk[]
    ingest.py            # dispatcher: routes any file to the right parser
  indexing/
    embedder.py           # dense (bge-small) + sparse (BM25-style) embedding wrappers
    qdrant_store.py       # collection schema, upsert logic
    build_index.py        # CLI: ingest -> embed -> upsert end-to-end
  retrieval/
    search.py             # dense_search() + sparse_search() against real Qdrant
    fusion.py             # Reciprocal Rank Fusion (pure logic, no dependencies)
    hybrid.py             # wires dense + sparse + fusion into hybrid_search()
  generation/             # (next: grounded generation, LLM-as-judge)
  api/                    # (next: FastAPI app)
  config.py               # all tunable settings in one place
data/
  sample_docs/             # test docs (onboarding.md)
  raw_docs/                 # put your real internal docs here
tests/
  test_indexing_offline.py
docker-compose.yml         # wires Qdrant + the API service together
Dockerfile                 # multi-stage build for the API service
requirements.txt
```

## Design notes worth remembering for interviews

- **Chunking is structure-first, size-limit-second**: markdown/HTML are split
  by heading before any token-size splitting happens, so a chunk never mixes
  two unrelated sections. PDF is split by page (the only reliable structural
  signal PDFs give you for free without layout analysis).
- **Token-based chunking, not character/word-based**: chunk size is measured
  in tokens because that's the unit embedding models and LLM context windows
  actually consume — word count is a poor proxy, especially for
  jargon-heavy/technical text which tokenizes less efficiently than plain prose.
- **Overlap** (`chunk_size - overlap` stride) exists so an idea straddling a
  chunk boundary still appears whole in at least one chunk.
- **Every chunk carries provenance metadata** (source file, heading path or
  page number) from the moment it's created — this is what makes citations
  possible later; bolting metadata on after the fact doesn't work.
- **Deterministic chunk IDs** (`sha256` of source+position+text prefix,
  mapped to a UUID via `uuid.uuid5`) mean re-ingesting an unchanged doc
  overwrites the same Qdrant points instead of creating duplicates.
- **Single Qdrant collection, two named vectors** (`dense` + `sparse`) per
  point, rather than two separate systems (e.g. Chroma + Elasticsearch) —
  keeps hybrid search's two representations tied to the same payload/ID
  without manual stitching.
- **Offline-testable indexing logic**: Qdrant's in-memory client +
  mocked embedders let you verify schema/batching/ID correctness without
  network access — separate concern from embedding *quality*, which needs
  the real model.

## Next session: pick up here

Next stage is cross-encoder re-ranking on top of `hybrid_search()`'s fused
results, then grounded generation with inline citations.

## A note on this repo's history

This project was built incrementally across a chat session with Claude,
with the sandbox environment's filesystem resetting between some turns.
If you notice a file's content doesn't quite match what was discussed at
some point, this zip is the source of truth — it was reassembled and
verified (tests re-run) after the reset to make sure nothing was lost.
