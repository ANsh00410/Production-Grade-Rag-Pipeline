"""
Pure unit tests, no network needed — same philosophy as test_fusion.py.
"""

from app.generation.citations import extract_citations, split_into_claims


def test_extract_citations_basic():
    text = "See chunk [2] and also chunk [10], then [2] again, and [1]."
    assert extract_citations(text, num_chunks=15) == [1, 2, 10]


def test_extract_citations_rejects_out_of_range():
    text = "Cites [1] and a hallucinated [99]."
    assert extract_citations(text, num_chunks=5) == [1]


def test_extract_citations_rejects_zero():
    text = "Invalid citation [0] and valid [3]."
    assert extract_citations(text, num_chunks=5) == [3]


def test_extract_citations_fullwidth_brackets():
    """Regression test for a real bug: Groq's gpt-oss-20b was observed
    drifting to full-width brackets despite explicit prompt instructions
    to use ASCII [1]."""
    text = "Deploys need approval【1】."
    assert extract_citations(text, num_chunks=5) == [1]


def test_split_into_claims_basic():
    text = "Deploys need approval [1]. Staging auto-deploys within 5 minutes [2][3]. This has no citation."
    result = split_into_claims(text, num_chunks=5)
    assert result == [
        ("Deploys need approval.", [1]),
        ("Staging auto-deploys within 5 minutes.", [2, 3]),
        ("This has no citation.", []),
    ]


def test_split_into_claims_fullwidth_brackets():
    text = "Deploys need approval【1】. This has no citation."
    result = split_into_claims(text, num_chunks=5)
    claim_texts = [c for c, _ in result]
    citation_lists = [cites for _, cites in result]
    assert "【" not in claim_texts[0] and "】" not in claim_texts[0]
    assert citation_lists[0] == [1]


if __name__ == "__main__":
    tests = [
        test_extract_citations_basic,
        test_extract_citations_rejects_out_of_range,
        test_extract_citations_rejects_zero,
        test_extract_citations_fullwidth_brackets,
        test_split_into_claims_basic,
        test_split_into_claims_fullwidth_brackets,
    ]
    for t in tests:
        t()
        print(f"  ✓ {t.__name__}")
    print(f"\nAll {len(tests)} tests passed.")