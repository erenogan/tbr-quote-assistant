İlk aşamayı bitirdim------

Docker+Postgres+seed,Github
seed verisi otomatik olarak çekiliyor

İkinci aşama olarak-----TASARIM-----
 Veri Modelini inceledim ve eksikleri çözmeye odaklandım

idempotency_keys PROBLEMİ*----------------------
Bu problem quote_items.idempotency_key satırında satır başına tek 1 tane istek düşebiliyor ancak bir satıra birden fazla istek gelebilir gelen bu isteklerin tutulması için ayrı bir tablo oluşturdum idempotency_keys tablosu

Aynı üründen iki aktif satır olmamalı PROBLEMİ*-------------------------------
Bunun için araştırmalarıma göre önüme birden fazla çözüm çıktı ancak PostgreSQL ile çalıştığım için en etkili çözüm kısıt vermekti ancak kısıtı tüm tabloya değil sadece aktif olan satırlara uyguladım. Yani Partial Unique Index uyguladım

Değiştirilen ürün sepette üstü çizilmiş şekilde gösterilmeli PROBLEMİ*-------
Eski satırı silmeden yeni bir satır oluşturarak eski satıra yeni bir kolon eklerim mesela replaced_by_item_id bu kolon yeni satırın item idsini taşır ancak yeni gelen ürünün bu kolonu NULL olur böylelikle bu ürünün aktif olan ürün olduğunu anlayabiliriz.

 Bekleyen ürün isteği----------
  isbackorder kontrolü ile bu durumu çözerim bir kullanıcı stokta olmayan bir ürünü bekleyebilirim diyerek kesin bir şekilde bunu belirtirse bu yeterli olmaz aynı zamanda kullanıcının tablosunda backorder durumunun true olması gerekir yyani allow_backorder kolonu kontrol edilmeli TRUE ise bekleyen ürün olarak işaretlenebilir.

  tool_call_logs isteği--------------
  istenilen isteğe göre rbotun ne yaptığı izlenilmek istiyor bu yüzden tool_call_logs oluştururum kolonları ise satırın idsi olur session idsi olur hangi sohbet bunu biliriz messageid olur hangi mesaj olduğuna dair sequence olur o mesjaın içinde kaçıncı çağrı sırası olduğu sonra tool name hangi tool çağırıldı kontrol için input olurdu  status olurdu başarılı mı error mu diye kontrol için output olurdu sonuç olarak ne yapıldıysa bir de created at olurdu ne zaman oluşturuldu.


  Sohbetlerin saklanması isteği------------------
  burada log tablosundan gelen verileri iki ayrı tabloya bölerim oturumdaki mesajlar ve oturum bilgileri olarak böylelikle sohbeti paylaşmak için ayrı bir tablo oluşturabilmiş olurum

  ###Deterministik bir yapı LLM isteğinden önce geliyor yani hataya yer olmasını istemiyorlar çok bariz belli. İki durumda da 6 tool net şekilde çağırılmalı####
  
  Webi güncelleme problemi*-------------------
  burada iki çözüm var ya verileri veri geldikçe push edeceğim ya da sistem 3 saniyede bir kontrol edip kendisi iletecek bu da polling oluyor araştırdım zaman kısıtlı olduğu için push biraz daha zahmetli olacağından ötürü seçimimi pollingden yana kullanıyorum yani 3 4 saniyede bir sistemi kontrol edip verileri iletecek bu de küçük bir gecikmeye yol açacak bu sistemin gizlenmesini istemediğim bir dezavantajıdır


  Retrieval kısmı için---------
Embedding kullanmama gerek yok gibi çünkü 70 tane kayıt var sadece hepsini full text olarak postgresqlden alabilirim.


Sepetten ürün silme yok isteği--------------
replaced/removed/active=false kullanarak bu durumu çözeceğim gibi duruyor henüz kod üzerinde ekleme yapmadım


Fiyat limiti kuralı----------
burası önemli gibi geldi bu yüzden dikkat et fıyat kuralını ihlal etmek diskalifiye sebebi çünkü bu yüzden limiti regex ile yakalayıp context içerisinekoyabilirsin add ve replace ortak bir fonksiyonla bunu kontrol eder backorderdan önce kontrol edilir 

Message_id NULL olabiliyor bu nasıl mümkün olabilir diye araştırma yaptım önüme çıkan sonuç testlerden kaynaklandığını söylüyor örneğin test yaparken toolu sohbet ya da mesaj olmadan çağırıyoruz bu yüzden message_id NULL olabiliyor**********


APPSCHEMA ile yukarıda ekleyeceğim tüm tabloları ve kolonları ekledim*"*"*"*"*""*

Şimdi FAZ1B ADIM 2 GEÇİYORUM

burada mekanik işlemler olacak dikkat et.
DB erişimi için 2 tane seçenek var ORM ve psycopg orm benim eklediğim özelliklei saklıyor ancak ben sistemin bunları eklediğimde nasıl tepki verdiğini görmek istiyorum ve anlatabilmek bu yüzden psycopg ama burada bunun bir bedeli var sql'i elle yazacağım.

Şuanda requirements dosyasını oluşturdum 24.09.13.25
dockerfile dosyasını oluşturdum host aşamasını 0.0..0 yaptım şuana kadar ki projelerimde hep 127.0.0.1 idi bu yüzden araştırma yaptım. 127 olan sadece içerden gelen istekleri kabul ediyor çoklu platformda telefondan ya da tarayıcıdıan gelen isteği reddediyor ancak 0.0.0.0 her yerden kabul ediyor.******YENİ BİR BİLGİ 

config.py dosyasını oluşturdum bu dosya otomatik veri okumama eksik ayar okumama yarayacak. yani ayarları okuyacak

db.py ekledim burası veritabanı ile bağlantılarını yönetecek
burada transaciton bağlatnısına dikkat et pdfte mutasyon ile ilgili bir tuzak vardı bu yüzden burada with bloğu kullanılabilir blok başarıyla biterse commit at olmazsa rollback yap sonra bağlantı havuza geri dönsün her iki durumda da

ve main.py ekledim sunucuyu ayağ kaldırıyoruz dockerfile dosyasındakı app.main de bunu referans alıyor zaten çerisine mode ekledim return içine çünkü yine deterministik bir yapı kaynaklı bence sistem deterministik istendiği için sürekli fallback çalışıyor mu bunu görebilmek istiyoruz


