from pathlib import Path

import pytest

from documind.compare import compare
from documind.extract import correct, extract
from documind.pdf_ingest import read_pdf
from documind.schemas import FieldName, MatchStatus, Report


@pytest.fixture(scope="module")
def reports(pdfs: dict[str, Path]) -> dict[str, Report]:
    return {name: extract(read_pdf(path)) for name, path in pdfs.items()}


@pytest.mark.parametrize("field", [FieldName.DELIVERY, FieldName.WARRANTY, FieldName.PAYMENT])
def test_controlled_equivalence_improves_strict_equality(
    reports: dict[str, Report], field: FieldName
) -> None:
    left, right = reports["standard"], reports["equivalent"]
    baseline = {row.field: row.status for row in compare(left, right, "strict")}
    rules = {row.field: row.status for row in compare(left, right)}
    assert baseline[field] is MatchStatus.DIFFERENT
    assert rules[field] is MatchStatus.MATCHED


@pytest.mark.parametrize(
    ("name", "field", "expected", "reason"),
    [
        ("different", FieldName.AMOUNT, MatchStatus.DIFFERENT, "normalized_inequality"),
        ("different", FieldName.PAYMENT, MatchStatus.DIFFERENT, "different_controlled_clause"),
        ("foreign", FieldName.AMOUNT, MatchStatus.NEEDS_REVIEW, "cross_currency_amount"),
        ("bad_total", FieldName.AMOUNT, MatchStatus.NEEDS_REVIEW, "unresolved_input"),
        ("local_format", FieldName.AMOUNT, MatchStatus.NEEDS_REVIEW, "unresolved_input"),
        ("conflict", FieldName.AMOUNT, MatchStatus.NEEDS_REVIEW, "unresolved_input"),
        ("partial", FieldName.WARRANTY, MatchStatus.MISSING, "missing_on_one_or_both_sides"),
        (
            "conditional",
            FieldName.PAYMENT,
            MatchStatus.NEEDS_REVIEW,
            "unsupported_clause_relationship",
        ),
        ("mixed", FieldName.VENDOR, MatchStatus.NEEDS_REVIEW, "unresolved_input"),
    ],
)
def test_decisions(
    reports: dict[str, Report], name: str, field: FieldName, expected: MatchStatus, reason: str
) -> None:
    rows = {row.field: row for row in compare(reports["standard"], reports[name])}
    assert (rows[field].status, rows[field].reason) == (expected, reason)


def test_controlled_clauses_keep_timing_qualifier(reports: dict[str, Report]) -> None:
    left = reports["standard"]
    right = correct(left, FieldName.DELIVERY, "14 calendar days after order", "Exact schedule")
    rows = {row.field: row for row in compare(left, right)}
    assert rows[FieldName.DELIVERY].status is MatchStatus.DIFFERENT


def test_manual_correction_releases_resolved_field(reports: dict[str, Report]) -> None:
    left = reports["standard"]
    right = correct(reports["conflict"], FieldName.AMOUNT, "1200", "Confirmed total on page 1")
    rows = {row.field: row for row in compare(left, right)}
    assert rows[FieldName.AMOUNT].status is MatchStatus.MATCHED
    assert rows[FieldName.AMOUNT].right_status.value == "manual"
