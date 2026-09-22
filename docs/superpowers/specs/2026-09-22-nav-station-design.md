# Yer İstasyonu, IMU Kalibrasyonu ve Arming — Tasarım

Tarih: 2026-09-22
Durum: onay bekliyor

## 1. Amaç

Üç iş tek pakette:

1. **Yer istasyonu** — ESP32 kumandaya USB ile bağlanan, telemetriyi yapay ufuk ve sayısal panellerle gösteren bir Python programı.
2. **IMU kalibrasyonu** — uçak düz zeminde dururken GY-85'in montaj eğimini sıfır kabul eden, sonucu STM32 flash'ına yazan bir komut.
3. **Arming** — STM32'ye güç verildiğinde kumandada gaz açık kalmışsa motorun kendiliğinden dönmesini engelleyen kilit.

Üçü birlikte ele alınıyor çünkü ikisi de kumandadan uçağa **komut gönderme** yeteneği gerektiriyor; o kanal bir kez kurulunca her ikisi de üstüne biniyor.

## 2. Kapsam dışı

- **Telemetri hızı.** 1 Hz'de kalıyor. 5 Hz istenirse önce E22'nin MCU tarafındaki UART hızı 9600'den 38400'e çıkarılmalı; ölçüm gerekçesi Bölüm 3'te. Ayrı iş.
- **Uçuşta disarm jesti.** Gerekçe Bölüm 6.4.
- **Mutlak irtifa.** Deniz seviyesi basıncı girdisi gerektirir; göreli irtifa yeterli.

## 3. Telemetri hızı: neden 1 Hz kalıyor

9600 baud, 8N1 → bayt başına ~1.04 ms.

| Çerçeve | Bayt | UART süresi |
|---|---|---|
| Kontrol | 15 | 15.6 ms |
| Telemetri isteği | 6 | 6.3 ms |
| Telemetri (37 bayt yük) | 42 | 43.8 ms |

Kumandanın kontrol paketi göndermeyi kesmesi gereken pencere:

```
6.3 (istek UART) + ~15 (hava + modül) + 43.8 (uçak UART yazma)
    + ~15 (hava) + 43.8 (kumanda UART okuma) ≈ 124 ms
```

5 Hz için 200 ms'de bir istek + ~150 ms guard gerekir; bu da her 200 ms'nin 150 ms'inde kontrol paketi gitmemesi, yani çubuk komutunda 150 ms'ye varan gecikme demek. Darboğaz hava hızı (38.4 kbps) değil, MCU–E22 arasındaki 9600 baud UART. 38400'e çıkarılırsa aynı alışveriş ~53 ms'ye iner ve 5 Hz gecikme yaratmadan mümkün olur.

Karar: bu iş 1 Hz'le yapılır. Python tarafı hıza bağımlı yazılmaz — gelen her pakette güncellenir, hız sonradan artarsa kod değişmez.

## 4. Protokol değişiklikleri

`include/radio_protocol.h`:

```c
PACKET_TYPE_COMMAND = 4

struct __attribute__((packed)) CommandPacket {
  uint8_t sequence;
  uint8_t command;
};

COMMAND_CALIBRATE_LEVEL   = 1
COMMAND_CLEAR_CALIBRATION = 2
COMMAND_DISARM            = 3
```

`TelemetryPacket` sonuna `uint8_t statusFlags` eklenir (36 → 37 bayt):

| Bit | Anlam |
|---|---|
| 0 | ivmeölçer (ADXL345) bulundu |
| 1 | jiro (ITG3205) bulundu |
| 2 | pusula (QMC5883L) bulundu |
| 3 | barometre (BMP280) bulundu |
| 4 | kalibrasyon yüklü ve uygulanıyor |
| 5 | armed |
| 6-7 | ayrılmış |

Paket boyu değiştiği için **iki kart da birlikte flash'lanmak zorunda**. Yarım güncelleme sessiz bozulmaya değil, telemetri yokluğuna yol açar (alıcı taraf boyut kontrolünde paketi eler). ESP32 boot'ta `TEL_STRUCT_SIZE` basar, doğrulama oradan yapılır.

## 5. IMU kalibrasyonu

### 5.1 Ne sıfırlanıyor

- `accelOffsetX`, `accelOffsetY` — ivmeölçerin yatay bileşenleri. Z'ye dokunulmaz, yerçekimi referansı orada.
- `gyroBiasX/Y/Z` — jironun duruş sapması.
- Pusula **dokunulmaz**. Sıfırlanırsa kuzeyi değil kalibrasyon anındaki yönü gösterir; manyetik yön bilgisi kaybedilir.

Ofsetler telemetri paketi doldurulurken ham değerlerden çıkarılır. Yani yer istasyonu da, ileride uçağın kendi kontrol döngüsü de düzeltilmiş veriyi görür.

### 5.2 Ölçüm

`COMMAND_CALIBRATE_LEVEL` geldiğinde bloklamayan bir toplayıcı devreye girer. Normal IMU okuma aralığı 50 ms; kalibrasyon süresince toplayıcı kendi hızında, **5 ms aralıkla 16 örnek** alır (~80 ms), ortalar, ofsetleri yazar. Kontrol döngüsü bu sırada çalışmaya devam eder — döngü bloklanmaz, her `loop()` turunda süresi gelen bir örnek alınır.

### 5.3 Flash kalıcılığı

- **Konum:** sektör 7, `0x08060000`, 128 KB. Firmware 41 KB ve sektör 0-2'de duruyor; sektör 7 ileride firmware büyüse bile çakışmaz.
- **Format:** magic (`uint32`) + sürüm (`uint16`) + 5 × `int16` ofset + dolgu (`uint16`) + sağlama (`uint16`) = 20 bayt. Dolgu boyutu 4'ün katı yapmak için: `HAL_FLASH_Program` word yazıyor.
- **Okuma:** boot'ta. Magic ve sağlama tutuyorsa yüklenir, `statusFlags` bit4 set edilir.
- **Yazma riski:** 128 KB sektör silme ~1-2 saniye **bloklar**. Bu sürede kontrol paketi işlenmez.

Bu yüzden yazma sırası şöyle:

1. `applyFailsafe()` — gaz minimuma, servolar merkeze.
2. Flash sil + yaz.
3. `lastPacketTime = millis()` — dönüşte sahte failsafe tetiklenmesin.

Kalibrasyon **yalnız yerde, motor kapalıyken** yapılmalı. Bu kısıt README'ye ve yer istasyonu arayüzüne yazılır. Ek koruma: STM32 armed durumdayken kalibrasyon komutunu reddeder.

### 5.4 Uçtan uca akış: KALİBRE ET butonu

Kalibrasyonu tetikleyen **tek** yol yer istasyonundaki butondur. Uçakta buton, kumandada çubuk jesti, otomatik kalibrasyon yok.

```
[Python] KALİBRE ET'e basılır
   → onay kutusu: "Uçak düz zeminde ve hareketsiz mi? Motor kapalı mı?"
   → onaylanırsa USB seriye "CAL\n"
[ESP32] satırı okur, COMMAND_CALIBRATE_LEVEL'i kuyruğa alır
   → bir sonraki gönderim yuvasında, AUX müsaitse LoRa'ya yazar
[STM32] komut paketini ayrıştırır
   → armed ise reddeder, hiçbir şey yapmaz
   → değilse: applyFailsafe() → 5 ms aralıkla 16 örnek → ortalama
   → ofsetleri RAM'e yaz, flash sektör 7'ye yaz
   → lastPacketTime tazele, statusFlags bit4 set
[STM32] sonraki telemetri paketi bit4 set ve ofsetlenmiş IMU değerleriyle gider
[Python] bit4'ü ve pitch/roll'un sıfıra indiğini görür → "Kalibrasyon tamam"
```

Python tarafı komutu gönderdikten sonra bit4'ü bekler. Telemetri 1 Hz olduğu için onay 1-2 saniyede gelir. **5 saniyede** gelmezse buton hata durumuna geçer ("onay gelmedi") ve tekrar denemeye açılır. Komut kaybı bu kanalda onaylanmıyor — tekrar basmak zararsız, kalibrasyon idempotent.

## 6. Arming

### 6.1 Sorun

STM32'ye güç verildiğinde kumandadaki gaz çubuğu yukarıda olabilir. İlk kontrol paketi geldiği anda ESC tam gaz komutu alır.

### 6.2 Yetki uçakta

Jest, gelen kontrol paketlerindeki çubuk değerlerinden **STM32 tarafında** çözülür. Kumandadan ayrı bir "arm" paketi gelmez. Gerekçe: motoru süren taraf yetkili olmalı; kumanda firmware'i eski kalsa bile uçak kendini korur.

Kumanda jesti kendi çözmez. Arming durumunu telemetrideki bit5'ten okur, OLED'de gösterir ve geçişte buzzer ile bildirir; bu bildirim telemetri 1 Hz olduğu için ~1 saniye gecikir ve telemetri yokken hiç gelmez. `include/arming.h` donanımdan bağımsız tutulur ki ana makinede testlenebilsin.

### 6.3 Jest

Ham paket değerleri üzerinden (STM32'nin kendi filtresinden **önce**, çift filtrelemenin gecikmesine takılmasın), 0–4095 ölçeğinde:

```
BOSTA    → iki çubuk da < 400   → ASAGI_1
ASAGI_1  → iki çubuk da > 1600  → YUKARI_1
YUKARI_1 → iki çubuk da < 400   → ASAGI_2
ASAGI_2  → 500 ms basili tutulur VE en az 8 kontrol paketi gelir → ARMED
```

Tutma süresi yalnız duvar saatiyle ölçülmez: `HOLD_MIN_SAMPLES = 8` kontrol paketi de gerekir, böylece link tutmanın ortasında koptuğunda aradan geçen süreye dayanarak tek bir geç paket jesti tamamlayamaz.

Sekans 3000 ms içinde tamamlanmazsa BOSTA'ya döner.

ARMED'e geçildikten sonra state machine atıl kalır — tekrar arm etmek gerekmez, çubuk hareketleri durumu değiştirmez. Disarm olunca BOSTA'ya döner ve jest yeniden aranır.

Arm anında gaz çubuğu eşiğin altındadır ama tam sıfır olmak zorunda değil: `DOWN_THRESHOLD` 400/4095, bu da yaklaşık 1182 µs, yani ~%10 gaz demek. Pratikte pilot çubuğu dibe bastırdığı için değer sıfıra yakın olur, ama pervanenin hangi noktada dönmeye başladığı tezgahta ölçülmeli.

**Açık bilinmez:** LY kumandada gaz için ters çevriliyor (`4095 - filteredLY`), yani LY=0 fiziksel olarak çubuk aşağı. RY'ye dokunulmuyor ve RY=0'ın fiziksel olarak aşağı mı yukarı mı olduğu koddan çıkarılamıyor — joystick montaj yönüne bağlı. Uygulama sırasında tezgahta doğrulanacak; bunun için ESP32 USB'ye `$S,LX,LY,RX,RY` satırı da basacak.

### 6.4 Disarm

- Güç kesme.
- 5 saniyeden uzun link kaybı.
- Yer istasyonundan `COMMAND_DISARM`.

Uçuşta jestle disarm **yok**. "İki çubuk aşağı" uçuşta gerçekten oluşabilen bir durum (rölantide burun aşağı); yanlışlıkla motor kesmek istenmiyor. 300 ms'lik mevcut failsafe zaten gazı minimuma çekiyor; 5 saniye eşiği ancak link gerçekten gittiyse devreye girer.

### 6.5 Disarm durumundaki davranış

- ESC çıkışı `MIN_THROTTLE`'da sabit. Bu aynı zamanda ESC'nin kendi arming'ini düzgün yapmasını sağlar.
- Servolar çubuğu izlemeye devam eder — uçuş öncesi kumanda yüzeyi kontrolü için gerekli.

## 7. ESP32 — USB köprüsü

Mevcut `[TEL]` satırı korunur (insan okuması için). Üstüne iki makine-okunur satır eklenir:

```
$T,<ms>,<mV>,<battC>,<escC>,<ax>,<ay>,<az>,<gx>,<gy>,<gz>,<hdg>,<Pa>,<baroC>,<flags>,<rx>
$S,<LX>,<LY>,<RX>,<RY>
```

`$T` her telemetri paketi alındığında (şu an 1 Hz), `$S` 5 Hz. Python `$` ile başlamayan satırı yok sayar.

USB seriden satır bazlı komut okunur:

| Girdi | Etki |
|---|---|
| `CAL` | `COMMAND_CALIBRATE_LEVEL` kuyruğa |
| `CALCLR` | `COMMAND_CLEAR_CALIBRATION` kuyruğa |
| `DISARM` | `COMMAND_DISARM` kuyruğa |

Kuyruktaki komut bir sonraki gönderim yuvasında, mevcut AUX kontrolüne uyarak yollanır.

OLED'e `ARMED` / `DISARMED` satırı eklenir. Kumanda, telemetrideki arming geçişinde buzzer ile bildirir: arm olunca iki yükselen ton, disarm olunca tek alçak ton.

## 8. Python yer istasyonu

`tools/navstation/`, dört modül, her biri tek işli:

| Dosya | Sorumluluk | Bağımlılık |
|---|---|---|
| `link.py` | Seri port okuma thread'i, `$T`/`$S` ayrıştırma, thread-safe son-değer tutucu, komut gönderme | pyserial |
| `attitude.py` | Saf matematik: ivme → pitch/roll, jiro ölçekleme, basınç → göreli irtifa | yok |
| `ui.py` | tkinter penceresi, çizim | tkinter |
| `__main__.py` | Argümanlar (port, baud), modülleri bağlar | — |

`attitude.py` hiç G/Ç yapmaz, `link.py` hiç GUI bilmez. İkisi de birim testlenebilir.

### 8.1 Ölçekler

- **İvmeölçer:** ADXL345, `DATA_FORMAT` yazılmıyor → varsayılan ±2 g, 10 bit, 256 LSB/g. Firmware 4'e bölüyor → **64 LSB/g**.
- **Jiro:** ITG3205, `FS_SEL=3` → ±2000 °/s, **14.375 LSB/(°/s)**.
- **Açılar:** `roll = atan2(ay, az)`, `pitch = atan2(-ax, sqrt(ay² + az²))`. Ölçek sadeleştiği için LSB katsayısı açı hesabını etkilemez; g ve °/s göstergeleri için gerekli.
- **İrtifa:** `44330 × (1 − (P/P₀)^0.1902949)`, P₀ = bağlantıdan sonraki ilk geçerli basınç.

### 8.2 Ekran

Tek pencere:

- **Orta — yapay ufuk.** Yuvarlak gösterge; gök/yer ayrımı roll ile döner, pitch ile kayar; 10°'de bir pitch merdiveni; ortada sabit sarı uçak sembolü; üstte roll yayı ve üçgen ok göstergesi.
- **Sol panel.** Batarya gerilimi, batarya/ESC/baro sıcaklığı, basınç, göreli irtifa.
- **Sağ panel.** Sayısal pitch/roll/heading, jiro hızları, ivme (g), link durumu (paket sayısı, son paketin yaşı), sensör bayrakları, `ARMED`/`DISARMED`, kalibrasyon durumu.
- **Alt şerit.** Port seçimi, bağlan/kes, **KALİBRE ET**, **KALİBRASYONU SİL**, **DISARM**, durum satırı.

**KALİBRE ET butonunun durumları:**

| Durum | Görünüm |
|---|---|
| Bağlı değil veya link yok | Pasif |
| Armed (telemetri bit5 set) | Pasif, ipucu: "Kalibrasyon yalnız disarm durumunda" |
| Hazır | Aktif |
| Basıldı, onay bekleniyor | Pasif, "Kalibre ediliyor..." |
| Onay geldi (bit4 set) | Aktif, durum satırı "Kalibrasyon tamam" |
| 5 sn onay gelmedi | Aktif, durum satırı "Onay gelmedi, tekrar dene" |

Basıldığında önce onay kutusu çıkar: uçağın düz zeminde, hareketsiz ve motorun kapalı olduğu doğrulanır. Tam akış Bölüm 5.4'te.

**KALİBRASYONU SİL** aynı akışı `CALCLR` ile izler; onayı bit4'ün **düşmesi**.

### 8.3 Hata davranışı

- Port açılamazsa durum satırında sebep, buton tekrar denemeye açık.
- 3 saniyedir paket gelmiyorsa paneller soluklaşır, durum satırı `LINK YOK`.
- Bozuk `$T` satırı sessizce atılır, sayaç tutulur; ayrıştırıcı asla istisna fırlatmaz.
- Sensör bayrağı düşükse ilgili alan `--` gösterir, 0 değil.

## 9. Test

| Ne | Nasıl |
|---|---|
| `attitude.py` | pytest, bilinen vektörlerle açı/irtifa doğrulaması |
| `link.py` ayrıştırıcı | pytest, örnek satırlar + bozuk/eksik alanlı satırlar |
| `arming.h` state machine | pytest değil — ana makinede derlenen küçük bir C++ test koşucusu, `test/` altında |
| KALİBRE ET akışı | Tezgahta uçtan uca: butona bas, `CAL` gittiğini seri monitörde gör, bit4'ün set olduğunu ve pitch/roll'un sıfıra indiğini doğrula. Ayrıca kablo çekiliyken 5 sn zaman aşımının çalıştığını gör |
| Flash kayıt/okuma | Tezgahta: kalibre et, güç kes, aç, bit4 ve ofsetlerin korunduğunu doğrula |
| Arming | Tezgahta, **pervane sökülü**: gaz yukarıdayken güç ver, motorun dönmediğini gör; jesti yap, armed'a geçtiğini gör |
| RY yönü | Tezgahta `$S` satırından |

## 10. Gereklilik

```
brew install python-tk@3.14
```

`.env` içinde tkinter yok; pyserial, numpy, matplotlib, PIL var.

## 11. Uygulama sırası

1. `radio_protocol.h` — komut paketi + statusFlags.
2. `arming.h` + ana makinede state machine testi.
3. STM32 — arming kilidi, komut ayrıştırma, kalibrasyon ofsetleri, flash.
4. ESP32 — `$T`/`$S` çıktısı, komut girişi, OLED + buzzer geri bildirimi.
5. Tezgah doğrulaması: RY yönü, arming, kalibrasyon kalıcılığı.
6. Python paketi, testlerle.
