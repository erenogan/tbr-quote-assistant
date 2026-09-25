"""Kural tabanlı beyin (deterministik router).

Kullanıcının cümlesini anlar (intent), hangi tool'ların hangi sırayla
çağrılacağına karar verir ve kaynaklı Türkçe bir cevap üretir.

Tool'ları DOĞRUDAN çağırmaz; hepsini turnikeden (ToolRunner) geçirir. Kurallar
(bütçe, stok, tekrar) tool'ların içinde: router hata yapsa bile kasa korur.
Emin olmadığı durumda mutasyon yapmaz, soru sorar (KNE-FALL-001).
"""
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Callable

from app.config import settings
from app.db import pool
from app.domain.intent import Intent, parse_intent
from app.domain.search import score_product
from app.tools.registry import ToolRunner

def tl(value) -> str:
    """Türkçe para biçimi: 7990 -> '7.990,00 TL'."""
    text = f"{Decimal(str(value)):,.2f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".") + " TL"


CITY_WORDS = {"istanbul": "İstanbul", "ankara": "Ankara", "izmir": "İzmir", "bursa": "Bursa",
              "antalya": "Antalya", "gaziantep": "Gaziantep", "konya": "Konya", "adana": "Adana"}


@dataclass
class Reply:
    """Cevabın parçaları ve kaynakları (sıralı, tekrarsız)."""
    parts: list[str] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    cited_topics: set = field(default_factory=set)
    quote: dict | None = None

    def say(self, text: str) -> None:
        self.parts.append(text)

    def source(self, source_id: str, kind: str, title: str) -> None:
        if all(s["id"] != source_id for s in self.sources):
            self.sources.append({"id": source_id, "type": kind, "title": title})

    @property
    def text(self) -> str:
        return " ".join(self.parts)


class Router:
    def __init__(self, runner: ToolRunner, quote_id: str, message_id: str):
        self.r = runner
        self.quote_id = quote_id
        self.message_id = message_id
        self.reply = Reply()

    # ---------- yardımcılar ----------
    def cite(self, topic: str, query: str = "") -> list[dict]:
        """Bir politikayı kaynak olarak ekler (tool üzerinden: log'da izlenebilir)."""
        if topic in self.reply.cited_topics:
            return []
        self.reply.cited_topics.add(topic)
        res = self.r.call("get_knowledge_entries", query=query or topic, topic=topic, locale="tr")
        entries = res.output["entries"] if res.ok else []
        for e in entries:
            self.reply.source(e["knowledge_id"], "knowledge", e["title"])
        return entries

    def load_quote(self) -> dict | None:
        res = self.r.call("get_quote", quote_id=self.quote_id)
        if res.ok:
            self.reply.quote = res.output
            return res.output
        self.reply.say(res.error["message"])
        return None

    def product_source(self, product: dict) -> None:
        self.reply.source(product["product_id"], "product", product["name_tr"])

    @staticmethod
    def load_products(ids: list[str]) -> dict:
        # Salt okuma yardımcısı (tool değil): sepet satırlarını ürün kaydıyla eşleştirmek için.
        with pool.connection() as conn:
            rows = conn.execute("SELECT * FROM products WHERE product_id = ANY(%s)", (ids,)).fetchall()
        return {p["product_id"]: p for p in rows}

    def match_line(self, quote: dict, phrase: str, prefer_out_of_stock: bool = False) -> tuple[dict, dict] | None:
        """Cümledeki ifadeye en çok uyan AKTİF sepet satırını bulur."""
        active = [l for l in quote["lines"] if l["status"] == "active"]
        if not active:
            return None
        products = self.load_products([l["product_id"] for l in active])
        scored = []
        for line in active:
            p = products[line["product_id"]]
            score, _ = score_product(phrase, p)
            if prefer_out_of_stock and p["stock_qty"] == 0:
                score += 1
            scored.append((score, line, p))
        scored.sort(key=lambda x: -x[0])
        best = scored[0]
        if best[0] == 0 or (len(scored) > 1 and scored[1][0] == best[0]):
            return None  # emin değiliz
        return best[1], best[2]

    @staticmethod
    def confident(results: list[dict]) -> dict | None:
        """En iyi sonuç net mi? (puan >= 2 ve ikinciden yüksek) Değilse mutasyon yok."""
        if not results or results[0]["score"] < 2:
            return None
        if len(results) > 1 and results[1]["score"] == results[0]["score"]:
            return None
        return results[0]

    def mutation_key(self, tool: str, product_id: str) -> str:
        # Aynı mesaj tekrar gelirse (retry) aynı anahtar üretilir -> ikinci kez uygulanmaz.
        return f"{self.message_id}:{tool}:{product_id}"

    # ---------- ürün bulma ----------
    def find_product(self, intent: Intent) -> dict | None:
        res = self.r.call("search_products", query=intent.product_phrase, locale="tr",
                          max_price_try=intent.max_price, in_stock_only=True)
        if not res.ok:
            self.reply.say(res.error["message"])
            return None
        results, unavailable = res.output["results"], res.output["unavailable"]

        # Aranan ürün stokta yok mu? (stoksuz eşleşme, stokluların hepsinden daha iyi uyuyorsa)
        top_score = results[0]["score"] if results else 0
        if unavailable and unavailable[0]["score"] > top_score:
            oos = unavailable[0]
            self.product_source(oos)
            if intent.accepts_backorder:
                return oos  # kasa, müşterinin izni olup olmadığına karar verecek
            self.cite("stock_rule")
            if intent.fallback_phrase:  # "X yoksa Y ekle"
                self.reply.say(f"{oos['name_tr']} şu anda stokta yok.")
                res2 = self.r.call("search_products", query=intent.fallback_phrase, locale="tr",
                                   max_price_try=intent.max_price, in_stock_only=True)
                alt = self.confident(res2.output["results"]) if res2.ok else None
                if alt:
                    return alt
                self.reply.say("Belirttiğiniz alternatifi de net olarak bulamadım.")
                return None
            self.suggest_substitutes(oos)
            return None

        best = self.confident(results)
        if best is None:
            if results:
                names = ", ".join(r["name_tr"] for r in results[:3])
                self.reply.say(f"Hangi ürünü kastettiğinizden emin olamadım. Adaylar: {names}. "
                               "Hangisini ekleyeyim?")
            else:
                self.reply.say("Bu isteğe uyan stoklu bir ürün bulamadım.")
            return None
        return best

    def suggest_substitutes(self, product: dict, reason: str = "out_of_stock") -> None:
        """Stokta olmayan ürün için stoklu muadilleri önerir (KNE-STOCK-001-SUP)."""
        subs = self.load_products(product["substitute_product_ids"])
        in_stock = [subs[i] for i in product["substitute_product_ids"] if i in subs and subs[i]["stock_qty"] > 0]
        if reason == "backorder_not_allowed":
            msg = (f"{product['name_tr']} şu anda stokta yok ve bu müşteri için bekleyen sipariş "
                   "açılamadığından teklife eklemedim.")
        else:
            msg = f"{product['name_tr']} şu anda stokta yok; stok kuralı gereği teklife eklemedim."
        if in_stock:
            msg += " Stoklu alternatifler: " + ", ".join(
                f"{p['name_tr']} ({tl(p['price_try'])})" for p in in_stock) + "."
        if reason == "out_of_stock":
            msg += " Beklemeyi kabul ederseniz bunu açıkça belirtin."
        self.reply.say(msg)

    # ---------- mutasyonlar ----------
    def do_add(self, product: dict, quantity: int, intent: Intent) -> None:
        res = self.r.call(
            "add_to_quote", quote_id=self.quote_id, product_id=product["product_id"],
            quantity=quantity, idempotency_key=self.mutation_key("add", product["product_id"]),
            source_message_id=self.message_id,
            max_price_try=intent.max_price, user_accepts_backorder=intent.accepts_backorder,
        )
        self.product_source(product)
        if not res.ok:
            code = res.error["code"]
            if code in ("out_of_stock", "backorder_not_allowed") and "substitute_product_ids" in product:
                self.suggest_substitutes(product, code)   # sadece "hayır" deme, alternatif sun
            else:
                self.reply.say(res.error["message"])
            if code in ("out_of_stock", "backorder_not_allowed"):
                self.cite("stock_rule")
            if res.error["code"] == "price_limit":
                self.cite("price_ceiling")
            return
        out = res.output
        d = out["delta"]
        if out["replayed"]:
            self.reply.say(f"Bu istek daha önce işlenmişti; {product['name_tr']} miktarı tekrar "
                           f"artırılmadı (şu an {d['quantity_after']}).")
        elif out["action"] == "incremented":
            self.reply.say(f"{product['name_tr']} zaten teklifte vardı; yeni satır açmadan miktarı "
                           f"{d['quantity_before']} → {d['quantity_after']} yaptım.")
        else:
            extra = " (stok gelince gönderilecek bekleyen kalem)" if out["is_backorder"] else ""
            self.reply.say(f"{product['name_tr']} ({tl(out['unit_price_try'])}) teklife {quantity} adet "
                           f"eklendi{extra}.")
        if out["action"] == "incremented" or out["replayed"]:
            self.cite("quote_idempotency")

    # ---------- eylemler ----------
    def handle_add(self, intent: Intent) -> None:
        if intent.needs:
            return self.handle_compatibility(intent)
        product = None
        if intent.refers_to_quote:  # "aynı okuyucudan", "1 tane daha"
            quote = self.load_quote()
            match = self.match_line(quote, intent.product_phrase) if quote else None
            if match:
                product = match[1]
        if product is None:
            product = self.find_product(intent)
        if product is None:
            return
        self.do_add(product, intent.quantity or 1, intent)

    def handle_compatibility(self, intent: Intent) -> None:
        entries = self.cite("compatibility", intent.text)
        if entries:
            self.reply.say(f"Uyumluluk kuralına göre: {entries[0]['body']}")
        for category, tag in intent.needs:
            res = self.r.call("search_products", query=intent.product_phrase, locale="tr",
                              category=category, required_tags=[tag], in_stock_only=True,
                              max_price_try=intent.max_price)
            if res.ok and res.output["results"]:
                self.do_add(res.output["results"][0], intent.quantity or 1, intent)
            else:
                self.reply.say(f"'{tag}' ihtiyacı için stoklu uygun ürün bulamadım.")

    def handle_set_total(self, intent: Intent) -> None:
        quote = self.load_quote()
        match = self.match_line(quote, intent.product_phrase) if quote else None
        if match is None:
            product = self.find_product(intent)
            if product:
                self.do_add(product, intent.quantity, intent)
            return
        line, product = match
        target, current = intent.quantity, line["quantity"]
        if target > current:
            self.do_add(product, target - current, intent)   # "toplam 4 olsun": 1 varsa 3 ekle
        elif target < current:
            self.do_update(line, product, target)
        else:
            self.product_source(product)
            self.reply.say(f"{product['name_tr']} zaten {current} adet; değişiklik gerekmedi.")

    def do_update(self, line: dict, product: dict, quantity: int) -> None:
        res = self.r.call("update_quote_item", quote_id=self.quote_id, product_id=product["product_id"],
                          quantity=quantity, reason="kullanıcı isteği")
        self.product_source(product)
        if res.ok:
            d = res.output["delta"]
            verb = "teklif­ten çıkardım" if quantity == 0 else f"miktarını {d['quantity_before']} → {d['quantity_after']} yaptım"
            self.reply.say(f"{product['name_tr']} {verb}.".replace("\u00ad", ""))
        else:
            self.reply.say(res.error["message"])

    def handle_update(self, intent: Intent) -> None:
        if intent.quantity is None:
            self.reply.say("Yeni miktarı belirtir misiniz?")
            return
        quote = self.load_quote()
        match = self.match_line(quote, intent.product_phrase) if quote else None
        if match is None:
            self.reply.say("Teklifte hangi satırı güncellemek istediğinizden emin olamadım.")
            return
        self.do_update(match[0], match[1], intent.quantity)

    def handle_replace(self, intent: Intent) -> None:
        quote = self.load_quote()
        prefer_oos = "stokta olmayan" in intent.text.lower() or "stoksuz" in intent.text.lower()
        match = self.match_line(quote, intent.product_phrase, prefer_oos) if quote else None
        if match is None:
            self.reply.say("Teklifte hangi ürünü değiştirmek istediğinizden emin olamadım.")
            return
        line, old = match
        self.product_source(old)

        query = intent.replace_target_phrase or old["name_tr"]
        res = self.r.call("search_products", query=query, locale="tr",
                          category=None if intent.replace_target_phrase else old["category"],
                          max_price_try=intent.max_price, in_stock_only=True, limit=10)
        results = [r for r in (res.output["results"] if res.ok else []) if r["product_id"] != old["product_id"]]
        if intent.generic_alternative:
            # Belirli ürün istenmedi: kataloğun resmi muadil listesini (sırasıyla) tercih et.
            by_id = {r["product_id"]: r for r in results}
            new = next((by_id[i] for i in old["substitute_product_ids"] if i in by_id), None) \
                or (results[0] if results else None)
        else:
            new = self.confident(results)
        if new is None:
            self.reply.say("Kurallara uyan (bütçe ve stok) bir alternatif bulamadım; teklifi değiştirmedim.")
            return

        res = self.r.call(
            "replace_with_alternative", quote_id=self.quote_id,
            from_product_id=old["product_id"], to_product_id=new["product_id"], quantity=None,
            reason=self._replace_reason(old, intent),
            idempotency_key=self.mutation_key("replace", old["product_id"]),
            source_message_id=self.message_id,
            max_price_try=intent.max_price, user_accepts_backorder=intent.accepts_backorder,
        )
        self.product_source(new)
        if not res.ok:
            self.reply.say(res.error["message"])
            return
        o = res.output
        why = " (katalogda resmi muadili olarak kayıtlı)" if o["is_listed_substitute"] else ""
        self.reply.say(f"{o['from']['name_tr']} satırını pasif (değiştirildi) yaptım; yerine "
                       f"{o['to']['name_tr']} ({tl(o['to']['price_try'])}, stok {o['to']['stock_qty']}) "
                       f"{o['to']['quantity']} adet eklendi{why}. Neden: {o['reason']}.")
        if old["stock_qty"] == 0:
            self.cite("stock_rule")

    @staticmethod
    def _replace_reason(old: dict, intent: Intent) -> str:
        if old["stock_qty"] == 0:
            return "mevcut ürün stokta yok"
        if intent.max_price is not None:
            return f"{tl(intent.max_price)} bütçe sınırı"
        return "kullanıcı isteği"

    def handle_info(self, intent: Intent) -> None:
        if intent.topic:
            entries = self.cite(intent.topic, intent.text)
            if entries:
                main = entries[0]
                self.reply.say(f"{main['title']} [{main['knowledge_id']}]: {main['body']}")
                for note in entries[1:]:
                    self.reply.say(f"Not [{note['knowledge_id']}]: {note['body']}")
                self._service_city_warning(intent)
        else:
            self.reply.say("Bu soru için kayıtlı bir politika kaydı bulamadım; kaynaksız cevap vermemek "
                           "için yanıtlamıyorum.")
        # Yedek modda cevap, retrieval + teklif durumuna dayanır (KNE-FALL-001).
        if True:  # yedek modda cevap retrieval + teklif durumuna dayanır (KNE-FALL-001)
            quote = self.load_quote()
            if quote and intent.wants_quote_view:
                self.describe_quote(quote)

    def _service_city_warning(self, intent: Intent) -> None:
        text = intent.text.lower().replace("İ", "i")
        if intent.topic != "service_policy" or "acil" not in text:
            return
        from app.domain.search import tokenize
        cities = [CITY_WORDS[t] for t in tokenize(intent.text) if t in CITY_WORDS]
        for city in cities:
            if city not in ("İstanbul", "Ankara"):
                self.reply.say(f"Bu politikaya göre {city} için acil kurulum kesin olarak vaat edilemez; "
                               "acil kurulum yalnızca İstanbul ve Ankara'da, ekip müsaitliğine bağlı.")

    def describe_quote(self, quote: dict) -> None:
        active = [l for l in quote["lines"] if l["status"] == "active"]
        if not active:
            self.reply.say("Teklifiniz şu an boş.")
            return
        items = ", ".join(f"{l['name_tr']} × {l['quantity']}" for l in active)
        self.reply.say(f"Teklifinizde: {items}. Toplam: {tl(quote['total_try'])}.")
        products = self.load_products([l["product_id"] for l in active])
        for l in active:
            self.product_source(products[l["product_id"]])

    def summarize_after_mutation(self, intent: Intent) -> None:
        """Mutasyon olduysa güncel teklifi oku; indirimleri ve kaynaklarını göster."""
        if not any(c.ok and c.is_mutation for c in self.r.calls):
            return
        quote = self.load_quote()
        if not quote:
            return
        rules = sorted({r for l in quote["lines"] if l["included_in_total"] for r in l["applied_rules"]})
        for rule in rules:
            self.reply.source(rule, "rule", rule)
        discounted = [l for l in quote["lines"] if l["included_in_total"] and l["discount_try"] > 0]
        if discounted:
            desc = "; ".join(f"{l['name_tr']}: %{l['discount_percent']} ({', '.join(l['applied_rules'])})"
                             for l in discounted)
            self.reply.say(f"Uygulanan indirimler: {desc}.")
        self.reply.say(f"Güncel teklif toplamı: {tl(quote['total_try'])} "
                       f"(indirim: {tl(quote['discount_total_try'])}).")

    def run(self, intent: Intent) -> Reply:
        handlers = {"add": self.handle_add, "set_total": self.handle_set_total,
                    "update": self.handle_update, "replace": self.handle_replace,
                    "info": self.handle_info}
        handler = handlers.get(intent.action)
        if handler is None:
            self.reply.say("Ne yapmak istediğinizi anlayamadım. Ürün ekleme, miktar güncelleme, "
                           "değiştirme veya politika sorusu sorabilirsiniz.")
        else:
            handler(intent)
        if intent.action in ("add", "set_total", "update", "replace"):
            self.summarize_after_mutation(intent)
            if intent.max_price is not None:
                self.cite("price_ceiling")
            if intent.wants_discount:
                self.cite("discount_policy")
            if intent.topic == "service_policy":
                self.cite("service_policy")
        # Bu beyin çalışıyorsa yedek moddayız (key yok ya da LLM başarısız oldu).
        self.cite("fallback")
        self.reply.say("(Yedek mod: bu yanıt kayıtlı politika ve teklif verisinden üretildi.)")
        return self.reply


def _ensure_session(session_id: str, quote_id: str, channel: str, message_id: str, text: str) -> None:
    with pool.connection() as conn:
        conn.execute("INSERT INTO chat_sessions (session_id, quote_id, channel) VALUES (%s, %s, %s) "
                     "ON CONFLICT (session_id) DO NOTHING", (session_id, quote_id, channel))
        # Aynı mesaj tekrar gelirse (retry) ikinci kez kaydedilmez.
        conn.execute("INSERT INTO chat_messages (message_id, session_id, role, content) "
                     "VALUES (%s, %s, 'user', %s) ON CONFLICT (message_id) DO NOTHING",
                     (message_id, session_id, text))


def _save_answer(session_id: str, message_id: str, text: str) -> None:
    with pool.connection() as conn:
        conn.execute("INSERT INTO chat_messages (message_id, session_id, role, content) "
                     "VALUES (%s, %s, 'assistant', %s) ON CONFLICT (message_id) DO NOTHING",
                     (f"{message_id}:assistant", session_id, text))


def handle_message(*, session_id: str, message_id: str, quote_id: str, text: str,
                   channel: str = "mobile", on_event: Callable[[dict], None] | None = None) -> dict:
    """Bir kullanıcı mesajını uçtan uca işler. SSE endpoint'i ve testler bunu çağırır.

    LLM açıksa önce LLM beyni denenir; herhangi bir sorunda kural tabanlı beyne düşülür.
    İki beyin de AYNI turnikeyi (runner) kullanır: loglar tek yerde, sıra numaraları kesintisiz.
    LLM yarıda kalıp router devralsa bile fiş numaraları aynı kalıpta olduğu için
    hiçbir mutasyon iki kez uygulanmaz.
    """
    _ensure_session(session_id, quote_id, channel, message_id, text)
    runner = ToolRunner(session_id=session_id, message_id=message_id, on_event=on_event)
    intent = parse_intent(text)
    mode, fallback_reason = "fallback", None

    if settings.llm_enabled:
        from app.orchestrator.llm import LLMError, run_llm
        try:
            out = run_llm(runner, intent, quote_id, message_id)
            mode = "llm"
            reply = Reply(parts=[out["text"]], sources=out["sources"], quote=out["quote"])
        except LLMError as e:
            fallback_reason = str(e)
    if mode == "fallback":
        reply = Router(runner, quote_id, message_id).run(intent)

    _save_answer(session_id, message_id, reply.text)
    return {
        "session_id": session_id,
        "message_id": message_id,
        "mode": mode,
        "fallback_reason": fallback_reason,
        "intent": intent.action,
        "text": reply.text,
        "sources": reply.sources,
        "tool_calls": runner.calls,
        "quote": reply.quote,
    }
