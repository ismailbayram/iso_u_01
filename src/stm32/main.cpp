#include <Arduino.h>
#include <Servo.h>

Servo myESC;
const int escPin = PA0;  // ESC Beyaz Kablo (5V Tolerant)
const int ledPin = PC13; // Blackpill üzerindeki dahili Mavi LED (Gerekirse PB12 veya PC13 yapabilirsin)

const int MIN_GAZ = 1100;
const int MAKS_GAZ = 1940;

void setup()
{
    // LED ve ESC Pin Ayarları
    pinMode(ledPin, OUTPUT);
    pinMode(escPin, OUTPUT_OPEN_DRAIN); // 5V sinyal sürmek için Open-Drain modu

    // 1. HAZIRLIK AŞAMASI: Hızlı hızlı LED kırp (5 Saniye Geri Sayım)
    // Bu süreçte ESC'ye hiçbir sinyal gitmez, sadece seni uyarır.
    for (int i = 0; i < 25; i++)
    {
        digitalWrite(ledPin, LOW); // Blackpill'de LOW led'i yakar
        delay(100);
        digitalWrite(ledPin, HIGH); // HIGH led'i söndürür
        delay(100);
    }

    // STM32 Dahili Servo donanımını başlat
    myESC.attach(escPin, MIN_GAZ, MAKS_GAZ);

    // 2. ADIM: Maksimum gaz basılıyor ve LED SABİT yanıyor
    // LED yandığı an LİPO PİLİ TAKMALISIN!
    digitalWrite(ledPin, LOW); // LED Sabit Yanık (Maksimum gaz başladı)
    myESC.writeMicroseconds(MAKS_GAZ);

    delay(4000); // Pili takman ve ESC'nin "Bip-Bip" demesi için gereken süre

    // 3. ADIM: Minimum gaz basılıyor ve LED SÖNÜYOR
    myESC.writeMicroseconds(MIN_GAZ);
    digitalWrite(ledPin, HIGH); // LED Söndü (Minimum gaza düşüldü)

    delay(4000); // ESC'nin hafızaya kaydedip uzun "Biiiiip" sesini vermesi için bekleme
}

void loop()
{
    // Kalibrasyon bitti. Motor 4 saniye dönecek, 4 saniye duracak.
    // Motor dönerken dahili LED de sana bilgi vermek için yanıp sönecek.

    digitalWrite(ledPin, LOW);             // LED Yanık -> Motor Dönüyor
    myESC.writeMicroseconds(MIN_GAZ + 80); // Güvenli düşük hız
    delay(4000);

    digitalWrite(ledPin, HIGH); // LED Sönük -> Motor Durdu
    myESC.writeMicroseconds(MIN_GAZ);
    delay(4000);
}