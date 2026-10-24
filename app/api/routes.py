import os
import shutil
import tempfile

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.ingestion.ingest import ingest_file
from app.indexing.qdrant_store import get_collection_info, upsert_chunks
from app.pipeline import run_pipeline


# --- Pydantic models (API contract — separate from internal dataclasses) ---

class QueryRequest(BaseModel):
    question: str


class ClaimResponse(BaseModel):
    """One claim's judge result, safe to serialize to JSON."""
    claim: str
    citations: list[int]
    verdict: str    # SUPPORTED | PARTIAL | NOT_SUPPORTED | UNKNOWN | UNCITED
    reason: str


class QueryResponse(BaseModel):
    answer: str
    overall: str              # "PASS" | "REVIEW"
    count: dict[str, int]     # e.g. {"SUPPORTED": 3, "PARTIAL": 1}
    claims: list[ClaimResponse]

class IngestResponse(BaseModel):
    filename: str
    chunks_indexed: int
    status: str


class CollectionInfo(BaseModel):
    chunk_count: int
    sources: list[str]


# --- Router (mounted in main.py, NOT the full FastAPI app) ---

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    result = run_pipeline(request.question)

    return QueryResponse(
        answer=result.answer,
        overall=result.report.overall,
        count=result.report.count,
        claims=[
            ClaimResponse(
                claim=cr.claim,
                citations=cr.citations,
                verdict=cr.verdict,
                reason=cr.reason,
            )
            for cr in result.claims
        ],
    )




@router.post("/ingest", response_model=IngestResponse)
async def ingest(file: UploadFile = File(...)):
    # 1. Save the uploaded file to a temp location
    suffix = os.path.splitext(file.filename)[1]  # e.g. ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    # 2. Run your existing ingestion logic
    chunks = ingest_file(tmp_path)
    # 3. Index the chunks (embed + store in Qdrant)
    upsert_chunks(chunks)
    # 4. Clean up temp file
    os.unlink(tmp_path)
    return IngestResponse(
        filename=file.filename,
        chunks_indexed=len(chunks),
        status="ok"
    )


@router.get("/collections", response_model=CollectionInfo)
def collections():
    """Returns total chunk count and list of indexed source files from Qdrant."""
    info = get_collection_info()
    return CollectionInfo(
        chunk_count=info["chunk_count"],
        sources=info["sources"],
    )
