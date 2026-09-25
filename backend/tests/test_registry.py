from decimal import Decimal

import pytest

from app.db import pool
from app.tools.get_quote import get_quote
from app.tools.registry import ToolRunner


def logs(message_id=None):
    with pool.connection() as conn:
        if message_id is None:
            return conn.execute("SELECT * FROM tool_call_logs ORDER BY id").fetchall()
        return conn.execute(
            "SELECT * FROM tool_call_logs WHERE message_id = %s ORDER BY seq", (message_id,)
        ).fetchall()


def test_successful_call_is_logged():
    runner = ToolRunner()
    result = runner.call("get_quote", quote_id="Q-1001")
    assert result.ok and result.seq == 1
    [row] = logs()
    assert row["tool_name"] == "get_quote"
    assert row["status"] == "success"
    assert row["input"] == {"quote_id": "Q-1001"}


def test_calls_get_increasing_sequence_numbers():
    runner = ToolRunner()
    runner.call("search_products", query="kablosuz QR okuyucu", max_price_try=Decimal(9000))
    runner.call("add_to_quote", quote_id="Q-1002", product_id="PRD-BC-110", quantity=1,
                idempotency_key="k1", source_message_id="m1")
    runner.call("get_quote", quote_id="Q-1002")
    assert runner.tool_names == ["search_products", "add_to_quote", "get_quote"]
    assert [r["seq"] for r in logs()] == [1, 2, 3]


def test_decimal_input_is_logged_as_text():
    ToolRunner().call("search_products", query="okuyucu", max_price_try=Decimal(9000))
    assert logs()[0]["input"]["max_price_try"] == "9000"


def test_rejected_mutation_is_logged_but_quote_unchanged():
    # Kasa reddediyor -> mutasyon ROLLBACK. Ama log kalmalı: "denendi, reddedildi."
    runner = ToolRunner()
    result = runner.call("add_to_quote", quote_id="Q-1002", product_id="PRD-BC-120",
                         quantity=1, idempotency_key="k1", source_message_id="m1",
                         max_price_try=Decimal(9000))
    assert not result.ok
    assert result.error["code"] == "price_limit"
    [row] = logs()
    assert row["status"] == "error"
    assert row["output"]["code"] == "price_limit"
    assert get_quote("Q-1002")["lines"] == []


def test_logs_linked_to_session_and_message():
    with pool.connection() as conn:
        conn.execute("INSERT INTO chat_sessions (session_id, quote_id, channel) "
                     "VALUES ('S-1', 'Q-1001', 'test')")
        conn.execute("INSERT INTO chat_messages (message_id, session_id, role, content) "
                     "VALUES ('M-1', 'S-1', 'user', 'teklifimde ne var?')")
    ToolRunner(session_id="S-1", message_id="M-1").call("get_quote", quote_id="Q-1001")
    [row] = logs("M-1")
    assert row["session_id"] == "S-1" and row["seq"] == 1


def test_unknown_tool_is_refused():
    with pytest.raises(ValueError):
        ToolRunner().call("delete_everything")