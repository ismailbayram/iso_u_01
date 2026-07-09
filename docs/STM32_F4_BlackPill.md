# STM32F411CEU6 Black Pill — Referans Kılavuzu

> Board: `blackpill_f411ce` (WeAct Studio Black Pill v2.0+/v3.0)  
> Chip: STM32F411CEU6 (ARM Cortex-M4F @ 100 MHz, UFQFPN48)  
> Datasheet: STM32F411xC/xE (DocID026289 Rev 6)  
> Framework: Arduino (via STM32duino / STMicroelectronics)

---

## 1. Genel Özellikler

| Özellik | Değer |
|---|---|
| Mikrodenetleyici | ARM Cortex-M4 with FPU @ 100 MHz |
| SRAM | 128 KB |
| Flash | 512 KB |
| ADC | 1 × 12-bit, 2.4 MSPS (16 kanal) |
| Timers | 6 × 16-bit, 2 × 32-bit, 1 × PWM motor kontrol |
| I2C | 3 × I2C (SMBus/PMBus) |
| USART | 3 × USART (2 × 12.5 Mbit/s, 1 × 6.25 Mbit/s) |
| SPI/I2S | 5 × SPI/I2S |
| USB | USB 2.0 FS OTG (on-chip PHY) |
| Çalışma Voltajı | 1.7V – 3.6V |

---

## 2. UFQFPN48 Pin Haritası

Kaynak: Figure 10, Table 8.

```
  ╔══════════════════════════════════════════════════════╗
  ║                    TOP VIEW                          ║
  ║                                                      ║
  ║  ┌─────┐  48  47  46  45  44  43  42  41  40  39   ║
  ║  │USB-C│                                         38 ║
  ║  └─────┘  37                                       ║
  ║        36                                          ║
  ║        35                                          ║
  ║        34                                          ║
  ║        33                                          ║
  ║        32                                          ║
  ║        31                                          ║
  ║        30                                          ║
  ║        29                                          ║
  ║        28                                          ║
  ║        27                                          ║
  ║        26                                          ║
  ║        25                                          ║
  ║        24                                          ║
  ║        23                                          ║
  ║        22                                          ║
  ║        21                                          ║
  ║        20                                          ║
  ║    1   2   3   4   5   6   7   8   9  10  11  12   ║
  ║                           13  14  15  16  17  18   ║
  ╚══════════════════════════════════════════════════════╝
```

Pin listesi (UFQFPN48, Table 8):

| Pin# | Pin Adı | I/O Yapı | Alternate Functions | Additional Functions |
|------|---------|----------|---------------------|---------------------|
| 1 | VBAT | S | — | — |
| 2 | PC13 | FT | — | ANTI_TAMP |
| 3 | PC14-OSC32_IN | FT | — | OSC32_IN |
| 4 | PC15-OSC32_OUT | FT | — | OSC32_OUT |
| 5 | PH0-OSC_IN | FT | — | OSC_IN |
| 6 | PH1-OSC_OUT | FT | — | OSC_OUT |
| 7 | NRST | FT | EVENTOUT | — |
| 8 | PC0 | FT | EVENTOUT | ADC1_IN10 |
| 9 | PC1 | FT | EVENTOUT | ADC1_IN11 |
| 10 | PC2 | FT | SPI2_MISO, I2S2ext_SD, EVENTOUT | ADC1_IN12 |
| 11 | PC3 | FT | SPI2_MOSI/I2S2_SD, EVENTOUT | ADC1_IN13 |
| 12 | VSSA | S | — | — |
| 13 | VREF+ | S | — | — |
| 14 | VDDA | S | — | — |
| 15 | **PA0-WKUP** | **TC ⚠️** | TIM2_CH1/ETR, TIM5_CH1, USART2_CTS, EVENTOUT | ADC1_IN0, WKUP1 |
| 16 | **PA1** | **FT** | TIM2_CH2, TIM5_CH2, SPI4_MOSI/I2S4_SD, USART2_RTS, EVENTOUT | ADC1_IN1 |
| 17 | PA2 | FT | TIM2_CH3, TIM5_CH3, TIM9_CH1, I2S2_CKIN, USART2_TX, EVENTOUT | ADC1_IN2 |
| 18 | PA3 | FT | TIM2_CH4, TIM5_CH4, TIM9_CH2, I2S2_MCK, USART2_RX, EVENTOUT | ADC1_IN3 |
| 19 | VSS | S | — | — |
| 20 | PA4 | FT | SPI1_NSS/I2S1_WS, SPI3_NSS/I2S3_WS, USART2_CK, EVENTOUT | ADC1_IN4 |
| 21 | PA5 | FT | TIM2_CH1/ETR, SPI1_SCK/I2S1_CK, EVENTOUT | ADC1_IN5 |
| 22 | PA6 | FT | TIM1_BKIN, TIM3_CH1, SPI1_MISO, I2S2_MCK, SDIO_CMD, EVENTOUT | ADC1_IN6 |
| 23 | PA7 | FT | TIM1_CH1N, TIM3_CH2, SPI1_MOSI/I2S1_SD, EVENTOUT | ADC1_IN7 |
| 24 | PC4 | FT | EVENTOUT | ADC1_IN14 |
| 25 | PC5 | FT | EVENTOUT | ADC1_IN15 |
| 26 | PB0 | FT | TIM1_CH2N, TIM3_CH3, SPI5_SCK/I2S5_CK, EVENTOUT | ADC1_IN8 |
| 27 | PB1 | FT | TIM1_CH3N, TIM3_CH4, SPI5_NSS/I2S5_WS, EVENTOUT | ADC1_IN9 |
| 28 | PB2 | FT | EVENTOUT | BOOT1 |
| 29 | PB10 | FT | TIM2_CH3, I2C2_SCL, SPI2_SCK/I2S2_CK, I2S3_MCK, SDIO_D7, EVENTOUT | — |
| 30 | VCAP_1 | S | — | — |
| 31 | VSS | S | — | — |
| 32 | VDD | S | — | — |
| 33 | PB12 | FT | TIM1_BKIN, I2C2_SMBA, SPI2_NSS/I2S2_WS, SPI4_NSS/I2S4_WS, SPI3_SCK/I2S3_CK, EVENTOUT | — |
| 34 | PB13 | FT | TIM1_CH1N, SPI2_SCK/I2S2_CK, SPI4_SCK/I2S4_CK, EVENTOUT | — |
| 35 | PB14 | FT | TIM1_CH2N, SPI2_MISO, I2S2ext_SD, SDIO_D6, EVENTOUT | — |
| 36 | PB15 | FT | RTC_50Hz, TIM1_CH3N, SPI2_MOSI/I2S2_SD, SDIO_CK, EVENTOUT | RTC_REFIN |
| 37 | PC6 | FT | TIM3_CH1, I2S2_MCK, USART6_TX, SDIO_D6, EVENTOUT | — |
| 38 | PC7 | FT | TIM3_CH2, SPI2_SCK/I2S2_CK, I2S3_MCK, USART6_RX, SDIO_D7, EVENTOUT | — |
| 39 | PC8 | FT | TIM3_CH3, USART6_CK, SDIO_D0, EVENTOUT | — |
| 40 | PC9 | FT | MCO_2, TIM3_CH4, I2C3_SDA, I2S2_CKIN, SDIO_D1, EVENTOUT | — |
| 41 | PA8 | FT | MCO_1, TIM1_CH1, I2C3_SCL, USART1_CK, USB_FS_SOF, SDIO_D1, EVENTOUT | — |
| 42 | PA9 | FT | TIM1_CH2, I2C3_SMBA, USART1_TX, USB_FS_VBUS, SDIO_D2, EVENTOUT | OTG_FS_VBUS |
| 43 | PA10 | FT | TIM1_CH3, SPI5_MOSI/I2S5_SD, USART1_RX, USB_FS_ID, EVENTOUT | — |
| 44 | PA11 | FT | TIM1_CH4, SPI4_MISO, USART1_CTS, USART6_TX, USB_FS_DM, EVENTOUT | — |
| 45 | PA12 | FT | TIM1_ETR, SPI5_MISO, USART1_RTS, USART6_RX, USB_FS_DP, EVENTOUT | — |
| 46 | PA13 | FT | JTMS-SWDIO, EVENTOUT | — |
| 47 | VSS | S | — | — |
| 48 | VDD | S | — | — |

Kart header'ında ek olarak çıkan pinler:

| Pin | I/O Yapı | Alternate Functions |
|-----|----------|---------------------|
| PA15 | FT | JTDI, TIM2_CH1/ETR, SPI1_NSS/I2S1_WS, SPI3_NSS/I2S3_WS, USART1_TX, EVENTOUT |
| PB3 | FT | JTDO-SWO, TIM2_CH2, SPI1_SCK/I2S1_CK, SPI3_SCK/I2S3_CK, USART1_RX, I2C2_SDA, EVENTOUT |
| PB4 | FT | JTRST, TIM3_CH1, SPI1_MISO, SPI3_MISO, I2S3ext_SD, I2C3_SDA, SDIO_D0, EVENTOUT |
| PB5 | **TC ⚠️** | TIM3_CH2, I2C1_SMBA, SPI1_MOSI/I2S1_SD, SPI3_MOSI/I2S3_SD, SDIO_D3, EVENTOUT |
| PB6 | FT | TIM4_CH1, I2C1_SCL, USART1_TX, EVENTOUT |
| PB7 | FT | TIM4_CH2, I2C1_SDA, USART1_RX, SDIO_D0, EVENTOUT |
| PB8 | FT | TIM4_CH3, TIM10_CH1, I2C1_SCL, SPI5_MOSI/I2S5_SD, I2C3_SDA, SDIO_D4, EVENTOUT |
| PB9 | FT | TIM4_CH4, TIM11_CH1, I2C1_SDA, SPI2_NSS/I2S2_WS, I2C2_SDA, SDIO_D5, EVENTOUT |
| PB11 | FT | TIM2_CH4, I2C2_SDA, I2S2_CKIN, EVENTOUT |

> **I/O Yapı Kısaltmaları (Table 7):**  
> **FT** = 5V tolerant I/O  
> **TC** = Standard 3.3V I/O (5V toleranssız)  
> **S** = Supply pin

---

## 3. Non-5V-Tolerant Pinler (TC)

STM32F411CEU6'da yalnızca iki pin **TC**'dir (5V toleranssız):

| Pin | Pin# | UFQFPN48 | Not |
|-----|------|----------|-----|
| **PA0** | 15 | Evet | WKUP1, ADC1_IN0, ayrıca USER BUTTON'a bağlı |
| **PB5** | — | Header | I2C1_SMBA, SPI1/SPI3 MOSI, SDIO_D3 |

Diğer tüm I/O pinleri **FT** (5V tolerant, VIN max 5.5V).

---

## 4. Kart Üzerinde Önemli Notlar

- **PA0 (pin 15):** Kart üzerinde **USER BUTTON'a** bağlıdır (3.3V harici pull-up). Ayrıca **WKUP1** ve **ADC1_IN0** ek fonksiyonlarına sahiptir. I/O yapısı **TC** olduğu için 5V uygulanmamalıdır.
- **PC13 (pin 2):** Dahili LED — **LOW = yanar, HIGH = söner**.
- **BOOT0 (pin 44):** HIGH = DFU modu (USB programlama).
- **VUSB:** USB 5V girişi — kartı USB'den besler.
- **8MB QSPI Flash (W25Q64, opsiyonel):** PA4/PA5/PA6/PA7 (SPI1). Bu pinler başka amaçla kullanılıyorsa QSPI flash kullanılamaz.
- **VCAP_1 (pin 30):** 2.2µF harici kapasitör bağlanmalıdır.

---

## 5. Arduino Çekirdeği Notları

| Parametre | Değer |
|---|---|
| PlatformIO Board | `blackpill_f411ce` |
| Framework | Arduino (STM32duino veya STMicroelectronics) |
| CPU Frekansı | 100 MHz (`board_build.f_cpu = 100000000L`) |
| Upload Protokolü | `dfu` (USB DFU) veya ST-Link (SWD) |
| Serial (USB CDC) | USB üstünden (`-D USBCON` ile) |
| Serial1 (USART1) | PA9 (TX), PA10 (RX) |
| I2C (Wire) | PB6 (SCL), PB7 (SDA) |

---

## 6. Referans Belgeler

- **STM32F411xC/xE Datasheet (DocID026289 Rev 6):** `STM32F411XC.PDF` (proje kök dizini)
- **Reference Manual (RM0383):** https://www.st.com/resource/en/reference_manual/rm0383-stm32f411xce-advanced-armbased-32bit-mcus-stmicroelectronics.pdf
- **WeAct Black Pill GitHub:** https://github.com/WeActStudio/WeActStudio.MiniSTM32F4x1
- **WeAct Pinout Diagram (v2.0+):** https://github.com/WeActStudio/WeActStudio.MiniSTM32F4x1/blob/master/General%20document/STM32F4x1%20v2.0%2B%20Pin%20Layout.pdf
