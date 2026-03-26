"""Pipeline checkpoint persistence — save/restore run state to survive restarts."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

logger = logging.getLogger(__name__)

# We store checkpoints in a dedicated lightweight table.  To avoid adding a new
# SQLAlchemy model to apf-db (which would require a migration) we use a raw DDL
# table that we create on first use.

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS pipeline_checkpoints (
    pipeline_id TEXT PRIMARY KEY,
    state       TEXT NOT NULL,
    saved_at    TEXT NOT NULL
)
"""


async def _ensure_table(engine: AsyncEngine) -> None:
    """Create the checkpoints table if it does not already exist."""
    async with engine.begin() as conn:
        await conn.execute(text(_CREATE_TABLE_SQL))


async def save_checkpoint(
    engine: AsyncEngine,
    pipeline_id: str,
    stage_name: str,
    state: dict[str, Any],
) -> None:
    """Persist *state* for *pipeline_id* / *stage_name*.

    Overwrites any previously stored checkpoint for this pipeline.
    """
    await _ensure_table(engine)
    payload = json.dumps(
        {
            "stage_name": stage_name,
            "state": state,
        }
    )
    saved_at = datetime.now(tz=timezone.utc).isoformat()

    async with engine.begin() as conn:
        # Upsert — works for both SQLite and PostgreSQL (via INSERT OR REPLACE)
        await conn.execute(
            text(
                "INSERT INTO pipeline_checkpoints (pipeline_id, state, saved_at) "
                "VALUES (:pid, :state, :saved_at) "
                "ON CONFLICT(pipeline_id) DO UPDATE SET state = :state, saved_at = :saved_at"
            ),
            {"pid": pipeline_id, "state": payload, "saved_at": saved_at},
        )
    logger.debug("Checkpoint saved for pipeline %s at stage %s", pipeline_id, stage_name)


async def load_checkpoint(
    engine: AsyncEngine,
    pipeline_id: str,
) -> dict[str, Any] | None:
    """Return the last saved checkpoint for *pipeline_id*, or *None* if none exists."""
    await _ensure_table(engine)
    async with engine.connect() as conn:
        row = await conn.execute(
            text(
                "SELECT state FROM pipeline_checkpoints WHERE pipeline_id = :pid"
            ),
            {"pid": pipeline_id},
        )
        result = row.fetchone()

    if result is None:
        return None

    try:
        data = json.loads(result[0])
    except (json.JSONDecodeError, TypeError):
        logger.warning("Corrupt checkpoint data for pipeline %s — ignoring", pipeline_id)
        return None

    logger.debug("Checkpoint loaded for pipeline %s", pipeline_id)
    return data


async def delete_checkpoint(engine: AsyncEngine, pipeline_id: str) -> None:
    """Remove the checkpoint for *pipeline_id* (e.g. after the pipeline completes)."""
    await _ensure_table(engine)
    async with engine.begin() as conn:
        await conn.execute(
            text("DELETE FROM pipeline_checkpoints WHERE pipeline_id = :pid"),
            {"pid": pipeline_id},
        )
    logger.debug("Checkpoint deleted for pipeline %s", pipeline_id)
