"""
Pure unit tests for RRF — no Qdrant, no embeddings, no network. This is
exactly the kind of test that should run in a CI pipeline on every commit,
fast and with zero external dependencies.
"""

from app.retrieval.fusion import reciprocal_rank_fusion


def test_agreement_beats_single_top_rank():
    """A doc ranked #2 and #1 across two lists should beat a doc ranked
    #1 in only one list and absent from the other — this is RRF's core
    property and the main thing worth being able to demonstrate."""
    dense = ["chunk_A", "chunk_B", "chunk_C", "chunk_D"]
    sparse = ["chunk_C", "chunk_A", "chunk_E"]

    result = reciprocal_rank_fusion([dense, sparse], k=60)
    ranking = [doc_id for doc_id, _ in result]

    assert ranking[0] == "chunk_A", f"expected chunk_A first, got {ranking}"
    assert ranking[1] == "chunk_C", f"expected chunk_C second, got {ranking}"


def test_doc_in_only_one_list_still_included():
    """A doc that only one method found should still show up, just lower."""
    dense = ["chunk_A"]
    sparse = ["chunk_A", "chunk_only_in_sparse"]

    result = reciprocal_rank_fusion([dense, sparse], k=60)
    ids = {doc_id for doc_id, _ in result}

    assert "chunk_only_in_sparse" in ids


def test_empty_lists_return_empty():
    assert reciprocal_rank_fusion([[], []], k=60) == []


def test_single_list_preserves_order():
    """Fusing just one list should preserve that list's original order."""
    single = ["chunk_A", "chunk_B", "chunk_C"]
    result = reciprocal_rank_fusion([single], k=60)
    ranking = [doc_id for doc_id, _ in result]
    assert ranking == single


def test_three_way_fusion():
    """Generalization beyond 2 lists (dense + sparse + e.g. a rerank pass)."""
    list_a = ["X", "Y"]
    list_b = ["Y", "X"]
    list_c = ["Y", "X"]
    result = reciprocal_rank_fusion([list_a, list_b, list_c], k=60)
    # Y appears at rank 1 twice and rank 2 once; X the reverse -> Y should win.
    assert result[0][0] == "Y"


if __name__ == "__main__":
    tests = [
        test_agreement_beats_single_top_rank,
        test_doc_in_only_one_list_still_included,
        test_empty_lists_return_empty,
        test_single_list_preserves_order,
        test_three_way_fusion,
    ]
    for t in tests:
        t()
        print(f"  ✓ {t.__name__}")
    print(f"\nAll {len(tests)} tests passed.")
