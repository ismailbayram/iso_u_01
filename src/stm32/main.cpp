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

    uint16_t LX;
    uint16_t LY;
    uint16_t RX;
    uint16_t RY;
};

ControlPacket receivedPacket;
unsigned long lastTelemetryTime = 0;

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

    Serial6.setTx(FT232_TX);
    Serial6.setRx(FT232_RX);
    Serial6.begin(115200);
    Serial6.println("[MONITOR] FT232 baslatildi. LoRa haberlesmesi izleniyor...");
}

void loop()
{
    // Tam olarak bir paket boyutu (10 byte) kadar veri geldi mi?
    if (Serial1.available() >= (int)sizeof(ControlPacket))
    {
        // Veriyi struct yapısına oku
        int alinanByte = Serial1.readBytes((uint8_t *)&receivedPacket, sizeof(ControlPacket));

        if (alinanByte == sizeof(ControlPacket))
        {
            digitalWrite(PIN_LED, !digitalRead(PIN_LED));

            // FT232 Ekranına Başarıyla Alındığını Basıyoruz
            Serial6.print("[RX] ID:");
            Serial6.print(receivedPacket.packetID);
            Serial6.print(" LX:");
            Serial6.print(receivedPacket.LX);
            Serial6.print(" LY:");
            Serial6.print(receivedPacket.LY);
            Serial6.println();

            // Servoları oynat
            servo1.write(map(receivedPacket.LX, 0, 32767, 0, 180));
            servo2.write(map(receivedPacket.RX, 0, 32767, 0, 180));
            servo3.write(map(receivedPacket.RY, 0, 32767, 0, 180));
        }
    }

    // TELEMETRİ GÖNDERİMİ
    if (millis() - lastTelemetryTime > 1000)
    {
        if (digitalRead(LORA_AUX) == HIGH)
        {
            Serial1.print("V:");
            Serial1.print(getBatteryVoltage(), 1);
            Serial1.print("\n");

            Serial6.print("[TX Telemetry] V:");
            Serial6.print(getBatteryVoltage(), 1);
            Serial6.println("V");

            lastTelemetryTime = millis();
        }
    }
}