from decimal import Decimal

import pytest

from app.domain.validation import check_product_for_quote


def make_product(price, stock, active=True):
    return {"price_try": Decimal(price), "stock_qty": stock, "active": active}


def make_customer(allow_backorder):
    return {"allow_backorder": allow_backorder}


# Her satır: fiyat, limit, stok, allow_backorder, bekleyebilirim, aktif,
#            beklenen_eklenebilir, beklenen_backorder, beklenen_sebep
CASES = [
    (7990, 9000, 18, False, False, True, True, False, None),                 # 1 normal
    (12950, 9000, 4, False, False, True, False, False, "price_limit"),       # 2 limit üstü
    (8000, None, 2, False, False, True, True, False, None),                  # 3 limit yok
    (9000, 9000, 2, False, False, True, True, False, None),                  # 4 limite eşit
    (8000, 10000, 0, True, False, True, False, False, "out_of_stock"),       # 5 kullanıcı demedi
    (8000, 10000, 0, False, True, True, False, False, "backorder_not_allowed"),  # 6 müşteri izinsiz
    (8000, 10000, 0, True, True, True, True, True, None),                    # 7 bekleyen kalem
    (8000, 7000, 0, True, True, True, False, False, "price_limit"),          # 8 limit önce gelir
    (8000, 10000, 0, True, True, False, False, False, "inactive"),           # 9 pasif
]


@pytest.mark.parametrize(
    "price,limit,stock,allow_bo,accepts_bo,active,exp_allowed,exp_backorder,exp_reason",
    CASES,
)
def test_check_product_rules(price, limit, stock, allow_bo, accepts_bo, active,
                             exp_allowed, exp_backorder, exp_reason):
    decision = check_product_for_quote(
        make_product(price, stock, active),
        make_customer(allow_bo),
        quantity=1,
        max_price=Decimal(limit) if limit is not None else None,
        user_accepts_backorder=accepts_bo,
    )
    assert decision.allowed == exp_allowed
    assert decision.is_backorder == exp_backorder
    assert decision.reason == exp_reason


def test_insufficient_stock_uses_total_line_quantity():
    # Satırda 15 var, 5 daha isteniyor, stok 18: toplam 20 > 18 -> red.
    decision = check_product_for_quote(
        make_product(7990, 18), make_customer(False), quantity=15 + 5
    )
    assert decision.allowed is False
    assert decision.reason == "insufficient_stock"