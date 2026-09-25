from decimal import Decimal

import pytest

from app.db import pool
from app.tools.add_to_quote import add_to_quote
from app.tools.errors import ToolError
from app.tools.get_quote import get_quote


def active_lines(quote_id, product_id):
    return [
        l for l in get_quote(quote_id)["lines"]
        if l["product_id"] == product_id and l["status"] == "active"
    ]


def add(quote_id, product_id, quantity, key, **context):
    return add_to_quote(quote_id, product_id, quantity, key, "msg-test", **context)


def test_adds_new_line_scn001():
    result = add("Q-1002", "PRD-BC-110", 1, "k1", max_price_try=Decimal(9000))
    assert result["action"] == "inserted"
    lines = active_lines("Q-1002", "PRD-BC-110")
    assert len(lines) == 1 and lines[0]["quantity"] == 1


def test_readding_increments_instead_of_new_line_scn003():
    # Q-1001'de zaten 1 adet var.
    result = add("Q-1001", "PRD-BC-110", 2, "k1")
    assert result["action"] == "incremented"
    assert result["delta"] == {"quantity_before": 1, "quantity_after": 3}
    lines = active_lines("Q-1001", "PRD-BC-110")
    assert len(lines) == 1 and lines[0]["quantity"] == 3


def test_same_key_twice_increments_once_scn010():
    first = add("Q-1001", "PRD-BC-110", 1, "same-key")
    second = add("Q-1001", "PRD-BC-110", 1, "same-key")  # ağ kopması, tekrar gönderim
    assert second["replayed"] is True
    assert second["delta"] == first["delta"]
    assert active_lines("Q-1001", "PRD-BC-110")[0]["quantity"] == 2  # 1 + 1, 1 + 2 değil


def test_different_keys_increment_twice():
    # Kullanıcı iki AYRI mesajda "1 tane daha" dedi: iki kez artmalı.
    add("Q-1001", "PRD-BC-110", 1, "key-a")
    add("Q-1001", "PRD-BC-110", 1, "key-b")
    assert active_lines("Q-1001", "PRD-BC-110")[0]["quantity"] == 3


def test_price_limit_rejects_and_writes_nothing():
    with pytest.raises(ToolError) as exc:
        add("Q-1002", "PRD-BC-120", 1, "k1", max_price_try=Decimal(9000))
    assert exc.value.code == "price_limit"
    assert active_lines("Q-1002", "PRD-BC-120") == []


def test_backorder_not_allowed_for_customer_scn002():
    # CUST-IST-001: allow_backorder = false. Kullanıcı kabul etse bile olmaz.
    with pytest.raises(ToolError) as exc:
        add("Q-1001", "PRD-BC-130", 1, "k1", user_accepts_backorder=True)
    assert exc.value.code == "backorder_not_allowed"
    assert active_lines("Q-1001", "PRD-BC-130") == []


def test_out_of_stock_without_user_consent():
    # CUST-ANK-002 izin veriyor ama kullanıcı "bekleyebilirim" demedi.
    with pytest.raises(ToolError) as exc:
        add("Q-1002", "PRD-BC-130", 1, "k1")
    assert exc.value.code == "out_of_stock"


def test_backorder_line_when_both_conditions_met():
    result = add("Q-1002", "PRD-BC-130", 1, "k1", user_accepts_backorder=True)
    assert result["is_backorder"] is True
    assert active_lines("Q-1002", "PRD-BC-130")[0]["is_backorder"] is True


def test_stock_checked_on_total_line_quantity():
    # Yedek batarya stoğu 2: önce 2 eklenir, sonra +1 toplam 3 > 2 olur.
    add("Q-1002", "PRD-ACC-720", 2, "k1")
    with pytest.raises(ToolError) as exc:
        add("Q-1002", "PRD-ACC-720", 1, "k2")
    assert exc.value.code == "insufficient_stock"
    assert active_lines("Q-1002", "PRD-ACC-720")[0]["quantity"] == 2


def test_price_snapshot_is_stored():
    add("Q-1002", "PRD-BC-110", 1, "k1")
    with pool.connection() as conn:
        conn.execute("UPDATE products SET price_try = 9999 WHERE product_id = 'PRD-BC-110'")
    # Ürün fiyatı değişti, teklif satırı eski fiyatı korumalı.
    assert active_lines("Q-1002", "PRD-BC-110")[0]["unit_price_try"] == Decimal("7990.00")


def test_idempotency_record_is_saved():
    add("Q-1002", "PRD-BC-110", 1, "k-record")
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT tool_name, quote_id FROM idempotency_keys WHERE idempotency_key = 'k-record'"
        ).fetchone()
    assert row == {"tool_name": "add_to_quote", "quote_id": "Q-1002"}


@pytest.mark.parametrize("quote_id,product_id,qty,code", [
    ("Q-9999", "PRD-BC-110", 1, "quote_not_found"),
    ("Q-1002", "PRD-YOK-000", 1, "product_not_found"),
    ("Q-1002", "PRD-BC-110", 0, "invalid_quantity"),
])
def test_invalid_requests(quote_id, product_id, qty, code):
    with pytest.raises(ToolError) as exc:
        add(quote_id, product_id, qty, "k1")
    assert exc.value.code == code