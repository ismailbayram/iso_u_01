#include <Arduino.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Wire.h>
// #include <BleGamepad.h>

// PIN Definitions
#define PIN_BUZZER 25

#define PIN_JOY_L_X 36
#define PIN_JOY_L_Y 39
#define PIN_JOY_R_X 34
#define PIN_JOY_R_Y 35

#define PIN_RX2 16
#define PIN_TX2 17

#define LORA_M0 18
#define LORA_M1 5
#define LORA_AUX 4

// OLED Display Definitions
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 32
#define OLED_RESET -1       // Set -1 because the OLED display doesn't have a reset pin
#define SCREEN_ADDRESS 0x3C // I2C Address, 0x3D or 0x3C

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
HardwareSerial LoRa(2);
// BleGamepad bleGamepad("ISO U1 Gamepad", "ISO", 100);

struct __attribute__((packed)) ControlPacket
{
  uint16_t packetID;

  uint16_t LX;
  uint16_t LY;
  uint16_t RX;
  uint16_t RY;
};

ControlPacket controlPacket;
uint32_t packetCounter = 0;

bool waitLoRaReady(unsigned long timeout)
{
  unsigned long start = millis();
  while (digitalRead(LORA_AUX) == LOW)
  {
    if (millis() - start > timeout)
      return false;
    yield();
  }
  return true;
}

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

static float filteredLX = 2048;
static float filteredLY = 2048;
static float filteredRX = 2048;
static float filteredRY = 2048;
const float FILTER_COEFFICIENT = 0.15;

void normalizeInputs(int *LX, int *LY, int *RX, int *RY)
{
  filteredLX = (*LX * FILTER_COEFFICIENT) + (filteredLX * (1.0 - FILTER_COEFFICIENT));
  filteredLY = (*LY * FILTER_COEFFICIENT) + (filteredLY * (1.0 - FILTER_COEFFICIENT));
  filteredRX = (*RX * FILTER_COEFFICIENT) + (filteredRX * (1.0 - FILTER_COEFFICIENT));
  filteredRY = (*RY * FILTER_COEFFICIENT) + (filteredRY * (1.0 - FILTER_COEFFICIENT));

  *LX = map(filteredLX, 0, 4095, 0, 32767);
  *LY = map(4095 - filteredLY, 0, 4095, 0, 32767); // Invert LY for throttle
  *RX = map(filteredRX, 0, 4095, 0, 32767);
  *RY = map(filteredRY, 0, 4095, 0, 32767);

  int LX_CENTER = 13800;
  int RX_CENTER = 14400;
  int RY_CENTER = 14200;

  if (*LX <= LX_CENTER)
  {
    *LX = map(*LX, 0, LX_CENTER, 0, 16384);
  }
  else
  {
    *LX = map(*LX, LX_CENTER, 32767, 16384, 32767);
  }

  if (*RX <= RX_CENTER)
  {
    *RX = map(*RX, 0, RX_CENTER, 0, 16384);
  }
  else
  {
    *RX = map(*RX, RX_CENTER, 32767, 16384, 32767);
  }

  if (*RY <= RY_CENTER)
  {
    *RY = map(*RY, 0, RY_CENTER, 0, 16384);
  }
  else
  {
    *RY = map(*RY, RY_CENTER, 32767, 16384, 32767);
  }

  if (*LX > 16200 && *LX < 16500)
    *LX = 16384;
  if (*RX > 16200 && *RX < 16500)
    *RX = 16384;
  if (*RY > 16200 && *RY < 16500)
    *RY = 16384;

  *LX = constrain(*LX, 0, 32767);
  *LY = constrain(*LY, 0, 32767);
  *RX = constrain(*RX, 0, 32767);
  *RY = constrain(*RY, 0, 32767);
}

void setup()
{
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_JOY_L_X, INPUT);
  pinMode(PIN_JOY_L_Y, INPUT);
  pinMode(PIN_JOY_R_X, INPUT);
  pinMode(PIN_JOY_R_Y, INPUT);

  pinMode(LORA_M0, OUTPUT);
  pinMode(LORA_M1, OUTPUT);
  pinMode(LORA_AUX, INPUT);

  digitalWrite(LORA_M0, LOW);
  digitalWrite(LORA_M1, LOW);

  delay(200);

  Serial.begin(115200);
  LoRa.begin(9600, SERIAL_8N1, PIN_RX2, PIN_TX2);
  playWelcomeTone();
  delay(1000);
  setupDisplay();

  // TODO: setup three way commnication between STM32

  // Serial.println("Bluetooth initialization...");
  // bleGamepad.begin();
}

void loop()
{
  int LX = analogRead(PIN_JOY_L_X);
  int LY = analogRead(PIN_JOY_L_Y);
  int RX = analogRead(PIN_JOY_R_X);
  int RY = analogRead(PIN_JOY_R_Y);
  normalizeInputs(&LX, &LY, &RX, &RY);

  // TODO: use CRC16 or CRC32 for packet integrity check

  controlPacket.packetID = packetCounter++;
  controlPacket.LX = LX;
  controlPacket.LY = LY;
  controlPacket.RX = RX;
  controlPacket.RY = RY;

  // wait for 10 milliseconds to listen for any incoming data from the STM32
  unsigned long listenStart = millis();
  while (millis() - listenStart < 10)
  {
    if (LoRa.available())
    {
      char c = LoRa.read();
      Serial.print(c);
    }
  }

  LoRa.write((uint8_t *)&controlPacket, sizeof(controlPacket));

  // if (bleGamepad.isConnected())
  // {
  // bleGamepad.setLeftThumb(LX, LY);
  // bleGamepad.setRightThumb(RX, RY);
  // bleGamepad.sendReport();

  Serial.print("LX");
  Serial.print(LX);
  Serial.print(" | LY");
  Serial.print(LY);
  Serial.print(" | RX");
  Serial.print(RX);
  Serial.print(" | RY");
  Serial.print(RY);
  Serial.println();
  // }
  // else
  // {
  //   Serial.println("Bluetooth not connected.");
  // }

  delay(20); // Small delay to avoid flooding the serial output
}
