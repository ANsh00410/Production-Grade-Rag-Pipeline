"""
Markdown parser.

Design choice: split by heading structure FIRST, then token-chunk each
section if it's still too long.

Why not just token-chunk the whole file? Because a naive fixed-size split
doesn't know that "## Environment Variables" starts a new topic — it'll
happily put the end of one section and the start of another into the same
chunk, which confuses both retrieval (the chunk is "about" two things at
once) and citation (which heading does this chunk actually belong to?).

By splitting on headings first, every chunk inherits a clean heading_path
like "Setup > Environment Variables", which becomes the citation trail.
"""

from pathlib import Path
from markdown_it import MarkdownIt
from app.ingestion.models import Chunk
from app.ingestion.chunker import split_into_token_chunks, count_tokens
from app.config import settings

_md = MarkdownIt()


def _extract_sections(md_text: str) -> list[dict]:
    """
    Walks the markdown token stream and groups content under its nearest
    heading, tracking heading depth so we can build a path like
    'Setup > Environment Variables'.
    """
    tokens = _md.parse(md_text)
    sections = []
    heading_stack: list[str] = []  # e.g. ["Setup", "Environment Variables"]
    current_text: list[str] = []

    def flush():
        text = "\n".join(current_text).strip()
        if text:
            sections.append({
                "heading_path": " > ".join(heading_stack),
                "text": text,
            })
        current_text.clear()

    i = 0
    while i < len(tokens):
        tok = tokens[i]

        if tok.type == "heading_open":
            flush()
            level = int(tok.tag[1])  # h1 -> 1, h2 -> 2, ...
            heading_text = tokens[i + 1].content  # inline token right after heading_open
            # Trim the stack to this heading's depth, then append.
            heading_stack = heading_stack[: level - 1]
            heading_stack.append(heading_text)
            i += 3  # skip heading_open, inline, heading_close
            continue

        if tok.type in ("paragraph_open", "bullet_list_open", "fence", "code_block"):
            # content-bearing tokens: grab their text where relevant
            if tok.type == "fence" or tok.type == "code_block":
                current_text.append(f"```\n{tok.content}```")
            i += 1
            continue

        if tok.type == "inline":
            current_text.append(tok.content)

        i += 1

    flush()
    return sections


def parse_markdown(file_path: str) -> list[Chunk]:
    path = Path(file_path)
    md_text = path.read_text(encoding="utf-8")
    sections = _extract_sections(md_text)

    chunks: list[Chunk] = []
    chunk_idx = 0

    for section in sections:
        text = section["text"]
        heading_path = section["heading_path"]

        # If the section is small enough, keep it as one chunk (best case:
        # a whole coherent idea in one chunk). Otherwise, token-split it,
        # inheriting the same heading_path across the sub-chunks.
        if count_tokens(text) <= settings.chunk_size_tokens:
            sub_texts = [text]
        else:
            sub_texts = split_into_token_chunks(text)

        for sub_text in sub_texts:
            chunks.append(Chunk(
                text=sub_text,
                source_file=str(path.name),
                source_type="markdown",
                heading_path=heading_path,
                chunk_index=chunk_idx,
            ))
            chunk_idx += 1

    return chunks
