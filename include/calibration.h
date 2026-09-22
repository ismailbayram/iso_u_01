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
