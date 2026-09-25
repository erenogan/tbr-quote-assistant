"""Kullanıcı cümlesinden niyet çıkarma. Saf fonksiyonlar: DB'ye dokunmaz.

Kural tabanlı beynin "kulakları": cümleyi okuyup ne istendiğini, bütçeyi,
miktarı ve bağlam bilgilerini (bekleyebilirim, sepetteki ürüne atıf) çıkarır.
"""
import re
from dataclasses import dataclass, field
from decimal import Decimal

from app.domain.knowledge import infer_topic
from app.domain.search import normalize, tokenize

# "9.000 TL altında", "1.500 TL altı", "8.500 TL üstüne çıkmadan", "en fazla 5.000 TL"
_PRICE_PATTERNS = [
    r"(\d{1,3}(?:[.\s]\d{3})+|\d+)\s*(?:tl|try|₺)\s*(?:altinda|alti|altindaki|ustune cikmadan|"
    r"ustune cikmayan|gecmeden|gecmeyen|kadar)",
    r"en fazla\s*(\d{1,3}(?:[.\s]\d{3})+|\d+)\s*(?:tl|try|₺)",
    r"(?:butce|butcem|limit|limitim)\w*\s*(\d{1,3}(?:[.\s]\d{3})+|\d+)",
]
_QTY_WORDS = r"(?:adet|tane|lokasyon|sube|kisi|adede|adete)"


COMPATIBILITY_NEEDS = [
    ("4g", "pos_terminal", "4g"),
    ("offline", "software", "offline"),
    ("sube", "software", "sube"),
]


@dataclass
class Intent:
    action: str                          # add | update | set_total | replace | info | unknown
    text: str
    max_price: Decimal | None = None
    quantity: int | None = None
    accepts_backorder: bool = False
    refers_to_quote: bool = False        # "aynı", "daha", "sepetteki"
    wants_quote_view: bool = False       # "teklifimde ne var"
    wants_discount: bool = False         # "indirimini göster"
    topic: str | None = None
    product_phrase: str = ""             # aranacak ürün ifadesi
    fallback_phrase: str | None = None   # "X yoksa Y" -> Y
    replace_target_phrase: str | None = None   # "... Y ile değiştir" -> Y
    generic_alternative: bool = False    # "alternatifle değiştir" (belirli ürün yok)
    needs: list[tuple[str, str]] = field(default_factory=list)  # [(kategori, etiket)]


def parse_price(text: str) -> Decimal | None:
    t = normalize(text)
    for pattern in _PRICE_PATTERNS:
        m = re.search(pattern, t)
        if m:
            return Decimal(re.sub(r"[.\s]", "", m.group(1)))
    return None


def parse_quantity(text: str) -> int | None:
    t = normalize(text)
    m = re.search(r"(\d+)\s*" + _QTY_WORDS, t)
    return int(m.group(1)) if m else None


def _strip_noise(phrase: str) -> str:
    """Ürün aramasına gitmeyecek kısımları (fiyat ve miktar ifadeleri) çıkarır."""
    t = re.sub(r"(\d{1,3}(?:[.\s]\d{3})+|\d+)\s*(tl|try|₺)\s*\S*(\s+[çc][ıi]kmadan)?", " ", phrase,
               flags=re.IGNORECASE)
    t = re.sub(r"\b\d+\s*(adet|tane|adede|adete)\b", " ", t, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", t).strip(" ,;.")


def _split_replace(text: str) -> tuple[str, str]:
    """ "X'i Y ile değiştir" cümlesini (X, Y) olarak böler.

    Türkçe'de ekler rolü söyler: çıkacak ürün belirtme hali alır (yazıcı-yı,
    okuyucu-yu), gelecek ürün vasıta hali alır (yazıcı-yla, alternatif-le).
    Önce ';' ve "yerine" gibi açık ayraçlara, sonra -yı/-yu ekli son kelimeye bakarız.
    """
    before = re.split(r"\s+de[gğ]i[sş]tir", text, flags=re.IGNORECASE)[0]
    for sep in (";", " yerine "):
        if sep in before:
            left, right = before.rsplit(sep, 1)
            return left, right
    words = before.split()
    for i in range(len(words) - 1, -1, -1):
        if re.search(r"(y[ıiuü]|n[ıiuü])$", normalize(words[i]).rstrip(".,")) and i < len(words) - 1:
            return " ".join(words[: i + 1]), " ".join(words[i + 1:])
    return before, ""


def parse_intent(text: str) -> Intent:
    t = normalize(text)
    tokens = tokenize(text)
    has = lambda *stems: any(tok.startswith(s) for tok in tokens for s in stems)

    intent = Intent(action="unknown", text=text)
    intent.max_price = parse_price(text)
    intent.quantity = parse_quantity(text)
    intent.accepts_backorder = has("bekleyebilir", "beklerim", "beklemeyi kabul")
    intent.refers_to_quote = has("ayni", "sepetteki", "teklifteki") or bool(
        re.search(r"\d+\s*(tane|adet)\s+daha", t))
    intent.wants_quote_view = bool(re.search(r"(teklif|sepet)\w*\s+(hangi|ne)\b", t))
    intent.wants_discount = has("indirim")
    intent.topic = infer_topic(text)

    # --- Eylem ---
    if has("degistir"):
        intent.action = "replace"
    elif re.search(r"toplam\s+\d+\s*(adet|tane)", t):
        intent.action = "set_total"
    elif has("guncelle") or re.search(r"\d+\s*(adede|adete)\s+(cikar|dusur|indir)", t) \
            or re.search(r"\d+\s*(adet|tane)\s+(yap|olsun)", t):
        intent.action = "update"
    elif has("ekle"):
        intent.action = "add"
    elif "?" in text or has("nedir") or re.search(r"\b(mi|mu|miyiz|miyim|misin)\b", t):
        intent.action = "info"

    # --- Ürün ifadeleri ---
    phrase = text
    if intent.action == "replace":
        from_part, target = _split_replace(text)
        target_words = tokenize(target)
        intent.generic_alternative = not target_words or any(w.startswith("alternatif") for w in target_words)
        intent.replace_target_phrase = None if intent.generic_alternative else _strip_noise(target)
        phrase = from_part
    m = re.search(r"^(.*?)\s+yoksa\s+(.*)$", text, re.IGNORECASE)
    if m:
        phrase, intent.fallback_phrase = m.group(1), _strip_noise(m.group(2))
    intent.product_phrase = _strip_noise(phrase)

    # --- Uyumluluk: bir cümlede birden fazla ürün ihtiyacı ---
    if intent.action == "add" and intent.topic == "compatibility":
        intent.needs = [(cat, tag) for key, cat, tag in COMPATIBILITY_NEEDS if has(key)]
    return intent
