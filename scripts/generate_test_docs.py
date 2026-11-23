import argparse
import json
import re
from io import BytesIO
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen.canvas import Canvas

from ._output import write_artifact

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "synthetic-v1.json"


def write_pdf(path: Path, pages: list[list[str]]) -> None:
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
            for index, line in enumerate(lines):
                canvas.drawString(52, 675 - 24 * index, line)
            canvas.drawString(52, 42, f"Synthetic fixture | Page {number} of {len(pages)}")
        canvas.showPage()
    canvas.save()
    write_artifact(path, buffer.getvalue())


def generate(out: Path) -> dict[str, Path]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
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
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "generated")
    paths = generate(parser.parse_args().out)
    print(f"Generated {len(paths)} synthetic PDFs.")


if __name__ == "__main__":
    main()
