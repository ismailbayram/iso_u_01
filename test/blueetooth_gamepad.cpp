#include <Arduino.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Wire.h>
#include <BleGamepad.h>

// PIN Definitions
#define PIN_BUZZER 25
#define PIN_JOY_L_X 36
#define PIN_JOY_L_Y 39
#define PIN_JOY_R_X 34
#define PIN_JOY_R_Y 35

// OLED Display Definitions
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 32
#define OLED_RESET -1
#define SCREEN_ADDRESS 0x3C

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// Bluetooth Gamepad tanımlaması (İsim, Üretici)
BleGamepad bleGamepad("ISO U1 Gamepad", "ISO", 100);
bool baglantiDurumu = false;

void playWelcomeTone()
{
    tone(PIN_BUZZER, 659, 150);
    delay(150);
    tone(PIN_BUZZER, 830, 150);
    delay(150);
    tone(PIN_BUZZER, 987, 300);
    delay(300);
    noTone(PIN_BUZZER);
}

void playErrorTone()
{
    tone(PIN_BUZZER, 330, 200);
    delay(200);
    noTone(PIN_BUZZER);
}

void setupDisplay()
{
    Wire.begin(21, 22);
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

void ekraniGuncelle(String mesaj)
{
    display.clearDisplay();
    display.setTextSize(1);
    display.setCursor(0, 0);
    display.println("--- ISO U1 RC ---");
    display.setCursor(0, 16);
    display.print("Gamepad: ");
    display.println(mesaj);
    display.display();
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

    // Kablosuz Gamepad'i başlatıyoruz
    Serial.println("Bluetooth Gamepad Başlatılıyor...");
    bleGamepad.begin();
}

static float filtrelileLx = 2048;
static float filtrelileLy = 2048;
static float filtrelileRx = 2048;
static float filtrelileRy = 2048;
const float FILTRE_KATSAYISI = 0.15; // 0.1 daha fazla filtreleme, 0.5 daha az filtreleme

void loop()
{
    int rawLx = analogRead(PIN_JOY_L_X);
    int rawLy = analogRead(PIN_JOY_L_Y);
    int rawRx = analogRead(PIN_JOY_R_X);
    int rawRy = analogRead(PIN_JOY_R_Y);

    filtrelileLx = (rawLx * FILTRE_KATSAYISI) + (filtrelileLx * (1.0 - FILTRE_KATSAYISI));
    filtrelileLy = (rawLy * FILTRE_KATSAYISI) + (filtrelileLy * (1.0 - FILTRE_KATSAYISI));
    filtrelileRx = (rawRx * FILTRE_KATSAYISI) + (filtrelileRx * (1.0 - FILTRE_KATSAYISI));
    filtrelileRy = (rawRy * FILTRE_KATSAYISI) + (filtrelileRy * (1.0 - FILTRE_KATSAYISI));

    // 1. Ham değerleri önce 0-32767 aralığına çekiyoruz
    int mapLx = map(filtrelileLx, 0, 4095, 0, 32767);
    int mapLy = map(4095 - filtrelileLy, 0, 4095, 0, 32767); // Gaz kolu tersleme dahil
    int mapRx = map(filtrelileRx, 0, 4095, 0, 32767);
    int mapRy = map(filtrelileRy, 0, 4095, 0, 32767);

    // 2. Senin Kumandana Özel Yaylı Kolların Orta Noktaları
    int LX_ORTA = 13800;
    int RX_ORTA = 14400;
    int RY_ORTA = 14200;

    int gameLx, gameLy, gameRx, gameRy;

    // --- LX KALİBRASYONU ---
    if (mapLx <= LX_ORTA)
    {
        gameLx = map(mapLx, 0, LX_ORTA, 0, 16384);
    }
    else
    {
        gameLx = map(mapLx, LX_ORTA, 32767, 16384, 32767);
    }

    // --- LY (GAZ) KALİBRASYONU: Bozuk olmadığı için doğrudan eşitliyoruz ---
    gameLy = mapLy;

    // --- RX KALİBRASYONU ---
    if (mapRx <= RX_ORTA)
    {
        gameRx = map(mapRx, 0, RX_ORTA, 0, 16384);
    }
    else
    {
        gameRx = map(mapRx, RX_ORTA, 32767, 16384, 32767);
    }

    // --- RY KALİBRASYONU ---
    if (mapRy <= RY_ORTA)
    {
        gameRy = map(mapRy, 0, RY_ORTA, 0, 16384);
    }
    else
    {
        gameRy = map(mapRy, RY_ORTA, 32767, 16384, 32767);
    }

    if (gameLx > 16200 && gameLx < 16500)
        gameLx = 16384;
    if (gameRx > 16200 && gameRx < 16500)
        gameRx = 16384;
    if (gameRy > 16200 && gameRy < 16500)
        gameRy = 16384;

    // Taşma korumaları
    gameLx = constrain(gameLx, 0, 32767);
    gameLy = constrain(gameLy, 0, 32767);
    gameRx = constrain(gameRx, 0, 32767);
    gameRy = constrain(gameRy, 0, 32767);

    // 4. Bluetooth Bağlantı Kontrolü
    if (bleGamepad.isConnected())
    {
        if (!baglantiDurumu)
        {
            baglantiDurumu = true;
            ekraniGuncelle("ONLINE (Hassas)");
            tone(PIN_BUZZER, 880, 100);
        }

        // Eksenleri Mac'e gönder
        bleGamepad.setLeftThumb(gameLx, gameLy);
        bleGamepad.setRightThumb(gameRx, gameRy);
        bleGamepad.sendReport();
        Serial.print("LX");
        Serial.print(gameLx);
        Serial.print(" | LY");
        Serial.print(gameLy);
        Serial.print(" | RX");
        Serial.print(gameRx);
        Serial.print(" | RY");
        Serial.print(gameRy);
        Serial.println();
    }
    else
    {
        if (baglantiDurumu || display.getCursorY() == 0)
        {
            baglantiDurumu = false;
            ekraniGuncelle("Eslenme Bekliyor");
        }
    }

    delay(15);
}