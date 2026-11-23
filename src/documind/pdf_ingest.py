import json
import subprocess
import sys
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from pathlib import Path

from .local_io import LocalPathError, read_local_bytes


class PDFError(ValueError):
    """A locally rejected PDF with a safe diagnostic."""


class PDFProblem(StrEnum):
    DEPENDENCY = "unsupported PyMuPDF version. Install the locked dependencies"
    INVALID = "PDF could not be parsed"
    REPAIRED = "PDF required structural repair"
    PASSWORD = "password-protected PDF is unsupported"
    PAGE_LIMIT = "PDF page count is outside the supported range"
    CHARACTER_LIMIT = "PDF exceeds the extracted character limit"
    UNREADABLE = "no readable text layer found. Image-only PDFs need OCR"


@dataclass(frozen=True)
class Limits:
    max_bytes: int = 10 * 1024 * 1024
    max_pages: int = 50
    max_characters: int = 500_000

    def __post_init__(self) -> None:
        if min(self.max_bytes, self.max_pages, self.max_characters) < 1:
            raise ValueError("PDF limits must be positive")


@dataclass(frozen=True)
class PDFText:
    sha256: str
    pages: tuple[str, ...]
    unreadable_pages: tuple[int, ...]


DEFAULT_LIMITS = Limits()
PARSER_TIMEOUT_SECONDS = 15


def read_pdf(path: Path, limits: Limits = DEFAULT_LIMITS) -> PDFText:
    try:
        data = read_local_bytes(path, limits.max_bytes)
    except LocalPathError as exc:
        raise PDFError(str(exc)) from exc
    except OSError as exc:
        raise PDFError("input could not be read") from exc
    if len(data) > limits.max_bytes:
        raise PDFError("PDF exceeds the byte limit")
    if not data.startswith(b"%PDF-"):
        raise PDFError("input does not have a PDF header")

    try:
        parsed = subprocess.run(
            [
                sys.executable,
                "-I",
                "-m",
                "documind._pdf_worker",
                str(limits.max_bytes),
                str(limits.max_pages),
                str(limits.max_characters),
            ],
            input=data,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=PARSER_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise PDFError("PDF parser exceeded its time limit") from exc
    except OSError as exc:
        raise PDFError("PDF parser could not start") from exc
    if parsed.returncode:
        raise PDFError("PDF parser failed or exceeded a resource limit")
    try:
        result = json.loads(parsed.stdout)
        if "error" in result:
            problem = PDFProblem(result["error"])
        else:
            pages = tuple(result["pages"])
            unreadable = tuple(result["unreadable_pages"])
            return PDFText(sha256(data).hexdigest(), pages, unreadable)
    except (KeyError, TypeError, ValueError) as exc:
        raise PDFError("PDF parser returned an invalid result") from exc
    raise PDFError(problem.value)
