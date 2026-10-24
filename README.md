# Production-Grade RAG Pipeline with Citation Verification & Hallucination Judge

An end-to-end, production-grade Retrieval-Augmented Generation (RAG) system with hybrid vector search, grounded generation, claim-level hallucination verification, and a modern React web interface. Entirely containerized for one-command deployment.

---

## 🚀 Key Highlights & Features

- **Multi-Format Ingestion:** Header/page-aware parsing for **PDFs**, **Markdown**, and **HTML** with deterministic chunk IDs and layout provenance.
- **Hybrid Search & Fusion:** Dual-vector indexing in **Qdrant** combining dense semantic embeddings (`BAAI/bge-small-en-v1.5`) and BM25-style sparse vectors, fused via **Reciprocal Rank Fusion (RRF)**.
- **Grounded Generation:** LLM inference powered by **Groq (LLaMA 3.3 70B Versatile)**, strictly constrained to retrieved context with bracketed citations (`[1]`, `[2]`).
- **Claim-Level Hallucination & Citation Judge:** Deconstructs generated answers into atomic factual claims, independently audits attribution against cited chunks, and classifies each claim (`SUPPORTED`, `PARTIAL`, `NOT_SUPPORTED`, `UNKNOWN`).
- **React + Vite Frontend:** Dark glassmorphic interface with interactive claim inspection, real-time verdict donut charts, document upload, and an in-app Pipeline Guide.
- **Single-Command Docker:** Multi-stage containerized setup (FastAPI + React + Qdrant + Nginx reverse proxy) runnable with `docker compose up --build`.

---

## 🧠 What the Pipeline Gives You

When you submit a query, the system returns:

1. **Grounded Answer with Bracketed Citations:** A concise, natural response where every statement contains inline bracket markers (e.g. `[2][3]`) linking directly to the retrieved passages.
2. **Executive Audit Verdict (`PASS` vs `⚠ REVIEW`):** 
   - `PASS`: Every claim in the answer is 100% corroborated by the documentation.
   - `⚠ REVIEW`: The system detected an extrapolation, ungrounded assumption, or citation mismatch that requires human validation.
3. **Verdict Breakdown Metrics:** A visual summary and count of factual reliability (e.g., *75% Supported, 25% Partial*).
4. **Claim-by-Claim Audit Trail:** Full transparency cards detailing:
   - The exact atomic statement.
   - The cited chunk ID(s).
   - The verdict (`Supported`, `Partial`, `Not Supported`, `Unknown`).
   - The judge's exact reasoning explaining why the claim was accepted or flagged.

---

## ⚖️ What You Have to Care About (Reading the Verdicts)

Standard RAG systems give you a confident paragraph with no indication of whether the LLM hallucinated. This pipeline acts as a **strict compliance auditor**:

| Verdict | Meaning | What You Need to Know |
| :--- | :--- | :--- |
| **`SUPPORTED`** 🟢 | **100% Backed by Document** | Every fact in this claim is explicitly proven by the cited source chunk. Safe for automated decision-making. |
| **`PARTIAL`** 🟡 | **Subtle Extrapolation / Missing Sub-clause** | The core premise may be accurate, but the LLM added an assumption, extrapolated a phrase, or combined multiple facts where one sub-clause was missing from the cited chunk. |
| **`NOT_SUPPORTED`** 🔴 | **Contradiction / Hallucination** | The statement contradicts the source documentation or is absent from the knowledge base. |
| **`UNKNOWN`** ⚪ | **Citation Mismatch** | The claim either lacks a citation or cited a chunk discussing an unrelated section of the document. |

### 💡 Tips for Achieving 100% `PASS` Rates
1. **Targeted Questions:** Specific queries (e.g., *"What is the maximum loan tenure?"*) map cleanly to single chunks, guaranteeing tight 1-to-1 attribution.
2. **Request Bullet Points for Broad Summaries:** Asking for *"concise bullet points with citations"* prevents run-on sentences that merge multiple clauses into one compound claim.
3. **Inspect the Citation Tags:** Clicking/checking the `[N]` tags shows the exact source paragraph used to audit the claim.

---

## 🛠️ Single-Command Quickstart

Ensure **Docker Desktop** is running, then run:

```bash
docker compose up --build
```
*(or run in the background with `-d`: `docker compose up --build -d`)*

### Access Points

| Service | URL | Role |
| :--- | :--- | :--- |
| **React Web UI** | `http://localhost` | Clean search interface, claim inspector, and doc upload |
| **FastAPI Swagger Docs** | `http://localhost:8000/docs` | Interactive REST API documentation |
| **Qdrant Dashboard** | `http://localhost:6333/dashboard` | Visual inspection of vectors, payloads, and collections |

To tear down containers while keeping vector database data intact:
```bash
docker compose down
```

---

## 🏛️ System Architecture

```text
User Question
      │
      ▼
┌────────────────────────────────────────────────────────┐
│ 1. Hybrid Search & Retrieval (Qdrant)                   │
│    ├─ Dense Embedding: BAAI/bge-small-en-v1.5           │
│    ├─ Sparse Embedding: BM25 (FastEmbed)               │
│    └─ Fusion: Reciprocal Rank Fusion (RRF)              │
└────────────────────────────────────┬───────────────────┘
                                     │ Top Chunks [1..k]
                                     ▼
┌────────────────────────────────────────────────────────┐
│ 2. Grounded Generation (Groq / LLaMA 3.3 70B)          │
│    └─ Synthesizes answer with inline citations [1], [2] │
└────────────────────────────────────┬───────────────────┘
                                     │ Answer + Citations
                                     ▼
┌────────────────────────────────────────────────────────┐
│ 3. Citation & Hallucination Judge                      │
│    ├─ Splits response into atomic factual claims       │
│    ├─ Maps claims to their cited chunk text            │
│    └─ Evaluates: SUPPORTED / PARTIAL / NOT_SUPPORTED   │
└────────────────────────────────────┬───────────────────┘
                                     │ Audited Result
                                     ▼
                      React UI (http://localhost)
```

---

## 📂 Project Structure

```text
├── app/
│   ├── api/                  # FastAPI web server and routes (/query, /ingest, /collections, /health)
│   ├── ingestion/            # PDF, Markdown, and HTML chunking with sliding-window overlap
│   ├── indexing/             # Qdrant client, schema initialization, and dense+sparse embedders
│   ├── retrieval/            # Dense search, sparse search, and Reciprocal Rank Fusion (RRF)
│   ├── generation/           # Prompt templates, Groq generation, and LLM-as-a-judge verifier
│   └── config.py             # Centralized pipeline configuration
├── frontend/
│   ├── src/                  # React + Vite application (Query page, Guide page, Ingest, Collections)
│   ├── nginx.conf            # Reverse proxy (/api/* → backend:8000) and SPA static server
│   └── Dockerfile            # Multi-stage Node 20 builder → Nginx 1.27 Alpine runtime
├── data/
│   └── sample_docs/          # Sample policy documents (e.g. Home Loan Policy PDF)
├── docker-compose.yml        # Multi-container orchestration (Qdrant, Backend, Frontend)
├── Dockerfile                # Backend container with CPU-only PyTorch pre-installation
├── requirements.txt          # Python dependencies
└── README.md
```

---

## 🎯 Production Design Highlights (For Technical Interviews)

- **Structure-First Chunking:** Markdown and HTML are parsed hierarchically by headings prior to token windowing; PDFs are split by page boundaries. Unrelated sections are never arbitrarily merged.
- **Dual Vector Representation in a Single Collection:** Rather than maintaining separate databases for keyword and semantic search, Qdrant stores both `dense` and `sparse` vectors alongside metadata payloads in a single point.
- **Deterministic Chunk IDs:** UUIDv5 hashes generated from document source path and text content ensure that re-ingesting a document updates existing points without creating duplicates.
- **Auditable Claim Decomposition:** Instead of a binary "hallucination score", answers are broken down into individual claims so users can pinpoint exactly which sub-clause lacks documentation.
- **CPU-Optimized Container Build:** Backend Dockerfile pins CPU-only wheels for PyTorch, reducing image size by over 1.2 GB and eliminating heavy GPU driver overhead during container initialization.
