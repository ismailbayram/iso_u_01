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

ControlPacket controlPacket;
uint16_t packetCounter = 0;
unsigned long lastSendTime = 0;
unsigned long lastDebugTime = 0;
unsigned long bootTime = 0;
unsigned long lastCfgEchoTime = 0;
bool cfgWasWritten = false;
uint8_t cfgReg0Applied = 0xFF;
uint8_t cfgReg3Applied = 0xFF;

const uint8_t FRAME_PREAMBLE_1 = 0xAA;
const uint8_t FRAME_PREAMBLE_2 = 0x55;
const unsigned long DEBUG_PRINT_INTERVAL_MS = 200;
const unsigned long SEND_INTERVAL_MS = 20;

uint8_t computeChecksum(const uint8_t *data, size_t len)
{
  uint8_t crc = 0;
  for (size_t i = 0; i < len; i++)
  {
    crc ^= data[i];
  }
  return crc;
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
const float FILTER_COEFFICIENT = 0.35;

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

void configureLoRa()
{
  const uint8_t READ_CMD_9[] = {0xC1, 0x00, 0x09};
  const uint8_t READ_CMD_6[] = {0xC1, 0x00, 0x06};
  const uint8_t WRITE_CMD_PREFIX[] = {0xC0, 0x00, 0x09};
  const uint8_t WRITE_CMD_PREFIX_6[] = {0xC0, 0x00, 0x06};
  const uint8_t LEGACY_READ_CMD[] = {0xC1, 0xC1, 0xC1};
  const uint8_t REG0_INDEX = 3;
  const uint8_t UART_115200_BITS = (0x07 << 3);
  const uint8_t AIR_RATE_BITS = 0x07;
  const uint8_t LEGACY_AIR_RATE_MASK = 0x07;

  LoRa.begin(9600, SERIAL_8N1, PIN_RX2, PIN_TX2);
  Serial.println("[CFG] LoRa modül yapılandırması...");

  digitalWrite(LORA_M0, HIGH);
  digitalWrite(LORA_M1, HIGH);
  delay(50);

  unsigned long start = millis();
  while (digitalRead(LORA_AUX) == LOW)
  {
    if (millis() - start > 500)
    {
      Serial.println("[CFG] HATA: Modul yanit vermiyor");
      digitalWrite(LORA_M0, LOW);
      digitalWrite(LORA_M1, LOW);
      return;
    }
  }
  delay(10);

  uint8_t raw[16];
  size_t rawLen = 0;
  while (LoRa.available()) { LoRa.read(); }
  LoRa.write(READ_CMD_9, sizeof(READ_CMD_9));
  LoRa.flush();
  unsigned long waitStart = millis();
  while ((millis() - waitStart) < 300) {
    while (LoRa.available() && rawLen < sizeof(raw)) {
      raw[rawLen++] = (uint8_t)LoRa.read();
    }
    if (rawLen >= 12) {
      break;
    }
  }

  if (rawLen < 9) {
    rawLen = 0;
    while (LoRa.available()) { LoRa.read(); }
    LoRa.write(READ_CMD_6, sizeof(READ_CMD_6));
    LoRa.flush();
    waitStart = millis();
    while ((millis() - waitStart) < 300) {
      while (LoRa.available() && rawLen < sizeof(raw)) {
        raw[rawLen++] = (uint8_t)LoRa.read();
      }
      if (rawLen >= 9) {
        break;
      }
    }
  }

  if (rawLen < 6) {
    rawLen = 0;
    while (LoRa.available()) { LoRa.read(); }
    LoRa.write(LEGACY_READ_CMD, sizeof(LEGACY_READ_CMD));
    LoRa.flush();
    waitStart = millis();
    while ((millis() - waitStart) < 300) {
      while (LoRa.available() && rawLen < sizeof(raw)) {
        raw[rawLen++] = (uint8_t)LoRa.read();
      }
      if (rawLen >= 6) {
        break;
      }
    }
  }

  uint8_t regs[9];
  bool parse9 = false;
  bool parse6 = false;
  if (rawLen >= 12 && raw[0] == 0xC1 && raw[1] == 0x00 && raw[2] == 0x09)
  {
    memcpy(regs, &raw[3], 9);
    parse9 = true;
  }
  else if (rawLen >= 9 && raw[0] == 0xC1 && raw[1] == 0x00 && raw[2] == 0x06)
  {
    parse6 = true;
  }
  else if (rawLen >= 6)
  {
    parse6 = true;
  }

  if (!parse9 && !parse6)
  {
    Serial.print("[CFG] HATA: Config okunamadi, gelen byte: ");
    Serial.println((int)rawLen);
    digitalWrite(LORA_M0, LOW);
    digitalWrite(LORA_M1, LOW);
    return;
  }

  if (parse9)
  {
    Serial.print("[CFG] Mevcut regs: ");
    for (int i = 0; i < 9; i++)
    {
      if (regs[i] < 0x10)
      {
        Serial.print('0');
      }
      Serial.print(regs[i], HEX);
      Serial.print(" ");
    }
    Serial.println();
  }

  uint8_t targetReg0 = 0;
  if (parse9)
  {
    targetReg0 = (regs[REG0_INDEX] & 0xC0) | UART_115200_BITS | AIR_RATE_BITS;
    bool needsWrite = (regs[REG0_INDEX] != targetReg0);
    cfgWasWritten = false;
    if (needsWrite)
    {
      regs[REG0_INDEX] = targetReg0;

      uint8_t wcmd[12];
      memcpy(wcmd, WRITE_CMD_PREFIX, sizeof(WRITE_CMD_PREFIX));
      memcpy(&wcmd[3], regs, sizeof(regs));
      LoRa.write(wcmd, sizeof(wcmd));
      LoRa.flush();
      delay(120);
      cfgWasWritten = true;
      Serial.println("[CFG] 9-byte profil guncellendi");
    }
    else
    {
      Serial.println("[CFG] 9-byte profil zaten dogru");
    }
  }
  else
  {
    uint8_t legacy[6];
    memcpy(legacy, &raw[rawLen - 6], 6);
    targetReg0 = (uint8_t)((legacy[2] & 0xF8) | LEGACY_AIR_RATE_MASK);
    bool needsWrite = (legacy[2] != targetReg0);
    cfgWasWritten = false;
    if (needsWrite)
    {
      legacy[2] = targetReg0;
      uint8_t wcmd[] = {WRITE_CMD_PREFIX_6[0], WRITE_CMD_PREFIX_6[1], WRITE_CMD_PREFIX_6[2], legacy[0], legacy[1], legacy[2], legacy[3], legacy[4], legacy[5]};
      LoRa.write(wcmd, sizeof(wcmd));
      LoRa.flush();
      delay(120);
      cfgWasWritten = true;
      Serial.println("[CFG] 6-byte profil guncellendi (yalniz air-rate)");
    }
    else
    {
      Serial.println("[CFG] 6-byte profil zaten dogru");
    }
  }

  cfgReg0Applied = targetReg0;
  cfgReg3Applied = 0;

  while (LoRa.available())
  {
    LoRa.read();
  }

  digitalWrite(LORA_M0, LOW);
  digitalWrite(LORA_M1, LOW);
  delay(200);

  LoRa.end();
  LoRa.begin(115200, SERIAL_8N1, PIN_RX2, PIN_TX2);

  Serial.println("[CFG] Tamam: 115200 UART, hizli air-rate");
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
  configureLoRa();
  playWelcomeTone();
  delay(1000);
  setupDisplay();
  bootTime = millis();
  Serial.println("[BOOT] Setup tamamlandi");

  // TODO: setup three way commnication between STM32

  // Serial.println("Bluetooth initialization...");
  // bleGamepad.begin();
}

void loop()
{
  // 1. Telemetriyi her an kesintisiz dinle
  // while (LoRa.available())
  // {
  //   char c = LoRa.read();
  //   Serial.print(c); // STM32'den gelen "V:12.4" bilgisini bilgisayara basar
  // }

  if (millis() - lastSendTime >= SEND_INTERVAL_MS)
  {
    lastSendTime = millis();

    int rawLX = analogRead(PIN_JOY_L_X);
    int rawLY = analogRead(PIN_JOY_L_Y);
    int rawRX = analogRead(PIN_JOY_R_X);
    int rawRY = analogRead(PIN_JOY_R_Y);
    normalizeInputs(&rawLX, &rawLY, &rawRX, &rawRY);

    if (digitalRead(LORA_AUX) == HIGH)
    {
      controlPacket.packetID = packetCounter++;
      controlPacket.LX = (uint8_t)map(rawLX, 0, 32767, 0, 255);
      controlPacket.LY = (uint8_t)map(rawLY, 0, 32767, 0, 255);
      controlPacket.RX = (uint8_t)map(rawRX, 0, 32767, 0, 255);
      controlPacket.RY = (uint8_t)map(rawRY, 0, 32767, 0, 255);

      ControlFrame frame;
      frame.preamble1 = FRAME_PREAMBLE_1;
      frame.preamble2 = FRAME_PREAMBLE_2;
      frame.payload = controlPacket;
      frame.checksum = computeChecksum((uint8_t *)&frame.payload, sizeof(ControlPacket));

      LoRa.write((uint8_t *)&frame, sizeof(ControlFrame));
    }

    if (millis() - lastDebugTime >= DEBUG_PRINT_INTERVAL_MS)
    {
      lastDebugTime = millis();
      Serial.print("Gonderilen ID: ");
      Serial.println(controlPacket.packetID);
    }
  }

  if ((millis() - bootTime) < 12000 && (millis() - lastCfgEchoTime) >= 2000)
  {
    lastCfgEchoTime = millis();
    Serial.print("[CFG SNAP] REG0=0x");
    if (cfgReg0Applied < 0x10)
      Serial.print('0');
    Serial.print(cfgReg0Applied, HEX);
    Serial.print(" REG3=0x");
    if (cfgReg3Applied < 0x10)
      Serial.print('0');
    Serial.print(cfgReg3Applied, HEX);
    Serial.print(" write=");
    Serial.println(cfgWasWritten ? "yes" : "no");
  }
}
