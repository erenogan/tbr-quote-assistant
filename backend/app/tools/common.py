"""Mutasyon tool'larının ortak adımları: kilit, fiş defteri, kayıt okuma.

add, update ve replace aynı kalıbı izliyor; kalıbı tek yerde tutuyoruz ki
üç tool'da üç farklı (ve zamanla farklılaşan) kopya olmasın.
"""
import json

from psycopg.types.json import Jsonb

from app.tools.errors import ToolError

REJECT_MESSAGES = {
    "inactive": "Bu ürün şu anda satışta değil.",
    "price_limit": "Ürün fiyatı belirttiğiniz üst limitin üzerinde.",
    "out_of_stock": "Ürün stokta yok. Bekleyebilirseniz belirtin; stoklu alternatif de önerebilirim.",
    "backorder_not_allowed": "Ürün stokta yok ve bu müşteri için bekleyen sipariş açılamıyor.",
    "insufficient_stock": "Stokta istenen miktar kadar ürün yok.",
}


def to_jsonb(data: dict) -> Jsonb:
    # Decimal gibi JSON'un bilmediği tipleri metne çevirerek yaz.
    return Jsonb(data, dumps=lambda d: json.dumps(d, default=str))


def lock_draft_quote(conn, quote_id: str) -> dict:
    """Teklifi kilitler. Aynı teklife gelen diğer mutasyonlar transaction bitene kadar bekler."""
    quote = conn.execute(
        "SELECT * FROM quotes WHERE quote_id = %s FOR UPDATE", (quote_id,)
    ).fetchone()
    if quote is None:
        raise ToolError("quote_not_found", f"{quote_id} numaralı teklif bulunamadı.")
    if quote["status"] != "draft":
        raise ToolError("quote_not_editable", "Sadece taslak teklifler değiştirilebilir.")
    return quote


def find_replay(conn, idempotency_key: str) -> dict | None:
    """Bu fiş daha önce işlendiyse ilk cevabı döner. KİLİTTEN SONRA çağrılmalı."""
    row = conn.execute(
        "SELECT response FROM idempotency_keys WHERE idempotency_key = %s",
        (idempotency_key,),
    ).fetchone()
    return {**row["response"], "replayed": True} if row else None


def save_receipt(conn, idempotency_key: str, tool_name: str, quote_id: str, response: dict):
    """Fişi mutasyonla AYNI transaction'da kaydeder."""
    conn.execute(
        """
        INSERT INTO idempotency_keys (idempotency_key, tool_name, quote_id, response)
        VALUES (%s, %s, %s, %s)
        """,
        (idempotency_key, tool_name, quote_id, to_jsonb(response)),
    )


def get_product(conn, product_id: str) -> dict:
    product = conn.execute(
        "SELECT * FROM products WHERE product_id = %s", (product_id,)
    ).fetchone()
    if product is None:
        raise ToolError("product_not_found", f"{product_id} ürünü bulunamadı.")
    return product


def get_customer(conn, customer_id: str) -> dict:
    return conn.execute(
        "SELECT * FROM customers WHERE customer_id = %s", (customer_id,)
    ).fetchone()


def get_active_line(conn, quote_id: str, product_id: str) -> dict | None:
    return conn.execute(
        """
        SELECT * FROM quote_items
        WHERE quote_id = %s AND product_id = %s AND status = 'active'
        """,
        (quote_id, product_id),
    ).fetchone()


def reject(decision):
    """Kural reddettiyse kontrollü hata fırlatır (with bloğu ROLLBACK yapar)."""
    if not decision.allowed:
        raise ToolError(decision.reason, REJECT_MESSAGES[decision.reason])