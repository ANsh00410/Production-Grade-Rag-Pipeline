"""
Core data model shared by every parser (md, pdf, html) and every downstream
stage (indexing, retrieval, generation).

Why this matters more than it looks like it should:
Most "toy" RAG pipelines chunk text and throw away everything except the raw
string. That works fine until someone asks "which document did this answer
come from?" and you have nothing to point to. Every chunk here carries enough
metadata to be cited back to an exact location in an exact source file.
"""

from dataclasses import dataclass, field
from typing import Optional
import hashlib
import uuid

# A fixed namespace UUID so that uuid.uuid5(NAMESPACE, chunk_id) is
# deterministic across runs — same chunk_id always maps to the same
# Qdrant point UUID, so re-ingesting unchanged docs upserts (overwrites)
# the same points instead of creating duplicates.
_UUID_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


@dataclass
class Chunk:
    # The actual text that gets embedded and shown to the LLM.
    text: str

    # --- Provenance metadata (this is what enables citations) ---
    source_file: str                       # e.g. "docs/onboarding.md"
    source_type: str                       # "markdown" | "pdf" | "html"
    heading_path: str = ""                 # e.g. "Setup > Environment Variables"
    page_number: Optional[int] = None      # PDFs only
    chunk_index: int = 0                   # position among chunks from the same source

    # --- Identity ---
    chunk_id: str = field(default="")      # stable id, derived in __post_init__

    def __post_init__(self):
        if not self.chunk_id:
            # Deterministic ID: same source + same position + same text -> same id.
            # This matters for re-ingestion: re-running ingestion on an unchanged
            # doc won't create duplicate vectors in Qdrant.
            raw = f"{self.source_file}:{self.chunk_index}:{self.text[:50]}"
            self.chunk_id = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def citation_label(self) -> str:
        """Human-readable citation string, e.g. 'onboarding.md > Setup (chunk 3)'"""
        loc = self.heading_path or (f"page {self.page_number}" if self.page_number else "")
        base = f"{self.source_file}"
        if loc:
            base += f" > {loc}"
        return base

    def chunk_id_as_uuid(self) -> str:
        """
        Qdrant point IDs must be an unsigned int or a valid UUID string —
        our short hex chunk_id doesn't qualify. uuid.uuid5 deterministically
        derives a real UUID from our chunk_id, so the same chunk always maps
        to the same Qdrant point (re-ingestion overwrites, never duplicates).
        """
        return str(uuid.uuid5(_UUID_NAMESPACE, self.chunk_id))
