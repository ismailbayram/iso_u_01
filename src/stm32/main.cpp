#include <Arduino.h>
#include <Servo.h>

Servo myESC;
#define PIN_ESC PA0
#define PIN_LED PC13

#define LORA_M0 PA1
#define LORA_M1 PA2
#define LORA_AUX PA3

const int MIN_THROTTLE = 1100;
const int MAX_THROTTLE = 1940;

struct __attribute__((packed)) ControlPacket
{
    uint16_t packetID;

    uint16_t LX;
    uint16_t LY;
    uint16_t RX;
    uint16_t RY;
};

ControlPacket receivedPacket;

bool waitLoRaReady(unsigned long timeout)
{
    unsigned long start = millis();
    while (digitalRead(LORA_AUX) == LOW)
    {
        if (millis() - start > timeout)
            return false;
    }
    return true;
}

float getBatteryVoltage()
{
    return 12.4;
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

    Serial1.begin(9600);
}

void loop()
{
    if (waitLoRaReady(50) && Serial1.available() >= (int)sizeof(ControlPacket))
    {
        Serial1.readBytes((uint8_t *)&receivedPacket, sizeof(ControlPacket));

        digitalWrite(PIN_LED, !digitalRead(PIN_LED));

        if (waitLoRaReady(50))
        {
            Serial1.println("VOLT:" + String(getBatteryVoltage()) + "V\n");
            Serial1.flush();
        }
    }
}