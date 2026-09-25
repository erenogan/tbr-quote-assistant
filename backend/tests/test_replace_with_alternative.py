from decimal import Decimal

import pytest

from app.tools.add_to_quote import add_to_quote
from app.tools.errors import ToolError
from app.tools.get_quote import get_quote
from app.tools.replace_with_alternative import replace_with_alternative


def lines_by_product(quote_id):
    return {l["product_id"]: l for l in get_quote(quote_id)["lines"]}


def replace(quote_id, from_id, to_id, key="k1", quantity=None, **context):
    return replace_with_alternative(quote_id, from_id, to_id, quantity, "test", key, "msg", **context)


def test_expensive_to_cheaper_scn005():
    result = replace("Q-1004", "PRD-BC-120", "PRD-BC-110", max_price_try=Decimal(9000))
    lines = lines_by_product("Q-1004")
    assert lines["PRD-BC-120"]["status"] == "replaced"
    assert lines["PRD-BC-120"]["replaced_by_item_id"] == result["to"]["quote_item_id"]
    assert lines["PRD-BC-110"]["status"] == "active"
    assert lines["PRD-BC-110"]["quantity"] == 1


def test_keeps_quantity_scn006():
    replace("Q-1005", "PRD-BC-130", "PRD-BC-140")
    lines = lines_by_product("Q-1005")
    assert lines["PRD-BC-140"]["quantity"] == 2  # eski satırdaki miktar korundu
    assert lines["PRD-BC-130"]["status"] == "replaced"


def test_mobile_printer_to_ethernet_scn014():
    result = replace("Q-2004", "PRD-PRN-330", "PRD-PRN-320")
    assert result["is_listed_substitute"] is True
    lines = lines_by_product("Q-2004")
    assert lines["PRD-PRN-330"]["status"] == "replaced"
    assert lines["PRD-PRN-320"]["quantity"] == 1


def test_only_one_active_equivalent_remains():
    # Sözleşme: iki aktif muadil bırakılmamalı.
    replace("Q-1004", "PRD-BC-120", "PRD-BC-110")
    active = [l for l in get_quote("Q-1004")["lines"] if l["status"] == "active"]
    assert [l["product_id"] for l in active] == ["PRD-BC-110"]


def test_alternative_over_price_limit_rejected():
    with pytest.raises(ToolError) as exc:
        replace("Q-1005", "PRD-BC-130", "PRD-BC-120", max_price_try=Decimal(9000))
    assert exc.value.code == "price_limit"
    assert lines_by_product("Q-1005")["PRD-BC-130"]["status"] == "active"  # hiçbir şey değişmedi


def test_out_of_stock_alternative_rejected():
    # Stokta olan ürünü stoksuzla değiştirmek: PRN-320 -> PRN-330 (stok 0)
    with pytest.raises(ToolError) as exc:
        replace("Q-1003", "PRD-PRN-320", "PRD-PRN-330")
    assert exc.value.code == "out_of_stock"


def test_same_key_twice_replaces_once():
    first = replace("Q-1004", "PRD-BC-120", "PRD-BC-110", key="same")
    second = replace("Q-1004", "PRD-BC-120", "PRD-BC-110", key="same")
    assert second["replayed"] is True
    assert second["to"] == first["to"]
    assert sum(1 for l in get_quote("Q-1004")["lines"] if l["status"] == "active") == 1


def test_target_already_in_quote_merges_into_existing_line():
    # Q-1001'de BC-110 var. Önce BC-140 ekleyip onu BC-110 ile değiştiriyoruz:
    # ikinci aktif BC-110 satırı açılmamalı, mevcut satırın miktarı artmalı.
    add_to_quote("Q-1001", "PRD-BC-140", 1, "k-add", "msg")
    replace("Q-1001", "PRD-BC-140", "PRD-BC-110", key="k-rep")
    active = [l for l in get_quote("Q-1001")["lines"] if l["status"] == "active"]
    assert [(l["product_id"], l["quantity"]) for l in active] == [("PRD-BC-110", 2)]


def test_missing_source_line_raises():
    with pytest.raises(ToolError) as exc:
        replace("Q-1002", "PRD-BC-120", "PRD-BC-110")
    assert exc.value.code == "item_not_found"