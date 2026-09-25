from decimal import Decimal

from app.db import pool
from app.domain.search import rank_products


def search_products(query, *, locale="tr", category=None, max_price_try=None, in_stock_only=True,
                    required_tags=None, limit=5):
    with pool.connection() as conn:
        products = conn.execute("SELECT * FROM products WHERE active").fetchall()
    results, unavailable = rank_products(
        query, products, max_price=max_price_try, category=category,
        required_tags=required_tags, limit=limit,
    )
    return {
        "results": results,
        "unavailable": unavailable,
        "filters_applied": {
            "locale": locale, "category": category, "max_price_try": max_price_try,
            "in_stock_only": in_stock_only, "required_tags": required_tags or [],
        },
    }
