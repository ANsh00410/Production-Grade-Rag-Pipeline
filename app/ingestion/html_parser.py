"""
HTML parser.

Same section-aware idea as the markdown parser: walk the DOM in document
order, track the current heading (h1-h6) as we go, and group text nodes
under their nearest heading. This handles real-world "internal docs" HTML
(Confluence exports, wikis, help centers) reasonably well without needing
a full layout engine.

We strip nav/script/style/footer tags first since they're boilerplate, not
content — including them would pollute retrieval with menu text.
"""

from pathlib import Path
from bs4 import BeautifulSoup
from app.ingestion.models import Chunk
from app.ingestion.chunker import split_into_token_chunks, count_tokens
from app.config import settings

_STRIP_TAGS = ["script", "style", "nav", "footer", "header", "aside"]
_HEADING_TAGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}


def _extract_sections(soup: BeautifulSoup) -> list[dict]:
    for tag_name in _STRIP_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    body = soup.body or soup
    sections = []
    heading_stack: list[str] = []
    current_text: list[str] = []

    def flush():
        text = "\n".join(t for t in current_text if t.strip())
        if text.strip():
            sections.append({
                "heading_path": " > ".join(heading_stack),
                "text": text.strip(),
            })
        current_text.clear()

    # Walk all descendant elements in document order.
    for el in body.find_all(True, recursive=True):
        if el.name in _HEADING_TAGS:
            flush()
            level = _HEADING_TAGS[el.name]
            heading_stack = heading_stack[: level - 1]
            heading_stack.append(el.get_text(strip=True))
        elif el.name in ("p", "li", "td", "pre"):
            text = el.get_text(" ", strip=True)
            if text:
                current_text.append(text)

    flush()
    return sections


def parse_html(file_path: str) -> list[Chunk]:
    path = Path(file_path)
    html = path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "lxml")

    sections = _extract_sections(soup)
    chunks: list[Chunk] = []
    chunk_idx = 0

    for section in sections:
        text = section["text"]
        heading_path = section["heading_path"]

        if count_tokens(text) <= settings.chunk_size_tokens:
            sub_texts = [text]
        else:
            sub_texts = split_into_token_chunks(text)

        for sub_text in sub_texts:
            chunks.append(Chunk(
                text=sub_text,
                source_file=path.name,
                source_type="html",
                heading_path=heading_path,
                chunk_index=chunk_idx,
            ))
            chunk_idx += 1

    return chunks
