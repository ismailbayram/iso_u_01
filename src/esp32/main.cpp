#include <Arduino.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Wire.h>

// PIN Definitions
#define PIN_BUZZER 25
#define PIN_JOY_L_X 36
#define PIN_JOY_L_Y 39
#define PIN_JOY_R_X 34
#define PIN_JOY_R_Y 35

// OLED Display Definitions
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 32
#define OLED_RESET -1       // Set -1 because the OLED display doesn't have a reset pin
#define SCREEN_ADDRESS 0x3C // I2C Address, 0x3D or 0x3C

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

void playWelcomeTone()
{
  tone(PIN_BUZZER, 659, 150); // Play E5 (659 Hz) for 150 ms
  delay(150);                 // Wait for the tone to finish
  tone(PIN_BUZZER, 830, 150); // Play F5 (830 Hz) for 150 ms
  delay(150);                 // Wait for the tone to finish
  tone(PIN_BUZZER, 987, 300); // Play G5 (987 Hz) for 300 ms
  delay(300);                 // Wait for the tone to finish
  noTone(PIN_BUZZER);         // Turn off the buzzer
}

void playErrorTone()
{
  tone(PIN_BUZZER, 330, 200); // Play E4 (330 Hz) for 200 ms
  delay(200);                 // Wait for the tone to finish
  noTone(PIN_BUZZER);         // Turn off the buzzer
}

void setupDisplay()
{
  Wire.begin(21, 22); // Initialize I2C with SDA=21 and SCL=22
  if (!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS))
  {
    Serial.println(F("OLED ekran baglantisi basarisiz!"));
    playErrorTone();
    // for(;;); // Don't lock up the code, just keep trying
  }
  else
  {
    display.clearDisplay();
    display.setTextSize(2);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);
    display.println("ISO U1'e");
    display.println("Hos Geldin!");
    display.display();
  }
}

void setup()
{
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_JOY_L_X, INPUT);
  pinMode(PIN_JOY_L_Y, INPUT);
  pinMode(PIN_JOY_R_X, INPUT);
  pinMode(PIN_JOY_R_Y, INPUT);

  Serial.begin(115200);
  playWelcomeTone();
  delay(1000);
  setupDisplay();
}

void loop()
{
  // Read joystick values
  int joyLx = analogRead(PIN_JOY_L_X);
  int joyLy = analogRead(PIN_JOY_L_Y);
  joyLy = 4095 - joyLy; // Invert Y-axis for left joystick
  int joyRx = analogRead(PIN_JOY_R_X);
  int joyRy = analogRead(PIN_JOY_R_Y);

  // Print joystick values to Serial Monitor
  Serial.print(joyLx);
  Serial.print(",");
  Serial.print(joyLy);
  Serial.print(",");
  Serial.print(joyRx);
  Serial.print(",");
  Serial.println(joyRy);

  delay(20); // Delay to avoid flooding the serial monitor
}
