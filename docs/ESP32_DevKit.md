# ESP32-DevKitC — Referans Kılavuzu

> Board: `esp32dev` (Espressif ESP32-DevKitC / generic ESP32 development board)  
> Chip: ESP32-WROOM-32 (dual-core Xtensa LX6, Wi-Fi + BLE)  
> Framework: Arduino

---

## 1. Genel Özellikler

| Özellik | Değer |
|---|---|
| Mikrodenetleyici | Xtensa LX6 çift çekirdek @ 240 MHz |
| SRAM | 520 KB |
| Flash | 4 MB (SPI flash) |
| Wi-Fi | 802.11 b/g/n (HT20) |
| Bluetooth | BLE 4.2 + BR/EDR |
| ADC | 2 × 12-bit SAR ADC (ADC1: 8 kanal, ADC2: 10 kanal) |
| DAC | 2 × 8-bit (GPIO 25, 26) |
| Çalışma Voltajı | 3.3V (5V toleranssız — GPIO'lar 3.3V seviyesindedir) |

---

## 2. Proje Pin Atamaları (ISO U1 Kumanda)

| Bileşen | Pin | ADC Kanalı | Tür | Tanım |
|---|---|---|---|---|
| **Sol Joystick X (Roll)** | **GPIO 36** | ADC1_CH0 | Analog Giriş | Sol stick yatay eksen |
| **Sol Joystick Y (Pitch)** | **GPIO 39** | ADC1_CH3 | Analog Giriş | Sol stick dikey eksen |
| **Sağ Joystick X (Yaw)** | **GPIO 34** | ADC1_CH6 | Analog Giriş | Sağ stick yatay eksen |
| **Sağ Joystick Y (Throttle)** | **GPIO 35** | ADC1_CH7 | Analog Giriş | Sağ stick dikey eksen (gaz) |
| **Buzzer** | **GPIO 25** | — | Çıkış (DAC) | Piezo buzzer — `tone()` çıkışı |
| **OLED SDA** | **GPIO 21** | — | I2C Veri | SSD1306 OLED I2C veri hattı |
| **OLED SCL** | **GPIO 22** | — | I2C Saat | SSD1306 OLED I2C saat hattı |

### Planlı / Gelecek Kullanım

| Bileşen | Pin | Tür | Tanım |
|---|---|---|---|
| **LoRa E22 RXD** | **GPIO 16 (TX2)** | UART2 Çıkış | ESP32 TX → LoRa RX (UART2) |
| **LoRa E22 TXD** | **GPIO 17 (RX2)** | UART2 Giriş | LoRa TX → ESP32 RX (UART2) |
| **LoRa E22 AUX** | **GPIO 4** | Giriş | LoRa modül durum çıkışı |
| **LoRa E22 M0** | **GPIO 18** | Çıkış | LoRa mod kontrol (seviye) |
| **LoRa E22 M1** | **GPIO 5** | Çıkış | LoRa mod kontrol (seviye) |

---

## 3. ESP32 Pin Haritası

```
                         ┌─────────────┐
               3V3 ─────┤ 1          38├───── GND
               EN  ─────┤ 2          37├───── GPIO 23
          (R) GPIO 36 ──┤ 3          36├───── GPIO 22 (OLED SCL)
          (R) GPIO 39 ──┤ 4          35├───── GPIO 1 (TX)
          (R) GPIO 34 ──┤ 5          34├───── GPIO 3 (RX)
          (R) GPIO 35 ──┤ 6          33├───── GPIO 21 (OLED SDA)
               GPIO 32 ──┤ 7          32├───── GND
               GPIO 33 ──┤ 8          31├───── GPIO 19
               GPIO 25 ──┤ 9          30├───── GPIO 18 (LoRa M0)
               GPIO 26 ──┤10          29├───── GPIO 5  (LoRa M1)
               GPIO 27 ──┤11          28├───── GPIO 17 (LoRa TXD)
               GPIO 14 ──┤12          27├───── GPIO 16 (LoRa RXD)
               GPIO 12 ──┤13          26├───── GPIO 4  (LoRa AUX)
               GND  ────┤14          25├───── GPIO 0
               GPIO 13 ──┤15          24├───── GPIO 2
          (T) GPIO 9  ──┤16          23├───── GPIO 15
          (T) GPIO 10 ──┤17          22├───── GPIO 8
          (T) GPIO 11 ──┤18          21├───── GPIO 7
               VIN  ────┤19          20├───── GPIO 6
                         └─────────────┘
                         ESP32-WROOM-32
                         (30-pin yaygın varyant)

    (R) = ADC1 (güvenli analog giriş, Wi-Fi etkilemez)
    (T) = GPIO 6-11: SPI flash için kullanılır, genelde kullanılamaz
```

---

## 4. ADC Kullanım Kılavuzu

### ADC1 Kanalları (Wi-Fi/RF'den etkilenmez — ÖNERİLEN)

| GPIO | ADC1 Kanalı | Bu Projede |
|---|---|---|
| GPIO 36 | ADC1_CH0 | Sol Joystick X (Roll) |
| GPIO 37 | ADC1_CH1 | — |
| GPIO 38 | ADC1_CH2 | — |
| GPIO 39 | ADC1_CH3 | Sol Joystick Y (Pitch) |
| GPIO 32 | ADC1_CH4 | — |
| GPIO 33 | ADC1_CH5 | — |
| GPIO 34 | ADC1_CH6 | Sağ Joystick X (Yaw) |
| GPIO 35 | ADC1_CH7 | Sağ Joystick Y (Throttle) |

### ADC2 Kanalları (Wi-Fi aktifken kararsız — KAÇININ)

| GPIO | ADC2 Kanalı | Not |
|---|---|---|
| GPIO 0 | ADC2_CH1 | Boot modu seçimi |
| GPIO 2 | ADC2_CH2 | Dahili LED |
| GPIO 4 | ADC2_CH3 | LoRa AUX — analog kullanmayın |
| GPIO 12 | ADC2_CH4 | — |
| GPIO 13 | ADC2_CH5 | — |
| GPIO 14 | ADC2_CH6 | — |
| GPIO 15 | ADC2_CH7 | — |
| GPIO 25 | ADC2_CH8 | Buzzer — analog kullanmayın |
| GPIO 26 | ADC2_CH9 | DAC destekli |
| GPIO 27 | ADC2_CH10 | — |

> ⚠️ Wi-Fi/BLE aktifken ADC2 **kararsız okuma yapar veya hiç okuma yapamaz**.  
> Tüm joystick eksenleri bu nedenle ADC1 pinlerine bağlanmıştır.

---

## 5. Önemli Uyarılar

> ⚠️ **Tüm GPIO'lar 3.3V seviyesindedir.**  
> 5V uygulanması kalıcı hasara yol açar. Joystick VCC'si 3.3V hattına bağlanmalıdır.

> ⚠️ **GPIO 6–11 (flash pinleri) genel amaçlı kullanılamaz.**  
> Dahili SPI flash'a aittir. Kullanılırsa sistem çökebilir.

> ⚠️ **GPIO 0 boot modu seçimindedir.**  
> LOW = flash modu (programlama). Çekme direnci olmadan kullanmayın.

> ⚠️ **GPIO 2 çıkışta yüksek seviyede başlar.**  
> Boot sırasında HIGH'dir, bazı devrelerde istenmeyen tetiklemeye yol açabilir.

> ⚠️ **GPIO 12 (MTDI) boot voltajını belirler.**  
> Boot sırasında LOW olmalıdır (iç çekme). Harici çekme ile flash voltajı değişir.

> ⚠️ **ADC2 pinleri Wi-Fi/BLE açıkken analog okuma için güvenilir değildir.**  
> Joystick gibi analog sensörler **kesinlikle ADC1'e** bağlanmalıdır.

---

## 6. I2C ve OLED

| Parametre | Değer |
|---|---|
| I2C Kanalı | Wire (varsayılan, GPIO 21=SDA, GPIO 22=SCL) |
| OLED Sürücü | SSD1306, 128×32 piksel |
| I2C Adres | 0x3C |
| Besleme | 3.3V |

---

## 7. UART (Planlı: LoRa Bağlantısı)

| UART | TX | RX | Hız | Bağlı Bileşen |
|---|---|---|---|---|
| **UART2** | GPIO 16 | GPIO 17 | — | LoRa E22-900T22D |

> USART1 (GPIO 1/3) seri konsol içindir, LoRa ile kullanılmaz.

---

## 8. Kaynak Koddaki Sabitler

```cpp
// src/esp32/main.cpp
#define PIN_BUZZER   25
#define PIN_JOY_L_X  36
#define PIN_JOY_L_Y  39
#define PIN_JOY_R_X  34
#define PIN_JOY_R_Y  35
```
