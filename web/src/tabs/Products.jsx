import { useEffect, useState } from "react";
import { api } from "../api.js";
import { CATEGORY_TR, splitList, tl } from "../format.js";

const EMPTY = {
  product_id: "", sku: "", name_tr: "", category: "barcode_scanner", brand: "",
  price_try: "", stock_qty: "", tags: "", aliases: "", substitute_product_ids: "",
};

export default function Products() {
  const [products, setProducts] = useState([]);
  const [includeInactive, setIncludeInactive] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [message, setMessage] = useState(null);

  const load = () => api.products(includeInactive).then(setProducts)
    .catch((e) => setMessage({ kind: "error", text: e.message }));
  useEffect(() => { load(); }, [includeInactive]);

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    try {
      // Doğrulamanın asıl yeri backend (Pydantic); buradaki dönüşüm sadece biçim.
      await api.createProduct({
        ...form,
        price_try: Number(form.price_try),
        stock_qty: Number(form.stock_qty),
        tags: splitList(form.tags),
        aliases: splitList(form.aliases),
        substitute_product_ids: splitList(form.substitute_product_ids),
      });
      setMessage({ kind: "ok", text: `${form.product_id} eklendi. Asistan bu ürünü hemen bulabilir.` });
      setForm(EMPTY);
      load();
    } catch (err) {
      setMessage({ kind: "error", text: err.message });
    }
  };

  return (
    <div className="stack">
      <section>
        <div className="section-head">
          <h2 className="section-title">Ürünler <span className="count">{products.length}</span></h2>
          <label className="toggle">
            <input type="checkbox" checked={includeInactive} onChange={(e) => setIncludeInactive(e.target.checked)} />
            Satıştan kaldırılanları da göster
          </label>
        </div>
        <div className="table-scroll">
          <table className="data">
            <thead>
              <tr><th>Ürün</th><th>Kategori</th><th className="num">Fiyat</th><th className="num">Stok</th><th>Türkçe adlar</th></tr>
            </thead>
            <tbody>
              {products.map((p) => (
                <tr key={p.product_id} className={p.active ? "" : "inactive"}>
                  <td><span className="product-name">{p.name_tr}</span><span className="product-id">{p.product_id}</span></td>
                  <td>{CATEGORY_TR[p.category] || p.category}</td>
                  <td className="num">{tl(p.price_try)}</td>
                  <td className={p.stock_qty === 0 ? "num out" : "num"}>{p.stock_qty === 0 ? "Stokta yok" : p.stock_qty}</td>
                  <td className="muted">{p.aliases.join(", ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="section-title">Ürün ekle</h2>
        <form className="form" onSubmit={submit}>
          <Field label="Ürün kodu" hint="PRD- ile başlar"><input required value={form.product_id} onChange={set("product_id")} placeholder="PRD-BC-150" /></Field>
          <Field label="SKU"><input required value={form.sku} onChange={set("sku")} placeholder="TBR-BC-150" /></Field>
          <Field label="Ürün adı" wide><input required value={form.name_tr} onChange={set("name_tr")} placeholder="BlueScan Mini 2D Kablosuz Okuyucu" /></Field>
          <Field label="Kategori">
            <select value={form.category} onChange={set("category")}>
              {Object.entries(CATEGORY_TR).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </Field>
          <Field label="Marka"><input required value={form.brand} onChange={set("brand")} /></Field>
          <Field label="Fiyat (TL)"><input required type="number" min="0.01" step="0.01" value={form.price_try} onChange={set("price_try")} /></Field>
          <Field label="Stok"><input required type="number" min="0" step="1" value={form.stock_qty} onChange={set("stock_qty")} /></Field>
          <Field label="Türkçe adlar" hint="virgülle ayırın" wide><input value={form.aliases} onChange={set("aliases")} placeholder="mini okuyucu, kablosuz okuyucu" /></Field>
          <Field label="Etiketler" hint="virgülle ayırın"><input value={form.tags} onChange={set("tags")} placeholder="2d, kablosuz" /></Field>
          <Field label="Muadil ürün kodları" hint="virgülle ayırın"><input value={form.substitute_product_ids} onChange={set("substitute_product_ids")} placeholder="PRD-BC-110" /></Field>
          <div className="form-actions">
            <button type="submit" className="primary">Ürünü ekle</button>
            {message && <p className={`notice ${message.kind}`}>{message.text}</p>}
          </div>
        </form>
      </section>
    </div>
  );
}

export function Field({ label, hint, wide, children }) {
  return (
    <label className={wide ? "field wide" : "field"}>
      <span className="field-label">{label}{hint && <span className="hint"> ({hint})</span>}</span>
      {children}
    </label>
  );
}
