import { useRef, useState } from "react";
import { FlatList, KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { newId, streamChat } from "./api";
import { colors, TOOL_TR } from "./format";

const EXAMPLES = [
  "9.000 TL altında, stokta olan kablosuz QR barkod okuyucu ekler misin?",
  "Aynı kablosuz barkod okuyucudan 2 tane daha ekle.",
  "Aktive edilmiş yazılım lisansını iade edebilir miyiz?",
];

export default function ChatScreen({ quoteId, sessionId, onQuoteChanged }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const listRef = useRef(null);

  // Bir asistan mesajını güncelle. Olaylar çok hızlı gelir: fonksiyon biçimi (prev => ...)
  // kullanılmazsa handler eski state'i görür ve parçalar birbirinin üstüne yazılıp kaybolur.
  const patch = (id, fn) => setMessages((prev) => prev.map((m) => (m.id === id ? fn(m) : m)));

  const run = (messageId, text) => {
    const answerId = `${messageId}:answer`;
    patch(answerId, (m) => ({ ...m, text: "", steps: [], sources: [], status: "streaming" }));
    let mutated = false;
    streamChat({ sessionId, messageId, quoteId, text }, (e) => {
      if (e.type === "tool_start") {
        patch(answerId, (m) => ({ ...m, steps: [...m.steps, { seq: e.seq, tool: e.tool, status: "running" }] }));
      } else if (e.type === "tool_result") {
        if (e.status === "success" && e.quote_delta && !e.replayed) mutated = true;
        patch(answerId, (m) => ({
          ...m,
          steps: m.steps.map((s) => (s.seq === e.seq ? { ...s, status: e.status, error: e.error,
            delta: e.quote_delta, replayed: e.replayed } : s)),
        }));
      } else if (e.type === "sources") {
        patch(answerId, (m) => ({ ...m, sources: e.sources }));
      } else if (e.type === "text") {
        patch(answerId, (m) => ({ ...m, text: m.text + e.chunk }));
      } else if (e.type === "done") {
        patch(answerId, (m) => ({ ...m, status: "done" }));
        if (mutated) onQuoteChanged(); // gerçek durum sunucudan tekrar okunacak
      } else if (e.type === "error" || e.type === "connection_error") {
        patch(answerId, (m) => ({ ...m, status: "error", text: m.text || e.message }));
      }
    });
  };

  const send = (text) => {
    const clean = text.trim();
    if (!clean) return;
    // Numara, gönder tuşuna basıldığı anda BİR KEZ üretilir ve mesajla saklanır.
    const messageId = newId("M");
    setMessages((prev) => [
      ...prev,
      { id: messageId, role: "user", text: clean },
      { id: `${messageId}:answer`, role: "assistant", text: "", steps: [], sources: [], status: "streaming" },
    ]);
    setInput("");
    run(messageId, clean);
  };

  return (
    <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === "ios" ? "padding" : "height"}>
      <FlatList
        ref={listRef}
        data={messages}
        keyExtractor={(m) => m.id}
        contentContainerStyle={styles.list}
        onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: true })}
        ListEmptyComponent={<Examples quoteId={quoteId} onPick={send} />}
        renderItem={({ item }) =>
          item.role === "user"
            ? <UserBubble message={item} onRetry={() => run(item.id, item.text)} />
            : <AssistantBubble message={item} />}
      />
      <View style={styles.composer}>
        <TextInput style={styles.input} value={input} onChangeText={setInput} placeholder="Mesajınızı yazın"
          placeholderTextColor={colors.muted} multiline />
        <Pressable style={styles.send} onPress={() => send(input)} accessibilityLabel="Gönder">
          <Text style={styles.sendText}>Gönder</Text>
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

function Examples({ quoteId, onPick }) {
  return (
    <View style={styles.examples}>
      <Text style={styles.examplesTitle}>{quoteId} için örnek mesajlar</Text>
      {EXAMPLES.map((e) => (
        <Pressable key={e} onPress={() => onPick(e)} style={styles.example}>
          <Text style={styles.exampleText}>{e}</Text>
        </Pressable>
      ))}
    </View>
  );
}

function UserBubble({ message, onRetry }) {
  return (
    <View style={styles.userWrap}>
      <View style={styles.userBubble}><Text style={styles.userText}>{message.text}</Text></View>
      {/* Retry: AYNI mesaj numarasıyla tekrar gönderir; sunucu işlemi ikinci kez uygulamaz. */}
      <Pressable onPress={onRetry}><Text style={styles.retry}>Aynı mesajı tekrar gönder</Text></Pressable>
    </View>
  );
}

function AssistantBubble({ message }) {
  return (
    <View style={styles.assistant}>
      {message.steps.map((s) => <Step key={s.seq} step={s} />)}
      {message.status === "streaming" && message.steps.length === 0 && <Text style={styles.muted}>Bağlanıyor…</Text>}
      {!!message.text && (
        <Text style={[styles.answer, message.status === "error" && { color: colors.red }]}>{message.text.trim()}</Text>
      )}
      {message.sources.length > 0 && (
        <View style={styles.sources}>
          {message.sources.map((src) => (
            <View key={src.id} style={styles.source}>
              <Text style={styles.sourceText}>{src.title !== src.id ? `${src.title} · ` : ""}{src.id}</Text>
            </View>
          ))}
        </View>
      )}
    </View>
  );
}

function Step({ step }) {
  const failed = step.status === "error";
  let detail = null;
  if (failed) detail = `Reddedildi: ${step.error?.message}`;
  else if (step.replayed) detail = "Daha önce işlenmişti; tekrar uygulanmadı.";
  else if (step.delta?.quantity_after !== undefined)
    detail = `Teklif güncellendi: ${step.delta.quantity_before} → ${step.delta.quantity_after}`;
  else if (step.delta?.with_product_id)
    detail = `${step.delta.replaced_product_id} → ${step.delta.with_product_id}`;
  return (
    <View style={styles.step}>
      <View style={[styles.dot, failed && { backgroundColor: colors.red }, step.status === "running" && styles.dotRunning]}>
        <Text style={styles.dotText}>{step.seq}</Text>
      </View>
      <View style={styles.flex}>
        <Text style={styles.stepTitle}>{TOOL_TR[step.tool] || step.tool}{step.status === "running" ? "…" : ""}</Text>
        {detail && <Text style={[styles.stepDetail, failed && { color: colors.red }]}>{detail}</Text>}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  list: { padding: 12, gap: 10, flexGrow: 1 },
  muted: { color: colors.muted },
  examples: { gap: 8, paddingTop: 12 },
  examplesTitle: { color: colors.muted, fontWeight: "600" },
  example: { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.line, borderRadius: 8, padding: 12 },
  exampleText: { color: colors.ink },
  userWrap: { alignItems: "flex-end", gap: 4 },
  userBubble: { backgroundColor: colors.blue, borderRadius: 12, padding: 10, maxWidth: "85%" },
  userText: { color: "#fff", fontSize: 15 },
  retry: { color: colors.muted, fontSize: 12, textDecorationLine: "underline" },
  assistant: { backgroundColor: colors.surface, borderRadius: 12, padding: 12, gap: 8, borderWidth: 1, borderColor: colors.line },
  answer: { color: colors.ink, fontSize: 15, lineHeight: 21 },
  step: { flexDirection: "row", gap: 8, alignItems: "flex-start" },
  dot: { width: 22, height: 22, borderRadius: 11, backgroundColor: colors.blue, alignItems: "center", justifyContent: "center" },
  dotRunning: { opacity: 0.5 },
  dotText: { color: "#fff", fontSize: 11, fontWeight: "700" },
  stepTitle: { color: colors.ink, fontWeight: "600", fontSize: 13 },
  stepDetail: { color: colors.blue, fontSize: 13 },
  sources: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  source: { backgroundColor: colors.blueSoft, borderRadius: 10, paddingHorizontal: 8, paddingVertical: 3 },
  sourceText: { color: colors.blue, fontSize: 12 },
  composer: { flexDirection: "row", gap: 8, padding: 10, backgroundColor: colors.surface,
    borderTopWidth: 1, borderTopColor: colors.line },
  input: { flex: 1, minHeight: 44, maxHeight: 120, borderWidth: 1, borderColor: colors.line, borderRadius: 8,
    paddingHorizontal: 12, paddingVertical: 10, color: colors.ink, fontSize: 15 },
  send: { backgroundColor: colors.blue, borderRadius: 8, paddingHorizontal: 16, justifyContent: "center" },
  sendText: { color: "#fff", fontWeight: "700" },
});
