# RC Kumanda Ana İstasyonu - Bağlantı Şeması (Pinout)

Bu bölümde, ESP32 tabanlı uzaktan kumanda ünitesinin bileşenleri arasındaki donanımsal pin bağlantılarını içerir.

## 1. Genel Bağlantı Tablosu

| Bileşen                | Bileşen Pini                                                        | ESP32 Pini                                                                                                                              | İşlevi / Açıklaması                                                    |
| :--------------------- | :------------------------------------------------------------------ | :-------------------------------------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------- |
| **OLED / LCD Ekran**   | VCC <br> GND <br> SDA <br> SCL                                      | **3V3** <br> **GND** <br> **GPIO 21** <br> **GPIO 22**                                                                                  | I2C Haberleşme Hattı (Sistem Bilgileri Ekranı)                         |
| **LoRa (E22-900T22D)** | VCC <br> GND <br> RXD <br> TXD <br> **AUX** <br> **M0** <br> **M1** | **3V3** <br> **GND** <br> **GPIO 17 (TX2)** <br> **GPIO 16 (RX2)** <br> **GPIO 4 (INPUT)** <br> **GPIO 18 (LOW)** <br> **GPIO 5 (LOW)** | UART2 Haberleşme — AUX modül durumu için INPUT, M0/M1 normal mod (LOW) |
| **Sol Joystick**       | VCC <br> GND <br> VRX (Roll) <br> VRY (Pitch)                       | **3V3** <br> **GND** <br> **GPIO 32** <br> **GPIO 33**                                                                                  | ADC1 Kanalı (Analog Giriş - Sinyal çakışmasından etkilenmez)           |
| **Sağ Joystick**       | VCC <br> GND <br> VRX (Yaw) <br> VRY (Throttle)                     | **3V3** <br> **GND** <br> **GPIO 34** <br> **GPIO 35**                                                                                  | ADC1 Kanalı (Analog Giriş - Sadece Giriş Destekli Pinler)              |
| **Buzzer**             | Artı (+) <br> Eksi (-)                                              | **GPIO 25** <br> **GND** <br>                                                                                                           | Telemetri ve Sistem Uyarı Sesleri Çıkışı (DAC Destekli Pin)            |

---

## 2. Kritik Donanım Notları ve Uyarılar

> ⚠️ **UYARI 1: Joystick Besleme Voltajı**
> Joysticklerin (Potansiyometrelerin) VCC bacakları **kesinlikle 5V hattına BAĞLANMAMALIDIR**. ESP32 analog pinleri maksimum 3.3V toleranslıdır. 5V bağlanması durumunda analog pinler kalıcı hasar görebilir.

> ⚠️ **UYARI 2: ADC1 ve Wi-Fi/RF Çakışması**
> ESP32 mimarisinde ADC2 pinleri (GPIO 0, 2, 4, 12-15, 25-27) dahili RF/Wi-Fi üniteleri aktifken kararsız çalışır veya analog okuma yapamaz. Bu nedenle tüm joystick eksenleri güvenli olan **ADC1 (GPIO 32, 33, 34, 35)** pinlerine yönlendirilmiştir.

> 💡 **Öneri: Güç Filtreleme (Kapasitör)**
> E22 LoRa modülü anlık yüksek akım çekebileceğinden, LoRa modülünün VCC ve GND pinlerine mümkün olduğunca yakın olacak şekilde **10uF - 100uF arası bir dekuplaj kondansatörü** paralel olarak eklenmelidir. Bu işlem voltaj dalgalanmalarını önler ve sistem kararlılığını artırır.

# RC Uçak Bağlantı Şeması (Pinout)

Bu bölümde, STM32F411CEU6 (Black Pill) kartının uçak bileşenleri arasındaki donanımsal pin bağlantılarını içerir.

| Bileşen                | Bileşen Pini                                                        | STM32F411CEU6 (Black Pill) Pini                                                                                                                         | İşlevi / Açıklaması                                                                                                                                  |
| :--------------------- | :------------------------------------------------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------ | :--------------------------------------------------------------------------------------------------------------------------------------------------- |
| **LoRa (E22-900T22D)** | VCC <br> GND <br> RXD <br> TXD <br> **AUX** <br> **M0** <br> **M1** | **3.3V** <br> **GND** <br> **PA9 (Serial1 TX)** <br> **PA10 (Serial1 RX)** <br> **PA11 (GPIO, INPUT)** <br> **PA15 (GPIO, LOW)** <br> **PA12 (GPIO, LOW)** | UART hatları PA9/PA10 üzerinde tutulur. AUX/M0/M1 kontrolü PA11/PA15/PA12 ile yapılır. |
| **Servo 1 (Roll)**     | Sinyal <br> VCC <br> GND                                            | **PA6 (TIM3_CH1, open-drain)** <br> **5V** <br> **GND**                                                                                                 | Kumanda sol stick X ekseni — kanat/roll kontrolü                                                                                                     |
| **Servo 2 (Pitch)**    | Sinyal <br> VCC <br> GND                                            | **PA7 (TIM3_CH2, open-drain)** <br> **5V** <br> **GND**                                                                                                 | Kumanda sol stick Y ekseni — irtifa/pitch kontrolü                                                                                                   |
| **Servo 3 (Yaw)**      | Sinyal <br> VCC <br> GND                                            | **PB0 (TIM3_CH3, open-drain)** <br> **5V** <br> **GND**                                                                                                 | Kumanda sağ stick X ekseni — dümen/yaw kontrolü                                                                                                      |
| **ESC (Skywalker 30A V2-UBEC, 4 kablo)** | **Beyaz** (throttle sinyal) <br> **Kırmızı** (+5V BEC) <br> **Siyah** (GND) <br> **Sarı** (Reverse Brake kontrol) | **PA1 (ESC PWM / LY throttle, open-drain + pull-up)** <br> **5V güç hattı** <br> **GND ortak** <br> **Kullanılmıyor (opsiyonel RX kanalına)** | Beyaz kablo ESC gaz sinyalidir ve kumandadaki **LY (throttle)** kanalına karşılık gelir. **PA1 sinyal hattına 4.7kΩ-10kΩ pull-up direnci 5V'a bağlanmalıdır.** Kırmızı/siyah BEC çıkışıdır (servo +5V besleme). Sarı kablo batarya telemetrisi değildir; Reverse Brake ON/OFF kontrol hattıdır. **PA1 FT (5V tolerant) olduğu için 5V pull-up güvenlidir.** |
| **GY-85 (MPU/IMU, I2C)** | VCC <br> GND <br> SDA <br> SCL                                    | **3.3V** <br> **GND** <br> **PB7 (I2C1 SDA)** <br> **PB6 (I2C1 SCL)**                                                                                   | IMU verisi. I2C hattı BMP280 ile ortaktır.                                                                                                           |
| **BMP280 (I2C)**       | VCC <br> GND <br> SDA <br> SCL                                      | **3.3V** <br> **GND** <br> **PB7 (I2C1 SDA)** <br> **PB6 (I2C1 SCL)**                                                                                   | Basınç/irtifa verisi. I2C hattı GY-85 ile ortaktır.                                                                                                  |
| **NEO-7M GPS (UART)**  | VCC <br> GND <br> TX <br> RX                                        | **5V veya 3.3V*** <br> **GND** <br> **PA3 (USART2 RX)** <br> **PA2 (USART2 TX)**                                                                      | GPS TX -> STM32 RX, GPS RX -> STM32 TX. Genelde sadece TX hattı yeterlidir.                                                                          |
| **DS18B20 (Pil Sıcaklık)** | VDD <br> GND <br> DQ                                            | **3.3V** <br> **GND** <br> **PA5 (1-Wire, ADC1_IN5 pin üzerinde GPIO olarak)**                                                                          | Pil sıcaklığı ölçümü. DQ hattına **4.7kΩ pull-up** (3.3V'a).                                                                                         |
| **DS18B20 (ESC Sıcaklık)** | VDD <br> GND <br> DQ                                            | **3.3V** <br> **GND** <br> **PB1 (1-Wire)**                                                                                                              | ESC sıcaklığı ölçümü. DQ hattına **4.7kΩ pull-up** (3.3V'a).                                                                                         |
| **Batarya Voltaj Ölçümü (3S LiPo, ADC)** | Batarya (+) -> R1 -> ADC düğüm <br> ADC düğüm -> R2 -> GND <br> Batarya (-) -> GND | **PA4 (ADC1_IN4)** <br> **GND**                                                                                                                          | Pil seviyesi doğrudan LiPo'dan ölçülür. Bölücü: **R1=330kΩ (üst)**, **R2=47kΩ (alt)**. 12.6V tam doluda ADC girişini ~1.57V seviyesinde tutar. |
| **FT232 (USB-UART, opsiyonel)**   | TXD <br> RXD <br> VCC <br> GND                                      | **PB10 (USART3 TX)** <br> **PB11 (USART3 RX)** <br> **3.3V veya 5V** <br> **GND**                                                                       | GPS USART2'ye (PA2/PA3) taşındığı için PB10/PB11 boşa çıktı — FT232 debug için kullanılabilir. |

> ⚠️ **Open-Drain ve Pull-Up** — ESC ve servo sinyal pinleri open-drain modunda çalışır. Her sinyal hattında **4.7kΩ–10kΩ pull-up direnci** 5V hattına bağlanmalıdır. Aksi halde sinyal 3.3V'de kalır ve servo/ESC çalışmayabilir.  
> ESC için PA1 (FT) ve servo pinleri (PA6, PA7, PB0 — FT) 5V tolerant olduğu için 5V pull-up güvenlidir.

> ⚠️ **PA8/MCO1 Çakışması** — PA8 (MCO1) saat çıkışıyla çakışma riskine karşı pil DS18B20 veri hattı PA8 yerine **PA5** pinine alınmıştır.

> ⚠️ **Skywalker 4 Kablo Notu** — Kırmızı kablo ESC'nin BEC 5V hattıdır; **STM32'nin 3.3V pinine bağlanmaz**. Siyah kablo ile STM32 GND ortak edilmelidir. Beyaz kablo PA1'e gider. Sarı kablo Reverse Brake kontrol hattıdır, batarya ölçümü için kullanılmaz.

> ⚠️ **LoRa Pin Notu** — Bu düzenlemede UART için PA9/PA10, mode pinleri için PA11/PA12/PA15 kullanılır. PA11/PA12 USB hatlarıyla ilişkili pinler olduğundan upload/debug sürecinde kablolama dikkatli yapılmalıdır.

> ⚠️ **I2C Ortak Hat Notu** — GY-85 ve BMP280 aynı I2C hattına bağlanır (PB6/PB7). Modüllerde dahili pull-up yoksa SDA/SCL için 3.3V'a **4.7kΩ** pull-up eklenmelidir.

> ⚠️ **GPS Besleme Notu** — NEO-7M kartının regülatör seviyesine göre VCC 5V veya 3.3V olabilir. TTL seviye mutlaka STM32 ile uyumlu olmalıdır (3.3V önerilir).

> ⚠️ **Batarya Voltaj Ölçümü (ADC) Notu** — PA4 ADC girişine mutlaka voltaj bölücü üzerinden girilmelidir. Örn. 4S/6S sistemlerde bölücü oranı, maksimum pil voltajı altında ADC girişini **3.3V altı** tutacak şekilde seçilmelidir.

> 💡 **Kondansatör Yerleşimi (Önerilen)**
> - Servo/ESC 5V güç hattına (5V-GND arası) en az **470uF** düşük ESR kondansatör ekleyin.
> - Her DS18B20 sensörünün VDD-GND uçlarına sensöre yakın **100nF seramik** kondansatör ekleyin.
> - PA4 ADC ölçüm düğümüne (PA4-GND arası) **10uF** kondansatör paralel ekleyin (ölçümü yumuşatır). Bölücünün çıkış empedansı ~41kΩ olduğundan bu kondansatör **zorunludur**; yoksa ADC okuması hatalı olur.

> 💡 **3S LiPo Bölücü** — R1=330kΩ ve R2=47kΩ ile bölücü oranı (330+47)/47 ≈ 8.02:1 olur.
> - 12.6V (tam dolu) / 8.02 ≈ **1.57V**, 9.0V (boş) / 8.02 ≈ **1.12V** — PA4 ADC için güvenli aralıktadır.
> - Ölçülebilir maksimum pil voltajı ≈ 3.3V × 8.02 ≈ 26.5V; yanlışlıkla 4S (16.8V) bağlansa bile PA4'te ~2.09V olur.
> - 12-bit ADC ile çözünürlük ≈ 6.5 mV (pil tarafı). Pilden sürekli çekilen akım ≈ 33 µA.
> - Direnç toleransı (±%1–5) okumayı etkiler; takılan dirençleri multimetreyle ölçüp gerçek değeri `src/stm32/main.cpp` içindeki `VBAT_DIVIDER_R_TOP` / `VBAT_DIVIDER_R_BOTTOM` sabitlerine yazın.

> 💡 **DS18B20 Alternatifi** — İki DS18B20 tek bir 1-Wire hattında da çalışabilir. Bu durumda tek pin + tek 4.7kΩ pull-up yeterlidir; sensörler yazılımda ROM ID ile ayrılır.
