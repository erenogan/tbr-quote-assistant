from decimal import Decimal

import pytest

from app.db import pool
from app.domain.pricing import RULE_IDS
from app.tools.errors import ToolError
from app.tools.get_quote import get_quote


def insert_line(quote_id, product_id, quantity, status="active"):
    """Test için teklife satır ekler (fiyat snapshot'ı ürünün güncel fiyatından)."""
    with pool.connection() as conn:
        price = conn.execute(
            "SELECT price_try FROM products WHERE product_id = %s", (product_id,)
        ).fetchone()["price_try"]
        conn.execute(
            """
            INSERT INTO quote_items (quote_item_id, quote_id, product_id, quantity,
                                     unit_price_try, status, source_message_id, idempotency_key)
            VALUES (%s, %s, %s, %s, %s, %s, 'test', %s)
            """,
            (f"T-{quote_id}-{product_id}", quote_id, product_id, quantity, price, status,
             f"test-{quote_id}-{product_id}"),
        )


def update_line(quote_item_id, **fields):
    sets = ", ".join(f"{k} = %s" for k in fields)
    with pool.connection() as conn:
        conn.execute(f"UPDATE quote_items SET {sets} WHERE quote_item_id = %s",
                     (*fields.values(), quote_item_id))


def line_for(quote, product_id):
    return next(l for l in quote["lines"] if l["product_id"] == product_id)


def test_seed_quote_totals():
    quote = get_quote("Q-1001")
    assert len(quote["lines"]) == 1
    assert quote["total_try"] == Decimal("7990.00")
    assert quote["customer"]["allow_backorder"] is False


def test_partner_category_discount_scn011():
    insert_line("Q-1002", "PRD-BC-110", 3)  # partner müşteri
    line = line_for(get_quote("Q-1002"), "PRD-BC-110")
    assert line["applied_rules"] == ["RUL-PARTNER-3"]
    assert line["discount_try"] == Decimal("1677.90")


def test_standard_customer_gets_no_partner_discount():
    insert_line("Q-1003", "PRD-BC-110", 3)  # standart müşteri
    assert line_for(get_quote("Q-1003"), "PRD-BC-110")["applied_rules"] == []


def test_plus_discount_visible_scn019():
    update_line("QI-2001-1", quantity=4)
    line = line_for(get_quote("Q-2001"), "PRD-BC-110-PLUS")
    assert "RUL-PLUS-QTY" in line["applied_rules"]
    assert line["discount_percent"] == Decimal(13)  # %7 partner + %6 Plus


def test_bundle_blocks_other_discounts():
    insert_line("Q-2002", "PRD-KIT-610-PLUS", 4)  # hem kit hem Plus
    line = line_for(get_quote("Q-2002"), "PRD-KIT-610-PLUS")
    assert line["applied_rules"] == ["RUL-BUNDLE-NO-STACK"]
    assert line["discount_try"] == Decimal("0.00")


def test_inactive_lines_listed_but_not_totaled():
    update_line("QI-1004-1", status="replaced")
    quote = get_quote("Q-1004")
    assert quote["lines"][0]["included_in_total"] is False
    assert quote["total_try"] == Decimal(0)


def test_unknown_quote_raises_tool_error():
    with pytest.raises(ToolError) as exc:
        get_quote("Q-9999")
    assert exc.value.code == "quote_not_found"


def test_all_rule_ids_exist_in_db():
    # Koddaki kural id'leri DB'deki price_rules ile uyumlu olmalı.
    with pool.connection() as conn:
        db_ids = {r["rule_id"] for r in conn.execute("SELECT rule_id FROM price_rules")}
    assert RULE_IDS == db_ids