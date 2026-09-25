"""Şirketin 22 golden senaryosunu uçtan uca çalıştırır.

Her senaryo için:
1. Beklenen tool çağrıları, beklenen sırayla ve parametrelerle yapıldı mı?
   (Aradaki ek çağrılara izin var: örn. mutasyondan sonra teklifi tekrar okumak.)
2. Yasaklı çağrılar (must_not_call) hiç denenmedi mi?
3. Beklenen kaynaklar (expected_sources) cevapta var mı?
4. Önerilmemesi gereken ürünler (must_not_recommend) cevapta yok mu?
5. Teklif sonunda beklenen durumda mı? (quote_assertion)
"""
import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.domain.search import normalize
from app.orchestrator.router import handle_message
from app.tools.get_quote import get_quote

GOLDEN = json.loads((Path(__file__).parent / "data" / "golden_test_scenarios.json").read_text("utf-8"))
MUTATIONS = {"add_to_quote", "update_quote_item", "replace_with_alternative"}


def active(quote_id):
    return {l["product_id"]: l for l in get_quote(quote_id)["lines"] if l["status"] == "active"}


def status(quote_id, product_id):
    return next(l["status"] for l in get_quote(quote_id)["lines"] if l["product_id"] == product_id)


def qty(quote_id):
    return {pid: l["quantity"] for pid, l in active(quote_id).items()}


# quote_assertion metinleri Türkçe cümle; her birini koda çevirdik.
QUOTE_CHECKS = {
    "SCN-001": lambda: qty("Q-1002") == {"PRD-BC-110": 1},
    "SCN-002": lambda: qty("Q-1001") == {"PRD-BC-110": 1},
    "SCN-003": lambda: qty("Q-1001") == {"PRD-BC-110": 3},
    "SCN-004": lambda: qty("Q-1003")["PRD-PRN-320"] == 4,
    "SCN-005": lambda: status("Q-1004", "PRD-BC-120") == "replaced" and qty("Q-1004") == {"PRD-BC-110": 1},
    "SCN-006": lambda: status("Q-1005", "PRD-BC-130") == "replaced" and qty("Q-1005") == {"PRD-BC-140": 2},
    "SCN-007": lambda: qty("Q-1001") == {"PRD-BC-110": 1},
    "SCN-008": lambda: {"PRD-POS-210", "PRD-SW-520"} <= set(qty("Q-1002")),
    "SCN-009": lambda: qty("Q-1001") == {"PRD-BC-110": 1},
    "SCN-010": lambda: qty("Q-1001") == {"PRD-BC-110": 2},
    "SCN-011": lambda: qty("Q-1002") == {"PRD-BC-110": 3}
                       and "RUL-PARTNER-3" in active("Q-1002")["PRD-BC-110"]["applied_rules"],
    "SCN-012": lambda: qty("Q-2003") == {"PRD-ACC-710-PLUS": 4, "PRD-ACC-710": 1},
    "SCN-013": lambda: qty("Q-2001") == {"PRD-BC-110-PLUS": 2},
    "SCN-014": lambda: status("Q-2004", "PRD-PRN-330") == "replaced" and qty("Q-2004") == {"PRD-PRN-320": 1},
    "SCN-015": lambda: qty("Q-2005") == {"PRD-SVC-810": 2},
    "SCN-016": lambda: qty("Q-2003") == {"PRD-ACC-710-PLUS": 4},
    "SCN-017": lambda: qty("Q-2002") == {"PRD-SW-520": 1, "PRD-SW-530": 1},
    "SCN-018": lambda: qty("Q-2003") == {"PRD-ACC-710-PLUS": 4},
    "SCN-019": lambda: qty("Q-2001") == {"PRD-BC-110-PLUS": 4}
                       and "RUL-PLUS-QTY" in active("Q-2001")["PRD-BC-110-PLUS"]["applied_rules"],
    "SCN-020": lambda: qty("Q-1002") == {"PRD-BC-110": 1},
    "SCN-021": lambda: qty("Q-2003") == {"PRD-ACC-710-PLUS": 4},
    "SCN-022": lambda: qty("Q-2002") == {"PRD-ACC-740": 1},
}


def value_matches(actual, expected) -> bool:
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        return actual is not None and Decimal(str(actual)) == Decimal(str(expected))
    return actual == expected


def call_matches(call, name, must_match, first_run_keys) -> bool:
    if call.tool_name != name:
        return False
    for key, expected in must_match.items():
        if key == "query_contains":
            if normalize(expected) not in normalize(call.input.get("query", "")):
                return False
        elif key == "same_idempotency_key":
            if call.input.get("idempotency_key") not in first_run_keys:
                return False
        elif key == "replayed":
            if not (call.ok and call.output.get("replayed") is expected):
                return False
        elif not value_matches(call.input.get(key), expected):
            return False
    return True


def run(scenario, times=1):
    results = []
    for _ in range(times):  # retry: AYNI message_id ile tekrar gönderim
        results.append(handle_message(
            session_id=f"S-{scenario['scenario_id']}", message_id=f"M-{scenario['scenario_id']}",
            quote_id=scenario["quote_id"], text=scenario["user_message"], channel="test"))
    return results


@pytest.mark.parametrize("scenario", GOLDEN, ids=[s["scenario_id"] for s in GOLDEN])
def test_golden_scenario(scenario):
    sid = scenario["scenario_id"]
    runs = run(scenario, times=2 if scenario.get("repeat_same_message_id") else 1)
    calls = [c for r in runs for c in r["tool_calls"]]
    first_run_keys = {c.input.get("idempotency_key") for c in runs[0]["tool_calls"]}

    # 1. Beklenen çağrılar, sırasıyla (aradaki ek çağrılara izin var)
    pos = 0
    for exp in scenario["expected_tool_calls"]:
        while pos < len(calls) and not call_matches(calls[pos], exp["name"], exp.get("must_match", {}), first_run_keys):
            pos += 1
        assert pos < len(calls), f"{sid}: beklenen çağrı bulunamadı: {exp} | yapılanlar: " + \
            str([(c.tool_name, c.input) for c in calls])
        pos += 1

    # 2. Yasaklı çağrılar hiç denenmemeli
    for forbidden in scenario.get("must_not_call", []):
        assert forbidden not in [c.tool_name for c in calls], f"{sid}: yasaklı çağrı: {forbidden}"

    # 3. Beklenen kaynaklar cevapta
    source_ids = {s["id"] for r in runs for s in r["sources"]}
    missing = set(scenario.get("expected_sources", [])) - source_ids
    assert not missing, f"{sid}: eksik kaynaklar {missing} | dönen: {source_ids}"

    # 4. Önerilmemesi gereken ürünler cevapta yok
    for pid in scenario.get("must_not_recommend", []):
        assert pid not in source_ids, f"{sid}: önerilmemesi gereken ürün kaynakta: {pid}"

    # 5. Teklifin son durumu
    assert QUOTE_CHECKS[sid](), f"{sid}: teklif durumu beklenen gibi değil: {qty(scenario['quote_id'])}"

    # Her cevap Türkçe metin ve en az bir kaynak içermeli
    assert runs[-1]["text"] and runs[-1]["sources"]


def test_scn018_does_not_promise_urgent_install_in_izmir():
    [r] = run(next(s for s in GOLDEN if s["scenario_id"] == "SCN-018"))
    assert "İzmir" in r["text"] and "vaat edilemez" in r["text"]


def test_every_call_is_logged():
    from app.db import pool
    [r] = run(GOLDEN[0])
    with pool.connection() as conn:
        n = conn.execute("SELECT count(*) AS n FROM tool_call_logs WHERE message_id = %s",
                         (r["message_id"],)).fetchone()["n"]
    assert n == len(r["tool_calls"])
