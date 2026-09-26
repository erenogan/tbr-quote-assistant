Yapay Zeka Destekli Teklif Asistanı

B2B müşterilerin mobil sohbetten ürün ve politika sorusu sorduğu, asistanın cevabını kaynaklarla verdiği ve gerektiğinde ortak bir teklif üzerinde gerçek değişiklik yaptığı bir sistem. Web paneli aynı teklifi canlı olarak gösterir.

Backend: FastAPI, PostgreSQL, psycopg (ORM yok)
Web: React (Vite), nginx
Mobil: React Native (Expo SDK 57)
LLM: OpenAI tool calling (opsiyonel); anahtar yoksa kural tabanlı yedek mod
Çalıştırma: Docker Compose

22 golden senaryonun tamamı uçtan uca otomatik testlerle geçiyor.

Gereksinimler

Docker Desktop, Git. Mobil için Node.js LTS ve telefonda Expo Go.

Backend, veritabanı ve web

git clone <repo-url>
cd tbr-quote-assistant
cp .env.example .env          # Windows: Copy-Item .env.example .env
docker compose up -d --build --wait


http://localhost:5173:	Web paneli

http://localhost:8000/docs :	API belgeleri (Swagger)

http://localhost:8000/health:	Sağlık kontrolü ve mod (Sistem llm modunda mı fallback modunda mı?)

Seed verisi ilk açılışta otomatik yüklenir

db/01_seed.sql, ardından db/02_app_schema.sql.
 Veritabanını sıfırlamak için:
 docker compose down -v && docker compose up -d --wait

 LLM modu : .env içine OPENAI_API_KEY ve OPENAI_MODEL yazın, sonra backend'i yeniden oluşturun (.env sadece container oluşturulurken okunur):

 docker compose up -d --force-recreate --wait backend

 Anahtar boşsa sistem yedek modda çalışır; bu, case'in fallback gereksinimini doğrudan gösterir.

 MOBİL KISIM

 cd mobile
npm install
cp .env.example .env          # EXPO_PUBLIC_API_URL=http://<bilgisayarın-Wi-Fi-IP'si>:8000
npx expo start

QR kodu Expo Go ile tarayın. Telefon ve bilgisayar aynı ağda olmalı. Telefonda localhost telefonun kendisini gösterdiği için adres olarak bilgisayarın Wi-Fi IP'si kullanılır.

iPhone: Expo SDK 57 ile birlikte iOS'taki Expo Go, geliştirme sunucusundan proje açmak için Expo CLI ve Expo Go'nun aynı Expo hesabıyla giriş yapmış olmasını istiyor. Bilgisayarda npx expo login --browser ile giriş yapıp telefonda "Try Again"e basın.

Windows güvenlik duvarı: Telefon http://<IP>:8000/health adresine ulaşamıyorsa ağ profilini "Özel" yapın ve 8000 ile 8081 portlarına gelen bağlantılara izin verin.

Telefon olmadan: npx expo install react-dom react-native-web ve npx expo start --web ile aynı uygulama tarayıcıda çalışır (.env içinde http://localhost:8000).

TESTLER

docker compose exec backend pytest -q

tests/test_add_to_quote.py::test_adds_new_line_scn001 PASSED [  0%]
tests/test_add_to_quote.py::test_readding_increments_instead_of_new_line_scn003 PASSED [  1%]
tests/test_add_to_quote.py::test_same_key_twice_increments_once_scn010 PASSED [  2%]
tests/test_add_to_quote.py::test_different_keys_increment_twice PASSED [  2%]
tests/test_add_to_quote.py::test_price_limit_rejects_and_writes_nothing PASSED [  3%]
tests/test_add_to_quote.py::test_backorder_not_allowed_for_customer_scn002 PASSED [  4%]
tests/test_add_to_quote.py::test_out_of_stock_without_user_consent PASSED [  4%]
tests/test_add_to_quote.py::test_backorder_line_when_both_conditions_met PASSED [  5%]
tests/test_add_to_quote.py::test_stock_checked_on_total_line_quantity PASSED [  6%]
tests/test_add_to_quote.py::test_price_snapshot_is_stored PASSED [  6%]
tests/test_add_to_quote.py::test_idempotency_record_is_saved PASSED [  7%]
tests/test_add_to_quote.py::test_invalid_requests[Q-9999-PRD-BC-110-1-quote_not_found] PASSED [  8%]
tests/test_add_to_quote.py::test_invalid_requests[Q-1002-PRD-YOK-000-1-product_not_found] PASSED [  8%]
tests/test_add_to_quote.py::test_invalid_requests[Q-1002-PRD-BC-110-0-invalid_quantity] PASSED [  9%]
tests/test_add_to_quote_concurrency.py::test_concurrent_duplicate_requests_increment_once PASSED [ 10%]
tests/test_chat_stream.py::test_event_order_start_tools_sources_text_done PASSED [ 10%]
tests/test_chat_stream.py::test_every_tool_start_has_matching_result PASSED [ 11%]
tests/test_chat_stream.py::test_mutation_result_carries_quote_delta PASSED [ 12%]
tests/test_chat_stream.py::test_input_summary_hides_technical_keys PASSED [ 12%]
tests/test_chat_stream.py::test_sources_and_text_are_streamed PASSED [ 13%]
tests/test_chat_stream.py::test_retry_same_message_id_does_not_double_apply PASSED [ 14%]
tests/test_chat_stream.py::test_invalid_request_rejected PASSED [ 14%]
tests/test_chat_stream.py::test_unknown_quote_is_controlled_not_crash PASSED [ 15%]
tests/test_chat_stream.py::test_replace_result_carries_quote_delta PASSED [ 16%]
tests/test_get_knowledge_entries.py::test_topic_inferred_from_golden_messages[SCN-007-Aktive edilmi\u015f yaz\u0131l\u0131m lisans\u0131n\u0131 iade edebilir miyiz?-return_policy] PASSED [ 16%]
tests/test_get_knowledge_entries.py::test_topic_inferred_from_golden_messages[SCN-008-Sahada internet olmayacak; 4G'li el terminali ve offline senkron i\xe7in gereken lisans\u0131 ekle.-compatibility] PASSED [ 17%]
tests/test_get_knowledge_entries.py::test_topic_inferred_from_golden_messages[SCN-009-\u0130ade s\xfcresi nedir ve teklifimde hangi \xfcr\xfcn var?-return_policy] PASSED [ 18%]
tests/test_get_knowledge_entries.py::test_topic_inferred_from_golden_messages[SCN-011-Depo i\xe7in 3 adet BlueScan Air ekle; partner indirimini de g\xf6ster.-discount_policy] PASSED [ 18%]
tests/test_get_knowledge_entries.py::test_topic_inferred_from_golden_messages[SCN-015-Yerinde kurulum hizmetini 2 lokasyon i\xe7in g\xfcncelle.-service_policy] PASSED [ 19%]
tests/test_get_knowledge_entries.py::test_topic_inferred_from_golden_messages[SCN-017-Offline senkron ve \u015fube senkronu i\xe7in gerekli yaz\u0131l\u0131mlar\u0131 ekle.-compatibility] PASSED [ 20%]
tests/test_get_knowledge_entries.py::test_topic_inferred_from_golden_messages[SCN-018-\u0130zmir i\xe7in yar\u0131na acil kurulum kesin diyebilir miyiz?-service_policy] PASSED [ 20%]
tests/test_get_knowledge_entries.py::test_topic_inferred_from_golden_messages[SCN-019-BlueScan Air Plus toplam 4 adet olsun, varsa hacim indirimini g\xf6ster.-discount_policy] PASSED [ 21%]
tests/test_get_knowledge_entries.py::test_topic_inferred_from_golden_messages[SCN-021-Stokta olan donan\u0131mlar i\xe7in teslimat kural\u0131 nedir?-delivery_policy] PASSED [ 22%]
tests/test_get_knowledge_entries.py::test_main_policy_comes_before_note PASSED [ 22%]
tests/test_get_knowledge_entries.py::test_given_topic_overrides_inference PASSED [ 23%]
tests/test_get_knowledge_entries.py::test_unknown_topic_returns_no_sources PASSED [ 24%]
tests/test_get_knowledge_entries.py::test_every_entry_has_knowledge_id_and_source PASSED [ 25%]
tests/test_get_quote.py::test_seed_quote_totals PASSED   [ 25%]
tests/test_get_quote.py::test_partner_category_discount_scn011 PASSED [ 26%]
tests/test_get_quote.py::test_standard_customer_gets_no_partner_discount PASSED [ 27%]
tests/test_get_quote.py::test_plus_discount_visible_scn019 PASSED [ 27%]
tests/test_get_quote.py::test_bundle_blocks_other_discounts PASSED [ 28%]
tests/test_get_quote.py::test_inactive_lines_listed_but_not_totaled PASSED [ 29%]
tests/test_get_quote.py::test_unknown_quote_raises_tool_error PASSED [ 29%]
tests/test_get_quote.py::test_all_rule_ids_exist_in_db PASSED [ 30%]
tests/test_golden.py::test_golden_scenario[SCN-001] PASSED [ 31%]
tests/test_golden.py::test_golden_scenario[SCN-002] PASSED [ 31%]
tests/test_golden.py::test_golden_scenario[SCN-003] PASSED [ 32%]
tests/test_golden.py::test_golden_scenario[SCN-004] PASSED [ 33%]
tests/test_golden.py::test_golden_scenario[SCN-005] PASSED [ 33%]
tests/test_golden.py::test_golden_scenario[SCN-006] PASSED [ 34%]
tests/test_golden.py::test_golden_scenario[SCN-007] PASSED [ 35%]
tests/test_golden.py::test_golden_scenario[SCN-008] PASSED [ 35%]
tests/test_golden.py::test_golden_scenario[SCN-009] PASSED [ 36%]
tests/test_golden.py::test_golden_scenario[SCN-010] PASSED [ 37%]
tests/test_golden.py::test_golden_scenario[SCN-011] PASSED [ 37%]
tests/test_golden.py::test_golden_scenario[SCN-012] PASSED [ 38%]
tests/test_golden.py::test_golden_scenario[SCN-013] PASSED [ 39%]
tests/test_golden.py::test_golden_scenario[SCN-014] PASSED [ 39%]
tests/test_golden.py::test_golden_scenario[SCN-015] PASSED [ 40%]
tests/test_golden.py::test_golden_scenario[SCN-016] PASSED [ 41%]
tests/test_golden.py::test_golden_scenario[SCN-017] PASSED [ 41%]
tests/test_golden.py::test_golden_scenario[SCN-018] PASSED [ 42%]
tests/test_golden.py::test_golden_scenario[SCN-019] PASSED [ 43%]
tests/test_golden.py::test_golden_scenario[SCN-020] PASSED [ 43%]
tests/test_golden.py::test_golden_scenario[SCN-021] PASSED [ 44%]
tests/test_golden.py::test_golden_scenario[SCN-022] PASSED [ 45%]
tests/test_golden.py::test_scn018_does_not_promise_urgent_install_in_izmir PASSED [ 45%]
tests/test_golden.py::test_every_call_is_logged PASSED   [ 46%]
tests/test_health.py::test_health_fallback_mode PASSED   [ 47%]
tests/test_isolation.py::test_a_modifies_quote PASSED    [ 47%]
tests/test_isolation.py::test_b_sees_clean_state PASSED  [ 48%]
tests/test_llm.py::test_llm_happy_path_goes_through_registry PASSED [ 49%]
tests/test_llm.py::test_server_injects_budget_quote_and_key PASSED [ 50%]
tests/test_llm.py::test_llm_cannot_break_price_limit PASSED [ 50%]
tests/test_llm.py::test_llm_cannot_touch_another_customers_quote PASSED [ 51%]
tests/test_llm.py::test_question_gets_no_mutation_tools PASSED [ 52%]
tests/test_llm.py::test_forbidden_tool_on_question_falls_back PASSED [ 52%]
tests/test_llm.py::test_unsourced_policy_answer_falls_back PASSED [ 53%]
tests/test_llm.py::test_openai_outage_falls_back PASSED  [ 54%]
tests/test_llm.py::test_partial_llm_then_fallback_does_not_double_add PASSED [ 54%]
tests/test_llm.py::test_malformed_arguments_fall_back PASSED [ 55%]
tests/test_llm.py::test_step_limit_falls_back PASSED     [ 56%]
tests/test_llm.py::test_llm_cannot_invent_referenced_item PASSED [ 56%]
tests/test_registry.py::test_successful_call_is_logged PASSED [ 57%]
tests/test_registry.py::test_calls_get_increasing_sequence_numbers PASSED [ 58%]
tests/test_registry.py::test_decimal_input_is_logged_as_text PASSED [ 58%]
tests/test_registry.py::test_rejected_mutation_is_logged_but_quote_unchanged PASSED [ 59%]
tests/test_registry.py::test_logs_linked_to_session_and_message PASSED [ 60%]
tests/test_registry.py::test_unknown_tool_is_refused PASSED [ 60%]
tests/test_replace_with_alternative.py::test_expensive_to_cheaper_scn005 PASSED [ 61%]
tests/test_replace_with_alternative.py::test_keeps_quantity_scn006 PASSED [ 62%]
tests/test_replace_with_alternative.py::test_mobile_printer_to_ethernet_scn014 PASSED [ 62%]
tests/test_replace_with_alternative.py::test_only_one_active_equivalent_remains PASSED [ 63%]
tests/test_replace_with_alternative.py::test_alternative_over_price_limit_rejected PASSED [ 64%]
tests/test_replace_with_alternative.py::test_out_of_stock_alternative_rejected PASSED [ 64%]
tests/test_replace_with_alternative.py::test_same_key_twice_replaces_once PASSED [ 65%]
tests/test_replace_with_alternative.py::test_target_already_in_quote_merges_into_existing_line PASSED [ 66%]
tests/test_replace_with_alternative.py::test_missing_source_line_raises PASSED [ 66%]
tests/test_rest_api.py::test_list_quotes PASSED          [ 67%]
tests/test_rest_api.py::test_read_quote_and_404 PASSED   [ 68%]
tests/test_rest_api.py::test_mobile_mutation_visible_on_web PASSED [ 68%]
tests/test_rest_api.py::test_create_and_list_product PASSED [ 69%]
tests/test_rest_api.py::test_duplicate_product_is_409 PASSED [ 70%]
tests/test_rest_api.py::test_invalid_product_is_422 PASSED [ 70%]
tests/test_rest_api.py::test_new_product_is_searchable_immediately PASSED [ 71%]
tests/test_rest_api.py::test_price_change_does_not_change_existing_quote PASSED [ 72%]
tests/test_rest_api.py::test_delete_deactivates_and_keeps_old_quotes PASSED [ 72%]
tests/test_rest_api.py::test_create_knowledge_used_as_source PASSED [ 73%]
tests/test_rest_api.py::test_list_knowledge_by_topic PASSED [ 74%]
tests/test_rest_api.py::test_sessions_messages_and_logs PASSED [ 75%]
tests/test_rest_api.py::test_logs_filter_errors PASSED   [ 75%]
tests/test_router_behaviour.py::test_backorder_refused_offers_in_stock_alternatives PASSED [ 76%]
tests/test_router_behaviour.py::test_backorder_accepted_when_customer_allows PASSED [ 77%]
tests/test_router_behaviour.py::test_ambiguous_request_asks_instead_of_guessing PASSED [ 77%]
tests/test_router_behaviour.py::test_reference_to_missing_item_asks_instead_of_adding PASSED [ 78%]
tests/test_search_products.py::test_golden_queries_find_expected_product[SCN-001-kablosuz QR barkod okuyucu-kwargs0-PRD-BC-110] PASSED [ 79%]
tests/test_search_products.py::test_golden_queries_find_expected_product[SCN-008-4G el terminali-kwargs1-PRD-POS-210] PASSED [ 79%]
tests/test_search_products.py::test_golden_queries_find_expected_product[SCN-011-Depo i\xe7in 3 adet BlueScan Air ekle-kwargs2-PRD-BC-110] PASSED [ 80%]
tests/test_search_products.py::test_golden_queries_find_expected_product[SCN-012-koruyucu k\u0131l\u0131f-kwargs3-PRD-ACC-710] PASSED [ 81%]
tests/test_search_products.py::test_golden_queries_find_expected_product[SCN-014-Ethernet fi\u015f yaz\u0131c\u0131-kwargs4-PRD-PRN-320] PASSED [ 81%]
tests/test_search_products.py::test_golden_queries_find_expected_product[SCN-017-offline senkron lisans-kwargs5-PRD-SW-520] PASSED [ 82%]
tests/test_search_products.py::test_golden_queries_find_expected_product[SCN-020-kablosuz QR okuyucu-kwargs6-PRD-BC-110] PASSED [ 83%]
tests/test_search_products.py::test_golden_queries_find_expected_product[SCN-022-USB-C h\u0131zl\u0131 \u015farj-kwargs7-PRD-ACC-740] PASSED [ 83%]
tests/test_search_products.py::test_golden_queries_find_expected_product[SCN-019-BlueScan Air Plus-kwargs8-PRD-BC-110-PLUS] PASSED [ 84%]
tests/test_search_products.py::test_price_limit_is_hard_filter PASSED [ 85%]
tests/test_search_products.py::test_out_of_stock_is_reported_not_recommended PASSED [ 85%]
tests/test_search_products.py::test_plus_variant_not_suggested_as_stock_alternative PASSED [ 86%]
tests/test_search_products.py::test_turkish_suffix_and_characters PASSED [ 87%]
tests/test_search_products.py::test_evidence_is_returned PASSED [ 87%]
tests/test_update_quote_item.py::test_sets_quantity_scn004 PASSED [ 88%]
tests/test_update_quote_item.py::test_service_quantity_scn015 PASSED [ 89%]
tests/test_update_quote_item.py::test_same_update_twice_is_naturally_idempotent PASSED [ 89%]
tests/test_update_quote_item.py::test_zero_marks_removed_not_deleted PASSED [ 90%]
tests/test_update_quote_item.py::test_removed_product_can_be_added_again PASSED [ 91%]
tests/test_update_quote_item.py::test_increase_beyond_stock_rejected PASSED [ 91%]
tests/test_update_quote_item.py::test_decrease_allowed_even_if_stock_dropped PASSED [ 92%]
tests/test_update_quote_item.py::test_missing_line_raises PASSED [ 93%]
tests/test_validation.py::test_check_product_rules[7990-9000-18-False-False-True-True-False-None] PASSED [ 93%]
tests/test_validation.py::test_check_product_rules[12950-9000-4-False-False-True-False-False-price_limit] PASSED [ 94%]
tests/test_validation.py::test_check_product_rules[8000-None-2-False-False-True-True-False-None] PASSED [ 95%]
tests/test_validation.py::test_check_product_rules[9000-9000-2-False-False-True-True-False-None] PASSED [ 95%]
tests/test_validation.py::test_check_product_rules[8000-10000-0-True-False-True-False-False-out_of_stock] PASSED [ 96%]
tests/test_validation.py::test_check_product_rules[8000-10000-0-False-True-True-False-False-backorder_not_allowed] PASSED [ 97%]
tests/test_validation.py::test_check_product_rules[8000-10000-0-True-True-True-True-True-None] PASSED [ 97%]
tests/test_validation.py::test_check_product_rules[8000-7000-0-True-True-True-False-False-price_limit] PASSED [ 98%]
tests/test_validation.py::test_check_product_rules[8000-10000-0-True-True-False-False-False-inactive] PASSED [ 99%]
tests/test_validation.py::test_insufficient_stock_uses_total_line_quantity PASSED         [100%]

-----------------148 passed-----------------

Testler ayrı bir test veritabanında (tbr_test) çalışır ve her testten önce şemayı sıfırlar; demo verisine dokunmaz. Testlerde LLM kapalıdır (deterministik ve ücretsiz); LLM davranışı sahte bir OpenAI ile test edilir.

MİMARİ NOTLAR

İş kuralları veritabanına dokunmayan saf fonksiyonlarda (domain/). Üç mutasyon tool'u aynı kural fonksiyonunu kullanır.
Bütün tool çağrıları tek bir kapıdan (registry.py) geçer; her çağrı sıra numarası alır ve loglanır.
İki orkestratör (LLM ve kural tabanlı) aynı tool'ları aynı kapıdan çağırır. Kurallar tek yerde durduğu için iki orkestratör de aynı kurallara uymak zorunda.


CASE'in sorduğu kararlar 
1. Kaynak bulma yaklaşımı

Ürünler: 48 ürün için uygulama tarafında puanlama. Metin normalleştirilir (Türkçe karakterler ve İ/I dönüşümü), kelimelere ayrılır, ad, Türkçe alias, etiket ve SKU ile eşleştirilir. Türkçe ekler için basit bir önek toleransı var ("yazıcıyla" → "yazıcı"). Ardışık kelimeler ürün adında yan yana geçiyorsa ek puan verilir. Her sonuçla birlikte eşleşme kanıtı (hangi kelimeler eşleşti) döner.

Neden full-text veya embedding değil:
-Veride türkçe karakter tutarsızlığı var Postgresin türkçe ayarı bunu eşitlemiyor(şarj,sarj)
Dataset'te Plus varyantlar normal ürünlerin alias'larını birebir kopyalıyor. "Kullanıcı 'plus' demediyse Plus önerilmez" bir iş kuralı; arama motoruna bırakılamaz.
Case eşleşme kanıtı istiyor.
Web'den eklenen ürün yeniden indeksleme olmadan hemen aranabiliyor.

Bilgi kayıtları: Konu, açık anahtar kelimelerle belirlenir ("iade" → return_policy). Konu bulunamazsa kaynak dönülmez ve cevap uydurulmaz. İlk denemede kelime puanlaması "hava durumu nasıl?" sorusuna alakasız bir politikayı kaynak olarak döndürmüştü  yanlış kaynak göstermek kaynaksızlıktan daha tehlikeli olduğu için yöntem değiştirildi. Bazı konuları kelimeler değil durum belirler (örneğin stokta olmayan bir ürün istendiğinde stok kuralı); bu yüzden orkestratör konuyu açıkça da verebilir.

ORKESTRASYON 
Hibrit yapı : Anahtar var ise önce LLM denenir; herhangi bir sorunda kural tabanlı router tüm sistemi devralır .Anahtar yoksa doğrudan router çalışır 

LLM karar verir ama yetki sunucudadır:

LLM'in yapabileceği hata	--------------Nasıl Korundu
Olmayan bir tool çağırmak--------	Kapı sadece 6 tool'u tanır
Başka müşterinin teklifine dokunmak------	quote_id'yi LLM seçemez; sunucu ekler
Bütçeyi unutmak	------------Bütçe kullanıcının cümlesinden sunucu tarafından çıkarılır; kural tool içinde
Soru soran kullanıcının teklifini değiştirmek---------	Soru cümlelerinde LLM'e mutasyon araçları gösterilmez
Teklifte olmayan bir ürüne "aynı / 1 tane daha" diyerek ekleme yapmak-------	Sunucu engeller, router kullanıcıya sorar
Kaynaksız politika cevabı---------	Reddedilir, router kaynaklı cevap üretir
Bozuk argüman, döngü, zaman aşımı, API hatası-------	Router devralır (en fazla 6 adım)


Router kural tabanlıdır: cümleden eylem, bütçe, miktar ve "bekleyebilirim" bilgisini çıkarır; en iyi arama sonucu net değilse (puan düşük ya da eşit) değişiklik yapmaz, adayları sayıp sorar.

Yedek mod : hangi davranış garanti ediliyor-------------

-LLM çağrısı yapılmaz; cevaplar kayıtlı politika ve teklif verisinden üretilir.
-Her politika cevabı en az bir knowledge_id kaynağı içerir; konu bulunamazsa cevap uydurulmaz
-Emin olunmayan mutasyon yapılmaz: belirsiz ürün, boşta kalan atıf ("aynı ürün" teklifte yoksa) veya tanınmayan istekte sistem sorar.
-Bütün iş kuralları (bütçe, stok, bekleyen kalem, tekrar satır, idempotency) LLM modundakiyle aynı şekilde uygulanır, çünkü tool'ların içindedir.
Yedek modda cevap KNE-FALL-001 kaynağını da gösterir.

Idempotency stratejisi-------------

Anahtar: İstemci her mesaj için bir message_id üretir ve tekrar gönderimde aynısını kullanır. Mutasyon anahtarı bundan türetilir: {message_id}:{tool}:{product_id}. Sunucu anahtar üretseydi tekrar gelen istek yeni istek sayılırdı.
Saklama: Verilen şemada quote_items.idempotency_key satır başına tek değer tutuyordu; oysa aynı satıra birden fazla istek gelebilir. Anahtarlar ayrı bir idempotency_keys tablosuna taşındı (anahtar primary key); ilk cevap JSONB olarak saklanır ve tekrar isteğe aynı cevap dönülür.
Eş zamanlılık: Teklif satırı SELECT ... FOR UPDATE ile kilitlenir, anahtar kontrolü kilitten sonra yapılır. Önce yapılsaydı aynı anda gelen iki kopya da "anahtar yok" görüp ikisi de ekleme yapardı. Aynı isteğin 5 kopyası aynı anda gönderilerek test edildi.
Mesaj seviyesi: chat_messages.message_id primary key; tekrar gelen mesaj ikinci kez kaydedilmez.
Güncelleme: update_quote_item miktarı ayarlar ("4 yap"), artırmaz; mutlak işlemler doğası gereği idempotenttir, sözleşmede de anahtar yoktur.
Yarıda kalan LLM: LLM bir ürünü ekleyip hata verirse router devralır ve aynı ürünü eklemeye çalışır; anahtar kalıbı aynı olduğu için işlem ikinci kez uygulanmaz.
Mobil: SSE kütüphanesinin varsayılan otomatik yeniden bağlanması (5 sn) kapatıldı; yoksa yayın bittikten sonra aynı POST tekrar gönderiliyordu.

Teklif Mutasyon Modeli----------

Tekrar ekleme: Aynı teklifte aynı üründen tek aktif satır olur; bunu uygulama kodu değil veritabanı garanti eder: CREATE UNIQUE INDEX ... ON quote_items (quote_id, product_id) WHERE status = 'active'. Düz UNIQUE kullanılsaydı değiştirilmiş bir satır, ürünün yeniden eklenmesini engellerdi.
Değiştirme: Eski satır silinmez; status = 'replaced' olur ve replaced_by_item_id ile yeni satırı gösterir. Önce yeni satır eklenir, sonra eski satır işaretlenir (foreign key sırası). Alternatif zaten teklifteyse yeni satır açılmaz, mevcut satırın miktarı artırılır.
Miktar 0: Satır removed olur; eski miktar geçmiş olarak kalır.
Bekleyen kalem: Ayrı is_backorder kolonu. "Satır teklifte mi?" ve "ürün stokta mı?" bağımsız sorular olduğu için status içine konmadı.
Fiyat: Satır, eklendiği andaki fiyatı saklar; ürün fiyatı sonradan değişse de teklif değişmez.
Ürün silme: active = false (soft delete); eski teklifler bozulmaz.
Transaction: Mutasyon ve idempotency kaydı aynı transaction'da; tool logu ayrı transaction'da yazılır. Böylece reddedilip geri alınan denemelerin de kaydı kalır.
Toplamlar: İndirim ve toplamlar sadece backend'de (get_quote) hesaplanır; web ve mobil hesap yapmaz, aynı endpoint'ten okur.


 Bilinen sınırlamalar-----------

Bkz. KNOWN_LIMITATIONS.md.


İş kuralları--------------------

Kontrol tek bir saf fonksiyonda ve bu sırayla yapılır:

Ürün pasif mi? → inactive
Fiyat, kullanıcının verdiği üst limitin üstünde mi? → price_limit
Stok 0 mı? Kullanıcı açıkça beklemeyi kabul etmediyse out_of_stock; kabul ettiyse ama müşterinin allow_backorder değeri false ise backorder_not_allowed; ikisi de sağlanıyorsa bekleyen kalem olarak eklenir.
Satırın toplam miktarı stoğu aşıyor mu? → insufficient_stock


Belirsizliklerde verilen kararlar
Durum-------	Karar
Fiyat limite tam eşit----	Kabul edilir (üst limit sınırı kapsar)
Stok var ama yetmiyor-----	Reddedilir ve mevcut stok söylenir; kısmi ekleme yapılmaz
Aynı satıra birden fazla indirim kuralı uyuyor----	Yüzdeler toplanır (SCN-019: %7 + %6)
Kit veya acil kurulum----	Başka indirim uygulanmaz (engelleyici kurallar)
Aksesuar indirimi kime uygulanır-----	price_rules koşuluna uyularak tüm müşterilere
Reddedilen isteğin anahtarı-----	Saklanmaz  hiçbir şey değişmediği için tekrar değerlendirilir



Dataset'te bulunan tuzaklar
Tuzak-------	Çözüm
Plus varyantlar normal ürünlerin alias'larını kopyalıyor----	Kullanıcı "plus" demediyse Plus önerilmez
Araç şarj adaptörü stokta yok, Plus'ı stokta-----	Alternatif olarak Plus değil, kataloğun muadil listesi kullanılır
"offline" etiketi hem yazılımda hem 4G terminalde---	Uyumluluk ihtiyaçlarında kategori filtresi
"4 adede çıkar"	---Güncelleme (kaldırma değil)
"Toplam 4 adet olsun" (teklifte 1 var)---	Fark kadar ekleme
Cümlede "stok" geçmeyen stok durumu---	Konuyu orkestratör durumdan belirler
Seed'deki tekil idempotency_key kolonu---	Ayrı anahtar tablosu


Streaming (SSE)

POST /chat/stream gövdesi: session_id, message_id (istemci üretir), quote_id, text, channel.

Olay-----	İçerik
start---	session_id, message_id, mod
tool_start	---sıra numarası, tool adı, girdi özeti (teknik anahtarlar gizli)
tool_result----	sıra numarası, başarı/hata, mutasyonsa teklif değişikliği (quote_delta), tekrar isteğiyse replayed
sources--	product_id, knowledge_id, uygulanan indirim kuralı
text--	cevap metni parçaları
done / error--- bitiş veya hata

Orkestratör senkron çalıştığı için ayrı bir thread'de çalıştırılır; olaylar bir kuyruk üzerinden, oluştukları anda istemciye iletilir.

API
Endpoint	----Açıklama
POST /chat/stream-------	Sohbet (SSE)
GET /quotes, GET /quotes/{id}-----	Teklifler
GET/POST /products, PUT/DELETE /products/{id}-----	Ürünler (silme = pasifleştirme)
GET/POST /knowledge, PUT/DELETE /knowledge/{id}----	Bilgi kayıtları
GET /sessions, GET /sessions/{id}/messages-----	Sohbet oturumları
GET /logs?session_id=&message_id=&status=	 tool*call logları

Web panelinin teklif okumaları loglanmaz; loglar asistanın adımlarını göstermek içindir.


Test kapsamı
Case'in test sınıfı----Nerede
Retrieval ve grounding--------	test_search_products.py, test_get_knowledge_entries.py
Tool-call seçimi------	test_golden.py (beklenen çağrılar, sırası ve parametreleri)
Mutasyon davranışı----	test_add_to_quote.py, test_update_quote_item.py, test_replace_with_alternative.py
Duplicate ve idempotency	-----Yukarıdakiler, test_add_to_quote_concurrency.py, test_chat_stream.py
Fiyat ve stok kuralları	----test_validation.py ve mutasyon testleri
Fallback	-----test_health.py, test_golden.py (anahtarsız), test_llm.py (LLM hatalarında yedek mod)
Web/mobil ortak durum-----	test_rest_api.py::test_mobile_mutation_visible_on_web

Golden senaryolar: Her senaryo için beklenen çağrıların sırasıyla yapıldığı (aradaki ek çağrılara izin verilerek), yasaklı çağrıların hiç denenmediği, beklenen kaynakların cevapta olduğu, önerilmemesi gereken ürünlerin cevapta olmadığı ve teklifin son durumu kontrol edilir. quote_assertion alanları metin olduğu için her biri koda çevrildi. Testlerin gerçekten bir şey ölçtüğü, bir kural bilerek kaldırılarak doğrulandı (Plus kuralı kaldırıldığında 5 senaryo kalıyor).


REPO YAPISI

db/                    seed, uygulama şeması, test veritabanı
backend/app/
  domain/              saf kurallar (validation, search, knowledge, pricing, intent)
  tools/               6 tool, ortak mutasyon adımları, registry
  orchestrator/        router (kural tabanlı), llm
  api/                 chat (SSE), quotes, catalog, activity
backend/tests/         birim, entegrasyon, golden ve LLM testleri
web/                   React paneli
mobile/                Expo uygulaması

Ayrıca: AI_USAGE.md, KNOWN_LIMITATIONS.md.
