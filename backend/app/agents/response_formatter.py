from __future__ import annotations

import json
from typing import Any

from app.agents.llm_client import complete

FORMAT_SYSTEM_PROMPT = """You turn database query results into a clear, well-formatted answer
for a business user, using Markdown.

Formatting rules:
- Open with a one-line, plain-English headline answer — no preamble like "Based on the data".
- If there are multiple rows with more than one field worth comparing, present them as a
  Markdown table with a header row. Keep column headers short and business-friendly.
- If the result is a single value (a count, sum, average, etc.), lead with that number in
  **bold** rather than burying it in a sentence.
- Use bullet points instead of a table for short lists of a single field (e.g. a list of names).
- Keep prose between/around tables brief — a sentence or two, not paragraphs.
- If the result set is empty, say so plainly in one line and do not speculate about why.

Do not mention SQL, tables, or columns by their technical names — translate into plain
business language.
"""

SUMMARY_SYSTEM_PROMPT = """You turn a LARGE database query result into a brief, well-formatted
Markdown summary for a business user — the person will be offered a full Excel download
separately, so your job here is orientation, not a full dump.

Formatting rules:
- Open with a one-line, plain-English headline (e.g. what was found, and how many rows total).
- Follow with a small Markdown table (5-8 rows max) showing a representative or top-ranked
  sample of the results — pick whichever rows best illustrate the answer (e.g. largest values,
  most over budget, etc. if that fits the question).
- Optionally add one short sentence of insight (a notable min/max/trend) if it's obvious from
  the sample — do not speculate beyond what's in the data.
- Do not say "here are the first N rows" mechanically — make the sample feel intentional.
- Do not mention SQL, tables, or columns by their technical names.
"""


async def format_response(user_message: str, rows: list[dict[str, Any]]) -> str:
    payload = json.dumps(rows[:50], default=str)  # cap payload sent to LLM
    user_prompt = f"Question: {user_message}\n\nQuery results (JSON):\n{payload}"
    return await complete(system=FORMAT_SYSTEM_PROMPT, user=user_prompt, max_tokens=600)


async def format_summary(user_message: str, rows: list[dict[str, Any]], total_row_count: int) -> str:
    """Used when the result set is large enough to be routed to an Excel download
    instead of being rendered in full in the chat."""
    payload = json.dumps(rows[:50], default=str)
    user_prompt = (
        f"Question: {user_message}\n\n"
        f"Total matching rows: {total_row_count} (showing a sample below for you to summarize)\n\n"
        f"Query results sample (JSON):\n{payload}"
    )
    return await complete(system=SUMMARY_SYSTEM_PROMPT, user=user_prompt, max_tokens=500)


def build_clarification(table_names: list[str], user_message: str) -> str:
    if table_names:
        readable = ", ".join(t.split(".")[-1] for t in table_names[:3])
        return (
            f"I wasn't fully confident that matches your question — I checked data "
            f"related to {readable}. Could you clarify what you're looking for, "
            f"e.g. a specific project, member, or time period?"
        )
    return (
        "I couldn't confidently match this to our project/resource data. Could you "
        "rephrase, or specify a project, member, or budget you're asking about?"
    )
