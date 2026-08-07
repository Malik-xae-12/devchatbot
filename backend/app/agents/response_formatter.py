from __future__ import annotations

import json
from typing import Any

from app.agents.llm_client import complete

FORMAT_SYSTEM_PROMPT = """You turn database query results into a clear, natural-language answer
for a business user. Be concise and direct. Use a short table or bullet list only if it
genuinely helps readability with multiple rows. If the result set is empty, say so plainly
and do not speculate about why.

Do not mention SQL, tables, or columns by their technical names — translate into plain
business language.
"""


async def format_response(user_message: str, rows: list[dict[str, Any]]) -> str:
    payload = json.dumps(rows[:50], default=str)  # cap payload sent to LLM
    user_prompt = f"Question: {user_message}\n\nQuery results (JSON):\n{payload}"
    return await complete(system=FORMAT_SYSTEM_PROMPT, user=user_prompt, max_tokens=600)


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
