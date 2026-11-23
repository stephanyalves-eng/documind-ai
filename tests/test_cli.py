import csv
import json
import subprocess
import sys
from io import StringIO
from pathlib import Path

from documind.schemas import Report


def run(*args: str | Path) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "-m", "documind", *map(str, args)],
        capture_output=True,
        check=False,
    )


def test_full_review_and_export_flow(tmp_path: Path, pdfs: dict[str, Path]) -> None:
    old = tmp_path / "extracted.json"
    extracted = run("extract", pdfs["partial"])
    assert extracted.returncode == 0 and not extracted.stderr
    old.write_bytes(extracted.stdout)
    reason = "Confirmed warranty with reviewer"
    correction = run("correct", old, "warranty", "12 months after delivery", "--reason", reason)
    assert correction.returncode == 0
    assert old.read_bytes() == extracted.stdout
    reviewed = tmp_path / "reviewed.json"
    reviewed.write_bytes(correction.stdout)
    parsed = Report.model_validate_json(correction.stdout)
    assert parsed.corrections[0].reason == reason
    comparison = run("compare", old, reviewed, "--reports")
    assert comparison.returncode == 0
    warranty = next(
        row for row in json.loads(comparison.stdout)["comparisons"] if row["field"] == "warranty"
    )
    assert warranty["right_status"] == "manual"
    assert warranty["status"] == "missing"
    csv_output = run("export", reviewed)
    assert csv_output.returncode == 0
    rows = list(csv.DictReader(StringIO(csv_output.stdout.decode("utf-8"))))
    warranty_csv = next(row for row in rows if row["field"] == "warranty")
    assert warranty_csv["effective_status"] == "manual"
    assert warranty_csv["correction_reason"] == reason
    assert warranty_csv["machine_source_page"] == ""
    verification = run("verify", reviewed, pdfs["partial"])
    assert verification.returncode == 0
    assert json.loads(verification.stdout) == {"machine_observations_verified": True}
    assert run("verify", reviewed, pdfs["standard"]).returncode == 2


def test_csv_neutralizes_formula_like_text_without_altering_json(
    tmp_path: Path, pdfs: dict[str, Path]
) -> None:
    extracted = run("extract", pdfs["standard"])
    report = tmp_path / "report.json"
    report.write_bytes(extracted.stdout)
    result = run("correct", report, "vendor", "=2+3", "--reason", "synthetic formula")
    assert result.returncode == 0
    assert json.loads(result.stdout)["corrections"][0]["value"] == "=2+3"
    report.write_bytes(result.stdout)
    exported = run("export", report)
    rows = list(csv.DictReader(StringIO(exported.stdout.decode("utf-8"))))
    assert rows[0]["effective_value"] == "'=2+3"
    assert rows[0]["machine_evidence_text"] == "Vendor: Meridian Test Supply"


def test_error_excludes_input_path_and_content(tmp_path: Path) -> None:
    path = tmp_path / "local-sensitive-filename.pdf"
    path.write_text("private sample", encoding="utf-8")
    result = run("extract", path)
    assert result.returncode == 2 and not result.stdout
    assert b"PDF header" in result.stderr
    assert b"private sample" not in result.stderr
    assert b"local-sensitive" not in result.stderr


def test_verify_detects_a_changed_observation(tmp_path: Path, pdfs: dict[str, Path]) -> None:
    extracted = run("extract", pdfs["standard"])
    forged = json.loads(extracted.stdout)
    forged["observations"]["vendor"]["evidence"][0]["source_page"] = 2
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(forged), encoding="utf-8")
    assert run("verify", report_path, pdfs["standard"]).returncode == 2
