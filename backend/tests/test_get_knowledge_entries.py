import pytest

from app.tools.get_knowledge_entries import get_knowledge_entries


@pytest.mark.parametrize("scenario,message,expected_topic", [
    ("SCN-007", "Aktive edilmiş yazılım lisansını iade edebilir miyiz?", "return_policy"),
    ("SCN-008", "Sahada internet olmayacak; 4G'li el terminali ve offline senkron için gereken lisansı ekle.", "compatibility"),
    ("SCN-009", "İade süresi nedir ve teklifimde hangi ürün var?", "return_policy"),
    ("SCN-011", "Depo için 3 adet BlueScan Air ekle; partner indirimini de göster.", "discount_policy"),
    ("SCN-015", "Yerinde kurulum hizmetini 2 lokasyon için güncelle.", "service_policy"),
    ("SCN-017", "Offline senkron ve şube senkronu için gerekli yazılımları ekle.", "compatibility"),
    ("SCN-018", "İzmir için yarına acil kurulum kesin diyebilir miyiz?", "service_policy"),
    ("SCN-019", "BlueScan Air Plus toplam 4 adet olsun, varsa hacim indirimini göster.", "discount_policy"),
    ("SCN-021", "Stokta olan donanımlar için teslimat kuralı nedir?", "delivery_policy"),
])
def test_topic_inferred_from_golden_messages(scenario, message, expected_topic):
    result = get_knowledge_entries(message)
    assert result["topic"] == expected_topic, scenario
    assert result["entries"], f"{scenario}: en az bir kaynak dönmeli"


def test_main_policy_comes_before_note():
    # SCN-016 iki kaynak bekliyor; ana politika önce.
    result = get_knowledge_entries("Aktive edilmiş yazılım lisansları iade edilebilir mi?")
    ids = [e["knowledge_id"] for e in result["entries"]]
    assert ids == ["KNE-RET-001", "KNE-RET-001-SUP"]


def test_given_topic_overrides_inference():
    # SCN-002: cümlede "stok" yok; konuyu router durumdan belirler ve açıkça verir.
    result = get_knowledge_entries("Cep tipi RedScan Mini 2D okuyucu ekle.", topic="stock_rule")
    assert result["topic"] == "stock_rule"
    assert result["topic_source"] == "given"
    assert result["entries"][0]["knowledge_id"] == "KNE-STOCK-001"


def test_unknown_topic_returns_no_sources():
    # Alakasız soruya uydurma kaynak gösterilmemeli.
    result = get_knowledge_entries("hava durumu nasıl")
    assert result["topic"] is None
    assert result["entries"] == []


def test_every_entry_has_knowledge_id_and_source():
    # PDF: politika cevapları knowledge_id kaynağı döndürmeli.
    for entry in get_knowledge_entries("teslimat süresi")["entries"]:
        assert entry["knowledge_id"].startswith("KNE-")
        assert entry["source"]