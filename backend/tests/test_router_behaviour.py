from app.orchestrator.router import handle_message
from app.tools.get_quote import get_quote


def ask(text, quote_id):
    return handle_message(session_id="S-rb", message_id="M-rb-1", quote_id=quote_id, text=text)


def test_backorder_refused_offers_in_stock_alternatives():
    # Kullanıcı beklemeyi kabul etti ama müşterinin izni yok: sadece "hayır" demek yetmez,
    # stoklu alternatifleri sunmalı (KNE-STOCK-001-SUP).
    r = ask("Cep tipi RedScan Mini 2D okuyucu ekle, bekleyebilirim.", "Q-1001")
    assert "Stoklu alternatifler" in r["text"]
    assert "GreenScan Eco" in r["text"]
    assert "Beklemeyi kabul ederseniz" not in r["text"]  # zaten kabul etmişti
    assert [l["product_id"] for l in get_quote("Q-1001")["lines"]] == ["PRD-BC-110"]


def test_backorder_accepted_when_customer_allows():
    r = ask("Cep tipi RedScan Mini 2D okuyucu ekle, bekleyebilirim.", "Q-1002")  # Ankara: izinli
    line = next(l for l in get_quote("Q-1002")["lines"] if l["product_id"] == "PRD-BC-130")
    assert line["is_backorder"] is True
    assert "bekleyen kalem" in r["text"]


def test_ambiguous_request_asks_instead_of_guessing():
    r = ask("okuyucu ekle", "Q-1002")
    assert not any(c.tool_name == "add_to_quote" for c in r["tool_calls"])
    assert "emin olamadım" in r["text"]


def test_reference_to_missing_item_asks_instead_of_adding():
    # Q-1003'te sadece Ethernet yazıcı var. "Aynı okuyucudan 2 tane daha" -> atıf boşta kalıyor.
    r = ask("Aynı kablosuz barkod okuyucudan 2 tane daha ekle.", "Q-1003")
    assert not any(c.tool_name == "add_to_quote" for c in r["tool_calls"])
    assert "bulamadım" in r["text"]
    assert [l["product_id"] for l in get_quote("Q-1003")["lines"]] == ["PRD-PRN-320"]
