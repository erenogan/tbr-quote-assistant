import { useEffect, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";
import { getJson, newId } from "./src/api";
import { colors } from "./src/format";
import ChatScreen from "./src/ChatScreen";
import QuoteScreen from "./src/QuoteScreen";

export default function App() {
  const [quotes, setQuotes] = useState([]);
  const [quoteId, setQuoteId] = useState("Q-1001");
  const [sessionId, setSessionId] = useState(() => newId("S"));
  const [tab, setTab] = useState("chat");
  const [quoteVersion, setQuoteVersion] = useState(0); // teklif değişince ekranı yenilemek için
  const [error, setError] = useState(null);

  useEffect(() => {
    getJson("/quotes").then(setQuotes).catch((e) => setError(`Sunucuya ulaşılamadı: ${e.message}`));
  }, []);

  const selectQuote = (id) => {
    setQuoteId(id);
    setSessionId(newId("S")); // her teklif için yeni sohbet oturumu
  };

  return (
    <SafeAreaProvider>
      <SafeAreaView style={styles.safe} edges={["top", "left", "right"]}>
        <StatusBar style="dark" />
        <View style={styles.header}>
          <Text style={styles.brand}>
            <Text style={{ color: colors.blue }}>The Blue </Text>
            <Text style={{ color: colors.red }}>Red</Text>
          </Text>
          <Text style={styles.headerSub}>Teklif asistanı</Text>
        </View>

        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.picker}
          contentContainerStyle={styles.pickerContent}>
          {quotes.map((q) => (
            <Pressable key={q.quote_id} onPress={() => selectQuote(q.quote_id)}
              style={[styles.chip, q.quote_id === quoteId && styles.chipActive]}>
              <Text style={[styles.chipText, q.quote_id === quoteId && styles.chipTextActive]}>{q.quote_id}</Text>
            </Pressable>
          ))}
        </ScrollView>
        {error && <Text style={styles.error}>{error}</Text>}

        <View style={styles.tabs}>
          {[["chat", "Sohbet"], ["quote", "Teklif"]].map(([id, label]) => (
            <Pressable key={id} onPress={() => setTab(id)} style={[styles.tab, tab === id && styles.tabActive]}>
              <Text style={[styles.tabText, tab === id && styles.tabTextActive]}>{label}</Text>
            </Pressable>
          ))}
        </View>

        {/* İki ekran da bellekte kalır; sohbet, sekme değişince kaybolmaz. */}
        <View style={[styles.flex, tab !== "chat" && styles.hidden]}>
          <ChatScreen key={sessionId} quoteId={quoteId} sessionId={sessionId}
            onQuoteChanged={() => setQuoteVersion((v) => v + 1)} />
        </View>
        <View style={[styles.flex, tab !== "quote" && styles.hidden]}>
          <QuoteScreen quoteId={quoteId} version={quoteVersion} visible={tab === "quote"} />
        </View>
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.paper },
  flex: { flex: 1 },
  hidden: { display: "none" },
  header: { flexDirection: "row", alignItems: "baseline", gap: 10, paddingHorizontal: 16, paddingTop: 8 },
  brand: { fontSize: 20, fontWeight: "700" },
  headerSub: { color: colors.muted, fontSize: 14 },
  picker: { flexGrow: 0, marginTop: 10 },
  pickerContent: { paddingHorizontal: 12, gap: 6 },
  chip: { paddingVertical: 6, paddingHorizontal: 12, borderRadius: 16, backgroundColor: colors.surface,
    borderWidth: 1, borderColor: colors.line },
  chipActive: { backgroundColor: colors.blue, borderColor: colors.blue },
  chipText: { color: colors.ink, fontWeight: "600", fontVariant: ["tabular-nums"] },
  chipTextActive: { color: "#fff" },
  error: { color: colors.red, paddingHorizontal: 16, paddingTop: 8 },
  tabs: { flexDirection: "row", marginTop: 10, borderBottomWidth: 1, borderBottomColor: colors.line,
    backgroundColor: colors.surface },
  tab: { flex: 1, paddingVertical: 12, alignItems: "center", borderBottomWidth: 3, borderBottomColor: "transparent" },
  tabActive: { borderBottomColor: colors.blue },
  tabText: { color: colors.muted, fontWeight: "600" },
  tabTextActive: { color: colors.ink },
});
