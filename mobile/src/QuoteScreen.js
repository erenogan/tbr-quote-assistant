import { useCallback, useEffect, useState } from "react";
import { FlatList, RefreshControl, StyleSheet, Text, View } from "react-native";
import { getJson } from "./api";
import { colors, tl } from "./format";

export default function QuoteScreen({ quoteId, version, visible }) {
  const [quote, setQuote] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Gerçek durum her zaman sunucudan okunur (web ile AYNI endpoint).
  // Sohbetteki delta'lar sadece bildirim; teklifi telefonda kendimiz hesaplamıyoruz.
  const load = useCallback(async () => {
    setLoading(true);
    try {
      setQuote(await getJson(`/quotes/${quoteId}`));
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [quoteId]);

  // Teklif değişince, sohbette bir mutasyon olunca ve sekme açılınca yeniden oku.
  useEffect(() => { load(); }, [load, version]);
  useEffect(() => { if (visible) load(); }, [visible, load]);

  const byId = Object.fromEntries((quote?.lines || []).map((l) => [l.quote_item_id, l]));

  return (
    <FlatList
      data={quote?.lines || []}
      keyExtractor={(l) => l.quote_item_id}
      contentContainerStyle={styles.list}
      refreshControl={<RefreshControl refreshing={loading} onRefresh={load} />}
      ListHeaderComponent={quote && (
        <View style={styles.head}>
          <Text style={styles.quoteId}>{quote.quote_id}</Text>
          <Text style={styles.customer}>{quote.customer.name}</Text>
          {error && <Text style={styles.error}>{error}</Text>}
        </View>
      )}
      ListEmptyComponent={!loading && <Text style={styles.muted}>Bu teklif boş. Sohbetten ürün ekleyebilirsiniz.</Text>}
      renderItem={({ item: l }) => {
        const inactive = !l.included_in_total;
        const replacement = l.replaced_by_item_id && byId[l.replaced_by_item_id];
        return (
          <View style={[styles.line, inactive && styles.lineInactive]}>
            <View style={styles.flex}>
              <Text style={[styles.name, inactive && styles.struck]}>{l.name_tr}</Text>
              <Text style={styles.meta}>{l.product_id} · {l.quantity} × {tl(l.unit_price_try)}</Text>
              {l.is_backorder && <Text style={styles.tag}>Bekleyen kalem</Text>}
              {l.applied_rules.length > 0 && (
                <Text style={styles.rules}>%{Number(l.discount_percent)} indirim · {l.applied_rules.join(", ")}</Text>
              )}
              {l.status === "replaced" && (
                <Text style={styles.note}>Değiştirildi{replacement ? `: yerine ${replacement.name_tr}` : ""}</Text>
              )}
              {l.status === "removed" && <Text style={styles.note}>Tekliften çıkarıldı</Text>}
            </View>
            <Text style={[styles.total, inactive && styles.struck]}>{inactive ? "–" : tl(l.line_total_try)}</Text>
          </View>
        );
      }}
      ListFooterComponent={quote && quote.lines.length > 0 && (
        <View style={styles.totals}>
          <Row label="Ara toplam" value={tl(quote.subtotal_try)} />
          <Row label="İndirim" value={`−${tl(quote.discount_total_try)}`} />
          <Row label="Toplam" value={tl(quote.total_try)} strong />
          <Text style={styles.footnote}>Toplamlar sunucuda hesaplanır; web ile aynıdır.</Text>
        </View>
      )}
    />
  );
}

function Row({ label, value, strong }) {
  return (
    <View style={[styles.row, strong && styles.rowStrong]}>
      <Text style={[styles.rowLabel, strong && styles.strong]}>{label}</Text>
      <Text style={[styles.rowValue, strong && styles.strong]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  list: { padding: 12, gap: 8 },
  head: { marginBottom: 6 },
  quoteId: { fontSize: 26, fontWeight: "700", color: colors.ink },
  customer: { color: colors.muted },
  error: { color: colors.red, marginTop: 4 },
  muted: { color: colors.muted, paddingVertical: 20 },
  line: { flexDirection: "row", gap: 10, backgroundColor: colors.surface, borderRadius: 10, padding: 12,
    borderWidth: 1, borderColor: colors.line },
  lineInactive: { backgroundColor: colors.paper },
  name: { color: colors.ink, fontWeight: "600", fontSize: 15 },
  struck: { textDecorationLine: "line-through", textDecorationColor: colors.red, color: colors.muted },
  meta: { color: colors.muted, fontSize: 13, marginTop: 2, fontVariant: ["tabular-nums"] },
  tag: { color: colors.blue, fontSize: 12, marginTop: 4 },
  rules: { color: colors.blue, fontSize: 13, marginTop: 4 },
  note: { color: colors.red, fontSize: 13, marginTop: 4 },
  total: { color: colors.ink, fontWeight: "700", fontVariant: ["tabular-nums"] },
  totals: { marginTop: 8, gap: 6, backgroundColor: colors.surface, borderRadius: 10, padding: 12,
    borderWidth: 1, borderColor: colors.line },
  row: { flexDirection: "row", justifyContent: "space-between" },
  rowStrong: { borderTopWidth: 2, borderTopColor: colors.ink, paddingTop: 8, marginTop: 4 },
  rowLabel: { color: colors.muted },
  rowValue: { color: colors.ink, fontVariant: ["tabular-nums"] },
  strong: { color: colors.ink, fontWeight: "700", fontSize: 17 },
  footnote: { color: colors.muted, fontSize: 12, textAlign: "right", marginTop: 4 },
});
