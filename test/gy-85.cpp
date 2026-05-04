#include <Arduino.h>
#include <stm32f4xx.h>
#include <Wire.h>

// [ACCELEROMETER]: ADXL345 I2C address and registers
#define ADXL345_ADDRESS 0x53
#define ADXL345_POWER_CTL 0x2D
#define ADXL345_DATAX0 0x32

// [GYROSCOPE]: ITG3205 I2C address and registers
#define ITG3205_ADDRESS 0x68
#define ITG3205_PWR_MGMT 0x3E
#define ITG3205_DATA_REG 0x1D

// [COMPASS]: QMC5883L I2C address and registers
#define QMC5883L_ADDRESS 0x0D  // Orijinal QMC5883L adresi
#define QMC5883L_DATA_REG 0x00 // Veri register adresi 0x03 olmalı

void initAccelerometer()
{
    Wire.begin();
    Wire.beginTransmission(ADXL345_ADDRESS); // ADXL345 I2C address
    Wire.write(ADXL345_POWER_CTL);           // Power control register
    Wire.write(0x08);                        // Set measure bit to start measurements
    Wire.endTransmission();
    Serial.println("Accelerometer initialized. Reading data...");
}

void initGyroscope()
{
    Wire.begin();
    Wire.setClock(100000); // I2C hızını 100 kHz'e sabitliyoruz

    // Jiroskop Dijital Alçak Geçiren Filtre (DLPF) Yapılandırması
    Wire.beginTransmission(ITG3205_ADDRESS);
    Wire.write(0x16); // G_DLPF_FS register adresi
    Wire.write(0x18); // 42 Hz Low-Pass Filtre ve tam ölçek hassasiyeti (+/- 2000 dps) aktif edildi
    Wire.endTransmission();

    // Güç yönetimi
    Wire.beginTransmission(ITG3205_ADDRESS);
    Wire.write(ITG3205_PWR_MGMT);
    Wire.write(0x01); // Clock source to PLL with X gyro reference ve disable sleep
    Wire.endTransmission();

    Serial.println("Gyroscope initialized. Reading data...");
}

void initCompass()
{
    // 1. SET/RESET periyodunu ayarla (Önerilen değer: 0x01)
    Wire.beginTransmission(QMC5883L_ADDRESS);
    Wire.write(0x0B);
    Wire.write(0x01);
    Wire.endTransmission();

    // 2. Control Register 1'i ayarla
    Wire.beginTransmission(QMC5883L_ADDRESS);
    Wire.write(0x09); // Control Register 1 adresi
    Wire.write(0x01); // Mod: Continuous Measurement, 10Hz, 2G, 512 OSR
    Wire.endTransmission();

    Serial.println("Compass initialized (QMC5883L)...");
}

void setup()
{
    Serial.begin(115200);
    Wire.begin();

    initAccelerometer();
    initGyroscope();
    initCompass();
}

void loop()
{
    // START READING ACCELEROMETER
    Wire.beginTransmission(ADXL345_ADDRESS);
    Wire.write(ADXL345_DATAX0);
    Wire.endTransmission(false); // Send repeated start for reading

    Wire.requestFrom(ADXL345_ADDRESS, 6);
    if (Wire.available() >= 6)
    {
        int16_t ax_raw = (Wire.read() | (Wire.read() << 8));
        int16_t ay_raw = (Wire.read() | (Wire.read() << 8));
        int16_t az_raw = (Wire.read() | (Wire.read() << 8));
        float ax = ax_raw / 256.0;
        float ay = ay_raw / 256.0;
        float az = az_raw / 256.0;

        Serial.print("AX: ");
        Serial.print(ax, 2);
        Serial.print(" AY: ");
        Serial.print(ay, 2);
        Serial.print(" AZ: ");
        Serial.print(az, 2);
        Serial.print(" | ");
    }
    else
    {
        Serial.print("AX: No Data | ");
    }
    Wire.endTransmission(true);
    // END READING ACCELEROMETER

    // START READING GYROSCOPE
    Wire.beginTransmission(ITG3205_ADDRESS);
    Wire.write(ITG3205_DATA_REG);
    Wire.endTransmission(false); // Send repeated start for reading

    Wire.requestFrom(ITG3205_ADDRESS, 6);
    if (Wire.available() >= 6)
    {
        int16_t gx_raw = (Wire.read() << 8) | Wire.read();
        int16_t gy_raw = (Wire.read() << 8) | Wire.read();
        int16_t gz_raw = (Wire.read() << 8) | Wire.read();

        float gx = (float)gx_raw / 14.375;
        float gy = (float)gy_raw / 14.375;
        float gz = (float)gz_raw / 14.375;

        Serial.print("GX: ");
        Serial.print(gx, 2);
        Serial.print(" GY: ");
        Serial.print(gy, 2);
        Serial.print(" GZ: ");
        Serial.print(gz, 2);
        Serial.print(" | ");
    }
    else
    {
        Serial.print("GX: No Data | ");
    }
    Wire.endTransmission(true);
    // END READING GYROSCOPE

    // START READING COMPASS
    Wire.beginTransmission(QMC5883L_ADDRESS);
    Wire.write(QMC5883L_DATA_REG); // 0x00 adresinden başlat
    Wire.endTransmission(false);

    Wire.requestFrom(QMC5883L_ADDRESS, 6);
    if (Wire.available() >= 6)
    {
        int16_t mx_raw = (int16_t)(Wire.read() | (Wire.read() << 8));
        int16_t my_raw = (int16_t)(Wire.read() | (Wire.read() << 8));
        int16_t mz_raw = (int16_t)(Wire.read() | (Wire.read() << 8));

        float mx = (float)mx_raw * 0.092;
        float my = (float)my_raw * 0.092;
        float mz = (float)mz_raw * 0.092;

        float heading = atan2(my, mx) * 180.0 / PI;
        if (heading < 0)
        {
            heading += 360.0;
        }
        Serial.print("Heading: ");
        Serial.print(heading, 2);
        Serial.print(" | ");
    }
    else
    {
        Serial.println("MX: No Data");
    }
    // END READING COMPASS

    Serial.println();
    delay(200);
}