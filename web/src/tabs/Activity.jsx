import { Fragment, useEffect, useState } from "react";
import { api } from "../api.js";
import { TOOL_TR, time } from "../format.js";

const POLL_MS = 3000;

export default function Activity() {
  const [sessions, setSessions] = useState([]);
  const [selected, setSelected] = useState(null);
  const [messages, setMessages] = useState([]);
  const [logs, setLogs] = useState([]);
  const [onlyErrors, setOnlyErrors] = useState(false);

  useEffect(() => {
    const load = () => api.sessions().then((s) => {
      setSessions(s);
      setSelected((cur) => cur ?? s[0]?.session_id ?? null);
    });
    load();
    const id = setInterval(load, POLL_MS);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    if (!selected && !onlyErrors) return;
    const load = () => {
      const params = onlyErrors ? { status: "error", limit: 200 } : { session_id: selected, limit: 500 };
      api.logs(params).then((l) => setLogs([...l].reverse()));
      if (selected && !onlyErrors) api.messages(selected).then(setMessages);
    };
    load();
    const id = setInterval(load, POLL_MS);
    return () => clearInterval(id);
  }, [selected, onlyErrors]);

  const logsByMessage = logs.reduce((acc, l) => ({ ...acc, [l.message_id]: [...(acc[l.message_id] || []), l] }), {});

  return (
    <div className="split">
      <aside className="list">
        <h2 className="section-title">Oturumlar</h2>
        {sessions.length === 0 && <p className="empty">Henüz sohbet yok. Mobil uygulamadan bir mesaj gönderin.</p>}
        <ul>
          {sessions.map((s) => (
            <li key={s.session_id}>
              <button className={s.session_id === selected && !onlyErrors ? "row-button selected" : "row-button"}
                onClick={() => { setOnlyErrors(false); setSelected(s.session_id); }}>
                <span className="row-main">{s.quote_id}</span>
                <span className="row-sub">{s.session_id}</span>
                <span className="row-meta">{s.channel === "mobile" ? "Mobil" : s.channel}, {s.message_count} mesaj, {time(s.last_message_at)}</span>
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <section className="detail">
        <div className="section-head">
          <h2 className="section-title">{onlyErrors ? "Reddedilen ve hatalı çağrılar" : "Asistanın adımları"}</h2>
          <label className="toggle">
            <input type="checkbox" checked={onlyErrors} onChange={(e) => setOnlyErrors(e.target.checked)} />
            Sadece reddedilenler
          </label>
        </div>

        {onlyErrors
          ? <Timeline calls={logs} showMessage />
          : messages.filter((m) => m.role === "user").map((m) => {
              const answer = messages.find((a) => a.message_id === `${m.message_id}:assistant`);
              return (
                <Fragment key={m.message_id}>
                  <div className="bubble user"><span className="who">Kullanıcı</span>{m.content}</div>
                  <Timeline calls={logsByMessage[m.message_id] || []} />
                  {answer && <div className="bubble assistant"><span className="who">Asistan</span>{answer.content}</div>}
                </Fragment>
              );
            })}
      </section>
    </div>
  );
}

// Sıra numaraları gerçek bir sıra: asistanın bu mesaj için attığı adımlar.
function Timeline({ calls, showMessage }) {
  if (calls.length === 0) return null;
  return (
    <ol className="timeline">
      {calls.map((c) => (
        <li key={c.id} className={c.status === "error" ? "step rejected" : "step"}>
          <span className="seq">{c.seq}</span>
          <div className="step-body">
            <p className="step-title">
              {TOOL_TR[c.tool_name] || c.tool_name}
              <span className="tool-code">{c.tool_name}</span>
            </p>
            <p className="step-input">{summarize(c.input)}</p>
            {c.status === "error"
              ? <p className="step-error">Reddedildi: {c.output?.message} <span className="tool-code">{c.output?.code}</span></p>
              : <p className="step-output">{outcome(c)}</p>}
            {showMessage && <p className="row-meta">{c.message_id || "test"} · {time(c.created_at)}</p>}
          </div>
        </li>
      ))}
    </ol>
  );
}

const HIDDEN = new Set(["idempotency_key", "source_message_id", "locale"]);
function summarize(input) {
  return Object.entries(input || {})
    .filter(([k, v]) => !HIDDEN.has(k) && v !== null && v !== "" && !(Array.isArray(v) && v.length === 0))
    .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : v}`)
    .join("   ");
}

function outcome(c) {
  const o = c.output || {};
  if (c.tool_name === "search_products") {
    const found = (o.results || []).map((r) => r.product_id).join(", ") || "yok";
    const oos = (o.unavailable || []).map((r) => r.product_id).join(", ");
    return `Bulunan: ${found}${oos ? `   Stokta yok: ${oos}` : ""}`;
  }
  if (c.tool_name === "get_knowledge_entries") return `Kaynak: ${(o.entries || []).map((e) => e.knowledge_id).join(", ") || "bulunamadı"}`;
  if (c.tool_name === "get_quote") return `Toplam ${o.total_try} TL, ${(o.lines || []).filter((l) => l.status === "active").length} aktif satır`;
  if (o.replayed) return "Aynı istek daha önce işlenmişti; tekrar uygulanmadı.";
  if (o.delta?.quantity_after !== undefined) return `${o.product_id}: ${o.delta.quantity_before} → ${o.delta.quantity_after}`;
  if (o.delta?.with_product_id) return `${o.delta.replaced_product_id} → ${o.delta.with_product_id}`;
  return "Tamamlandı";
}
