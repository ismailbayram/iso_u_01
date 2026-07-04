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
  int32_t gpsLatE7;
  int32_t gpsLonE7;
  uint8_t gpsFix;
  uint8_t gpsSats;
};

inline uint8_t computeFrameChecksum(uint8_t packetType, uint8_t payloadLength, const uint8_t *payload) {
  uint8_t checksum = packetType ^ payloadLength;
  for (uint8_t i = 0; i < payloadLength; i++) {
    checksum ^= payload[i];
  }
  return checksum;
}

}  // namespace radio
