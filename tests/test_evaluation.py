from pathlib import Path

from scripts.evaluate import evaluate, ratio, score_counts


def test_metric_zero_denominators_are_explicit() -> None:
    assert ratio(0, 0) is None
    assert score_counts(2, 1, 2) == {
        "tp": 2,
        "fp": 1,
        "fn": 2,
        "precision": 2 / 3,
        "recall": 0.5,
        "f1": 4 / 7,
    }


def test_reproducible_data_and_scores(tmp_path: Path) -> None:
    first = evaluate(tmp_path / "first")
    second = evaluate(tmp_path / "second")
    assert first.pop("latency_ms")
    assert second.pop("latency_ms")
    assert first == second
