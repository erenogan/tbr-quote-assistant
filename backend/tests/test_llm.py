"""LLM beyninin testleri. OpenAI çağrısı taklit edilir: LLM'in ne diyeceğini biz yazarız,
sistemin buna nasıl tepki verdiğini ölçeriz. Özellikle LLM'in YANLIŞ davrandığı durumlar.
"""
import json

import pytest

from app.config import settings
from app.orchestrator import llm
from app.orchestrator.router import handle_message
from app.tools.get_quote import get_quote


def tool_call(name, i=1, **args):
    return {"id": f"call_{i}", "type": "function",
            "function": {"name": name, "arguments": json.dumps(args)}}


class FakeOpenAI:
    """Sırayla önceden yazılmış cevapları döner; kendisine verilen tool listesini kaydeder."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.seen_tools = []

    def __call__(self, messages, tools):
        self.seen_tools.append({t["function"]["name"] for t in tools})
        resp = self.responses.pop(0)
        if isinstance(resp, Exception):
            raise resp
        return resp


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "test-key")   # LLM açık
    def install(*responses):
        f = FakeOpenAI(*responses)
        monkeypatch.setattr(llm, "call_openai", f)
        return f
    return install


def ask(text, quote_id="Q-1002", message_id="M-llm-1"):
    return handle_message(session_id="S-llm", message_id=message_id, quote_id=quote_id, text=text)


def lines(quote_id):
    return {l["product_id"]: l["quantity"] for l in get_quote(quote_id)["lines"] if l["status"] == "active"}


def test_llm_happy_path_goes_through_registry(fake):
    fake({"tool_calls": [tool_call("search_products", query="kablosuz QR okuyucu")]},
         {"tool_calls": [tool_call("add_to_quote", 2, product_id="PRD-BC-110", quantity=1)]},
         {"content": "BlueScan Air teklife eklendi."})
    r = ask("9.000 TL altında kablosuz QR okuyucu ekle")
    assert r["mode"] == "llm"
    assert [c.tool_name for c in r["tool_calls"]] == ["search_products", "add_to_quote"]
    assert lines("Q-1002") == {"PRD-BC-110": 1}


def test_server_injects_budget_quote_and_key(fake):
    # LLM bütçeyi, teklif numarasını ve fiş numarasını HİÇ vermedi; sunucu ekledi.
    fake({"tool_calls": [tool_call("add_to_quote", product_id="PRD-BC-110", quantity=1)]},
         {"content": "Eklendi."})
    r = ask("9.000 TL altında kablosuz QR okuyucu ekle")
    add = r["tool_calls"][0]
    assert str(add.input["max_price_try"]) == "9000"
    assert add.input["quote_id"] == "Q-1002"
    assert add.input["idempotency_key"] == "M-llm-1:add:PRD-BC-110"


def test_llm_cannot_break_price_limit(fake):
    # LLM kuralı unutup 12.950 TL'lik ürünü eklemeye çalışıyor: kasa reddeder.
    fake({"tool_calls": [tool_call("add_to_quote", product_id="PRD-BC-120", quantity=1)]},
         {"content": "Bütçenizi aşan ürünü ekleyemedim."})
    r = ask("9.000 TL altında okuyucu ekle")
    assert r["tool_calls"][0].error["code"] == "price_limit"
    assert lines("Q-1002") == {}


def test_llm_cannot_touch_another_customers_quote(fake):
    # LLM başka bir teklif numarası uydursa bile sunucu kendi quote_id'sini koyar.
    fake({"tool_calls": [tool_call("add_to_quote", product_id="PRD-BC-110", quantity=1,
                                   quote_id="Q-2002")]},
         {"content": "Eklendi."})
    ask("kablosuz QR okuyucu ekle")
    assert lines("Q-2002") == {}
    assert lines("Q-1002") == {"PRD-BC-110": 1}


def test_question_gets_no_mutation_tools(fake):
    f = fake({"tool_calls": [tool_call("get_knowledge_entries", query="iade", topic="return_policy")]},
             {"content": "Aktive lisanslar iade edilemez [KNE-RET-001]."})
    r = ask("Aktive edilmiş lisansı iade edebilir miyiz?", quote_id="Q-1001")
    assert r["mode"] == "llm"
    assert f.seen_tools[0].isdisjoint({"add_to_quote", "update_quote_item", "replace_with_alternative"})
    assert "KNE-RET-001" in {s["id"] for s in r["sources"]}


def test_forbidden_tool_on_question_falls_back(fake):
    # Soru sorulmuşken LLM ekleme yapmaya kalkarsa: izin yok -> kural tabanlı beyin.
    fake({"tool_calls": [tool_call("add_to_quote", product_id="PRD-BC-110", quantity=5)]})
    r = ask("Aktive edilmiş lisansı iade edebilir miyiz?", quote_id="Q-1001")
    assert r["mode"] == "fallback" and "izin verilmeyen" in r["fallback_reason"]
    assert lines("Q-1001") == {"PRD-BC-110": 1}  # sepete dokunulmadı


def test_unsourced_policy_answer_falls_back(fake):
    # LLM kaynak getirmeden politika cevabı uydurdu: güvenmiyoruz.
    fake({"content": "Evet, 30 gün içinde iade edebilirsiniz."})
    r = ask("Aktive edilmiş lisansı iade edebilir miyiz?", quote_id="Q-1001")
    assert r["mode"] == "fallback"
    assert "KNE-RET-001" in {s["id"] for s in r["sources"]}
    assert "30 gün" not in r["text"]


def test_openai_outage_falls_back(fake):
    fake(llm.LLMError("timeout"))
    r = ask("9.000 TL altında, stokta olan kablosuz QR barkod okuyucu ekler misin?")
    assert r["mode"] == "fallback"
    assert lines("Q-1002") == {"PRD-BC-110": 1}  # yedek beyin işi tamamladı


def test_partial_llm_then_fallback_does_not_double_add(fake):
    # LLM ürünü EKLEDİ, sonra çöktü. Router devralıp aynı ürünü tekrar eklemeye çalışır;
    # fiş numarası aynı olduğu için kasa ikinci kez uygulamaz.
    fake({"tool_calls": [tool_call("add_to_quote", product_id="PRD-BC-110", quantity=1)]},
         llm.LLMError("bağlantı koptu"))
    r = ask("9.000 TL altında, stokta olan kablosuz QR barkod okuyucu ekler misin?")
    assert r["mode"] == "fallback"
    adds = [c for c in r["tool_calls"] if c.tool_name == "add_to_quote"]
    assert len(adds) == 2 and adds[1].output["replayed"] is True
    assert lines("Q-1002") == {"PRD-BC-110": 1}  # 2 değil


def test_malformed_arguments_fall_back(fake):
    bad = {"id": "c1", "type": "function", "function": {"name": "search_products", "arguments": "{bozuk"}}
    fake({"tool_calls": [bad]})
    assert ask("kablosuz QR okuyucu ekle")["mode"] == "fallback"


def test_step_limit_falls_back(fake):
    loop = {"tool_calls": [tool_call("get_quote")]}
    fake(*[loop] * llm.MAX_STEPS)
    assert ask("teklifimde ne var?")["mode"] == "fallback"


def test_llm_cannot_invent_referenced_item(fake):
    # "Aynı okuyucudan 2 tane daha" ama Q-1003'te okuyucu yok; LLM yine de eklemeye çalışıyor.
    fake({"tool_calls": [tool_call("add_to_quote", product_id="PRD-BC-110", quantity=2)]})
    r = ask("Aynı kablosuz barkod okuyucudan 2 tane daha ekle.", quote_id="Q-1003")
    assert r["mode"] == "fallback" and "atıf" in r["fallback_reason"]
    assert lines("Q-1003") == {"PRD-PRN-320": 2}
