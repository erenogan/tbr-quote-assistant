"""Ürün ve bilgi kaydı yönetimi (web admin paneli için CRUD)."""
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, HTTPException
from psycopg import errors
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from app.db import pool

router = APIRouter(tags=["catalog"])


# ---------------- Ürünler ----------------
class ProductIn(BaseModel):
    # Doğrulama backend'de: web'in formu atlanıp API'ye doğrudan istek atılabilir.
    product_id: str = Field(pattern=r"^PRD-[A-Z0-9-]+$")
    sku: str = Field(min_length=1)
    name_tr: str = Field(min_length=1)
    category: str = Field(min_length=1)
    brand: str = Field(min_length=1)
    price_try: Decimal = Field(gt=0)
    stock_qty: int = Field(ge=0)
    active: bool = True
    min_order_qty: int = Field(default=1, ge=1)
    delivery_days: int = Field(default=0, ge=0)
    warranty_months: int = Field(default=0, ge=0)
    tags: list[str] = []
    aliases: list[str] = []                 # Türkçe alias'lar; DB'de {"tr": [...]} olarak tutulur
    substitute_product_ids: list[str] = []
    notes: str = ""


class ProductUpdate(BaseModel):
    """Kısmi güncelleme: sadece gönderilen alanlar değişir."""
    name_tr: str | None = None
    price_try: Decimal | None = Field(default=None, gt=0)
    stock_qty: int | None = Field(default=None, ge=0)
    active: bool | None = None
    tags: list[str] | None = None
    aliases: list[str] | None = None
    substitute_product_ids: list[str] | None = None
    notes: str | None = None


def _product_row(p) -> dict:
    return {**p, "aliases": p["aliases"].get("tr", [])}


@router.get("/products")
def list_products(include_inactive: bool = False):
    sql = "SELECT * FROM products" + ("" if include_inactive else " WHERE active") + " ORDER BY product_id"
    with pool.connection() as conn:
        return [_product_row(p) for p in conn.execute(sql).fetchall()]


@router.post("/products", status_code=201)
def create_product(p: ProductIn):
    try:
        with pool.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO products (product_id, sku, name_tr, category, brand, price_try, stock_qty,
                    active, min_order_qty, delivery_days, warranty_months, tags, aliases,
                    substitute_product_ids, notes)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *
                """,
                (p.product_id, p.sku, p.name_tr, p.category, p.brand, p.price_try, p.stock_qty,
                 p.active, p.min_order_qty, p.delivery_days, p.warranty_months, Jsonb(p.tags),
                 Jsonb({"tr": p.aliases}), Jsonb(p.substitute_product_ids), p.notes),
            ).fetchone()
    except errors.UniqueViolation:
        raise HTTPException(409, f"{p.product_id} zaten var.")
    return _product_row(row)


@router.put("/products/{product_id}")
def update_product(product_id: str, p: ProductUpdate):
    fields = p.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(400, "Güncellenecek alan yok.")
    for key in ("tags", "substitute_product_ids"):
        if key in fields:
            fields[key] = Jsonb(fields[key])
    if "aliases" in fields:
        fields["aliases"] = Jsonb({"tr": fields["aliases"]})
    # Kolon adları sabit bir listeden (ProductUpdate alanları) geliyor; kullanıcı girdisi değil.
    sets = ", ".join(f"{k} = %s" for k in fields)
    with pool.connection() as conn:
        row = conn.execute(f"UPDATE products SET {sets} WHERE product_id = %s RETURNING *",
                           (*fields.values(), product_id)).fetchone()
    if row is None:
        raise HTTPException(404, f"{product_id} bulunamadı.")
    return _product_row(row)


@router.delete("/products/{product_id}")
def deactivate_product(product_id: str):
    """Silme yok, pasifleştirme var: eski teklifler bu ürünü göstermeye devam eder."""
    with pool.connection() as conn:
        row = conn.execute("UPDATE products SET active = false WHERE product_id = %s RETURNING product_id",
                           (product_id,)).fetchone()
    if row is None:
        raise HTTPException(404, f"{product_id} bulunamadı.")
    return {"product_id": product_id, "active": False}


# ---------------- Bilgi kayıtları ----------------
class KnowledgeIn(BaseModel):
    knowledge_id: str = Field(pattern=r"^KNE-[A-Z0-9-]+$")
    topic: str = Field(min_length=1)
    locale: str = "tr"
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    source: str = Field(min_length=1)
    applies_to: list[str] = []
    effective_from: date


class KnowledgeUpdate(BaseModel):
    title: str | None = None
    body: str | None = None
    source: str | None = None
    applies_to: list[str] | None = None
    effective_from: date | None = None


@router.get("/knowledge")
def list_knowledge(topic: str | None = None):
    with pool.connection() as conn:
        if topic:
            return conn.execute("SELECT * FROM knowledge_entries WHERE topic = %s ORDER BY knowledge_id",
                                (topic,)).fetchall()
        return conn.execute("SELECT * FROM knowledge_entries ORDER BY topic, knowledge_id").fetchall()


@router.post("/knowledge", status_code=201)
def create_knowledge(k: KnowledgeIn):
    try:
        with pool.connection() as conn:
            return conn.execute(
                """
                INSERT INTO knowledge_entries (knowledge_id, topic, locale, title, body, source,
                    applies_to, effective_from)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *
                """,
                (k.knowledge_id, k.topic, k.locale, k.title, k.body, k.source,
                 Jsonb(k.applies_to), k.effective_from),
            ).fetchone()
    except errors.UniqueViolation:
        raise HTTPException(409, f"{k.knowledge_id} zaten var.")


@router.put("/knowledge/{knowledge_id}")
def update_knowledge(knowledge_id: str, k: KnowledgeUpdate):
    fields = k.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(400, "Güncellenecek alan yok.")
    if "applies_to" in fields:
        fields["applies_to"] = Jsonb(fields["applies_to"])
    sets = ", ".join(f"{key} = %s" for key in fields)
    with pool.connection() as conn:
        row = conn.execute(f"UPDATE knowledge_entries SET {sets} WHERE knowledge_id = %s RETURNING *",
                           (*fields.values(), knowledge_id)).fetchone()
    if row is None:
        raise HTTPException(404, f"{knowledge_id} bulunamadı.")
    return row


@router.delete("/knowledge/{knowledge_id}")
def delete_knowledge(knowledge_id: str):
    """Bilgi kayıtlarına hiçbir tablo bağlı değil (FK yok); kalıcı silme güvenli.
    Geçmiş cevaplarda kaynak id'si metin olarak kalır."""
    with pool.connection() as conn:
        row = conn.execute("DELETE FROM knowledge_entries WHERE knowledge_id = %s RETURNING knowledge_id",
                           (knowledge_id,)).fetchone()
    if row is None:
        raise HTTPException(404, f"{knowledge_id} bulunamadı.")
    return {"knowledge_id": knowledge_id, "deleted": True}
