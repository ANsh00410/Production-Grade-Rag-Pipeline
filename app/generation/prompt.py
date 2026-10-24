"""
Prompt construction for grounded generation.

Two things happen here that matter more than they look like they should:

1. Chunks are numbered [1], [2], [3]... in the prompt. This gives the LLM
   a simple, unambiguous token to cite ("[2]") instead of having to quote
   the source or invent its own reference scheme — a fixed, small set of
   valid citation markers is much easier to validate and parse afterward
   than free-form attribution.

2. The system prompt explicitly permits "I don't know." Without this,
   a model under instruction to "answer the question" will often produce
   a plausible-sounding response even when the retrieved context doesn't
   actually contain the answer — which is exactly the hallucination this
   whole pipeline exists to prevent. Explicitly authorizing "insufficient
   context" as a valid answer removes the pressure to fabricate one.
"""

from app.retrieval.search import SearchResult


SYSTEM_PROMPT = """You are a documentation assistant. Answer the user's question using ONLY the numbered context chunks provided below. 

Rules:
- Every factual claim in your answer MUST be followed by a citation marker using ASCII square brackets, exactly like this: [1] or [2] — referencing the chunk number it came from. Do not use any other bracket style.
- Example of correct citation format: "Deploys require manual approval [1]."
- If a claim draws on multiple chunks, cite all of them, e.g. [1][3].
- If the provided context does not contain enough information to answer the question, say so explicitly — do NOT use outside knowledge, and do NOT guess.
- Do not fabricate citations. Only cite chunk numbers that actually appear in the context below.
- Always write in plain prose sentences. Never use bullet points, numbered lists, or markdown formatting — only flowing sentences separated by periods.
"""


def build_context_block(chunks: list[SearchResult]) -> str:
    """Formats retrieved chunks into a numbered block the LLM can cite by number."""
    lines = []
    for i, chunk in enumerate(chunks, start=1):
        heading = chunk.payload.get("heading_path", "")
        source = chunk.payload.get("source_file", "")
        location = f"{source} > {heading}" if heading else source
        lines.append(f"[{i}] (from {location})\n{chunk.payload['text']}\n")
    return "\n".join(lines)


def build_user_message(query: str, chunks: list[SearchResult]) -> str:
    context_block = build_context_block(chunks)
    return f"""Context:
{context_block}

Question: {query}

Answer using only the context above, with inline [n] citations."""