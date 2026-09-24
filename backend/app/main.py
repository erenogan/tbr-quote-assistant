from fastapi import FastAPI
from app.config import settings
from app.db import pool

app = FastAPI(title="TBR Teklif Asistanı")

@app.get("/health")
def health():
    with pool.connection() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok", "mode": "llm" if settings.llm_enabled else "fallback"}