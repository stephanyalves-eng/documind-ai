import argparse
import json
import platform
import tempfile
from collections import Counter
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Annotated

from pydantic import Field

from documind.compare import Mode, compare
from documind.evidence import verify_evidence
from documind.extract import extract
from documind.normalize import NUMERIC_FIELDS, REQUIRED
from documind.pdf_ingest import read_pdf
from documind.schemas import FieldName, FieldStatus, MatchStatus, Record, Report

from ._output import write_artifact
from .generate_test_docs import MANIFEST, ROOT, generate

GOLD = ROOT / "data" / "gold-v1.json"


class Annotation(Record):
    value: str
    source_page: Annotated[int, Field(ge=1)]
    evidence_text: str


class Pair(Record):
    left: str
    right: str
    expected: dict[FieldName, MatchStatus]


class Gold(Record):
    version: str
    documents: dict[str, dict[FieldName, Annotation]]
    pairs: list[Pair]


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def score_counts(tp: int, fp: int, fn: int) -> dict[str, int | float | None]:
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": ratio(tp, tp + fp),
        "recall": ratio(tp, tp + fn),
        "f1": ratio(2 * tp, 2 * tp + fp + fn),
    }


def score_comparisons(gold: Gold, reports: dict[str, Report], mode: Mode) -> dict[str, object]:
    confusion: Counter[tuple[str, str]] = Counter()
    details: list[dict[str, object]] = []
    divergence: Counter[str] = Counter()
    for pair in gold.pairs:
        predictions = compare(reports[pair.left], reports[pair.right], mode)
        if set(pair.expected) != {row.field for row in predictions}:
            raise ValueError("comparison gold must cover exactly the comparison fields")
        for row in predictions:
            expected = pair.expected[row.field]
            confusion[expected.value, row.status.value] += 1
            if row.status is MatchStatus.DIFFERENT:
                divergence["tp" if expected is MatchStatus.DIFFERENT else "fp"] += 1
            elif expected is MatchStatus.DIFFERENT:
                divergence["fn"] += 1
            details.append(
                dict(
                    left=pair.left,
                    right=pair.right,
                    field=row.field.value,
                    expected=expected.value,
                    predicted=row.status.value,
                    reason=row.reason,
                )
            )
    total = confusion.total()
    review = sum(count for (_, actual), count in confusion.items() if actual == "needs_review")
    agreed = sum(confusion[state.value, state.value] for state in MatchStatus)
    return {
        "status_accuracy": ratio(agreed, total),
        "status_correct": agreed,
        "status_total": total,
        "abstention_rate": ratio(review, total),
        "abstentions": review,
        "divergence": score_counts(divergence["tp"], divergence["fp"], divergence["fn"]),
        "confusion_expected_then_predicted": {
            expected.value: {
                actual.value: confusion[expected.value, actual.value] for actual in MatchStatus
            }
            for expected in MatchStatus
        },
        "cases": details,
    }


def evaluate(output_dir: Path) -> dict[str, object]:
    manifest_bytes = MANIFEST.read_bytes()
    gold_bytes = GOLD.read_bytes()
    gold = Gold.model_validate_json(gold_bytes)
    paths = generate(output_dir)
    if set(paths) != set(gold.documents) or gold.version != json.loads(manifest_bytes)["version"]:
        raise ValueError("fixture manifest and gold must describe the same dataset")

    counts: Counter[str] = Counter()
    fields: dict[FieldName, Counter[str]] = {field: Counter() for field in FieldName}
    details: list[dict[str, object]] = []
    reports = {}
    timings = []
    for name, path in paths.items():
        started = perf_counter()
        document = read_pdf(path)
        report = extract(document)
        timings.append((perf_counter() - started) * 1000)
        reports[name] = report
        references = gold.documents[name]
        for field, annotation in references.items():
            page = annotation.source_page
            if page > len(document.pages) or annotation.evidence_text not in (
                document.pages[page - 1].split("\n")
            ):
                raise ValueError(f"unverifiable gold annotation for {name}/{field}")

        for field, observation in report.observations.items():
            reference = references.get(field)
            actual = observation.value
            expected = reference.value if reference else None
            exact = expected is not None and actual == expected
            if exact:
                fields[field]["tp"] += 1
            else:
                fields[field]["fp"] += int(actual is not None)
                fields[field]["fn"] += int(expected is not None)
            if field in NUMERIC_FIELDS and reference:
                counts["numeric_gold"] += 1
                counts["numeric_correct"] += int(exact)
            if field in REQUIRED:
                counts["required_slots"] += 1
                counts["required_abstained"] += int(actual is None)
                counts["required_needs_review"] += int(
                    observation.confidence_or_status is FieldStatus.NEEDS_REVIEW
                )
            all_verified = all(verify_evidence(document, item) for item in observation.evidence)
            if actual is not None:
                cites_gold = reference is not None and any(
                    item.source_page == reference.source_page
                    and item.evidence_text == reference.evidence_text
                    for item in observation.evidence
                )
                counts["citations_predicted"] += 1
                counts["citations_correct"] += int(exact and cites_gold and all_verified)
            details.append(
                dict(
                    document=name,
                    field=field.value,
                    expected=expected,
                    actual=actual,
                    status=observation.confidence_or_status.value,
                    evidence_verified=bool(observation.evidence) and all_verified,
                    reason=observation.reason,
                )
            )

    totals: Counter[str] = Counter()
    for field_counts in fields.values():
        totals.update(field_counts)
    return {
        "dataset": {
            "version": gold.version,
            "documents": len(paths),
            "pairs": len(gold.pairs),
            "manifest_sha256": sha256(manifest_bytes).hexdigest(),
            "gold_sha256": sha256(gold_bytes).hexdigest(),
            "pdf_sha256": {name: report.document_sha256 for name, report in reports.items()},
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "pymupdf": version("PyMuPDF"),
            "pydantic": version("pydantic"),
            "reportlab": version("reportlab"),
        },
        "extraction": {
            "micro": score_counts(totals["tp"], totals["fp"], totals["fn"]),
            "per_field": {
                field.value: score_counts(items["tp"], items["fp"], items["fn"])
                for field, items in fields.items()
            },
            "numeric_exact_match": ratio(counts["numeric_correct"], counts["numeric_gold"]),
            "citation_accuracy": ratio(counts["citations_correct"], counts["citations_predicted"]),
            "required_abstention_rate": ratio(
                counts["required_abstained"], counts["required_slots"]
            ),
            "counts": dict(counts),
            "cases": details,
        },
        "comparison": {
            "strict": score_comparisons(gold, reports, "strict"),
            "rules": score_comparisons(gold, reports, "rules"),
        },
        "latency_ms": {
            "operation": "sequential PDF read and extraction including parser worker startup",
            "samples": [round(value, 3) for value in timings],
            "median": round(median(timings), 3),
            "min": round(min(timings), 3),
            "max": round(max(timings), 3),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate DocuMind on annotated synthetic PDFs")
    parser.add_argument("--output", type=Path, help="write JSON instead of printing it")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="documind-synthetic-") as scratch:
        result = evaluate(Path(scratch))
    payload = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        write_artifact(args.output, payload.encode("utf-8"))
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
