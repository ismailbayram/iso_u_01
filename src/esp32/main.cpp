#include <Arduino.h>

const int STM32_RX_PIN = 16; // ESP32 receives STM32 TX here
const int STM32_TX_PIN = 17; // ESP32 transmits to STM32 RX here
const int BAUD_RATE = 115200;

void setup()
{
  Serial.begin(BAUD_RATE);
  while (!Serial) {
    delay(10);
  }
  Serial.println("ESP32 serial bridge ready");

  Serial2.begin(BAUD_RATE, SERIAL_8N1, STM32_RX_PIN, STM32_TX_PIN);
  Serial.println("Serial2 started: RX=GPIO16, TX=GPIO17");
}

void loop()
{
  while (Serial2.available()) {
    Serial.write(Serial2.read());
  }

  while (Serial.available()) {
    Serial2.write(Serial.read());
  }
}
