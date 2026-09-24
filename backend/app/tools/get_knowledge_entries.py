from app.db import pool
from app.domain.knowledge import infer_topic


def get_knowledge_entries(
    query: str,
    *,
    topic: str | None = None,
    locale: str = "tr",
    limit: int = 5,
) -> dict:
    # Router durumdan karar verdiyse (örn. ürün stokta yok -> stock_rule) onu kullan;
    # yoksa cümleden tahmin et.
    topic_source = "given" if topic else "inferred"
    topic = topic or infer_topic(query)

    # Konu belirlenemediyse kaynak uydurma: boş dön.
    # Yanlış kaynak göstermek, kaynak göstermemekten kötü.
    if topic is None:
        return {"entries": [], "topic": None, "topic_source": topic_source}

    with pool.connection() as conn:
        entries = conn.execute(
            """
            SELECT knowledge_id, topic, title, body, source
            FROM knowledge_entries
            WHERE topic = %s AND locale = %s
            ORDER BY knowledge_id LIKE '%%-SUP', knowledge_id
            LIMIT %s
            """,
            (topic, locale, limit),
        ).fetchall()

    return {"entries": entries, "topic": topic, "topic_source": topic_source}