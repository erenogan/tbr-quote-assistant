from decimal import Decimal

from app.db import pool
from app.domain.validation import check_product_for_quote
from app.tools.add_to_quote import new_item_id
from app.tools.common import (
    find_replay, get_active_line, get_customer, get_product,
    lock_draft_quote, reject, save_receipt,
)
from app.tools.errors import ToolError


def replace_with_alternative(
    quote_id: str,
    from_product_id: str,
    to_product_id: str,
    quantity: int | None,
    reason: str,
    idempotency_key: str,
    source_message_id: str,
    *,
    max_price_try: Decimal | None = None,
    user_accepts_backorder: bool = False,
) -> dict:
    """Aktif satırı alternatifle değiştirir. Eski satır silinmez: 'replaced' olur
    ve replaced_by_item_id yeni satırı gösterir. quantity None ise eski miktar korunur.
    """
    if from_product_id == to_product_id:
        raise ToolError("same_product", "Ürün kendisiyle değiştirilemez.")
    if quantity is not None and quantity <= 0:
        raise ToolError("invalid_quantity", "Miktar 0'dan büyük olmalı.")

    with pool.connection() as conn:
        quote = lock_draft_quote(conn, quote_id)
        replay = find_replay(conn, idempotency_key)
        if replay:
            return replay

        old_line = get_active_line(conn, quote_id, from_product_id)
        if old_line is None:
            raise ToolError("item_not_found", f"Teklifte aktif {from_product_id} satırı yok.")
        from_product = get_product(conn, from_product_id)
        to_product = get_product(conn, to_product_id)
        customer = get_customer(conn, quote["customer_id"])

        new_quantity = quantity if quantity is not None else old_line["quantity"]  # SCN-006: 2 korunur

        # Alternatif zaten sepette aktifse ikinci aktif satır açılamaz: onun miktarını artır.
        target = get_active_line(conn, quote_id, to_product_id)
        quantity_after = (target["quantity"] if target else 0) + new_quantity

        decision = check_product_for_quote(
            to_product, customer,
            quantity=quantity_after,
            max_price=max_price_try,              # SCN-005: 9.000 TL altı
            user_accepts_backorder=user_accepts_backorder,
        )
        reject(decision)

        # Sıra önemli: önce yeni satır var olmalı, sonra eski satır onu gösterebilir (FK).
        if target:
            conn.execute(
                "UPDATE quote_items SET quantity = %s WHERE quote_item_id = %s",
                (quantity_after, target["quote_item_id"]),
            )
            new_item = target["quote_item_id"]
        else:
            new_item = new_item_id(quote_id)
            conn.execute(
                """
                INSERT INTO quote_items (quote_item_id, quote_id, product_id, quantity,
                    unit_price_try, status, source_message_id, idempotency_key, is_backorder)
                VALUES (%s, %s, %s, %s, %s, 'active', %s, %s, %s)
                """,
                (new_item, quote_id, to_product_id, new_quantity, to_product["price_try"],
                 source_message_id, idempotency_key, decision.is_backorder),
            )
        conn.execute(
            """
            UPDATE quote_items SET status = 'replaced', replaced_by_item_id = %s
            WHERE quote_item_id = %s
            """,
            (new_item, old_line["quote_item_id"]),
        )

        response = {
            "quote_id": quote_id,
            "action": "replaced",
            # PDF: mutasyon olaylarında teklif değişikliği (delta) görünmeli.
            "delta": {
                "replaced_product_id": from_product_id,
                "with_product_id": to_product_id,
                "quantity": new_quantity,
            },
            "from": {
                "quote_item_id": old_line["quote_item_id"],
                "product_id": from_product_id,
                "name_tr": from_product["name_tr"],
                "price_try": str(from_product["price_try"]),
                "stock_qty": from_product["stock_qty"],
            },
            "to": {
                "quote_item_id": new_item,
                "product_id": to_product_id,
                "name_tr": to_product["name_tr"],
                "price_try": str(to_product["price_try"]),
                "stock_qty": to_product["stock_qty"],
                "quantity": new_quantity,
            },
            # Kanıt: alternatif, ürün kaydındaki resmi muadil listesinde mi?
            "is_listed_substitute": to_product_id in from_product["substitute_product_ids"],
            "reason": reason,
            "replayed": False,
        }
        save_receipt(conn, idempotency_key, "replace_with_alternative", quote_id, response)

    return response
