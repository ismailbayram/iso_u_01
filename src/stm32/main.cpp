#include <Arduino.h>

const int ledPin = LED_BUILTIN;
const unsigned long interval = 500;
unsigned long previousMillis = 0;
bool ledState = LOW;

void setup()
{
    pinMode(ledPin, OUTPUT);
    digitalWrite(ledPin, ledState);
}

void loop()
{
    unsigned long currentMillis = millis();

    if (currentMillis - previousMillis >= interval)
    {
        previousMillis = currentMillis;
        ledState = !ledState;
        digitalWrite(ledPin, ledState);
    }
}
