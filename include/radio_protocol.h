#pragma once

#include <stdint.h>

namespace radio {

constexpr uint8_t PREAMBLE_1 = 0xAA;
constexpr uint8_t PREAMBLE_2 = 0x55;

enum PacketType : uint8_t {
  PACKET_TYPE_CONTROL = 1,
  PACKET_TYPE_TELEMETRY = 2,
  PACKET_TYPE_TELEMETRY_REQ = 3
};

enum SensorStatusBit : uint8_t {
  SENSOR_STATUS_ADXL345 = 1 << 0,
  SENSOR_STATUS_ITG3205 = 1 << 1,
  SENSOR_STATUS_QMC5883L = 1 << 2,
  SENSOR_STATUS_DS18_BATT = 1 << 3,
  SENSOR_STATUS_DS18_ESC = 1 << 4
};

struct __attribute__((packed)) TelemetryRequestPacket {
  uint8_t sequence;
};

struct __attribute__((packed)) ControlPacket {
  uint16_t packetID;
  uint16_t LX;
  uint16_t LY;
  uint16_t RX;
  uint16_t RY;
};

struct __attribute__((packed)) TelemetryPacket {
  uint16_t voltageMv;
  int16_t battTempCentiC;
  int16_t escTempCentiC;
  int16_t mpuAx;
  int16_t mpuAy;
  int16_t mpuAz;
  int16_t mpuGx;
  int16_t mpuGy;
  int16_t mpuGz;
  int16_t compassHeading;
  uint8_t sensorStatus;
  uint8_t i2cErrAdxl;
  uint8_t i2cErrItg;
  uint8_t i2cErrQmc;
};

inline uint8_t computeFrameChecksum(uint8_t packetType, uint8_t payloadLength, const uint8_t *payload) {
  uint8_t checksum = packetType ^ payloadLength;
  for (uint8_t i = 0; i < payloadLength; i++) {
    checksum ^= payload[i];
  }
  return checksum;
}

}  // namespace radio
