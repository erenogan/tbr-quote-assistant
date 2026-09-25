"""Teklif okuma. Web ve mobil AYNI fonksiyonu (get_quote) kullanır: tek doğruluk kaynağı.

Not: Bu okumalar turnikeden (registry) geçmez. Web 2 sn'de bir sorar (polling);
loglara yazılsaydı asistanın gerçek adımları bu kalabalıkta kaybolurdu.
Loglar ASİSTANIN ne yaptığını göstermek için var.
"""
from fastapi import APIRouter, HTTPException

from app.db import pool
from app.tools.errors import ToolError
from app.tools.get_quote import get_quote

router = APIRouter(prefix="/quotes", tags=["quotes"])


@router.get("")
def list_quotes():
    with pool.connection() as conn:
        return conn.execute(
            """
            SELECT q.quote_id, q.status, q.created_by_channel, c.name AS customer_name,
                   c.price_tier, c.allow_backorder,
                   count(i.*) FILTER (WHERE i.status = 'active') AS active_lines
            FROM quotes q
            JOIN customers c ON c.customer_id = q.customer_id
            LEFT JOIN quote_items i ON i.quote_id = q.quote_id
            GROUP BY q.quote_id, c.customer_id
            ORDER BY q.quote_id
            """
        ).fetchall()


@router.get("/{quote_id}")
def read_quote(quote_id: str):
    try:
        return get_quote(quote_id)
    except ToolError as e:
        raise HTTPException(status_code=404, detail=e.message)
