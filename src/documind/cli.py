import argparse
import json
import sys
from pathlib import Path
from typing import NoReturn

from pydantic import ValidationError

from .compare import compare
from .export import comparison_csv, report_csv
from .extract import correct, extract, validate
from .local_io import read_local_bytes
from .normalize import normalize
from .pdf_ingest import PDFError, read_pdf
from .schemas import FieldName, Report

MAX_REPORT_BYTES = 16 * 1024 * 1024
MAX_CORRECTION_BYTES = 16_384


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        super().error("invalid arguments. Run with --help for usage.")


def _load_report(path: Path) -> Report:
    data = read_local_bytes(path, MAX_REPORT_BYTES)
    if len(data) > MAX_REPORT_BYTES:
        raise ValueError("report exceeds the byte limit")
    report = Report.model_validate_json(data)
    for field, observation in report.observations.items():
        if observation.value is not None and observation.value != normalize(
            field, observation.value
        ):
            raise ValueError("report contains a noncanonical observation")
    for entry in report.corrections:
        if entry.value != normalize(entry.field, entry.value):
            raise ValueError("report contains a noncanonical correction")
    return report.model_copy(update={"issues": validate(report)})


def _verify_report(report: Report, path: Path) -> Report:
    original = extract(read_pdf(path))
    excluded = {"corrections", "issues", "schema_version"}
    if report.model_dump(exclude=excluded) != original.model_dump(exclude=excluded):
        raise PDFError("report does not match PDF machine evidence. Regenerate it from the PDF")
    return report.model_copy(update={"schema_version": original.schema_version})


def _correction_input(args: argparse.Namespace) -> tuple[str, str]:
    if not args.correction_stdin:
        if args.value is None or args.reason is None:
            raise ValueError("a correction needs a value and a reason")
        return str(args.value), str(args.reason)
    if args.value is not None or args.reason is not None:
        raise ValueError("choose one correction input method")
    data = sys.stdin.buffer.read(MAX_CORRECTION_BYTES + 1)
    if len(data) > MAX_CORRECTION_BYTES:
        raise ValueError("correction input exceeds the byte limit")
    body = json.loads(data)
    if not isinstance(body, dict) or set(body) != {"value", "reason"}:
        raise ValueError("expected a correction object")
    value, reason = body["value"], body["reason"]
    if not isinstance(value, str) or not isinstance(reason, str):
        raise ValueError("expected a string value and reason")
    return value, reason


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="documind", description="Local PDF proposal analysis")
    commands = parser.add_subparsers(dest="command", required=True)
    extraction = commands.add_parser("extract", help="extract fields and citations from a PDF")
    extraction.add_argument("pdf", type=Path)
    comparison = commands.add_parser("compare", help="compare two PDFs or two reviewed reports")
    comparison.add_argument("left", type=Path)
    comparison.add_argument("right", type=Path)
    comparison.add_argument("--reports", action="store_true", help="use existing JSON reports")
    comparison.add_argument(
        "--source-pdfs",
        nargs=2,
        type=Path,
        metavar=("LEFT_PDF", "RIGHT_PDF"),
        help="verify both reports against their source PDFs",
    )
    review = commands.add_parser("correct", help="append a correction to a JSON report")
    review.add_argument("report", type=Path)
    review.add_argument("field", type=FieldName, choices=list(FieldName))
    review.add_argument("value", nargs="?")
    review.add_argument("--reason")
    review.add_argument(
        "--stdin",
        dest="correction_stdin",
        action="store_true",
        help="read a JSON object with value and reason from standard input",
    )
    export = commands.add_parser("export", help="export a JSON report as CSV")
    export.add_argument("report", type=Path)
    verification = commands.add_parser("verify", help="check machine observations against a PDF")
    verification.add_argument("report", type=Path)
    verification.add_argument("pdf", type=Path)
    for command in (extraction, comparison):
        command.add_argument("--format", choices=("json", "csv"), default="json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "extract":
            report = extract(read_pdf(args.pdf))
            output = (
                report_csv(report) if args.format == "csv" else report.model_dump_json(indent=2)
            )
        elif args.command == "compare":
            if args.reports:
                left, right = _load_report(args.left), _load_report(args.right)
                machine_evidence = "unverified"
                if args.source_pdfs:
                    left = _verify_report(left, args.source_pdfs[0])
                    right = _verify_report(right, args.source_pdfs[1])
                    machine_evidence = "verified"
            else:
                if args.source_pdfs:
                    raise ValueError("--source-pdfs requires --reports")
                left, right = extract(read_pdf(args.left)), extract(read_pdf(args.right))
                machine_evidence = "verified"
            results = compare(left, right)
            if args.format == "csv":
                output = comparison_csv(results, machine_evidence)
            else:
                output = json.dumps(
                    {
                        "left": left.model_dump(mode="json"),
                        "right": right.model_dump(mode="json"),
                        "machine_evidence": machine_evidence,
                        "comparisons": [item.model_dump(mode="json") for item in results],
                    },
                    indent=2,
                )
        elif args.command == "correct":
            value, reason = _correction_input(args)
            report = correct(_load_report(args.report), args.field, value, reason)
            output = report.model_dump_json(indent=2)
        elif args.command == "export":
            output = report_csv(_load_report(args.report))
        else:
            _verify_report(_load_report(args.report), args.pdf)
            output = json.dumps({"machine_observations_verified": True})
    except PDFError as exc:
        print(f"documind: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValidationError, ValueError):
        print(
            "documind: could not read the report or apply the correction. Check the input format.",
            file=sys.stderr,
        )
        return 2
    sys.stdout.buffer.write(output.encode("utf-8"))
    if not output.endswith("\n"):
        sys.stdout.buffer.write(b"\n")
    return 0
