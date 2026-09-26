# Bilinen Sınırlamalar

Bu belge, bilerek kapsam dışında bıraktığım veya zaman kısıtı nedeniyle basit tuttuğum konuları ve her birinin ne zaman değiştirilmesi gerektiğini listeler.

## Arama ve kaynak

| Sınırlama | Neden kabul edildi | Ne zaman değişmeli |
|---|---|---|
| Ürün araması tüm aktif ürünleri belleğe alıp uygulama tarafında puanlıyor | 48 ürün; eşleşme kanıtı ve Plus kuralı gerekiyordu | Katalog binlerce ürüne çıktığında: SQL'de filtre, Postgres full-text + `unaccent` + trigram |
| Türkçe ek toleransı basit bir önek kuralı | Veri setindeki ifadeler için yeterli | Daha serbest kullanıcı dili için gerçek bir kök bulma veya hibrit arama |
| Bilgi kaydı konusu sabit bir anahtar kelime listesiyle belirleniyor | Yanlış kaynak göstermemek, kelime puanlamasından daha güvenli | Listede olmayan ifadeler yakalanmaz; LLM modu bu esnekliği kısmen sağlıyor |
| Uyumluluk ihtiyaçları (4G terminal, offline lisans, şube modülü) `KNE-COMP-001`'in koda dökülmüş hali | Deterministik ve test edilebilir | Bilgi kaydı değişirse kod da elle güncellenmeli |

## Orkestrasyon

| Sınırlama | Açıklama |
|---|---|
| Kural tabanlı router kalıp tabanlı | Golden senaryoların kalıplarını ve benzerlerini anlar; dolaylı cümleleri anlamayabilir. Anlamadığında değişiklik yapmaz, sorar. |
| Değiştirme cümlesinin bölünmesi sezgisel | Çıkacak ve gelecek ürün Türkçe eklerle (-yı / -yla) ayrılıyor; alışılmadık cümle yapılarında yanılabilir. |
| LLM sohbet geçmişini görmüyor | LLM'e sadece son mesaj gidiyor; önceki mesajlara atıf yapan konuşmalar desteklenmiyor. |
| LLM modunda kaynak listesi LLM'in çağırdığı tool'lardan oluşuyor | Yedek modda bütçe politikası (`KNE-PRICE-001`) otomatik kaynak gösteriliyor; LLM modunda LLM kural kaydına bakmadıysa görünmeyebilir. Kural her iki modda aynı şekilde uygulanıyor. |
| LLM'in cevapta hangi kaydı kullandığı ayrıca doğrulanmıyor | Kaynaklar çağrılardan toplanıyor; politika sorusunda hiç kayıt yoksa cevap reddediliyor. |
| Model adı `.env`'den geliyor | Farklı modellerle davranış değişebilir; testler LLM'i taklit ederek yapıldı. |

## Streaming

| Sınırlama | Açıklama |
|---|---|
| Yedek modda metin gerçek zamanlı üretilmiyor | Cevap tek seferde üretilip parçalara bölünerek aktarılıyor. Gerçek zamanlı olan kısım tool olayları. |
| LLM modunda token streaming yok | LLM cevabı tamamlandıktan sonra parçalanıyor. |
| SSE, istek başına bir thread kullanıyor | Yüksek eş zamanlı yükte asenkron bir yapıya geçilmeli. |

## İş kuralları

| Sınırlama | Açıklama |
|---|---|
| Stok yetersizse kısmi ekleme yok | "10 istendi, 4 var" durumunda istek reddedilir ve mevcut stok söylenir; karar kullanıcıya bırakılır. |
| İndirimler toplanıyor | PDF üst üste binmeyi tanımlamıyor; SCN-019'da iki indirimin de görünmesi için toplamayı seçtim. Kademeli hesap da mümkündü. |
| Aksesuar indiriminin kapsamı | Bilgi kaydı ile `price_rules` arasında belirsizlik vardı; `price_rules`'a uyuldu. |
| Taslak teklif stok rezervasyonu yapmıyor | `KNE-QUOTE-001` ile uyumlu; stok kontrolü ekleme anındaki stoğa göre. |

## Web ve mobil

| Sınırlama | Açıklama |
|---|---|
| Web teklifi 2 saniyede bir okuyor (polling) | Mobildeki değişiklik web'e en fazla 2 saniye gecikmeyle yansır. Çok kullanıcılı kullanımda push'a geçilmeli. |
| iOS'ta Expo Go giriş gerektiriyor | Expo SDK 57 ile birlikte fiziksel iOS cihazlarda Expo CLI ve Expo Go'nun aynı Expo hesabıyla giriş yapması gerekiyor (`npx expo login --browser`). Mobil uygulama `npx expo start --web` ile tarayıcıda da çalışıyor. |
| Mobilde API adresi elle ayarlanıyor | `mobile/.env` içinde bilgisayarın Wi-Fi IP'si yazılmalı. |

## Güvenlik ve üretim hazırlığı

Bu proje yerel bir demo olarak tasarlandı. Üretime çıkmadan önce gerekenler:

- Kimlik doğrulama ve yetkilendirme (şu an herkes her teklife erişebiliyor).
- CORS şu an bütün kaynaklara açık; web'in adresiyle sınırlanmalı.
- İstek sınırlama (rate limiting).
- Şema değişiklikleri için bir migration aracı (şu an init script'leri kullanılıyor).
- `idempotency_keys` tablosu için süre dolumu ve temizlik.
- Metrikler ve izleme.
- Prompt injection: Bilgi kaydı metinleri LLM bağlamına giriyor. LLM enjekte edilmiş bir talimata uysa bile teklif numarası, bütçe ve anahtarlar sunucu tarafından verildiği ve kurallar tool'ların içinde olduğu için yetkisi sınırlı; yine de metinlerin ayrıca temizlenmesi düşünülmeli.

## Testler

- Golden senaryolardaki `quote_assertion` alanları metin olduğu için her biri elle koda çevrildi.
- Golden testlerde beklenen çağrıların sırasıyla yapılması kontrol ediliyor; araya giren ek çağrılara (örneğin mutasyondan sonra teklifi tekrar okumak) izin veriliyor.
- LLM gerçek API ile değil, sahte bir istemciyle test edildi; gerçek model davranışı elle doğrulandı.