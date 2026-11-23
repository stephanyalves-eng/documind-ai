from hashlib import sha256
from pathlib import Path

import pymupdf
import pytest

from documind.pdf_ingest import Limits, PDFError, read_pdf
from scripts.generate_test_docs import write_pdf


def test_two_physical_pages_and_hash(pdfs: dict[str, Path]) -> None:
    path = pdfs["standard"]
    actual = read_pdf(path)
    assert actual.sha256 == sha256(path.read_bytes()).hexdigest()
    assert len(actual.pages) == 2
    assert "Vendor:" in actual.pages[0]
    assert "Warranty:" in actual.pages[1]
    assert not actual.unreadable_pages


@pytest.mark.parametrize("data", [b"", b"<html>Vendor: fake</html>", b"%PDF-1.7\ninvalid"])
def test_reject_non_pdf_and_invalid_pdf(tmp_path: Path, data: bytes) -> None:
    path = tmp_path / "invalid.pdf"
    path.write_bytes(data)
    with pytest.raises(PDFError):
        read_pdf(path)


def test_reject_nonfile(tmp_path: Path) -> None:
    with pytest.raises(PDFError, match="regular file"):
        read_pdf(tmp_path)
    with pytest.raises(PDFError, match="regular file"):
        read_pdf(tmp_path / "missing.pdf")


@pytest.mark.parametrize(
    ("limits", "message"),
    [
        (Limits(max_bytes=15), "byte limit"),
        (Limits(max_pages=1), "page count"),
        (Limits(max_characters=12), "character limit"),
    ],
)
def test_ingestion_limits(pdfs: dict[str, Path], limits: Limits, message: str) -> None:
    with pytest.raises(PDFError, match=message):
        read_pdf(pdfs["standard"], limits)


def test_accept_exact_limits(pdfs: dict[str, Path]) -> None:
    path = pdfs["standard"]
    reference = read_pdf(path)
    assert (
        read_pdf(
            path,
            Limits(
                max_bytes=path.stat().st_size,
                max_pages=2,
                max_characters=sum(map(len, reference.pages)),
            ),
        )
        == reference
    )


def test_empty_layer_and_partial_text(tmp_path: Path, pdfs: dict[str, Path]) -> None:
    blank = tmp_path / "blank.pdf"
    write_pdf(blank, [[]])
    with pytest.raises(PDFError, match="no readable text layer"):
        read_pdf(blank)
    assert read_pdf(pdfs["mixed"]).unreadable_pages == (2,)


def test_image_only_pdf_requests_review_via_rejection(tmp_path: Path) -> None:
    path = tmp_path / "synthetic-image.pdf"
    with pymupdf.open() as doc:
        page = doc.new_page()
        pixels = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 16, 16), False)
        pixels.clear_with(60)
        page.insert_image(pymupdf.Rect(20, 20, 130, 130), pixmap=pixels)
        doc.save(path)
    with pytest.raises(PDFError, match="OCR"):
        read_pdf(path)


def test_password_protection(tmp_path: Path, pdfs: dict[str, Path]) -> None:
    encrypted = tmp_path / "encrypted.pdf"
    with pymupdf.open(pdfs["standard"]) as doc:
        doc.save(
            encrypted,
            encryption=pymupdf.PDF_ENCRYPT_AES_256,
            user_pw="synthetic",
            owner_pw="synthetic-owner",
        )
    with pytest.raises(PDFError, match="password-protected"):
        read_pdf(encrypted)


def test_truncated_xref_is_rejected(tmp_path: Path, pdfs: dict[str, Path]) -> None:
    source = pdfs["standard"].read_bytes()
    path = tmp_path / "truncated.pdf"
    path.write_bytes(source[: source.rindex(b"\nxref\n")])
    with pytest.raises(PDFError, match="structural repair|could not be parsed"):
        read_pdf(path)
