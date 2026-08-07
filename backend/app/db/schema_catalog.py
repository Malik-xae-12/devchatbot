"""
Schema catalog: builds a lightweight index of tables/columns from
INFORMATION_SCHEMA so the SQL-generation agent can look up only the
tables relevant to a given question, instead of loading a 30-50 table
schema into every prompt.

Call refresh_catalog() once at startup (or via an admin endpoint) after
the DB is configured. Until then, this returns an empty catalog and the
agents fall back to their "DB not configured" response.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.db.connection import run_query, DatabaseNotConfiguredError
from app.db.virtual_views import VIRTUAL_VIEWS

_TABLES_QUERY = """
SELECT
    t.TABLE_SCHEMA AS table_schema,
    t.TABLE_NAME AS table_name,
    t.TABLE_TYPE AS table_type,
    c.COLUMN_NAME AS column_name,
    c.DATA_TYPE AS data_type,
    c.IS_NULLABLE AS is_nullable
FROM INFORMATION_SCHEMA.TABLES t
JOIN INFORMATION_SCHEMA.COLUMNS c
    ON t.TABLE_NAME = c.TABLE_NAME AND t.TABLE_SCHEMA = c.TABLE_SCHEMA
WHERE t.TABLE_TYPE IN ('BASE TABLE', 'VIEW')
ORDER BY t.TABLE_SCHEMA, t.TABLE_NAME, c.ORDINAL_POSITION
"""

# Manual business-context descriptions, keyed by "schema.table_or_view_name",
# for REAL tables/views that do exist in INFORMATION_SCHEMA. (Views we can't
# create — no CREATE VIEW permission — live in app/db/virtual_views.py
# instead, and get merged into the catalog separately; see refresh() below.)
KNOWN_DESCRIPTIONS: dict[str, str] = {}


@dataclass
class ColumnInfo:
    name: str
    data_type: str
    nullable: bool


@dataclass
class TableInfo:
    schema: str
    name: str
    columns: list[ColumnInfo] = field(default_factory=list)
    description: str = ""  # optional: fill in manually for business context
    is_virtual: bool = False  # True = not a real DB object, see virtual_views.py

    @property
    def full_name(self) -> str:
        return f"{self.schema}.{self.name}"

    def summary(self) -> str:
        # Show more columns for wider tables/views (e.g. the 37-column
        # project/budget view) so the table-selector agent actually sees
        # relevant column names instead of just the first few and guessing
        # "low confidence" on anything past that cutoff.
        limit = 25
        cols = ", ".join(c.name for c in self.columns[:limit])
        more = f" (+{len(self.columns) - limit} more)" if len(self.columns) > limit else ""
        desc = f" — {self.description}" if self.description else ""
        return f"{self.full_name}: {cols}{more}{desc}"


class SchemaCatalog:
    def __init__(self) -> None:
        self._tables: dict[str, TableInfo] = {}

    @property
    def is_loaded(self) -> bool:
        return bool(self._tables)

    def refresh(self) -> None:
        rows = run_query(_TABLES_QUERY)
        tables: dict[str, TableInfo] = {}
        for row in rows:
            key = f"{row['table_schema']}.{row['table_name']}"
            if key not in tables:
                tables[key] = TableInfo(
                    schema=row["table_schema"],
                    name=row["table_name"],
                    description=KNOWN_DESCRIPTIONS.get(key, ""),
                )
            tables[key].columns.append(
                ColumnInfo(
                    name=row["column_name"],
                    data_type=row["data_type"],
                    nullable=row["is_nullable"] == "YES",
                )
            )

        # Merge in virtual views (defined in code, not real DB objects —
        # see app/db/virtual_views.py) so the table-selector/SQL-generation
        # agents can pick them the same way as any real table/view.
        for key, vv in VIRTUAL_VIEWS.items():
            tables[key] = TableInfo(
                schema=vv.schema,
                name=vv.name,
                description=vv.description,
                is_virtual=True,
                columns=[ColumnInfo(name=c, data_type="", nullable=True) for c in vv.columns],
            )

        self._tables = tables

    def all_tables(self) -> list[TableInfo]:
        return list(self._tables.values())

    def get_table(self, full_name: str) -> TableInfo | None:
        return self._tables.get(full_name)

    def catalog_summary_text(self) -> str:
        """A compact listing (table + top columns) suitable for a table-selection prompt."""
        return "\n".join(t.summary() for t in self._tables.values())

    def detailed_schema_text(self, table_names: list[str]) -> str:
        """Full column detail for a specific set of tables, for the SQL-generation prompt."""
        parts = []
        for name in table_names:
            table = self._tables.get(name)
            if not table:
                continue
            cols = "\n".join(
                f"  - {c.name}" + (f" ({c.data_type}{', nullable' if c.nullable else ''})" if c.data_type else "")
                for c in table.columns
            )
            parts.append(f"{table.full_name}\n{cols}")
        return "\n\n".join(parts)


catalog = SchemaCatalog()


def ensure_catalog_loaded() -> bool:
    """Attempt to load the catalog if not already loaded. Returns True if loaded."""
    if catalog.is_loaded:
        return True
    try:
        catalog.refresh()
        return catalog.is_loaded
    except DatabaseNotConfiguredError:
        return False


def force_refresh() -> bool:
    """Reload the catalog from the DB right now, even if already loaded.

    The catalog is a process-level singleton (see `catalog = SchemaCatalog()`
    above) that normally loads once and stays cached for the life of the
    process — so code changes to KNOWN_DESCRIPTIONS / VIRTUAL_VIEWS won't show
    up until either the process restarts, or this is called (see the
    /api/health/refresh-catalog route).
    """
    try:
        catalog.refresh()
        return catalog.is_loaded
    except DatabaseNotConfiguredError:
        return False
