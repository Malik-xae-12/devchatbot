"""
Splices virtual-view CTE definitions into a generated query, so that a
`FROM vw_ProjectMemberBudgetFeatures` written by the LLM works even though
no such object exists in the DB (see app/db/virtual_views.py for why).

Runs AFTER sql_validator.validate_sql() on the raw LLM output, and its
output is re-validated before execution — it only ever adds fixed, known-safe
SELECT-only CTE text, but re-validating costs nothing and keeps the
"only ever run something that passed validate_sql" invariant simple.
"""
from __future__ import annotations

import re

from app.db.virtual_views import VIRTUAL_VIEWS

_WITH_PREFIX = re.compile(r"^\s*WITH\b", re.IGNORECASE)


def inline_virtual_views(sql: str) -> str:
    referenced = [
        vv for vv in VIRTUAL_VIEWS.values()
        if re.search(rf"\b{re.escape(vv.name)}\b", sql, re.IGNORECASE)
    ]
    if not referenced:
        return sql

    # CTE names can never be schema-qualified when referenced in T-SQL — but
    # the LLM (correctly, per the catalog listing "dbo.vw_...") often writes
    # `FROM dbo.vw_ProjectMemberBudgetFeatures`. Left as-is, SQL Server treats
    # that as a real object lookup ("Invalid object name") instead of
    # resolving it to our CTE. Strip the schema prefix off every reference
    # before splicing the CTE in.
    for vv in referenced:
        sql = re.sub(
            rf"\b{re.escape(vv.schema)}\.{re.escape(vv.name)}\b",
            vv.name,
            sql,
            flags=re.IGNORECASE,
        )

    cte_block = ",\n".join(vv.cte_sql for vv in referenced)

    if _WITH_PREFIX.match(sql):
        # Query already has its own WITH clause — splice ours in first.
        return _WITH_PREFIX.sub(f"WITH {cte_block},", sql, count=1)

    return f"WITH {cte_block}\n{sql}"
