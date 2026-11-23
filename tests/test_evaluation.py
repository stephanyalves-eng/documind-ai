import json
from pathlib import Path

import pytest

from documind.schemas import Evidence
from scripts.evaluate import Annotation, evaluate, ratio, score_counts
from scripts.generate_test_docs import ROOT


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


@pytest.mark.parametrize("dataset", ["v1", "v2"])
def test_reproducible_data_and_scores(tmp_path: Path, dataset: str) -> None:
    first = evaluate(tmp_path / "first", dataset)
    second = evaluate(tmp_path / "second", dataset)
    assert first.pop("latency_ms")
    assert second.pop("latency_ms")
    assert first == second
    filename = "benchmark.json" if dataset == "v1" else "benchmark-v2.json"
    published = json.loads((ROOT / "docs" / filename).read_bytes())
    for key in ("dataset", "extraction", "comparison"):
        assert first[key] == published[key]


def test_citation_needs_every_annotated_line_on_its_physical_page() -> None:
    annotation = Annotation(
        value="due 30 days after invoice Only after written acceptance.",
        source_page=2,
        evidence_text="Payment terms: due 30 days after invoice\nOnly after written acceptance.",
    )
    first = Evidence(source_page=2, evidence_text="Payment terms: due 30 days after invoice")
    wrong_page = Evidence(source_page=1, evidence_text="Only after written acceptance.")
    continuation = Evidence(source_page=2, evidence_text="Only after written acceptance.")
    assert not annotation.supported_by((first,))
    assert not annotation.supported_by((first, wrong_page))
    assert annotation.supported_by((first, continuation))
