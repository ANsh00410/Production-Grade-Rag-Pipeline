"""
Offline unit tests for verify_claims() and summarize_results().

No Groq API calls, no Qdrant connection needed.

Import isolation strategy
--------------------------
verify.py imports SearchResult from app.retrieval.search, which in turn
imports qdrant_client and the embedder at module level. Those would fail if
Qdrant / the model files are not available. We pre-stub the entire
app.retrieval.search module in sys.modules before any app code is imported,
so the heavy dependencies are never touched.

judge_claim() is patched per-test with unittest.mock so the judge logic
stays deterministic and offline too.
"""

import sys
import types
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Pre-stub app.retrieval.search BEFORE any app imports touch it.
# verify.py only uses SearchResult from it, so a minimal dataclass is enough.
# ---------------------------------------------------------------------------
from dataclasses import dataclass

@dataclass
class _FakeSearchResult:
    chunk_id: str = "fake"
    point_id: str = "fake"
    score: float = 1.0
    payload: dict = None
    def __post_init__(self):
        if self.payload is None:
            self.payload = {}

_fake_search_module = types.ModuleType("app.retrieval.search")
_fake_search_module.SearchResult = _FakeSearchResult
sys.modules.setdefault("app.retrieval.search", _fake_search_module)

# Now it's safe to import app code
from app.generation.verify import ClaimResult, verify_claims, summarize_results  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _chunk(text: str) -> _FakeSearchResult:
    """Minimal chunk: verify_claims() only reads payload['text']."""
    return _FakeSearchResult(payload={"text": text})


# ---------------------------------------------------------------------------
# verify_claims()
# ---------------------------------------------------------------------------

def test_uncited_claim_gets_uncited_verdict():
    """A sentence with no citation brackets → UNCITED, judge is never called."""
    answer = "The sky is green."
    chunks = [_chunk("The sky is blue.")]

    with patch("app.generation.verify.judge_claim") as mock_judge:
        results = verify_claims(answer, chunks)
        mock_judge.assert_not_called()

    assert len(results) == 1
    assert results[0].verdict == "UNCITED"
    assert results[0].citations == []


def test_cited_claim_calls_judge_and_maps_verdict():
    """A claim with [1] calls judge_claim and maps its verdict/reason correctly."""
    answer = "Water boils at 100 °C [1]."
    chunks = [_chunk("Water boils at 100 degrees Celsius at sea level.")]
    fake_response = "VERDICT: SUPPORTED\nREASON: Chunk directly confirms this."

    with patch("app.generation.verify.judge_claim", return_value=fake_response):
        results = verify_claims(answer, chunks)

    assert len(results) == 1
    r = results[0]
    assert r.verdict == "SUPPORTED"
    assert r.reason == "Chunk directly confirms this."
    assert r.citations == [1]


def test_out_of_range_citation_treated_as_uncited():
    """Citation number larger than chunk count is silently dropped → UNCITED."""
    answer = "Some claim [9]."   # only 1 chunk provided
    chunks = [_chunk("Unrelated text.")]

    with patch("app.generation.verify.judge_claim") as mock_judge:
        results = verify_claims(answer, chunks)
        mock_judge.assert_not_called()

    assert results[0].verdict == "UNCITED"


def test_mixed_claims_one_cited_one_uncited():
    """Two sentences: one cited (SUPPORTED), one uncited → one of each verdict."""
    answer = "Claim A is true [1]. Claim B has no source."
    chunks = [_chunk("Evidence for claim A.")]
    fake_response = "VERDICT: SUPPORTED\nREASON: Evidence matches."

    with patch("app.generation.verify.judge_claim", return_value=fake_response):
        results = verify_claims(answer, chunks)

    assert len(results) == 2
    assert sum(1 for r in results if r.verdict == "SUPPORTED") == 1
    assert sum(1 for r in results if r.verdict == "UNCITED") == 1


def test_partial_verdict_is_preserved():
    """PARTIAL verdict from the judge is mapped through unchanged."""
    answer = "Claim X [1]."
    chunks = [_chunk("Partial evidence for X.")]
    fake_response = "VERDICT: PARTIAL\nREASON: Only half is confirmed."

    with patch("app.generation.verify.judge_claim", return_value=fake_response):
        results = verify_claims(answer, chunks)

    assert results[0].verdict == "PARTIAL"
    assert results[0].reason == "Only half is confirmed."


# ---------------------------------------------------------------------------
# summarize_results()
# ---------------------------------------------------------------------------

def _claim(verdict: str) -> ClaimResult:
    return ClaimResult(claim="x", citations=[], verdict=verdict, reason="r")


def test_all_supported_gives_pass():
    claims = [_claim("SUPPORTED"), _claim("SUPPORTED")]
    report = summarize_results(claims)

    assert report.overall == "PASS"
    assert report.total == 2
    assert report.count == {"SUPPORTED": 2}
    assert report.flagged == []


def test_any_non_supported_gives_review():
    claims = [_claim("SUPPORTED"), _claim("PARTIAL"), _claim("UNCITED")]
    report = summarize_results(claims)

    assert report.overall == "REVIEW"
    assert report.total == 3
    assert report.count["SUPPORTED"] == 1
    assert report.count["PARTIAL"] == 1
    assert report.count["UNCITED"] == 1
    assert len(report.flagged) == 2   # PARTIAL + UNCITED


def test_empty_claims_gives_review():
    """Edge case: zero claims → REVIEW (nothing passed verification)."""
    report = summarize_results([])
    assert report.overall == "REVIEW"
    assert report.total == 0
    assert report.flagged == []


def test_flagged_contains_only_non_supported():
    claims = [_claim("SUPPORTED"), _claim("NOT_SUPPORTED"), _claim("SUPPORTED")]
    report = summarize_results(claims)

    assert len(report.flagged) == 1
    assert report.flagged[0].verdict == "NOT_SUPPORTED"


def test_count_dict_tracks_all_verdicts():
    claims = [
        _claim("SUPPORTED"), _claim("SUPPORTED"),
        _claim("PARTIAL"),
        _claim("NOT_SUPPORTED"),
        _claim("UNKNOWN"),
    ]
    report = summarize_results(claims)
    assert report.count == {
        "SUPPORTED": 2,
        "PARTIAL": 1,
        "NOT_SUPPORTED": 1,
        "UNKNOWN": 1,
    }
    assert report.overall == "REVIEW"


# ---------------------------------------------------------------------------
# Runner (matches the pattern in test_judge_offline.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_uncited_claim_gets_uncited_verdict,
        test_cited_claim_calls_judge_and_maps_verdict,
        test_out_of_range_citation_treated_as_uncited,
        test_mixed_claims_one_cited_one_uncited,
        test_partial_verdict_is_preserved,
        test_all_supported_gives_pass,
        test_any_non_supported_gives_review,
        test_empty_claims_gives_review,
        test_flagged_contains_only_non_supported,
        test_count_dict_tracks_all_verdicts,
    ]
    for t in tests:
        t()
        print(f"  ✓ {t.__name__}")
    print(f"\nAll {len(tests)} tests passed.")
