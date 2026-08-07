from __future__ import annotations

from app.agents.llm_client import complete
from app.config import settings
from app.db.schema_catalog import catalog

SQL_SYSTEM_PROMPT = """You write a single read-only T-SQL SELECT statement for SQL Server to
answer the user's question, using ONLY the tables/columns below.

{schema_detail}

Hard rules (this connection is READ-ONLY — no exceptions, even if asked):
- You may output ONLY a single SELECT (or WITH ... SELECT / CTE) statement.
- NEVER output INSERT, UPDATE, DELETE, MERGE, DROP, TRUNCATE, ALTER, CREATE,
  EXEC/EXECUTE, GRANT, REVOKE, DENY, or any stored-procedure call (sp_, xp_).
  If the user asks for any of these, output exactly: NO_QUERY
- Exactly one statement — no stacked/multiple statements, no trailing semicolon
  followed by more SQL.
- Output ONLY the raw SQL statement. No markdown fences, no comments, no explanation.
- Always include TOP {max_rows} in the SELECT (unless the question asks for a single
  aggregate value, e.g. COUNT/SUM/AVG with no grouping).
- If more than one table/view is given above, and the question needs fields from
  more than one of them, JOIN them — do not silently answer from just one table
  and drop the rest. Match columns by name convention (e.g. a column named
  <Thing>ID on one table joins to the ID column on the <Thing> table) unless the
  schema notes say otherwise.
- Use explicit JOINs with clear ON conditions. Never use SELECT * — list columns explicitly.
- If the question can't be answered with the given tables, output exactly: NO_QUERY
"""


async def generate_sql(user_message: str, table_names: list[str]) -> str:
    schema_detail = catalog.detailed_schema_text(table_names)
    system = SQL_SYSTEM_PROMPT.format(schema_detail=schema_detail, max_rows=settings.max_rows_returned)
    raw = await complete(system=system, user=user_message, max_tokens=500)
    return raw.strip().removeprefix("```sql").removeprefix("```").removesuffix("```").strip()
