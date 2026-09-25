import json
import uuid
from decimal import Decimal

from psycopg.types.json import Jsonb

from app.db import pool
from app.domain.validation import check_product_for_quote
from app.tools.errors import ToolError

# Kullanıcıya dönecek Türkçe mesajlar (sebep kodu -> mesaj)
REJECT_MESSAGES = {
    "inactive": "Bu ürün şu anda satışta değil.",
    "price_limit": "Ürün fiyatı belirttiğiniz üst limitin üzerinde.",
    "out_of_stock": "Ürün stokta yok. Bekleyebilirseniz belirtin; stoklu alternatif de önerebilirim.",
    "backorder_not_allowed": "Ürün stokta yok ve bu müşteri için bekleyen sipariş açılamıyor.",
    "insufficient_stock": "Stokta istenen miktar kadar ürün yok.",
}


def _jsonb(data: dict) -> Jsonb:
    # Decimal gibi JSON'un bilmediği tipleri metne çevirerek yaz.
    return Jsonb(data, dumps=lambda d: json.dumps(d, default=str))


def add_to_quote(
    quote_id: str,
    product_id: str,
    quantity: int,
    idempotency_key: str,
    source_message_id: str,
    *,
    max_price_try: Decimal | None = None,
    user_accepts_backorder: bool = False,
) -> dict:
    """Ürünü teklife ekler; aynı ürün aktifse miktarı artırır.

    max_price_try ve user_accepts_backorder sözleşmede yok: router bunları
    kullanıcının mesajından çıkarıp BAĞLAM olarak verir (LLM'e bırakılmaz).
    """
    if quantity <= 0:
        raise ToolError("invalid_quantity", "Miktar 0'dan büyük olmalı.")

    
    with pool.connection() as conn:
        
        quote = conn.execute(
            "SELECT * FROM quotes WHERE quote_id = %s FOR UPDATE", (quote_id,)
        ).fetchone()
        if quote is None:
            raise ToolError("quote_not_found", f"{quote_id} numaralı teklif bulunamadı.")
        if quote["status"] != "draft":
            raise ToolError("quote_not_editable", "Sadece taslak teklifler değiştirilebilir.")

        
        previous = conn.execute(
            "SELECT response FROM idempotency_keys WHERE idempotency_key = %s",
            (idempotency_key,),
        ).fetchone()
        if previous is not None:
            return {**previous["response"], "replayed": True}

        
        product = conn.execute(
            "SELECT * FROM products WHERE product_id = %s", (product_id,)
        ).fetchone()
        if product is None:
            raise ToolError("product_not_found", f"{product_id} ürünü bulunamadı.")
        customer = conn.execute(
            "SELECT * FROM customers WHERE customer_id = %s", (quote["customer_id"],)
        ).fetchone()
        existing = conn.execute(
            """
            SELECT * FROM quote_items
            WHERE quote_id = %s AND product_id = %s AND status = 'active'
            """,
            (quote_id, product_id),
        ).fetchone()

        quantity_before = existing["quantity"] if existing else 0
        quantity_after = quantity_before + quantity

        
        decision = check_product_for_quote(
            product,
            customer,
            quantity=quantity_after,
            max_price=max_price_try,
            user_accepts_backorder=user_accepts_backorder,
        )
        if not decision.allowed:
            
            raise ToolError(decision.reason, REJECT_MESSAGES[decision.reason])

        
        if existing:
            conn.execute(
                "UPDATE quote_items SET quantity = %s WHERE quote_item_id = %s",
                (quantity_after, existing["quote_item_id"]),
            )
            quote_item_id, action = existing["quote_item_id"], "incremented"
        else:
            quote_item_id = f"QI-{quote_id.removeprefix('Q-')}-{uuid.uuid4().hex[:8]}"
            conn.execute(
                """
                INSERT INTO quote_items (quote_item_id, quote_id, product_id, quantity,
                    unit_price_try, status, source_message_id, idempotency_key, is_backorder)
                VALUES (%s, %s, %s, %s, %s, 'active', %s, %s, %s)
                """,
                (quote_item_id, quote_id, product_id, quantity,
                 product["price_try"],  # fiyat snapshot'ı
                 source_message_id, idempotency_key, decision.is_backorder),
            )
            action = "inserted"

        response = {
            "quote_id": quote_id,
            "quote_item_id": quote_item_id,
            "product_id": product_id,
            "action": action,
            "delta": {"quantity_before": quantity_before, "quantity_after": quantity_after},
            "is_backorder": decision.is_backorder,
            "unit_price_try": str(product["price_try"]),
            "replayed": False,
        }

    
        conn.execute(
            """
            INSERT INTO idempotency_keys (idempotency_key, tool_name, quote_id, response)
            VALUES (%s, 'add_to_quote', %s, %s)
            """,
            (idempotency_key, quote_id, _jsonb(response)),
        )

    return response