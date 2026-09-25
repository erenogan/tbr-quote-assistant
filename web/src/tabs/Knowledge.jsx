import { useEffect, useState } from "react";
import { api } from "../api.js";
import { TOPIC_TR } from "../format.js";
import { Field } from "./Products.jsx";

const today = () => new Date().toISOString().slice(0, 10);
const EMPTY = { knowledge_id: "", topic: "return_policy", title: "", body: "", source: "", effective_from: today() };

export default function Knowledge() {
  const [entries, setEntries] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [message, setMessage] = useState(null);

  const load = () => api.knowledge().then(setEntries).catch((e) => setMessage({ kind: "error", text: e.message }));
  useEffect(() => { load(); }, []);
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    try {
      await api.createKnowledge(form);
      setMessage({ kind: "ok", text: `${form.knowledge_id} eklendi. Asistan bu konudaki sorularda kaynak olarak kullanır.` });
      setForm(EMPTY);
      load();
    } catch (err) {
      setMessage({ kind: "error", text: err.message });
    }
  };

  const byTopic = entries.reduce((acc, k) => ({ ...acc, [k.topic]: [...(acc[k.topic] || []), k] }), {});

  return (
    <div className="stack">
      <section>
        <h2 className="section-title">Bilgi kayıtları <span className="count">{entries.length}</span></h2>
        <p className="lead">Asistan politika sorularını yalnızca bu kayıtlara dayanarak cevaplar ve her cevapta kaydın kodunu gösterir.</p>
        <div className="topics">
          {Object.entries(byTopic).map(([topic, items]) => (
            <article key={topic} className="topic">
              <h3>{TOPIC_TR[topic] || topic}</h3>
              {items.map((k) => (
                <div key={k.knowledge_id} className="entry">
                  <p className="entry-title">{k.title} <span className="product-id">{k.knowledge_id}</span></p>
                  <p className="entry-body">{k.body}</p>
                  <p className="entry-source">Kaynak: {k.source}</p>
                </div>
              ))}
            </article>
          ))}
        </div>
      </section>

      <section>
        <h2 className="section-title">Bilgi kaydı ekle</h2>
        <form className="form" onSubmit={submit}>
          <Field label="Kayıt kodu" hint="KNE- ile başlar"><input required value={form.knowledge_id} onChange={set("knowledge_id")} placeholder="KNE-WAR-002" /></Field>
          <Field label="Konu">
            <select value={form.topic} onChange={set("topic")}>
              {Object.entries(TOPIC_TR).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </Field>
          <Field label="Geçerlilik başlangıcı"><input required type="date" value={form.effective_from} onChange={set("effective_from")} /></Field>
          <Field label="Başlık" wide><input required value={form.title} onChange={set("title")} /></Field>
          <Field label="Metin" wide><textarea required rows={4} value={form.body} onChange={set("body")} /></Field>
          <Field label="Kaynak" hint="örn. policy/warranty/v2026-09" wide><input required value={form.source} onChange={set("source")} /></Field>
          <div className="form-actions">
            <button type="submit" className="primary">Kaydı ekle</button>
            {message && <p className={`notice ${message.kind}`}>{message.text}</p>}
          </div>
        </form>
      </section>
    </div>
  );
}
