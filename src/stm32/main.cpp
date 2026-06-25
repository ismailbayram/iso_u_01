#include <Arduino.h>
#include <Servo.h>

Servo myESC;
#define PIN_ESC PA0
#define PIN_LED PC13

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

float getBatteryVoltage()
{
    return 12.4;
}

void setup()
{
    pinMode(PIN_LED, OUTPUT);
    pinMode(PIN_ESC, OUTPUT_OPEN_DRAIN); // open-drain mode for ESC signal

    myESC.attach(PIN_ESC, MIN_THROTTLE, MAX_THROTTLE);

    Serial1.begin(9600); // Initialize Serial1 for communication with LoRa module
}

void loop()
{
    if (Serial1.available() >= (int)sizeof(ControlPacket))
    {

        Serial1.readBytes((uint8_t *)&receivedControls, sizeof(ControlPacket));

        digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));

        Serial1.println("VOLT:" + String(getBatteryVoltage()) + "V\n");
    }
}