# Yer İstasyonu, IMU Kalibrasyonu ve Arming — Implementasyon Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ESP32 kumandaya USB ile bağlanan bir Python yer istasyonu kurmak; oradan tek butonla GY-85 kalibrasyonunu tetikleyip STM32 flash'ına kalıcı yazmak; ve STM32'ye güç verildiğinde motorun kendiliğinden dönmesini engelleyen bir arming kilidi eklemek.

**Architecture:** Kumandadan uçağa yeni bir `PACKET_TYPE_COMMAND` paketi eklenir; kalibrasyon ve disarm bu kanaldan gider. Arming jesti uçakta, gelen kontrol paketlerinden çözülür — algılayıcı ortak bir başlıkta durur, iki firmware de aynı kodu derler. Kumanda USB seriye makine-okunur `$T`/`$S` satırları basar ve satır bazlı komut kabul eder; Python tarafı bu iki yönü sarar.

**Tech Stack:** C++ (Arduino/PlatformIO, STM32duino + ESP32 Arduino), Python 3.14 + tkinter + pyserial, pytest, g++ (ana makinede header testleri).

**Spec:** `docs/superpowers/specs/2026-09-22-nav-station-design.md`

## Global Constraints

- **Telemetri hızı 1 Hz'de kalır.** `TELEMETRY_REQUEST_INTERVAL_MS = 1000` ve `TELEMETRY_RX_GUARD_MS = 250` değiştirilmez. Gerekçe spec Bölüm 3.
- **`TelemetryPacket` 36 → 37 bayt olur.** İki kart da birlikte flash'lanmak zorunda. ESP32 boot'ta `TEL_STRUCT_SIZE` basar; 37 görülmeden saha testine geçilmez.
- **Pusula kalibrasyonda sıfırlanmaz.** Yalnız `accelOffsetX/Y` ve `gyroBiasX/Y/Z`.
- **Uçuşta jestle disarm yoktur.** Disarm yalnız: güç kesme, >5 sn link kaybı, `COMMAND_DISARM`.
- **Kalibrasyon armed durumdayken reddedilir** — hem STM32 komutu eler, hem Python butonu pasifleşir.
- **Eşikler (0–4095 ölçeği):** `DOWN_THRESHOLD = 400`, `RELEASE_THRESHOLD = 1600`, `HOLD_MS = 500`, `SEQUENCE_TIMEOUT_MS = 3000`.
- **Sensör ölçekleri:** ivmeölçer **64 LSB/g** (ADXL345 ±2 g, 256 LSB/g, firmware 4'e bölüyor), jiro **14.375 LSB/(°/s)** (ITG3205 ±2000 °/s).
- **Flash kayıt konumu:** sektör 7, `0x08060000`.
- **Sıcaklık yokluk işareti:** `INT16_MIN` (−32768). Python bunu `--` gösterir, 0 değil.
- **Python bağımlılığı:** `brew install python-tk@3.14` gerekli. Komutlar `.env/bin/python` ile çalıştırılır.
- Yeni Python kodu `tools/navstation/` altında. Ana makinede derlenen C++ testleri `test/native/` altında ve **`pio test` ile değil**, `tools/run_native_tests.sh` ile çalıştırılır (`test/` klasöründe zaten PlatformIO test'i olmayan eski taslaklar var).

---

## Dosya Yapısı

| Dosya | Sorumluluk | Durum |
|---|---|---|
| `include/radio_protocol.h` | Paket tanımları, komut/bayrak sabitleri | Değiştirilir |
| `include/arming.h` | Arming jesti state machine, donanımdan bağımsız | Yeni |
| `include/calibration.h` | Flash kayıt yapısı + sağlama, donanımdan bağımsız | Yeni |
| `src/stm32/main.cpp` | Arming kilidi, komut ayrıştırma, kalibrasyon, flash | Değiştirilir |
| `src/esp32/main.cpp` | `$T`/`$S` çıktısı, USB komut girişi, OLED/buzzer | Değiştirilir |
| `test/native/test_protocol.cpp` | Paket boyu ve sağlama testleri | Yeni |
| `test/native/test_arming.cpp` | Jest state machine testleri | Yeni |
| `test/native/test_calibration.cpp` | Kayıt sağlaması testleri | Yeni |
| `tools/run_native_tests.sh` | Üç native testi derleyip çalıştırır | Yeni |
| `tools/navstation/attitude.py` | Saf matematik, G/Ç yok | Yeni |
| `tools/navstation/link.py` | Seri okuma thread'i, ayrıştırma, komut gönderme | Yeni |
| `tools/navstation/ui.py` | tkinter penceresi ve çizim | Yeni |
| `tools/navstation/__main__.py` | Argümanlar, modülleri bağlar | Yeni |
| `tools/navstation/README.md` | Kurulum ve kullanım | Yeni |
| `tools/navstation/tests/test_attitude.py` | pytest | Yeni |
| `tools/navstation/tests/test_link.py` | pytest | Yeni |

---

### Task 1: Protokol — komut paketi ve durum bayrakları

**Files:**
- Modify: `include/radio_protocol.h`
- Create: `test/native/test_protocol.cpp`
- Create: `tools/run_native_tests.sh`

**Interfaces:**
- Consumes: yok (ilk görev)
- Produces: `radio::PACKET_TYPE_COMMAND`, `radio::CommandPacket{uint8_t sequence; uint8_t command;}`, `radio::COMMAND_CALIBRATE_LEVEL/CLEAR_CALIBRATION/DISARM`, `radio::STATUS_ACCEL_OK/GYRO_OK/MAG_OK/BARO_OK/CALIBRATED/ARMED`, `TelemetryPacket::statusFlags`

- [ ] **Step 1: Testi yaz**

`test/native/test_protocol.cpp`:

```cpp
#include <cassert>
#include <cstdio>
#include "radio_protocol.h"

int main()
{
    assert(sizeof(radio::TelemetryPacket) == 37);
    assert(sizeof(radio::CommandPacket) == 2);
    assert(sizeof(radio::ControlPacket) == 10);
    assert(sizeof(radio::TelemetryRequestPacket) == 1);

    assert(radio::PACKET_TYPE_COMMAND == 4);
    assert(radio::COMMAND_CALIBRATE_LEVEL == 1);
    assert(radio::COMMAND_CLEAR_CALIBRATION == 2);
    assert(radio::COMMAND_DISARM == 3);

    assert(radio::STATUS_ACCEL_OK == 0x01);
    assert(radio::STATUS_GYRO_OK == 0x02);
    assert(radio::STATUS_MAG_OK == 0x04);
    assert(radio::STATUS_BARO_OK == 0x08);
    assert(radio::STATUS_CALIBRATED == 0x10);
    assert(radio::STATUS_ARMED == 0x20);

    // Sagalama: tip ve uzunluk da hesaba katiliyor.
    const uint8_t payload[2] = {0x01, 0x02};
    assert(radio::computeFrameChecksum(4, 2, payload) == (uint8_t)(4 ^ 2 ^ 0x01 ^ 0x02));

    // Tek bayt degisimi sagalamayi degistirmeli.
    const uint8_t altered[2] = {0x01, 0x03};
    assert(radio::computeFrameChecksum(4, 2, payload) !=
           radio::computeFrameChecksum(4, 2, altered));

    printf("test_protocol: OK\n");
    return 0;
}
```

- [ ] **Step 2: Test koşucusunu yaz**

`tools/run_native_tests.sh`:

```bash
#!/usr/bin/env bash
# Ana makinede derlenen donanimsiz testler. PlatformIO'nun test runner'i
# kullanilmiyor; test/ klasorunde PlatformIO testi olmayan eski taslaklar var.
set -euo pipefail

cd "$(dirname "$0")/.."
OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT

FAILED=0
for src in test/native/test_*.cpp; do
    name="$(basename "$src" .cpp)"
    if ! g++ -std=c++17 -Wall -Wextra -Iinclude "$src" -o "$OUT/$name"; then
        echo "DERLEME HATASI: $src"
        FAILED=1
        continue
    fi
    if ! "$OUT/$name"; then
        echo "TEST BASARISIZ: $src"
        FAILED=1
    fi
done

exit "$FAILED"
```

- [ ] **Step 3: Testi çalıştır, başarısız olduğunu gör**

```bash
chmod +x tools/run_native_tests.sh
./tools/run_native_tests.sh
```

Beklenen: derleme hatası — `PACKET_TYPE_COMMAND`, `CommandPacket`, `STATUS_ARMED` tanımlı değil.

- [ ] **Step 4: Protokolü yaz**

`include/radio_protocol.h` içinde `PacketType` enum'unu genişlet:

```cpp
enum PacketType : uint8_t {
  PACKET_TYPE_CONTROL = 1,
  PACKET_TYPE_TELEMETRY = 2,
  PACKET_TYPE_TELEMETRY_REQ = 3,
  PACKET_TYPE_COMMAND = 4
};

enum CommandId : uint8_t {
  COMMAND_CALIBRATE_LEVEL = 1,
  COMMAND_CLEAR_CALIBRATION = 2,
  COMMAND_DISARM = 3
};

// TelemetryPacket::statusFlags bitleri.
enum StatusFlag : uint8_t {
  STATUS_ACCEL_OK = 1 << 0,
  STATUS_GYRO_OK = 1 << 1,
  STATUS_MAG_OK = 1 << 2,
  STATUS_BARO_OK = 1 << 3,
  STATUS_CALIBRATED = 1 << 4,
  STATUS_ARMED = 1 << 5
};

struct __attribute__((packed)) CommandPacket {
  uint8_t sequence;
  uint8_t command;
};
```

`TelemetryPacket`'in sonuna, `baroTempCentiC` satırından hemen sonra:

```cpp
  uint8_t statusFlags;     // StatusFlag bitleri.
```

- [ ] **Step 5: Testi çalıştır, geçtiğini gör**

```bash
./tools/run_native_tests.sh
```

Beklenen: `test_protocol: OK`

- [ ] **Step 6: İki firmware'in de derlendiğini doğrula**

```bash
pio run
```

Beklenen: `esp32 SUCCESS`, `stm32 SUCCESS`. `statusFlags` henüz doldurulmuyor, bu normal.

- [ ] **Step 7: Commit**

```bash
git add include/radio_protocol.h test/native/test_protocol.cpp tools/run_native_tests.sh
git commit -m "feat(protocol): komut paketi ve telemetri durum bayraklari ekle"
```

---

### Task 2: Ortak arming jesti state machine

**Files:**
- Create: `include/arming.h`
- Create: `test/native/test_arming.cpp`

**Interfaces:**
- Consumes: yok
- Produces: `arming::GestureDetector` — `void reset(uint32_t nowMs)`, `bool update(uint16_t throttleAxis, uint16_t pitchAxis, uint32_t nowMs)` (armed'a geçiş anında bir kez `true`), `void disarm(uint32_t nowMs)`, `bool isArmed() const`, `arming::Phase phase() const`. Sabitler: `arming::DOWN_THRESHOLD`, `RELEASE_THRESHOLD`, `HOLD_MS`, `SEQUENCE_TIMEOUT_MS`.

- [ ] **Step 1: Testi yaz**

`test/native/test_arming.cpp`:

```cpp
#include <cassert>
#include <cstdio>
#include "arming.h"

using arming::GestureDetector;
using arming::Phase;

static const uint16_t DOWN = 100;   // DOWN_THRESHOLD altinda
static const uint16_t UP = 3000;    // RELEASE_THRESHOLD ustunde
static const uint16_t MID = 2048;   // ikisinin de disinda

// Jesti tamamlar, armed'a gectigi turda true dondugunu dogrular.
static bool runFullGesture(GestureDetector &d, uint32_t startMs)
{
    bool armedEdge = false;
    armedEdge |= d.update(DOWN, DOWN, startMs);
    armedEdge |= d.update(UP, UP, startMs + 200);
    armedEdge |= d.update(DOWN, DOWN, startMs + 400);
    armedEdge |= d.update(DOWN, DOWN, startMs + 900);  // 500 ms tutuldu
    return armedEdge;
}

int main()
{
    // 1. Yeni detector armed degil.
    {
        GestureDetector d;
        d.reset(0);
        assert(!d.isArmed());
        assert(d.phase() == Phase::Idle);
    }

    // 2. Tam jest arm eder ve kenar tam bir kez gelir.
    {
        GestureDetector d;
        d.reset(0);
        assert(runFullGesture(d, 1000));
        assert(d.isArmed());
        // Zaten armed'ken tekrar kenar gelmez.
        assert(!d.update(DOWN, DOWN, 2000));
    }

    // 3. Tek asagi cevrimi arm etmez.
    {
        GestureDetector d;
        d.reset(0);
        d.update(DOWN, DOWN, 0);
        d.update(DOWN, DOWN, 600);
        assert(!d.isArmed());
    }

    // 4. Ikinci asagida yeterince tutulmazsa arm etmez.
    {
        GestureDetector d;
        d.reset(0);
        d.update(DOWN, DOWN, 0);
        d.update(UP, UP, 200);
        d.update(DOWN, DOWN, 400);
        d.update(DOWN, DOWN, 800);   // sadece 400 ms
        assert(!d.isArmed());
    }

    // 5. Ikinci asagi biraktirilirsa bastan baslar.
    {
        GestureDetector d;
        d.reset(0);
        d.update(DOWN, DOWN, 0);
        d.update(UP, UP, 200);
        d.update(DOWN, DOWN, 400);
        d.update(MID, MID, 600);     // birakti
        assert(d.phase() == Phase::Idle);
        d.update(DOWN, DOWN, 700);
        d.update(DOWN, DOWN, 1300);
        assert(!d.isArmed());
    }

    // 6. Sekans zaman asimi bastan baslatir.
    {
        GestureDetector d;
        d.reset(0);
        d.update(DOWN, DOWN, 0);
        d.update(UP, UP, 4000);      // 3000 ms gecti
        assert(d.phase() == Phase::Idle);
    }

    // 7. Tek cubuk ilerletmez.
    {
        GestureDetector d;
        d.reset(0);
        d.update(DOWN, UP, 0);
        assert(d.phase() == Phase::Idle);
        d.update(UP, DOWN, 100);
        assert(d.phase() == Phase::Idle);
    }

    // 8. Esik sinirlari: tam esik degeri asagi sayilmaz.
    {
        GestureDetector d;
        d.reset(0);
        d.update(arming::DOWN_THRESHOLD, arming::DOWN_THRESHOLD, 0);
        assert(d.phase() == Phase::Idle);
        d.update(arming::DOWN_THRESHOLD - 1, arming::DOWN_THRESHOLD - 1, 100);
        assert(d.phase() == Phase::Down1);
    }

    // 9. disarm() armed'i kaldirir ve jest tekrar aranabilir.
    {
        GestureDetector d;
        d.reset(0);
        runFullGesture(d, 0);
        assert(d.isArmed());
        d.disarm(2000);
        assert(!d.isArmed());
        assert(d.phase() == Phase::Idle);
        assert(runFullGesture(d, 3000));
        assert(d.isArmed());
    }

    printf("test_arming: OK\n");
    return 0;
}
```

- [ ] **Step 2: Testi çalıştır, başarısız olduğunu gör**

```bash
./tools/run_native_tests.sh
```

Beklenen: `arming.h: No such file or directory`

- [ ] **Step 3: `include/arming.h` yaz**

```cpp
#pragma once

#include <stdint.h>

// Arming jesti: iki cubuk da asagi, birak, tekrar asagi, 500 ms tut.
// Donanimdan bagimsiz tutuluyor cunku hem STM32 (yetkili karar) hem ESP32
// (anlik sesli geri bildirim) ayni kodu derliyor. Ikisi birbirinden sapmasin.
namespace arming {

constexpr uint16_t DOWN_THRESHOLD = 400;
constexpr uint16_t RELEASE_THRESHOLD = 1600;
constexpr uint32_t HOLD_MS = 500;
constexpr uint32_t SEQUENCE_TIMEOUT_MS = 3000;

enum class Phase : uint8_t {
  Idle = 0,
  Down1 = 1,
  Up1 = 2,
  Down2 = 3
};

class GestureDetector {
public:
  void reset(uint32_t nowMs) {
    phase_ = Phase::Idle;
    phaseEnteredMs_ = nowMs;
    sequenceStartedMs_ = nowMs;
    armed_ = false;
  }

  // Bir kontrol paketi besler. Armed'a gecis turunda bir kez true doner.
  bool update(uint16_t throttleAxis, uint16_t pitchAxis, uint32_t nowMs) {
    if (armed_) {
      return false;
    }

    const bool bothDown =
        throttleAxis < DOWN_THRESHOLD && pitchAxis < DOWN_THRESHOLD;
    const bool bothReleased =
        throttleAxis > RELEASE_THRESHOLD && pitchAxis > RELEASE_THRESHOLD;

    switch (phase_) {
    case Phase::Idle:
      if (bothDown) {
        enter(Phase::Down1, nowMs);
        sequenceStartedMs_ = nowMs;
      }
      break;

    case Phase::Down1:
      // Zaman asimi gecisten ONCE bakilir: sekans suresi dolduysa gec gelen
      // dogru hareket sekansi kurtarmamali.
      if (timedOut(nowMs)) {
        enter(Phase::Idle, nowMs);
      } else if (bothReleased) {
        enter(Phase::Up1, nowMs);
      }
      break;

    case Phase::Up1:
      if (timedOut(nowMs)) {
        enter(Phase::Idle, nowMs);
      } else if (bothDown) {
        enter(Phase::Down2, nowMs);
      }
      break;

    case Phase::Down2:
      // Son asamada sekans zaman asimi uygulanmaz; tutma suresi bittiginde
      // sekansin toplam suresi esigi asabilir ve bu yaris istenmiyor.
      if (!bothDown) {
        enter(Phase::Idle, nowMs);
      } else if (nowMs - phaseEnteredMs_ >= HOLD_MS) {
        armed_ = true;
        enter(Phase::Idle, nowMs);
        return true;
      }
      break;
    }

    return false;
  }

  void disarm(uint32_t nowMs) {
    armed_ = false;
    enter(Phase::Idle, nowMs);
  }

  bool isArmed() const { return armed_; }
  Phase phase() const { return phase_; }

private:
  void enter(Phase next, uint32_t nowMs) {
    phase_ = next;
    phaseEnteredMs_ = nowMs;
  }

  bool timedOut(uint32_t nowMs) const {
    return nowMs - sequenceStartedMs_ > SEQUENCE_TIMEOUT_MS;
  }

  Phase phase_ = Phase::Idle;
  uint32_t phaseEnteredMs_ = 0;
  uint32_t sequenceStartedMs_ = 0;
  bool armed_ = false;
};

}  // namespace arming
```

- [ ] **Step 4: Testi çalıştır, geçtiğini gör**

```bash
./tools/run_native_tests.sh
```

Beklenen: `test_protocol: OK` ve `test_arming: OK`

- [ ] **Step 5: Commit**

```bash
git add include/arming.h test/native/test_arming.cpp
git commit -m "feat(arming): ortak jest state machine ve testleri"
```

---

### Task 3: Kalibrasyon kayıt yapısı ve sağlaması

**Files:**
- Create: `include/calibration.h`
- Create: `test/native/test_calibration.cpp`

**Interfaces:**
- Consumes: yok
- Produces: `calibration::Record` (packed, 20 bayt: `uint32_t magic; uint16_t version; int16_t accelOffsetX, accelOffsetY, gyroBiasX, gyroBiasY, gyroBiasZ; uint16_t reserved; uint16_t checksum;`), `calibration::MAGIC`, `calibration::VERSION`, `uint16_t calibration::computeChecksum(const Record&)`, `bool calibration::isValid(const Record&)`, `void calibration::finalize(Record&)`

- [ ] **Step 1: Testi yaz**

`test/native/test_calibration.cpp`:

```cpp
#include <cassert>
#include <cstdio>
#include <cstring>
#include "calibration.h"

int main()
{
    assert(sizeof(calibration::Record) == 20);
    // Flash word word yazildigi icin boyut 4'un kati olmali.
    assert(sizeof(calibration::Record) % 4 == 0);

    calibration::Record r{};
    r.magic = calibration::MAGIC;
    r.version = calibration::VERSION;
    r.accelOffsetX = -12;
    r.accelOffsetY = 34;
    r.gyroBiasX = 5;
    r.gyroBiasY = -6;
    r.gyroBiasZ = 7;
    calibration::finalize(r);

    assert(calibration::isValid(r));

    // Tek alan bozulursa gecersiz olmali.
    calibration::Record bad = r;
    bad.accelOffsetX = 0;
    assert(!calibration::isValid(bad));

    // Yanlis magic gecersiz.
    calibration::Record wrongMagic = r;
    wrongMagic.magic = 0xDEADBEEF;
    assert(!calibration::isValid(wrongMagic));

    // Yanlis surum gecersiz.
    calibration::Record wrongVersion = r;
    wrongVersion.version = calibration::VERSION + 1;
    calibration::finalize(wrongVersion);
    assert(!calibration::isValid(wrongVersion));

    // Silinmis flash (hepsi 0xFF) gecersiz.
    calibration::Record erased;
    memset(&erased, 0xFF, sizeof(erased));
    assert(!calibration::isValid(erased));

    printf("test_calibration: OK\n");
    return 0;
}
```

- [ ] **Step 2: Testi çalıştır, başarısız olduğunu gör**

```bash
./tools/run_native_tests.sh
```

Beklenen: `calibration.h: No such file or directory`

- [ ] **Step 3: `include/calibration.h` yaz**

```cpp
#pragma once

#include <stdint.h>

// STM32 flash'inda saklanan IMU kalibrasyon kaydi. Donanimdan bagimsiz
// tutuluyor ki sagalama mantigi ana makinede testlenebilsin.
namespace calibration {

constexpr uint32_t MAGIC = 0x314C4143;  // 'CAL1'
constexpr uint16_t VERSION = 1;

struct __attribute__((packed)) Record {
  uint32_t magic;
  uint16_t version;
  int16_t accelOffsetX;
  int16_t accelOffsetY;
  int16_t gyroBiasX;
  int16_t gyroBiasY;
  int16_t gyroBiasZ;
  uint16_t reserved;  // 20 bayta tamamlar: HAL_FLASH_Program word yaziyor.
  uint16_t checksum;
};

// checksum alani haric tum baytlarin toplami.
inline uint16_t computeChecksum(const Record &record) {
  const uint8_t *bytes = (const uint8_t *)&record;
  const uint32_t counted = sizeof(Record) - sizeof(record.checksum);
  uint16_t sum = 0;
  for (uint32_t i = 0; i < counted; i++) {
    sum = (uint16_t)(sum + bytes[i]);
  }
  return sum;
}

inline void finalize(Record &record) {
  record.checksum = computeChecksum(record);
}

inline bool isValid(const Record &record) {
  return record.magic == MAGIC && record.version == VERSION &&
         record.checksum == computeChecksum(record);
}

}  // namespace calibration
```

- [ ] **Step 4: Testi çalıştır, geçtiğini gör**

```bash
./tools/run_native_tests.sh
```

Beklenen: üç test de `OK`.

- [ ] **Step 5: Commit**

```bash
git add include/calibration.h test/native/test_calibration.cpp
git commit -m "feat(calibration): flash kayit yapisi ve sagalama"
```

---

### Task 4: STM32 — arming kilidi

**Files:**
- Modify: `src/stm32/main.cpp`

**Interfaces:**
- Consumes: `arming::GestureDetector` (Task 2), `radio::STATUS_ARMED` (Task 1)
- Produces: `bool isArmed()` (dosya içi), `armDetector` global, `DISARM_ON_LINK_LOSS_MS` sabiti

- [ ] **Step 1: Başlık ve global'leri ekle**

`src/stm32/main.cpp` başındaki include bloğuna, `#include "radio_protocol.h"` satırından hemen sonra:

```cpp
#include "arming.h"
```

`RX_TIMEOUT_MS` tanımının hemen altına:

```cpp
// Link uzun sure giderse disarm et. 300 ms'lik failsafe gazi zaten minimuma
// cekiyor; bu esik ancak baglanti gercekten koptuysa devreye girer.
const unsigned long DISARM_ON_LINK_LOSS_MS = 5000;
arming::GestureDetector armDetector;
```

- [ ] **Step 2: ESC çıkışını arming'e bağla**

`applyOutputs` içinde, `myESC.writeMicroseconds(escUs);` satırını (şu an 163) şununla değiştir:

```cpp
    // Disarm durumunda gaz cubugu nerede olursa olsun ESC minimumda kalir.
    // Bu ayni zamanda ESC'nin kendi arming'ini duzgun yapmasini saglar.
    myESC.writeMicroseconds(armDetector.isArmed() ? escUs : MIN_THROTTLE);
```

- [ ] **Step 3: Jesti kontrol paketinden besle**

`loop()` içinde, kontrol paketi alındığında çalışan bloğu (şu an 575-580 civarı) şununla değiştir:

```cpp
        if (parseIncomingByte((uint8_t)Serial1.read()))
        {
            lastPacketTime = millis();
            // Jest, STM32'nin kendi filtresinden ONCE, ham paket degerleriyle
            // cozuluyor; cift filtrelemenin gecikmesine takilmasin.
            armDetector.update(receivedPacket.LY, receivedPacket.RY, millis());
            applyOutputs(receivedPacket);
        }
```

- [ ] **Step 4: Uzun link kaybında disarm et**

`loop()` sonundaki failsafe bloğunu şununla değiştir:

```cpp
    if (millis() - lastPacketTime > RX_TIMEOUT_MS)
    {
        applyFailsafe();
    }

    if (millis() - lastPacketTime > DISARM_ON_LINK_LOSS_MS)
    {
        armDetector.disarm(millis());
    }
```

- [ ] **Step 5: Boot'ta detector'ü sıfırla**

`setup()` sonundaki `lastPacketTime = millis();` satırının hemen üstüne:

```cpp
    armDetector.reset(millis());
```

- [ ] **Step 6: Derle**

```bash
pio run -e stm32
```

Beklenen: `SUCCESS`

- [ ] **Step 7: Tezgahta doğrula — PERVANE SÖKÜLÜ OLMALI**

1. Gaz çubuğunu yukarı al, sonra STM32'ye güç ver. Motor **dönmemeli**.
2. Gaz çubuğunu oynat. Motor hâlâ dönmemeli.
3. Jesti yap: iki çubuk aşağı → bırak → iki çubuk aşağı → yarım saniye tut.
4. Gazı aç. Motor artık dönmeli.
5. Kumandayı kapat, 5 saniye bekle, aç. Motor dönmemeli (disarm olmuş).

Adım 3'te jest tutmazsa RY'nin yönü ters olabilir. Bu Task 6'daki `$S` satırıyla kesinleşecek; şimdilik `armDetector.update(receivedPacket.LY, 4095 - receivedPacket.RY, millis())` deneyip hangisinin çalıştığını **not al**, kalıcı düzeltmeyi Task 6'dan sonra yap.

- [ ] **Step 8: Commit**

```bash
git add src/stm32/main.cpp
git commit -m "feat(stm32): arming kilidi, motor jest yapilmadan calismiyor"
```

---

### Task 5: STM32 — komut ayrıştırma, kalibrasyon ve flash

**Files:**
- Modify: `src/stm32/main.cpp`

**Interfaces:**
- Consumes: `radio::CommandPacket`, `radio::COMMAND_*`, `radio::STATUS_*` (Task 1); `arming::GestureDetector` (Task 4); `calibration::Record` ve yardımcıları (Task 3)
- Produces: `applyCalibration()`, `startCalibration()`, `serviceCalibration()`, `loadCalibrationFromFlash()`, `saveCalibrationToFlash()`, `buildStatusFlags()`

- [ ] **Step 1: Başlık, global'ler ve flash sabitleri ekle**

`#include "arming.h"` satırının altına:

```cpp
#include "calibration.h"
```

`armDetector` tanımının altına:

```cpp
// Kalibrasyon kaydi flash sektor 7'de (0x08060000, 128 KB). Firmware 41 KB
// ve sektor 0-2'de duruyor; sektor 7 firmware buyuse bile cakismaz.
#define CALIBRATION_FLASH_ADDRESS 0x08060000UL
#define CALIBRATION_FLASH_SECTOR FLASH_SECTOR_7

int16_t accelOffsetX = 0;
int16_t accelOffsetY = 0;
int16_t gyroBiasX = 0;
int16_t gyroBiasY = 0;
int16_t gyroBiasZ = 0;
bool calibrationLoaded = false;

// Kalibrasyon orneklemesi loop()'u bloklamaz: her turda suresi gelen bir
// ornek alinir. Normal IMU araligi 50 ms, burada 5 ms kullaniliyor.
const unsigned long CAL_SAMPLE_INTERVAL_MS = 5;
const uint8_t CAL_SAMPLE_TARGET = 16;
bool calSampling = false;
uint8_t calSampleCount = 0;
int32_t calAccumAx = 0, calAccumAy = 0;
int32_t calAccumGx = 0, calAccumGy = 0, calAccumGz = 0;
unsigned long lastCalSampleMs = 0;

uint8_t pendingCommand = 0;
```

- [ ] **Step 2: Flash okuma/yazma ve kalibrasyon fonksiyonlarını ekle**

`void sendFrame(...)` bildiriminin (şu an 87 civarı) hemen altına:

```cpp
void loadCalibrationFromFlash()
{
    calibration::Record record;
    memcpy(&record, (const void *)CALIBRATION_FLASH_ADDRESS, sizeof(record));

    if (!calibration::isValid(record))
    {
        calibrationLoaded = false;
        return;
    }

    accelOffsetX = record.accelOffsetX;
    accelOffsetY = record.accelOffsetY;
    gyroBiasX = record.gyroBiasX;
    gyroBiasY = record.gyroBiasY;
    gyroBiasZ = record.gyroBiasZ;
    calibrationLoaded = true;
}

// DIKKAT: sektor silme ~1-2 saniye surer ve bu sirada flash veriyolu
// durdugu icin kod calismaz. Cagiran taraf once gazi minimuma cekmeli.
bool saveCalibrationToFlash()
{
    calibration::Record record{};
    record.magic = calibration::MAGIC;
    record.version = calibration::VERSION;
    record.accelOffsetX = accelOffsetX;
    record.accelOffsetY = accelOffsetY;
    record.gyroBiasX = gyroBiasX;
    record.gyroBiasY = gyroBiasY;
    record.gyroBiasZ = gyroBiasZ;
    calibration::finalize(record);

    HAL_FLASH_Unlock();

    FLASH_EraseInitTypeDef erase = {};
    erase.TypeErase = FLASH_TYPEERASE_SECTORS;
    erase.Sector = CALIBRATION_FLASH_SECTOR;
    erase.NbSectors = 1;
    erase.VoltageRange = FLASH_VOLTAGE_RANGE_3;

    uint32_t sectorError = 0;
    if (HAL_FLASHEx_Erase(&erase, &sectorError) != HAL_OK)
    {
        HAL_FLASH_Lock();
        return false;
    }

    const uint32_t wordCount = sizeof(calibration::Record) / 4;
    const uint32_t *words = (const uint32_t *)&record;
    for (uint32_t i = 0; i < wordCount; i++)
    {
        if (HAL_FLASH_Program(FLASH_TYPEPROGRAM_WORD,
                              CALIBRATION_FLASH_ADDRESS + i * 4,
                              words[i]) != HAL_OK)
        {
            HAL_FLASH_Lock();
            return false;
        }
    }

    HAL_FLASH_Lock();
    return true;
}

void startCalibration()
{
    calSampling = true;
    calSampleCount = 0;
    calAccumAx = 0;
    calAccumAy = 0;
    calAccumGx = 0;
    calAccumGy = 0;
    calAccumGz = 0;
    lastCalSampleMs = 0;
}

void clearCalibration()
{
    accelOffsetX = 0;
    accelOffsetY = 0;
    gyroBiasX = 0;
    gyroBiasY = 0;
    gyroBiasZ = 0;
    calibrationLoaded = false;
    applyFailsafe();
    saveCalibrationToFlash();  // magic bozulur, bir sonraki boot'ta yuklenmez
    lastPacketTime = millis();
}
```

Not: `clearCalibration()` sıfır ofsetli **geçerli** bir kayıt yazar; `calibrationLoaded` bir sonraki boot'ta `true` olur ama tüm ofsetler sıfırdır. Bu istenen davranış — "kalibrasyon yok" ile "kalibrasyon sıfır" pratikte aynı sonucu verir ve kayıt geçerli kalır. `STATUS_CALIBRATED` bitini sadece sıfırdan farklı ofset varsa set etmek için `buildStatusFlags` aşağıda buna göre yazılıyor.

- [ ] **Step 3: Örnekleme servisini ve bayrak üreticisini ekle**

`readGy85(...)` fonksiyonunun hemen altına (dosyada `readBmp280` `readGy85`'ten **önce** geliyor; `serviceCalibration` `readGy85`'i çağırdığı için ondan sonra gelmek zorunda):

```cpp
void serviceCalibration()
{
    if (!calSampling)
    {
        return;
    }

    if (millis() - lastCalSampleMs < CAL_SAMPLE_INTERVAL_MS)
    {
        return;
    }
    lastCalSampleMs = millis();

    int16_t ax = 0, ay = 0, az = 0, gx = 0, gy = 0, gz = 0, heading = 0;
    readGy85(ax, ay, az, gx, gy, gz, heading);

    calAccumAx += ax;
    calAccumAy += ay;
    calAccumGx += gx;
    calAccumGy += gy;
    calAccumGz += gz;
    calSampleCount++;

    if (calSampleCount < CAL_SAMPLE_TARGET)
    {
        return;
    }

    accelOffsetX = (int16_t)(calAccumAx / CAL_SAMPLE_TARGET);
    accelOffsetY = (int16_t)(calAccumAy / CAL_SAMPLE_TARGET);
    gyroBiasX = (int16_t)(calAccumGx / CAL_SAMPLE_TARGET);
    gyroBiasY = (int16_t)(calAccumGy / CAL_SAMPLE_TARGET);
    gyroBiasZ = (int16_t)(calAccumGz / CAL_SAMPLE_TARGET);
    calSampling = false;

    // Flash yazimi kodu ~1-2 saniye durdurur. Once gazi minimuma cek,
    // sonra donuste sahte failsafe tetiklenmesin diye saati tazele.
    applyFailsafe();
    calibrationLoaded = saveCalibrationToFlash();
    lastPacketTime = millis();
}

uint8_t buildStatusFlags()
{
    uint8_t flags = 0;
    if (adxlFound) flags |= radio::STATUS_ACCEL_OK;
    if (itgFound) flags |= radio::STATUS_GYRO_OK;
    if (qmcFound) flags |= radio::STATUS_MAG_OK;
    if (bmpFound) flags |= radio::STATUS_BARO_OK;
    if (calibrationLoaded &&
        (accelOffsetX != 0 || accelOffsetY != 0 ||
         gyroBiasX != 0 || gyroBiasY != 0 || gyroBiasZ != 0))
    {
        flags |= radio::STATUS_CALIBRATED;
    }
    if (armDetector.isArmed()) flags |= radio::STATUS_ARMED;
    return flags;
}
```

`applyFailsafe` dosyada `readGy85`'ten sonra tanımlı olduğu için dosya başına ileri bildirim ekle:

```cpp
void applyFailsafe();
```

- [ ] **Step 4: Komut paketini ayrıştır**

`parseIncomingByte` içindeki `case 5:` bloğunda, telemetri isteği kontrolünün hemen altına:

```cpp
        if (checksum == b && incomingPacketType == radio::PACKET_TYPE_COMMAND &&
            incomingPayloadLength == sizeof(radio::CommandPacket))
        {
            radio::CommandPacket cmd;
            memcpy(&cmd, payloadBuffer, sizeof(cmd));
            pendingCommand = cmd.command;
        }
```

- [ ] **Step 5: Komutları `loop()` içinde işle**

`loop()` başındaki `updateDs18Temperatures();` satırının hemen altına:

```cpp
    if (pendingCommand != 0)
    {
        const uint8_t command = pendingCommand;
        pendingCommand = 0;

        switch (command)
        {
        case radio::COMMAND_CALIBRATE_LEVEL:
            // Armed'ken reddedilir: flash yazimi kodu saniyelerce durdurur.
            if (!armDetector.isArmed())
            {
                startCalibration();
            }
            break;
        case radio::COMMAND_CLEAR_CALIBRATION:
            if (!armDetector.isArmed())
            {
                clearCalibration();
            }
            break;
        case radio::COMMAND_DISARM:
            armDetector.disarm(millis());
            break;
        default:
            break;
        }
    }

    serviceCalibration();
```

- [ ] **Step 6: Ofsetleri telemetriye uygula ve bayrakları doldur**

`loop()` içindeki telemetri doldurma bloğunda ilgili satırları değiştir:

```cpp
        telemetry.mpuAx = (int16_t)(imuAx - accelOffsetX);
        telemetry.mpuAy = (int16_t)(imuAy - accelOffsetY);
        telemetry.mpuAz = imuAz;
        telemetry.mpuGx = (int16_t)(imuGx - gyroBiasX);
        telemetry.mpuGy = (int16_t)(imuGy - gyroBiasY);
        telemetry.mpuGz = (int16_t)(imuGz - gyroBiasZ);
```

ve `telemetry.baroTempCentiC = baroTempCentiC;` satırının altına:

```cpp
        telemetry.statusFlags = buildStatusFlags();
```

- [ ] **Step 7: Boot'ta flash'tan yükle**

`setup()` içinde `initBmp280();` satırının hemen altına:

```cpp
    loadCalibrationFromFlash();
    Serial.print("[SETUP] Kalibrasyon: ");
    Serial.println(calibrationLoaded ? "yuklendi" : "yok");
```

- [ ] **Step 8: Derle**

```bash
pio run -e stm32
```

Beklenen: `SUCCESS`

- [ ] **Step 9: Commit**

```bash
git add src/stm32/main.cpp
git commit -m "feat(stm32): komut ayristirma, IMU kalibrasyonu ve flash kaliciligi"
```

---

### Task 6: ESP32 — USB köprüsü, OLED ve buzzer

**Files:**
- Modify: `src/esp32/main.cpp`

**Interfaces:**
- Consumes: `radio::CommandPacket`, `radio::COMMAND_*`, `radio::STATUS_*` (Task 1)
- Produces: USB seri protokolü — çıktı `$T,...` ve `$S,...`, girdi `CAL` / `CALCLR` / `DISARM`

- [ ] **Step 1: Global'leri ekle**

`lastLinkLostBeepTime` tanımının altına:

```cpp
char usbLineBuffer[32];
uint8_t usbLineLength = 0;
uint8_t pendingCommand = 0;
uint8_t commandSeq = 0;

const unsigned long STICK_REPORT_INTERVAL_MS = 200;  // 5 Hz
unsigned long lastStickReportTime = 0;

bool lastArmedState = false;
bool armedStateKnown = false;
```

- [ ] **Step 2: `$T` satırını yaz**

`parseIncomingLoRaByte` içinde, `relativeAltitudeM` hesabının hemen altına (telemetri kabul bloğunun sonuna, `return true;` öncesine):

```cpp
      Serial.print("$T,");
      Serial.print(millis());
      Serial.print(',');
      Serial.print(lastTelemetry.voltageMv);
      Serial.print(',');
      Serial.print(lastTelemetry.battTempCentiC);
      Serial.print(',');
      Serial.print(lastTelemetry.escTempCentiC);
      Serial.print(',');
      Serial.print(lastTelemetry.mpuAx);
      Serial.print(',');
      Serial.print(lastTelemetry.mpuAy);
      Serial.print(',');
      Serial.print(lastTelemetry.mpuAz);
      Serial.print(',');
      Serial.print(lastTelemetry.mpuGx);
      Serial.print(',');
      Serial.print(lastTelemetry.mpuGy);
      Serial.print(',');
      Serial.print(lastTelemetry.mpuGz);
      Serial.print(',');
      Serial.print(lastTelemetry.compassHeading);
      Serial.print(',');
      Serial.print(lastTelemetry.pressurePa);
      Serial.print(',');
      Serial.print(lastTelemetry.baroTempCentiC);
      Serial.print(',');
      Serial.print(lastTelemetry.statusFlags);
      Serial.print(',');
      Serial.println(telemetryRxCount);
```

- [ ] **Step 3: USB komut okuyucusunu ekle**

`normalizeInputs` fonksiyonunun hemen üstüne:

```cpp
void handleUsbCommand(const char *line)
{
  if (strcmp(line, "CAL") == 0)
  {
    pendingCommand = radio::COMMAND_CALIBRATE_LEVEL;
  }
  else if (strcmp(line, "CALCLR") == 0)
  {
    pendingCommand = radio::COMMAND_CLEAR_CALIBRATION;
  }
  else if (strcmp(line, "DISARM") == 0)
  {
    pendingCommand = radio::COMMAND_DISARM;
  }
}

void pollUsbCommands()
{
  while (Serial.available())
  {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r')
    {
      if (usbLineLength > 0)
      {
        usbLineBuffer[usbLineLength] = '\0';
        handleUsbCommand(usbLineBuffer);
        usbLineLength = 0;
      }
    }
    else if (usbLineLength < sizeof(usbLineBuffer) - 1)
    {
      usbLineBuffer[usbLineLength++] = c;
    }
    else
    {
      usbLineLength = 0;  // asiri uzun satir, at
    }
  }
}
```

Dosya başına `#include <string.h>` ekle.

- [ ] **Step 4: Arming geri bildirimini ekle**

`pollUsbCommands`'ın altına:

```cpp
void updateArmedFeedback()
{
  const bool armed = (lastTelemetry.statusFlags & radio::STATUS_ARMED) != 0;

  if (!armedStateKnown)
  {
    armedStateKnown = true;
    lastArmedState = armed;
    return;
  }

  if (armed == lastArmedState)
  {
    return;
  }
  lastArmedState = armed;

  if (armed)
  {
    tone(PIN_BUZZER, 784, 120);  // G5
    delay(140);
    tone(PIN_BUZZER, 1047, 200); // C6
  }
  else
  {
    tone(PIN_BUZZER, 330, 250);  // E4
  }
}
```

- [ ] **Step 5: OLED'e arming satırı ekle**

`updateStatusDisplay` içindeki `display.print("Link OK  #");` bloğunu şununla değiştir:

```cpp
    display.print((lastTelemetry.statusFlags & radio::STATUS_ARMED) ? "ARMED" : "DISARM");
    display.print("  #");
    display.println(telemetryRxCount);
```

- [ ] **Step 6: `loop()`'a bağla**

`loop()` içinde `updateStatusDisplay();` satırının hemen üstüne:

```cpp
  pollUsbCommands();
  updateArmedFeedback();

  if (millis() - lastStickReportTime >= STICK_REPORT_INTERVAL_MS)
  {
    lastStickReportTime = millis();
    Serial.print("$S,");
    Serial.print(controlPacket.LX);
    Serial.print(',');
    Serial.print(controlPacket.LY);
    Serial.print(',');
    Serial.print(controlPacket.RX);
    Serial.print(',');
    Serial.println(controlPacket.RY);
  }
```

- [ ] **Step 7: Komut paketini gönder**

`loop()` içinde, `if (digitalRead(LORA_AUX) == HIGH)` bloğunun **başına**, kontrol paketi kurulmadan önce:

```cpp
      if (pendingCommand != 0)
      {
        radio::CommandPacket cmd;
        cmd.sequence = commandSeq++;
        cmd.command = pendingCommand;
        pendingCommand = 0;
        sendFrame(radio::PACKET_TYPE_COMMAND, &cmd, sizeof(cmd));
        return;  // bu yuvada kontrol paketi gonderme, 20 ms sonra devam
      }
```

- [ ] **Step 8: Derle ve iki kartı da flash'la**

```bash
pio run
pio run -e esp32 -t upload
pio run -e stm32 -t upload
```

- [ ] **Step 9: Tezgahta doğrula**

Seri monitörü aç (`pio device monitor -e esp32`):

1. Boot satırında `TEL_STRUCT_SIZE=37` görülmeli. Görülmüyorsa iki kart farklı firmware'de.
2. `$T,...` satırları saniyede bir, `$S,...` satırları saniyede beş akmalı.
3. **RY yönünü belirle:** sağ çubuğu fiziksel olarak aşağı it, `$S` satırındaki dördüncü sayıya bak. 400'ün altına iniyorsa Task 4'teki kod doğru. 3600'ün üstüne çıkıyorsa STM32'de `armDetector.update(receivedPacket.LY, 4095 - receivedPacket.RY, millis());` olarak düzelt, yeniden flash'la, jesti tekrar dene.
4. Monitörden `CAL` yazıp enter'a bas. Bir-iki saniye sonra `$T` satırındaki `flags` alanında 16 biti (`STATUS_CALIBRATED`) set olmalı ve `mpuAx`/`mpuAy` sıfıra yakınsamalı.
5. Güç kes, aç. `[SETUP] Kalibrasyon: yuklendi` çıkmalı ve flags yine 16'yı içermeli.
6. Kalibrasyon sırasında servoların şiddetli seğirmediğini gözle doğrula. Seğiriyorsa flash yazımı sırasında kesmelerin durması sorun çıkarıyor demektir — o durumda dur ve rapor et.

- [ ] **Step 10: Commit**

```bash
git add src/esp32/main.cpp src/stm32/main.cpp
git commit -m "feat(esp32): USB telemetri/komut koprusu, arming gostergesi ve sesli bildirim"
```

---

### Task 7: Python — attitude modülü

**Files:**
- Create: `tools/navstation/__init__.py`
- Create: `tools/navstation/attitude.py`
- Create: `tools/navstation/tests/__init__.py`
- Create: `tools/navstation/tests/test_attitude.py`

**Interfaces:**
- Consumes: yok
- Produces: `ACCEL_LSB_PER_G`, `GYRO_LSB_PER_DPS`, `accel_to_g(raw: int) -> float`, `gyro_to_dps(raw: int) -> float`, `pitch_roll_deg(ax: int, ay: int, az: int) -> tuple[float, float]`, `heading_deg(raw_decideg: int) -> float`, `relative_altitude_m(pressure_pa: int, reference_pa: int) -> float`

- [ ] **Step 1: Testi yaz**

`tools/navstation/tests/test_attitude.py`:

```python
import math

import pytest

from navstation import attitude


def test_accel_scale_uses_64_lsb_per_g():
    assert attitude.accel_to_g(64) == pytest.approx(1.0)
    assert attitude.accel_to_g(-32) == pytest.approx(-0.5)


def test_gyro_scale_uses_itg3205_2000dps_range():
    assert attitude.gyro_to_dps(14.375) == pytest.approx(1.0)


def test_level_attitude_is_zero():
    pitch, roll = attitude.pitch_roll_deg(0, 0, 64)
    assert pitch == pytest.approx(0.0)
    assert roll == pytest.approx(0.0)


def test_roll_right_is_positive():
    # Saga yatinca y bileseni yercekimini gormeye baslar.
    pitch, roll = attitude.pitch_roll_deg(0, 64, 64)
    assert roll == pytest.approx(45.0)
    assert pitch == pytest.approx(0.0)


def test_pitch_up_is_positive():
    pitch, roll = attitude.pitch_roll_deg(-64, 0, 64)
    assert pitch == pytest.approx(45.0)
    assert roll == pytest.approx(0.0)


def test_all_zero_accel_does_not_raise():
    pitch, roll = attitude.pitch_roll_deg(0, 0, 0)
    assert math.isfinite(pitch)
    assert math.isfinite(roll)


def test_heading_converts_decidegrees():
    assert attitude.heading_deg(1234) == pytest.approx(123.4)


def test_heading_wraps_into_0_360():
    assert attitude.heading_deg(-100) == pytest.approx(350.0)
    assert attitude.heading_deg(3700) == pytest.approx(10.0)


def test_altitude_zero_at_reference():
    assert attitude.relative_altitude_m(101325, 101325) == pytest.approx(0.0)


def test_altitude_positive_when_pressure_drops():
    # ~12 Pa dusus deniz seviyesinde kabaca 1 metre.
    assert attitude.relative_altitude_m(101325 - 12, 101325) == pytest.approx(1.0, abs=0.2)


def test_altitude_returns_zero_for_invalid_input():
    assert attitude.relative_altitude_m(0, 101325) == 0.0
    assert attitude.relative_altitude_m(101325, 0) == 0.0
```

- [ ] **Step 2: Testi çalıştır, başarısız olduğunu gör**

```bash
.env/bin/python -m pytest tools/navstation/tests/test_attitude.py -v
```

Beklenen: `ModuleNotFoundError: No module named 'navstation'` veya pytest bulunamadı.

pytest yoksa kur:

```bash
.env/bin/pip install pytest
```

- [ ] **Step 3: Modülü yaz**

`tools/navstation/__init__.py` — boş dosya.

`tools/navstation/tests/__init__.py` — boş dosya.

`tools/navstation/attitude.py`:

```python
"""Telemetri ham degerlerini fiziksel birimlere ceviren saf fonksiyonlar.

Bu modul hicbir G/C yapmaz ve hicbir GUI kutuphanesi import etmez.
"""

import math

# ADXL345 varsayilan DATA_FORMAT: +-2 g, 10 bit, 256 LSB/g.
# Ucus firmware'i ham degeri 4'e boluyor, geriye 64 LSB/g kaliyor.
ACCEL_LSB_PER_G = 64.0

# ITG3205 FS_SEL=3: +-2000 derece/saniye.
GYRO_LSB_PER_DPS = 14.375

# Barometrik irtifa formulu (ISA).
_ALTITUDE_COEFFICIENT = 44330.0
_ALTITUDE_EXPONENT = 0.1902949


def accel_to_g(raw: float) -> float:
    return raw / ACCEL_LSB_PER_G


def gyro_to_dps(raw: float) -> float:
    return raw / GYRO_LSB_PER_DPS


def pitch_roll_deg(ax: int, ay: int, az: int) -> tuple[float, float]:
    """Ivmeolcer vektorunden pitch ve roll, derece cinsinden.

    Olcek sadelestigi icin LSB katsayisi sonucu etkilemez.
    Uc eksen de sifirsa (sensor yok) 0, 0 doner; istisna atilmaz.
    """
    roll = math.degrees(math.atan2(ay, az))
    pitch = math.degrees(math.atan2(-ax, math.hypot(ay, az)))
    return pitch, roll


def heading_deg(raw_decideg: int) -> float:
    """Firmware pusula acisini deci-derece olarak yolluyor."""
    return (raw_decideg / 10.0) % 360.0


def relative_altitude_m(pressure_pa: int, reference_pa: int) -> float:
    """Referans basinca gore irtifa. Gecersiz girdide 0.0."""
    if pressure_pa <= 0 or reference_pa <= 0:
        return 0.0
    ratio = pressure_pa / reference_pa
    return _ALTITUDE_COEFFICIENT * (1.0 - ratio**_ALTITUDE_EXPONENT)
```

- [ ] **Step 4: Testi çalıştır, geçtiğini gör**

```bash
cd tools && ../.env/bin/python -m pytest navstation/tests/test_attitude.py -v
```

Beklenen: 11 test PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/navstation/__init__.py tools/navstation/attitude.py \
        tools/navstation/tests/__init__.py tools/navstation/tests/test_attitude.py
git commit -m "feat(navstation): ivme/jiro/basinc donusumleri ve testleri"
```

---

### Task 8: Python — seri link modülü

**Files:**
- Create: `tools/navstation/link.py`
- Create: `tools/navstation/tests/test_link.py`

**Interfaces:**
- Consumes: yok
- Produces: `Telemetry` dataclass (`t_ms, voltage_mv, batt_temp_centi, esc_temp_centi, ax, ay, az, gx, gy, gz, heading_decideg, pressure_pa, baro_temp_centi, flags, rx_count`), `Sticks` dataclass (`lx, ly, rx, ry`), `parse_line(line: str) -> Telemetry | Sticks | None`, `TEMP_ABSENT`, `FLAG_ACCEL/GYRO/MAG/BARO/CALIBRATED/ARMED`, `SerialLink` (`open()`, `close()`, `latest_telemetry()`, `latest_sticks()`, `send_command(name: str)`, `is_open`, `last_error`)

- [ ] **Step 1: Testi yaz**

`tools/navstation/tests/test_link.py`:

```python
from navstation import link


VALID_T = "$T,12345,11850,2431,3012,1,-2,64,3,-4,5,1234,101325,2380,17,42"
VALID_S = "$S,2048,120,2050,3900"


def test_parses_telemetry_line():
    result = link.parse_line(VALID_T)
    assert isinstance(result, link.Telemetry)
    assert result.t_ms == 12345
    assert result.voltage_mv == 11850
    assert result.batt_temp_centi == 2431
    assert result.esc_temp_centi == 3012
    assert (result.ax, result.ay, result.az) == (1, -2, 64)
    assert (result.gx, result.gy, result.gz) == (3, -4, 5)
    assert result.heading_decideg == 1234
    assert result.pressure_pa == 101325
    assert result.baro_temp_centi == 2380
    assert result.flags == 17
    assert result.rx_count == 42


def test_parses_stick_line():
    result = link.parse_line(VALID_S)
    assert isinstance(result, link.Sticks)
    assert (result.lx, result.ly, result.rx, result.ry) == (2048, 120, 2050, 3900)


def test_tolerates_trailing_whitespace_and_crlf():
    assert isinstance(link.parse_line(VALID_T + "\r\n"), link.Telemetry)


def test_ignores_human_readable_lines():
    assert link.parse_line("[TEL] V=11.85 Tbatt=NA") is None
    assert link.parse_line("[E22] ayar zaten uygun") is None
    assert link.parse_line("") is None


def test_ignores_unknown_record_type():
    assert link.parse_line("$X,1,2,3") is None


def test_returns_none_on_wrong_field_count():
    assert link.parse_line("$T,1,2,3") is None
    assert link.parse_line(VALID_T + ",99") is None


def test_returns_none_on_non_numeric_field():
    broken = VALID_T.replace("11850", "abc")
    assert link.parse_line(broken) is None


def test_never_raises_on_garbage():
    for garbage in ["$T,", "$", "$S,,,,", "$T," + "," * 100, "\x00\xff"]:
        assert link.parse_line(garbage) is None


def test_flag_helpers_match_firmware_bits():
    assert link.FLAG_ACCEL == 0x01
    assert link.FLAG_GYRO == 0x02
    assert link.FLAG_MAG == 0x04
    assert link.FLAG_BARO == 0x08
    assert link.FLAG_CALIBRATED == 0x10
    assert link.FLAG_ARMED == 0x20


def test_temp_absent_sentinel_matches_int16_min():
    assert link.TEMP_ABSENT == -32768
```

- [ ] **Step 2: Testi çalıştır, başarısız olduğunu gör**

```bash
cd tools && ../.env/bin/python -m pytest navstation/tests/test_link.py -v
```

Beklenen: `ImportError: cannot import name 'link'`

- [ ] **Step 3: Modülü yaz**

`tools/navstation/link.py`:

```python
"""ESP32 kumandaya USB seri baglanti: satir ayristirma ve komut gonderme.

Bu modul GUI bilmez. Ayristirici hicbir kosulda istisna atmaz; bozuk satir
None doner ve cagiran taraf sayar.
"""

import threading
from dataclasses import dataclass

import serial

# Firmware INT16_MIN yolluyor: sensor yok demek, 0 derece degil.
TEMP_ABSENT = -32768

FLAG_ACCEL = 0x01
FLAG_GYRO = 0x02
FLAG_MAG = 0x04
FLAG_BARO = 0x08
FLAG_CALIBRATED = 0x10
FLAG_ARMED = 0x20

_COMMANDS = {"CAL", "CALCLR", "DISARM"}


@dataclass(frozen=True)
class Telemetry:
    t_ms: int
    voltage_mv: int
    batt_temp_centi: int
    esc_temp_centi: int
    ax: int
    ay: int
    az: int
    gx: int
    gy: int
    gz: int
    heading_decideg: int
    pressure_pa: int
    baro_temp_centi: int
    flags: int
    rx_count: int


@dataclass(frozen=True)
class Sticks:
    lx: int
    ly: int
    rx: int
    ry: int


def parse_line(line: str) -> Telemetry | Sticks | None:
    """Tek satiri ayristirir. Taninmayan veya bozuk satirda None doner."""
    try:
        text = line.strip()
    except (AttributeError, UnicodeDecodeError):
        return None

    if not text.startswith("$"):
        return None

    parts = text.split(",")
    tag = parts[0]

    if tag == "$T":
        fields = parts[1:]
        if len(fields) != 15:
            return None
        values = _to_ints(fields)
        return None if values is None else Telemetry(*values)

    if tag == "$S":
        fields = parts[1:]
        if len(fields) != 4:
            return None
        values = _to_ints(fields)
        return None if values is None else Sticks(*values)

    return None


def _to_ints(fields: list[str]) -> list[int] | None:
    try:
        return [int(f) for f in fields]
    except ValueError:
        return None


class SerialLink:
    """Arka planda seri portu okuyan thread ve son-deger tutucu."""

    def __init__(self, port: str, baud: int = 115200):
        self.port = port
        self.baud = baud
        self.last_error: str | None = None
        self.bad_line_count = 0

        self._serial: serial.Serial | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._telemetry: Telemetry | None = None
        self._sticks: Sticks | None = None

    @property
    def is_open(self) -> bool:
        return self._serial is not None and self._serial.is_open

    def open(self) -> bool:
        self.last_error = None
        try:
            self._serial = serial.Serial(self.port, self.baud, timeout=0.2)
        except (serial.SerialException, OSError) as exc:
            self.last_error = str(exc)
            self._serial = None
            return False

        self._stop.clear()
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        return True

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        if self._serial is not None:
            try:
                self._serial.close()
            except (serial.SerialException, OSError):
                pass
            self._serial = None

    def latest_telemetry(self) -> Telemetry | None:
        with self._lock:
            return self._telemetry

    def latest_sticks(self) -> Sticks | None:
        with self._lock:
            return self._sticks

    def send_command(self, name: str) -> bool:
        if name not in _COMMANDS or not self.is_open:
            return False
        try:
            self._serial.write((name + "\n").encode("ascii"))
            return True
        except (serial.SerialException, OSError) as exc:
            self.last_error = str(exc)
            return False

    def _read_loop(self) -> None:
        while not self._stop.is_set():
            try:
                raw = self._serial.readline()
            except (serial.SerialException, OSError) as exc:
                self.last_error = str(exc)
                return

            if not raw:
                continue

            record = parse_line(raw.decode("ascii", errors="replace"))
            if record is None:
                if raw.startswith(b"$"):
                    self.bad_line_count += 1
                continue

            with self._lock:
                if isinstance(record, Telemetry):
                    self._telemetry = record
                else:
                    self._sticks = record
```

- [ ] **Step 4: Testi çalıştır, geçtiğini gör**

```bash
cd tools && ../.env/bin/python -m pytest navstation/tests/ -v
```

Beklenen: tüm testler PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/navstation/link.py tools/navstation/tests/test_link.py
git commit -m "feat(navstation): seri link, satir ayristirici ve testleri"
```

---

### Task 9: Python — arayüz ve giriş noktası

**Files:**
- Create: `tools/navstation/ui.py`
- Create: `tools/navstation/__main__.py`
- Create: `tools/navstation/README.md`

**Interfaces:**
- Consumes: `attitude` (Task 7), `link` (Task 8)
- Produces: `NavStationWindow(link: SerialLink)` — `run()`

- [ ] **Step 1: tkinter'ı kur ve doğrula**

```bash
brew install python-tk@3.14
.env/bin/python -c "import tkinter; print('tkinter OK')"
```

Beklenen: `tkinter OK`

- [ ] **Step 2: `tools/navstation/ui.py` yaz**

```python
"""Yer istasyonu penceresi: yapay ufuk, sayisal paneller, komut butonlari."""

import math
import time
import tkinter as tk
from tkinter import messagebox

from . import attitude, link

REFRESH_MS = 100
LINK_STALE_MS = 3000
CALIBRATION_TIMEOUT_MS = 5000

HORIZON_SIZE = 320
HORIZON_RADIUS = 140
PIXELS_PER_DEGREE = 3.0

BG = "#101418"
FG = "#e6edf3"
DIM = "#6b7885"
SKY = "#2f7fd1"
GROUND = "#8a5a2b"
PLANE = "#ffd24a"


class NavStationWindow:
    def __init__(self, serial_link: link.SerialLink):
        self.link = serial_link
        self.reference_pa: int | None = None
        self.calibration_deadline_ms: int | None = None
        self.calibration_baseline_flags: int = 0
        self.pending_calibration: str | None = None
        self.last_rx_count: int | None = None
        self.last_packet_wall_time: float | None = None

        self.root = tk.Tk()
        self.root.title("ISO U1 — Yer Istasyonu")
        self.root.configure(bg=BG)

        self._build_layout()

    # -- kurulum ----------------------------------------------------------

    def _build_layout(self) -> None:
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=12, pady=12)

        self.left = self._make_panel(body, "UCUS")
        self.left.pack(side="left", fill="y", padx=(0, 12))

        self.canvas = tk.Canvas(
            body, width=HORIZON_SIZE, height=HORIZON_SIZE,
            bg=BG, highlightthickness=0,
        )
        self.canvas.pack(side="left")

        self.right = self._make_panel(body, "DURUM")
        self.right.pack(side="left", fill="y", padx=(12, 0))

        self.left_values = self._make_rows(
            self.left,
            ["Batarya", "Batarya sic.", "ESC sic.", "Baro sic.", "Basinc", "Irtifa"],
        )
        self.right_values = self._make_rows(
            self.right,
            ["Pitch", "Roll", "Heading", "Jiro p/q/r", "Ivme x/y/z",
             "Sensorler", "Kalibrasyon", "Arming", "Paket", "Yas"],
        )

        self._build_bottom_bar()

    def _make_panel(self, parent: tk.Widget, title: str) -> tk.Frame:
        frame = tk.Frame(parent, bg=BG)
        tk.Label(frame, text=title, bg=BG, fg=DIM,
                 font=("TkDefaultFont", 10, "bold")).pack(anchor="w", pady=(0, 6))
        return frame

    def _make_rows(self, parent: tk.Frame, labels: list[str]) -> dict[str, tk.Label]:
        values: dict[str, tk.Label] = {}
        for name in labels:
            row = tk.Frame(parent, bg=BG)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=name, bg=BG, fg=DIM, width=12,
                     anchor="w").pack(side="left")
            value = tk.Label(row, text="--", bg=BG, fg=FG, width=14,
                             anchor="e", font=("TkFixedFont", 11))
            value.pack(side="right")
            values[name] = value
        return values

    def _build_bottom_bar(self) -> None:
        bar = tk.Frame(self.root, bg=BG)
        bar.pack(fill="x", padx=12, pady=(0, 12))

        self.calibrate_button = tk.Button(
            bar, text="KALIBRE ET", command=self._on_calibrate, state="disabled")
        self.calibrate_button.pack(side="left")

        self.clear_button = tk.Button(
            bar, text="KALIBRASYONU SIL", command=self._on_clear_calibration,
            state="disabled")
        self.clear_button.pack(side="left", padx=6)

        self.disarm_button = tk.Button(
            bar, text="DISARM", command=self._on_disarm, state="disabled")
        self.disarm_button.pack(side="left")

        self.status = tk.Label(bar, text="Baglaniyor...", bg=BG, fg=DIM, anchor="w")
        self.status.pack(side="left", fill="x", expand=True, padx=12)

    # -- komutlar ---------------------------------------------------------

    def _on_calibrate(self) -> None:
        confirmed = messagebox.askokcancel(
            "Kalibrasyon",
            "Ucak duz zeminde, hareketsiz ve motor kapali mi?\n\n"
            "Kalibrasyon sirasinda STM32 flash'a yazar ve 1-2 saniye\n"
            "kontrol paketi islemez.",
        )
        if not confirmed:
            return

        telemetry = self.link.latest_telemetry()
        self.calibration_baseline_flags = telemetry.flags if telemetry else 0

        if self.link.send_command("CAL"):
            self.pending_calibration = "CAL"
            self.calibration_deadline_ms = CALIBRATION_TIMEOUT_MS
            self.status.configure(text="Kalibre ediliyor...")
        else:
            self.status.configure(text=f"Komut gonderilemedi: {self.link.last_error}")

    def _on_clear_calibration(self) -> None:
        if not messagebox.askokcancel("Kalibrasyon", "Kalibrasyon silinsin mi?"):
            return
        if self.link.send_command("CALCLR"):
            self.pending_calibration = "CALCLR"
            self.calibration_deadline_ms = CALIBRATION_TIMEOUT_MS
            self.status.configure(text="Kalibrasyon siliniyor...")

    def _on_disarm(self) -> None:
        if self.link.send_command("DISARM"):
            self.status.configure(text="DISARM gonderildi")

    # -- dongu ------------------------------------------------------------

    def run(self) -> None:
        self._tick()
        self.root.mainloop()

    def _tick(self) -> None:
        telemetry = self.link.latest_telemetry()

        if telemetry is not None and telemetry.rx_count != self.last_rx_count:
            self.last_rx_count = telemetry.rx_count
            self.last_packet_wall_time = time.monotonic()

        age_s = (time.monotonic() - self.last_packet_wall_time
                 if self.last_packet_wall_time is not None else None)
        stale = age_s is None or age_s * 1000 > LINK_STALE_MS

        if telemetry is not None:
            self._update_panels(telemetry, age_s)
            self._draw_horizon(*attitude.pitch_roll_deg(
                telemetry.ax, telemetry.ay, telemetry.az))
            self._update_buttons(telemetry, stale)
            self._check_calibration(telemetry)
        else:
            self._draw_horizon(0.0, 0.0)
            self._set_buttons_enabled(False)

        # Bayat linkte paneller soluklasir, degerler ekranda kalir.
        colour = DIM if stale else FG
        for label in (*self.left_values.values(), *self.right_values.values()):
            label.configure(fg=colour)

        if stale:
            self.status.configure(text="LINK YOK")

        self.root.after(REFRESH_MS, self._tick)

    def _check_calibration(self, telemetry: link.Telemetry) -> None:
        if self.calibration_deadline_ms is None:
            return

        now_calibrated = bool(telemetry.flags & link.FLAG_CALIBRATED)
        # CAL bekliyorsak bit4'un yukselmesini, CALCLR bekliyorsak dusmesini ariyoruz.
        expected = self.pending_calibration == "CAL"

        if now_calibrated == expected:
            self.calibration_deadline_ms = None
            self.pending_calibration = None
            self.status.configure(
                text="Kalibrasyon tamam" if expected else "Kalibrasyon silindi")
            return

        self.calibration_deadline_ms -= REFRESH_MS
        if self.calibration_deadline_ms <= 0:
            self.calibration_deadline_ms = None
            self.pending_calibration = None
            self.status.configure(text="Onay gelmedi, tekrar dene")

    # -- cizim ------------------------------------------------------------

    def _update_panels(self, t: link.Telemetry, age_s: float | None) -> None:
        if self.reference_pa is None and t.pressure_pa > 0:
            self.reference_pa = t.pressure_pa

        self.left_values["Batarya"].configure(text=f"{t.voltage_mv / 1000:.2f} V")
        self.left_values["Batarya sic."].configure(text=_temp(t.batt_temp_centi))
        self.left_values["ESC sic."].configure(text=_temp(t.esc_temp_centi))

        has_baro = bool(t.flags & link.FLAG_BARO)
        self.left_values["Baro sic."].configure(
            text=_temp(t.baro_temp_centi) if has_baro else "--")
        self.left_values["Basinc"].configure(
            text=f"{t.pressure_pa} Pa" if has_baro else "--")
        altitude = attitude.relative_altitude_m(t.pressure_pa, self.reference_pa or 0)
        self.left_values["Irtifa"].configure(
            text=f"{altitude:+.1f} m" if has_baro else "--")

        pitch, roll = attitude.pitch_roll_deg(t.ax, t.ay, t.az)
        has_accel = bool(t.flags & link.FLAG_ACCEL)
        self.right_values["Pitch"].configure(text=f"{pitch:+.1f}" if has_accel else "--")
        self.right_values["Roll"].configure(text=f"{roll:+.1f}" if has_accel else "--")
        self.right_values["Ivme x/y/z"].configure(
            text=(f"{attitude.accel_to_g(t.ax):+.2f} "
                  f"{attitude.accel_to_g(t.ay):+.2f} "
                  f"{attitude.accel_to_g(t.az):+.2f}") if has_accel else "--")

        has_mag = bool(t.flags & link.FLAG_MAG)
        self.right_values["Heading"].configure(
            text=f"{attitude.heading_deg(t.heading_decideg):.1f}" if has_mag else "--")

        has_gyro = bool(t.flags & link.FLAG_GYRO)
        self.right_values["Jiro p/q/r"].configure(
            text=(f"{attitude.gyro_to_dps(t.gx):+.0f} "
                  f"{attitude.gyro_to_dps(t.gy):+.0f} "
                  f"{attitude.gyro_to_dps(t.gz):+.0f}") if has_gyro else "--")

        present = "".join([
            "A" if has_accel else "-",
            "G" if has_gyro else "-",
            "M" if has_mag else "-",
            "B" if has_baro else "-",
        ])
        self.right_values["Sensorler"].configure(text=present)
        self.right_values["Kalibrasyon"].configure(
            text="VAR" if t.flags & link.FLAG_CALIBRATED else "YOK")
        self.right_values["Arming"].configure(
            text="ARMED" if t.flags & link.FLAG_ARMED else "DISARMED")
        self.right_values["Paket"].configure(text=str(t.rx_count))
        self.right_values["Yas"].configure(
            text=f"{age_s:.1f} s" if age_s is not None else "--")

    def _update_buttons(self, t: link.Telemetry, stale: bool) -> None:
        armed = bool(t.flags & link.FLAG_ARMED)
        busy = self.calibration_deadline_ms is not None
        can_calibrate = self.link.is_open and not armed and not busy and not stale

        self.calibrate_button.configure(state="normal" if can_calibrate else "disabled")
        self.clear_button.configure(state="normal" if can_calibrate else "disabled")
        self.disarm_button.configure(state="normal" if self.link.is_open else "disabled")

    def _set_buttons_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.calibrate_button.configure(state=state)
        self.clear_button.configure(state=state)
        self.disarm_button.configure(state=state)

    def _draw_horizon(self, pitch: float, roll: float) -> None:
        c = self.canvas
        c.delete("all")

        cx = cy = HORIZON_SIZE / 2
        r = HORIZON_RADIUS

        angle = math.radians(-roll)
        offset = pitch * PIXELS_PER_DEGREE

        # Ufuk cizgisinin merkezi, pitch kadar kaymis halde.
        hx = cx + offset * math.sin(angle)
        hy = cy + offset * math.cos(angle)

        span = r * 3
        dx = span * math.cos(angle)
        dy = -span * math.sin(angle)
        nx = span * math.sin(angle)
        ny = span * math.cos(angle)

        c.create_polygon(
            hx - dx, hy - dy, hx + dx, hy + dy,
            hx + dx - nx, hy + dy - ny, hx - dx - nx, hy - dy - ny,
            fill=SKY, outline="")
        c.create_polygon(
            hx - dx, hy - dy, hx + dx, hy + dy,
            hx + dx + nx, hy + dy + ny, hx - dx + nx, hy - dy + ny,
            fill=GROUND, outline="")
        c.create_line(hx - dx, hy - dy, hx + dx, hy + dy, fill=FG, width=2)

        # Pitch merdiveni, 10 derecede bir.
        for step in range(-30, 31, 10):
            if step == 0:
                continue
            d = (pitch - step) * PIXELS_PER_DEGREE
            mx = cx + d * math.sin(angle)
            my = cy + d * math.cos(angle)
            half = 28 if step % 20 else 44
            c.create_line(mx - half * math.cos(angle), my + half * math.sin(angle),
                          mx + half * math.cos(angle), my - half * math.sin(angle),
                          fill=FG, width=1)

        # Yuvarlak maske: tkinter'da kirpma yok, arka plan renginde bir halka ciz.
        c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=BG, width=HORIZON_SIZE)
        c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=DIM, width=2)

        # Roll gostergesi: tepede sabit ucgen ok.
        c.create_polygon(cx, cy - r + 4, cx - 9, cy - r + 20, cx + 9, cy - r + 20,
                         fill=PLANE, outline="")

        # Sabit ucak sembolu.
        c.create_line(cx - 50, cy, cx - 16, cy, fill=PLANE, width=3)
        c.create_line(cx + 16, cy, cx + 50, cy, fill=PLANE, width=3)
        c.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, outline=PLANE, width=2)


def _temp(centi: int) -> str:
    if centi == link.TEMP_ABSENT:
        return "--"
    return f"{centi / 100:.1f} C"
```

- [ ] **Step 3: `tools/navstation/__main__.py` yaz**

```python
"""Giris noktasi:  python -m navstation --port /dev/cu.usbserial-XXXX"""

import argparse
import sys

from . import link, ui


def main() -> int:
    parser = argparse.ArgumentParser(description="ISO U1 yer istasyonu")
    parser.add_argument("--port", required=True,
                        help="ESP32 kumandanin seri portu")
    parser.add_argument("--baud", type=int, default=115200)
    args = parser.parse_args()

    serial_link = link.SerialLink(args.port, args.baud)
    if not serial_link.open():
        print(f"Port acilamadi: {serial_link.last_error}", file=sys.stderr)
        return 1

    try:
        ui.NavStationWindow(serial_link).run()
    finally:
        serial_link.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: `tools/navstation/README.md` yaz**

```markdown
# ISO U1 Yer İstasyonu

ESP32 kumandaya USB ile bağlanır, telemetriyi yapay ufuk ve sayısal
panellerle gösterir, GY-85 kalibrasyonunu tetikler.

## Kurulum

    brew install python-tk@3.14
    .env/bin/pip install pyserial pytest

## Çalıştırma

Portu bul:

    ls /dev/cu.usbserial-* /dev/cu.SLAB_USBtoUART 2>/dev/null

Sonra `tools/` dizininden:

    ../.env/bin/python -m navstation --port /dev/cu.usbserial-XXXX

Kumanda seri monitörü aynı anda açık olmamalı — port tek kullanıcı kabul eder.

## Kalibrasyon

**KALİBRE ET** butonu uçağın o anki IMU okumalarını sıfır kabul eder ve
sonucu STM32 flash'ına yazar.

Koşullar:

- Uçak düz zeminde ve hareketsiz olmalı.
- Motor kapalı olmalı. STM32 armed durumdayken komutu reddeder, buton da pasifleşir.
- Flash yazımı sırasında STM32 1-2 saniye kontrol paketi işlemez. Pervane sökülü olmalı.

Onay telemetriden gelir ve telemetri 1 Hz olduğu için 1-2 saniye sürer.
5 saniyede gelmezse buton "Onay gelmedi" der; tekrar basmak zararsızdır.

Pusula kalibre edilmez — sıfırlansaydı kuzeyi değil kalibrasyon anındaki
yönü gösterirdi.

## Arming

Motor, uçağa güç verildiğinde dönmez. Çalıştırmak için kumandadan:

1. İki çubuğu da aşağı çek
2. Bırak
3. Tekrar aşağı çek ve yarım saniye tut

Kumanda arm olunca iki yükselen ton, disarm olunca tek alçak ton çalar.

Disarm: güç kesme, 5 saniyeden uzun link kaybı, veya bu programdaki
**DISARM** butonu. Uçuşta çubukla disarm yoktur.

## Testler

    cd tools && ../.env/bin/python -m pytest navstation/tests/ -v
```

- [ ] **Step 5: Portsuz çalıştırıp hata yolunu doğrula**

```bash
cd tools && ../.env/bin/python -m navstation --port /dev/does-not-exist
```

Beklenen: `Port acilamadi: ...` ve çıkış kodu 1, traceback yok.

- [ ] **Step 6: Gerçek kumandayla çalıştır**

Kumanda bağlıyken:

```bash
cd tools && ../.env/bin/python -m navstation --port /dev/cu.usbserial-XXXX
```

Doğrula:
1. Pencere açılıyor, paneller 1 saniyede bir güncelleniyor.
2. Uçağı elle yatır — yapay ufuk doğru yöne dönüyor (sağa yatırınca ufuk sola eğiliyor).
3. Sensör satırı `AGMB` gösteriyor (hepsi bağlıysa).
4. **KALİBRE ET**'e bas, onayla, "Kalibrasyon tamam" görün, pitch/roll sıfıra insin.
5. Kumandadan arming jestini yap — Arming satırı `ARMED` olsun, buton pasifleşsin.
6. **DISARM**'a bas — satır `DISARMED` olsun.

- [ ] **Step 7: Tüm testleri çalıştır**

```bash
./tools/run_native_tests.sh
cd tools && ../.env/bin/python -m pytest navstation/tests/ -v
```

Beklenen: hepsi geçer.

- [ ] **Step 8: Commit**

```bash
git add tools/navstation/ui.py tools/navstation/__main__.py tools/navstation/README.md
git commit -m "feat(navstation): tkinter arayuzu, yapay ufuk ve komut butonlari"
```

---

## Self-Review Notları

**Spec kapsamı.** Spec bölümleri → görevler: 4 → Task 1; 5.1/5.2 → Task 5; 5.3 → Task 3 + Task 5; 5.4 → Task 5 + 6 + 9; 6.2/6.3 → Task 2 + 4; 6.4/6.5 → Task 4 + 5; 7 → Task 6; 8.1 → Task 7; 8.2 → Task 9; 8.3 → Task 8 + 9; 9 → her görevin test adımları; 10 → Task 9 Step 1.

**Bilinçli sapma.** Spec `arming.h` dışında ayrı bir başlık öngörmüyordu; `calibration.h` eklendi ki flash kayıt sağlaması ana makinede testlenebilsin. Aksi halde o mantık yalnız tezgahta doğrulanabilirdi.

**Açık kalan.** RY ekseninin fiziksel yönü Task 6 Step 9'da kesinleşir. Task 4 Step 7 bunu geçici olarak deneyip not almayı, kalıcı düzeltmeyi Task 6'dan sonra yapmayı söyler.

**Risk.** Flash yazımı sırasında kesmelerin ~1-2 saniye durması servo çıkışını etkileyebilir. Task 6 Step 9.6 bunu açıkça gözlemeyi ve sorun varsa durup rapor etmeyi şart koşuyor.

**Self-review'da düzeltilenler.**
1. `ui.py` içinde `math` fonksiyon gövdesinde import ediliyordu — modül seviyesine alındı.
2. `LINK_STALE_MS` tanımlıydı ama kullanılmıyordu; spec 8.3'teki "3 saniyedir paket yoksa paneller soluklaşır" karşılıksız kalmıştı. Artık `rx_count` değişimi ana makine saatiyle izleniyor, bayat linkte etiketler soluklaşıyor ve kalibrasyon butonu pasifleşiyor.
3. "Yaş" alanı ESP32'nin kendi çalışma süresini gösteriyordu, paket yaşını değil. Düzeltildi.
4. `KALİBRASYONU SİL` için onay bekleme yoktu; spec 8.2 bit4'ün düşmesini onay sayıyor. `pending_calibration` alanı eklendi, iki yön de aynı zaman aşımıyla izleniyor.
