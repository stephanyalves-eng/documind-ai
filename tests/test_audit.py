import json
import subprocess
import sys
from decimal import localcontext
from pathlib import Path
from typing import NoReturn

import pymupdf
import pytest

from documind import _pdf_worker
from documind._pdf_worker import parse
from documind.compare import compare
from documind.extract import extract
from documind.local_io import LocalPathError, read_local_bytes
from documind.pdf_ingest import DEFAULT_LIMITS, PDFError, PDFProblem, PDFText, read_pdf
from documind.schemas import FieldName, FieldStatus, MatchStatus
from scripts import generate_test_docs
from scripts._output import write_artifact


def _cli(*args: str | Path, body: bytes = b"") -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "-m", "documind", *map(str, args)],
        input=body,
        capture_output=True,
        check=False,
    )


def test_parser_timeout_uses_safe_diagnostic(
    pdfs: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    def timeout(*args: object, **kwargs: object) -> NoReturn:
        raise subprocess.TimeoutExpired("synthetic private path", 15)

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(PDFError, match="time limit") as caught:
        read_pdf(pdfs["standard"])
    assert "private path" not in str(caught.value)


def test_nonzero_worker_exit_excludes_native_output(
    pdfs: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    def failed(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess([], 1, b"", b"synthetic private parser diagnostic")

    monkeypatch.setattr(subprocess, "run", failed)
    with pytest.raises(PDFError, match="failed or exceeded") as caught:
        read_pdf(pdfs["standard"])
    assert "private parser diagnostic" not in str(caught.value)


def test_worker_rejects_outdated_parser_dependency(
    pdfs: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_pdf_worker, "version", lambda _: "1.28.2")
    assert parse(pdfs["standard"].read_bytes(), DEFAULT_LIMITS) is PDFProblem.DEPENDENCY


@pytest.mark.parametrize("span", [{"type": 3, "opacity": 1}, {"type": 0, "opacity": 0}])
def test_worker_abstains_when_page_lacks_visible_text(
    pdfs: dict[str, Path], monkeypatch: pytest.MonkeyPatch, span: dict[str, int]
) -> None:
    get_trace = pymupdf.Page.get_texttrace

    def trace(page: pymupdf.Page) -> list[dict[str, object]]:
        return [span] if page.number == 1 else get_trace(page)

    monkeypatch.setattr(pymupdf.Page, "get_texttrace", trace)
    parsed = parse(pdfs["standard"].read_bytes(), DEFAULT_LIMITS)
    assert isinstance(parsed, dict)
    assert parsed["unreadable_pages"] == [2]
    assert parsed["pages"][1] == ""


def test_no_field_boundary_in_unicode_line_separator() -> None:
    document = PDFText("1" * 64, ("A prose sentence\u2028Vendor: Test supplier",), ())
    observation = extract(document).observations[FieldName.VENDOR]
    assert observation.confidence_or_status is FieldStatus.MISSING


def test_invalid_optional_tax_blocks_total_comparison_without_subtotal() -> None:
    valid = extract(PDFText("1" * 64, ("Currency: USD\nTotal: 100",), ()))
    partial = extract(PDFText("2" * 64, ("Currency: USD\nTotal: 100\nTax: pending",), ()))
    assert any(issue.code == "arithmetic_unresolved" for issue in partial.issues)
    total = next(row for row in compare(valid, partial) if row.field is FieldName.AMOUNT)
    assert total.status is MatchStatus.NEEDS_REVIEW


def test_amount_validation_is_independent_of_decimal_context() -> None:
    document = PDFText(
        "1" * 64, ("Currency: USD\nTotal: 1234.56\nSubtotal: 1234.50\nTax: 0.06",), ()
    )
    with localcontext() as ctx:
        ctx.prec = 2
        result = extract(document)
    assert not any(issue.code == "inconsistent_total" for issue in result.issues)


def test_compare_identifies_when_machine_evidence_was_checked(
    pdfs: dict[str, Path], tmp_path: Path
) -> None:
    source = pdfs["standard"]
    report = tmp_path / "report.json"
    report.write_bytes(_cli("extract", source).stdout)
    result = _cli("compare", report, report, "--reports")
    assert result.returncode == 0
    assert json.loads(result.stdout)["machine_evidence"] == "unverified"
    checked = _cli("compare", report, report, "--reports", "--source-pdfs", source, source)
    assert checked.returncode == 0
    assert json.loads(checked.stdout)["machine_evidence"] == "verified"
    mismatch = _cli(
        "compare", report, report, "--reports", "--source-pdfs", source, pdfs["equivalent"]
    )
    assert mismatch.returncode == 2 and not mismatch.stdout
    assert b"does not match PDF machine evidence" in mismatch.stderr
    csv_result = _cli("compare", source, source, "--format", "csv")
    assert csv_result.returncode == 0
    assert b"machine_evidence" in csv_result.stdout
    assert b",verified" in csv_result.stdout


def test_private_correction_can_be_supplied_over_stdin(
    pdfs: dict[str, Path], tmp_path: Path
) -> None:
    report = tmp_path / "report.json"
    report.write_bytes(_cli("extract", pdfs["standard"]).stdout)
    update = {"value": "1250", "reason": "Confirmed revised amount"}
    result = _cli("correct", report, "amount", "--stdin", body=json.dumps(update).encode())
    assert result.returncode == 0 and not result.stderr
    assert json.loads(result.stdout)["corrections"][0]["value"] == "1250.00"
    bad = _cli("correct", report, "amount", "--stdin", body=b"private sample")
    assert bad.returncode == 2 and b"private sample" not in bad.stderr
    large = _cli("correct", report, "amount", "--stdin", body=b" " * 16_385)
    assert large.returncode == 2 and not large.stdout


def test_invalid_cli_arguments_do_not_echo_values() -> None:
    result = _cli("correct", "local-private.json", "private-input")
    assert result.returncode == 2
    assert b"local-private" not in result.stderr
    assert b"private-input" not in result.stderr


@pytest.mark.skipif(sys.platform != "win32", reason="Windows path namespace")
def test_windows_unc_is_rejected_before_probing_path(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_probe(path: Path) -> NoReturn:
        raise AssertionError("a UNC path should not reach the filesystem")

    monkeypatch.setattr(Path, "is_file", no_probe)
    with pytest.raises(LocalPathError, match="UNC"):
        read_local_bytes(Path(r"\\documind.invalid\example\synthetic.pdf"), 100)


def test_invalid_fixture_names_fail_before_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = tmp_path / "fixtures.json"
    manifest.write_text(json.dumps({"documents": {"valid": [[]], "invalid name": [[]]}}))
    monkeypatch.setattr(generate_test_docs, "MANIFEST", manifest)
    out = tmp_path / "generated"
    with pytest.raises(ValueError, match="fixture name"):
        generate_test_docs.generate(out)
    assert not out.exists()


def test_failed_output_replacement_leaves_existing_file_and_cleans_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "existing.json"
    target.write_bytes(b"synthetic original")

    def fail(*args: object) -> NoReturn:
        raise OSError("simulated interruption")

    monkeypatch.setattr(Path, "replace", fail)
    with pytest.raises(OSError, match="simulated interruption"):
        write_artifact(target, b"synthetic replacement")
    assert target.read_bytes() == b"synthetic original"
    assert list(tmp_path.iterdir()) == [target]
