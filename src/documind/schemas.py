from enum import StrEnum
from typing import Annotated, Final, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FieldName(StrEnum):
    VENDOR = "vendor"
    CURRENCY = "currency"
    AMOUNT = "amount"
    DELIVERY = "delivery_term"
    WARRANTY = "warranty"
    PAYMENT = "payment_terms"
    SUBTOTAL = "subtotal"
    TAX = "tax"
    ISSUE_DATE = "issue_date"
    VALID_UNTIL = "valid_until"


CLAUSE_FIELDS = frozenset({FieldName.DELIVERY, FieldName.WARRANTY, FieldName.PAYMENT})
CURRENT_REPORT_VERSION: Final = 2


class FieldStatus(StrEnum):
    EXTRACTED = "extracted"
    MISSING = "missing"
    NEEDS_REVIEW = "needs_review"
    MANUAL = "manual"


class MatchStatus(StrEnum):
    MATCHED = "matched"
    DIFFERENT = "different"
    MISSING = "missing"
    NEEDS_REVIEW = "needs_review"


PageNumber = Annotated[int, Field(ge=1)]


class Evidence(Record):
    source_page: PageNumber
    evidence_text: str = Field(min_length=1)
    extraction_method: Literal["anchored_label", "adjacent_condition"] = "anchored_label"


class Observation(Record):
    value: str | None = None
    confidence_or_status: FieldStatus
    evidence: tuple[Evidence, ...] = ()
    reason: str | None = None

    @model_validator(mode="after")
    def check_state(self) -> Self:
        if self.confidence_or_status is FieldStatus.EXTRACTED:
            if not self.value or not self.evidence or self.reason is not None:
                raise ValueError("extraction requires a value with evidence")
        elif self.confidence_or_status in {FieldStatus.MISSING, FieldStatus.NEEDS_REVIEW}:
            if self.value is not None or not self.reason:
                raise ValueError("abstention requires a reason and no value")
            if self.confidence_or_status is FieldStatus.MISSING and self.evidence:
                raise ValueError("missing observations cannot carry evidence")
        else:
            raise ValueError("manual values belong to the correction history")
        return self


class Correction(Record):
    field: FieldName
    value: str = Field(min_length=1, max_length=512)
    reason: str = Field(min_length=1, max_length=512)
    extraction_method: Literal["manual_review"] = "manual_review"

    @field_validator("reason")
    @classmethod
    def nonblank_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("provide a review reason")
        return value.strip()


class Issue(Record):
    code: str
    fields: tuple[FieldName, ...]
    detail: str


class Report(Record):
    schema_version: Literal[1, 2] = 1
    document_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    page_count: PageNumber
    unreadable_pages: tuple[PageNumber, ...] = ()
    observations: dict[FieldName, Observation]
    corrections: tuple[Correction, ...] = ()
    issues: tuple[Issue, ...] = ()

    @model_validator(mode="after")
    def check_pages_and_fields(self) -> Self:
        if set(self.observations) != set(FieldName):
            raise ValueError("report must cover all fields")
        evidence_pages = (
            evidence.source_page
            for item in self.observations.values()
            for evidence in item.evidence
        )
        if any(page > self.page_count for page in (*self.unreadable_pages, *evidence_pages)):
            raise ValueError("page index exceeds document length")
        return self

    def effective_value(self, field: FieldName) -> tuple[str | None, FieldStatus]:
        for correction in reversed(self.corrections):
            if correction.field is field:
                return correction.value, FieldStatus.MANUAL
        observation = self.observations[field]
        return observation.value, observation.confidence_or_status


class Comparison(Record):
    field: FieldName
    left_value: str | None
    right_value: str | None
    left_status: FieldStatus
    right_status: FieldStatus
    status: MatchStatus
    reason: str
