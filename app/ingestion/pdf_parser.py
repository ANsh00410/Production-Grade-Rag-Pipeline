"""
PDF parser.

Design choice: chunk per-page first, then token-split within a page if needed.

PDFs don't have a clean structural signal like markdown headings (unless you
do layout analysis, which is a whole extra project). Page number is the most
reliable, always-available piece of provenance a PDF gives you for free, so
we anchor every chunk to it — "page 12" is a citation a user can actually
verify by opening the source file.

Note: this is a text-layer extractor. Scanned/image-only PDFs need OCR first
(out of scope here, but worth knowing as a stated limitation if asked).
"""

from pathlib import Path
import pymupdf as fitz  # PyMuPDF (new import name; `fitz` alias kept for readability)
from app.ingestion.models import Chunk
from app.ingestion.chunker import split_into_token_chunks, count_tokens
from app.config import settings


def parse_pdf(file_path: str) -> list[Chunk]:
    path = Path(file_path)
    doc = fitz.open(str(path))

    chunks: list[Chunk] = []
    chunk_idx = 0

    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        if not text:
            continue  # skip blank / image-only pages

        if count_tokens(text) <= settings.chunk_size_tokens:
            sub_texts = [text]
        else:
            sub_texts = split_into_token_chunks(text)

        for sub_text in sub_texts:
            chunks.append(Chunk(
                text=sub_text,
                source_file=path.name,
                source_type="pdf",
                page_number=page_num,
                chunk_index=chunk_idx,
            ))
            chunk_idx += 1

    doc.close()
    return chunks
