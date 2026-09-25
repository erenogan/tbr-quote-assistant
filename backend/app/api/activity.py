"""Sohbet oturumları ve tool-call logları (web panelinde robotun ne yaptığını izlemek için)."""
from fastapi import APIRouter, Query

from app.db import pool

router = APIRouter(tags=["activity"])


@router.get("/sessions")
def list_sessions():
    with pool.connection() as conn:
        return conn.execute(
            """
            SELECT s.session_id, s.quote_id, s.channel, s.created_at,
                   count(m.*) AS message_count, max(m.created_at) AS last_message_at
            FROM chat_sessions s
            LEFT JOIN chat_messages m ON m.session_id = s.session_id
            GROUP BY s.session_id
            ORDER BY last_message_at DESC NULLS LAST
            """
        ).fetchall()


@router.get("/sessions/{session_id}/messages")
def session_messages(session_id: str):
    with pool.connection() as conn:
        return conn.execute(
            "SELECT * FROM chat_messages WHERE session_id = %s ORDER BY created_at, message_id",
            (session_id,),
        ).fetchall()


@router.get("/logs")
def list_logs(session_id: str | None = None, message_id: str | None = None,
              status: str | None = None, limit: int = Query(100, le=500)):
    filters, params = [], []
    for column, value in (("session_id", session_id), ("message_id", message_id), ("status", status)):
        if value:
            filters.append(f"{column} = %s")
            params.append(value)
    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    with pool.connection() as conn:
        return conn.execute(
            f"SELECT * FROM tool_call_logs {where} ORDER BY id DESC LIMIT %s", (*params, limit)
        ).fetchall()
