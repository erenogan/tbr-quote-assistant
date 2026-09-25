import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { tl, time } from "../format.js";

const POLL_MS = 2000;

export default function Quotes() {
  const [quotes, setQuotes] = useState([]);
  const [selected, setSelected] = useState("Q-1001");
  const [quote, setQuote] = useState(null);
  const [error, setError] = useState(null);
  const [updatedAt, setUpdatedAt] = useState(null);
  const [changed, setChanged] = useState(new Set());
  const previous = useRef({});

  useEffect(() => {
    api.quotes().then(setQuotes).catch((e) => setError(e.message));
  }, []);

  // Polling: mobilde yapılan değişikliği 2 sn içinde gösterir.
  // Cleanup (return) olmazsa her render'da yeni interval eklenir ve istekler çığ gibi artar.
  useEffect(() => {
    let alive = true;
    previous.current = {};
    const load = async () => {
      try {
        const q = await api.quote(selected);
        if (!alive) return;
        // Değişen satırları bul: kullanıcının dikkatini değişikliğe çekmek için kısa bir vurgu.
        const now = Object.fromEntries(q.lines.map((l) => [l.quote_item_id, `${l.status}:${l.quantity}`]));
        const diff = Object.keys(previous.current).length
          ? new Set(Object.keys(now).filter((id) => previous.current[id] !== now[id]))
          : new Set();
        previous.current = now;
        setQuote(q);
        setChanged(diff);
        setUpdatedAt(new Date().toISOString());
        setError(null);
      } catch (e) {
        if (alive) setError(e.message);
      }
    };
    load();
    const id = setInterval(load, POLL_MS);
    return () => { alive = false; clearInterval(id); };
  }, [selected]);

  return (
    <div className="split">
      <aside className="list">
        <h2 className="section-title">Teklifler</h2>
        <ul>
          {quotes.map((q) => (
            <li key={q.quote_id}>
              <button className={q.quote_id === selected ? "row-button selected" : "row-button"}
                onClick={() => setSelected(q.quote_id)}>
                <span className="row-main">{q.quote_id}</span>
                <span className="row-sub">{q.customer_name}</span>
                <span className="row-meta">
                  {q.price_tier === "partner" ? "Partner" : "Standart"}
                  {q.allow_backorder ? ", bekleyen siparişe izinli" : ""}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <section className="detail">
        {error && <p className="notice error">{error}</p>}
        {quote && (
          <>
            <div className="detail-head">
              <div>
                <h1 className="quote-id">{quote.quote_id}</h1>
                <p className="customer">{quote.customer.name}</p>
              </div>
              <p className="live" title="Web, teklifi 2 saniyede bir yeniden okur.">
                <span className="live-dot" aria-hidden="true" />
                Canlı · son okuma {time(updatedAt)}
              </p>
            </div>
            <QuoteLines quote={quote} changed={changed} />
          </>
        )}
      </section>
    </div>
  );
}

function QuoteLines({ quote, changed }) {
  const byId = Object.fromEntries(quote.lines.map((l) => [l.quote_item_id, l]));
  if (quote.lines.length === 0) {
    return <p className="empty">Bu teklif boş. Mobil uygulamadan ürün eklendiğinde burada görünecek.</p>;
  }
  return (
    <>
      <table className="lines">
        <thead>
          <tr>
            <th>Ürün</th><th className="num">Adet</th><th className="num">Birim fiyat</th>
            <th>İndirim</th><th className="num">Satır toplamı</th>
          </tr>
        </thead>
        <tbody>
          {quote.lines.map((l) => {
            const inactive = !l.included_in_total;
            const replacement = l.replaced_by_item_id && byId[l.replaced_by_item_id];
            return (
              <tr key={l.quote_item_id}
                className={[inactive ? "inactive" : "", changed.has(l.quote_item_id) ? "changed" : ""].join(" ")}>
                <td>
                  <span className="product-name">{l.name_tr}</span>
                  <span className="product-id">{l.product_id}</span>
                  {l.is_backorder && <span className="tag waiting">Bekleyen kalem</span>}
                  {l.status === "replaced" && (
                    <span className="status-note">
                      Değiştirildi{replacement ? `: yerine ${replacement.name_tr}` : ""}
                    </span>
                  )}
                  {l.status === "removed" && <span className="status-note">Tekliften çıkarıldı</span>}
                </td>
                <td className="num">{l.quantity}</td>
                <td className="num">{tl(l.unit_price_try)}</td>
                <td>
                  {l.applied_rules.length > 0
                    ? <span className="rules">%{Number(l.discount_percent)} · {l.applied_rules.join(", ")}</span>
                    : <span className="muted">–</span>}
                </td>
                <td className="num strong">{inactive ? "–" : tl(l.line_total_try)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <dl className="totals">
        <div><dt>Ara toplam</dt><dd>{tl(quote.subtotal_try)}</dd></div>
        <div><dt>İndirim</dt><dd>−{tl(quote.discount_total_try)}</dd></div>
        <div className="grand"><dt>Toplam</dt><dd>{tl(quote.total_try)}</dd></div>
      </dl>
      <p className="footnote">Toplamlar sunucuda hesaplanır; web ve mobil aynı sayıyı gösterir.</p>
    </>
  );
}
