#include <Arduino.h>

const int ledPin = 2; // ESP32 built-in LED is usually GPIO 2 on esp32dev
const unsigned long interval = 500;
unsigned long previousMillis = 0;

void setup()
{
  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, LOW);
}

void loop()
{
  unsigned long currentMillis = millis();

  if (currentMillis - previousMillis >= interval)
  {
    previousMillis = currentMillis;
    digitalWrite(ledPin, !digitalRead(ledPin));
  }
}