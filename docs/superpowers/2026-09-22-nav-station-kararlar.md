# SDD ledger — plan: docs/superpowers/plans/2026-09-22-nav-station.md

Branch: feat/nav-station (worktree DEGIL — gerekce asagida)
Spec: docs/superpowers/specs/2026-09-22-nav-station-design.md
Base commit: 5895e2f

## Pre-flight tarama

Paylasilan dosya / arayuz cifti:

| Uretici | Tuketici | Ne | Sonuc |
|---|---|---|---|
| T1 radio_protocol.h | T4,T5,T6 | STATUS_*, COMMAND_*, CommandPacket, statusFlags | isim/deger uyumlu |
| T2 arming.h | T4,T5 | reset/update/disarm/isArmed/phase | uyumlu |
| T3 calibration.h | T5 | Record/MAGIC/VERSION/finalize/isValid | uyumlu |
| T1 run_native_tests.sh | T2,T3 | glob test/native/test_*.cpp | uyumlu |
| T7 attitude.py | T9 | accel_to_g/gyro_to_dps/pitch_roll_deg/heading_deg/relative_altitude_m | 5/5 kullaniliyor |
| T8 link.py | T9 | Telemetry/Sticks/FLAG_*/TEMP_ABSENT/SerialLink | latest_sticks kullanilmiyor — R3 |
| T4 stm32/main.cpp | T5 ayni dosya | T5 armDetector'e bagimli, sira 4→5 dogru | uyumlu |
| T6 | stm32/main.cpp'e de dokunuyor | RY duzeltmesi donanim adimina bagli | R4 |

Gorev ici tutarlilik:

| Gorev | Bulgu |
|---|---|
| T1 | test ile header uyumlu; checksum imzasi dogru |
| T2 | **KUSUR** — zaman asimi gecisten sonra kontrol ediliyordu, kendi Test 6'si gecmezdi. Plan duzeltildi. |
| T3 | test ile header uyumlu; 16 bayt dogrulanabilir |
| T4 | tutarli |
| T5 | **KUSUR** — ayni adim serviceCalibration'i once readBmp280 altina, sonra readGy85 altina koydur diyordu; dosyada readBmp280 once geliyor, ilk yerlesim derlenmezdi. Plan duzeltildi. |
| T6 | updateArmedFeedback icinde delay(140) var — R5 |
| T7 | irtifa testi elle dogrulandi (12 Pa -> 0.999 m, tolerans 0.2) |
| T8 | tutarli |
| T9 | brew install ve GUI calistirma subagent isi degil — R2 |

## Rulings

Ruling: Worktree yerine yerinde dal (feat/nav-station) — `.env` sanal ortami git'te yok ve `.pio/` gitignore'lu, worktree'de ikisi de bulunmaz; ayrica kart flash'lama kullanicinin bildigi checkout'tan yapilmali — Maliyet: ana checkout kirlenir, geri almak icin dal degistirmek gerekir.
Ruling: Donanim adimlari (flash, tezgah dogrulama, brew install) subagent'lara verilmez; subagent'lar kod + derleme + ana makine testleriyle sinirli, donanim kontrol listesi sonda kullaniciya verilir — Maliyet: planin dogrulama adimlari yurutme sirasinda degil, sonrasinda kosulur; bir donanim kusuru gec fark edilir.
Ruling: link.latest_sticks() UI'da kullanilmiyor ama tutuluyor — parse_line'in `$S` satirlarini tanimasi zorunlu (yoksa bozuk-satir sayaci sisirilir, spec 8.3), accessor 3 satir ve RY tezgah adimina hizmet ediyor — Maliyet: kullanilmayan bir public metot.
Ruling: T6 Step 9.3'teki RY yonu duzeltmesi yurutmeden cikarildi, donanim listesine tasindi — Maliyet: jest ilk denemede ters yonde calisabilir, tek satirlik duzeltme gerekir.
Ruling: T6 updateArmedFeedback icindeki delay(140) kabul — gecis yerde olur ve 140 ms ucagin 300 ms failsafe esiginin altinda — Maliyet: arm/disarm aninda bir kontrol paketi penceresi kacar.
Ruling: Implementer'lar kod parcalarini satir numarasiyla degil, alintilanan metin ile bulacak — T4 dosyanin basina satir ekledigi icin T5'teki numaralar kayar — Maliyet: yanlis yere yerlestirme, derleme hatasiyla yakalanir.

## Ilerleme
Ruling: T1+T2+T3 tek dispatch'te birlestirildi — ucu de tam kodu verilmis transkripsiyon isi, ayni dosya ailesi (include/ + test/native/), ve T2/T3 T1'in test kosucusuna bagli — Maliyet: ucunun review yuzeyi tek pakette gelir, bir gorevdeki kusur digerlerinin commit'lerini de fix loop'una sokar.
Planlanan dispatch gruplari: [T1-T3 haiku] [T4 sonnet] [T5 sonnet] [T6 sonnet] [T7+T8 haiku] [T9 sonnet]
T1-T3: dispatch edildi, BASE=5895e2f
Ruling: T3 Record 16 degil 20 bayt; jiro alanlari int16_t kalacak. Planin 16 iddiasi aritmetik hataydi (4+2+5*2+2=18) ve implementer testi tutturmak icin gyroBiasY/Z'yi int8_t'ye dusurmustu — ITG3205 sapmasi +-127 LSB'yi asar, kalibrasyon bozulurdu. Ayrica 18 de 4'un kati degil: T5 flash'a sizeof/4 word yaziyor, checksum hic yazilmazdi. Cozum: uint16_t reserved dolgusu, toplam 20 bayt = 5 word. Plan duzeltildi. — Maliyet: flash kaydi 4 bayt buyur (128 KB sektorde onemsiz).
T1-T3: fix round 1/5 dispatch edildi (Record 20 bayt, int16_t geri)
T1-T3: fix round 1/5 tamam (1 addressed, 0 open; commit 6d01a48). Bagimsiz dogrulama: Record=20 mod4=0, Telemetry=37, Command=2.
T1-T3: task review dispatch edildi (paket review-5895e2f..6d01a48.diff)
T1-T3: task review -> Spec OK x3, quality approved. 1 Important (Down2'de zaman asimi yok), 1 Minor (yorum yazim hatasi).
T1-T3: "Cannot verify from diff" (pio run) kontrolcu tarafindan kapatildi: esp32 SUCCESS, stm32 SUCCESS, uc native test OK.
Ruling: arming.h Down2'de zaman asimi uygulanmamasi KALIYOR. SEQUENCE_TIMEOUT_MS jest desenini tamamlama suresini sinirlar; Down2'ye zamaninda girildiyse pilot cubuklari bilincli tutuyordur ve tutma ortasinda sessiz red geri bildirimsiz basarisizlik olurdu. En kotu durum 3.0 s yerine 3.5 s'de arm; jest geregi gaz zaten minimumda, tehlike yok. Bulgunun gecerli kismi "test edilmemis" olmasiydi: Test 10/11/12 eklendi ve gerekce koda yazildi. — Maliyet: arm beklenenden 500 ms gec olabilir; pilot jesti tamamladigini sanip beklemek zorunda kalirsa kafa karisikligi.
T1-T3: fix round 2/5 dispatch edildi (Test 10-11-12 + yorum gerekcesi + yazim hatasi)
T1-T3: fix round 2/5 tamam (2 addressed, 0 open; commit be94774). Re-review: arming.h mantigi degismemis (sadece yorum), Test 10/11/12 elle izlendi, hicbiri vacuous degil.
T1-T3: minor (deferred): Test 12 tasma testi abs()/sinirsiz-signed hata sinifini yakaliyor ama duz signed 32-bit fark implementasyonundan ayirt etmiyor. Kapsam iddiasi testin yaptigindan biraz genis.
T1-T3: complete (commits 5895e2f..be94774, review clean)
T4: dispatch edildi, BASE=be94774
T4: task review -> Spec OK, quality approved, bulgu yok. Tum myESC.writeMicroseconds yollari izlendi (170 kapili, 191/524 kosulsuz MIN_THROTTLE); detector cikislardan once guncelleniyor, bayat-armed penceresi yok; 300 ms failsafe ile 5000 ms disarm bagimsiz if'ler.
T4: not - T4 brief'inin "Produces" satiri dosya kapsaminda bool isArmed() sarmalayicisi listeliyordu ama hicbir adim tanimlamiyor; implementer dogru davranip armDetector.isArmed() cagirmis. T5/T6 plan metni de dogrudan nesneyi kullaniyor, islem gerekmiyor.
T4: complete (commits be94774..8654087, review clean)
T5: dispatch edildi, BASE=8654087
T5: implementer DONE (88ac3c7), -Waddress-of-packed-member bildirdi ve zararsiz dedi.
Ruling: Uyari kontrolcu rebuild'inde cikmadi (arm-none-eabi GCC 12 sessiz), ama (const uint32_t*)&record cast'i yine de tanimsiz davranis: Record packed, hizalamasi 1, derleyici yereli 4'e bolunmeyen adrese koyabilir. Cortex-M4'te hizasiz LDR genelde calisir ama burasi ucus kalibrasyonunu flash'a yazan rutin. Review oncesi duzeltiliyor: hizali yerel tampona memcpy. — Maliyet: 20 baytlik ek yigin kullanimi; yanlissam gereksiz bir tur.
T5: fix round 1/5 dispatch edildi (hizali tampon)
T5: task review (opus) -> Spec OK, quality NOT approved. 2 Critical, 3 Important, 3 Minor, 2 "cannot verify".
  C1 arming kontrolu komut aninda yapiliyor, yazim aninda yapilmiyor (~80 ms ornekleme penceresinde arm olunabilir)
  C2 clearCalibration devam eden ornekleme iptal etmiyor + yazim sonucunu yok sayiyor
  I3 kayit basarisiz olsa da ofsetler telemetriye uygulanmaya devam ediyor
  I4 pendingCommand tek yuva, komut ezilip kaybolabilir (DISARM dahil), sequence kullanilmiyor, retransmit ikinci silme cevrimi acar
  I5 DISARM gazi hemen kesmiyor
  m6 jiro ofset cikarmasi int16_t tasabilir  m7 yorum yanlis  m8 sectorError olu
Ruling: Minor 6/7/8 de fix turuna alindi — ucu de zaten degistirilen fonksiyonlarin icinde, ayrica tutmak bedava; m6'nin basarisizlik modu (ters yonde tam skala donus telemetrisi) yer istasyonunun ufkunu bozar, minor etiketinden agir. — Maliyet: fix turu biraz genisledi.
Ruling: Komut icin protokole ack/sequence baytı EKLENMIYOR. Bunun yerine (a) sequence ile tekrar eleme, (b) DISARM'in parse aninda islenmesi. Ack eklemek 37 baytlik paketi ve T6/T8/T9'u da degistirirdi; yer istasyonunun 5 sn zaman asimi + STATUS_* gozlemi zaten dokumante onay mekanizmasi. — Maliyet: armed reddi ile kayip paket yer istasyonunda hala ayirt edilemiyor; operator STATUS_ARMED'a bakmak zorunda.
Ruling: Silme sirasinda flash yazimi basarisiz olursa RAM/flash uyusmazligi kabul ediliyor, sadece debug seriye basiliyor. Tam kapatmak icin protokole "flash hatasi" biti ve UI gerekirdi. — Maliyet: erase donanim hatasinda operator guc cevriminden sonra kalibrasyonun geri geldigini gorur, kafa karistirir.
Ruling: Flash yaziminin ardindan armDetector.reset() ekleniyor (review'un dogrulanamayan millis maddesi). Kalibrasyon sonrasi jestin tekrar yapilmasi zaten dogru davranis. — Maliyet: operator kalibrasyondan sonra yeniden arm etmek zorunda.
T5: OPERATOR KONTROL LISTESINE: kalibrasyondan sonra LoRa linki geri geliyor mu? 1-2 sn duraklamada UART RX overrun kesin, core'un ORE'yi temizleyip devam ettigi kodda dogrulanamiyor.
T5: fix round 2/5 dispatch edildi (9 madde)
T5: fix round 2/5 tamam (9 addressed, 0 open; commit 32163f7). Re-review 3 yeni madde buldu.
  A (Moderate/Important) applyFailsafe servolari merkeze aliyor ama applyOutputs'un static onbellegini guncellemiyor -> disarm sonrasi cubuk kipirdamamissa AIL/RUD bir daha hic komut almiyor. RX-timeout yolunda zaten vardi, DISARM degisikligi rutin hale getirdi.
  B (Low) dedupe, yer istasyonu yeniden baslarsa 1/256 ihtimalle ilk komutu yutuyor
  C (Low) armed-abort sessiz
Ruling: A duzeltiliyor (fix round 3). Ucakta bu, temiz gorunen bir uculus oncesi kontrolden sonra iki olu kumanda yuzeyi demek — Minor degil. — Maliyet: uc degisken dosya kapsamina cikiyor, kapsam biraz genisliyor.
Ruling: B parkediliyor. 1/256, kendini iyilestiriyor (operator tekrar basar, sequence artar), ve yer istasyonunun 5 sn zaman asimi zaten "tekrar dene" diyor. Zaman pencereli dedupe alternatifi retransmit'i kacirip cift silme cevrimi acardi, yani daha kotu. — Maliyet: kumanda yeniden baslatildiktan sonraki ilk komut 1/256 ihtimalle sessizce yok sayilir.
Ruling: C icin sadece debug print ekleniyor, telemetri biti eklenmiyor — protokol degisikligi ve dort gorev daha etkilenirdi; yer istasyonu zaten armed'ken butonu pasifliyor ve 5 sn zaman asimi veriyor. — Maliyet: operator tezgahta seri monitore bakmadan iptal sebebini goremez.
T5: fix round 3/5 dispatch edildi (servo onbellegi + iptal logu)
T5: fix round 3 commit 59ab46c. DIKKAT: dalda paralel calisma var — 2dbe2d8 ve 2c4121d (docs: controller case spec) bu plana ait degil, baska bir is ayni dala commit ediyor. Kullaniciya bildirildi. Re-review paketi 2dbe2d8..59ab46c olarak daraltildi.
T5: fix round 3/5 tamam (2 addressed, 0 open; commit 59ab46c). Re-review: static'ler tam kaldirilmis, non-failsafe yol davranissal olarak ayni, setup()'in yazdigi aci dosya kapsami baslangic degeriyle eslesiyor, servolara yazan baska yol yok.
T5: minor (deferred): pendingCommand hala tek yuva — CALIBRATE ve CLEAR ayni 32 baytlik okuma turunda gelirse biri kaybolur. DISARM artik yuvayi atladigi icin tehlikeli kismi kapandi.
T5: complete (commits 8654087..59ab46c, review clean, 2 parked)
T6: dispatch edildi
T6: task review -> Spec OK, quality approved. 3 Minor, hicbiri loop'a girmedi.
T6: minor (deferred): updateArmedFeedback'teki delay(140) arm/disarm kenarinda loop'u bir kez 140 ms blokluyor (~7 kontrol paketi kaciyor). Tek seferlik ve yerde oluyor.
T6: minor (deferred): pendingCommand kumanda tarafinda da tek yuva; ayni turda iki USB komutu gelirse birincisi sessizce eziliyor. Brief'in kendi tasarimi.
T6: minor (deferred): pollUsbCommands asiri uzun satirda indeksi sifirliyor ama satir sonuna kadar atmiyor; >31 karakterlik cop satirin kuyrugu yeni satir gibi gorunebilir. Kabul edilen komutlar <=6 karakter, pratikte etkisiz.
T6: sequence anlasmasi iki tarafta da dogrulandi (ESP32 her gonderimde artiriyor, STM32 sadece birebir tekrari eliyor).
T6: complete (commits 2c4121d..199721b, review clean)
T7+T8: dispatch edildi
T7+T8: task review -> Spec OK x2, quality NOT approved. 1 Critical, 1 Important, 2 Minor.
  C parse_line bytes girdide TypeError atiyor: bytes.strip() calisiyor, hata bir satir asagida startswith'te patliyor, except (AttributeError, UnicodeDecodeError) guard'i yakalamiyor. Plan kodumun kusuru.
  I send_command/_read_loop, close() self._serial'i None yaparken kilitsiz dereference ediyor -> AttributeError yakalanmiyor
  m open() yeniden girise kapali degil, onceki thread sahipsiz kaliyor
  m pitch/roll isaret konvansiyonunun fiziksel montajla eslesmesi diff'ten dogrulanamaz
Ruling: Isaret konvansiyonu operator kontrol listesine tasindi — IMU'nun karta hangi yonde lehimlendigi koddan cikarilamaz, tezgahta ucagi saga yatirip ufkun dogru yone dondugune bakmak tek yol. — Maliyet: ilk tezgah denemesinde ufuk ters donerse bir isaret duzeltmesi gerekir.
Ruling: Iki Minor'dan open() duzeltiliyor (uc satir, ayni dosyada), isaret konvansiyonu parkediliyor.
T7+T8: fix round 1/5 dispatch edildi
T7+T8: fix round 1/5 tamam (3 addressed, 0 open; commit b741e6c). Bagimsiz dogrulama: parse_line bytes/None/int/list/float/object icin None donuyor, istisna yok.
T7+T8: minor (deferred): close() artik okuyucu readline() icinde bloklanmisken ayni fd'yi kapatabiliyor. Beklenen sonuc (SerialException/OSError) yakalaniyor; teorik fd-yeniden-kullanim yarisi kaliyor. Alternatif sira (once join sonra close) okuyucunun join zaman asimini asmasina yol aciyordu, yani takas bilincli.
T7+T8: minor (deferred): send_command/_read_loop artik AttributeError'i de yutuyor; gercek bir programlama hatasi zararsiz kopma gibi gorunebilir.
T7+T8: complete (commits fdb1ce1..b741e6c, review clean, 3 parked)
T9: task review -> Spec OK, quality NOT approved. 2 Critical, 1 Important, 1 Minor. Ikisi de plan kodumun kusuru.
  C1 yuvarlak maske create_oval(width=HORIZON_SIZE) ile ciziliyor; Tk cizgiyi yolun iki yanina esit dagittigi icin 160 px ICERI tasiyor, HORIZON_RADIUS 140 -> tum disk BG ile boyaniyor, ufuk bos gorunuyor.
  C2 _check_calibration sadece anlik bayraga bakiyor, calibration_baseline_flags hic okunmuyor -> bayrak zaten setliyse ucak hicbir sey yapmadan "tamam" diyor.
  I3 _tick'te try/except yok; tek bir hata after() cagrisina ulasilmasini engelleyip yenileme dongusunu kalici donduruyor (pencere acik, degerler donmus, uyari yok).
  m4 irtifa referansi FLAG_BARO kontrolu olmadan yakalaniyor.
Ruling: C2 icin gercek kenar araniyor, ama bayrak bastan istenen konumdaysa bu kanaldan onay MUMKUN DEGIL. UI o durumda "tamam" da "onay gelmedi" de demiyor; "komut gonderildi, otomatik onay yok - pitch/roll sifira indi mi bak" diyor. Alternatifler: (a) zaten kalibreyken butonu kilitleyip once SIL'i zorunlu kilmak - iki flash cevrimi ve fazladan tiklama, (b) protokole onay dizisi eklemek - 37 baytlik paketi ve uc gorevi daha degistirirdi. — Maliyet: yeniden kalibrasyonda operator sonucu gozle dogrulamak zorunda.
T9: fix round 1/5 dispatch edildi (4 madde)
T9: fix round 1/5 tamam (4 addressed, 0 open; commit 35c15fb). Re-review dort kalibrasyon kombinasyonunu izledi, pending state hicbir yolda takili kalmiyor, CAL/CALCLR onaylari birbirine yazilamiyor.
T9: minor (deferred): _on_clear_calibration'da send_command basarisiz olursa else dali yok, _on_calibrate'te var. Onceden beri var olan bosluk.
T9: complete (commits b741e6c..35c15fb, review clean, 1 parked)
TUM GOREVLER TAMAM. Son butun-dal review'u dispatch ediliyor.
SON REVIEW: merge'e uygun degil. 1 Blocker (DISARM onay yolu + uc sessiz dusme rotasi) + oneriler. Tek fix dalgasi (9 madde) uygulandi -> 5cfbaac.
Ruling: Son review benim "1/256 sequence yutulmasi parkedildi" kararimi cevirdi ve kabul ediyorum. Flash komutlari icin park dogruydu (operator tekrar basar), acil durdurma icin degildi: geri bildirimsiz dusen bir kill switch kendini iyilestirmez. DISARM artik tekrar elemesinden muaf. — Maliyet: gecikmis bir duplicate DISARM iki kez uygulanir, ki idempotent.
SCOPED RE-REVIEW (fix dalgasi): 9 madde de ADDRESSED, ama H1 regresyonu bulundu.
  H1 Servo::attach() iceride pinMode(OUTPUT) yapiyor; restore blogum OUTPUT_OPEN_DRAIN'i geri koymuyordu -> ilk kalibrasyondan sonra servo hatlari push-pull 3.3 V, 5 V seviye cevirici kayboluyor.
  M1 DISARM kuyruktaki flash komutunu iptal etmiyor  M3 _check_disarm yanlis alarm uretebiliyor  M4 busy disarm'i saymiyor
  L1-L6 kucuk
Ruling: "Ikinci fix dalgasi yok" kuralina ragmen son ve dar bir gecis yapiliyor. Gerekce: H1 ve L3 dogrudan benim ilk dalgamin urettigi regresyonlar, M1/M4 ayni dalganin dogrudan sonuclari. Kendi yarattigim bir regresyonu tur sayisi kuralina dayanarak sahaya birakmak yanlis olurdu. Sonrasinda kalan her sey yargilanip kapatilacak, tekrar dongu yok. — Maliyet: bir tur daha sure; bu gecis de regresyon uretirse yakalanmayacak.
Ruling: M2 (ESC flash sirasinda park edilmiyor) kod degisikligi degil, tezgah listesine. applyFailsafe zaten tam bir MIN_THROTTLE darbesi yaziyor ve sinyal kesilmesinde ESC'ler keser; servolar gibi durduruculara dayanma riski yok. — Maliyet: ESC hattinin duraklamada ne yaptigi ancak osiloskopla gorulur.
Ruling: L1 (holdSamples paket sayiyor, aralik olcmuyor) davranis olarak kabul, sadece yorum duzeltiliyor. Radyo birikmis cerceveleri toplu teslim ederse sayac 500 ms'den kisa surede dolabilir; ama cubuklar o sure boyunca fiziksel olarak asagida tutuldu, sadece biz duymadik. — Maliyet: kopuk link sonrasi jest beklenenden erken tamamlanabilir.
Ruling: L5 (DISARM onay mantiginin testi yok) parkediliyor. Mantik tk widget'larina bagli; test icin UI'yi ayirmak bu asamada yeni risk. Operator kontrol listesinde elle dogrulanacak. — Maliyet: bu yol yalniz tezgahta sinaniyor.
Ruling: L6 (250 ms telemetri guard DISARM'i geciktirebilir) parkediliyor — ucagin kendi failsafe esigi 300 ms, ayni mertebe.
Son gecis dispatch edildi (8 madde)
