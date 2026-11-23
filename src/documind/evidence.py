from .pdf_ingest import PDFText
from .schemas import Evidence


def verify_evidence(document: PDFText, evidence: Evidence) -> bool:
    """Verify the exact extracted line on the claimed physical page."""
    return 1 <= evidence.source_page <= len(
        document.pages
    ) and evidence.evidence_text in document.pages[evidence.source_page - 1].split("\n")
