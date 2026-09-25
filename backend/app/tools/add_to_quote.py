import uuid
from decimal import Decimal

from app.db import pool
from app.domain.validation import check_product_for_quote
from app.tools.common import (
    find_replay, get_active_line, get_customer, get_product,
    lock_draft_quote, reject, save_receipt,
)
from app.tools.errors import ToolError


def new_item_id(quote_id: str) -> str:
    return f"QI-{quote_id.removeprefix('Q-')}-{uuid.uuid4().hex[:8]}"


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

    with pool.connection() as conn:                      # tek transaction
        quote = lock_draft_quote(conn, quote_id)         # 1. kilit
        replay = find_replay(conn, idempotency_key)      # 2. fiş kontrolü (kilitten sonra)
        if replay:
            return replay

        product = get_product(conn, product_id)          # 3. oku
        customer = get_customer(conn, quote["customer_id"])
        existing = get_active_line(conn, quote_id, product_id)
        quantity_before = existing["quantity"] if existing else 0
        quantity_after = quantity_before + quantity

        decision = check_product_for_quote(              # 4. kurallar (TOPLAM miktar)
            product, customer,
            quantity=quantity_after,
            max_price=max_price_try,
            user_accepts_backorder=user_accepts_backorder,
        )
        reject(decision)

        if existing:                                     # 5. yaz
            conn.execute(
                "UPDATE quote_items SET quantity = %s WHERE quote_item_id = %s",
                (quantity_after, existing["quote_item_id"]),
            )
            quote_item_id, action = existing["quote_item_id"], "incremented"
        else:
            quote_item_id = new_item_id(quote_id)
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
        save_receipt(conn, idempotency_key, "add_to_quote", quote_id, response)  # 6. fiş

    return response