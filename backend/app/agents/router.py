from __future__ import annotations

from enum import Enum

from app.agents.llm_client import complete
from app.config import settings


class QueryIntent(str, Enum):
    DB_QUERY = "db_query"
    OFF_TOPIC = "off_topic"


ROUTER_SYSTEM_PROMPT = """You classify user messages for a database assistant scoped to: {domain}.

Respond with exactly one word, nothing else: "db_query" or "off_topic".

Rules:
- Greetings, small talk, meta-questions about capabilities, or anything unrelated
  to the database domain = off_topic
- Anything asking about data, records, counts, statuses, trends, or specific
  business entities that would live in the database = db_query
- If uncertain, prefer db_query so the user gets a real attempt at an answer.
"""


async def classify_intent(user_message: str) -> QueryIntent:
    system = ROUTER_SYSTEM_PROMPT.format(domain=settings.domain_description)
    raw = await complete(system=system, user=user_message, max_tokens=10)
    cleaned = raw.strip().lower()
    if "off_topic" in cleaned:
        return QueryIntent.OFF_TOPIC
    return QueryIntent.DB_QUERY


def off_topic_reply() -> str:
    return (
        f"I'm set up to answer questions about {settings.domain_description}. "
        f"Try asking something like: {settings.example_questions}."
    )
