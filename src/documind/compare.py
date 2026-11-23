import re
from typing import Literal

from .extract import validate
from .normalize import REQUIRED, text_key
from .schemas import (
    CLAUSE_FIELDS,
    CURRENT_REPORT_VERSION,
    Comparison,
    FieldName,
    FieldStatus,
    MatchStatus,
    Report,
)

Mode = Literal["strict", "rules"]
PAYMENT = re.compile(
    r"(?:due |payable )?(?:within )?([1-9][0-9]{0,2}) days? (?:from|after) invoice(?: date)?"
)
WARRANTY = re.compile(r"([1-9][0-9]{0,2}) (months?|years?) (?:from|after) delivery")
DELIVERY = re.compile(r"(?:within )?([1-9][0-9]{0,2}) (calendar days?|weeks?) (?:from|after) order")


def _clause_key(field: FieldName, value: str) -> tuple[int, bool] | None:
    # The boolean distinguishes an explicit upper bound from an exact schedule.
    if field is FieldName.PAYMENT and (match := PAYMENT.fullmatch(value)):
        return int(match[1]), "within " in value
    if field is FieldName.WARRANTY and (match := WARRANTY.fullmatch(value)):
        return int(match[1]) * (12 if match[2].startswith("year") else 1), False
    if field is FieldName.DELIVERY and (match := DELIVERY.fullmatch(value)):
        return int(match[1]) * (7 if match[2].startswith("week") else 1), value.startswith(
            "within "
        )
    return None


def _decision(
    field: FieldName, left: str | None, right: str | None, blocked: bool, mode: Mode
) -> tuple[MatchStatus, str]:
    if blocked:
        return MatchStatus.NEEDS_REVIEW, "unresolved_input"
    if left is None or right is None:
        return MatchStatus.MISSING, "missing_on_one_or_both_sides"
    a, b = text_key(left), text_key(right)
    if a == b:
        return MatchStatus.MATCHED, "normalized_equality"
    if field not in CLAUSE_FIELDS or mode == "strict":
        return MatchStatus.DIFFERENT, "normalized_inequality"
    first, second = _clause_key(field, a), _clause_key(field, b)
    if first is None or second is None:
        return MatchStatus.NEEDS_REVIEW, "unsupported_clause_relationship"
    if first == second:
        return MatchStatus.MATCHED, "equivalent_controlled_clause"
    return MatchStatus.DIFFERENT, "different_controlled_clause"


def compare(left: Report, right: Report, mode: Mode = "rules") -> tuple[Comparison, ...]:
    issues = (*validate(left), *validate(right))
    blocked_fields = {
        field for issue in issues if issue.code != "required_field" for field in issue.fields
    }
    left_currency, _ = left.effective_value(FieldName.CURRENCY)
    right_currency, _ = right.effective_value(FieldName.CURRENCY)
    results = []
    for field in REQUIRED:
        a, a_status = left.effective_value(field)
        b, b_status = right.effective_value(field)
        blocked = field in blocked_fields or FieldStatus.NEEDS_REVIEW in (a_status, b_status)
        legacy_clause = (
            field in CLAUSE_FIELDS
            and a is not None
            and b is not None
            and (
                (left.schema_version < CURRENT_REPORT_VERSION and a_status is FieldStatus.EXTRACTED)
                or (
                    right.schema_version < CURRENT_REPORT_VERSION
                    and b_status is FieldStatus.EXTRACTED
                )
            )
        )
        if legacy_clause:
            status, reason = MatchStatus.NEEDS_REVIEW, "legacy_clause_evidence"
        elif field is FieldName.AMOUNT and a is not None and b is not None:
            if left_currency is None or right_currency is None:
                status, reason = MatchStatus.NEEDS_REVIEW, "unresolved_currency"
            elif left_currency != right_currency:
                status, reason = MatchStatus.NEEDS_REVIEW, "cross_currency_amount"
            else:
                status, reason = _decision(field, a, b, blocked, mode)
        else:
            status, reason = _decision(field, a, b, blocked, mode)
        results.append(
            Comparison(
                field=field,
                left_value=a,
                right_value=b,
                left_status=a_status,
                right_status=b_status,
                status=status,
                reason=reason,
            )
        )
    return tuple(results)
