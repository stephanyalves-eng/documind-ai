from pathlib import Path

import pytest
from pydantic import ValidationError

from documind.evidence import verify_evidence
from documind.extract import extract
from documind.pdf_ingest import read_pdf
from documind.schemas import Evidence, FieldName, Report


def test_quote_is_exact_on_the_right_physical_page(pdfs: dict[str, Path]) -> None:
    document = read_pdf(pdfs["standard"])
    report = extract(document)
    (quote,) = report.observations[FieldName.WARRANTY].evidence
    assert quote.source_page == 2
    assert quote.evidence_text == "Warranty: 12 months after delivery"
    assert verify_evidence(document, quote)
    assert not verify_evidence(document, Evidence(source_page=1, evidence_text=quote.evidence_text))
    assert not verify_evidence(document, Evidence(source_page=2, evidence_text="12 months"))
    assert not verify_evidence(document, Evidence(source_page=3, evidence_text=quote.evidence_text))
    raw = report.model_dump(mode="json")
    raw["observations"]["warranty"]["evidence"][0]["source_page"] = 3
    with pytest.raises(ValidationError, match="page index"):
        Report.model_validate(raw)
