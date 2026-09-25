from app.db import pool
from app.domain.pricing import price_quote
from app.tools.errors import ToolError


def get_quote(quote_id: str) -> dict:
    with pool.connection() as conn:
        quote = conn.execute(
            "SELECT * FROM quotes WHERE quote_id = %s", (quote_id,)
        ).fetchone()
        if quote is None:
            raise ToolError("quote_not_found", f"{quote_id} numaralı teklif bulunamadı.")

        customer = conn.execute(
            "SELECT * FROM customers WHERE customer_id = %s", (quote["customer_id"],)
        ).fetchone()
        # Aktif satırlar önce; pasifler (replaced/removed) de listelenir ki web gösterebilsin.
        lines = conn.execute(
            """
            SELECT * FROM quote_items
            WHERE quote_id = %s
            ORDER BY status = 'active' DESC, quote_item_id
            """,
            (quote_id,),
        ).fetchall()
        product_ids = list({l["product_id"] for l in lines})
        products = {
            p["product_id"]: p
            for p in conn.execute(
                "SELECT * FROM products WHERE product_id = ANY(%s)", (product_ids,)
            ).fetchall()
        }
        rule_percents = {
            r["rule_id"]: r["discount_percent"]
            for r in conn.execute("SELECT rule_id, discount_percent FROM price_rules").fetchall()
        }

    priced = price_quote(lines, products, customer, rule_percents)
    return {
        "quote_id": quote["quote_id"],
        "status": quote["status"],
        "currency": quote["currency"],
        "customer": {
            "customer_id": customer["customer_id"],
            "name": customer["name"],
            "price_tier": customer["price_tier"],
            "allow_backorder": customer["allow_backorder"],
        },
        **priced,
    }