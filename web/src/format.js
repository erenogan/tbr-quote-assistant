// Toplamları web hesaplamaz; backend'in hesapladığı sayıyı sadece biçimlendirir.
const money = new Intl.NumberFormat("tr-TR", { style: "currency", currency: "TRY" });
export const tl = (v) => (v === null || v === undefined ? "–" : money.format(Number(v)));

export const time = (iso) =>
  iso ? new Date(iso).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "";

export const CATEGORY_TR = {
  barcode_scanner: "Barkod okuyucu",
  pos_terminal: "El terminali",
  receipt_printer: "Fiş yazıcı",
  label_printer: "Etiket yazıcı",
  software: "Yazılım",
  bundle: "Kit",
  accessory: "Aksesuar",
  service: "Hizmet",
};

export const TOPIC_TR = {
  return_policy: "İade",
  delivery_policy: "Teslimat",
  warranty: "Garanti",
  quote_validity: "Teklif geçerliliği",
  discount_policy: "İndirim",
  stock_rule: "Stok",
  service_policy: "Kurulum hizmeti",
  compatibility: "Uyumluluk",
  quote_idempotency: "Tekrar ekleme",
  price_ceiling: "Fiyat limiti",
  fallback: "Yedek mod",
};

export const TOOL_TR = {
  search_products: "Katalogda arama",
  get_knowledge_entries: "Politika kaydı",
  get_quote: "Teklifi okuma",
  add_to_quote: "Teklife ekleme",
  update_quote_item: "Miktar güncelleme",
  replace_with_alternative: "Alternatifle değiştirme",
};

export const splitList = (s) => s.split(",").map((x) => x.trim()).filter(Boolean);
