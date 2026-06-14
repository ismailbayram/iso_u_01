# RC Kumanda Ana İstasyonu - Bağlantı Şeması (Pinout)

Bu bölümde, ESP32 tabanlı uzaktan kumanda ünitesinin bileşenleri arasındaki donanımsal pin bağlantılarını içerir.

## 1. Genel Bağlantı Tablosu

| Bileşen                | Bileşen Pini                                            | ESP32 Pini                                                                                                          | İşlevi / Açıklaması                                          |
| :--------------------- | :------------------------------------------------------ | :------------------------------------------------------------------------------------------------------------------ | :----------------------------------------------------------- |
| **OLED / LCD Ekran**   | VCC <br> GND <br> SDA <br> SCL                          | **3V3** <br> **GND** <br> **GPIO 21** <br> **GPIO 22**                                                              | I2C Haberleşme Hattı (Sistem Bilgileri Ekranı)               |
| **LoRa (E22-900T22D)** | VCC <br> GND <br> RXD <br> TXD <br> AUX <br> M0 <br> M1 | **3V3** <br> **GND** <br> **GPIO 17 (RX2)** <br> **GPIO 16 (TX2)** <br> **GPIO 4** <br> **GPIO 18** <br> **GPIO 5** | UART2 Donanımsal Haberleşme Hattı ve Mod Kontrol Pinleri     |
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
