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
unsigned long lastTelemetryTime = 0;

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

    Serial1.begin(9600);
}

void loop()
{
    if (Serial1.available() >= (int)sizeof(ControlPacket))
    {
        Serial1.readBytes((uint8_t *)&receivedPacket, sizeof(ControlPacket));

        digitalWrite(PIN_LED, !digitalRead(PIN_LED));

        servo1.write(map(receivedPacket.LX, 0, 32767, 0, 180));
        servo2.write(map(receivedPacket.LY, 0, 32767, 0, 180));
        servo3.write(map(receivedPacket.RX, 0, 32767, 0, 180));
    }

    if (millis() - lastTelemetryTime > 500)
    {
        if (digitalRead(LORA_AUX) == HIGH)
        {
            Serial1.print("V:");
            Serial1.print(getBatteryVoltage(), 1);
            Serial1.print("\n");

            lastTelemetryTime = millis();
        }
    }
}