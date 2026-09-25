"""POST /chat/stream: kullanıcı mesajını işler, olayları SSE ile canlı yayınlar.

Router senkron çalışıyor; olayları işler OLURKEN gönderebilmek için router'ı ayrı
bir thread'de çalıştırıp olayları bir kuyruğa koyuyoruz. HTTP cevabı kuyruktan
okudukça telefona yazıyor.

Olay sırası: start → (tool_start → tool_result)* → sources → text* → done
Hata olursa: ... → error (bağlantı sessizce kopmaz, kontrollü kapanır)
"""
import json
import queue
import threading

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.orchestrator.router import handle_message

router = APIRouter()
_DONE = object()  # kuyruğun "bitti" işareti


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1)
    message_id: str = Field(min_length=1)   # CLIENT üretir; retry'da AYNISINI gönderir
    quote_id: str = Field(min_length=1)
    text: str = Field(min_length=1, max_length=2000)
    channel: str = "mobile"


def sse(event: str, data: dict) -> str:
    """Tek bir SSE olayı: 'event: ...' + 'data: ...' + boş satır."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


def chunk_text(text: str, words_per_chunk: int = 4):
    words = text.split(" ")
    for i in range(0, len(words), words_per_chunk):
        yield " ".join(words[i:i + words_per_chunk]) + " "


@router.post("/chat/stream")
def chat_stream(req: ChatRequest):
    events: queue.Queue = queue.Queue()

    def worker():
        try:
            result = handle_message(
                session_id=req.session_id, message_id=req.message_id, quote_id=req.quote_id,
                text=req.text, channel=req.channel, on_event=events.put,
            )
            events.put({"type": "sources", "sources": result["sources"]})
            # Yedek modda metin tek seferde üretiliyor; aynı sözleşmeyle parça parça akıtıyoruz.
            for chunk in chunk_text(result["text"]):
                events.put({"type": "text", "chunk": chunk})
            quote = result["quote"] or {}
            events.put({"type": "done", "intent": result["intent"], "quote_id": req.quote_id,
                        "total_try": quote.get("total_try")})
        except Exception:  # beklenmedik hata: kontrollü kapat
            events.put({"type": "error", "code": "internal_error",
                        "message": "Beklenmeyen bir hata oluştu, lütfen tekrar deneyin."})
        finally:
            events.put(_DONE)

    def stream():
        yield sse("start", {"session_id": req.session_id, "message_id": req.message_id,
                            "mode": "llm" if settings.llm_enabled else "fallback"})
        threading.Thread(target=worker, daemon=True).start()
        while (event := events.get()) is not _DONE:
            yield sse(event.pop("type"), event)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
