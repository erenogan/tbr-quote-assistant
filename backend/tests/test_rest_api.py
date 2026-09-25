from fastapi.testclient import TestClient

from app.main import app
from app.orchestrator.router import handle_message

client = TestClient(app)

NEW_PRODUCT = {
    "product_id": "PRD-TEST-900", "sku": "TBR-TEST-900", "name_tr": "Test Kablosuz Okuyucu",
    "category": "barcode_scanner", "brand": "TestBrand", "price_try": 4999.90, "stock_qty": 5,
    "tags": ["kablosuz", "test"], "aliases": ["test okuyucu"],
}


# ---------- teklif ----------
def test_list_quotes():
    quotes = client.get("/quotes").json()
    assert len(quotes) == 10
    q1001 = next(q for q in quotes if q["quote_id"] == "Q-1001")
    assert q1001["customer_name"] == "Mavi Kırmızı Market A.Ş." and q1001["active_lines"] == 1


def test_read_quote_and_404():
    assert client.get("/quotes/Q-1001").json()["lines"][0]["product_id"] == "PRD-BC-110"
    assert client.get("/quotes/Q-9999").status_code == 404


def test_mobile_mutation_visible_on_web():
    # PDF test sınıfı: "Web/mobil ortak durum". Mobil sohbetle ekle -> web aynı durumu okur.
    before = client.get("/quotes/Q-1002").json()
    handle_message(session_id="S-mob", message_id="M-mob-1", quote_id="Q-1002", channel="mobile",
                   text="9.000 TL altında, stokta olan kablosuz QR barkod okuyucu ekler misin?")
    after = client.get("/quotes/Q-1002").json()
    assert before["lines"] == []
    assert [(l["product_id"], l["quantity"]) for l in after["lines"]] == [("PRD-BC-110", 1)]
    assert str(after["total_try"]) in ("7990.00", "7990.0")


# ---------- ürünler ----------
def test_create_and_list_product():
    assert client.post("/products", json=NEW_PRODUCT).status_code == 201
    ids = {p["product_id"] for p in client.get("/products").json()}
    assert "PRD-TEST-900" in ids


def test_duplicate_product_is_409():
    client.post("/products", json=NEW_PRODUCT)
    assert client.post("/products", json=NEW_PRODUCT).status_code == 409


def test_invalid_product_is_422():
    assert client.post("/products", json={**NEW_PRODUCT, "price_try": -5}).status_code == 422
    assert client.post("/products", json={**NEW_PRODUCT, "product_id": "yanlis"}).status_code == 422


def test_new_product_is_searchable_immediately():
    client.post("/products", json=NEW_PRODUCT)
    from app.tools.search_products import search_products
    res = search_products("test okuyucu")
    assert res["results"][0]["product_id"] == "PRD-TEST-900"


def test_price_change_does_not_change_existing_quote():
    # Fiyat snapshot'ı: teklifteki satır eski fiyatı korur.
    client.put("/products/PRD-BC-110", json={"price_try": 9999})
    line = client.get("/quotes/Q-1001").json()["lines"][0]
    assert str(line["unit_price_try"]) in ("7990.00", "7990.0")


def test_delete_deactivates_and_keeps_old_quotes():
    assert client.delete("/products/PRD-BC-110").json()["active"] is False
    assert "PRD-BC-110" not in {p["product_id"] for p in client.get("/products").json()}
    assert "PRD-BC-110" in {p["product_id"] for p in client.get("/products?include_inactive=true").json()}
    # Eski teklif hâlâ bu ürünü gösteriyor
    assert client.get("/quotes/Q-1001").json()["lines"][0]["product_id"] == "PRD-BC-110"


# ---------- bilgi kayıtları ----------
def test_create_knowledge_used_as_source():
    entry = {"knowledge_id": "KNE-TEST-001", "topic": "warranty", "title": "Test garanti notu",
             "body": "Test amaçlı garanti açıklaması.", "source": "test/v1", "effective_from": "2026-09-01"}
    assert client.post("/knowledge", json=entry).status_code == 201
    from app.tools.get_knowledge_entries import get_knowledge_entries
    ids = [e["knowledge_id"] for e in get_knowledge_entries("garanti ne kadar?")["entries"]]
    assert "KNE-TEST-001" in ids


def test_list_knowledge_by_topic():
    ids = [k["knowledge_id"] for k in client.get("/knowledge?topic=return_policy").json()]
    assert ids == ["KNE-RET-001", "KNE-RET-001-SUP"]


# ---------- oturumlar ve loglar ----------
def test_sessions_messages_and_logs():
    handle_message(session_id="S-web", message_id="M-web-1", quote_id="Q-1001", channel="mobile",
                   text="Aktive edilmiş yazılım lisansını iade edebilir miyiz?")
    sessions = client.get("/sessions").json()
    assert sessions[0]["session_id"] == "S-web" and sessions[0]["message_count"] == 2  # soru + cevap
    roles = [m["role"] for m in client.get("/sessions/S-web/messages").json()]
    assert roles == ["user", "assistant"]
    logs = client.get("/logs?message_id=M-web-1").json()
    assert logs and {l["tool_name"] for l in logs} >= {"get_knowledge_entries"}


def test_logs_filter_errors():
    handle_message(session_id="S-err", message_id="M-err-1", quote_id="Q-1002", channel="mobile",
                   text="Cep tipi RedScan Mini 2D okuyucu ekle, bekleyebilirim.")
    errors = client.get("/logs?status=error").json()
    assert all(l["status"] == "error" for l in errors)
