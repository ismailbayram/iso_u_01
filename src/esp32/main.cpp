#include <Arduino.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <LoRa_E22.h>
#include <Wire.h>
#include "radio_protocol.h"

#ifndef USE_GPS
#define USE_GPS 0
#endif
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
LoRa_E22 e22(&LoRa, LORA_AUX, LORA_M0, LORA_M1, UART_BPS_RATE_9600);
// BleGamepad bleGamepad("ISO U1 Gamepad", "ISO", 100);

using radio::ControlPacket;
using radio::TelemetryPacket;
using radio::TelemetryRequestPacket;

ControlPacket controlPacket;
uint16_t packetCounter = 0;
unsigned long lastSendTime = 0;
unsigned long lastDebugTime = 0;
unsigned long bootTime = 0;
unsigned long lastBootEchoTime = 0;
bool loraSetupDone = false;
bool loraSetupChanged = false;
unsigned long lastTelemetryPrintTime = 0;

uint8_t rxPacketType = 0;
uint8_t rxPayloadLength = 0;
uint8_t rxPayloadIndex = 0;
uint8_t rxParserState = 0;
uint8_t rxPayloadBuffer[64];
TelemetryPacket lastTelemetry;

const unsigned long DEBUG_PRINT_INTERVAL_MS = 20;
const unsigned long SEND_INTERVAL_MS = 20;
const unsigned long TELEMETRY_REQUEST_INTERVAL_MS = 1000;
const unsigned long TELEMETRY_RX_GUARD_MS = 250;
unsigned long lastTelemetryRequestTime = 0;
unsigned long telemetryGuardUntil = 0;
uint8_t telemetryReqSeq = 0;
uint32_t telemetryReqSentCount = 0;
uint32_t telemetryRxCount = 0;

#if USE_GPS
const uint8_t MIN_SATS_REQUIRED = 4;
const unsigned long LOW_SAT_BEEP_INTERVAL_MS = 2000;
unsigned long lastLowSatBeepTime = 0;
#endif
const unsigned long STATUS_DISPLAY_INTERVAL_MS = 500;
const unsigned long TELEMETRY_LOST_TIMEOUT_MS = 3000;
const unsigned long LINK_LOST_BEEP_INTERVAL_MS = 2000;
unsigned long lastStatusDisplayTime = 0;
unsigned long lastTelemetryRxTime = 0;
unsigned long lastLinkLostBeepTime = 0;

// Ilk gecerli basinc olcumu referans alinip irtifa ona gore hesaplanir, boylece
// kalkis noktasi sifir olur. Mutlak irtifa icin deniz seviyesi basinci gerekirdi.
uint32_t baselinePressurePa = 0;
float relativeAltitudeM = 0.0f;

float pressureToAltitude(uint32_t pressurePa, uint32_t referencePa)
{
  if (pressurePa == 0 || referencePa == 0)
  {
    return 0.0f;
  }
  return 44330.0f * (1.0f - powf((float)pressurePa / (float)referencePa, 0.1902949f));
}

void sendFrame(uint8_t packetType, const void *payload, uint8_t payloadLength)
{
  const uint8_t *payloadBytes = (const uint8_t *)payload;
  LoRa.write(radio::PREAMBLE_1);
  LoRa.write(radio::PREAMBLE_2);
  LoRa.write(packetType);
  LoRa.write(payloadLength);
  LoRa.write(payloadBytes, payloadLength);
  LoRa.write(radio::computeFrameChecksum(packetType, payloadLength, payloadBytes));
}

bool parseIncomingLoRaByte(uint8_t b)
{
  switch (rxParserState)
  {
  case 0:
    if (b == radio::PREAMBLE_1)
      rxParserState = 1;
    break;
  case 1:
    if (b == radio::PREAMBLE_2)
    {
      rxParserState = 2;
    }
    else
    {
      rxParserState = (b == radio::PREAMBLE_1) ? 1 : 0;
    }
    break;
  case 2:
    rxPacketType = b;
    rxParserState = 3;
    break;
  case 3:
    rxPayloadLength = b;
    rxPayloadIndex = 0;
    if (rxPayloadLength > sizeof(rxPayloadBuffer))
    {
      rxParserState = 0;
    }
    else
    {
      rxParserState = 4;
    }
    break;
  case 4:
    rxPayloadBuffer[rxPayloadIndex++] = b;
    if (rxPayloadIndex >= rxPayloadLength)
    {
      rxParserState = 5;
    }
    break;
  case 5:
  {
    uint8_t expected = radio::computeFrameChecksum(rxPacketType, rxPayloadLength, rxPayloadBuffer);
    rxParserState = 0;
    if (expected == b && rxPacketType == radio::PACKET_TYPE_TELEMETRY && rxPayloadLength == sizeof(TelemetryPacket))
    {
      memcpy(&lastTelemetry, rxPayloadBuffer, sizeof(TelemetryPacket));
      telemetryRxCount++;
      lastTelemetryRxTime = millis();
      if (lastTelemetry.pressurePa != 0)
      {
        if (baselinePressurePa == 0)
        {
          baselinePressurePa = lastTelemetry.pressurePa;
        }
        relativeAltitudeM = pressureToAltitude(lastTelemetry.pressurePa, baselinePressurePa);
      }
      return true;
    }
    break;
  }
  default:
    rxParserState = 0;
    break;
  }
  return false;
}

void setupLoRaWithLibrary()
{
  Serial.println("[E22] setup basliyor...");

  if (!e22.begin())
  {
    Serial.println("[E22] begin basarisiz");
    loraSetupDone = false;
    return;
  }

  ResponseStructContainer c = e22.getConfiguration();
  if (c.status.code != E22_SUCCESS)
  {
    Serial.print("[E22] config okunamadi: ");
    Serial.println(c.status.getResponseDescription());
    c.close();
    loraSetupDone = false;
    return;
  }

  Configuration cfg = *(Configuration *)c.data;
  c.close();

  bool changed = false;

  if (cfg.SPED.uartBaudRate != UART_BPS_9600)
  {
    cfg.SPED.uartBaudRate = UART_BPS_9600;
    changed = true;
  }

  if (cfg.SPED.airDataRate != AIR_DATA_RATE_110_384)
  {
    cfg.SPED.airDataRate = AIR_DATA_RATE_110_384;
    changed = true;
  }

  if (cfg.TRANSMISSION_MODE.WORTransceiverControl != WOR_RECEIVER)
  {
    cfg.TRANSMISSION_MODE.WORTransceiverControl = WOR_RECEIVER;
    changed = true;
  }

  if (changed)
  {
    ResponseStatus rs = e22.setConfiguration(cfg, WRITE_CFG_PWR_DWN_SAVE);
    Serial.print("[E22] kaydet: ");
    Serial.println(rs.getResponseDescription());
    loraSetupChanged = true;
  }
  else
  {
    Serial.println("[E22] ayar zaten uygun");
    loraSetupChanged = false;
  }

  e22.setMode(MODE_0_NORMAL);
  loraSetupDone = true;
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

void printTemperature(int16_t centiC)
{
  if (centiC == INT16_MIN)
  {
    display.print("--");
  }
  else
  {
    display.print(centiC / 100.0f, 1);
  }
}

void updateStatusDisplay()
{
  if (millis() - lastStatusDisplayTime < STATUS_DISPLAY_INTERVAL_MS)
  {
    return;
  }
  lastStatusDisplayTime = millis();

  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);

#if USE_GPS
  bool lowSats = lastTelemetry.gpsSats < MIN_SATS_REQUIRED;

  display.print("Uydu: ");
  display.println(lastTelemetry.gpsSats);
  if (lowSats)
  {
    display.println("YETERLI UYDU");
    display.println("SAYISINA ULASILAMADI");
  }
  else
  {
    display.println("GPS OK");
  }
  display.display();

  if (lowSats && millis() - lastLowSatBeepTime >= LOW_SAT_BEEP_INTERVAL_MS)
  {
    lastLowSatBeepTime = millis();
    tone(PIN_BUZZER, 330, 150);
  }
#else
  // GPS bu asamada kullanilmiyor; ekranda telemetri ve link durumu gosteriliyor.
  bool linkLost = (lastTelemetryRxTime == 0) ||
                  (millis() - lastTelemetryRxTime > TELEMETRY_LOST_TIMEOUT_MS);

  if (linkLost)
  {
    display.println("TELEMETRI YOK");
    display.println("Baglanti bekleniyor");
  }
  else
  {
    display.print("Batarya: ");
    display.print(lastTelemetry.voltageMv / 1000.0f, 2);
    display.println("V");
    display.print("Tb ");
    printTemperature(lastTelemetry.battTempCentiC);
    display.print(" Tesc ");
    printTemperature(lastTelemetry.escTempCentiC);
    display.println("C");
    display.print("Irtifa: ");
    if (lastTelemetry.pressurePa == 0)
    {
      display.println("--");
    }
    else
    {
      display.print(relativeAltitudeM, 1);
      display.println("m");
    }
    display.print("Link OK  #");
    display.println(telemetryRxCount);
  }
  display.display();

  if (linkLost && millis() - lastLinkLostBeepTime >= LINK_LOST_BEEP_INTERVAL_MS)
  {
    lastLinkLostBeepTime = millis();
    tone(PIN_BUZZER, 330, 150);
  }
#endif
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

  *LX = (int)filteredLX;
  *LY = 4095 - (int)filteredLY; // Invert LY for throttle
  *RX = (int)filteredRX;
  *RY = (int)filteredRY;

  const int center = 2048;
  const int deadband = 18;
  if (abs(*LX - center) < deadband)
    *LX = center;
  if (abs(*RX - center) < deadband)
    *RX = center;
  if (abs(*RY - center) < deadband)
    *RY = center;

  *LX = constrain(*LX, 0, 4095);
  *LY = constrain(*LY, 0, 4095);
  *RX = constrain(*RX, 0, 4095);
  *RY = constrain(*RY, 0, 4095);
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

  // Filtreleri sabit orta noktadan degil, gercek stick pozisyonundan baslat.
  // Aksi halde ilk paketlerde throttle gercek deger yakinsayana kadar
  // yanlis (orta seviye) bir gaz komutu gonderilir.
  filteredLX = analogRead(PIN_JOY_L_X);
  filteredLY = analogRead(PIN_JOY_L_Y);
  filteredRX = analogRead(PIN_JOY_R_X);
  filteredRY = analogRead(PIN_JOY_R_Y);

  Serial.begin(115200);
  Serial.println("[FW] esp32-telemetry-parser-v2");
  Serial.print("[DBG] TEL_STRUCT_SIZE=");
  Serial.println(sizeof(TelemetryPacket));
  setupLoRaWithLibrary();
  bootTime = millis();

  playWelcomeTone();
  delay(1000);
  setupDisplay();

  // TODO: setup three way commnication between STM32

  // Serial.println("Bluetooth initialization...");
  // bleGamepad.begin();
}

void loop()
{
  while (LoRa.available())
  {
    if (parseIncomingLoRaByte((uint8_t)LoRa.read()))
    {
      if (millis() - lastTelemetryPrintTime > 200)
      {
        lastTelemetryPrintTime = millis();
        Serial.print("[TEL] V=");
        Serial.print(lastTelemetry.voltageMv / 1000.0f, 2);
        Serial.print(" Tbatt=");
        if (lastTelemetry.battTempCentiC == INT16_MIN)
        {
          Serial.print("NA");
        }
        else
        {
          Serial.print(lastTelemetry.battTempCentiC / 100.0f, 1);
          Serial.print("C");
        }
        Serial.print(" Tesc=");
        if (lastTelemetry.escTempCentiC == INT16_MIN)
        {
          Serial.print("NA");
        }
        else
        {
          Serial.print(lastTelemetry.escTempCentiC / 100.0f, 1);
          Serial.print("C");
        }
        Serial.print(" acc=");
        Serial.print(lastTelemetry.mpuAx);
        Serial.print(",");
        Serial.print(lastTelemetry.mpuAy);
        Serial.print(",");
        Serial.print(lastTelemetry.mpuAz);
        Serial.print(" gyr=");
        Serial.print(lastTelemetry.mpuGx);
        Serial.print(",");
        Serial.print(lastTelemetry.mpuGy);
        Serial.print(",");
        Serial.print(lastTelemetry.mpuGz);
        Serial.print(" hdg=");
        Serial.print(lastTelemetry.compassHeading / 10.0f, 1);
        Serial.print(" baro=");
        if (lastTelemetry.pressurePa == 0)
        {
          Serial.print("NA");
        }
        else
        {
          Serial.print(lastTelemetry.pressurePa);
          Serial.print("Pa alt=");
          Serial.print(relativeAltitudeM, 1);
          Serial.print("m Tbaro=");
          Serial.print(lastTelemetry.baroTempCentiC / 100.0f, 1);
          Serial.print("C");
        }
#if USE_GPS
        Serial.print(" GPSfix=");
        Serial.print(lastTelemetry.gpsFix);
        Serial.print(" sats=");
        Serial.print(lastTelemetry.gpsSats);
        Serial.print(" lat=");
        Serial.print(lastTelemetry.gpsLatE7 / 10000000.0, 6);
        Serial.print(" lon=");
        Serial.print(lastTelemetry.gpsLonE7 / 10000000.0, 6);
#endif
        Serial.println();
      }
    }
  }

  updateStatusDisplay();

  if (millis() - lastTelemetryRequestTime >= TELEMETRY_REQUEST_INTERVAL_MS)
  {
    TelemetryRequestPacket req;
    req.sequence = telemetryReqSeq++;
    sendFrame(radio::PACKET_TYPE_TELEMETRY_REQ, &req, sizeof(TelemetryRequestPacket));
    telemetryReqSentCount++;
    lastTelemetryRequestTime = millis();
    telemetryGuardUntil = millis() + TELEMETRY_RX_GUARD_MS;
  }

  if (millis() - lastSendTime >= SEND_INTERVAL_MS)
  {
    if (millis() < telemetryGuardUntil)
    {
      lastSendTime = millis();
      return;
    }

    lastSendTime = millis();

    int rawLX = analogRead(PIN_JOY_L_X);
    int rawLY = analogRead(PIN_JOY_L_Y);
    int rawRX = analogRead(PIN_JOY_R_X);
    int rawRY = analogRead(PIN_JOY_R_Y);
    normalizeInputs(&rawLX, &rawLY, &rawRX, &rawRY);

    if (digitalRead(LORA_AUX) == HIGH)
    {
      controlPacket.packetID = packetCounter++;
      controlPacket.LX = (uint16_t)rawLX;
      controlPacket.LY = (uint16_t)rawLY;
      controlPacket.RX = (uint16_t)rawRX;
      controlPacket.RY = (uint16_t)rawRY;

      sendFrame(radio::PACKET_TYPE_CONTROL, &controlPacket, sizeof(ControlPacket));

      if (millis() - lastDebugTime >= DEBUG_PRINT_INTERVAL_MS)
      {
        lastDebugTime = millis();
      }
    }
  }
}
