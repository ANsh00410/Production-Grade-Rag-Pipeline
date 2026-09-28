"""
Splits a block of text into overlapping, token-sized chunks.

Design choice: token-based sizing, not character-based.
LLMs and embedding models operate on tokens, not characters — a 500-character
chunk could be 80 tokens (mostly short words) or 200 tokens (dense technical
text). Sizing by tokens keeps chunks consistently sized *for the model*,
which is what actually matters for retrieval quality and context budgets.

Design choice: overlap.
Without overlap, a sentence or idea that straddles a chunk boundary gets torn
in half, and neither resulting chunk fully represents it. ~15% overlap is a
reasonable default — costs a little extra storage, buys back a meaningful
amount of retrieval recall at boundaries.
"""

from app.config import settings

# cl100k_base is the tokenizer used by GPT-4/Claude-adjacent tokenization schemes.
# It's not a perfect match for every embedding model's own tokenizer, but it's
# a consistent, fast proxy for "how big is this chunk roughly going to be."
#
# tiktoken downloads its vocab file from OpenAI's servers on first use. In a
# locked-down network (corporate proxy, air-gapped sandbox, this environment)
# that download can fail. Rather than let the whole ingestion pipeline crash
# on a network blip, we fall back to a lightweight approximate tokenizer.
# This is a real production concern worth knowing, not just a workaround:
# any pipeline with a "phones home on first import" dependency needs a
# fallback path, or it becomes a single point of failure at deploy time.
try:
    import tiktoken
    _ENCODING = tiktoken.get_encoding("cl100k_base")
    _USING_TIKTOKEN = True
except Exception:
    _ENCODING = None
    _USING_TIKTOKEN = False


def count_tokens(text: str) -> int:
    if _USING_TIKTOKEN:
        return len(_ENCODING.encode(text))
    # Approximation: English averages ~1.3 tokens per word. Not exact, but
    # good enough to size chunks consistently when the real tokenizer is
    # unavailable.
    return int(len(text.split()) * 1.3)


def split_into_token_chunks(
    text: str,
    chunk_size: int = settings.chunk_size_tokens,
    overlap: int = settings.chunk_overlap_tokens,
) -> list[str]:
    """
    Splits `text` into overlapping chunks of ~chunk_size tokens.
    Returns a list of text strings (metadata is attached by the caller).
    """
    if not text.strip():
        return []

    if _USING_TIKTOKEN:
        tokens = _ENCODING.encode(text)
        if len(tokens) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(tokens):
            end = min(start + chunk_size, len(tokens))
            chunks.append(_ENCODING.decode(tokens[start:end]))
            if end == len(tokens):
                break
            # Move forward by (chunk_size - overlap), so the next chunk
            # re-includes the last `overlap` tokens of this one.
            start += chunk_size - overlap
        return chunks

    # --- Fallback: word-based splitting with the same sliding-window logic ---
    words = text.split()
    approx_word_chunk = int(chunk_size / 1.3)
    approx_word_overlap = int(overlap / 1.3)

    if len(words) <= approx_word_chunk:
        return [text]

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + approx_word_chunk, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += approx_word_chunk - approx_word_overlap
    return chunks
