from decimal import Decimal

import pytest

from app.tools.search_products import search_products


def top_id(result):
    return result["results"][0]["product_id"] if result["results"] else None


@pytest.mark.parametrize("scenario,query,kwargs,expected", [
    ("SCN-001", "kablosuz QR barkod okuyucu", {"max_price_try": Decimal(9000)}, "PRD-BC-110"),
    ("SCN-008", "4G el terminali", {"required_tags": ["4g"]}, "PRD-POS-210"),
    ("SCN-011", "Depo için 3 adet BlueScan Air ekle", {}, "PRD-BC-110"),
    ("SCN-012", "koruyucu kılıf", {"max_price_try": Decimal(1500)}, "PRD-ACC-710"),
    ("SCN-014", "Ethernet fiş yazıcı", {}, "PRD-PRN-320"),
    ("SCN-017", "offline senkron lisans", {"required_tags": ["offline"], "category": "software"}, "PRD-SW-520"),
    ("SCN-020", "kablosuz QR okuyucu", {"max_price_try": Decimal(8500)}, "PRD-BC-110"),
    ("SCN-022", "USB-C hızlı şarj", {}, "PRD-ACC-740"),
    ("SCN-019", "BlueScan Air Plus", {}, "PRD-BC-110-PLUS"),
])
def test_golden_queries_find_expected_product(scenario, query, kwargs, expected):
    assert top_id(search_products(query, **kwargs)) == expected, scenario


def test_price_limit_is_hard_filter():
    # SCN-001 / SCN-020: limit üstü ürünler hiçbir listede görünmemeli.
    res = search_products("kablosuz QR okuyucu", max_price_try=Decimal(8500))
    ids = {r["product_id"] for r in res["results"] + res["unavailable"]}
    assert "PRD-BC-120" not in ids
    assert "PRD-BC-110-PLUS" not in ids


def test_out_of_stock_is_reported_not_recommended():
    # SCN-002: RedScan Mini bulunmalı ama öneri listesinde değil.
    res = search_products("RedScan Mini 2D okuyucu")
    assert "PRD-BC-130" in {r["product_id"] for r in res["unavailable"]}
    assert "PRD-BC-130" not in {r["product_id"] for r in res["results"]}


def test_plus_variant_not_suggested_as_stock_alternative():
    # SCN-022 tuzağı: Araç şarj stokta yok, Plus'ı stokta; ama Plus önerilmemeli.
    res = search_products("araç şarj adaptörü")
    all_ids = {r["product_id"] for r in res["results"] + res["unavailable"]}
    assert "PRD-ACC-730-PLUS" not in all_ids


def test_turkish_suffix_and_characters():
    # "yazıcıyla" -> "yazıcı" eki; "fis" (Türkçe karaktersiz) -> "fiş"
    assert top_id(search_products("ethernet fis yaziciyla değiştir")) == "PRD-PRN-320"


def test_evidence_is_returned():
    res = search_products("kablosuz QR barkod okuyucu")
    evidence = res["results"][0]["evidence"]
    assert "qr" in evidence["matched_terms"]