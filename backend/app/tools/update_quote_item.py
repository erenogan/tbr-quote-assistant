from app.db import pool
from app.domain.validation import check_product_for_quote
from app.tools.common import (
    get_active_line, get_customer, get_product, lock_draft_quote, reject,
)
from app.tools.errors import ToolError


def update_quote_item(quote_id: str, product_id: str, quantity: int, reason: str) -> dict:
    """Aktif satırın miktarını AYARLAR (artırmaz). quantity = 0 -> satır 'removed'.

    Sözleşmede idempotency_key yok, ve buna gerek de yok: "4 yap" komutu iki kez
    çalışsa da sonuç 4'tür. Mutlak değer atayan işlemler doğası gereği idempotent.
    """
    if quantity < 0:
        raise ToolError("invalid_quantity", "Miktar negatif olamaz.")

    with pool.connection() as conn:
        quote = lock_draft_quote(conn, quote_id)
        line = get_active_line(conn, quote_id, product_id)
        if line is None:
            raise ToolError("item_not_found", f"Teklifte aktif {product_id} satırı yok.")
        quantity_before = line["quantity"]

        if quantity == 0:
            # Silme yok, işaretleme var. Eski miktar geçmiş olarak satırda kalır.
            conn.execute(
                "UPDATE quote_items SET status = 'removed' WHERE quote_item_id = %s",
                (line["quote_item_id"],),
            )
            action = "removed"
        else:
            # Sadece ARTIŞTA kural kontrolü: stok sonradan düştüyse bile
            # kullanıcının miktarı AZALTMASI engellenmemeli.
            if quantity > quantity_before:
                decision = check_product_for_quote(
                    get_product(conn, product_id),
                    get_customer(conn, quote["customer_id"]),
                    quantity=quantity,
                    # Fiyat limiti yok: ürün değişmiyor  fiyat eklenirken kabul edildi.
                    # Bekleyen satırda bekleyebilirim zaten eklenirken kabul edildi.
                    user_accepts_backorder=line["is_backorder"],
                )
                reject(decision)
            conn.execute(
                "UPDATE quote_items SET quantity = %s WHERE quote_item_id = %s",
                (quantity, line["quote_item_id"]),
            )
            action = "updated"

    return {
        "quote_id": quote_id,
        "quote_item_id": line["quote_item_id"],
        "product_id": product_id,
        "action": action,
        "delta": {"quantity_before": quantity_before, "quantity_after": quantity},
        "reason": reason,
    }