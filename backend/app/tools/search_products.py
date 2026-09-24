from decimal import Decimal

from app.db import pool
from app.domain.search import rank_products


def search_products(
    query: str,
    *,
    category: str | None = None,
    max_price_try: Decimal | None = None,
    in_stock_only: bool = True,
    required_tags: list[str] | None = None,
    limit: int = 5,
) -> dict:
    with pool.connection() as conn:
        products = conn.execute("SELECT * FROM products WHERE active").fetchall()

    results, unavailable = rank_products(
        query,
        products,
        max_price=max_price_try,
        category=category,
        required_tags=required_tags,
        limit=limit,
    )
    return {
        "results": results,
        "unavailable": unavailable,
        "filters_applied": {
            "category": category,
            "max_price_try": max_price_try,
            "in_stock_only": in_stock_only,
            "required_tags": required_tags or [],
        },
    }