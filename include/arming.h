#pragma once

#include <stdint.h>

// Arming jesti: iki cubuk da asagi, birak, tekrar asagi, 500 ms tut.
// YALNIZCA ucaktaki STM32 bu detector'u calistirir; motoru suren taraf
// yetkili olsun diye. Kumanda jesti kendi cozmez, arm/disarm bildirimini
// telemetrideki STATUS_ARMED bitinden alir ve bu yuzden ~1 saniye gecikir.
// Donanimdan bagimsiz tutuluyor ki ana makinede testlenebilsin.
namespace arming {

constexpr uint16_t DOWN_THRESHOLD = 400;
constexpr uint16_t RELEASE_THRESHOLD = 1600;
constexpr uint32_t HOLD_MS = 500;
constexpr uint32_t SEQUENCE_TIMEOUT_MS = 3000;
constexpr uint8_t HOLD_MIN_SAMPLES = 8;

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
    holdSamples_ = 0;
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
      // Son asamada sekans zaman asimi uygulanmaz. SEQUENCE_TIMEOUT_MS jest
      // desenini tamamlama suresini sinirlar; Down2'ye zamaninda girildiyse
      // pilot cubuklari bilincli tutuyor demektir ve jesti tutma ortasinda
      // sessizce reddetmek geri bildirimsiz bir basarisizlik olurdu.
      // Sonuc: arm en gec ~3500 ms'de olur. Test 10-11 bu siniri sabitliyor.
      if (!bothDown) {
        enter(Phase::Idle, nowMs);
      } else {
        if (holdSamples_ < 255) {
          holdSamples_++;
        }
        // Tutma hem duvar saatiyle hem gelen paket sayisiyla olculur. Paket
        // sayisi, link yarida koptuktan sonra tek bir gec pakete dayanarak
        // arm etmeyi engeller. Araliklari olcmez: radyo birikmis cerceveleri
        // toplu teslim ederse sayac 500 ms'den kisa surede dolabilir.
        if (nowMs - phaseEnteredMs_ >= HOLD_MS && holdSamples_ >= HOLD_MIN_SAMPLES) {
          armed_ = true;
          enter(Phase::Idle, nowMs);
          return true;
        }
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
    holdSamples_ = 0;
    phase_ = next;
    phaseEnteredMs_ = nowMs;
  }

  bool timedOut(uint32_t nowMs) const {
    return nowMs - sequenceStartedMs_ > SEQUENCE_TIMEOUT_MS;
  }

  Phase phase_ = Phase::Idle;
  uint32_t phaseEnteredMs_ = 0;
  uint32_t sequenceStartedMs_ = 0;
  uint8_t holdSamples_ = 0;
  bool armed_ = false;
};

}  // namespace arming
