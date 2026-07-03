#include <Arduino.h>
#include <LoRa_E22.h>
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
LoRa_E22 e22(&Serial1, LORA_AUX, LORA_M0, LORA_M1, UART_BPS_RATE_9600);

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

void setupLoRaWithLibrary()
{
    Serial6.println("[E22] setup basliyor...");

    if (!e22.begin()) {
        Serial6.println("[E22] begin basarisiz");
        return;
    }

    ResponseStructContainer c = e22.getConfiguration();
    if (c.status.code != E22_SUCCESS) {
        Serial6.print("[E22] config okunamadi: ");
        Serial6.println(c.status.getResponseDescription());
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

    if (cfg.SPED.airDataRate != AIR_DATA_RATE_111_625) {
        cfg.SPED.airDataRate = AIR_DATA_RATE_111_625;
        changed = true;
    }

    if (cfg.TRANSMISSION_MODE.WORTransceiverControl != WOR_RECEIVER) {
        cfg.TRANSMISSION_MODE.WORTransceiverControl = WOR_RECEIVER;
        changed = true;
    }

    if (changed) {
        ResponseStatus rs = e22.setConfiguration(cfg, WRITE_CFG_PWR_DWN_SAVE);
        Serial6.print("[E22] kaydet: ");
        Serial6.println(rs.getResponseDescription());
    } else {
        Serial6.println("[E22] ayar zaten uygun");
    }

    e22.setMode(MODE_0_NORMAL);
    Serial6.println("[E22] setup tamam");
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
