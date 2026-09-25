import pytest

from app.db import pool
from app.tools.add_to_quote import add_to_quote
from app.tools.errors import ToolError
from app.tools.get_quote import get_quote
from app.tools.update_quote_item import update_quote_item


def line(quote_id, product_id):
    return next(l for l in get_quote(quote_id)["lines"] if l["product_id"] == product_id)


def test_sets_quantity_scn004():
    # "4 adede çıkar": 2'den 4'e AYARLA (2 + 4 = 6 değil).
    result = update_quote_item("Q-1003", "PRD-PRN-320", 4, "kullanıcı isteği")
    assert result["delta"] == {"quantity_before": 2, "quantity_after": 4}
    assert line("Q-1003", "PRD-PRN-320")["quantity"] == 4


def test_service_quantity_scn015():
    update_quote_item("Q-2005", "PRD-SVC-810", 2, "2 lokasyon")
    assert line("Q-2005", "PRD-SVC-810")["quantity"] == 2


def test_same_update_twice_is_naturally_idempotent():
    update_quote_item("Q-1003", "PRD-PRN-320", 4, "ilk")
    update_quote_item("Q-1003", "PRD-PRN-320", 4, "tekrar")
    assert line("Q-1003", "PRD-PRN-320")["quantity"] == 4


def test_zero_marks_removed_not_deleted():
    update_quote_item("Q-1003", "PRD-PRN-320", 0, "çıkar")
    removed = line("Q-1003", "PRD-PRN-320")
    assert removed["status"] == "removed"
    assert removed["included_in_total"] is False


def test_removed_product_can_be_added_again():
    # Partial index sayesinde: removed satır, yeni aktif satırı engellemez.
    update_quote_item("Q-1003", "PRD-PRN-320", 0, "çıkar")
    add_to_quote("Q-1003", "PRD-PRN-320", 1, "k1", "msg")
    statuses = sorted(l["status"] for l in get_quote("Q-1003")["lines"])
    assert statuses == ["active", "removed"]


def test_increase_beyond_stock_rejected():
    # PRD-PRN-320 stoğu 6.
    with pytest.raises(ToolError) as exc:
        update_quote_item("Q-1003", "PRD-PRN-320", 7, "fazla")
    assert exc.value.code == "insufficient_stock"
    assert line("Q-1003", "PRD-PRN-320")["quantity"] == 2


def test_decrease_allowed_even_if_stock_dropped():
    with pool.connection() as conn:
        conn.execute("UPDATE products SET stock_qty = 0 WHERE product_id = 'PRD-PRN-320'")
    update_quote_item("Q-1003", "PRD-PRN-320", 1, "azalt")
    assert line("Q-1003", "PRD-PRN-320")["quantity"] == 1


def test_missing_line_raises():
    with pytest.raises(ToolError) as exc:
        update_quote_item("Q-1003", "PRD-BC-110", 3, "yok")
    assert exc.value.code == "item_not_found"