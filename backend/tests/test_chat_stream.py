import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def stream(message_id, text, quote_id="Q-1002", session_id="S-sse"):
    """SSE cevabını okuyup [(olay, veri), ...] listesine çevirir."""
    resp = client.post("/chat/stream", json={
        "session_id": session_id, "message_id": message_id, "quote_id": quote_id, "text": text})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    events = []
    for block in resp.text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.split("\n"))
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def names(events):
    return [e for e, _ in events]


def test_event_order_start_tools_sources_text_done():
    events = stream("m1", "9.000 TL altında, stokta olan kablosuz QR barkod okuyucu ekler misin?")
    assert names(events)[0] == "start"
    assert names(events)[-1] == "done"
    assert events[0][1]["session_id"] == "S-sse" and events[0][1]["message_id"] == "m1"
    order = names(events)
    assert order.index("sources") > max(i for i, n in enumerate(order) if n == "tool_result")
    assert order.index("sources") < order.index("text")


def test_every_tool_start_has_matching_result():
    events = stream("m1", "9.000 TL altında, stokta olan kablosuz QR barkod okuyucu ekler misin?")
    starts = [(d["seq"], d["tool"]) for e, d in events if e == "tool_start"]
    results = [(d["seq"], d["tool"]) for e, d in events if e == "tool_result"]
    assert starts == results
    assert [s for s, _ in starts] == list(range(1, len(starts) + 1))


def test_mutation_result_carries_quote_delta():
    events = stream("m1", "9.000 TL altında, stokta olan kablosuz QR barkod okuyucu ekler misin?")
    add = next(d for e, d in events if e == "tool_result" and d["tool"] == "add_to_quote")
    assert add["quote_delta"] == {"quantity_before": 0, "quantity_after": 1}


def test_input_summary_hides_technical_keys():
    events = stream("m1", "9.000 TL altında, stokta olan kablosuz QR barkod okuyucu ekler misin?")
    add = next(d for e, d in events if e == "tool_start" and d["tool"] == "add_to_quote")
    assert "idempotency_key" not in add["input_summary"]
    assert add["input_summary"]["product_id"] == "PRD-BC-110"


def test_sources_and_text_are_streamed():
    events = stream("m1", "Aktive edilmiş yazılım lisansını iade edebilir miyiz?", quote_id="Q-1001")
    sources = next(d for e, d in events if e == "sources")["sources"]
    assert "KNE-RET-001" in {s["id"] for s in sources}
    text = "".join(d["chunk"] for e, d in events if e == "text")
    assert "iade" in text.lower()
    assert names(events).count("text") > 1  # parça parça akıyor


def test_retry_same_message_id_does_not_double_apply():
    msg = "Kablosuz barkod okuyucudan 1 tane daha ekle."
    stream("retry-1", msg, quote_id="Q-1001")
    second = stream("retry-1", msg, quote_id="Q-1001")  # bağlantı koptu, aynı mesaj tekrar
    add = next(d for e, d in second if e == "tool_result" and d["tool"] == "add_to_quote")
    assert add["replayed"] is True
    assert add["quote_delta"] == {"quantity_before": 1, "quantity_after": 2}  # 3 değil


def test_invalid_request_rejected():
    resp = client.post("/chat/stream", json={"session_id": "s", "quote_id": "Q-1001", "text": "merhaba"})
    assert resp.status_code == 422  # message_id eksik


def test_unknown_quote_is_controlled_not_crash():
    events = stream("m1", "Teklifimde hangi ürün var?", quote_id="Q-9999")
    assert names(events)[-1] in ("done", "error")


def test_replace_result_carries_quote_delta():
    events = stream("m1", "Rugged okuyucu çok pahalı; 9.000 TL altında stoklu alternatifle değiştir.",
                    quote_id="Q-1004")
    rep = next(d for e, d in events if e == "tool_result" and d["tool"] == "replace_with_alternative")
    assert rep["quote_delta"] == {"replaced_product_id": "PRD-BC-120",
                                  "with_product_id": "PRD-BC-110", "quantity": 1}
