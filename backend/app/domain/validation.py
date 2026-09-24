from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Decision:
    allowed: bool
    is_backorder: bool = False
    reason: str | None = None


def check_product_for_quote(
    product: dict,
    customer: dict,
    *,
    quantity: int,
    max_price: Decimal | None = None,
    user_accepts_backorder: bool = False,
) -> Decision:
    """Bir ürünün teklif satırına bu miktarla girip giremeyeceğine karar verir.

    Saf fonksiyon: DB'ye dokunmaz, sadece verilen bilgilere bakar.
    quantity: Satırın işlem SONRASI toplam miktarı (mevcut + eklenen).
    Kontrol sırası önemli: pasif -> fiyat limiti -> stok/backorder -> miktar.
    """
    
    if not product["active"]:
        return Decision(False, reason="inactive")

    
    if max_price is not None and Decimal(product["price_try"]) > Decimal(max_price):
        return Decision(False, reason="price_limit")

    stock = product["stock_qty"]

   
    if stock == 0:
        if not user_accepts_backorder:
            return Decision(False, reason="out_of_stock")
        if not customer["allow_backorder"]:
            return Decision(False, reason="backorder_not_allowed")
        return Decision(True, is_backorder=True)

  
    if quantity > stock:
        return Decision(False, reason="insufficient_stock")

    return Decision(True)