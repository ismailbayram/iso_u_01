#include <SPI.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define SCREEN_WIDTH 128 // OLED ekran genişliği (piksel)
#define SCREEN_HEIGHT 32 // OLED ekran yüksekliği (piksel)

// I2C için reset pini olmadığından -1 bırakıyoruz
#define OLED_RESET -1
// 0x3C genelde bu ekranların fabrikasyon I2C adresidir. Çalışmazsa 0x3D dene.
#define SCREEN_ADDRESS 0x3C

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

int sayac = 0;

void setup()
{
    Serial.begin(115200);

    // I2C pinlerini (SDA=21, SCL=22) burada zorla başlatıyoruz
    Wire.begin(21, 22);

    // Ekranı başlatıyoruz
    if (!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS))
    {
        Serial.println(F("Ekran baglantisi basarisiz!"));
        // for(;;);  <-- Bunu yorum satırı yapalım ki kod kilitlenmesin, akmaya çalışsın
    }

    display.clearDisplay();
    display.display();
}

void loop()
{
    // Her döngü başında ekranı temizle ki eski yazılar üst üste binmesin
    display.clearDisplay();

    // --- Başlık Kısmı ---
    display.setTextSize(2);              // Yazı boyutu (1 küçük, 2 orta)
    display.setTextColor(SSD1306_WHITE); // Yazı rengi beyaz
    display.setCursor(0, 0);             // X=15, Y=0 koordinatına git
    display.println("CANIM KARIM");

    // Başlığın altına şık bir çizgi çekelim
    display.drawFastHLine(0, 15, 128, SSD1306_WHITE);

    // Hazırladığımız tüm bu çizimleri ekrana fiziksel olarak bas
    display.display();

    // Sayacı artır ve 1 saniye bekle
    sayac++;
    delay(1000);
}