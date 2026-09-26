// Mobil hesap yapmaz; sunucunun hesapladığı sayıyı sadece biçimlendirir.
export const tl = (v) => {
  if (v === null || v === undefined) return "–";
  const [int, dec] = Number(v).toFixed(2).split(".");
  return `${int.replace(/\B(?=(\d{3})+(?!\d))/g, ".")},${dec} TL`;
};

export const TOOL_TR = {
  search_products: "Katalogda aranıyor",
  get_knowledge_entries: "Politika kaydına bakılıyor",
  get_quote: "Teklif okunuyor",
  add_to_quote: "Teklife ekleniyor",
  update_quote_item: "Miktar güncelleniyor",
  replace_with_alternative: "Alternatifle değiştiriliyor",
};

export const colors = {
  ink: "#16213a", muted: "#5d6882", paper: "#f3f5f9", surface: "#ffffff", line: "#d8deea",
  blue: "#1d4ed8", blueSoft: "#e8eefc", red: "#c9302c", redSoft: "#fcebea",
};
