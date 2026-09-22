#pragma once

#include <stdint.h>

namespace radio {

constexpr uint8_t PREAMBLE_1 = 0xAA;
constexpr uint8_t PREAMBLE_2 = 0x55;

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

struct __attribute__((packed)) TelemetryRequestPacket {
  uint8_t sequence;
};

struct __attribute__((packed)) CommandPacket {
  uint8_t sequence;
  uint8_t command;
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
  int32_t gpsLatE7;
  int32_t gpsLonE7;
  uint8_t gpsFix;
  uint8_t gpsSats;
  uint32_t pressurePa;     // BMP280 basinci, Pascal. Sensor yoksa 0.
  int16_t baroTempCentiC;  // BMP280 sicakligi, santi-derece. Sensor yoksa INT16_MIN.
  uint8_t statusFlags;     // StatusFlag bitleri.
};

inline uint8_t computeFrameChecksum(uint8_t packetType, uint8_t payloadLength, const uint8_t *payload) {
  uint8_t checksum = packetType ^ payloadLength;
  for (uint8_t i = 0; i < payloadLength; i++) {
    checksum ^= payload[i];
  }
  return checksum;
}

}  // namespace radio
