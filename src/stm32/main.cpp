#include <Arduino.h>
#include <LoRa_E22.h>
#include <Servo.h>
#include "radio_protocol.h"

Servo myESC;
Servo servo1;
Servo servo2;
Servo servo3;
#define PIN_ESC PA0
#define PIN_SERVO1 PA6
#define PIN_SERVO2 PA7
#define PIN_SERVO3 PB0
#define PIN_LED PC13

#define LORA_M0 PA1
#define LORA_M1 PA2
#define LORA_AUX PA3
LoRa_E22 e22(&Serial1, LORA_AUX, LORA_M0, LORA_M1, UART_BPS_RATE_9600);

const int MIN_THROTTLE = 1100;
const int MAX_THROTTLE = 1940;

using radio::ControlPacket;
using radio::TelemetryPacket;

ControlPacket receivedPacket;
unsigned long lastTelemetryTime = 0;
unsigned long lastPacketTime = 0;

const unsigned long RX_TIMEOUT_MS = 300;
const unsigned long TELEMETRY_INTERVAL_MS = 200;
uint8_t payloadBuffer[64];
uint8_t payloadIndex = 0;
uint8_t parserState = 0;
uint8_t incomingPacketType = 0;
uint8_t incomingPayloadLength = 0;

void sendFrame(uint8_t packetType, const void *payload, uint8_t payloadLength);

void applyServoOutputs(const ControlPacket &packet)
{
    const int center = 2048;
    const int deadband = 45;
    const float filterAlpha = 0.35f;
    static int lastServo1 = 90;
    static int lastServo2 = 90;
    static int lastServo3 = 90;
    static float filteredLX = 2048.0f;
    static float filteredRX = 2048.0f;
    static float filteredRY = 2048.0f;

    filteredLX = filteredLX + filterAlpha * ((float)packet.LX - filteredLX);
    filteredRX = filteredRX + filterAlpha * ((float)packet.RX - filteredRX);
    filteredRY = filteredRY + filterAlpha * ((float)packet.RY - filteredRY);

    int lx = (int)filteredLX;
    int rx = (int)filteredRX;
    int ry = (int)filteredRY;

    if (abs(lx - center) < deadband)
    {
        lx = center;
    }
    if (abs(rx - center) < deadband)
    {
        rx = center;
    }
    if (abs(ry - center) < deadband)
    {
        ry = center;
    }

    int s1 = map(lx, 0, 4095, 0, 180);
    int s2 = map(rx, 0, 4095, 0, 180);
    int s3 = map(ry, 0, 4095, 0, 180);

    if (abs(s1 - lastServo1) >= 2)
    {
        servo1.write(s1);
        lastServo1 = s1;
    }
    if (abs(s2 - lastServo2) >= 2)
    {
        servo2.write(s2);
        lastServo2 = s2;
    }
    if (abs(s3 - lastServo3) >= 2)
    {
        servo3.write(s3);
        lastServo3 = s3;
    }
}

void applyFailsafe()
{
    myESC.writeMicroseconds(MIN_THROTTLE);
    servo1.write(90);
    servo2.write(90);
    servo3.write(90);
}

bool parseIncomingByte(uint8_t b)
{
    switch (parserState)
    {
    case 0:
        if (b == radio::PREAMBLE_1)
        {
            parserState = 1;
        }
        break;
    case 1:
        if (b == radio::PREAMBLE_2)
        {
            parserState = 2;
        }
        else if (b == radio::PREAMBLE_1)
        {
            parserState = 1;
        }
        else
        {
            parserState = 0;
        }
        break;
    case 2:
        incomingPacketType = b;
        parserState = 3;
        break;
    case 3:
        incomingPayloadLength = b;
        payloadIndex = 0;
        if (incomingPayloadLength == 0 || incomingPayloadLength > sizeof(payloadBuffer))
        {
            parserState = 0;
        }
        else
        {
            parserState = 4;
        }
        break;
    case 4:
        payloadBuffer[payloadIndex++] = b;
        if (payloadIndex >= incomingPayloadLength)
        {
            parserState = 5;
        }
        break;
    case 5:
    {
        uint8_t checksum = radio::computeFrameChecksum(incomingPacketType, incomingPayloadLength, payloadBuffer);
        parserState = 0;
        if (checksum == b && incomingPacketType == radio::PACKET_TYPE_CONTROL && incomingPayloadLength == sizeof(ControlPacket))
        {
            memcpy(&receivedPacket, payloadBuffer, sizeof(ControlPacket));
            return true;
        }
        break;
    }
    default:
        parserState = 0;
        break;
    }
    return false;
}

float getBatteryVoltage()
{
    return 12.4;
}

void sendFrame(uint8_t packetType, const void *payload, uint8_t payloadLength)
{
    const uint8_t *payloadBytes = (const uint8_t *)payload;
    Serial1.write(radio::PREAMBLE_1);
    Serial1.write(radio::PREAMBLE_2);
    Serial1.write(packetType);
    Serial1.write(payloadLength);
    Serial1.write(payloadBytes, payloadLength);
    Serial1.write(radio::computeFrameChecksum(packetType, payloadLength, payloadBytes));
}

void setupLoRaWithLibrary()
{
    if (!e22.begin()) {
        return;
    }

    ResponseStructContainer c = e22.getConfiguration();
    if (c.status.code != E22_SUCCESS) {
        c.close();
        return;
    }

    Configuration cfg = *(Configuration *)c.data;
    c.close();

    bool changed = false;

    if (cfg.SPED.uartBaudRate != UART_BPS_9600) {
        cfg.SPED.uartBaudRate = UART_BPS_9600;
        changed = true;
    }

    if (cfg.SPED.airDataRate != AIR_DATA_RATE_110_384) {
        cfg.SPED.airDataRate = AIR_DATA_RATE_110_384;
        changed = true;
    }

    if (cfg.TRANSMISSION_MODE.WORTransceiverControl != WOR_RECEIVER) {
        cfg.TRANSMISSION_MODE.WORTransceiverControl = WOR_RECEIVER;
        changed = true;
    }

    if (changed) {
        e22.setConfiguration(cfg, WRITE_CFG_PWR_DWN_SAVE);
    }

    e22.setMode(MODE_0_NORMAL);
}

void setup()
{
    pinMode(PIN_LED, OUTPUT);
    pinMode(PIN_ESC, OUTPUT_OPEN_DRAIN);
    pinMode(LORA_M0, OUTPUT);
    pinMode(LORA_M1, OUTPUT);
    pinMode(LORA_AUX, INPUT);

    digitalWrite(LORA_M0, LOW);
    digitalWrite(LORA_M1, LOW);
    delay(200);

    myESC.attach(PIN_ESC, MIN_THROTTLE, MAX_THROTTLE);
    myESC.writeMicroseconds(MIN_THROTTLE);

    servo1.attach(PIN_SERVO1);
    servo2.attach(PIN_SERVO2);
    servo3.attach(PIN_SERVO3);
    pinMode(PIN_SERVO1, OUTPUT_OPEN_DRAIN);
    pinMode(PIN_SERVO2, OUTPUT_OPEN_DRAIN);
    pinMode(PIN_SERVO3, OUTPUT_OPEN_DRAIN);

    servo1.write(90);
    servo2.write(90);
    servo3.write(90);

    setupLoRaWithLibrary();

    lastPacketTime = millis();
}

void loop()
{
    while (Serial1.available())
    {
        if (parseIncomingByte((uint8_t)Serial1.read()))
        {
            lastPacketTime = millis();
            applyServoOutputs(receivedPacket);
            digitalWrite(PIN_LED, !digitalRead(PIN_LED));
        }
    }

    if (millis() - lastPacketTime > RX_TIMEOUT_MS)
    {
        applyFailsafe();
    }

    if (millis() - lastTelemetryTime > TELEMETRY_INTERVAL_MS)
    {
        if (digitalRead(LORA_AUX) == HIGH)
        {
            TelemetryPacket telemetry;
            telemetry.voltageMv = (uint16_t)(getBatteryVoltage() * 1000.0f);
            telemetry.mpuAx = 0;
            telemetry.mpuAy = 0;
            telemetry.mpuAz = 0;
            telemetry.gpsLatE7 = 0;
            telemetry.gpsLonE7 = 0;
            telemetry.gpsFix = 0;
            telemetry.gpsSats = 0;

            sendFrame(radio::PACKET_TYPE_TELEMETRY, &telemetry, sizeof(TelemetryPacket));
            lastTelemetryTime = millis();
        }
    }
}
