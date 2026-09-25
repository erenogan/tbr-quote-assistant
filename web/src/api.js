// Tarayıcı Docker ağının DIŞINDA çalışır: backend'e "backend:8000" ile değil,
// bilgisayarın portu üzerinden "localhost:8000" ile ulaşır.
export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    throw new Error(describeError(body, res.status));
  }
  return body;
}

// FastAPI hataları: 409/404 -> {detail: "metin"}, 422 -> {detail: [{loc, msg}, ...]}
function describeError(body, status) {
  const detail = body?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => `${d.loc?.slice(-1)[0]}: ${d.msg}`).join(" · ");
  }
  return `İstek başarısız oldu (HTTP ${status}).`;
}

export const api = {
  quotes: () => request("/quotes"),
  quote: (id) => request(`/quotes/${id}`),
  products: (includeInactive) => request(`/products${includeInactive ? "?include_inactive=true" : ""}`),
  createProduct: (data) => request("/products", { method: "POST", body: JSON.stringify(data) }),
  knowledge: () => request("/knowledge"),
  createKnowledge: (data) => request("/knowledge", { method: "POST", body: JSON.stringify(data) }),
  sessions: () => request("/sessions"),
  messages: (sessionId) => request(`/sessions/${sessionId}/messages`),
  logs: (params) => request(`/logs?${new URLSearchParams(params)}`),
};
