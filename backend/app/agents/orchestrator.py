from __future__ import annotations

import logging

from app.agents.query_rewriter import inline_virtual_views
from app.agents.response_formatter import build_clarification, format_response, format_summary
from app.agents.router import QueryIntent, classify_intent, off_topic_reply
from app.agents.sql_generator import generate_sql
from app.agents.sql_validator import UnsafeQueryError, validate_sql
from app.agents.table_selector import select_tables
from app.config import settings
from app.db.connection import DatabaseNotConfiguredError, run_query
from app.db.schema_catalog import ensure_catalog_loaded
from app.models.chat import ChatResponse
from app.services.export_cache import export_cache

logger = logging.getLogger("chat_orchestrator")


async def handle_message(message: str) -> ChatResponse:
    intent = await classify_intent(message)

    if intent == QueryIntent.OFF_TOPIC:
        return ChatResponse(reply=off_topic_reply(), intent=intent.value)

    if not ensure_catalog_loaded():
        return ChatResponse(
            reply=(
                "The database connection isn't configured yet, so I can't look "
                "anything up right now. Once it's connected I'll be able to answer this."
            ),
            intent=intent.value,
        )

    selection = await select_tables(message)

    if not selection.tables:
        return ChatResponse(
            reply=build_clarification(selection.tables, message),
            intent=intent.value,
        )

    sql = await generate_sql(message, selection.tables)

    rows: list[dict] = []
    sql_error = False
    try:
        validated_sql = validate_sql(sql)
        # Any virtual views (no CREATE VIEW permission — see
        # app/db/virtual_views.py) get inlined as CTEs here, then
        # re-validated before it ever reaches the DB.
        executable_sql = validate_sql(inline_virtual_views(validated_sql))
        rows = run_query(executable_sql)
    except UnsafeQueryError as e:
        logger.warning("Rejected unsafe SQL: %s | sql=%s", e, sql)
        sql_error = True
    except DatabaseNotConfiguredError:
        return ChatResponse(
            reply="The database connection isn't configured yet — I can't run this lookup.",
            intent=intent.value,
        )
    except Exception as e:
        logger.error("Query execution failed: %s | sql=%s", e, sql)
        sql_error = True

    low_confidence = selection.confidence == "low"
    empty_result = not rows

    if sql_error or (low_confidence and empty_result):
        # best-guess attempt failed or was low-confidence with nothing found -> clarify
        return ChatResponse(
            reply=build_clarification(selection.tables, message),
            intent=intent.value,
            sql=sql if not sql_error else None,
            row_count=0,
        )

    row_count = len(rows)
    export_id: str | None = None
    export_row_count: int | None = None

    if row_count > settings.excel_export_row_threshold:
        answer = await format_summary(message, rows, row_count)
        export_id = export_cache.store(rows, message)
        export_row_count = row_count
        answer = (
            f"{answer}\n\nThat's **{row_count} rows** in total — more than fits comfortably "
            "here. Want the full details? Download the complete result as an Excel file below."
        )
    else:
        answer = await format_response(message, rows)

    if low_confidence:
        answer = f"{answer}\n\n{build_clarification(selection.tables, message)}"

    return ChatResponse(
        reply=answer,
        intent=intent.value,
        sql=sql,
        row_count=row_count,
        export_id=export_id,
        export_row_count=export_row_count,
    )
