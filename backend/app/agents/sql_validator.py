from __future__ import annotations

import re

BLOCKED_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "EXEC", "EXECUTE",
    "MERGE", "TRUNCATE", "CREATE", "GRANT", "REVOKE", "DENY",
    "sp_", "xp_",
]


class UnsafeQueryError(Exception):
    pass


def validate_sql(sql: str) -> str:
    """Raises UnsafeQueryError if the statement looks unsafe. Returns cleaned SQL otherwise.

    This is a defense-in-depth check — the DB login itself must also be read-only.
    """
    if not sql or sql.strip().upper() == "NO_QUERY":
        raise UnsafeQueryError("No valid query generated")

    stripped = sql.strip().rstrip(";")

    if not re.match(r"^\s*(SELECT|WITH)\b", stripped, re.IGNORECASE):
        raise UnsafeQueryError("Only SELECT statements are permitted")

    upper = stripped.upper()
    for keyword in BLOCKED_KEYWORDS:
        pattern = rf"\b{re.escape(keyword.upper())}\b" if not keyword.endswith("_") else keyword.upper()
        if re.search(pattern, upper):
            raise UnsafeQueryError(f"Blocked keyword detected: {keyword}")

    # Prevent stacked statements
    if ";" in stripped:
        raise UnsafeQueryError("Multiple statements are not permitted")

    return stripped
