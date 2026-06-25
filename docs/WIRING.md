# RC Kumanda Ana İstasyonu - Bağlantı Şeması (Pinout)

Bu bölümde, ESP32 tabanlı uzaktan kumanda ünitesinin bileşenleri arasındaki donanımsal pin bağlantılarını içerir.

## 1. Genel Bağlantı Tablosu

| Bileşen                | Bileşen Pini                                            | ESP32 Pini                                                                                                          | İşlevi / Açıklaması                                          |
| :--------------------- | :------------------------------------------------------ | :------------------------------------------------------------------------------------------------------------------ | :----------------------------------------------------------- |
| **OLED / LCD Ekran**   | VCC <br> GND <br> SDA <br> SCL                          | **3V3** <br> **GND** <br> **GPIO 21** <br> **GPIO 22**                                                              | I2C Haberleşme Hattı (Sistem Bilgileri Ekranı)               |
| **LoRa (E22-900T22D)** | VCC <br> GND <br> RXD <br> TXD <br> **AUX** <br> **M0** <br> **M1** | **3V3** <br> **GND** <br> **GPIO 17 (TX2)** <br> **GPIO 16 (RX2)** <br> **GPIO 4 (INPUT)** <br> **GPIO 18 (LOW)** <br> **GPIO 5 (LOW)** | UART2 Haberleşme — AUX modül durumu için INPUT, M0/M1 normal mod (LOW) |
| **Sol Joystick**       | VCC <br> GND <br> VRX (Roll) <br> VRY (Pitch)           | **3V3** <br> **GND** <br> **GPIO 32** <br> **GPIO 33**                                                              | ADC1 Kanalı (Analog Giriş - Sinyal çakışmasından etkilenmez) |
| **Sağ Joystick**       | VCC <br> GND <br> VRX (Yaw) <br> VRY (Throttle)         | **3V3** <br> **GND** <br> **GPIO 34** <br> **GPIO 35**                                                              | ADC1 Kanalı (Analog Giriş - Sadece Giriş Destekli Pinler)    |
| **Buzzer**             | Artı (+) <br> Eksi (-)                                  | **GPIO 25** <br> **GND** <br>                                                                                       | Telemetri ve Sistem Uyarı Sesleri Çıkışı (DAC Destekli Pin)  |

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

| Bileşen                | Bileşen Pini                                            | STM32F411CEU6 (Black Pill) Pini                                                                                 | İşlevi / Açıklaması                                                     |
| :--------------------- | :------------------------------------------------------ | :-------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------- |
| **LoRa (E22-900T22D)** | VCC <br> GND <br> RXD <br> TXD <br> **AUX** <br> **M0** <br> **M1** | **3.3V** <br> **GND** <br> **PA9 (Serial1 TX)** <br> **PA10 (Serial1 RX)** <br> **PA3 (GPIO, INPUT)** <br> **PA1 (GPIO, LOW)** <br> **PA2 (GPIO, LOW)** | USART1 Haberleşme Hattı — AUX modül durumu için INPUT, M0/M1 normal mod (LOW) |
| **Servo 1 (Roll)** | Sinyal <br> VCC <br> GND | **PA6 (TIM3_CH1, open-drain)** <br> **5V** <br> **GND** | Kumanda sol stick X ekseni — kanat/roll kontrolü |
| **Servo 2 (Pitch)** | Sinyal <br> VCC <br> GND | **PA7 (TIM3_CH2, open-drain)** <br> **5V** <br> **GND** | Kumanda sol stick Y ekseni — irtifa/pitch kontrolü |
| **Servo 3 (Yaw)** | Sinyal <br> VCC <br> GND | **PB0 (TIM3_CH3, open-drain)** <br> **5V** <br> **GND** | Kumanda sağ stick X ekseni — dümen/yaw kontrolü |
| **FT232 (USB-UART)** | TXD <br> RXD <br> VCC <br> GND | **PA12 (USART6 RX)** <br> **PA11 (USART6 TX)** <br> **3.3V veya 5V** <br> **GND** | Bilgisayardan LoRa verilerini izleme (monitör) — STM32 TX(PA11) → FT232 RX, STM32 RX(PA12) → FT232 TX |

> ⚠️ **Open-Drain ve Pull-Up** — ESC ve servo sinyal pinleri open-drain modunda çalışır. Her sinyal hattında **4.7kΩ–10kΩ pull-up direnci** 5V hattına bağlanmalıdır. Aksi halde sinyal 3.3V'de kalır ve servo/ESC çalışmayabilir.
