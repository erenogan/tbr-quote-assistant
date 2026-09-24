"""Ürün arama ve puanlama. Saf fonksiyonlar: DB'ye dokunmaz."""
import re
from decimal import Decimal

_TR_FOLD = str.maketrans({
    "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
    "â": "a", "î": "i", "û": "u",
})


def normalize(text: str) -> str:
    text = text.replace("İ", "i").replace("I", "ı").lower()
    return text.translate(_TR_FOLD)


def tokenize(text: str) -> list[str]:
    # "usb-c" gibi tireli kelimeleri tek parça tutar.
    return re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", normalize(text))


def _token_hit(query_token: str, product_token: str) -> bool:
    if query_token == product_token:
        return True
    ## burada 3 harften kısa ise tam eşleşme istiyoruz unutma
    return len(product_token) >= 3 and query_token.startswith(product_token)


def score_product(query: str, product: dict) -> tuple[int, dict]:
    q_tokens = tokenize(query)
    aliases = product["aliases"].get("tr", [])
    texts = [product["name_tr"], *aliases]
    p_tokens = set(tokenize(" ".join(texts + product["tags"] + [product["sku"]])))

    matched = sorted({q for q in q_tokens if any(_token_hit(q, p) for p in p_tokens)})

   
    phrase_text = " | ".join(normalize(t) for t in texts)
    phrases = [f"{a} {b}" for a, b in zip(q_tokens, q_tokens[1:]) if f"{a} {b}" in phrase_text]

    return len(matched) + len(phrases), {"matched_terms": matched, "matched_phrases": phrases}


def rank_products(
    query: str,
    products: list[dict],
    *,
    max_price: Decimal | None = None,
    category: str | None = None,
    required_tags: list[str] | None = None,
    limit: int = 5,
) -> tuple[list[dict], list[dict]]:
    """(results, unavailable) döner.

    results: stokta olan, önerilebilir eşleşmeler.
    unavailable: stoğu 0 olan eşleşmeler. Öneri değil, sadece bilgi.
    """
    required_tags = required_tags or []
    wants_plus = "plus" in tokenize(query)
    results, unavailable = [], []

    for p in products:
        if not p["active"]:
            continue
        if category and p["category"] != category:
            continue
        if max_price is not None and Decimal(p["price_try"]) > Decimal(max_price):
            continue
        if any(tag not in p["tags"] for tag in required_tags):
            continue
        
        if p["sku"].endswith("PLUS") and not wants_plus:
            continue

        score, evidence = score_product(query, p)
        
        if score == 0 and not required_tags:
            continue

        item = {
            "product_id": p["product_id"],
            "sku": p["sku"],
            "name_tr": p["name_tr"],
            "category": p["category"],
            "price_try": p["price_try"],
            "stock_qty": p["stock_qty"],
            "substitute_product_ids": p["substitute_product_ids"],
            "score": score,
            "evidence": evidence,
        }
        (results if p["stock_qty"] > 0 else unavailable).append(item)

    
    def sort_key(r):
        return (-r["score"], Decimal(r["price_try"]))

    return sorted(results, key=sort_key)[:limit], sorted(unavailable, key=sort_key)[:limit]