# Yapay Zeka Destekli Teklif Asistanı

B2B müşterilerin mobil sohbetten ürün ve politika sorusu sorduğu, asistanın cevabını kaynaklarla verdiği ve gerektiğinde ortak bir teklif üzerinde gerçek değişiklik yaptığı bir sistem. Web paneli aynı teklifi canlı olarak gösterir.

**Backend:** FastAPI, PostgreSQL, psycopg (ORM yok)
**Web:** React (Vite), nginx
**Mobil:** React Native (Expo SDK 57)
**LLM:** OpenAI tool calling (opsiyonel); anahtar yoksa kural tabanlı yedek mod
**Çalıştırma:** Docker Compose

**22 golden senaryonun tamamı uçtan uca otomatik testlerle geçiyor.**

---

## Gereksinimler

Docker Desktop, Git. Mobil için Node.js LTS ve telefonda Expo Go.

---

## Backend, veritabanı ve web

```bash
git clone <repo-url>
cd tbr-quote-assistant

cp .env.example .env
# Windows:
Copy-Item .env.example .env

docker compose up -d --build --wait
```

Web paneli:

```text
http://localhost:5173
```

API belgeleri (Swagger):

```text
http://localhost:8000/docs
```

Sağlık kontrolü ve mod:

```text
http://localhost:8000/health
```

`/health` sistemin LLM modunda mı yoksa fallback modunda mı olduğunu gösterir.

Seed verisi ilk açılışta otomatik yüklenir:

```text
db/01_seed.sql
db/02_app_schema.sql
```

### Veritabanını sıfırlamak için

```bash
docker compose down -v
docker compose up -d --wait
```

### LLM modu

`.env` içine `OPENAI_API_KEY` ve `OPENAI_MODEL` yazın, sonra backend'i yeniden oluşturun.

`.env` sadece container oluşturulurken okunur:

```bash
docker compose up -d --force-recreate --wait backend
```

Anahtar boşsa sistem yedek modda çalışır; bu, case'in fallback gereksinimini doğrudan gösterir.

---

# Mobil Kısım

```bash
cd mobile
npm install
cp .env.example .env
```

`.env`:

```text
EXPO_PUBLIC_API_URL=http://<bilgisayarın-Wi-Fi-IP'si>:8000
```

Ardından:

```bash
npx expo start
```

QR kodu Expo Go ile tarayın.

Telefon ve bilgisayar aynı ağda olmalı. Telefonda `localhost` telefonun kendisini gösterdiği için adres olarak bilgisayarın Wi-Fi IP'si kullanılır.

### iPhone

Expo SDK 57 ile birlikte iOS'taki Expo Go, geliştirme sunucusundan proje açmak için Expo CLI ve Expo Go'nun aynı Expo hesabıyla giriş yapmış olmasını istiyor.

Bilgisayarda:

```bash
npx expo login --browser
```

ile giriş yapıp telefonda **"Try Again"**e basın.

### Windows güvenlik duvarı

Telefon:

```text
http://<IP>:8000/health
```

adresine ulaşamıyorsa ağ profilini **"Özel"** yapın ve `8000` ile `8081` portlarına gelen bağlantılara izin verin.

### Telefon olmadan çalıştırmak

```bash
npx expo install react-dom react-native-web
npx expo start --web
```

ile aynı uygulama tarayıcıda çalışır.

Bu durumda `.env` içinde:

```text
http://localhost:8000
```

kullanılır.

---

# Testler

```bash
docker compose exec backend pytest -q
```

## Test sonucu

```text
-----------------148 passed-----------------
```

Toplam **148 test geçiyor.**

Testler ayrı bir test veritabanında (`tbr_test`) çalışır ve her testten önce şemayı sıfırlar; demo verisine dokunmaz.

Testlerde LLM kapalıdır (deterministik ve ücretsiz); LLM davranışı sahte bir OpenAI ile test edilir.

---

# Mimari Notlar

İş kuralları veritabanına dokunmayan saf fonksiyonlarda (`domain/`).

Üç mutasyon tool'u aynı kural fonksiyonunu kullanır.

Bütün tool çağrıları tek bir kapıdan (`registry.py`) geçer; her çağrı sıra numarası alır ve loglanır.

İki orkestratör (LLM ve kural tabanlı) aynı tool'ları aynı kapıdan çağırır.

Kurallar tek yerde durduğu için iki orkestratör de aynı kurallara uymak zorunda.

---

# Case'in Sorduğu Kararlar

## 1. Kaynak Bulma Yaklaşımı

### Ürünler

48 ürün için uygulama tarafında puanlama.

Metin normalleştirilir (Türkçe karakterler ve İ/I dönüşümü), kelimelere ayrılır, ad, Türkçe alias, etiket ve SKU ile eşleştirilir.

Türkçe ekler için basit bir önek toleransı var:

```text
"yazıcıyla" → "yazıcı"
```

Ardışık kelimeler ürün adında yan yana geçiyorsa ek puan verilir.

Her sonuçla birlikte eşleşme kanıtı (hangi kelimeler eşleşti) döner.

### Neden full-text veya embedding değil?

* Veride türkçe karakter tutarsızlığı var. PostgreSQL'in türkçe ayarı bunu eşitlemiyor (`şarj`, `sarj`).
* Dataset'te Plus varyantlar normal ürünlerin alias'larını birebir kopyalıyor. "Kullanıcı 'plus' demediyse Plus önerilmez" bir iş kuralı; arama motoruna bırakılamaz.
* Case eşleşme kanıtı istiyor.
* Web'den eklenen ürün yeniden indeksleme olmadan hemen aranabiliyor.

### Bilgi kayıtları

Konu, açık anahtar kelimelerle belirlenir:

```text
"iade" → return_policy
```

Konu bulunamazsa kaynak dönülmez ve cevap uydurulmaz.

İlk denemede kelime puanlaması `"hava durumu nasıl?"` sorusuna alakasız bir politikayı kaynak olarak döndürmüştü.

Yanlış kaynak göstermek kaynaksızlıktan daha tehlikeli olduğu için yöntem değiştirildi.

Bazı konuları kelimeler değil durum belirler. Örneğin stokta olmayan bir ürün istendiğinde stok kuralı devreye girer. Bu yüzden orkestratör konuyu açıkça da verebilir.

---

# Orkestrasyon

**Hibrit yapı:** Anahtar var ise önce LLM denenir; herhangi bir sorunda kural tabanlı router tüm sistemi devralır.

Anahtar yoksa doğrudan router çalışır.

## LLM Karar Verir, Yetki Sunucudadır

LLM yalnızca hangi işlemin yapılması gerektiğine karar verir. Asıl yetki ve iş kuralları sunucu tarafındadır.

| LLM'in yapabileceği hata                                              | Nasıl korunuyor?                                                                           |
| --------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Olmayan bir tool çağırmak                                             | Kapı yalnızca tanımlı 6 tool'u kabul eder.                                                 |
| Başka müşterinin teklifine dokunmak                                   | `quote_id` LLM tarafından seçilemez; sunucu tarafından eklenir.                            |
| Bütçeyi unutmak                                                       | Bütçe kullanıcının cümlesinden sunucu tarafından çıkarılır ve kural tool içinde uygulanır. |
| Soru soran kullanıcının teklifini değiştirmek                         | Soru cümlelerinde LLM'e mutasyon araçları gösterilmez.                                     |
| Teklifte olmayan bir ürüne "aynı / 1 tane daha" diyerek ekleme yapmak | Sunucu işlemi engeller ve router kullanıcıya sorar.                                        |
| Kaynaksız politika cevabı vermek                                      | Cevap reddedilir; router kaynaklı cevap üretir.                                            |
| Bozuk argüman, döngü, zaman aşımı veya API hatası                     | Router devralır ve en fazla 6 adım çalıştırır.                                             |

### Router

Router kural tabanlıdır.

Kullanıcının cümlesinden:

* eylem
* bütçe
* miktar
* "bekleyebilirim" bilgisi

çıkarılır.

En iyi arama sonucu yeterince net değilse (puan düşük veya sonuçlar eşitse) değişiklik yapılmaz.

Bunun yerine adayların sayısı kullanıcıya bildirilir ve seçim yapması istenir.

---

# Yedek Mod

Yedek modda LLM tamamen devre dışıdır.

| Garanti edilen davranış    | Açıklama                                                                                                                               |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| LLM çağrısı yapılmaz       | Cevaplar kayıtlı politika ve teklif verilerinden üretilir.                                                                             |
| Kaynak zorunluluğu         | Her politika cevabı en az bir `knowledge_id` kaynağı içerir. Konu bulunamazsa cevap uydurulmaz.                                        |
| Belirsiz mutasyon yapılmaz | Belirsiz ürün, boşta kalan atıf ("aynı ürün" teklifte yoksa) veya tanınmayan isteklerde sistem kullanıcıya soru sorar.                 |
| İş kuralları korunur       | Bütçe, stok, bekleyen kalem, tekrar satır ve idempotency kuralları LLM moduyla aynıdır. Çünkü bu kurallar tool'ların içinde uygulanır. |
| Yedek mod kaynağı          | Cevaplarda `KNE-FALL-001` kaynağı da gösterilir.                                                                                       |

---

# Idempotency Stratejisi

## Anahtar Üretimi

İstemci her mesaj için bir `message_id` üretir ve tekrar gönderimde aynı ID'yi kullanır.

Mutasyon anahtarı:

```text
{message_id}:{tool}:{product_id}
```

Anahtarın sunucu tarafından üretilmemesinin nedeni, aynı mesajın tekrar gönderildiğinde yeni bir istek olarak değerlendirilmesini önlemektir.

## Anahtarların Saklanması

Başlangıçta `quote_items.idempotency_key` alanının satır başına tek değer tutması planlanmıştı.

Ancak aynı satıra birden fazla istek gelebileceği için anahtarlar ayrı bir `idempotency_keys` tablosuna taşındı.

* Anahtar `PRIMARY KEY` olarak tutulur.
* İlk cevabın tamamı `JSONB` olarak saklanır.
* Aynı istek tekrar geldiğinde daha önce kaydedilmiş cevap döndürülür.

## Eş Zamanlılık

Teklif satırı:

```sql
SELECT ... FOR UPDATE
```

ile kilitlenir.

Idempotency kontrolü kilitten **sonra** yapılır.

Bunun nedeni, kontrol kilitten önce yapılırsa aynı anda gelen iki kopyanın da "anahtar yok" görerek aynı işlemi gerçekleştirebilmesidir.

Aynı isteğin 5 kopyası aynı anda gönderilerek bu durum test edilmiştir.

## Mesaj Seviyesi

`chat_messages.message_id` alanı `PRIMARY KEY` olarak kullanılır.

Böylece aynı mesaj tekrar gönderildiğinde ikinci kez kaydedilmez.

## Güncelleme İşlemleri

`update_quote_item` miktarı artırmaz, doğrudan belirtilen değere ayarlar.

Örneğin:

```text
"4 yap"
```

işlemi miktarı `4` olarak ayarlar.

Bu nedenle mutlak güncelleme işlemleri doğası gereği idempotenttir ve sözleşmede ayrıca idempotency anahtarına ihtiyaç duymaz.

## Yarıda Kalan LLM İşlemleri

LLM bir ürünü ekledikten sonra hata verirse router devralabilir ve aynı ürünü tekrar eklemeyi deneyebilir.

Ancak aynı idempotency anahtar kalıbı kullanıldığı için işlem ikinci kez uygulanmaz.

## Mobil

SSE kütüphanesinin varsayılan otomatik yeniden bağlanması (5 sn) kapatıldı.

Yoksa yayın bittikten sonra aynı POST tekrar gönderiliyordu.

---

# Teklif Mutasyon Modeli

## Tekrar Ekleme

Aynı teklifte aynı üründen tek aktif satır olur.

Bunu uygulama kodu değil, veritabanı garanti eder:

```sql
CREATE UNIQUE INDEX ...
ON quote_items (quote_id, product_id)
WHERE status = 'active';
```

Düz `UNIQUE` kullanılsaydı değiştirilmiş bir satır, ürünün yeniden eklenmesini engellerdi.

## Değiştirme

Eski satır silinmez:

```text
status = 'replaced'
```

olur ve `replaced_by_item_id` ile yeni satırı gösterir.

Önce yeni satır eklenir, sonra eski satır işaretlenir (foreign key sırası).

Alternatif zaten teklifteyse yeni satır açılmaz, mevcut satırın miktarı artırılır.

## Miktar 0

Satır `removed` olur; eski miktar geçmiş olarak kalır.

## Bekleyen Kalem

Ayrı `is_backorder` kolonu kullanılır.

"Satır teklifte mi?" ve "ürün stokta mı?" bağımsız sorular olduğu için status içine konmadı.

## Fiyat

Satır, eklendiği andaki fiyatı saklar.

Ürün fiyatı sonradan değişse de teklif değişmez.

## Ürün Silme

Ürün:

```text
active = false
```

yapılarak soft delete edilir.

Eski teklifler bozulmaz.

## Transaction

Mutasyon ve idempotency kaydı aynı transaction'da yapılır.

Tool logu ayrı transaction'da yazılır.

Böylece reddedilip geri alınan denemelerin de kaydı kalır.

## Toplamlar

İndirim ve toplamlar sadece backend'de (`get_quote`) hesaplanır.

Web ve mobil hesap yapmaz, aynı endpoint'ten okur.

---

# Bilinen Sınırlamalar

Bkz. [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md).

---

# İş Kuralları

Kontrol tek bir saf fonksiyonda ve bu sırayla yapılır:

1. Ürün pasif mi? → `inactive`
2. Fiyat, kullanıcının verdiği üst limitin üstünde mi? → `price_limit`
3. Stok 0 mı?

   * Kullanıcı açıkça beklemeyi kabul etmediyse → `out_of_stock`
   * Kabul ettiyse ama müşterinin `allow_backorder` değeri `false` ise → `backorder_not_allowed`
   * İkisi de sağlanıyorsa bekleyen kalem olarak eklenir.
4. Satırın toplam miktarı stoğu aşıyor mu? → `insufficient_stock`

---

# Belirsizliklerde Verilen Kararlar

| Durum                                          | Karar                                                         |
| ---------------------------------------------- | ------------------------------------------------------------- |
| Fiyat limite tam eşit                          | Kabul edilir (üst limit sınırı kapsar)                        |
| Stok var ama yetmiyor                          | Reddedilir ve mevcut stok söylenir; kısmi ekleme yapılmaz     |
| Aynı satıra birden fazla indirim kuralı uyuyor | Yüzdeler toplanır (SCN-019: %7 + %6)                          |
| Kit veya acil kurulum                          | Başka indirim uygulanmaz (engelleyici kurallar)               |
| Aksesuar indirimi kime uygulanır               | `price_rules` koşuluna uyularak tüm müşterilere               |
| Reddedilen isteğin anahtarı                    | Saklanmaz; hiçbir şey değişmediği için tekrar değerlendirilir |

---

# Dataset'te Bulunan Tuzaklar

| Tuzak                                                    | Çözüm                                                             |
| -------------------------------------------------------- | ----------------------------------------------------------------- |
| Plus varyantlar normal ürünlerin alias'larını kopyalıyor | Kullanıcı "plus" demediyse Plus önerilmez                         |
| Araç şarj adaptörü stokta yok, Plus'ı stokta             | Alternatif olarak Plus değil, kataloğun muadil listesi kullanılır |
| "offline" etiketi hem yazılımda hem 4G terminalde        | Uyumluluk ihtiyaçlarında kategori filtresi                        |
| "4 adede çıkar"                                          | Güncelleme (kaldırma değil)                                       |
| "Toplam 4 adet olsun" (teklifte 1 var)                   | Fark kadar ekleme                                                 |
| Cümlede "stok" geçmeyen stok durumu                      | Konuyu orkestratör durumdan belirler                              |
| Seed'deki tekil `idempotency_key` kolonu                 | Ayrı anahtar tablosu                                              |

---

# Streaming (SSE)

`POST /chat/stream` gövdesi:

```text
session_id
message_id (istemci üretir)
quote_id
text
channel
```

| Olay           | İçerik                                                                                                 |
| -------------- | ------------------------------------------------------------------------------------------------------ |
| `start`        | `session_id`, `message_id`, mod                                                                        |
| `tool_start`   | sıra numarası, tool adı, girdi özeti (teknik anahtarlar gizli)                                         |
| `tool_result`  | sıra numarası, başarı/hata, mutasyonsa teklif değişikliği (`quote_delta`), tekrar isteğiyse `replayed` |
| `sources`      | `product_id`, `knowledge_id`, uygulanan indirim kuralı                                                 |
| `text`         | cevap metni parçaları                                                                                  |
| `done / error` | bitiş veya hata                                                                                        |

Orkestratör senkron çalıştığı için ayrı bir thread'de çalıştırılır; olaylar bir kuyruk üzerinden, oluştukları anda istemciye iletilir.

---

# API

| Endpoint                                    | Açıklama                        |
| ------------------------------------------- | ------------------------------- |
| `POST /chat/stream`                         | Sohbet (SSE)                    |
| `GET /quotes`                               | Teklifler                       |
| `GET /quotes/{id}`                          | Teklif detayı                   |
| `GET/POST /products`                        | Ürünler                         |
| `PUT/DELETE /products/{id}`                 | Ürünler (silme = pasifleştirme) |
| `GET/POST /knowledge`                       | Bilgi kayıtları                 |
| `PUT/DELETE /knowledge/{id}`                | Bilgi kayıtları                 |
| `GET /sessions`                             | Sohbet oturumları               |
| `GET /sessions/{id}/messages`               | Sohbet mesajları                |
| `GET /logs?session_id=&message_id=&status=` | `tool` call logları             |

Web panelinin teklif okumaları loglanmaz; loglar asistanın adımlarını göstermek içindir.

---

# Test Kapsamı

| Case'in test sınıfı      | Nerede                                                                                     |
| ------------------------ | ------------------------------------------------------------------------------------------ |
| Retrieval ve grounding   | `test_search_products.py`, `test_get_knowledge_entries.py`                                 |
| Tool-call seçimi         | `test_golden.py` (beklenen çağrılar, sırası ve parametreleri)                              |
| Mutasyon davranışı       | `test_add_to_quote.py`, `test_update_quote_item.py`, `test_replace_with_alternative.py`    |
| Duplicate ve idempotency | Yukarıdakiler, `test_add_to_quote_concurrency.py`, `test_chat_stream.py`                   |
| Fiyat ve stok kuralları  | `test_validation.py` ve mutasyon testleri                                                  |
| Fallback                 | `test_health.py`, `test_golden.py` (anahtarsız), `test_llm.py` (LLM hatalarında yedek mod) |
| Web/mobil ortak durum    | `test_rest_api.py::test_mobile_mutation_visible_on_web`                                    |

### Golden senaryolar

Her senaryo için:

* beklenen çağrıların sırasıyla yapıldığı (aradaki ek çağrılara izin verilerek),
* yasaklı çağrıların hiç denenmediği,
* beklenen kaynakların cevapta olduğu,
* önerilmemesi gereken ürünlerin cevapta olmadığı,
* teklifin son durumu

kontrol edilir.

`quote_assertion` alanları metin olduğu için her biri koda çevrildi.

Testlerin gerçekten bir şey ölçtüğü, bir kural bilerek kaldırılarak doğrulandı.

Plus kuralı kaldırıldığında 5 senaryo kalıyor.

---

# Repo Yapısı

```text
db/
├── seed
├── uygulama şeması
└── test veritabanı

backend/
└── app/
    ├── domain/              saf kurallar (validation, search, knowledge, pricing, intent)
    ├── tools/               6 tool, ortak mutasyon adımları, registry
    ├── orchestrator/        router (kural tabanlı), llm
    └── api/                 chat (SSE), quotes, catalog, activity

backend/tests/               birim, entegrasyon, golden ve LLM testleri
web/                         React paneli
mobile/                      Expo uygulaması
```

Ayrıca:

```text
AI_USAGE.md
KNOWN_LIMITATIONS.md
```

---

## Not

README dosyası oluşturulurken veriler ve cümleler elle yazılıp AI(ChatGPT) tarafından düzenlenmiştir (tablolar, fonksiyonlar vs.).Elle yazılmış hali READMEV2.md olarak repoda bulunmaktadır.
