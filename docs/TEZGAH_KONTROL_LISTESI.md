# Tezgah Kontrol Listesi — Yer İstasyonu, Kalibrasyon ve Arming

Bu listedeki maddeler koddan doğrulanamaz; gerçek donanım gerektirir. Kod tarafı
derleniyor ve test ediliyor, ama aşağıdakilerin hiçbiri henüz fiziksel olarak
denenmedi.

**Sırayı bozma.** 1-3 arası adımlar diğerlerinin güvenli olup olmadığını belirler.

---

## 0. Ön koşul — her seferinde

- [ ] **Pervane sökülü.** 1-6 arası adımların tamamı pervanesiz yapılır.
- [ ] İlk kalibrasyon denemesinde **servo kolları da sökülü** olsun (madde 5'in
      gerekçesine bak).
- [ ] **İki kartı da birlikte flash'la.** `TelemetryPacket` 37 bayt oldu; tek
      taraflı güncelleme telemetriyi tamamen susturur.

## 1. Paket boyutu ve link

- [ ] Kumandanın seri monitöründe boot satırı: `TEL_STRUCT_SIZE=37`.
      Başka bir sayı görürsen kartlar farklı firmware'de, dur.
- [ ] `$T,...` satırları akıyor, `$S,...` satırları saniyede beş akıyor.
- [ ] OLED'de `ARMED` / `DISARM` satırı görünüyor. Görünmüyorsa uçakta arming
      kilidi yok demektir — gaz denemesi yapma.

## 2. RY çubuğunun yönü

Arming jesti iki çubuğun da "aşağı" olmasını arıyor. Gaz ekseni (LY) kumandada
ters çevriliyor, ama RY'nin hangi yönünün fiziksel aşağı olduğu koddan
çıkarılamıyor.

- [ ] Sağ çubuğu fiziksel olarak **aşağı** it, `$S` satırındaki **dördüncü**
      sayıya bak.
- [ ] 400'ün **altına** iniyorsa kod doğru, bir şey yapma.
- [ ] 3600'ün **üstüne** çıkıyorsa `src/stm32/main.cpp` içinde
      `armDetector.update(receivedPacket.LY, receivedPacket.RY, millis());`
      satırını `4095 - receivedPacket.RY` olacak şekilde düzelt ve yeniden
      flash'la.

## 3. Arming kilidi — pervane sökülü

- [ ] Gaz çubuğunu **yukarı** al, sonra uçağa güç ver. Motor **dönmemeli**.
- [ ] Gaz çubuğunu oynat. Hâlâ dönmemeli.
- [ ] Jesti yap: iki çubuk aşağı → bırak → iki çubuk aşağı → yarım saniye tut.
      OLED `ARMED` olmalı, kumanda iki yükselen ton çalmalı.
- [ ] Gazı yavaşça aç. Motor artık dönmeli.
- [ ] **Pervanenin hangi noktada dönmeye başladığını not et.** `DOWN_THRESHOLD`
      400/4095, yani jest tamamlandığı anda gaz teorik olarak ~%10'a kadar
      olabilir. Pratikte sıfıra yakın olmalı; değilse eşiği düşürmeyi konuşuruz.
- [ ] Kumandayı kapat, 5 saniye bekle, aç. Motor dönmemeli (link kaybı disarm
      etti).

## 4. DISARM yolu

- [ ] Uçak armed'ken yer istasyonundan **DISARM**'a bas.
- [ ] Durum satırında **"DISARM onaylandi"** görünmeli. "UCAK HALA ARMED"
      görürsen komut düşmüş demektir, tekrar bas ve bunu bana bildir.
- [ ] "Telemetri gelmedi - DISARM dogrulanamadi" mesajı farklı bir şeydir:
      komut gitmiş olabilir ama onay gelmemiştir, linke bak.
- [ ] DISARM anında gazın **hemen** kesildiğini doğrula, bir sonraki pakete
      kadar beklemediğini.

## 5. Kalibrasyon — ilk deneme servo kolları sökülü

Flash silme sırasında komut getirme durur, dolayısıyla **kesmeler de çalışmaz**.
stm32duino'nun `Servo`'su kesme tabanlı, bu yüzden kod hatları bırakıyor
(sinyal yokluğu = servo pozisyonunu korur). Bu mantığın gerçekte tuttuğunu ilk
seferde gözle görmek gerekir.

- [ ] Uçak düz zeminde, hareketsiz, **disarm**.
- [ ] Yer istasyonundan **KALİBRE ET** → onayla.
- [ ] 1-2 saniye içinde "Kalibrasyon tamam" görünmeli.
- [ ] `pitch` ve `roll` sıfıra yakın olmalı.
- [ ] **Servolar bu 1-2 saniyede şiddetli seğirmemeli veya bir durdurucuya
      dayanmamalı.** Dayanıyorsa dur ve bildir.
- [ ] Kalibrasyondan sonra **LoRa linki geri geliyor mu?** Duraklamada UART
      taşması kesin; core'un toparlandığı koddan doğrulanamadı. Gelmezse bildir.
- [ ] Kalibrasyondan sonra **arming jestini tekrar yapman gerekir** — bu kasıtlı.

## 6. Osiloskop yerine işlevsel test

Osiloskop yoksa ikisi de işlevsel olarak doğrulanabilir. Bu testler "tasarımdaki
gibi mi" sorusunu değil "çalışıyor mu" sorusunu cevaplar — sahada önemli olan bu.

**Servo sinyal seviyesi (kalibrasyondan sonra)**

`Servo::attach()` pinleri push-pull'a çeviriyor, kod sonrasında açık kollektöre
geri alıyor. Geri alma tutmazsa hatlar 3.3 V'ta kalır ve 5 V seviye çevirici
kaybolur. Çoğu analog servo 3.3 V lojiği yine de kabul eder, o yüzden fark
ancak karşılaştırmayla görünür:

- [ ] Kalibrasyondan **önce** üç servonun da tam hareket aralığını gözle not et
      (çubuğu uçtan uca gezdir; açı, hız, titreme var mı).
- [ ] Kalibre et.
- [ ] Aynı testi **tekrarla**. Üçü de aynı aralıkta, aynı hızda, titremeden
      hareket etmeli.
- [ ] Tepki kaybı, daralmış aralık veya titreme varsa bildir.

Multimetren varsa ek kanıt: servo sinyal pinini GND'ye göre **DC** modda ölç.
Çubuk ortadayken doluluk ~%7.5'tir, yani 5 V hat ~0.37 V, 3.3 V hat ~0.25 V
gösterir. Fark küçük ve ucuz metrede güvenilir değil — asıl kanıt yukarıdaki
karşılaştırma.

**ESC hattı (flash silme sırasında)**

Kalibrasyon armed'ken zaten reddediliyor, yani bu sırada ESC `MIN_THROTTLE`'da
ve motor dönemez. Riskli olan tek şey ESC'nin hata durumuna kilitlenmesi:

- [ ] ESC bağlı ve beslenmişken kalibre et (**pervane sökülü**).
- [ ] Kalibrasyondan sonra arming jestini yap, gazı aç. Motor normal dönmeli.
- [ ] Dönmüyor ve ESC sürekli bip çalıyorsa hata durumuna girmiş, güç çevrimi
      gerekir. Bu olursa bildir.

## 7. Kalibrasyonun kalıcılığı

- [ ] Kalibre et, gücü kes, tekrar aç.
- [ ] Uçağın seri çıktısında `[SETUP] Kalibrasyon: yuklendi`.
- [ ] Yer istasyonunda Kalibrasyon satırı `VAR`.
- [ ] `pitch`/`roll` hâlâ sıfıra yakın.

## 8. Yapay ufuk

- [ ] Pencere açıldığında ufuk **boş bir daire olmamalı** — gök/yer ayrımı,
      ufuk çizgisi ve pitch merdiveni görünmeli.
- [ ] Uçağı **sağa yatır**: ufuk çizgisinin sağ tarafı aşağı inmeli.
      Ters dönüyorsa `attitude.pitch_roll_deg` içindeki işaret düzeltilecek.
- [ ] Uçağın **burnunu kaldır**: ufuk aşağı kaymalı.
- [ ] Sensör satırı `AGMB` göstermeli (ivme, jiro, pusula, baro).

## 9. Bilinen sınırlar — hata değil

- **İrtifa referansı iki yerde ayrı yakalanıyor.** Kumanda açılışta, yer
      istasyonu bağlandığında. Farklı zamanlarda başlatılırsa OLED ile ekran
      farklı irtifa gösterir.
- **Zaten kalibreyken tekrar kalibre edersen otomatik onay gelmez.**
      `STATUS_CALIBRATED` biti baştan setli olduğu için gözlenecek bir geçiş yok.
      Arayüz bunu söyler; `pitch`/`roll`'a bakarak doğrula.
- **Telemetri 1 Hz.** Yapay ufuk saniyede bir güncellenir. Daha hızlısı için
      önce E22'nin MCU tarafındaki UART hızı 9600'den 38400'e çıkarılmalı.
- **Kumandanın arming bildirimi ~1 saniye gecikir** ve telemetri yokken hiç
      gelmez; jesti kumanda değil uçak çözüyor.
