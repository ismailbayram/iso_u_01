#include <Arduino.h>
#include <Servo.h>

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

#define FT232_TX PA11
#define FT232_RX PA12

HardwareSerial Serial6(6);

const int MIN_THROTTLE = 1100;
const int MAX_THROTTLE = 1940;

struct __attribute__((packed)) ControlPacket
{
    uint16_t packetID;
    uint8_t LX;
    uint8_t LY;
    uint8_t RX;
    uint8_t RY;
};

struct __attribute__((packed)) ControlFrame
{
    uint8_t preamble1;
    uint8_t preamble2;
    ControlPacket payload;
    uint8_t checksum;
};

ControlPacket receivedPacket;
unsigned long lastTelemetryTime = 0;
unsigned long lastPacketTime = 0;
unsigned long lastDebugTime = 0;

const uint8_t FRAME_PREAMBLE_1 = 0xAA;
const uint8_t FRAME_PREAMBLE_2 = 0x55;
const unsigned long RX_TIMEOUT_MS = 300;
const unsigned long DEBUG_PRINT_INTERVAL_MS = 200;

uint8_t payloadBuffer[sizeof(ControlPacket)];
uint8_t payloadIndex = 0;
uint8_t parserState = 0;

uint8_t computeChecksum(const uint8_t *data, size_t len)
{
    uint8_t crc = 0;
    for (size_t i = 0; i < len; i++)
    {
        crc ^= data[i];
    }
    return crc;
}

void applyServoOutputs(const ControlPacket &packet)
{
    const int center = 128;
    const int deadband = 3;
    static int lastServo1 = 90;
    static int lastServo2 = 90;
    static int lastServo3 = 90;

    int lx = packet.LX;
    int rx = packet.RX;
    int ry = packet.RY;

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

    int s1 = map(lx, 0, 255, 0, 180);
    int s2 = map(rx, 0, 255, 0, 180);
    int s3 = map(ry, 0, 255, 0, 180);

    if (abs(s1 - lastServo1) >= 1)
    {
        servo1.write(s1);
        lastServo1 = s1;
    }
    if (abs(s2 - lastServo2) >= 1)
    {
        servo2.write(s2);
        lastServo2 = s2;
    }
    if (abs(s3 - lastServo3) >= 1)
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
        if (b == FRAME_PREAMBLE_1)
        {
            parserState = 1;
        }
        break;
    case 1:
        if (b == FRAME_PREAMBLE_2)
        {
            parserState = 2;
            payloadIndex = 0;
        }
        else if (b == FRAME_PREAMBLE_1)
        {
            parserState = 1;
        }
        else
        {
            parserState = 0;
        }
        break;
    case 2:
        payloadBuffer[payloadIndex++] = b;
        if (payloadIndex >= sizeof(ControlPacket))
        {
            parserState = 3;
        }
        break;
    case 3:
    {
        uint8_t checksum = computeChecksum(payloadBuffer, sizeof(ControlPacket));
        parserState = 0;
        if (checksum == b)
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

void configureLoRa()
{
    const uint8_t READ_CMD_9[] = {0xC1, 0x00, 0x09};
    const uint8_t READ_CMD_6[] = {0xC1, 0x00, 0x06};
    const uint8_t WRITE_CMD_PREFIX[] = {0xC0, 0x00, 0x09};
    const uint8_t WRITE_CMD_PREFIX_6[] = {0xC0, 0x00, 0x06};
    const uint8_t LEGACY_READ_CMD[] = {0xC1, 0xC1, 0xC1};
    const uint8_t REG0_INDEX = 3;
    const uint8_t UART_115200_BITS = (0x07 << 3);
    const uint8_t AIR_RATE_BITS = 0x07;
    const uint8_t LEGACY_AIR_RATE_MASK = 0x07;

    Serial6.println("[CFG] LoRa modül yapılandırması...");

    digitalWrite(LORA_M0, HIGH);
    digitalWrite(LORA_M1, HIGH);
    delay(50);

    unsigned long _start = millis();
    while (digitalRead(LORA_AUX) == LOW)
    {
        if (millis() - _start > 500)
        {
            Serial6.println("[CFG] HATA: Modul yanit vermiyor");
            digitalWrite(LORA_M0, LOW);
            digitalWrite(LORA_M1, LOW);
            return;
        }
    }
    delay(10);

    uint8_t raw[16];
    size_t rawLen = 0;
    while (Serial1.available()) { Serial1.read(); }
    Serial1.write(READ_CMD_9, sizeof(READ_CMD_9));
    Serial1.flush();
    unsigned long waitStart = millis();
    while ((millis() - waitStart) < 300)
    {
        while (Serial1.available() && rawLen < sizeof(raw))
        {
            raw[rawLen++] = (uint8_t)Serial1.read();
        }
        if (rawLen >= 12)
        {
            break;
        }
    }

    if (rawLen < 9)
    {
        rawLen = 0;
        while (Serial1.available()) { Serial1.read(); }
        Serial1.write(READ_CMD_6, sizeof(READ_CMD_6));
        Serial1.flush();
        waitStart = millis();
        while ((millis() - waitStart) < 300)
        {
            while (Serial1.available() && rawLen < sizeof(raw))
            {
                raw[rawLen++] = (uint8_t)Serial1.read();
            }
            if (rawLen >= 9)
            {
                break;
            }
        }
    }

    if (rawLen < 6)
    {
        rawLen = 0;
        while (Serial1.available()) { Serial1.read(); }
        Serial1.write(LEGACY_READ_CMD, sizeof(LEGACY_READ_CMD));
        Serial1.flush();
        waitStart = millis();
        while ((millis() - waitStart) < 300)
        {
            while (Serial1.available() && rawLen < sizeof(raw))
            {
                raw[rawLen++] = (uint8_t)Serial1.read();
            }
            if (rawLen >= 6)
            {
                break;
            }
        }
    }

    uint8_t regs[9];
    bool parse9 = false;
    bool parse6 = false;
    if (rawLen >= 12 && raw[0] == 0xC1 && raw[1] == 0x00 && raw[2] == 0x09)
    {
        memcpy(regs, &raw[3], 9);
        parse9 = true;
    }
    else if (rawLen >= 9 && raw[0] == 0xC1 && raw[1] == 0x00 && raw[2] == 0x06)
    {
        parse6 = true;
    }
    else if (rawLen >= 6)
    {
        parse6 = true;
    }

    if (!parse9 && !parse6)
    {
        Serial6.print("[CFG] HATA: Config okunamadi, gelen byte: ");
        Serial6.println((int)rawLen);
        digitalWrite(LORA_M0, LOW);
        digitalWrite(LORA_M1, LOW);
        return;
    }

    if (parse9)
    {
        Serial6.print("[CFG] Mevcut regs: ");
        for (int i = 0; i < 9; i++)
        {
            if (regs[i] < 0x10)
            {
                Serial6.print('0');
            }
            Serial6.print(regs[i], HEX);
            Serial6.print(" ");
        }
        Serial6.println();
    }

    uint8_t targetReg0 = 0;
    if (parse9)
    {
        targetReg0 = (regs[REG0_INDEX] & 0xC0) | UART_115200_BITS | AIR_RATE_BITS;
        bool needsWrite = (regs[REG0_INDEX] != targetReg0);
        if (needsWrite)
        {
            regs[REG0_INDEX] = targetReg0;
            uint8_t wcmd[12];
            memcpy(wcmd, WRITE_CMD_PREFIX, sizeof(WRITE_CMD_PREFIX));
            memcpy(&wcmd[3], regs, sizeof(regs));
            Serial1.write(wcmd, sizeof(wcmd));
            Serial1.flush();
            delay(120);
            Serial6.println("[CFG] 9-byte profil guncellendi");
        }
        else
        {
            Serial6.println("[CFG] 9-byte profil zaten dogru");
        }
    }
    else
    {
        uint8_t legacy[6];
        memcpy(legacy, &raw[rawLen - 6], 6);
        targetReg0 = (uint8_t)((legacy[2] & 0xF8) | LEGACY_AIR_RATE_MASK);
        bool needsWrite = (legacy[2] != targetReg0);
        if (needsWrite)
        {
            legacy[2] = targetReg0;
            uint8_t wcmd[] = {WRITE_CMD_PREFIX_6[0], WRITE_CMD_PREFIX_6[1], WRITE_CMD_PREFIX_6[2], legacy[0], legacy[1], legacy[2], legacy[3], legacy[4], legacy[5]};
            Serial1.write(wcmd, sizeof(wcmd));
            Serial1.flush();
            delay(120);
            Serial6.println("[CFG] 6-byte profil guncellendi (yalniz air-rate)");
        }
        else
        {
            Serial6.println("[CFG] 6-byte profil zaten dogru");
        }
    }

    while (Serial1.available())
    {
        Serial1.read();
    }

    digitalWrite(LORA_M0, LOW);
    digitalWrite(LORA_M1, LOW);
    delay(200);

    Serial1.end();
    Serial1.begin(115200);

    Serial6.println("[CFG] Tamam: 115200 UART, hizli air-rate");
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

    Serial6.setTx(FT232_TX);
    Serial6.setRx(FT232_RX);
    Serial6.begin(115200);
    Serial6.println("[MONITOR] FT232 baslatildi.");

    Serial1.begin(9600);
    configureLoRa();

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

            // if (millis() - lastDebugTime >= DEBUG_PRINT_INTERVAL_MS)
            // {
            //     lastDebugTime = millis();
            //     Serial6.print("[RX] ID:");
            //     Serial6.print(receivedPacket.packetID);
            //     Serial6.print(" LX:");
            //     Serial6.print(receivedPacket.LX);
            //     Serial6.print(" LY:");
            //     Serial6.print(receivedPacket.LY);
            //     Serial6.print(" RX:");
            //     Serial6.print(receivedPacket.RX);
            //     Serial6.print(" RY:");
            //     Serial6.print(receivedPacket.RY);
            //     Serial6.println();
            // }
        }
    }

    if (millis() - lastPacketTime > RX_TIMEOUT_MS)
    {
        applyFailsafe();
    }

    // if (millis() - lastTelemetryTime > 1000)
    // {
    //     if (digitalRead(LORA_AUX) == HIGH)
    //     {
    //         Serial1.print("V:");
    //         Serial1.print(getBatteryVoltage(), 1);
    //         Serial1.print("\n");

    //         Serial6.print("[TX Telemetry] V:");
    //         Serial6.print(getBatteryVoltage(), 1);
    //         Serial6.println("V");

    //         lastTelemetryTime = millis();
    //     }
    // }
}
