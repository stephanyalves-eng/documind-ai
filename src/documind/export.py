import csv
from collections.abc import Iterable, Iterator
from io import StringIO

from .schemas import Comparison, Report


def _csv_cell(value: object) -> object:
    if isinstance(value, str) and (
        value.startswith(("\t", "\r", "\n"))
        or value.lstrip().startswith(("=", "+", "-", "@", "＝", "＋", "－", "＠"))
    ):
        return "'" + value
    return value


def _csv(header: tuple[str, ...], rows: Iterable[tuple[object, ...]]) -> str:
    buffer = StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(tuple(map(_csv_cell, row)) for row in rows)
    return buffer.getvalue()


def report_csv(report: Report) -> str:
    def rows() -> Iterator[tuple[object, ...]]:
        for field, observation in report.observations.items():
            effective, status = report.effective_value(field)
            correction = next(
                (entry for entry in reversed(report.corrections) if entry.field is field), None
            )
            issue_codes = ", ".join(issue.code for issue in report.issues if field in issue.fields)
            for evidence in observation.evidence or (None,):
                yield (
                    report.document_sha256,
                    field,
                    effective,
                    status,
                    observation.value,
                    observation.confidence_or_status,
                    observation.reason,
                    evidence.source_page if evidence else None,
                    evidence.evidence_text if evidence else None,
                    evidence.extraction_method if evidence else None,
                    correction.extraction_method if correction else None,
                    correction.reason if correction else None,
                    issue_codes,
                )

    return _csv(
        (
            "document_sha256",
            "field",
            "effective_value",
            "effective_status",
            "observed_value",
            "observation_status",
            "observation_reason",
            "machine_source_page",
            "machine_evidence_text",
            "machine_evidence_method",
            "correction_method",
            "correction_reason",
            "issues",
        ),
        rows(),
    )


def comparison_csv(comparisons: Iterable[Comparison], machine_evidence: str = "unverified") -> str:
    return _csv(
        (
            "field",
            "left_value",
            "right_value",
            "left_status",
            "right_status",
            "status",
            "reason",
            "machine_evidence",
        ),
        (
            (
                item.field,
                item.left_value,
                item.right_value,
                item.left_status,
                item.right_status,
                item.status,
                item.reason,
                machine_evidence,
            )
            for item in comparisons
        ),
    )
