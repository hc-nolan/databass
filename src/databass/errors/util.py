"""
Translates low-level exceptions (SQLAlchemy/DB errors, image-fetch failures,
etc.) into short messages that are safe and useful to show to an end user,
instead of a raw stack trace or driver error string.
"""
import re
from sqlalchemy.exc import IntegrityError

# Matches both SQLite ("UNIQUE constraint failed: release.mbid") and
# Postgres ("duplicate key value violates unique constraint \"release_mbid_key\"",
# with a "Key (mbid)=(...)" detail line) integrity error messages.
_UNIQUE_RE = [
    re.compile(r"UNIQUE constraint failed: (?:\w+\.)?(\w+)", re.IGNORECASE),
    re.compile(r"Key \((\w+)\)=.*already exists", re.IGNORECASE),
]
_NOT_NULL_RE = [
    re.compile(r"NOT NULL constraint failed: (?:\w+\.)?(\w+)", re.IGNORECASE),
    re.compile(r'null value in column "(\w+)"', re.IGNORECASE),
]
_CHECK_RE = [
    re.compile(r"CHECK constraint failed: (\w+)", re.IGNORECASE),
    re.compile(r'violates check constraint "(\w+)"', re.IGNORECASE),
]
_FK_RE = [
    re.compile(r"FOREIGN KEY constraint failed"),
    re.compile(r'violates foreign key constraint "(\w+)"', re.IGNORECASE),
]


def _field_label(field: str) -> str:
    return field.replace("_", " ")


def _first_match(patterns: list[re.Pattern], text: str) -> str | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match.group(1) if match.groups() else ""
    return None


def integrity_error_message(err: IntegrityError) -> str:
    """
    Build a user-facing message describing which field caused a database
    integrity error (unique, not-null, check, or foreign key violation).
    Falls back to a generic message if the underlying error can't be parsed.
    """
    text = str(err.orig) if getattr(err, "orig", None) else str(err)

    field = _first_match(_UNIQUE_RE, text)
    if field is not None:
        return f"A record with that {_field_label(field)} already exists."

    field = _first_match(_NOT_NULL_RE, text)
    if field is not None:
        return f"The '{_field_label(field)}' field is required."

    field = _first_match(_CHECK_RE, text)
    if field is not None:
        return f"The value provided for '{_field_label(field)}' is not valid."

    if _first_match(_FK_RE, text) is not None:
        return "This entry references a record that doesn't exist."

    return "Could not save the entry because it conflicts with an existing record."


def friendly_message(exc: Exception) -> str:
    """
    Convert an exception into a short, user-facing message. Used as a
    catch-all for routes that don't need bespoke handling of a specific
    exception type.
    """
    if isinstance(exc, IntegrityError):
        return integrity_error_message(exc)
    message = str(exc).strip()
    return message or f"An unexpected {type(exc).__name__} occurred."
