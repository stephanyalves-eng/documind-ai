import re
import tomllib
import unicodedata
from datetime import date
from decimal import Decimal
from importlib.resources import files

from .schemas import FieldName

with files("documind").joinpath("fields.toml").open("rb") as stream:
    _CONFIG = tomllib.load(stream)

ALIASES = {
    label.casefold(): FieldName(field)
    for field, labels in _CONFIG["aliases"].items()
    for label in labels
}
REQUIRED = tuple(FieldName(field) for field in _CONFIG["validation"]["required"])
CURRENCIES = frozenset(_CONFIG["validation"]["currencies"])
NUMERIC_FIELDS = frozenset({FieldName.AMOUNT, FieldName.SUBTOTAL, FieldName.TAX})
DATE_FIELDS = frozenset({FieldName.ISSUE_DATE, FieldName.VALID_UNTIL})
MONEY = re.compile(r"(?:[0-9]{1,12}|[0-9]{1,3}(?:,[0-9]{3}){1,3})(?:\.[0-9]{1,2})?")
PLACEHOLDERS = {"", "-", "n/a", "na", "tbd", "pending", "unknown", "not provided", "see attached"}


def text_key(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).casefold().split())


def normalize(field: FieldName, raw: str) -> str:
    if any(unicodedata.category(char) in {"Cc", "Cf", "Zl", "Zp"} for char in raw):
        raise ValueError("control characters are unsupported")
    value = " ".join(raw.split())
    if text_key(value) in PLACEHOLDERS or len(value) > 512:
        raise ValueError("blank, placeholder, or oversized value")
    if field in NUMERIC_FIELDS:
        if not MONEY.fullmatch(value):
            raise ValueError("use unsigned amounts with decimal point and optional comma grouping")
        return format(Decimal(value.replace(",", "")), ".2f")
    if field is FieldName.CURRENCY:
        if not value.isascii() or value.upper() not in CURRENCIES:
            raise ValueError("unsupported or ambiguous currency")
        return value.upper()
    if field in DATE_FIELDS:
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            raise ValueError("expected an ISO calendar date")
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError as exc:
            raise ValueError("invalid calendar date") from exc
    return value
