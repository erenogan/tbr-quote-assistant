# Yapay Zeka Kullanımı

Bu projeyi Anthropic'in Claude modeliyle birlikte geliştirdim. Bu belge ise hangi işlerde nasıl kullandığımı hangi kararların bana ait olduğunu ve ürettiğim kodu nasıl doğruladığımı açıklıyor

## Nasıl çalıştım

Amacım sadece çalışan bir teslim çıkarmak değil, her kararın nedenini anlayıp savunabilmekti. Bu yüzden Claude'u iki farklı şekilde kullandım:

-Öğretici olarak: Veri modeli ve iş kuralları  konularında Claude'dan çözümü vermek yerine bana sorular sormasını istedim. Tasarımı bu sorulara cevap vererek ve yanlış cevaplarımı düzelterek oluşturdum.

Kod üreticisi olarak: Router, LLM katmanı, SSE, REST API, web paneli ve mobil uygulamanın kodunun büyük kısmını Claude yazdı. Ben her parçayı çalıştırdım, testleri geçirdim ve davranışlarını kendim kontrol ettim.

Proje LLM dışında deterministik bir yapı istediği için bende çalışırken kararları LLM'e bırakmaktan çok seçenekler araştırıp kararları kendim verdim.Yani evet herkes gibi projemde AI kullandım ancak onun kontrol etmesini değil kendim kontrol etmemi ve kararler vermemi sağladım.Yani nasıl proje deterministik bir sistem istiyor ise benim çalışma sistemimi de buna benzetebiliriz bende deterministik bir yapıyla son kararı kendime bıraktım.

## Benim yaptıklarım ve kararlarım

- Case'i analiz ettim ve asıl ölçülen şeyin "LLM hata yapsa bile kuralların bozulmaması" olduğu sonucuna vardım.
- **Veri modeli:** Verilen şemadaki idempotency eksikliğini veriyi ilk incelediğimmde fark ettim.Araştırmalarıma göre burada  bire-çok ilişki vardı. Bu yüzdn ayrı bir tablo tasarladım; ikinci aktif satır sorununda sistemin düz UNIQUE neden izin vermediğini anlayıp PARTIAL UNIQUE INDEX kullandım.`replaced_by_item_id` ve oturum tablolarını tasarladım.
- **İş kuralları:** Kasa kurallarının test tablosunu yazdım ve belirsiz durumlarda  kararları verdim. Mesela fiyat limite eşitse eklenebilir kararı , stok yetmeme durumunda verilen output.
- **LLM'i ekleme kararı:** Zaman kısıtından dolayı en başta LLM eklememeyi düşündüm sadece deterministik bir yapı çıkaracaktım ancak daha sonra ekledim ve testleri sadece LLM'in yanlış senaryolar ürettiği durumlar üzerinden test ettim.
- **Elle test:** Mobil uygulamayı telefonda denerken teklifte olmayan bir ürüne "aynı üründen 2 tane daha ekle" dediğimde hem router beyin hem LLM'in ürünü eklediğini fark ettim. Otomatik testlerin hiçbiri bu durumu kapsamıyordu. Düzeltme ve iki yeni test ekledim ve durumu çözdüm.

## Claude'un yaptıkları

- Router, LLM katmanı, SSE endpoint'i, REST API, web paneli ve mobil uygulamanın kodu.
- Golden senaryoları uçtan uca çalıştıran test altyapısı.
- Dokümantasyon düzenlemeleri.

## Doğrulama yöntemim

- Her adımda bir çok test çalıştırdım; bu sayede verilen tüm golden senaryoların otomatikmen geçmesini sağladım.
- Testlerin gerçekten bir şey ölçtüğünü görmek için kuralları bilerek bozdum örneğin PLUS problemindeki kuralı kaldırdığımda sistem 5 tane golden senaryodan kaldı.Ya da kural sırasını kaldırdığımda ve fiyat limitini daha sonraya aldığımda fiyat limitini dinlemeden önce stok kontrolü yapıp ekleyebiliyordu.
- Eş zamanlılık problemini aynı anda 5 tane isteği göndererek çözdüm
- SSE çıktısını, web ve mobil ekranların tasarımlarını elle inceledim ve kontrol ettim.

## Süreçte yakalanan hatalar

Boşta kalan atıflar vardı, teklifte olmayan bir ürüne aynı üründen ekle diyince ekleme yapıyordu. Bu hatayı mobilden kurduğum sistemi denerken fark ettim ve düzelttim.
ilk arama yönteminde hava durumu sorduğunda "durum" kelimesinden politika cevabı döndürüyordu. yöntemi değiştirdim anlam bağlamıyla hareket ettirdim
SSE katmanında teklif değişikliğinde delta gözükmüyordu bu yüzden  replace_with_alternative için status oluşturdum
mobil sse kütüphanesi aynı isteği 5 saniyede bir tekrar gönderiyordu bunu kütüphanenin kaynak kodunu okurken fark ettim
bir durumda da kendi hatamı var idi ben kullanıcı açık şekilde bekleyebililrim der ise allow_backorder=True olacak zannediyordum ancak o durum müşterinin sabit değiştirilemez bir özelliğiymiş. Tasarım yaparkn düzelttim

## Öğrendiklerim
Idempotency_key ile ilgili bir sürü kural öğrendim bir satıra birden fazla isteğin düzeltilmesi.
Kararı kesinlikle LLM vermemeli ve deterministik bir yapı çıkmalı bunu öğrendim
Sistem LLM olmadığı durumda fallback olmalı ve ikinci beyin çalışmalı bu nasıl güvenilir şekilde oluşturulur bunu öğrendim yani LLM karar verici değil sadece bir aracı olacaktı kuralları yapıya bağladım ve testlerin bir çok şeyi gerçekten ölçtüğünü öğrendim
Oluşturulan 22 golden testi geçmek için bölüm bölüm toplamda 150'yi aşkın test yaptım amacım 22 golden testi başarı ile otomatik olarak geçmekti yani testleri genelden özele indirmeyi öğrendim.
Veride bir çok tuzak vardı eksikti onları nasıl düzelteceğimi öğrendim ve app_schema ekleyerek verideki düzeltmelerimi yaptım
İş kuralları konusunda deterministik yapıdan güvenilir bir şekilde sonuç nasıl alınır işleyiş nasıl olur öğrendim
Transaction yapısında log kısmını neden ayrı oluşturmalıyım bunu öğrendim

