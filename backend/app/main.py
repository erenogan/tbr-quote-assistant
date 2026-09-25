from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.activity import router as activity_router
from app.api.catalog import router as catalog_router
from app.api.chat import router as chat_router
from app.api.quotes import router as quotes_router
from app.config import settings
from app.db import pool

app = FastAPI(title="TBR Teklif Asistanı")

# Web (localhost:5173) ve mobil farklı adresten istek atıyor; tarayıcı CORS izni ister.
# Yerel demo için tüm kaynaklara izin veriyoruz (KNOWN_LIMITATIONS'ta belirtildi).
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(chat_router)
app.include_router(quotes_router)
app.include_router(catalog_router)
app.include_router(activity_router)


@app.get("/health")
def health():
    with pool.connection() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok", "mode": "llm" if settings.llm_enabled else "fallback"}
