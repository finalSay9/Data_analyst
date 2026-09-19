"""
Sanitizing arbitrary strings (CSV headers, filenames) into safe, unique
Postgres identifiers.

Why this matters beyond cosmetics: these strings eventually get
interpolated into DDL (`CREATE TABLE ...`) and column lists. Postgres
identifiers have real rules (can't start with a digit, limited charset,
63-byte length limit), and since we're building DDL dynamically rather
than using parameterized queries (DDL can't be parameterized the way
DML can), sanitization here is also a security boundary, not just
formatting.
"""

import re

_POSTGRES_IDENTIFIER_MAX_LENGTH = 63
_INVALID_CHARS = re.compile(r"[^a-z0-9_]")
_REPEATED_UNDERSCORES = re.compile(r"_+")


def sanitize_identifier(raw: str, fallback: str = "col") -> str:
    """
    Turn an arbitrary string into a single safe Postgres identifier.

    Does NOT guarantee uniqueness across a set of columns — see
    `dedupe_identifiers` for that. This function only guarantees the
    result is a *valid* identifier in isolation.
    """
    value = raw.strip().lower()
    value = _INVALID_CHARS.sub("_", value)
    value = _REPEATED_UNDERSCORES.sub("_", value)
    value = value.strip("_")

    if not value:
        value = fallback

    # Postgres identifiers can't start with a digit.
    if value[0].isdigit():
        value = f"{fallback}_{value}"

    return value[:_POSTGRES_IDENTIFIER_MAX_LENGTH]


def dedupe_identifiers(raw_names: list[str], fallback: str = "col") -> list[str]:
    """
    Sanitize a list of names (e.g. CSV headers) and resolve collisions
    with a numeric suffix: "Total $" and "Total #" both sanitize to
    "total_" -> "total_" and "total_2".

    Order-preserving: the Nth column keeps its position, only the name
    changes.
    """
    seen: dict[str, int] = {}
    result: list[str] = []

    for i, raw in enumerate(raw_names):
        base = sanitize_identifier(raw, fallback=f"{fallback}_{i}")

        if base not in seen:
            seen[base] = 1
            result.append(base)
        else:
            seen[base] += 1
            candidate = f"{base}_{seen[base]}"
            # Extremely unlikely, but guard against the suffixed name
            # itself colliding with an existing column.
            while candidate in seen:
                seen[base] += 1
                candidate = f"{base}_{seen[base]}"
            seen[candidate] = 1
            result.append(candidate)

    return result


def build_table_name(dataset_id: int, name_hint: str) -> str:
    """
    Deterministic dynamic table name, e.g. dataset_7_sales_data.

    Including the dataset_id guarantees uniqueness even if two uploads
    have the same filename; the sanitized hint keeps it human-readable
    when browsing the database directly.
    """
    slug = sanitize_identifier(name_hint, fallback="upload")
    prefix = f"dataset_{dataset_id}_"
    max_slug_length = _POSTGRES_IDENTIFIER_MAX_LENGTH - len(prefix)
    return f"{prefix}{slug[:max_slug_length]}"
