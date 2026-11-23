import argparse
import json
import re
from collections.abc import Sequence
from io import BytesIO
from pathlib import Path
from typing import TypedDict

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen.canvas import Canvas

from ._output import write_artifact

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "synthetic-v1.json"
DATASETS = ("v1", "v2")


class StructuredPage(TypedDict, total=False):
    title: str
    lines: list[str]
    rows: list[tuple[str, str]]
    columns: tuple[list[str], list[str]]


def manifest_path(dataset: str) -> Path:
    if dataset not in DATASETS:
        raise ValueError(f"unsupported dataset: {dataset}")
    return MANIFEST if dataset == "v1" else ROOT / "data" / "synthetic-v2.json"


def _draw_page(canvas: Canvas, page: StructuredPage) -> None:
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(52, 681, page["title"])
    canvas.setFont("Helvetica", 11)
    if rows := page.get("rows"):
        for index, (label, value) in enumerate(rows):
            y = 637 - 28 * index
            canvas.setStrokeColor(HexColor("#c8d5d9"))
            canvas.line(52, y - 8, 560, y - 8)
            canvas.drawString(59, y, label)
            canvas.drawString(245, y, value)
    elif columns := page.get("columns"):
        canvas.setStrokeColor(HexColor("#c8d5d9"))
        canvas.line(304, 655, 304, 480)
        for x, lines in zip((52, 322), columns, strict=True):
            for index, line in enumerate(lines):
                canvas.drawString(x, 637 - 24 * index, line)
    else:
        for index, line in enumerate(page.get("lines", [])):
            canvas.drawString(52, 637 - 24 * index, line)


def write_pdf(path: Path, pages: Sequence[list[str] | StructuredPage]) -> None:
    buffer = BytesIO()
    canvas = Canvas(buffer, pagesize=letter, invariant=True)
    canvas.setTitle("DocuMind synthetic sample")
    canvas.setAuthor("DocuMind AI")
    for number, lines in enumerate(pages, 1):
        if lines:
            canvas.setFillColor(HexColor("#164949"))
            canvas.setFont("Helvetica-Bold", 17)
            canvas.drawString(52, 728, "SYNTHETIC | DocuMind test document")
            canvas.setFillColor(HexColor("#202b33"))
            canvas.setFont("Helvetica", 11)
            if isinstance(lines, list):
                for index, line in enumerate(lines):
                    canvas.drawString(52, 675 - 24 * index, line)
            else:
                _draw_page(canvas, lines)
            canvas.drawString(52, 42, f"Synthetic fixture | Page {number} of {len(pages)}")
        canvas.showPage()
    canvas.save()
    write_artifact(path, buffer.getvalue())


def generate(out: Path, dataset: str = "v1") -> dict[str, Path]:
    manifest = json.loads(manifest_path(dataset).read_text(encoding="utf-8"))
    documents = manifest["documents"]
    if any(
        not re.fullmatch(r"[a-z0-9_]+", name)
        or re.fullmatch(r"(?:con|prn|aux|nul|(?:com|lpt)[0-9])", name)
        for name in documents
    ):
        raise ValueError("invalid synthetic fixture name")
    out.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, pages in documents.items():
        path = out / f"{name}.pdf"
        write_pdf(path, pages)
        paths[name] = path
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic PDF fixtures offline")
    parser.add_argument("--dataset", choices=DATASETS, default="v1")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    default_dir = ROOT / "data" / ("generated" if args.dataset == "v1" else "generated-v2")
    paths = generate(args.out or default_dir, args.dataset)
    print(f"Generated {len(paths)} synthetic PDFs.")


if __name__ == "__main__":
    main()
