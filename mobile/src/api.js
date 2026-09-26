import EventSource from "react-native-sse";

// Telefonda "localhost" telefonun kendisidir. Bilgisayarın Wi-Fi IP'si .env'den gelir:
// EXPO_PUBLIC_API_URL=http://192.168.x.x:8000   (nokta ile okunmalı, köşeli parantezle değil)
export const API_URL = process.env.EXPO_PUBLIC_API_URL || "http://192.168.1.35:8000";

export async function getJson(path) {
  const res = await fetch(`${API_URL}${path}`);
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new Error(body?.detail || `HTTP ${res.status}`);
  return body;
}

// Her mesajın numarasını TELEFON üretir ve mesajla birlikte saklar.
// Tekrar gönderimde (retry) AYNI numara kullanılır; sunucu işlemi ikinci kez uygulamaz.
export const newId = (prefix) => `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const EVENTS = ["start", "tool_start", "tool_result", "sources", "text", "done", "error"];

/**
 * Mesajı gönderir, sunucunun SSE olaylarını onEvent'e iletir.
 * Dönen fonksiyon bağlantıyı kapatır.
 */
export function streamChat({ sessionId, messageId, quoteId, text }, onEvent) {
  const es = new EventSource(`${API_URL}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId, message_id: messageId, quote_id: quoteId, text, channel: "mobile",
    }),
    // TUZAK: Varsayılan 5000 ms. Yayın bitince kütüphane bağlantıyı yeniden açar ve
    // AYNI POST'u tekrar gönderir. 0 = otomatik yeniden bağlanma yok.
    pollingInterval: 0,
  });

  let finished = false;
  const finish = () => { if (!finished) { finished = true; es.close(); } };

  EVENTS.forEach((type) => {
    es.addEventListener(type, (event) => {
      // "error" hem kütüphanenin bağlantı hatası hem sunucunun kontrollü hatası olabilir:
      // sunucudan gelenin "data" alanı vardır.
      if (type === "error" && !event.data) {
        if (!finished) onEvent({ type: "connection_error", message: event.message || "Bağlantı kurulamadı." });
        finish();
        return;
      }
      const data = event.data ? JSON.parse(event.data) : {};
      onEvent({ type, ...data });
      if (type === "done" || type === "error") finish();
    });
  });
  return finish;
}
