"""LLM beyni: OpenAI tool calling ile hangi tool'un çağrılacağına LLM karar verir.

Güvenlik katmanları:
1. LLM sadece 6 tool'u görür; çağrılar yine turnikeden (ToolRunner) geçer.
2. quote_id, fiş numarası ve mesaj id'si SUNUCU tarafından eklenir; LLM seçemez.
3. Bütçe ve "bekleyebilirim" bilgisi LLM'den alınmaz; sunucu cümleden çıkarır.
4. Soru cümlesinde (intent=info) LLM'e mutasyon araçları hiç gösterilmez.
5. Hata / zaman aşımı / kaynaksız politika cevabı -> LLMError -> kural tabanlı beyin.
"""
import json

import httpx

from app.config import settings
from app.db import pool
from app.domain.intent import Intent
from app.tools.registry import MUTATIONS, ToolRunner

MAX_STEPS = 6
TOPICS = ["return_policy", "delivery_policy", "warranty", "quote_validity", "discount_policy",
          "stock_rule", "service_policy", "compatibility", "price_ceiling"]

SYSTEM_PROMPT = """Sen The Blue Red'in B2B teklif asistanısın. Barkod okuyucu, el terminali,
yazıcı, yazılım lisansı ve kurulum hizmeti satıyoruz. Her zaman Türkçe cevap ver.

Kurallar:
- Ürün önerirken veya eklerken önce search_products ile ara; sadece aramada dönen product_id'leri kullan.
- Politika, iade, teslimat, garanti, indirim, uyumluluk sorularında MUTLAKA get_knowledge_entries çağır
  ve cevabında kullandığın kaydın knowledge_id'sini köşeli parantezle belirt, örn. [KNE-RET-001].
  Kayıt bulamazsan cevap uydurma; bilmediğini söyle.
- "aynı", "daha", "sepetteki" gibi ifadelerde önce get_quote ile teklife bak. Atıf yapılan ürün
  teklifte yoksa yeni ürün EKLEME; kullanıcıya teklifte böyle bir ürün olmadığını söyle ve sor.
- Bir tool hata dönerse (bütçe, stok) bunu kullanıcıya dürüstçe açıkla; kuralı aşmaya çalışma.
- Stokta olmayan ürün için stoklu alternatif öner.
- Emin olmadığın bir değişikliği yapma; kullanıcıya sor.
- Cevabın kısa ve net olsun."""

_TOOL_SPECS = {
    "search_products": ("Katalogda ürün arar. Stoklu sonuçlar 'results', stoksuzlar 'unavailable' listesindedir.",
                        {"query": {"type": "string"},
                         "category": {"type": "string", "enum": ["barcode_scanner", "pos_terminal",
                                      "receipt_printer", "label_printer", "software", "bundle",
                                      "accessory", "service"]},
                         "required_tags": {"type": "array", "items": {"type": "string"}}},
                        ["query"]),
    "get_knowledge_entries": ("Politika ve uyumluluk kayıtlarını kaynak olarak getirir.",
                              {"query": {"type": "string"}, "topic": {"type": "string", "enum": TOPICS}},
                              ["query"]),
    "get_quote": ("Mevcut teklifin satırlarını, indirimlerini ve toplamını getirir.", {}, []),
    "add_to_quote": ("Ürünü teklife ekler; aynı ürün varsa miktarı artırır.",
                     {"product_id": {"type": "string"}, "quantity": {"type": "integer", "minimum": 1}},
                     ["product_id", "quantity"]),
    "update_quote_item": ("Teklifteki bir ürünün miktarını AYARLAR (0 = çıkar).",
                          {"product_id": {"type": "string"}, "quantity": {"type": "integer", "minimum": 0}},
                          ["product_id", "quantity"]),
    "replace_with_alternative": ("Teklifteki bir ürünü alternatifiyle değiştirir.",
                                 {"from_product_id": {"type": "string"}, "to_product_id": {"type": "string"}},
                                 ["from_product_id", "to_product_id"]),
}


class LLMError(Exception):
    """LLM yolunun kullanılamadığı durum; çağıran kural tabanlı beyne düşer."""


def tool_definitions(allow_mutations: bool) -> list[dict]:
    return [
        {"type": "function", "function": {
            "name": name, "description": desc,
            "parameters": {"type": "object", "properties": props, "required": required}}}
        for name, (desc, props, required) in _TOOL_SPECS.items()
        if allow_mutations or name not in MUTATIONS
    ]


def call_openai(messages: list[dict], tools: list[dict]) -> dict:
    """Tek bir Chat Completions çağrısı. Testlerde bu fonksiyon taklit edilir (mock)."""
    try:
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            # temperature gönderilmiyor: bazı yeni modeller (akıl yürütme modelleri) bu parametreyi reddediyor.
            json={"model": settings.openai_model, "messages": messages, "tools": tools},
            timeout=settings.llm_timeout_seconds,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
        raise LLMError(f"OpenAI çağrısı başarısız: {e}") from e


def _server_side_args(name: str, args: dict, intent: Intent, quote_id: str, message_id: str) -> dict:
    """LLM'in verdiği argümanlara, LLM'e BIRAKILMAYAN değerleri sunucu ekler."""
    args = dict(args)
    if name == "search_products":
        args.update(locale="tr", in_stock_only=True, max_price_try=intent.max_price)
    elif name == "get_knowledge_entries":
        args["locale"] = "tr"
    elif name == "get_quote":
        args = {"quote_id": quote_id}
    elif name == "add_to_quote":
        args.update(quote_id=quote_id, source_message_id=message_id,
                    idempotency_key=f"{message_id}:add:{args.get('product_id')}",
                    max_price_try=intent.max_price, user_accepts_backorder=intent.accepts_backorder)
    elif name == "update_quote_item":
        args.update(quote_id=quote_id, reason="kullanıcı isteği (LLM)")
    elif name == "replace_with_alternative":
        args.update(quote_id=quote_id, quantity=None, reason="kullanıcı isteği (LLM)",
                    source_message_id=message_id,
                    idempotency_key=f"{message_id}:replace:{args.get('from_product_id')}",
                    max_price_try=intent.max_price, user_accepts_backorder=intent.accepts_backorder)
    return args


def _is_active_in_quote(quote_id: str, product_id: str | None) -> bool:
    with pool.connection() as conn:
        return conn.execute(
            "SELECT 1 FROM quote_items WHERE quote_id = %s AND product_id = %s AND status = 'active'",
            (quote_id, product_id),
        ).fetchone() is not None


def _for_llm(result) -> str:
    """Tool sonucunu LLM'e kısa ve JSON olarak geri ver."""
    payload = result.output if result.ok else {"error": result.error}
    return json.dumps(payload, ensure_ascii=False, default=str)[:6000]


def run_llm(runner: ToolRunner, intent: Intent, quote_id: str, message_id: str) -> dict:
    """LLM ajan döngüsü. Başarılıysa {'text', 'sources', 'quote'} döner, değilse LLMError."""
    allow_mutations = intent.action != "info"   # soru soranın sepetine dokunulmaz
    tools = tool_definitions(allow_mutations)
    allowed = {t["function"]["name"] for t in tools}
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": intent.text}]

    for _ in range(MAX_STEPS):
        msg = call_openai(messages, tools)
        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            return _finish(runner, msg.get("content") or "", intent)
        messages.append({"role": "assistant", "content": msg.get("content"), "tool_calls": tool_calls})
        for tc in tool_calls:
            name = tc["function"]["name"]
            if name not in allowed:
                raise LLMError(f"LLM izin verilmeyen tool çağırdı: {name}")
            try:
                args = json.loads(tc["function"].get("arguments") or "{}")
            except json.JSONDecodeError as e:
                raise LLMError("LLM bozuk argüman üretti") from e
            if name == "add_to_quote" and intent.refers_to_quote \
                    and not _is_active_in_quote(quote_id, args.get("product_id")):
                # Kullanıcı "aynı / 1 tane daha" diyerek teklifteki bir ürüne atıf yapıyor, ama LLM
                # teklifte olmayan bir ürünü eklemeye çalışıyor: varsayıma dayalı mutasyon, izin yok.
                raise LLMError("LLM, teklifte olmayan bir ürünü atıf varmış gibi eklemeye çalıştı")
            result = runner.call(name, **_server_side_args(name, args, intent, quote_id, message_id))
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": _for_llm(result)})
    raise LLMError("LLM adım sınırını aştı")


def _finish(runner: ToolRunner, text: str, intent: Intent) -> dict:
    sources, quote = [], None

    def add(source_id, kind, title):
        if all(s["id"] != source_id for s in sources):
            sources.append({"id": source_id, "type": kind, "title": title})

    for c in runner.calls:
        if not c.ok:
            continue
        if c.tool_name == "get_knowledge_entries":
            for e in c.output["entries"]:
                add(e["knowledge_id"], "knowledge", e["title"])
        elif c.tool_name == "get_quote":
            quote = c.output
        elif c.tool_name in MUTATIONS:
            pid = c.output.get("product_id") or c.output.get("to", {}).get("product_id")
            add(pid, "product", pid)

    # Kaynaksız politika cevabı diskalifiye sebebi: LLM kaynak getirmediyse güvenmiyoruz.
    policy_question = intent.action == "info" and intent.topic is not None
    if policy_question and not any(s["type"] == "knowledge" for s in sources):
        raise LLMError("LLM politika cevabına kaynak eklemedi")
    if not text.strip():
        raise LLMError("LLM boş cevap döndü")
    return {"text": text, "sources": sources, "quote": quote}
