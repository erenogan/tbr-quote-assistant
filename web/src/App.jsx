import { useState } from "react";
import Quotes from "./tabs/Quotes.jsx";
import Products from "./tabs/Products.jsx";
import Knowledge from "./tabs/Knowledge.jsx";
import Activity from "./tabs/Activity.jsx";

const TABS = [
  { id: "quotes", label: "Teklifler", Component: Quotes },
  { id: "products", label: "Ürünler", Component: Products },
  { id: "knowledge", label: "Bilgi kayıtları", Component: Knowledge },
  { id: "activity", label: "Oturumlar ve loglar", Component: Activity },
];

export default function App() {
  const [tab, setTab] = useState("quotes");
  const Active = TABS.find((t) => t.id === tab).Component;
  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand" aria-label="The Blue Red">
          <span className="brand-blue">The Blue</span>
          <span className="brand-red">Red</span>
          <span className="brand-sub">Teklif paneli</span>
        </div>
        <nav className="tabs" role="tablist">
          {TABS.map((t) => (
            <button key={t.id} role="tab" aria-selected={tab === t.id}
              className={tab === t.id ? "tab active" : "tab"} onClick={() => setTab(t.id)}>
              {t.label}
            </button>
          ))}
        </nav>
      </header>
      {/* Sekme değişince eski sekme kaldırılır; içindeki polling interval'ı temizlenir. */}
      <main className="content"><Active /></main>
    </div>
  );
}
