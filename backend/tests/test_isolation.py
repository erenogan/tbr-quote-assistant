from app.db import pool


def test_a_modifies_quote():
    with pool.connection() as conn:
        conn.execute(
            "UPDATE quote_items SET quantity = 99 WHERE quote_item_id = %s",
            ("QI-1001-1",),
        )
        row = conn.execute(
            "SELECT quantity FROM quote_items WHERE quote_item_id = %s",
            ("QI-1001-1",),
        ).fetchone()
    assert row["quantity"] == 99


def test_b_sees_clean_state():
     with pool.connection() as conn:
        row = conn.execute(
            "SELECT quantity FROM quote_items WHERE quote_item_id = %s",
            ("QI-1001-1",),
        ).fetchone()
     assert row["quantity"] == 1
    