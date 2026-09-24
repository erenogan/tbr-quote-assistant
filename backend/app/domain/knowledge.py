"""Bilgi kaydı konusunu belirleme. Saf fonksiyon: DB'ye dokunmaz."""
from app.domain.search import tokenize

# Sıra önemli: bir cümle iki konuya uyarsa listede önce gelen kazanır.
TOPIC_KEYWORDS = [
    ("return_policy",   ["iade"]),
    ("delivery_policy", ["teslimat", "kargo", "sevk"]),
    ("warranty",        ["garanti"]),
    ("service_policy",  ["kurulum", "servis"]),
    ("discount_policy", ["indirim"]),
    ("compatibility",   ["uyumlu", "offline", "senkron"]),
    ("price_ceiling",   ["butce", "limit"]),
    ("quote_validity",  ["gecerli", "rezervasyon"]),
    ("stock_rule",      ["stok", "bekle"]),
]


def infer_topic(query: str) -> str | None:
    """Cümledeki anahtar kelimelere göre konuyu tahmin eder; bulamazsa None.

    Kelime sonuna ek gelebilir ("iadesi", "indirimini"), bu yüzden startswith.
    """
    tokens = tokenize(query)
    for topic, keywords in TOPIC_KEYWORDS:
        if any(t.startswith(k) for t in tokens for k in keywords):
            return topic
    return None