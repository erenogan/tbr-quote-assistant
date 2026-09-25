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


her testten sonra veritabanının tüm şemasını yok edip tekrar baştan yüklemek . bunun bedeli var hert test biraz yavaşlar ama toplamda 30 40 tane test var zaten bu yüzden create test dp ekledim tbr test ile çalıştırdık 
conftest ekledim her testin başında case_seed şeması siliniyor ve yeniden çalışıyor.

FAZ 2 GEÇİŞ YAPIYORUM

bu aşamada iş kurallarını ekleyeceğim 6 tool ekleyeceğim ve bunların testlerini 

İLK FONKSİYON validation fiyat limiti stok ve backorder kontrolünü yapacak
product customer max_price user accepts
add_to_quote ve replace_witj_alternative bunu çağırır

fiyat 9000 limit 9000 stok 2 allow backorder - bekleyebilirim - aktif evet eklenebiir evet  backorder hayır sebep -

fiyat 8000 limit 10000 stok 0 allow backorder true bekleyebilirim - aktif hayır eklenebilir hayır backorder hayır sebep kullanıcı demedi 

fiyat 8000 limit 10000 stok 0 allowbackorder false bekelyebilirim evet  aktif hayır eklenebilir hayır sebep  isbackorder

fiyat 8000 limit 10000 stok 0 allow true bekleyebilirim evet aktif evet eklenebilir evet  sebep -
 fiyat 8000 limit 7000 stok 0 allow true bekleyebilirim evet aktif hayır eklenebilir hayır sebep out of the stock

fiyat 8000 limit 10000 stok 0 allowtrue bekleyebilirim evet akfif hayır eklenebilir hayır sebep inactiv

yazdığım test senaryoları-----------üsttekiler


Birden fazla ihlal olursa hangisi sebep gösterilmeli 
 ürün pasifse ilk gerekçe bu inactive
 fiyat limiti ikinci seenek
 stok üçüncü seçenek
 backorder dört
 bekleyebilirim dedi mi son seçenek

 validation py yazdım domain içersine 
 gelelim toolları yazmaya
 ilk olarak search_products yazdım ve testlerini yaptım
 search products napıyor kullanıcının cümlsine göre en uygun ürünleri bulup listeliyor 
 dbden 48 tane ürünü alıyor
 soruguyu sadeleştiriyor
 filtreliyor
 puanlıyor 
 ve results veriyor 
 PLUS TUZAĞI BURADA*****
 STOKSUZ ÜRÜN GİZLENMEME TUZAĞI BURADA****
 TÜRKÇE KARAKTER BURADA****
 EŞLEŞME KANITI BURADA***

get_knowledge_entries ekledim 

get_quote kısmı zor dikkat
indirimlerin üst üste binme prblemi var
indirim yok kurallarına dikkat 
partner dışında bir de aksesuar indirimi var aksesuar indirimi pricerules dbsine göre herkese uygulanıyor partnerlere değil
kategori tuzağına dikkat 
indirim yüzdeliklerini toplamayı seçtim 

addquote geçiyorum burada çok fazla tuzak ve düzeltmem gereken durum var
araştırmama göre check then act race mantığı kullanılabilir yani kontrol et sonrayap

update için burada idempotency key yok bu tuzak mı ?
mutlak değer atarsak bu bir idempotent davranış olur
yani sistemlerin genelinde bir şeyi arttır diyip mutlak değer atamaktansa onu update yaparak güncellemek daha az sorun yaratır
scn 004 burada örnekleniyor test diyr ki ethernet fiş yazıcısını 4 adede çıkar diyor ancak sepette 2 var sonuç olarak 6 mı olacak 4 mü olacak test ediyor sonuçta bu bir updade ekleme değil yani idempotent yok
Verdiğim kararlar
miktar 0 ise removed etiketi yapıştırdık satır silinmeyecek eski miktar geçmiş olarak kalacak
kuralı sadece artışta kontrol edeceğiz
bütçe kontrolü de yokürün değişmez fiyat zaten eklenirken kabul edilmiş durumda

replacewithalternative NOTLARI
eski satırı replaced yapıyoruz ve kurala göre alternatifle değiştirebiliyoruz 
burada iş kurallarına bi çözüm buldun replaced by item id yani foreign key bunu unutma en başta yapmıştın
alternatif ürün sepette varsa?
mevcut olanı 1 arttırarak çözebiliriz buna bir test yazmak lazım
