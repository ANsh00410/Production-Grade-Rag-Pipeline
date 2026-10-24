"""
Pure unit tests for parse_verdict() — no Groq API call needed, since
parsing is entirely separate from the network call that produces the
text being parsed.
"""

from app.generation.judge import parse_verdict


def test_valid_supported_verdict():
    text = "VERDICT: SUPPORTED\nREASON: The chunk explicitly confirms this."
    verdict, reason = parse_verdict(text)
    assert verdict == "SUPPORTED"
    assert reason == "The chunk explicitly confirms this."  # casing preserved


def test_invalid_verdict_word_becomes_unknown():
    text = "VERDICT: MAYBE\nREASON: Not totally sure."
    verdict, reason = parse_verdict(text)
    assert verdict == "UNKNOWN"
    assert reason == "Not totally sure."


def test_totally_malformed_response_preserves_raw_text():
    text = "I think this claim is probably true based on the chunk."
    verdict, reason = parse_verdict(text)
    assert verdict == "UNKNOWN"
    assert reason == text  # nothing lost, full text preserved for debugging


def test_partial_verdict():
    text = "VERDICT: PARTIAL\nREASON: Only the first half is supported."
    verdict, reason = parse_verdict(text)
    assert verdict == "PARTIAL"


if __name__ == "__main__":
    tests = [
        test_valid_supported_verdict,
        test_invalid_verdict_word_becomes_unknown,
        test_totally_malformed_response_preserves_raw_text,
        test_partial_verdict,
    ]
    for t in tests:
        t()
        print(f"  ✓ {t.__name__}")
    print(f"\nAll {len(tests)} tests passed.")