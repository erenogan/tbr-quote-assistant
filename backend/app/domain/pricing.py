"""Teklif fiyatlandırma ve indirim kuralları. Saf fonksiyonlar: DB'ye dokunmaz."""
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

PARTNER_CATEGORIES = {"barcode_scanner", "receipt_printer", "label_printer"}
SOFTWARE_BUNDLE = {"PRD-SW-520", "PRD-SW-530"}
RULE_IDS = {
    "RUL-PARTNER-3", "RUL-ACC-5", "RUL-BUNDLE-NO-STACK",
    "RUL-SVC-URGENT", "RUL-SW-BUNDLE", "RUL-PLUS-QTY",
}
CENT = Decimal("0.01")


def money(value) -> Decimal:
    """Kuruşa yuvarlar (0,005 yukarı)."""
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def matching_rules(line, product, customer, category_qty, active_product_ids) -> list[str]:
    """Bir satıra uyan indirim kurallarının id'lerini döner.

    price_rules tablosundaki koşullar düz metin; parse etmek yerine burada kodla
    uyguluyoruz. Yüzdeler DB'den geliyor.
    """
    
    if product["category"] == "bundle":
        return ["RUL-BUNDLE-NO-STACK"]
    if product["category"] == "service" and "acil" in product["tags"]:
        return ["RUL-SVC-URGENT"]

    rules = []
   
    if (customer["price_tier"] == "partner"
            and product["category"] in PARTNER_CATEGORIES
            and category_qty[product["category"]] >= 3):
        rules.append("RUL-PARTNER-3")
    
    if product["category"] == "accessory" and line["quantity"] >= 5:
        rules.append("RUL-ACC-5")
    if product["category"] == "software" and SOFTWARE_BUNDLE <= active_product_ids:
        rules.append("RUL-SW-BUNDLE")
    if product["sku"].endswith("PLUS") and line["quantity"] >= 4:
        rules.append("RUL-PLUS-QTY")
    return rules


def price_quote(lines, products, customer, rule_percents) -> dict:
    """Satır ve teklif toplamlarını hesaplar. Sadece aktif satırlar toplama girer.

    Birden fazla kural uyarsa yüzdeler toplanır (SCN-019: %7 + %6 = %13).
    """
    active = [l for l in lines if l["status"] == "active"]

    category_qty = defaultdict(int)
    for l in active:
        category_qty[products[l["product_id"]]["category"]] += l["quantity"]
    active_ids = {l["product_id"] for l in active}

    priced, subtotal, discount_total = [], Decimal(0), Decimal(0)
    for l in lines:
        p = products[l["product_id"]]
        
        line_subtotal = money(Decimal(l["unit_price_try"]) * l["quantity"])
        is_active = l["status"] == "active"

        rules = matching_rules(l, p, customer, category_qty, active_ids) if is_active else []
        percent = sum((Decimal(rule_percents[r]) for r in rules), Decimal(0))
        line_discount = money(line_subtotal * percent / 100)

        priced.append({
            "quote_item_id": l["quote_item_id"],
            "product_id": l["product_id"],
            "name_tr": p["name_tr"],
            "category": p["category"],
            "quantity": l["quantity"],
            "unit_price_try": money(l["unit_price_try"]),
            "status": l["status"],
            "is_backorder": l["is_backorder"],
            "replaced_by_item_id": l["replaced_by_item_id"],
            "line_subtotal_try": line_subtotal,
            "applied_rules": rules,
            "discount_percent": percent,
            "discount_try": line_discount,
            "line_total_try": line_subtotal - line_discount,
            "included_in_total": is_active,
        })
        if is_active:
            subtotal += line_subtotal
            discount_total += line_discount

    return {
        "lines": priced,
        "subtotal_try": subtotal,
        "discount_total_try": discount_total,
        "total_try": subtotal - discount_total,
    }