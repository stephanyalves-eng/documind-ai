import re
from collections import defaultdict
from decimal import Context, Decimal, localcontext

from .normalize import ALIASES, REQUIRED, normalize, text_key
from .pdf_ingest import PDFText
from .schemas import (
    CLAUSE_FIELDS,
    CURRENT_REPORT_VERSION,
    Correction,
    Evidence,
    FieldName,
    FieldStatus,
    Issue,
    Observation,
    Report,
)

LABEL = re.compile(r"^[ \t]*([A-Za-z][A-Za-z ]{0,40})[ \t]*:[ \t]*(.*)$")
CONDITION = re.compile(
    r"^[ \t]*(?:[•–-][ \t]+)?"
    r"(?:only|subject[ \t]+to|unless|if|provided|except|excluding|"
    r"contingent[ \t]+on|conditional[ \t]+on|not[ \t]+until|"
    r"somente|apenas|desde[ \t]+que|sujeit[oa][ \t]+a|salvo|exceto)\b",
    re.IGNORECASE,
)


def _observe(field: FieldName, candidates: list[tuple[str, tuple[Evidence, ...]]]) -> Observation:
    if not candidates:
        return Observation(confidence_or_status=FieldStatus.MISSING, reason="no_supported_label")
    evidence = tuple(item for _, group in candidates for item in group)
    if any(item.extraction_method == "adjacent_condition" for item in evidence):
        return Observation(
            confidence_or_status=FieldStatus.NEEDS_REVIEW,
            evidence=evidence,
            reason="possible_clause_continuation",
        )
    try:
        values = [normalize(field, raw) for raw, _ in candidates]
    except ValueError as exc:
        return Observation(
            confidence_or_status=FieldStatus.NEEDS_REVIEW, evidence=evidence, reason=str(exc)
        )
    if len({text_key(value) for value in values}) > 1:
        return Observation(
            confidence_or_status=FieldStatus.NEEDS_REVIEW,
            evidence=evidence,
            reason="conflicting_labeled_values",
        )
    return Observation(
        value=values[0], confidence_or_status=FieldStatus.EXTRACTED, evidence=evidence
    )


def validate(report: Report) -> tuple[Issue, ...]:
    issues = []
    if report.unreadable_pages:
        issues.append(
            Issue(code="unreadable_pages", fields=REQUIRED, detail="inspect the unreadable pages")
        )
    for field in REQUIRED:
        _, status = report.effective_value(field)
        if status in {FieldStatus.MISSING, FieldStatus.NEEDS_REVIEW}:
            issues.append(Issue(code="required_field", fields=(field,), detail=status.value))

    def value(field: FieldName) -> str | None:
        return report.effective_value(field)[0]

    money_fields = (FieldName.AMOUNT, FieldName.SUBTOTAL, FieldName.TAX)
    amount, subtotal, tax = (value(field) for field in money_fields)
    if any(report.effective_value(field)[1] is FieldStatus.NEEDS_REVIEW for field in money_fields):
        issues.append(
            Issue(
                code="arithmetic_unresolved",
                fields=money_fields,
                detail="a supplied total component needs review",
            )
        )
    elif amount is not None and subtotal is not None and tax is not None:
        with localcontext(Context(prec=16)):
            arithmetic_matches = Decimal(amount) == Decimal(subtotal) + Decimal(tax)
        if not arithmetic_matches:
            issues.append(
                Issue(
                    code="inconsistent_total",
                    fields=money_fields,
                    detail="subtotal plus tax differs from the total",
                )
            )

    issue_date, valid_until = value(FieldName.ISSUE_DATE), value(FieldName.VALID_UNTIL)
    if issue_date and valid_until and valid_until < issue_date:
        issues.append(
            Issue(
                code="date_order",
                fields=(FieldName.ISSUE_DATE, FieldName.VALID_UNTIL),
                detail="validity ends before the issue date",
            )
        )
    return tuple(issues)


def extract(document: PDFText) -> Report:
    candidates: dict[FieldName, list[tuple[str, tuple[Evidence, ...]]]] = defaultdict(list)
    for page, text in enumerate(document.pages, 1):
        lines = text.split("\n")
        for index, line in enumerate(lines):
            match = LABEL.fullmatch(line)
            if match and (field := ALIASES.get(text_key(match[1]))) is not None:
                evidence = [Evidence(source_page=page, evidence_text=line)]
                if field in CLAUSE_FIELDS:
                    # A recognized condition immediately after a clause can change its meaning.
                    next_index = index + 1
                    while next_index < len(lines) and CONDITION.match(lines[next_index]):
                        evidence.append(
                            Evidence(
                                source_page=page,
                                evidence_text=lines[next_index],
                                extraction_method="adjacent_condition",
                            )
                        )
                        next_index += 1
                candidates[field].append((match[2], tuple(evidence)))

    report = Report(
        schema_version=CURRENT_REPORT_VERSION,
        document_sha256=document.sha256,
        page_count=len(document.pages),
        unreadable_pages=document.unreadable_pages,
        observations={field: _observe(field, candidates[field]) for field in FieldName},
    )
    return report.model_copy(update={"issues": validate(report)})


def correct(report: Report, field: FieldName, value: str, reason: str) -> Report:
    correction = Correction(field=field, value=normalize(field, value), reason=reason)
    updated = report.model_copy(update={"corrections": (*report.corrections, correction)})
    return updated.model_copy(update={"issues": validate(updated)})
