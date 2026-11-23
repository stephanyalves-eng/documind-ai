"""Internal in-memory parser invoked by pdf_ingest in a separate process."""

import json
import sys
from importlib.metadata import version
from typing import TypedDict

from .pdf_ingest import Limits, PDFProblem


class ParsedText(TypedDict):
    pages: list[str]
    unreadable_pages: list[int]


def parse(data: bytes, limits: Limits) -> ParsedText | PDFProblem:
    if version("PyMuPDF") != "2.1":
        return PDFProblem.DEPENDENCY
    import pymupdf

    pages: list[str] = []
    unreadable: list[int] = []
    extracted_characters = 0
    # These diagnostic switches are untyped in PyMuPDF 2.1.
    pymupdf.TOOLS.mupdf_display_errors(False)  # type: ignore[no-untyped-call]
    pymupdf.TOOLS.mupdf_display_warnings(False)  # type: ignore[no-untyped-call]
    try:
        # PyMuPDF does not annotate its document constructor.
        with pymupdf.open(stream=data, filetype="pdf") as document:  # type: ignore[no-untyped-call]
            if not document.is_pdf:
                return PDFProblem.INVALID
            if document.is_repaired:
                return PDFProblem.REPAIRED
            if document.needs_pass:
                return PDFProblem.PASSWORD
            if not 1 <= document.page_count <= limits.max_pages:
                return PDFProblem.PAGE_LIMIT
            for page in document:
                value = page.get_text("text")
                extracted_characters += len(value)
                if extracted_characters > limits.max_characters:
                    return PDFProblem.CHARACTER_LIMIT
                if (
                    not value.strip()
                    or "\ufffd" in value
                    or any(
                        span["type"] == 3 or span["opacity"] == 0 for span in page.get_texttrace()
                    )
                ):
                    unreadable.append(page.number + 1)
                    value = ""
                pages.append(value)
    except (RuntimeError, ValueError):
        return PDFProblem.INVALID
    if len(unreadable) == len(pages):
        return PDFProblem.UNREADABLE
    return {"pages": pages, "unreadable_pages": unreadable}


def _set_limits() -> None:
    if sys.platform != "linux":
        return
    import resource

    for kind, cap in ((resource.RLIMIT_AS, 512 * 1024 * 1024), (resource.RLIMIT_CPU, 10)):
        bounds = resource.getrlimit(kind)
        effective = min((cap, *(bound for bound in bounds if bound >= 0)))
        resource.setrlimit(kind, (effective, effective))


def main() -> None:
    _set_limits()
    limits = Limits(*map(int, sys.argv[1:]))
    data = sys.stdin.buffer.read(limits.max_bytes + 1)
    result = parse(data, limits) if len(data) <= limits.max_bytes else PDFProblem.INVALID
    print(json.dumps({"error": result} if isinstance(result, PDFProblem) else result))


if __name__ == "__main__":
    main()
