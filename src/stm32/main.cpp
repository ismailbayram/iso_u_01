#include <Arduino.h>
#include <DallasTemperature.h>
#include <LoRa_E22.h>
#include <OneWire.h>
#include <Servo.h>
#include "radio_protocol.h"

Servo myESC;
Servo servoAIL;
Servo servoELE;
Servo servoRUD;
#define PIN_ESC PA1
#define PIN_SERVO_AIL PA6
#define PIN_SERVO_ELE PA7
#define PIN_SERVO_RUD PB0
#define PIN_LED PC13
#define PIN_DS18_BATT PA5
#define PIN_DS18_ESC PB1
#define PIN_VBAT_SENSE PA4
#define PIN_GPS_TX PA2
#define PIN_GPS_RX PA3

#define LORA_M0 PA15
#define LORA_M1 PA12
#define LORA_AUX PA11
LoRa_E22 e22(&Serial1, LORA_AUX, LORA_M0, LORA_M1, UART_BPS_RATE_9600);

const int MIN_THROTTLE = 1100;
const int MAX_THROTTLE = 1940;
const float VBAT_DIVIDER_R_TOP = 100000.0f;
const float VBAT_DIVIDER_R_BOTTOM = 20000.0f;
const float ADC_REF_V = 3.3f;
const float ADC_MAX_COUNTS = 4095.0f;

using radio::ControlPacket;
using radio::TelemetryPacket;
using radio::TelemetryRequestPacket;

ControlPacket receivedPacket;
unsigned long lastTelemetryTime = 0;
unsigned long lastPacketTime = 0;

const unsigned long RX_TIMEOUT_MS = 300;
uint8_t payloadBuffer[64];
uint8_t payloadIndex = 0;
uint8_t parserState = 0;
uint8_t incomingPacketType = 0;
uint8_t incomingPayloadLength = 0;
bool telemetryRequested = false;
uint8_t lastTelemetryReqSeq = 0;

OneWire oneWireBatt(PIN_DS18_BATT);
DallasTemperature ds18Batt(&oneWireBatt);
OneWire oneWireEsc(PIN_DS18_ESC);
DallasTemperature ds18Esc(&oneWireEsc);

unsigned long lastTempRequestMs = 0;
const unsigned long TEMP_CONVERSION_INTERVAL_MS = 300;
int16_t battTempCentiC = INT16_MIN;
int16_t escTempCentiC = INT16_MIN;

void sendFrame(uint8_t packetType, const void *payload, uint8_t payloadLength);

void applyOutputs(const ControlPacket &packet)
{
    const int center = 2048;
    const int deadband = 45;
    const float filterAlpha = 0.35f;
    static int lastServoAIL = 90;
    static int lastServoELE = 90;
    static int lastServoRUD = 90;
    static float filteredLX = 2048.0f;
    static float filteredLY = 0.0f;
    static float filteredRX = 2048.0f;
    static float filteredRY = 2048.0f;

    filteredLX = filteredLX + filterAlpha * ((float)packet.LX - filteredLX);
    filteredLY = filteredLY + filterAlpha * ((float)packet.LY - filteredLY);
    filteredRX = filteredRX + filterAlpha * ((float)packet.RX - filteredRX);
    filteredRY = filteredRY + filterAlpha * ((float)packet.RY - filteredRY);

    int lx = (int)filteredLX;
    int ly = (int)filteredLY;
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

    int s1 = map(rx, 0, 4095, 0, 180);
    int s2 = map(ry, 0, 4095, 0, 180);
    int s3 = map(lx, 0, 4095, 0, 180);
    int escUs = map(constrain(ly, 0, 4095), 0, 4095, MIN_THROTTLE, MAX_THROTTLE);

    myESC.writeMicroseconds(escUs);

    if (abs(s1 - lastServoAIL) >= 2)
    {
        servoAIL.write(s1);
        lastServoAIL = s1;
    }
    if (abs(s2 - lastServoELE) >= 2)
    {
        servoELE.write(s2);
        lastServoELE = s2;
    }
    if (abs(s3 - lastServoRUD) >= 2)
    {
        servoRUD.write(s3);
        lastServoRUD = s3;
    }
}

void applyFailsafe()
{
    myESC.writeMicroseconds(MIN_THROTTLE);
    servoAIL.write(90);
    servoELE.write(90);
    servoRUD.write(90);
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
        if (checksum == b && incomingPacketType == radio::PACKET_TYPE_TELEMETRY_REQ && incomingPayloadLength == sizeof(TelemetryRequestPacket))
        {
            TelemetryRequestPacket req;
            memcpy(&req, payloadBuffer, sizeof(TelemetryRequestPacket));
            lastTelemetryReqSeq = req.sequence;
            telemetryRequested = true;
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
    uint32_t sum = 0;
    for (int i = 0; i < 8; i++)
    {
        sum += analogRead(PIN_VBAT_SENSE);
    }
    float adcCounts = (float)sum / 8.0f;
    float vSense = (adcCounts / ADC_MAX_COUNTS) * ADC_REF_V;
    return vSense * ((VBAT_DIVIDER_R_TOP + VBAT_DIVIDER_R_BOTTOM) / VBAT_DIVIDER_R_BOTTOM);
}

void updateDs18Temperatures()
{
    if (millis() - lastTempRequestMs < TEMP_CONVERSION_INTERVAL_MS)
    {
        return;
    }

    lastTempRequestMs = millis();

    float battC = ds18Batt.getTempCByIndex(0);
    float escC = ds18Esc.getTempCByIndex(0);

    battTempCentiC = (battC == DEVICE_DISCONNECTED_C) ? INT16_MIN : (int16_t)(battC * 100.0f);
    escTempCentiC = (escC == DEVICE_DISCONNECTED_C) ? INT16_MIN : (int16_t)(escC * 100.0f);

    ds18Batt.requestTemperatures();
    ds18Esc.requestTemperatures();
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
    if (!e22.begin())
    {
        return;
    }

    ResponseStructContainer c = e22.getConfiguration();
    if (c.status.code != E22_SUCCESS)
    {
        c.close();
        return;
    }

    Configuration cfg = *(Configuration *)c.data;
    c.close();

    bool changed = false;

    if (cfg.SPED.uartBaudRate != UART_BPS_9600)
    {
        cfg.SPED.uartBaudRate = UART_BPS_9600;
        changed = true;
    }

    if (cfg.SPED.airDataRate != AIR_DATA_RATE_110_384)
    {
        cfg.SPED.airDataRate = AIR_DATA_RATE_110_384;
        changed = true;
    }

    if (cfg.TRANSMISSION_MODE.WORTransceiverControl != WOR_RECEIVER)
    {
        cfg.TRANSMISSION_MODE.WORTransceiverControl = WOR_RECEIVER;
        changed = true;
    }

    if (changed)
    {
        e22.setConfiguration(cfg, WRITE_CFG_PWR_DWN_SAVE);
    }

    e22.setMode(MODE_0_NORMAL);
}

void setup()
{
    pinMode(PIN_LED, OUTPUT);
    pinMode(PIN_ESC, OUTPUT_OPEN_DRAIN);
    pinMode(PIN_VBAT_SENSE, INPUT_ANALOG);
    pinMode(LORA_M0, OUTPUT);
    pinMode(LORA_M1, OUTPUT);
    pinMode(LORA_AUX, INPUT);

    digitalWrite(LORA_M0, LOW);
    digitalWrite(LORA_M1, LOW);
    delay(200);

    myESC.attach(PIN_ESC, MIN_THROTTLE, MAX_THROTTLE);
    myESC.writeMicroseconds(MIN_THROTTLE);

    servoAIL.attach(PIN_SERVO_AIL);
    servoELE.attach(PIN_SERVO_ELE);
    servoRUD.attach(PIN_SERVO_RUD);
    pinMode(PIN_SERVO_AIL, OUTPUT_OPEN_DRAIN);
    pinMode(PIN_SERVO_ELE, OUTPUT_OPEN_DRAIN);
    pinMode(PIN_SERVO_RUD, OUTPUT_OPEN_DRAIN);

    servoAIL.write(90);
    servoELE.write(90);
    servoRUD.write(90);

    ds18Batt.begin();
    ds18Esc.begin();
    ds18Batt.setWaitForConversion(false);
    ds18Esc.setWaitForConversion(false);
    ds18Batt.setResolution(10);
    ds18Esc.setResolution(10);
    ds18Batt.requestTemperatures();
    ds18Esc.requestTemperatures();
    lastTempRequestMs = millis();

    Serial1.setTx(PA9);
    Serial1.setRx(PA10);

    setupLoRaWithLibrary();

    lastPacketTime = millis();
}

void loop()
{
    updateDs18Temperatures();

    uint8_t bytesProcessed = 0;
    while (Serial1.available() && bytesProcessed < 32)
    {
        if (parseIncomingByte((uint8_t)Serial1.read()))
        {
            lastPacketTime = millis();
            applyOutputs(receivedPacket);
        }
        bytesProcessed++;
    }

    if (telemetryRequested)
    {
        if (digitalRead(LORA_AUX) == HIGH)
        {
            TelemetryPacket telemetry;
            telemetry.voltageMv = (uint16_t)(getBatteryVoltage() * 1000.0f);
            telemetry.battTempCentiC = battTempCentiC;
            telemetry.escTempCentiC = escTempCentiC;
            telemetry.mpuAx = 0;
            telemetry.mpuAy = 0;
            telemetry.mpuAz = 0;
            telemetry.gpsLatE7 = 0;
            telemetry.gpsLonE7 = 0;
            telemetry.gpsFix = 1;
            telemetry.gpsSats = lastTelemetryReqSeq;

            sendFrame(radio::PACKET_TYPE_TELEMETRY, &telemetry, sizeof(TelemetryPacket));
            delayMicroseconds(2500);
            sendFrame(radio::PACKET_TYPE_TELEMETRY, &telemetry, sizeof(TelemetryPacket));

            telemetryRequested = false;
            lastTelemetryTime = millis();
        }
    }

    if (millis() - lastPacketTime > RX_TIMEOUT_MS)
    {
        applyFailsafe();
    }
}
