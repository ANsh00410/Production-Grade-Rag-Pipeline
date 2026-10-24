"""
Single entrypoint for ingestion: point it at a directory of mixed-format
docs, get back a flat list of Chunk objects ready for indexing.

This is the "multi-format ingestion pipeline" piece — the dispatcher pattern
here matters: adding a new format later (docx, csv, Notion export, whatever)
means writing one new parser function and adding one line here. Nothing else
in the pipeline needs to change.
"""

from pathlib import Path
from app.ingestion.models import Chunk
from app.ingestion.markdown_parser import parse_markdown
from app.ingestion.pdf_parser import parse_pdf
from app.ingestion.html_parser import parse_html

_PARSERS = {
    ".md": parse_markdown,
    ".markdown": parse_markdown,
    ".pdf": parse_pdf,
    ".html": parse_html,
    ".htm": parse_html,
}


def ingest_file(file_path: str) -> list[Chunk]:
    ext = Path(file_path).suffix.lower()
    parser = _PARSERS.get(ext)
    if parser is None:
        raise ValueError(f"No parser registered for extension '{ext}' ({file_path})")
    return parser(file_path)


def ingest_directory(dir_path: str) -> list[Chunk]:
    all_chunks: list[Chunk] = []
    skipped: list[str] = []

    for file_path in Path(dir_path).rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in _PARSERS:
            skipped.append(str(file_path))
            continue

        chunks = ingest_file(str(file_path))
        all_chunks.extend(chunks)
        print(f"  [OK] {file_path.name}: {len(chunks)} chunks")

    if skipped:
        print(f"  (skipped {len(skipped)} unsupported files: {[Path(s).name for s in skipped]})")

    return all_chunks


if __name__ == "__main__":
    import sys
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "data/sample_docs"
    print(f"Ingesting from: {target_dir}")
    chunks = ingest_directory(target_dir)
    print(f"\nTotal chunks: {len(chunks)}")
    if chunks:
        print("\nSample chunk:")
        c = chunks[0]
        print(f"  id: {c.chunk_id}")
        print(f"  citation: {c.citation_label()}")
        print(f"  text: {c.text[:200]}...")
