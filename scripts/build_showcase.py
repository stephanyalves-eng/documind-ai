"""Build a static recruiter demo from the public synthetic fixtures."""

import argparse
import json
from pathlib import Path
from shutil import copyfile

from documind.compare import compare
from documind.extract import extract
from documind.pdf_ingest import read_pdf

from ._output import write_artifact
from .generate_test_docs import ROOT, generate

SOURCE = ROOT / "app" / "static_showcase"
BENCHMARK = ROOT / "docs" / "benchmark.json"
PORTFOLIO = ROOT / "docs" / "portfolio"
CASES = {
    "conditional": "Conditional payment",
    "equivalent": "Equivalent wording",
    "different": "Different terms",
    "partial": "Missing information",
    "foreign": "Different currency",
    "bad_total": "Inconsistent total",
    "conflict": "Conflicting totals",
    "freeform": "Free-form wording",
    "local_format": "Unsupported amount format",
    "mixed": "Unreadable page",
    "unlabeled": "Unlabeled values",
}
ASSETS = ("index.html", "portfolio.html", "styles.css", "app.js", "icon.png")
MEDIA = ("walkthrough.mp4", "walkthrough.en.srt", "short.mp4", "short.en.srt", "thumbnail.png")


def build(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for name in ASSETS:
        copyfile(SOURCE / name, output / name)
    media = output / "media"
    media.mkdir(exist_ok=True)
    for name in MEDIA:
        copyfile(PORTFOLIO / "media" / name, media / name)
    copyfile(PORTFOLIO / "comparison.png", media / "comparison.png")
    copyfile(BENCHMARK.with_name("benchmark-v2.json"), output / "benchmark-v2.json")
    write_artifact(output / ".nojekyll", b"")
    fixtures = generate(output / "examples")
    documents = {name: read_pdf(path) for name, path in fixtures.items()}
    reports = {name: extract(document) for name, document in documents.items()}
    baseline = reports["standard"]
    comparisons = {}
    for name in CASES:
        report = reports[name]
        rows = [item.model_dump(mode="json") for item in compare(baseline, report)]
        comparisons[name] = rows
        result = {
            "dataset": "synthetic-v1",
            "machine_evidence": "verified",
            "left": baseline.model_dump(mode="json"),
            "right": report.model_dump(mode="json"),
            "comparisons": rows,
        }
        write_artifact(
            output / "examples" / f"{name}.json", json.dumps(result, indent=2).encode("utf-8")
        )
    benchmark = json.loads(BENCHMARK.read_bytes())
    expected = {
        (case["right"], case["field"]): (case["predicted"], case["reason"])
        for case in benchmark["comparison"]["rules"]["cases"]
    }
    actual = {
        (name, row["field"]): (row["status"], row["reason"])
        for name, rows in comparisons.items()
        for row in rows
    }
    if expected != actual or set(benchmark["dataset"]["pdf_sha256"]) != set(documents):
        raise ValueError("showcase differs from the captured benchmark. Reproduce evaluation first")
    write_artifact(output / "benchmark.json", BENCHMARK.read_bytes())
    payload = {
        "cases": CASES,
        "comparisons": comparisons,
        "documents": {
            name: dict(
                fields=report.model_dump(mode="json")["observations"],
                issues=report.model_dump(mode="json")["issues"],
                pages=documents[name].pages,
            )
            for name, report in reports.items()
        },
        "benchmark": {
            "dataset": benchmark["dataset"]["version"],
            "documents": benchmark["dataset"]["documents"],
            "pairs": benchmark["dataset"]["pairs"],
            "extraction": {
                key: value
                for key, value in benchmark["extraction"].items()
                if key in ("micro", "counts")
            },
            "comparison": {
                mode: {key: value for key, value in scores.items() if key != "cases"}
                for mode, scores in benchmark["comparison"].items()
            },
        },
    }
    write_artifact(
        output / "data.js", ("window.DOCUMIND = " + json.dumps(payload) + ";\n").encode()
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the synthetic DocuMind showcase")
    parser.add_argument("--out", type=Path, default=ROOT / "outputs" / "showcase")
    build(parser.parse_args().out)


if __name__ == "__main__":
    main()
