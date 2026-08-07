from __future__ import annotations

import json
import re
from dataclasses import dataclass

from app.agents.llm_client import complete
from app.db.schema_catalog import catalog

SELECTOR_SYSTEM_PROMPT = """You select which database tables are relevant to a user's question.

Here is the table catalog (table name: sample columns):
{catalog_summary}

Respond with ONLY a JSON object, no preamble, no markdown fences:
{{"tables": ["schema.table1", "schema.table2"], "confidence": "high" | "low"}}

Rules:
- Pick every table needed to fully answer the question, up to 5 — do not default
  to a single table if the question clearly needs data joined across several
  (e.g. a project's name AND its budget AND its members are three different
  tables unless a pre-joined view already covers all three).
- confidence "high" if you're fairly sure these tables answer the question directly.
- confidence "low" if the question is vague, ambiguous, or doesn't clearly map
  to any table (e.g. wrong terminology, missing specifics).
- If nothing matches at all, return an empty tables list with confidence "low".
- Views like vw_ProjectMemberBudgetFeatures already join several base tables —
  when a view's description covers the question, select ONLY that view (not
  its underlying base tables too), and treat that as high confidence.

Example — question needs a join across separate tables, no view covers it:
Question: "list customers and their project names"
{{"tables": ["dbo.Customer", "dbo.Project"], "confidence": "high"}}

Example — a pre-joined view already covers the question:
Question: "which projects are over budget"
{{"tables": ["dbo.vw_ProjectMemberBudgetFeatures"], "confidence": "high"}}
"""


@dataclass
class TableSelection:
    tables: list[str]
    confidence: str  # "high" | "low"


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_selection(raw: str) -> TableSelection:
    cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback: the model added a preamble/trailing text around the JSON —
        # pull out the first {...} block instead of giving up entirely.
        match = _JSON_OBJECT_RE.search(cleaned)
        if not match:
            return TableSelection(tables=[], confidence="low")
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return TableSelection(tables=[], confidence="low")

    tables = data.get("tables", []) if isinstance(data, dict) else []
    confidence = data.get("confidence", "low") if isinstance(data, dict) else "low"
    if not isinstance(tables, list):
        tables = []
    return TableSelection(tables=tables, confidence=confidence)


async def select_tables(user_message: str) -> TableSelection:
    system = SELECTOR_SYSTEM_PROMPT.format(catalog_summary=catalog.catalog_summary_text())
    raw = await complete(system=system, user=user_message, max_tokens=300, json_mode=True)
    return _parse_selection(raw)
