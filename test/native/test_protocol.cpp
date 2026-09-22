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
