#include <TinyGPS++.h>

// GPS objemizi tanımlıyoruz
TinyGPSPlus gps;

// ESP32'nin donanımsal Seri Port 2'sini (HardwareSerial) kullanacağız
// Pin 16 = RX2, Pin 17 = TX2
HardwareSerial gpsSerial(2);

void ekranaYazdir()
{
  Serial.print("Konum: ");
  if (gps.location.isValid())
  {
    Serial.print(gps.location.lat(), 6); // Enlem
    Serial.print(" , ");
    Serial.print(gps.location.lng(), 6); // Boylam
  }
  else
  {
    Serial.print("UYDU ARANIYOR...");
  }

  Serial.print(" | Yükseklik: ");
  if (gps.altitude.isValid())
  {
    Serial.print(gps.altitude.meters());
    Serial.print("m");
  }
  else
  {
    Serial.print("---");
  }

  Serial.print(" | Hız: ");
  if (gps.speed.isValid())
  {
    Serial.print(gps.speed.kmph());
    Serial.print(" km/h");
  }
  else
  {
    Serial.print("---");
  }

  Serial.print(" | Uydu Sayısı: ");
  Serial.println(gps.satellites.value());
}

void setup()
{
  // Bilgisayar ile haberleşme hızı
  Serial.begin(115200);

  // GPS modülü ile haberleşme hızı (NEO-7M fabrikasyon olarak 9600 baud kullanır)
  gpsSerial.begin(9600, SERIAL_8N1, 16, 17);

  Serial.println("GPS Modülü Başlatılıyor... Lütfen bekleyin.");
}

void loop()
{
  // GPS'ten veri geldikçe TinyGPS kütüphanesine besliyoruz
  while (gpsSerial.available() > 0)
  {
    if (gps.encode(gpsSerial.read()))
    {
      ekranaYazdir();
    }
  }

  // Eğer 5 saniye boyunca hiç veri gelmiyorsa bağlantıyı kontrol et uyarısı verelim
  if (millis() > 5000 && gps.charsProcessed() < 10)
  {
    Serial.println("Hata: GPS modülü bulunamadı, kabloları kontrol edin!");
    delay(2000);
  }
}
